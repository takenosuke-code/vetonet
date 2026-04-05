"""
ML-based attack classifier for VetoNet.

Fast CPU-based classifier that runs before the LLM semantic check.
Uses sentence embeddings + sklearn classifier for quick inference.
"""

import hashlib
import hmac
import io
import os
import json
import logging
from pathlib import Path
from typing import Optional

from vetonet.models import IntentAnchor, AgentPayload, CheckResult

logger = logging.getLogger(__name__)

# Lazy load ML dependencies to avoid import errors if not installed
_embedder = None
_classifier = None
_model_loaded = False
_load_attempted = False


def _get_model_path() -> Path:
    """Get the path to the trained classifier model."""
    # Check environment variable first
    model_path = os.environ.get("VETONET_CLASSIFIER_PATH")
    if model_path:
        return Path(model_path)

    # Default to models directory relative to package
    package_dir = Path(__file__).parent.parent.parent
    return package_dir / "models" / "attack_classifier.pkl"


def _verify_model_integrity(data: bytes) -> bool:
    """Verify model file integrity against expected SHA-256 hash.

    Returns True if hash matches, False if mismatch or env var not set.
    """
    try:
        computed = hashlib.sha256(data).hexdigest()
        expected = os.environ.get("VETONET_CLASSIFIER_HASH")

        if expected:
            if hmac.compare_digest(computed, expected.lower().strip()):
                return True
            logger.error(
                "Model hash mismatch! Expected %s, got %s",
                expected.lower().strip(),
                computed,
            )
            return False

        logger.error("VETONET_CLASSIFIER_HASH env var is required but not set")
        return False
    except Exception:
        logger.exception("Error verifying model integrity")
        return False


def _download_from_supabase(model_path: Path) -> bool:
    """Download model from Supabase Storage if not found locally."""
    try:
        from supabase import create_client

        url = os.environ.get("SUPABASE_URL")
        key = os.environ.get("SUPABASE_KEY")

        if not url or not key:
            logger.warning("Supabase credentials not set, cannot download model")
            return False

        logger.info("Downloading classifier model from Supabase Storage...")
        client = create_client(url, key)

        # Download from storage
        data = client.storage.from_("models").download("attack_classifier.pkl")

        # Verify integrity before writing to disk
        if not _verify_model_integrity(data):
            logger.error("Downloaded model failed integrity check — refusing to save")
            return False

        # Ensure directory exists
        model_path.parent.mkdir(parents=True, exist_ok=True)

        # Save to local file
        with open(model_path, "wb") as f:
            f.write(data)

        logger.info(f"Model downloaded to {model_path} ({len(data) / 1024:.1f} KB)")
        return True

    except Exception as e:
        logger.error(f"Failed to download model from Supabase: {e}")
        return False


def _load_model() -> bool:
    """
    Lazily load the ML model and embedder.
    Returns True if model loaded successfully, False otherwise.
    """
    global _embedder, _classifier, _model_loaded, _load_attempted

    if _load_attempted:
        return _model_loaded

    _load_attempted = True

    try:
        from sentence_transformers import SentenceTransformer
        import joblib

        model_path = _get_model_path()

        # Track whether model was freshly downloaded vs already on disk
        was_downloaded = False
        if not model_path.exists():
            logger.info(f"Model not found at {model_path}, checking Supabase...")
            if not _download_from_supabase(model_path):
                logger.warning("Could not load classifier model")
                return False
            was_downloaded = True

        logger.info(f"Loading classifier model from {model_path}")

        # Read raw bytes for integrity check and safe deserialization
        raw_bytes = model_path.read_bytes()
        expected_hash = os.environ.get("VETONET_CLASSIFIER_HASH")

        if expected_hash:
            computed = hashlib.sha256(raw_bytes).hexdigest()
            if not hmac.compare_digest(computed, expected_hash.lower().strip()):
                logger.error(
                    "Model hash mismatch! Expected %s, got %s",
                    expected_hash.lower().strip(),
                    computed,
                )
                return False
        elif was_downloaded:
            logger.error(
                "VETONET_CLASSIFIER_HASH required for downloaded models — refusing to load"
            )
            model_path.unlink(missing_ok=True)
            return False
        else:
            logger.warning("VETONET_CLASSIFIER_HASH not set — loading unverified local model")

        # Load embedder (small, fast model)
        _embedder = SentenceTransformer("all-MiniLM-L6-v2")

        # Load trained classifier from bytes (avoids TOCTOU with disk file)
        _classifier = joblib.load(io.BytesIO(raw_bytes))

        # Suppress verbose output from RandomForest
        if hasattr(_classifier, "verbose"):
            _classifier.verbose = 0

        _model_loaded = True
        logger.info("Classifier model loaded successfully")
        return True

    except ImportError as e:
        logger.warning(f"ML dependencies not installed: {e}")
        logger.warning("Install with: pip install sentence-transformers joblib scikit-learn")
        return False

    except Exception as e:
        logger.error(f"Failed to load classifier model: {e}")
        return False


def is_classifier_available() -> bool:
    """Check if the classifier is available and loaded."""
    return _load_model()


def check_classifier(
    anchor: IntentAnchor, payload: AgentPayload, confidence_threshold: float = 0.85
) -> Optional[CheckResult]:
    """
    Run the ML classifier check on a transaction.

    This is a fast pre-filter that runs before the LLM semantic check.
    It can confidently block obvious attacks or pass obvious legitimate requests.
    Uncertain cases (confidence between 0.5 and threshold) should fall through to LLM.

    Args:
        anchor: The user's locked intent
        payload: The agent's proposed transaction
        confidence_threshold: Minimum confidence to block (default 0.85)

    Returns:
        CheckResult if confident, None if uncertain (should fall through to LLM)
    """
    if not _load_model():
        # Model not available, skip this check
        return None

    try:
        # Prepare text for embedding (same format as training)
        prompt_text = (
            f"{anchor.item_category} {anchor.max_price} {' '.join(anchor.core_constraints)}"
        )
        payload_dict = payload.model_dump() if hasattr(payload, "model_dump") else payload.dict()
        # Remove metadata field and sort keys for consistent formatting with training data
        payload_dict.pop("metadata", None)
        payload_json = json.dumps(payload_dict, sort_keys=True, default=str)

        text = f"{prompt_text} | {payload_json}"

        # Create embedding
        embedding = _embedder.encode([text])

        # Get prediction probabilities
        proba = _classifier.predict_proba(embedding)[0]

        # proba[0] = legitimate, proba[1] = attack
        attack_prob = proba[1]
        legitimate_prob = proba[0]

        # Decision logic
        if attack_prob >= confidence_threshold:
            # Confident it's an attack
            return CheckResult(
                name="classifier",
                passed=False,
                reason=f"ML classifier detected attack pattern ({attack_prob:.0%} confidence)",
                score=1.0 - attack_prob,  # Invert so lower = worse
            )

        if legitimate_prob >= confidence_threshold:
            # Confident it's legitimate
            return CheckResult(
                name="classifier",
                passed=True,
                reason=f"ML classifier approved ({legitimate_prob:.0%} confidence)",
                score=legitimate_prob,
            )

        # Uncertain - return None to signal fall-through to LLM
        logger.debug(f"Classifier uncertain: attack={attack_prob:.2f}, legit={legitimate_prob:.2f}")
        return None

    except Exception as e:
        logger.error(f"Classifier check failed: {e}")
        # On error, don't block - let the request through to other checks
        return None


def get_classifier_stats() -> dict:
    """Get statistics about the classifier model."""
    if not _load_model():
        return {"loaded": False, "error": "Model not loaded"}

    try:
        model_path = _get_model_path()
        metadata_path = model_path.parent / "attack_classifier_metadata.json"

        stats = {"loaded": True, "model_path": str(model_path), "embedder": "all-MiniLM-L6-v2"}

        if metadata_path.exists():
            with open(metadata_path) as f:
                stats["metadata"] = json.load(f)

        return stats

    except Exception as e:
        return {"loaded": True, "error": str(e)}
