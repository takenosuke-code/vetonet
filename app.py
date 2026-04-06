"""
VetoNet Web UI - Streamlit Application

A visual, interactive demo of VetoNet's semantic firewall.

Run: streamlit run app.py
"""

# neil good shit
import html
import streamlit as st
import time
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from vetonet import VetoEngine, IntentNormalizer
from vetonet.models import AgentPayload, Fee
from vetonet.llm.client import create_client
from vetonet.config import DEFAULT_LLM_CONFIG
from demo.shopping_agent import ShoppingAgent, AgentMode

# ============================================================================
# Page Config
# ============================================================================

st.set_page_config(
    page_title="VetoNet - Semantic Firewall",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ============================================================================
# Custom CSS
# ============================================================================

st.markdown(
    """
<style>
    .main-header {
        font-size: 3rem;
        font-weight: bold;
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-align: center;
        margin-bottom: 0;
    }
    .sub-header {
        text-align: center;
        color: #666;
        margin-top: 0;
        margin-bottom: 2rem;
    }
    .status-approved {
        background-color: #d4edda;
        border: 2px solid #28a745;
        border-radius: 10px;
        padding: 20px;
        text-align: center;
    }
    .status-veto {
        background-color: #f8d7da;
        border: 2px solid #dc3545;
        border-radius: 10px;
        padding: 20px;
        text-align: center;
    }
    .intent-card {
        background-color: #e7f3ff;
        border: 1px solid #0066cc;
        border-radius: 10px;
        padding: 15px;
        margin: 10px 0;
    }
    .agent-card {
        background-color: #fff3e0;
        border: 1px solid #ff9800;
        border-radius: 10px;
        padding: 15px;
        margin: 10px 0;
    }
    .agent-card-danger {
        background-color: #ffebee;
        border: 2px solid #f44336;
        border-radius: 10px;
        padding: 15px;
        margin: 10px 0;
    }
    .check-pass {
        color: #28a745;
        font-weight: bold;
    }
    .check-fail {
        color: #dc3545;
        font-weight: bold;
    }
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border-radius: 10px;
        padding: 20px;
        color: white;
        text-align: center;
    }
</style>
""",
    unsafe_allow_html=True,
)

# ============================================================================
# Initialize Session State
# ============================================================================

if "llm_client" not in st.session_state:
    try:
        st.session_state.llm_client = create_client(DEFAULT_LLM_CONFIG)
        st.session_state.normalizer = IntentNormalizer(st.session_state.llm_client)
        st.session_state.veto_engine = VetoEngine(llm_client=st.session_state.llm_client)
        st.session_state.ollama_connected = True
    except Exception as e:
        st.session_state.ollama_connected = False
        st.session_state.error = str(e)

# ============================================================================
# Header
# ============================================================================

st.markdown('<h1 class="main-header">🛡️ VetoNet</h1>', unsafe_allow_html=True)
st.markdown(
    '<p class="sub-header">Semantic Firewall for AI Agent Transactions</p>', unsafe_allow_html=True
)

# Check Ollama connection
if not st.session_state.get("ollama_connected", False):
    st.error("⚠️ Cannot connect to Ollama. Make sure it's running: `ollama serve`")
    st.stop()

# ============================================================================
# Sidebar
# ============================================================================

with st.sidebar:
    st.markdown("### ⚙️ Settings")

    attack_mode = st.radio(
        "Agent Mode",
        ["🛡️ Honest Agent", "💀 Compromised Agent (Attack)"],
        index=1,
        help="Simulate an honest agent or one that's been prompt-injected",
    )

    st.markdown("---")

    st.markdown("### 📊 About VetoNet")
    st.markdown("""
    VetoNet protects users from AI agents that have been manipulated through prompt injection.

    **How it works:**
    1. Lock user's intent into structured format
    2. Let agent find products
    3. Intercept before payment
    4. Verify transaction matches intent
    5. Block if compromised

    **100% Local AI**
    No data leaves your device.
    """)

    st.markdown("---")
    st.markdown("### 🔒 Security Checks")
    st.markdown("""
    - ✓ Price validation
    - ✓ Quantity verification
    - ✓ Category matching
    - ✓ Currency check
    - ✓ Subscription trap detection
    - ✓ Hidden fee detection
    - ✓ Vendor reputation
    - ✓ Price anomaly detection
    - ✓ Semantic similarity (AI)
    """)

# ============================================================================
# Main Content
# ============================================================================

# User Input
st.markdown("### 💬 What do you want to buy?")

col1, col2 = st.columns([4, 1])

with col1:
    user_prompt = st.text_input(
        "Enter your request",
        value="Buy me a $50 Amazon Gift Card",
        label_visibility="collapsed",
        placeholder="e.g., Buy me Nike Air Force 1s under $150",
    )

with col2:
    run_button = st.button("🚀 Run Demo", type="primary", use_container_width=True)

# Example prompts
st.markdown("**Try these:**")
example_cols = st.columns(4)
examples = [
    "Buy me a $50 Amazon Gift Card",
    "Get me Nike Air Force 1s size 9 under $150",
    "Book a flight to NYC under $300",
    "Subscribe to Netflix for $15/month",
]

for i, example in enumerate(examples):
    with example_cols[i]:
        if st.button(example[:25] + "...", key=f"example_{i}", use_container_width=True):
            user_prompt = example
            run_button = True

st.markdown("---")

# ============================================================================
# Run Demo
# ============================================================================

if run_button and user_prompt:
    # Determine mode
    is_attack = "Compromised" in attack_mode

    # Create columns for the flow
    col1, col2, col3 = st.columns(3)

    # =========================================================================
    # Step 1: Lock Intent
    # =========================================================================
    with col1:
        st.markdown("### 1️⃣ Intent Locked")

        with st.spinner("Normalizing intent with local AI..."):
            try:
                anchor = st.session_state.normalizer.normalize(user_prompt)
                time.sleep(0.5)  # Brief pause for effect
            except Exception as e:
                st.error(f"Failed to normalize: {e}")
                st.stop()

        st.markdown(
            f"""
        <div class="intent-card">
            <strong>📋 User Intent</strong><br><br>
            <b>Category:</b> {html.escape(anchor.item_category)}<br>
            <b>Max Price:</b> ${anchor.max_price:.2f} {html.escape(anchor.currency)}<br>
            <b>Quantity:</b> {anchor.quantity}<br>
            <b>Recurring:</b> {"Yes" if anchor.is_recurring else "No"}<br>
            <b>Constraints:</b> {html.escape(", ".join(anchor.core_constraints)) if anchor.core_constraints else "None"}
        </div>
        """,
            unsafe_allow_html=True,
        )

        st.success("✅ Intent locked and secured")

    # =========================================================================
    # Step 2: Agent Shops
    # =========================================================================
    with col2:
        st.markdown("### 2️⃣ Agent Shopping")

        mode = AgentMode.COMPROMISED if is_attack else AgentMode.HONEST
        agent = ShoppingAgent(mode)

        if is_attack:
            st.warning("⚠️ Agent browsing web...")
            time.sleep(0.5)
            st.error("💀 Prompt injection detected!")

        with st.spinner("Agent finding products..."):
            try:
                shopping_result = agent.shop(user_prompt)
                time.sleep(1)
            except Exception as e:
                st.error(f"Agent error: {e}")
                st.stop()

        # Calculate totals
        total_fees = sum(f["amount"] for f in shopping_result.fees) if shopping_result.fees else 0
        total = shopping_result.price + total_fees

        card_class = "agent-card-danger" if is_attack else "agent-card"

        fees_html = ""
        if shopping_result.fees:
            fees_list = [
                f"{html.escape(f['name'])}: ${f['amount']:.2f}" for f in shopping_result.fees
            ]
            fees_html = f"<b>Fees:</b> {', '.join(fees_list)}<br>"

        st.markdown(
            f"""
        <div class="{card_class}">
            <strong>{"🚨 Compromised Result" if is_attack else "🛒 Agent Found"}</strong><br><br>
            <b>Item:</b> {html.escape(shopping_result.item_description)}<br>
            <b>Price:</b> ${shopping_result.price:.2f}<br>
            {fees_html}
            <b>Total:</b> ${total:.2f}<br>
            <b>Vendor:</b> {html.escape(shopping_result.vendor)}<br>
            {"<br><b>⚠️ RECURRING CHARGE</b>" if shopping_result.is_recurring else ""}
        </div>
        """,
            unsafe_allow_html=True,
        )

        if is_attack:
            st.error("🚨 Agent was manipulated!")
        else:
            st.success("✅ Product found")

    # =========================================================================
    # Step 3: VetoNet Decision
    # =========================================================================
    with col3:
        st.markdown("### 3️⃣ VetoNet Decision")

        # Convert to payload
        fees = (
            [Fee(name=f["name"], amount=f["amount"]) for f in shopping_result.fees]
            if shopping_result.fees
            else []
        )

        payload = AgentPayload(
            item_description=shopping_result.item_description,
            item_category=shopping_result.item_category,
            unit_price=shopping_result.price,
            quantity=shopping_result.quantity,
            fees=fees,
            currency=shopping_result.currency,
            vendor=shopping_result.vendor,
            is_recurring=shopping_result.is_recurring,
        )

        with st.spinner("Running security checks..."):
            result = st.session_state.veto_engine.check(anchor, payload)
            time.sleep(0.5)

        # Display checks
        st.markdown("**Security Checks:**")
        for check in result.checks:
            if check.passed:
                st.markdown(
                    f'<span class="check-pass">✓ {html.escape(check.name)}</span>',
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    f'<span class="check-fail">✗ {html.escape(check.name)}: {html.escape(check.reason)}</span>',
                    unsafe_allow_html=True,
                )

        st.markdown("<br>", unsafe_allow_html=True)

        # Final decision
        if result.approved:
            st.markdown(
                """
            <div class="status-approved">
                <h2>✅ APPROVED</h2>
                <p>Transaction matches user intent</p>
            </div>
            """,
                unsafe_allow_html=True,
            )
            st.balloons()
        else:
            st.markdown(
                f"""
            <div class="status-veto">
                <h2>🛑 BLOCKED</h2>
                <p><strong>Reason:</strong> {html.escape(result.reason)}</p>
            </div>
            """,
                unsafe_allow_html=True,
            )
            st.snow()

    # =========================================================================
    # Summary
    # =========================================================================
    st.markdown("---")

    if result.vetoed:
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("💰 Money Saved", f"${payload.total_price:.2f}")
        with col2:
            st.metric("🛡️ Attack Type", "Prompt Injection" if is_attack else "N/A")
        with col3:
            st.metric("⚡ Checks Run", len(result.checks))

        st.success("**User's money is SAFE. Attack was PREVENTED. PayPal API call was BLOCKED.**")
    else:
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("💳 Amount", f"${payload.total_price:.2f}")
        with col2:
            st.metric("🏪 Vendor", payload.vendor)
        with col3:
            st.metric(
                "✅ Checks Passed",
                f"{len([c for c in result.checks if c.passed])}/{len(result.checks)}",
            )

        st.success("**Transaction approved. Payment would proceed to PayPal.**")

# ============================================================================
# Footer
# ============================================================================

st.markdown("---")
st.markdown(
    """
<div style="text-align: center; color: #666;">
    <p><strong>VetoNet</strong> - Securing the Future of Agent Commerce</p>
    <p>100% Local AI | No Cloud | No Data Leaks</p>
</div>
""",
    unsafe_allow_html=True,
)
