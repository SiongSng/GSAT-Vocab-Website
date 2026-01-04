from .features import FeatureExtractor, extract_features_for_word
from .model import ImportanceModel, load_model, train_model
from .weights import CURRICULUM_CUTOFF_YEAR, TRIAL_YEARS

# Modern pipeline components
from .value import VocabValueEstimator, VocabValue
from .embeddings import VocabEmbedder, EmbeddingFeatureExtractor
from .graph import VocabGraph, GraphFeatureExtractor
from .sense_survival import SenseLevelSurvival
from .ensemble import EnsembleVocabRanker, EnsembleConfig
from .business_metrics import (
    BusinessMetrics,
    compute_business_metrics,
    compute_coverage_at_k,
    generate_evaluation_report,
)
from .pipeline import ModernVocabPipeline, PipelineConfig

__all__ = [
    # Legacy
    "extract_features_for_word",
    "FeatureExtractor",
    "ImportanceModel",
    "load_model",
    "train_model",
    "CURRICULUM_CUTOFF_YEAR",
    "TRIAL_YEARS",
    # Modern - Value Estimation
    "VocabValueEstimator",
    "VocabValue",
    # Modern - Embeddings
    "VocabEmbedder",
    "EmbeddingFeatureExtractor",
    # Modern - Graph
    "VocabGraph",
    "GraphFeatureExtractor",
    # Modern - Sense Survival
    "SenseLevelSurvival",
    # Modern - Ensemble
    "EnsembleVocabRanker",
    "EnsembleConfig",
    # Modern - Evaluation
    "BusinessMetrics",
    "compute_business_metrics",
    "compute_coverage_at_k",
    "generate_evaluation_report",
    # Modern - Pipeline
    "ModernVocabPipeline",
    "PipelineConfig",
]
