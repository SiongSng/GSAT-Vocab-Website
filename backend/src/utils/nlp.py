import logging
from functools import lru_cache

import spacy

logger = logging.getLogger(__name__)

_gpu_initialized = False


def _ensure_gpu() -> None:
    """Initialize GPU once globally."""
    global _gpu_initialized
    if _gpu_initialized:
        return

    try:
        import torch

        if torch.backends.mps.is_available():
            logger.info("MPS (Apple Silicon GPU) available - enabling GPU acceleration for spaCy")
            spacy.prefer_gpu()
        elif torch.cuda.is_available():
            logger.info("CUDA available - enabling GPU acceleration for spaCy")
            spacy.prefer_gpu()
        else:
            logger.info("No GPU available - using CPU for spaCy")
    except ImportError:
        logger.warning("PyTorch not found - using CPU backend for spaCy")

    _gpu_initialized = True


@lru_cache(maxsize=4)
def load_spacy_trf(
    model_name: str = "en_core_web_trf", disable: tuple[str, ...] | None = None
) -> spacy.Language:
    """Load spaCy transformer model with GPU acceleration if available.

    Args:
        model_name: spaCy model name (default: en_core_web_trf)
        disable: Tuple of pipeline components to disable (must be tuple for caching)

    Returns:
        Loaded spaCy Language model
    """
    _ensure_gpu()

    nlp = spacy.load(model_name, disable=list(disable) if disable else [])

    try:
        trf = nlp.get_pipe("transformer")
        model = getattr(trf, "model", None)
        if model is None:
            return nlp

        for _name, param in model.named_parameters():
            device = param.device
            logger.info(f"spaCy transformer model running on device: {device}")
            break
    except Exception as e:
        logger.debug(f"Could not determine spaCy device: {e}")

    return nlp
