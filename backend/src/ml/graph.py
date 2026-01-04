"""
Graph-based features for vocabulary prediction.

Models vocabulary relationships as a graph:
- Nodes: Vocabulary items
- Edges: WordNet relations (synonyms, antonyms, hypernyms) + exam co-occurrence

Uses Graph Neural Network concepts but implemented efficiently with numpy/scipy
for the current scale (~10k nodes). Can be extended to PyG if needed.
"""

import logging
import pickle
from collections import defaultdict
from pathlib import Path
from typing import Any

import numpy as np
from scipy import sparse

logger = logging.getLogger(__name__)


class VocabGraph:
    """
    Graph representation of vocabulary relationships.

    Edge types:
    1. SYNONYM: WordNet synonyms
    2. ANTONYM: WordNet antonyms
    3. HYPERNYM: WordNet hypernyms (is-a relationships)
    4. COOCCUR: Appeared in same exam question/options
    5. SIMILAR: High embedding similarity
    """

    EDGE_TYPES = {
        "synonym": 0,
        "antonym": 1,
        "hypernym": 2,
        "cooccur": 3,
        "similar": 4,
    }

    def __init__(self):
        self.lemma_to_idx: dict[str, int] = {}
        self.idx_to_lemma: dict[int, str] = {}
        self.n_nodes: int = 0

        # Adjacency matrices (sparse) per edge type
        self.adjacency: dict[str, sparse.csr_matrix] = {}

        # Node features (if any)
        self.node_features: np.ndarray | None = None

    def build(
        self,
        vocab_data: list[dict],
        embeddings: np.ndarray | None = None,
        similarity_threshold: float = 0.7,
    ):
        """
        Build the vocabulary graph from data.

        Args:
            vocab_data: List of word dictionaries
            embeddings: Optional embedding matrix for similarity edges
            similarity_threshold: Threshold for similarity-based edges
        """
        # Build node index
        for i, w in enumerate(vocab_data):
            lemma = w.get("lemma", "")
            self.lemma_to_idx[lemma.lower()] = i
            self.idx_to_lemma[i] = lemma.lower()

        self.n_nodes = len(vocab_data)
        logger.info(f"Building graph with {self.n_nodes} nodes...")

        # Initialize edge lists
        edges: dict[str, list[tuple[int, int]]] = {
            edge_type: [] for edge_type in self.EDGE_TYPES
        }

        # Build edges from vocab data
        for i, w in enumerate(vocab_data):
            lemma = w.get("lemma", "").lower()

            # Synonym edges
            for syn in w.get("synonyms", []) or []:
                syn_lower = syn.lower()
                if syn_lower in self.lemma_to_idx:
                    j = self.lemma_to_idx[syn_lower]
                    if i != j:
                        edges["synonym"].append((i, j))

            # Antonym edges
            for ant in w.get("antonyms", []) or []:
                ant_lower = ant.lower()
                if ant_lower in self.lemma_to_idx:
                    j = self.lemma_to_idx[ant_lower]
                    if i != j:
                        edges["antonym"].append((i, j))

        # Build co-occurrence edges from contexts
        cooccur_map = self._build_cooccurrence(vocab_data)
        for (i, j), count in cooccur_map.items():
            if count >= 2:  # At least 2 co-occurrences
                edges["cooccur"].append((i, j))

        # Build similarity edges from embeddings
        if embeddings is not None and len(embeddings) == self.n_nodes:
            similarity_edges = self._build_similarity_edges(
                embeddings, similarity_threshold
            )
            edges["similar"] = similarity_edges

        # Convert to sparse matrices
        for edge_type, edge_list in edges.items():
            if edge_list:
                rows, cols = zip(*edge_list) if edge_list else ([], [])
                data = np.ones(len(rows))
                adj = sparse.csr_matrix(
                    (data, (rows, cols)),
                    shape=(self.n_nodes, self.n_nodes)
                )
                # Make symmetric for undirected edges
                self.adjacency[edge_type] = adj + adj.T
            else:
                self.adjacency[edge_type] = sparse.csr_matrix(
                    (self.n_nodes, self.n_nodes)
                )

        # Log statistics
        for edge_type, adj in self.adjacency.items():
            n_edges = adj.nnz // 2  # Divide by 2 for undirected
            logger.info(f"  {edge_type}: {n_edges} edges")

    def _build_cooccurrence(self, vocab_data: list[dict]) -> dict[tuple[int, int], int]:
        """Build co-occurrence edges from exam contexts"""
        # Group words by (year, exam_type, question_number)
        question_words: dict[tuple, set[int]] = defaultdict(set)

        for i, w in enumerate(vocab_data):
            contexts = w.get("contexts", [])
            for ctx in contexts:
                source = ctx.get("source", {})
                year = ctx.get("year") or source.get("year") or 0
                exam_type = ctx.get("exam_type") or source.get("exam_type", "")
                q_num = source.get("question_number") or 0

                if year > 0 and q_num > 0:
                    key = (year, str(exam_type), q_num)
                    question_words[key].add(i)

        # Count co-occurrences
        cooccur: dict[tuple[int, int], int] = defaultdict(int)
        for words in question_words.values():
            word_list = list(words)
            for idx_a in range(len(word_list)):
                for idx_b in range(idx_a + 1, len(word_list)):
                    i, j = word_list[idx_a], word_list[idx_b]
                    key = (min(i, j), max(i, j))
                    cooccur[key] += 1

        return cooccur

    def _build_similarity_edges(
        self,
        embeddings: np.ndarray,
        threshold: float,
        max_neighbors: int = 10,
    ) -> list[tuple[int, int]]:
        """Build similarity edges from embeddings using approximate KNN"""
        edges = []

        # Normalize embeddings for cosine similarity
        norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        normalized = embeddings / norms

        # For efficiency, use approximate nearest neighbors
        # Here we use brute force for simplicity, but could use FAISS/Annoy
        try:
            from sklearn.neighbors import NearestNeighbors
            nn = NearestNeighbors(n_neighbors=max_neighbors + 1, metric="cosine")
            nn.fit(normalized)
            distances, indices = nn.kneighbors(normalized)

            for i in range(len(embeddings)):
                for j, dist in zip(indices[i], distances[i], strict=False):
                    if i != j and (1 - dist) >= threshold:
                        edges.append((i, j))

        except Exception as e:
            logger.warning(f"Similarity edge building failed: {e}")

        return edges

    def get_neighbors(self, lemma: str, edge_type: str | None = None) -> list[str]:
        """Get neighboring nodes for a lemma"""
        lemma_lower = lemma.lower()
        if lemma_lower not in self.lemma_to_idx:
            return []

        idx = self.lemma_to_idx[lemma_lower]
        neighbors = set()

        if edge_type:
            if edge_type in self.adjacency:
                row = self.adjacency[edge_type].getrow(idx)
                for j in row.indices:
                    neighbors.add(self.idx_to_lemma[j])
        else:
            # All edge types
            for adj in self.adjacency.values():
                row = adj.getrow(idx)
                for j in row.indices:
                    neighbors.add(self.idx_to_lemma[j])

        return list(neighbors)

    def get_degree(self, lemma: str, edge_type: str | None = None) -> int:
        """Get node degree (number of connections)"""
        lemma_lower = lemma.lower()
        if lemma_lower not in self.lemma_to_idx:
            return 0

        idx = self.lemma_to_idx[lemma_lower]

        if edge_type:
            if edge_type in self.adjacency:
                return int(self.adjacency[edge_type].getrow(idx).nnz)
            return 0
        else:
            total = 0
            for adj in self.adjacency.values():
                total += adj.getrow(idx).nnz
            return total


class GraphFeatureExtractor:
    """
    Extracts graph-based features for ML training.

    Features:
    1. Node degree (by edge type)
    2. Neighbor test rate (what fraction of neighbors were tested)
    3. PageRank-like centrality
    4. Local clustering coefficient
    """

    def __init__(self, graph: VocabGraph | None = None):
        self.graph = graph

        # Computed on fit()
        self._pagerank: dict[int, float] = {}
        self._neighbor_test_rates: dict[int, dict[str, float]] = {}

    def fit(
        self,
        graph: VocabGraph,
        tested_lemmas: set[str],
        target_year: int | None = None,
    ):
        """
        Fit the graph feature extractor.

        Args:
            graph: Vocabulary graph
            tested_lemmas: Set of tested lemmas
            target_year: Year for prediction (filters test history)
        """
        self.graph = graph

        # Compute PageRank
        self._pagerank = self._compute_pagerank()

        # Compute neighbor test rates
        tested_indices = {
            graph.lemma_to_idx[lemma.lower()]
            for lemma in tested_lemmas
            if lemma.lower() in graph.lemma_to_idx
        }

        for idx in range(graph.n_nodes):
            self._neighbor_test_rates[idx] = {}

            for edge_type, adj in graph.adjacency.items():
                row = adj.getrow(idx)
                neighbors = row.indices

                if len(neighbors) == 0:
                    self._neighbor_test_rates[idx][edge_type] = 0.0
                else:
                    tested_neighbors = sum(1 for n in neighbors if n in tested_indices)
                    self._neighbor_test_rates[idx][edge_type] = tested_neighbors / len(neighbors)

        logger.info("Graph feature extractor fitted")

    def _compute_pagerank(self, damping: float = 0.85, max_iter: int = 100) -> dict[int, float]:
        """Compute PageRank centrality"""
        if not self.graph or self.graph.n_nodes == 0:
            return {}

        # Combine all adjacency matrices
        combined = sparse.csr_matrix((self.graph.n_nodes, self.graph.n_nodes))
        for adj in self.graph.adjacency.values():
            combined = combined + adj

        # Make stochastic (row-normalized)
        row_sums = np.array(combined.sum(axis=1)).flatten()
        row_sums[row_sums == 0] = 1.0
        normalized = combined.multiply(1.0 / row_sums.reshape(-1, 1))

        # Power iteration
        n = self.graph.n_nodes
        pr = np.ones(n) / n

        for _ in range(max_iter):
            pr_new = (1 - damping) / n + damping * normalized.T.dot(pr)
            if np.allclose(pr, pr_new, atol=1e-6):
                break
            pr = pr_new

        return {i: float(pr[i]) for i in range(n)}

    def extract_features(self, lemma: str) -> dict[str, float]:
        """
        Extract graph-based features for a single word.
        """
        features = {
            "graph_degree_total": 0.0,
            "graph_degree_synonym": 0.0,
            "graph_degree_antonym": 0.0,
            "graph_degree_cooccur": 0.0,
            "graph_pagerank": 0.0,
            "graph_neighbor_test_rate_synonym": 0.0,
            "graph_neighbor_test_rate_cooccur": 0.0,
        }

        if not self.graph:
            return features

        lemma_lower = lemma.lower()
        if lemma_lower not in self.graph.lemma_to_idx:
            return features

        idx = self.graph.lemma_to_idx[lemma_lower]

        # Degree features
        features["graph_degree_total"] = float(self.graph.get_degree(lemma))
        features["graph_degree_synonym"] = float(self.graph.get_degree(lemma, "synonym"))
        features["graph_degree_antonym"] = float(self.graph.get_degree(lemma, "antonym"))
        features["graph_degree_cooccur"] = float(self.graph.get_degree(lemma, "cooccur"))

        # PageRank
        features["graph_pagerank"] = self._pagerank.get(idx, 0.0)

        # Neighbor test rates
        if idx in self._neighbor_test_rates:
            rates = self._neighbor_test_rates[idx]
            features["graph_neighbor_test_rate_synonym"] = rates.get("synonym", 0.0)
            features["graph_neighbor_test_rate_cooccur"] = rates.get("cooccur", 0.0)

        return features

    def extract_batch(self, lemmas: list[str]) -> list[dict[str, float]]:
        """Extract graph features for multiple words"""
        return [self.extract_features(lemma) for lemma in lemmas]

    def save(self, path: Path):
        """Save fitted state"""
        data = {
            "graph": self.graph,
            "pagerank": self._pagerank,
            "neighbor_test_rates": self._neighbor_test_rates,
        }
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "wb") as f:
            pickle.dump(data, f)

    @classmethod
    def load(cls, path: Path) -> "GraphFeatureExtractor":
        """Load fitted state"""
        with open(path, "rb") as f:
            data = pickle.load(f)

        obj = cls()
        obj.graph = data["graph"]
        obj._pagerank = data["pagerank"]
        obj._neighbor_test_rates = data["neighbor_test_rates"]

        return obj


# Feature names for integration
GRAPH_FEATURE_NAMES = [
    "graph_degree_total",
    "graph_degree_synonym",
    "graph_degree_antonym",
    "graph_degree_cooccur",
    "graph_pagerank",
    "graph_neighbor_test_rate_synonym",
    "graph_neighbor_test_rate_cooccur",
]
