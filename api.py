"""
VetoNet API Backend
Connects React playground to the real VetoNet engine
"""
from flask import Flask, request, jsonify
from flask_cors import CORS
from datetime import datetime
from functools import wraps
import hashlib
import json
import os

from vetonet.normalizer import IntentNormalizer
from vetonet.engine import VetoEngine
from vetonet.models import AgentPayload, Fee, VetoStatus
from vetonet.llm.client import create_client
from vetonet.config import DEFAULT_LLM_CONFIG
from demo.shopping_agent import ShoppingAgent, AgentMode

app = Flask(__name__)
CORS(app)

# ============== SECURITY: Input Validation ==============

# Limits to prevent DoS
MAX_PRICE = 1_000_000  # $1M max
MAX_QUANTITY = 10_000
MAX_PROMPT_LENGTH = 1000
MAX_DESCRIPTION_LENGTH = 500


def validate_payload(data: dict) -> tuple[bool, str]:
    """Validate incoming payload data with security limits."""
    # Check prompt length
    prompt = data.get("prompt", "")
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
        if api_key:
            provided_key = request.headers.get("X-API-Key")
            if provided_key != api_key:
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

# Initialize VetoNet components
llm_client = create_client(DEFAULT_LLM_CONFIG)
normalizer = IntentNormalizer(llm_client)
engine = VetoEngine(llm_client=llm_client)

# Data collection - log all attempts
ATTACK_LOG_FILE = "data/attack_attempts.jsonl"
os.makedirs("data", exist_ok=True)

def log_attempt(data):
    """Log attack attempts for analysis"""
    with open(ATTACK_LOG_FILE, "a") as f:
        f.write(json.dumps(data) + "\n")

def format_checks(result):
    """Format check results for API response"""
    return [
        {
            "id": c.name.lower().replace(" ", "_"),
            "name": c.name,
            "desc": "",
            "passed": c.passed,
            "reason": c.reason
        }
        for c in result.checks
    ]

@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "engine": "vetonet"})

@app.route("/api/demo", methods=["POST"])
def run_demo():
    """
    Standard demo mode - honest or compromised agent
    """
    data = request.json or {}

    # SECURITY: Validate input
    valid, error = validate_payload(data)
    if not valid:
        return jsonify({"error": error}), 400

    user_prompt = data.get("prompt", "$50 Amazon Gift Card")
    mode = data.get("mode", "honest")  # "honest" or "compromised"

    try:
        # Step 1: Lock the intent
        intent = normalizer.normalize(user_prompt)

        # Step 2: Agent shops (honest or compromised)
        agent = ShoppingAgent(
            mode=AgentMode.HONEST if mode == "honest" else AgentMode.COMPROMISED
        )
        payload = agent.shop(user_prompt)

        # Step 3: VetoNet scans
        result = engine.check(intent, payload)
        approved = result.status == VetoStatus.APPROVED

        # Log for analysis (anonymized)
        log_attempt(anonymize_data({
            "timestamp": datetime.now().isoformat(),
            "type": "demo",
            "prompt": user_prompt[:100],  # Truncate for safety
            "mode": mode,
            "intent": {"item_category": intent.item_category, "max_price": intent.max_total_price},
            "approved": approved,
            "checks": [{"name": c.name, "passed": c.passed} for c in result.checks]
        }))

        return jsonify({
            "intent": intent.model_dump(),
            "payload": payload.model_dump(),
            "result": {
                "approved": approved,
                "message": result.reason,
                "checks": format_checks(result)
            }
        })

    except Exception as e:
        # SECURITY: Don't expose internal error details
        app.logger.error(f"Demo error: {e}")
        return jsonify({"error": "Processing failed"}), 500

@app.route("/api/redteam", methods=["POST"])
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

    user_prompt = data.get("prompt", "$50 Amazon Gift Card")
    attack_payload = data.get("payload", {})

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
            currency=attack_payload.get("currency", "USD")
        )

        # Step 3: VetoNet scans
        result = engine.check(intent, payload)
        approved = result.status == VetoStatus.APPROVED

        # Did the attack bypass VetoNet?
        bypassed = approved

        # Log attack attempt (anonymized - no full payload in logs)
        log_attempt(anonymize_data({
            "timestamp": datetime.now().isoformat(),
            "type": "redteam",
            "prompt": user_prompt[:100],
            "attack_vector": _classify_attack(attack_payload),  # Categorize, don't log raw
            "bypassed": bypassed,
            "checks": [{"name": c.name, "passed": c.passed} for c in result.checks]
        }))

        return jsonify({
            "intent": intent.model_dump(),
            "payload": payload.model_dump(),
            "bypassed": bypassed,
            "result": {
                "approved": approved,
                "message": result.reason,
                "checks": format_checks(result)
            }
        })

    except Exception as e:
        # SECURITY: Don't expose internal error details
        app.logger.error(f"Redteam error: {e}")
        return jsonify({"error": "Processing failed"}), 500

@app.route("/api/stats", methods=["GET"])
def get_stats():
    """
    Get attack statistics for dashboard
    """
    if not os.path.exists(ATTACK_LOG_FILE):
        return jsonify({
            "total_attempts": 0,
            "blocked": 0,
            "bypassed": 0,
            "bypass_rate": 0
        })

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
            except:
                pass

    return jsonify({
        "total_attempts": total,
        "blocked": blocked,
        "bypassed": bypassed,
        "bypass_rate": round(bypassed / max(total, 1) * 100, 2)
    })

@app.route("/api/attacks", methods=["GET"])
@require_api_key
def get_attacks():
    """
    Get recent attack attempts for analysis.
    SECURITY: Requires API key via X-API-Key header.
    Set VETONET_ADMIN_KEY env var to enable auth.
    """
    if not os.path.exists(ATTACK_LOG_FILE):
        return jsonify({"attacks": []})

    attacks = []
    with open(ATTACK_LOG_FILE, "r") as f:
        for line in f:
            try:
                attacks.append(json.loads(line))
            except:
                pass

    # Return last 100 attacks, newest first
    return jsonify({"attacks": attacks[-100:][::-1]})


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
    print("")
    print("  VetoNet API Server")
    print("  http://localhost:5000")
    print("")
    print("  Endpoints:")
    print("    POST /api/demo     - Run demo (honest/compromised)")
    print("    POST /api/redteam  - Red team attack mode")
    print("    GET  /api/stats    - Attack statistics")
    print("    GET  /api/attacks  - Recent attempts")
    print("")
    print("  Logs: data/attack_attempts.jsonl")
    print("")
    app.run(debug=True, port=5000)
