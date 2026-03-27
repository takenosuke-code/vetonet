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
from vetonet.config import LLMConfig
from demo.shopping_agent import ShoppingAgent, AgentMode

app = Flask(__name__)
CORS(app)

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
    print(f"  LLM: Groq (llama-3.1-8b-instant)")
else:
    # Try Ollama locally, or run without LLM
    try:
        from vetonet.config import DEFAULT_LLM_CONFIG
        llm_client = create_client(DEFAULT_LLM_CONFIG)
        normalizer = IntentNormalizer(llm_client)
        engine = VetoEngine(llm_client=llm_client)
        print(f"  LLM: Ollama (local)")
    except Exception as e:
        print(f"  Warning: No LLM available ({e}). Semantic checks disabled.")
        llm_client = None
        normalizer = None
        engine = VetoEngine(llm_client=None)

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

# ============== Database Setup ==============
DATABASE_URL = os.environ.get("DATABASE_URL")

def get_db():
    """Get database connection."""
    if not DATABASE_URL:
        return None
    import psycopg2
    return psycopg2.connect(DATABASE_URL)

def init_db():
    """Create tables if they don't exist."""
    if not DATABASE_URL:
        print("  Database: None (using file fallback)")
        return

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
    print("  Database: PostgreSQL (connected)")

# Initialize database on startup
try:
    init_db()
except Exception as e:
    print(f"  Database: Failed ({e})")

# Data collection - log all attempts
ATTACK_LOG_FILE = "data/attack_attempts.jsonl"
os.makedirs("data", exist_ok=True)

def log_attempt(data):
    """Log attack attempts to database (or file fallback)."""
    if DATABASE_URL:
        try:
            conn = get_db()
            cur = conn.cursor()

            # Find which check blocked it
            blocked_by = None
            if not data.get("bypassed") and not data.get("approved"):
                for check in data.get("checks", []):
                    if not check.get("passed"):
                        blocked_by = check.get("name")
                        break

            cur.execute("""
                INSERT INTO attacks (type, prompt, attack_vector, bypassed, blocked_by, checks, payload)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (
                data.get("type"),
                data.get("prompt"),
                data.get("attack_vector"),
                data.get("bypassed", data.get("approved", False)),
                blocked_by,
                json.dumps(data.get("checks", [])),
                json.dumps(data.get("payload", {})),
            ))
            conn.commit()
            conn.close()
            return
        except Exception as e:
            print(f"DB Error: {e}")

    # Fallback to file
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

    # Check if LLM is available
    if normalizer is None:
        return jsonify({"error": "LLM not configured. Set GROQ_API_KEY environment variable."}), 503

    try:
        # Step 1: Lock the intent
        intent = normalizer.normalize(user_prompt)

        # Step 2: Agent shops (honest or compromised)
        agent = ShoppingAgent(
            mode=AgentMode.HONEST if mode == "honest" else AgentMode.COMPROMISED
        )
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

        # Log for analysis (anonymized)
        log_attempt(anonymize_data({
            "timestamp": datetime.now().isoformat(),
            "type": "demo",
            "prompt": user_prompt[:100],  # Truncate for safety
            "mode": mode,
            "intent": {"item_category": intent.item_category, "max_price": intent.max_price},
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
    # Try Postgres first
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

            return jsonify({
                "total_attempts": total,
                "blocked": blocked,
                "bypassed": bypassed,
                "bypass_rate": round(bypassed / max(total, 1) * 100, 2)
            })
        except Exception as e:
            print(f"DB stats error: {e}")

    # Fallback to file
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
                attacks.append({
                    "timestamp": row[0].isoformat() if row[0] else None,
                    "type": row[1],
                    "prompt": row[2],
                    "attack_vector": row[3],
                    "bypassed": row[4],
                    "blocked_by": row[5],
                    "checks": row[6],
                    "payload": row[7],
                })

            return jsonify({"attacks": attacks})
        except Exception as e:
            print(f"DB attacks error: {e}")

    # Fallback to file
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

    # Header row
    writer.writerow([
        "Timestamp", "Type", "Prompt", "Attack Vector",
        "Bypassed", "Blocked By", "Unit Price", "Vendor"
    ])

    # Try Postgres first
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
                writer.writerow([
                    row[0].isoformat() if row[0] else "",
                    row[1] or "",
                    row[2] or "",
                    row[3] or "",
                    "Yes" if row[4] else "No",
                    row[5] or "",
                    payload.get("unit_price", ""),
                    payload.get("vendor", ""),
                ])
        except Exception as e:
            print(f"DB export error: {e}")
    else:
        # Fallback to file
        if os.path.exists(ATTACK_LOG_FILE):
            with open(ATTACK_LOG_FILE, "r") as f:
                for line in f:
                    try:
                        entry = json.loads(line)
                        payload = entry.get("payload", {})
                        writer.writerow([
                            entry.get("timestamp", ""),
                            entry.get("type", ""),
                            entry.get("prompt", ""),
                            entry.get("attack_vector", ""),
                            "Yes" if entry.get("bypassed") else "No",
                            entry.get("blocked_by", ""),
                            payload.get("unit_price", ""),
                            payload.get("vendor", ""),
                        ])
                    except:
                        pass

    response = app.response_class(
        response=output.getvalue(),
        status=200,
        mimetype='text/csv'
    )
    response.headers["Content-Disposition"] = "attachment; filename=vetonet_attacks.csv"
    return response


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
    print("    GET  /api/stats      - Attack statistics")
    print("    GET  /api/attacks    - Recent attempts (auth)")
    print("    GET  /api/export/csv - Export to CSV (auth)")
    print("")
    print("  Logs: data/attack_attempts.jsonl")
    print("")
    app.run(debug=True, host="0.0.0.0", port=port)
