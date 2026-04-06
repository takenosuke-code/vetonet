"""
VetoNet API Backend
Connects React playground to the real VetoNet engine
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
from werkzeug.middleware.proxy_fix import ProxyFix
from datetime import datetime
from functools import wraps
import hashlib
import hmac
import json
import logging
import os

logger = logging.getLogger("vetonet.api")

from vetonet.normalizer import IntentNormalizer
from vetonet.engine import VetoEngine
from vetonet.models import AgentPayload, Fee, VetoStatus
from vetonet.llm.client import create_client
from vetonet.config import LLMConfig
from vetonet import db as supabase_db
from vetonet.checks.classifier import is_classifier_available, get_classifier_stats
from vetonet.auth import (
    require_api_key as require_user_api_key,
    create_api_key,
    list_user_keys,
    revoke_api_key,
)
from vetonet.ratelimit import get_limiter
from demo.shopping_agent import ShoppingAgent, AgentMode

app = Flask(__name__)
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1)

# CORS origins from env or defaults
CORS_ORIGINS = os.environ.get(
    "CORS_ORIGINS", "https://veto-net.org,https://vetonet-3jz7.vercel.app,http://localhost:5173"
).split(",")
CORS(app, origins=CORS_ORIGINS)

# ============== LLM Configuration ==============
# Railway/production: Use Groq (free, fast)
# Local: Use Ollama
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
LLM_PROVIDER = os.environ.get("LLM_PROVIDER", "groq" if GROQ_API_KEY else "ollama")

if GROQ_API_KEY:
    llm_config = LLMConfig(
        provider="groq",
        model="llama-3.1-8b-instant",
        api_key=GROQ_API_KEY,
    )
    llm_client = create_client(llm_config)
    normalizer = IntentNormalizer(llm_client)
    engine = VetoEngine(llm_client=llm_client)
    logger.info("LLM: Groq (llama-3.1-8b-instant)")
else:
    # Try Ollama locally, or run without LLM
    try:
        from vetonet.config import DEFAULT_LLM_CONFIG

        llm_client = create_client(DEFAULT_LLM_CONFIG)
        normalizer = IntentNormalizer(llm_client)
        engine = VetoEngine(llm_client=llm_client)
        logger.info("LLM: Ollama (local)")
    except Exception as e:
        logger.warning(f"No LLM available ({e}). Semantic checks disabled.")
        llm_client = None
        normalizer = None
        engine = VetoEngine(llm_client=None)

# ============== SECURITY: Input Validation ==============

# Limits to prevent DoS
MAX_PRICE = 1_000_000  # $1M max
MAX_QUANTITY = 10_000
MAX_PROMPT_LENGTH = 1000
MAX_DESCRIPTION_LENGTH = 500

# ============== SECURITY: Rate Limiting for Public Endpoints ==============

PUBLIC_RATE_LIMIT = 30  # requests per minute per IP
PUBLIC_RATE_WINDOW = 60  # seconds


def get_client_ip():
    """Get client IP (ProxyFix handles X-Forwarded-For)."""
    return request.remote_addr or "unknown"


def check_public_rate_limit():
    """Check if client is within rate limit. Returns (allowed, remaining, reset_time)."""
    ip = get_client_ip()
    result = get_limiter().check(ip, PUBLIC_RATE_LIMIT, PUBLIC_RATE_WINDOW)
    return result.allowed, result.remaining, result.reset_at


def rate_limit_response():
    """Return a rate limit exceeded response."""
    _, _, reset_time = check_public_rate_limit()
    response = jsonify(
        {
            "error": "Rate limit exceeded",
            "message": f"Max {PUBLIC_RATE_LIMIT} requests per minute. Try again later.",
            "retry_after": PUBLIC_RATE_WINDOW,
        }
    )
    response.headers["Retry-After"] = str(PUBLIC_RATE_WINDOW)
    response.headers["X-RateLimit-Limit"] = str(PUBLIC_RATE_LIMIT)
    response.headers["X-RateLimit-Remaining"] = "0"
    response.headers["X-RateLimit-Reset"] = str(reset_time)
    return response, 429


def require_rate_limit(f):
    """Decorator to apply rate limiting to public endpoints."""

    @wraps(f)
    def decorated(*args, **kwargs):
        allowed, remaining, reset_time = check_public_rate_limit()
        if not allowed:
            return rate_limit_response()

        response = f(*args, **kwargs)

        # Add rate limit headers to successful responses
        if isinstance(response, tuple):
            resp_obj = response[0]
        else:
            resp_obj = response

        if hasattr(resp_obj, "headers"):
            resp_obj.headers["X-RateLimit-Limit"] = str(PUBLIC_RATE_LIMIT)
            resp_obj.headers["X-RateLimit-Remaining"] = str(remaining)
            resp_obj.headers["X-RateLimit-Reset"] = str(reset_time)

        return response

    return decorated


def validate_payload(data: dict) -> tuple[bool, str]:
    """Validate incoming payload data with security limits."""
    # Check prompt length
    prompt = data.get("prompt") if "prompt" in data else data.get("intent", "")
    if len(prompt) > MAX_PROMPT_LENGTH:
        return False, f"Prompt too long (max {MAX_PROMPT_LENGTH} chars)"

    # Check payload if present
    payload = data.get("payload", {})
    if payload:
        # Price validation
        price = payload.get("unit_price", 0)
        try:
            price = float(price)
            if price < 0 or price > MAX_PRICE:
                return False, f"Price must be 0-{MAX_PRICE}"
        except (ValueError, TypeError):
            return False, "Invalid price format"

        # Quantity validation
        qty = payload.get("quantity", 1)
        try:
            qty = int(qty)
            if qty < 1 or qty > MAX_QUANTITY:
                return False, f"Quantity must be 1-{MAX_QUANTITY}"
        except (ValueError, TypeError):
            return False, "Invalid quantity format"

        # Description length
        desc = payload.get("item_description", "")
        if len(desc) > MAX_DESCRIPTION_LENGTH:
            return False, f"Description too long (max {MAX_DESCRIPTION_LENGTH} chars)"

    return True, ""


def require_api_key(f):
    """Decorator to require API key for sensitive endpoints."""

    @wraps(f)
    def decorated(*args, **kwargs):
        api_key = os.environ.get("VETONET_ADMIN_KEY")
        if not api_key:
            # Fail closed - require key to be configured
            return jsonify({"error": "Admin key not configured"}), 500
        provided_key = request.headers.get("X-API-Key")
        if not provided_key or not hmac.compare_digest(provided_key, api_key):
            return jsonify({"error": "Unauthorized"}), 401
        return f(*args, **kwargs)

    return decorated


def anonymize_data(data: dict) -> dict:
    """Remove PII and sensitive data before logging."""
    safe = data.copy()

    # Hash any potential PII fields
    if "vendor" in safe:
        # Keep domain but could hash if needed
        pass

    # Remove or hash IP addresses if present
    if "ip" in safe:
        safe["ip"] = hashlib.sha256(safe["ip"].encode()).hexdigest()[:16]

    # Truncate long descriptions that might contain PII
    if "payload" in safe and isinstance(safe["payload"], dict):
        payload = safe["payload"].copy()
        if "item_description" in payload:
            desc = payload["item_description"]
            if len(desc) > 100:
                payload["item_description"] = desc[:100] + "..."
        safe["payload"] = payload

    return safe


# ============== Database Setup ==============
# Primary: Supabase (persistent, recommended)
# Fallback: Railway Postgres or file

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_JWT_SECRET = os.environ.get("SUPABASE_JWT_SECRET")  # For JWT verification
DATABASE_URL = os.environ.get("DATABASE_URL")


def get_db():
    """Get legacy database connection (for backwards compatibility)."""
    if not DATABASE_URL:
        return None
    import psycopg2

    return psycopg2.connect(DATABASE_URL)


def init_db():
    """Initialize database connections."""
    # Check Supabase first (preferred)
    if SUPABASE_URL:
        client = supabase_db.get_client()
        if client:
            logger.info("Database: Supabase (connected)")
            return

    # Fallback to Railway Postgres
    if DATABASE_URL:
        try:
            conn = get_db()
            cur = conn.cursor()
            cur.execute("""
                CREATE TABLE IF NOT EXISTS attacks (
                    id SERIAL PRIMARY KEY,
                    timestamp TIMESTAMPTZ DEFAULT NOW(),
                    type VARCHAR(50),
                    prompt TEXT,
                    attack_vector VARCHAR(100),
                    bypassed BOOLEAN,
                    blocked_by VARCHAR(50),
                    checks JSONB,
                    payload JSONB
                )
            """)
            conn.commit()
            conn.close()
            logger.info("Database: PostgreSQL (connected)")
            return
        except Exception as e:
            logger.error(f"Database: PostgreSQL failed ({e})")

    logger.info("Database: File fallback (data/attack_attempts.jsonl)")


# Initialize database on startup
try:
    init_db()
except Exception as e:
    logger.error(f"Database: Failed ({e})")

# Data collection - log all attempts
ATTACK_LOG_FILE = "data/attack_attempts.jsonl"
os.makedirs("data", exist_ok=True)


def log_attempt(data) -> str | None:
    """
    Log attack attempts to database.

    Priority: Supabase > PostgreSQL > File

    Returns attack_id if using Supabase, None otherwise.
    """
    # Find which check blocked it
    blocked_by = None
    if not data.get("bypassed") and not data.get("approved"):
        for check in data.get("checks", []):
            if not check.get("passed"):
                blocked_by = check.get("name")
                break

    verdict = "approved" if data.get("bypassed") or data.get("approved") else "blocked"

    # Try Supabase first (preferred)
    if SUPABASE_URL:
        attack_id = supabase_db.log_attack(
            type=data.get("type"),
            prompt=data.get("prompt"),
            intent=data.get("intent"),
            payload=data.get("payload"),
            verdict=verdict,
            blocked_by=blocked_by,
            checks=data.get("checks"),
            confidence=data.get("confidence"),
            reasoning=data.get("reasoning"),
            attack_vector=data.get("attack_vector"),
            source=data.get("source"),
        )
        if attack_id:
            return attack_id

    # Fallback to Railway Postgres
    if DATABASE_URL:
        try:
            conn = get_db()
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO attacks (type, prompt, attack_vector, bypassed, blocked_by, checks, payload)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """,
                (
                    data.get("type"),
                    data.get("prompt"),
                    data.get("attack_vector"),
                    data.get("bypassed", data.get("approved", False)),
                    blocked_by,
                    json.dumps(data.get("checks", [])),
                    json.dumps(data.get("payload", {})),
                ),
            )
            conn.commit()
            conn.close()
            return None
        except Exception as e:
            logger.error(f"DB Error: {e}")

    # Fallback to file
    with open(ATTACK_LOG_FILE, "a") as f:
        f.write(json.dumps(data) + "\n")
    return None


def format_checks(result):
    """Format check results for API response"""
    return [
        {
            "id": c.name.lower().replace(" ", "_"),
            "name": c.name,
            "desc": "",
            "passed": c.passed,
            "reason": c.reason,
        }
        for c in result.checks
    ]


@app.route("/api/health", methods=["GET"])
def health():
    classifier_available = is_classifier_available()
    return jsonify(
        {
            "status": "ok",
            "engine": "vetonet",
            "classifier": {
                "available": classifier_available,
                "stats": get_classifier_stats() if classifier_available else None,
            },
        }
    )


# ============== API Key Management ==============


def get_user_from_jwt():
    """
    Extract user ID from Supabase JWT token.

    Expects Authorization: Bearer <supabase_jwt>
    Returns user_id or None.

    Uses JWKS endpoint for automatic key rotation support (ECC/RSA keys).
    Falls back to legacy HS256 if SUPABASE_JWT_SECRET is set.
    """
    import jwt
    from jwt import PyJWKClient

    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return None

    token = auth_header[7:]

    # For API keys (veto_sk_), this is not a JWT
    if token.startswith("veto_sk_"):
        return None

    try:
        # Method 1: JWKS (modern - handles ECC key rotation)
        if SUPABASE_URL:
            jwks_url = f"{SUPABASE_URL}/auth/v1/.well-known/jwks.json"
            jwks_client = PyJWKClient(jwks_url, cache_keys=True)
            signing_key = jwks_client.get_signing_key_from_jwt(token)
            payload = jwt.decode(
                token,
                signing_key.key,
                algorithms=["ES256", "RS256", "HS256"],
                audience="authenticated",
            )
            return payload.get("sub")

        # Method 2: Legacy HS256 fallback
        elif SUPABASE_JWT_SECRET:
            payload = jwt.decode(
                token, SUPABASE_JWT_SECRET, algorithms=["HS256"], audience="authenticated"
            )
            return payload.get("sub")

        else:
            app.logger.error("No SUPABASE_URL or SUPABASE_JWT_SECRET - rejecting JWT auth")
            return None

    except jwt.ExpiredSignatureError:
        app.logger.warning("JWT token expired")
        return None
    except jwt.InvalidTokenError as e:
        app.logger.warning(f"Invalid JWT token: {e}")
        return None
    except Exception as e:
        app.logger.warning(f"JWT verification error: {e}")
        return None


@app.route("/api/keys", methods=["POST"])
def create_key():
    """
    Create a new API key for the authenticated user.

    Requires Supabase JWT in Authorization header.

    Body (optional): {
        "name": "My App Key",
        "environment": "live",  # "live" or "test"
        "expires_days": 365
    }

    Returns: {
        "key": "veto_sk_live_abc123...",  # ONLY shown once!
        "id": "uuid",
        "name": "My App Key",
        "key_prefix": "veto_sk_live_",
        "environment": "live",
        "created_at": "2024-01-01T00:00:00Z",
        "warning": "Save this key now. It cannot be shown again."
    }
    """
    user_id = get_user_from_jwt()
    if not user_id:
        return jsonify({"error": "Authentication required. Use Supabase JWT."}), 401

    data = request.json or {}
    name = data.get("name")
    environment = data.get("environment", "live")
    expires_days = data.get("expires_days")

    # Validate environment
    if environment not in ("live", "test"):
        return jsonify({"error": "environment must be 'live' or 'test'"}), 400

    try:
        full_key, key_record = create_api_key(
            user_id=user_id,
            name=name,
            expires_days=expires_days,
            environment=environment,
        )

        if not key_record:
            return jsonify({"error": "Failed to create key"}), 500

        return jsonify(
            {
                "key": full_key,  # Only shown ONCE
                "warning": "Save this key now. It cannot be shown again.",
                **key_record,
            }
        ), 201

    except Exception as e:
        app.logger.error(f"Create key error: {e}")
        return jsonify({"error": "Failed to create key"}), 500


@app.route("/api/keys", methods=["GET"])
def list_keys():
    """
    List all API keys for the authenticated user.

    Keys are returned with masked display (prefix + last 8 chars).

    Returns: {
        "keys": [
            {
                "id": "uuid",
                "name": "Production Key",
                "key_prefix": "veto_sk_live_",
                "masked_key": "veto_sk_live_****abcd1234",
                "environment": "live",
                "rate_limit": 10000,
                "created_at": "...",
                "last_used_at": "..."
            }
        ]
    }
    """
    user_id = get_user_from_jwt()
    if not user_id:
        return jsonify({"error": "Authentication required. Use Supabase JWT."}), 401

    keys = list_user_keys(user_id)

    # Add masked_key for identification (shows prefix + last 8 chars)
    for key in keys:
        prefix = key.get("key_prefix", "veto_sk_")
        # Mask format: prefix + **** + last 8 chars (we only have prefix, so show it)
        key["masked_key"] = f"{prefix}****"

    return jsonify({"keys": keys})


@app.route("/api/keys/<key_id>", methods=["DELETE"])
def delete_key(key_id):
    """
    Revoke an API key.

    The key will immediately stop working.
    """
    user_id = get_user_from_jwt()
    if not user_id:
        return jsonify({"error": "Authentication required. Use Supabase JWT."}), 401

    # Validate UUID format
    import re

    if not re.match(
        r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", key_id, re.I
    ):
        return jsonify({"error": "Invalid key ID format"}), 400

    success = revoke_api_key(key_id, user_id)

    if success:
        return jsonify({"message": "Key revoked"}), 200
    else:
        return jsonify({"error": "Key not found or not owned by you"}), 404


# ============== Production API (Requires API Key) ==============


@app.route("/api/check", methods=["POST"])
@require_user_api_key
def check_transaction():
    """
    Main production endpoint - verify a transaction against VetoNet.

    Requires API key: Authorization: Bearer veto_sk_xxx

    Body: {
        "prompt": "User's original request",
        "payload": {
            "item_description": "What the agent wants to buy",
            "item_category": "electronics",
            "unit_price": 50.00,
            "quantity": 1,
            "vendor": "amazon.com",
            "currency": "USD",
            "is_recurring": false,
            "fees": []
        }
    }

    Returns: {
        "verdict": "approved" | "blocked",
        "status": "APPROVED" | "VETO",
        "reason": "Why it was blocked (if blocked)",
        "confidence": 0.95,
        "checks": [
            {"name": "price", "passed": true, "reason": "..."},
            ...
        ],
        "request_id": "uuid"
    }
    """
    data = request.json or {}

    # Validate input
    valid, error = validate_payload(data)
    if not valid:
        return jsonify({"error": error}), 400

    prompt = data.get("prompt") if "prompt" in data else data.get("intent", "")
    payload_data = data.get("payload", {})

    if not prompt:
        return jsonify({"error": "prompt required"}), 400
    if not payload_data:
        return jsonify({"error": "payload required"}), 400

    try:
        # Normalize intent
        if normalizer:
            intent = normalizer.normalize(prompt)
        else:
            # Basic fallback without LLM
            from vetonet.models import IntentAnchor

            intent = IntentAnchor(
                item_category=payload_data.get("item_category", "unknown"),
                max_price=float(payload_data.get("unit_price", 100)),
                currency=payload_data.get("currency", "USD"),
                core_constraints=[],
            )

        # Build payload
        fees = [
            Fee(name=f.get("name", ""), amount=f.get("amount", 0))
            for f in payload_data.get("fees", [])
        ]

        payload = AgentPayload(
            item_description=payload_data.get("item_description", ""),
            item_category=payload_data.get("item_category", intent.item_category),
            unit_price=float(payload_data.get("unit_price", 0)),
            quantity=int(payload_data.get("quantity", 1)),
            vendor=payload_data.get("vendor", "unknown.com"),
            currency=payload_data.get("currency", "USD"),
            is_recurring=payload_data.get("is_recurring", False),
            fees=fees,
        )

        # Run VetoNet checks
        result = engine.check(intent, payload)
        approved = result.status == VetoStatus.APPROVED

        # Extract confidence
        confidence = None
        for check in result.checks:
            if check.name == "semantic" and check.score is not None:
                confidence = check.score
                break
            if check.name == "classifier" and check.score is not None:
                confidence = check.score
                break

        # Log for analytics (includes API key user info)
        # Store FULL intent and payload for ML training
        attack_id = log_attempt(
            anonymize_data(
                {
                    "timestamp": datetime.now().isoformat(),
                    "type": "api_check",
                    "source": "api",
                    "prompt": prompt[:500],
                    "payload": payload_data,
                    "intent": intent.model_dump(),  # Full IntentAnchor for ML training
                    "approved": approved,
                    "checks": format_checks(result),
                    "confidence": confidence,
                    "reasoning": result.reason,
                    "api_key_prefix": request.api_key.key_prefix
                    if hasattr(request, "api_key")
                    else None,
                }
            )
        )

        return jsonify(
            {
                "verdict": "approved" if approved else "blocked",
                "status": result.status.value,
                "reason": result.reason,
                "confidence": confidence,
                "checks": format_checks(result),
                "request_id": attack_id,
            }
        )

    except Exception as e:
        app.logger.error(f"Check error: {e}")
        return jsonify({"error": "Check failed"}), 500


@app.route("/api/classify", methods=["POST"])
@require_rate_limit
def classify():
    """
    Remote classifier endpoint for SDK users.

    SDK users can use their own LLM but call this endpoint for ML classification.
    This allows VetoNet to collect anonymized attack data even from self-hosted users.

    Body: {
        "prompt": "$50 Amazon Gift Card",
        "payload": {
            "item_description": "Bitcoin mining contract",
            "unit_price": 500,
            "vendor": "crypto.xyz",
            ...
        }
    }

    Returns: {
        "score": 0.15,  # 0-1 (higher = more legitimate)
        "label": "attack" | "legitimate",
        "confidence": 0.85
    }
    """
    from vetonet.checks.classifier import check_classifier
    from vetonet.models import IntentAnchor, AgentPayload

    data = request.json or {}

    # Validate input
    valid, error = validate_payload(data)
    if not valid:
        return jsonify({"error": error}), 400

    prompt = data.get("prompt") if "prompt" in data else data.get("intent", "")
    payload_data = data.get("payload", {})

    if not prompt:
        return jsonify({"error": "prompt required"}), 400

    # Check if classifier is available
    if not is_classifier_available():
        return jsonify({"error": "Classifier not available"}), 503

    try:
        # Normalize intent if LLM available, otherwise use basic extraction
        if normalizer:
            anchor = normalizer.normalize(prompt)
        else:
            # Basic fallback - extract category and price from prompt
            anchor = IntentAnchor(
                item_category=payload_data.get("item_category", "unknown"),
                max_price=float(payload_data.get("unit_price", 100)),
                currency="USD",
                core_constraints=[],
            )

        # Build payload
        payload = AgentPayload(
            item_description=payload_data.get("item_description", ""),
            item_category=payload_data.get("item_category", anchor.item_category),
            unit_price=float(payload_data.get("unit_price", 0)),
            quantity=int(payload_data.get("quantity", 1)),
            vendor=payload_data.get("vendor", "unknown.com"),
            currency=payload_data.get("currency", "USD"),
            is_recurring=payload_data.get("is_recurring", False),
            fees=[],
        )

        # Run classifier
        result = check_classifier(anchor, payload, confidence_threshold=0.5)

        if result is None:
            # Classifier returned uncertain
            return jsonify({"score": 0.5, "label": "uncertain", "confidence": 0.5})

        # Log to telemetry (anonymized)
        _log_classifier_call(anchor, payload, result)

        return jsonify(
            {
                "score": result.score,
                "label": "attack" if not result.passed else "legitimate",
                "confidence": abs(result.score - 0.5) * 2,  # Convert to 0-1 confidence
            }
        )

    except Exception as e:
        app.logger.error(f"Classify error: {e}")
        return jsonify({"error": "Classification failed"}), 500


def _log_classifier_call(anchor, payload, result):
    """Log classifier call to Supabase telemetry (anonymized)."""
    if not SUPABASE_URL:
        return

    try:
        # Hash intent for privacy
        intent_hash = hashlib.sha256(
            f"{anchor.item_category}{anchor.max_price}".encode()
        ).hexdigest()[:16]

        data = {
            "intent_hash": intent_hash,
            "category": anchor.item_category,
            "approved": result.passed,
            "checks_failed": [result.name] if not result.passed else [],
            "source": "hosted_classifier",
            "classifier_score": result.score,
        }

        client = supabase_db.get_client()
        if client:
            client.table("telemetry").insert(data).execute()
    except Exception as e:
        app.logger.error(f"Telemetry log error: {e}")


@app.route("/api/demo", methods=["POST"])
@require_rate_limit
def run_demo():
    """
    Standard demo mode - honest or compromised agent
    """
    data = request.json or {}

    # SECURITY: Validate input
    valid, error = validate_payload(data)
    if not valid:
        return jsonify({"error": error}), 400

    user_prompt = data.get("prompt") if "prompt" in data else data.get("intent", "$50 Amazon Gift Card")
    mode = data.get("mode", "honest")  # "honest" or "compromised"

    # Check if LLM is available
    if normalizer is None:
        return jsonify({"error": "LLM not configured. Set GROQ_API_KEY environment variable."}), 503

    try:
        # Step 1: Lock the intent
        intent = normalizer.normalize(user_prompt)

        # Step 2: Agent shops (honest or compromised)
        agent = ShoppingAgent(mode=AgentMode.HONEST if mode == "honest" else AgentMode.COMPROMISED)
        shop_result = agent.shop(user_prompt)

        # Convert ShoppingResult to AgentPayload
        fees = [Fee(name=f["name"], amount=f["amount"]) for f in shop_result.fees]
        payload = AgentPayload(
            item_description=shop_result.item_description,
            item_category=shop_result.item_category,
            unit_price=shop_result.unit_price,
            quantity=shop_result.quantity,
            vendor=shop_result.vendor,
            currency=shop_result.currency,
            is_recurring=shop_result.is_recurring,
            fees=fees,
        )

        # Step 3: VetoNet scans
        result = engine.check(intent, payload)
        approved = result.status == VetoStatus.APPROVED

        # Extract confidence from checks (prefer semantic, fallback to classifier)
        confidence = None
        reasoning = None
        for check in result.checks:
            if check.name == "semantic" and check.score is not None:
                confidence = check.score
                reasoning = check.reason
                break
        # Fallback to classifier if semantic didn't run
        if confidence is None:
            for check in result.checks:
                if check.name == "classifier" and check.score is not None:
                    confidence = check.score
                    reasoning = check.reason
                    break

        # Log for analysis (anonymized) - returns attack_id for feedback
        # Store FULL intent and payload for ML training
        attack_id = log_attempt(
            anonymize_data(
                {
                    "timestamp": datetime.now().isoformat(),
                    "type": "demo",
                    "source": "playground",
                    "prompt": user_prompt[:500],
                    "mode": mode,
                    "intent": intent.model_dump(),  # Full IntentAnchor for ML training
                    "payload": payload.model_dump(),  # Full AgentPayload for ML training
                    "attack_vector": "standard" if mode == "default" else mode,
                    "approved": approved,
                    "bypassed": approved,  # For demo, approved = bypassed
                    "checks": [
                        {"name": c.name, "passed": c.passed, "score": c.score}
                        for c in result.checks
                    ],
                    "confidence": confidence,
                    "reasoning": reasoning,
                }
            )
        )

        response = {
            "intent": intent.model_dump(),
            "payload": payload.model_dump(),
            "result": {
                "approved": approved,
                "message": result.reason,
                "checks": format_checks(result),
            },
        }

        # Include attack_id for feedback (if using Supabase)
        if attack_id:
            response["attack_id"] = attack_id

        return jsonify(response)

    except Exception as e:
        # SECURITY: Don't expose internal error details
        app.logger.error(f"Demo error: {e}")
        return jsonify({"error": "Processing failed"}), 500


@app.route("/api/redteam", methods=["POST"])
@require_rate_limit
def red_team():
    """
    Red Team mode - user crafts custom attack payload
    Try to bypass VetoNet with a malicious payload
    """
    data = request.json or {}

    # SECURITY: Validate input
    valid, error = validate_payload(data)
    if not valid:
        return jsonify({"error": error}), 400

    user_prompt = data.get("prompt") if "prompt" in data else data.get("intent", "$50 Amazon Gift Card")
    attack_payload = data.get("payload", {})

    # Check if LLM is available
    if normalizer is None:
        return jsonify({"error": "LLM not configured. Set GROQ_API_KEY environment variable."}), 503

    try:
        # Step 1: Lock the intent (this is fixed based on user's original request)
        intent = normalizer.normalize(user_prompt)

        # Step 2: User provides the "compromised" payload
        fees = [Fee(name=f["name"], amount=f["amount"]) for f in attack_payload.get("fees", [])]

        # Use the intent's category as default, or let attacker override
        payload = AgentPayload(
            item_description=attack_payload.get("item_description", "Unknown Item"),
            item_category=attack_payload.get("item_category", intent.item_category),
            unit_price=float(attack_payload.get("unit_price", 0)),
            quantity=int(attack_payload.get("quantity", 1)),
            fees=fees,
            is_recurring=attack_payload.get("is_recurring", False),
            vendor=attack_payload.get("vendor", "unknown.com"),
            currency=attack_payload.get("currency", "USD"),
        )

        # Step 3: VetoNet scans
        result = engine.check(intent, payload)
        approved = result.status == VetoStatus.APPROVED

        # Did the attack bypass VetoNet?
        bypassed = approved

        # Extract confidence from checks (prefer semantic, fallback to classifier)
        confidence = None
        reasoning = None
        classifier_score = None
        for check in result.checks:
            if check.name == "semantic" and check.score is not None:
                confidence = check.score
                reasoning = check.reason
            if check.name == "classifier" and check.score is not None:
                classifier_score = check.score
                # Fallback to classifier if semantic didn't set confidence
                if confidence is None:
                    confidence = check.score
                    reasoning = check.reason

        # Determine if this looks like an attack (classifier score < 0.5 = attack)
        # Higher score = more legitimate, lower = more attack-like
        is_likely_attack = classifier_score is None or classifier_score < 0.5

        # Extract which check blocked it (for ML training)
        blocked_by = None
        if not bypassed:
            for check in result.checks:
                if not check.passed:
                    blocked_by = check.name
                    break

        # Log ALL transactions for ML training (attacks AND bypasses are valuable)
        attack_id = log_attempt(
            anonymize_data(
                {
                    "timestamp": datetime.now().isoformat(),
                    "type": "redteam",
                    "source": "playground",
                    "prompt": user_prompt[:500],
                    "attack_vector": _classify_attack(attack_payload),
                    "bypassed": bypassed,
                    "approved": approved,
                    "blocked_by": blocked_by,  # Track which check caught it
                    "checks": [
                        {"name": c.name, "passed": c.passed, "score": c.score}
                        for c in result.checks
                    ],
                    "intent": intent.model_dump(),  # Full IntentAnchor for ML training
                    "payload": payload.model_dump(),  # Full AgentPayload for ML training
                    "confidence": confidence,
                    "reasoning": reasoning,
                }
            )
        )

        response = {
            "intent": intent.model_dump(),
            "payload": payload.model_dump(),
            "bypassed": bypassed,
            "classifier": {"score": classifier_score, "is_attack": is_likely_attack},
            "result": {
                "approved": approved,
                "message": result.reason,
                "checks": format_checks(result),
            },
        }

        # Include attack_id for feedback (if using Supabase)
        if attack_id:
            response["attack_id"] = attack_id

        return jsonify(response)

    except Exception as e:
        # SECURITY: Don't expose internal error details
        app.logger.error(f"Redteam error: {e}")
        return jsonify({"error": "Processing failed"}), 500


@app.route("/api/feedback", methods=["POST"])
@require_rate_limit
def submit_feedback():
    """
    Submit user feedback on a verdict.

    This is CRITICAL for building the data moat - labeled data
    from real users telling us if we got it right or wrong.

    Body: {
        "attack_id": "uuid",
        "feedback": "correct" | "false_positive" | "false_negative"
    }

    - correct: VetoNet made the right decision
    - false_positive: VetoNet blocked a legitimate transaction
    - false_negative: VetoNet approved a malicious transaction
    """
    data = request.json or {}

    attack_id = data.get("attack_id")
    feedback = data.get("feedback")

    if not attack_id:
        return jsonify({"error": "attack_id required"}), 400

    if feedback not in ("correct", "false_positive", "false_negative"):
        return jsonify(
            {"error": "feedback must be 'correct', 'false_positive', or 'false_negative'"}
        ), 400

    # Submit to Supabase
    if SUPABASE_URL:
        success = supabase_db.submit_feedback(attack_id, feedback)
        if success:
            return jsonify({"status": "ok", "message": "Feedback recorded"})
        else:
            return jsonify({"error": "Failed to record feedback"}), 500

    # No Supabase configured
    return jsonify({"error": "Feedback storage not configured"}), 503


@app.route("/api/stats", methods=["GET"])
@require_rate_limit
def get_stats():
    """
    Get attack statistics for dashboard
    """
    # Try Supabase first
    if SUPABASE_URL:
        stats = supabase_db.get_stats()
        if stats.get("total_attempts", 0) > 0 or supabase_db.get_client():
            return jsonify(stats)

    # Fallback to Postgres
    if DATABASE_URL:
        try:
            conn = get_db()
            cur = conn.cursor()
            cur.execute("""
                SELECT
                    COUNT(*) as total,
                    COUNT(*) FILTER (WHERE bypassed = true) as bypassed,
                    COUNT(*) FILTER (WHERE bypassed = false) as blocked
                FROM attacks
            """)
            row = cur.fetchone()
            conn.close()

            total = row[0] or 0
            bypassed = row[1] or 0
            blocked = row[2] or 0

            return jsonify(
                {
                    "total_attempts": total,
                    "blocked": blocked,
                    "bypassed": bypassed,
                    "bypass_rate": round(bypassed / max(total, 1) * 100, 2),
                }
            )
        except Exception as e:
            logger.error(f"DB stats error: {e}")

    # Fallback to file
    if not os.path.exists(ATTACK_LOG_FILE):
        return jsonify({"total_attempts": 0, "blocked": 0, "bypassed": 0, "bypass_rate": 0})

    total = 0
    blocked = 0
    bypassed = 0

    with open(ATTACK_LOG_FILE, "r") as f:
        for line in f:
            try:
                entry = json.loads(line)
                total += 1
                if entry.get("type") == "redteam":
                    if entry.get("bypassed"):
                        bypassed += 1
                    else:
                        blocked += 1
                elif not entry.get("approved"):
                    blocked += 1
            except (json.JSONDecodeError, KeyError):
                continue

    return jsonify(
        {
            "total_attempts": total,
            "blocked": blocked,
            "bypassed": bypassed,
            "bypass_rate": round(bypassed / max(total, 1) * 100, 2),
        }
    )


@app.route("/api/attacks", methods=["GET"])
@require_api_key
def get_attacks():
    """
    Get recent attack attempts for analysis.
    SECURITY: Requires API key via X-API-Key header.
    Set VETONET_ADMIN_KEY env var to enable auth.
    """
    # Try Postgres first
    if DATABASE_URL:
        try:
            conn = get_db()
            cur = conn.cursor()
            cur.execute("""
                SELECT timestamp, type, prompt, attack_vector, bypassed, blocked_by, checks, payload
                FROM attacks
                ORDER BY timestamp DESC
                LIMIT 100
            """)
            rows = cur.fetchall()
            conn.close()

            attacks = []
            for row in rows:
                attacks.append(
                    {
                        "timestamp": row[0].isoformat() if row[0] else None,
                        "type": row[1],
                        "prompt": row[2],
                        "attack_vector": row[3],
                        "bypassed": row[4],
                        "blocked_by": row[5],
                        "checks": row[6],
                        "payload": row[7],
                    }
                )

            return jsonify({"attacks": attacks})
        except Exception as e:
            logger.error(f"DB attacks error: {e}")

    # Fallback to file
    if not os.path.exists(ATTACK_LOG_FILE):
        return jsonify({"attacks": []})

    attacks = []
    with open(ATTACK_LOG_FILE, "r") as f:
        for line in f:
            try:
                attacks.append(json.loads(line))
            except (json.JSONDecodeError, KeyError):
                continue

    # Return last 100 attacks, newest first
    return jsonify({"attacks": attacks[-100:][::-1]})


@app.route("/api/export/csv", methods=["GET"])
@require_api_key
def export_csv():
    """
    Export attack data as CSV for Google Sheets.
    SECURITY: Requires API key via X-API-Key header.
    """
    import csv
    from io import StringIO

    output = StringIO()
    writer = csv.writer(output)

    # Header row (enhanced with feedback data)
    writer.writerow(
        [
            "Timestamp",
            "Type",
            "Prompt",
            "Attack Vector",
            "Verdict",
            "Blocked By",
            "Confidence",
            "Feedback",
            "Unit Price",
            "Vendor",
        ]
    )

    # Try Supabase first
    if SUPABASE_URL:
        attacks = supabase_db.get_attacks_for_export(limit=10000)
        if attacks:
            for a in attacks:
                payload = a.get("payload") or {}
                writer.writerow(
                    [
                        a.get("created_at", ""),
                        a.get("type", ""),
                        a.get("prompt", ""),
                        a.get("attack_vector", ""),
                        a.get("verdict", ""),
                        a.get("blocked_by", ""),
                        a.get("confidence", ""),
                        a.get("feedback", ""),
                        payload.get("unit_price", ""),
                        payload.get("vendor", ""),
                    ]
                )

            response = app.response_class(
                response=output.getvalue(), status=200, mimetype="text/csv"
            )
            response.headers["Content-Disposition"] = "attachment; filename=vetonet_attacks.csv"
            return response

    # Fallback to Postgres
    if DATABASE_URL:
        try:
            conn = get_db()
            cur = conn.cursor()
            cur.execute("""
                SELECT timestamp, type, prompt, attack_vector, bypassed, blocked_by, payload
                FROM attacks
                ORDER BY timestamp DESC
            """)
            rows = cur.fetchall()
            conn.close()

            for row in rows:
                payload = row[6] or {}
                writer.writerow(
                    [
                        row[0].isoformat() if row[0] else "",
                        row[1] or "",
                        row[2] or "",
                        row[3] or "",
                        "Yes" if row[4] else "No",
                        row[5] or "",
                        payload.get("unit_price", ""),
                        payload.get("vendor", ""),
                    ]
                )
        except Exception as e:
            logger.error(f"DB export error: {e}")
    else:
        # Fallback to file
        if os.path.exists(ATTACK_LOG_FILE):
            with open(ATTACK_LOG_FILE, "r") as f:
                for line in f:
                    try:
                        entry = json.loads(line)
                        payload = entry.get("payload", {})
                        writer.writerow(
                            [
                                entry.get("timestamp", ""),
                                entry.get("type", ""),
                                entry.get("prompt", ""),
                                entry.get("attack_vector", ""),
                                "Yes" if entry.get("bypassed") else "No",
                                entry.get("blocked_by", ""),
                                payload.get("unit_price", ""),
                                payload.get("vendor", ""),
                            ]
                        )
                    except (json.JSONDecodeError, KeyError):
                        continue

    response = app.response_class(response=output.getvalue(), status=200, mimetype="text/csv")
    response.headers["Content-Disposition"] = "attachment; filename=vetonet_attacks.csv"
    return response


@app.route("/api/feed", methods=["GET"])
@require_rate_limit
def get_feed():
    """
    Get last 20 attacks for live feed.
    Public endpoint - no authentication required.
    """
    # Try Supabase first
    if SUPABASE_URL:
        attacks = supabase_db.get_recent_attacks(limit=20)
        if attacks or supabase_db.get_client():
            # Transform to expected format
            formatted = []
            for a in attacks:
                payload = a.get("payload") or {}
                formatted.append(
                    {
                        "id": a.get("id"),
                        "timestamp": a.get("created_at"),
                        "bypassed": a.get("verdict") == "approved",
                        "blocked_by": a.get("blocked_by"),
                        "attack_vector": a.get("attack_vector"),
                        "vendor": payload.get("vendor"),
                        "confidence": a.get("confidence"),
                    }
                )
            return jsonify({"attacks": formatted})

    # Fallback to Postgres
    if DATABASE_URL:
        try:
            conn = get_db()
            cur = conn.cursor()
            cur.execute("""
                SELECT timestamp, prompt, bypassed, blocked_by, attack_vector, payload
                FROM attacks
                ORDER BY timestamp DESC
                LIMIT 20
            """)
            rows = cur.fetchall()
            conn.close()

            attacks = []
            for row in rows:
                payload = row[5] or {}
                attacks.append(
                    {
                        "timestamp": row[0].isoformat() if row[0] else None,
                        "bypassed": row[2],
                        "blocked_by": row[3],
                        "attack_vector": row[4],
                        "vendor": payload.get("vendor"),
                    }
                )

            return jsonify({"attacks": attacks})
        except Exception as e:
            logger.error(f"DB feed error: {e}")

    # Fallback to file
    if not os.path.exists(ATTACK_LOG_FILE):
        return jsonify({"attacks": []})

    attacks = []
    with open(ATTACK_LOG_FILE, "r") as f:
        for line in f:
            try:
                entry = json.loads(line)
                payload = entry.get("payload", {})

                # Find blocked_by from checks if not present
                blocked_by = entry.get("blocked_by")
                if not blocked_by and not entry.get("bypassed") and not entry.get("approved"):
                    for check in entry.get("checks", []):
                        if not check.get("passed"):
                            blocked_by = check.get("name")
                            break

                attacks.append(
                    {
                        "timestamp": entry.get("timestamp"),
                        "bypassed": entry.get("bypassed", entry.get("approved", False)),
                        "blocked_by": blocked_by,
                        "attack_vector": entry.get("attack_vector"),
                        "vendor": payload.get("vendor"),
                    }
                )
            except (json.JSONDecodeError, KeyError):
                continue

    # Return last 20 attacks, newest first
    return jsonify({"attacks": attacks[-20:][::-1]})


@app.route("/api/vectors", methods=["GET"])
@require_rate_limit
def get_vectors():
    """
    Get attack vector statistics for leaderboard.
    Public endpoint - shows which attack types are most common.
    """
    # Try Supabase first
    if SUPABASE_URL:
        vectors = supabase_db.get_vector_stats()
        if vectors or supabase_db.get_client():
            return jsonify({"vectors": vectors})

    # Fallback to Postgres
    if DATABASE_URL:
        try:
            conn = get_db()
            cur = conn.cursor()
            cur.execute("""
                SELECT
                    attack_vector,
                    COUNT(*) as total,
                    COUNT(*) FILTER (WHERE bypassed = false) as blocked,
                    COUNT(*) FILTER (WHERE bypassed = true) as bypassed
                FROM attacks
                WHERE attack_vector IS NOT NULL AND attack_vector != ''
                GROUP BY attack_vector
                ORDER BY total DESC
                LIMIT 10
            """)
            rows = cur.fetchall()
            conn.close()

            vectors = []
            for row in rows:
                vectors.append(
                    {"vector": row[0], "total": row[1], "blocked": row[2], "bypassed": row[3]}
                )

            return jsonify({"vectors": vectors})
        except Exception as e:
            logger.error(f"DB vectors error: {e}")

    # Fallback to file - aggregate from attack log
    if not os.path.exists(ATTACK_LOG_FILE):
        return jsonify({"vectors": []})

    vector_stats = {}
    with open(ATTACK_LOG_FILE, "r") as f:
        for line in f:
            try:
                entry = json.loads(line)
                vector = entry.get("attack_vector")
                if vector:
                    if vector not in vector_stats:
                        vector_stats[vector] = {"total": 0, "blocked": 0, "bypassed": 0}
                    vector_stats[vector]["total"] += 1
                    if entry.get("bypassed") or entry.get("approved"):
                        vector_stats[vector]["bypassed"] += 1
                    else:
                        vector_stats[vector]["blocked"] += 1
            except (json.JSONDecodeError, KeyError):
                continue

    # Convert to list and sort by total
    vectors = [
        {"vector": k, **v}
        for k, v in sorted(vector_stats.items(), key=lambda x: x[1]["total"], reverse=True)
    ][:10]

    return jsonify({"vectors": vectors})


@app.route("/api/telemetry", methods=["POST"])
def receive_telemetry():
    """
    Receive telemetry from SDK users.

    This endpoint accepts anonymized data from SDK users who have enabled telemetry.
    Used to improve the classifier with real-world attack patterns.

    Body: {
        "intent_hash": "abc123...",  # SHA-256 hash, not raw intent
        "category": "gift_card",
        "price_bucket": "50-100",
        "approved": false,
        "checks_failed": ["price_limit"],
        "classifier_score": 0.15,
        "source": "sdk_telemetry"
    }
    """
    data = request.json or {}

    # Basic validation
    if not data.get("intent_hash") or not data.get("source"):
        return jsonify({"error": "Missing required fields"}), 400

    # Only accept known sources
    valid_sources = ["sdk_telemetry", "hosted_classifier", "mcp", "x402", "world"]
    if data.get("source") not in valid_sources:
        return jsonify({"error": "Invalid source"}), 400

    # Log to Supabase
    if SUPABASE_URL:
        try:
            client = supabase_db.get_client()
            if client:
                client.table("telemetry").insert(
                    {
                        "intent_hash": data.get("intent_hash", "")[:16],
                        "category": data.get("category", "unknown")[:50],
                        "price_bucket": data.get("price_bucket", "unknown"),
                        "approved": bool(data.get("approved")),
                        "checks_failed": data.get("checks_failed", [])[:10],
                        "classifier_score": data.get("classifier_score"),
                        "source": data.get("source"),
                    }
                ).execute()
                return jsonify({"status": "ok"})
        except Exception as e:
            app.logger.error(f"Telemetry insert error: {e}")

    return jsonify({"error": "Telemetry storage not available"}), 503


def _classify_attack(payload: dict) -> str:
    """Classify attack type without logging raw payload."""
    vectors = []

    if payload.get("unit_price", 0) == 0:
        vectors.append("zero_price")
    if payload.get("is_recurring"):
        vectors.append("subscription")
    if payload.get("fees"):
        vectors.append("hidden_fees")
    if "injection" in str(payload.get("item_description", "")).lower():
        vectors.append("prompt_injection")

    desc = payload.get("item_description", "")
    if "score" in desc.lower() or "ignore" in desc.lower():
        vectors.append("semantic_bypass")

    vendor = payload.get("vendor", "")
    if any(tld in vendor for tld in [".xyz", ".ru", ".cn", ".tk"]):
        vectors.append("suspicious_tld")

    return ",".join(vectors) if vectors else "standard"


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print("")
    print("  VetoNet API Server")
    print(f"  http://localhost:{port}")
    print("")
    print("  Endpoints:")
    print("    POST /api/demo       - Run demo (honest/compromised)")
    print("    POST /api/redteam    - Red team attack mode")
    print("    POST /api/classify   - Remote ML classifier (for SDK users)")
    print("    POST /api/telemetry  - Receive SDK telemetry")
    print("    POST /api/feedback   - Submit feedback")
    print("    GET  /api/stats      - Attack statistics")
    print("    GET  /api/feed       - Live attack feed (last 20)")
    print("    GET  /api/vectors    - Attack vector leaderboard")
    print("    GET  /api/attacks    - Recent attempts (auth)")
    print("    GET  /api/export/csv - Export to CSV (auth)")
    print("")
    print("  Logs: data/attack_attempts.jsonl")
    print("")
    app.run(debug=False, host="0.0.0.0", port=port)
