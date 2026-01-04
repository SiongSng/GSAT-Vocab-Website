"""
Embedding-based features for vocabulary prediction.

Uses OpenAI text-embedding-3-small for semantic features:
1. Semantic similarity to historically tested vocabulary
2. Vocabulary clustering by semantic domains
3. Context-aware embeddings from exam sentences

Embeddings are computed once and cached to disk.
"""

import hashlib
import logging
import pickle
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import numpy as np
from openai import OpenAI, RateLimitError

logger = logging.getLogger(__name__)

EMBEDDING_DIM = 1536  # text-embedding-3-small dimension


class EmbeddingCache:
    """Disk-based embedding cache to avoid recomputation"""

    def __init__(self, cache_dir: Path):
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._memory_cache: dict[str, np.ndarray] = {}

    def _get_key(self, text: str) -> str:
        """Generate cache key from text"""
        return hashlib.md5(text.encode()).hexdigest()

    def get(self, text: str) -> np.ndarray | None:
        """Get embedding from cache"""
        key = self._get_key(text)

        if key in self._memory_cache:
            return self._memory_cache[key]

        cache_path = self.cache_dir / f"{key}.npy"
        if cache_path.exists():
            emb = np.load(cache_path)
            self._memory_cache[key] = emb
            return emb

        return None

    def put(self, text: str, embedding: np.ndarray):
        """Store embedding in cache"""
        key = self._get_key(text)
        self._memory_cache[key] = embedding
        cache_path = self.cache_dir / f"{key}.npy"
        np.save(cache_path, embedding)

    def get_batch(self, texts: list[str]) -> tuple[list[np.ndarray | None], list[int]]:
        """Get batch of embeddings, return missing indices"""
        results = []
        missing_indices = []

        for i, text in enumerate(texts):
            emb = self.get(text)
            results.append(emb)
            if emb is None:
                missing_indices.append(i)

        return results, missing_indices


class VocabEmbedder:
    """
    Computes vocabulary embeddings using OpenAI API.

    Features:
    - Batched computation for efficiency
    - Disk caching to avoid recomputation
    - Rate limit handling with retries
    """

    def __init__(
        self,
        cache_dir: Path | str = "data/cache/embeddings",
    ):
        self.cache_dir = Path(cache_dir)
        self.cache = EmbeddingCache(self.cache_dir)
        self._client: OpenAI | None = None
        self._model: str | None = None
        self._request_delay: float = 0.0

    def _get_client(self) -> OpenAI:
        """Get or create OpenAI client"""
        if self._client is None:
            from ..config import get_settings
            settings = get_settings()
            self._client = OpenAI(
                api_key=settings.openai_api_key,
                base_url=settings.openai_base_url,
            )
            self._model = settings.openai_embedding_model
            self._request_delay = settings.llm_request_delay
        return self._client

    def _compute_batch(
        self,
        texts: list[str],
        max_retries: int = 3,
    ) -> list[np.ndarray]:
        """Compute embeddings for a single batch with retry logic"""
        client = self._get_client()

        for attempt in range(max_retries):
            try:
                if self._request_delay > 0:
                    time.sleep(self._request_delay)

                response = client.embeddings.create(
                    input=texts,
                    model=self._model,
                )
                return [np.array(item.embedding) for item in response.data]

            except RateLimitError:
                wait_time = 10 * (attempt + 1)
                logger.warning(
                    f"Rate limit hit, waiting {wait_time}s (attempt {attempt + 1}/{max_retries})..."
                )
                time.sleep(wait_time)

            except Exception as e:
                if attempt == max_retries - 1:
                    logger.error(f"Embedding failed after {max_retries} attempts: {e}")
                    raise
                wait_time = 2 * (attempt + 1)
                logger.warning(
                    f"Embedding failed, retrying in {wait_time}s (attempt {attempt + 1}/{max_retries}): {e}"
                )
                time.sleep(wait_time)

        raise RuntimeError("Max retries exceeded")

    def embed_texts(
        self,
        texts: list[str],
        use_cache: bool = True,
        batch_size: int = 500,
        max_workers: int = 8,
    ) -> list[np.ndarray]:
        """
        Embed a list of texts, using cache when possible.

        Args:
            texts: List of texts to embed
            use_cache: Whether to use disk cache
            batch_size: Number of texts per API call (max ~2000 for OpenAI)
            max_workers: Number of parallel API requests

        Returns:
            List of embedding vectors (1536-dim each)
        """
        if not texts:
            return []

        if use_cache:
            cached, missing_indices = self.cache.get_batch(texts)
        else:
            cached = [None] * len(texts)
            missing_indices = list(range(len(texts)))

        if missing_indices:
            missing_texts = [texts[i] for i in missing_indices]
            n_batches = (len(missing_texts) + batch_size - 1) // batch_size
            logger.info(
                f"Computing {len(missing_texts)} embeddings via OpenAI API "
                f"({n_batches} batches, {max_workers} workers)..."
            )

            batches = [
                (i, missing_texts[i:i + batch_size])
                for i in range(0, len(missing_texts), batch_size)
            ]

            batch_results: dict[int, list[np.ndarray]] = {}
            completed = 0

            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = {
                    executor.submit(self._compute_batch, batch): batch_idx
                    for batch_idx, batch in batches
                }

                for future in as_completed(futures):
                    batch_idx = futures[future]
                    try:
                        result = future.result()
                        batch_results[batch_idx] = result
                        completed += 1
                        if completed % 10 == 0 or completed == len(batches):
                            logger.info(f"Embedding progress: {completed}/{len(batches)} batches")
                    except Exception as e:
                        logger.error(f"Batch {batch_idx} failed: {e}")
                        batch_size_actual = len(batches[batch_idx // batch_size][1]) if batch_idx < len(batches) else batch_size
                        batch_results[batch_idx] = [np.zeros(EMBEDDING_DIM)] * batch_size_actual

            all_new_embeddings = []
            for batch_idx, _ in batches:
                all_new_embeddings.extend(batch_results.get(batch_idx, []))

            for idx, emb in zip(missing_indices, all_new_embeddings, strict=False):
                cached[idx] = emb
                if use_cache:
                    self.cache.put(texts[idx], emb)

        return [e if e is not None else np.zeros(EMBEDDING_DIM) for e in cached]


class EmbeddingFeatureExtractor:
    """
    Extracts embedding-based features for ML training.

    Features:
    1. Centroid similarity: Distance to "tested words" centroid
    2. Cluster membership: Which semantic cluster does the word belong to
    3. Nearest tested neighbors: K-nearest tested words
    """

    def __init__(
        self,
        embedder: VocabEmbedder | None = None,
        n_clusters: int = 20,
    ):
        self.embedder = embedder or VocabEmbedder()
        self.n_clusters = n_clusters

        self._tested_centroid: np.ndarray | None = None
        self._recent_centroid: np.ndarray | None = None
        self._cluster_model = None
        self._cluster_test_rates: dict[int, float] = {}
        self._all_embeddings: np.ndarray | None = None
        self._lemma_to_idx: dict[str, int] = {}

    def fit(
        self,
        vocab_data: list[dict],
        target_year: int,
        tested_lemmas: set[str],
        recent_tested_lemmas: set[str] | None = None,
    ):
        """
        Fit the embedding feature extractor.

        Args:
            vocab_data: List of word dictionaries
            target_year: Year for prediction
            tested_lemmas: Set of lemmas tested before target_year
            recent_tested_lemmas: Set of lemmas tested in last 3 years
        """
        self._lemma_to_idx = {w.get("lemma", ""): i for i, w in enumerate(vocab_data)}

        # Prepare texts for embedding
        texts = []
        for w in vocab_data:
            lemma = w.get("lemma", "")
            senses = w.get("senses", [])

            if senses:
                sense_text = "; ".join([
                    f"{s.get('zh_def', '')} {s.get('en_def', '')}"
                    for s in senses[:3]
                ])
                text = f"{lemma}: {sense_text}"
            else:
                text = lemma

            texts.append(text)

        # Compute embeddings
        logger.info(f"Computing embeddings for {len(texts)} vocabulary items...")
        embeddings = self.embedder.embed_texts(texts)
        self._all_embeddings = np.array(embeddings, dtype=np.float64)

        # Compute tested centroid
        tested_indices = [
            self._lemma_to_idx[lemma]
            for lemma in tested_lemmas
            if lemma in self._lemma_to_idx
        ]
        if tested_indices:
            self._tested_centroid = self._all_embeddings[tested_indices].mean(axis=0)
        else:
            self._tested_centroid = self._all_embeddings.mean(axis=0)

        # Compute recent tested centroid
        if recent_tested_lemmas:
            recent_indices = [
                self._lemma_to_idx[lemma]
                for lemma in recent_tested_lemmas
                if lemma in self._lemma_to_idx
            ]
            if recent_indices:
                self._recent_centroid = self._all_embeddings[recent_indices].mean(axis=0)

        # Fit clustering model
        try:
            from sklearn.cluster import KMeans
            self._cluster_model = KMeans(
                n_clusters=min(self.n_clusters, len(vocab_data)),
                random_state=42,
                n_init=10,
            )
            cluster_labels = self._cluster_model.fit_predict(self._all_embeddings)

            for cluster_id in range(self.n_clusters):
                cluster_indices = np.where(cluster_labels == cluster_id)[0]
                if len(cluster_indices) == 0:
                    continue

                tested_in_cluster = sum(
                    1 for idx in cluster_indices
                    if vocab_data[idx].get("lemma", "") in tested_lemmas
                )
                self._cluster_test_rates[cluster_id] = tested_in_cluster / len(cluster_indices)

        except Exception as e:
            logger.warning(f"Clustering failed: {e}")
            self._cluster_model = None

        logger.info("Embedding feature extractor fitted successfully")

    def extract_features(self, lemma: str) -> dict[str, float]:
        """Extract embedding-based features for a single word."""
        features = {
            "emb_centroid_sim": 0.0,
            "emb_recent_centroid_sim": 0.0,
            "emb_cluster_id": -1.0,
            "emb_cluster_test_rate": 0.0,
            "emb_norm": 0.0,
        }

        if self._all_embeddings is None or lemma not in self._lemma_to_idx:
            return features

        idx = self._lemma_to_idx[lemma]
        emb = self._all_embeddings[idx]

        if self._tested_centroid is not None:
            features["emb_centroid_sim"] = float(self._cosine_similarity(emb, self._tested_centroid))

        if self._recent_centroid is not None:
            features["emb_recent_centroid_sim"] = float(self._cosine_similarity(emb, self._recent_centroid))

        if self._cluster_model is not None:
            cluster_id = int(self._cluster_model.predict([emb])[0])
            features["emb_cluster_id"] = float(cluster_id)
            features["emb_cluster_test_rate"] = self._cluster_test_rates.get(cluster_id, 0.0)

        features["emb_norm"] = float(np.linalg.norm(emb))

        return features

    def extract_batch(self, lemmas: list[str]) -> list[dict[str, float]]:
        """Extract embedding features for multiple words"""
        return [self.extract_features(lemma) for lemma in lemmas]

    @staticmethod
    def _cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
        """Compute cosine similarity between two vectors"""
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return float(np.dot(a, b) / (norm_a * norm_b))

    def save(self, path: Path):
        """Save fitted state to disk"""
        data = {
            "tested_centroid": self._tested_centroid,
            "recent_centroid": self._recent_centroid,
            "cluster_model": self._cluster_model,
            "cluster_test_rates": self._cluster_test_rates,
            "all_embeddings": self._all_embeddings,
            "lemma_to_idx": self._lemma_to_idx,
        }
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "wb") as f:
            pickle.dump(data, f)

    @classmethod
    def load(cls, path: Path, embedder: VocabEmbedder | None = None) -> "EmbeddingFeatureExtractor":
        """Load fitted state from disk"""
        with open(path, "rb") as f:
            data = pickle.load(f)

        obj = cls(embedder=embedder)
        obj._tested_centroid = data["tested_centroid"]
        obj._recent_centroid = data["recent_centroid"]
        obj._cluster_model = data["cluster_model"]
        obj._cluster_test_rates = data["cluster_test_rates"]
        obj._all_embeddings = data["all_embeddings"]
        obj._lemma_to_idx = data["lemma_to_idx"]

        return obj


EMBEDDING_FEATURE_NAMES = [
    "emb_centroid_sim",
    "emb_recent_centroid_sim",
    "emb_cluster_id",
    "emb_cluster_test_rate",
    "emb_norm",
]
