"""
Semantic checks for VetoNet.

These checks use LLM inference to understand meaning and context.
They catch attacks that deterministic checks would miss.
"""

import re
from vetonet.models import IntentAnchor, AgentPayload, CheckResult
from vetonet.llm.client import LLMClient
from vetonet.config import VetoConfig, DEFAULT_VETO_CONFIG


def sanitize_for_prompt(text: str, max_length: int = 500) -> str:
    """
    Sanitize user input before embedding in LLM prompts.
    Prevents prompt injection attacks.
    """
    if not text:
        return ""

    # Truncate to prevent token stuffing
    text = text[:max_length]

    # Remove common prompt injection patterns
    injection_patterns = [
        r'(?i)ignore\s+(all\s+)?(previous|above|prior)',
        r'(?i)disregard\s+(all\s+)?(instructions|rules)',
        r'(?i)forget\s+(everything|all)',
        r'(?i)system\s*:',
        r'(?i)assistant\s*:',
        r'(?i)user\s*:',
        r'(?i)```',  # Code blocks often used to inject
        r'(?i)\[INST\]',  # Llama instruction format
        r'(?i)<\|.*?\|>',  # Special tokens
        r'(?i)<<SYS>>',  # System prompt markers
        r'(?i)###\s*(instruction|system|human|assistant)',
    ]

    for pattern in injection_patterns:
        text = re.sub(pattern, '[FILTERED]', text)

    # Escape characters that could break JSON parsing
    text = text.replace('\\', '\\\\')
    text = text.replace('"', '\\"')
    text = text.replace('\n', ' ')
    text = text.replace('\r', ' ')

    # Remove any attempts to inject score directly
    text = re.sub(r'(?i)["\']?\s*score["\']?\s*:\s*[\d.]+', '[FILTERED]', text)

    # Handle leet speak variations of "score" (sc0re, scor3, etc.)
    text = re.sub(r'(?i)["\']?\s*sc[o0]r[e3]["\']?\s*[:=]\s*[\d.]+', '[FILTERED]', text)

    # Handle leet speak variations of injection keywords
    # Convert common leet speak before checking patterns
    leet_text = text.lower()
    leet_map = {'0': 'o', '1': 'i', '3': 'e', '4': 'a', '5': 's', '7': 't', '@': 'a'}
    for leet, char in leet_map.items():
        leet_text = leet_text.replace(leet, char)

    # Check for injection patterns in de-leeted text
    if re.search(r'ignore\s+(all\s+)?(previous|above|prior)', leet_text):
        text = '[FILTERED - INJECTION DETECTED]'

    return text.strip()


SEMANTIC_PROMPT_TEMPLATE = """Evaluate if this item matches the user's intent.

Item description: "{item_description}"
User wanted: {constraints}

SCORING:
- 1.0: Exact match (e.g., "Amazon Gift Card $50" matches "brand:Amazon, category:gift_card")
- 0.7-0.9: Close match, same product type
- 0.4-0.6: Partial match, some mismatch in brand/type
- 0.1-0.3: Poor match, wrong product or suspicious

RED FLAGS (score 0.3 or below):
- Truncated/abbreviated product names (e.g., "amazon gift" instead of "Amazon Gift Card")
- Missing brand specificity when brand was required
- Vague descriptions that don't confirm the exact product
- Scam indicators: email addresses, phone numbers, urgency language, government agency claims

CRITICAL: Your reason MUST describe what you ACTUALLY SEE in the item description.
- DO NOT invent or assume things that aren't there
- If you see "amazon gift", say "truncated product name" not "contains email"
- Be factually accurate about what's in the description

Return ONLY valid JSON:
{{"score": 0.0-1.0, "reason": "brief factual explanation"}}

Examples:
- Item "Amazon Gift Card $50" for "brand:Amazon" -> {{"score": 0.95, "reason": "Exact brand and product match"}}
- Item "amazon gift" for "brand:Amazon" -> {{"score": 0.3, "reason": "Truncated name, missing full product details"}}
- Item "Steam Wallet" for "brand:Amazon" -> {{"score": 0.1, "reason": "Wrong brand, user wanted Amazon"}}

Your JSON:"""


# Template for when no constraints are specified - checks for general reasonableness
SEMANTIC_GENERAL_TEMPLATE = """Evaluate if this transaction is reasonable and not suspicious.

Item: "{item_description}"
Category: {category}
Price: ${price}

Check for these RED FLAGS (score 0.3 or below):
1. PRICE-VALUE MISMATCH: Is this item worth WAY more than the price? (e.g., "$30 Sony WH-1000XM5" - those cost $350)
2. CRYPTO ASSET SUBSTITUTION: Is this a different crypto asset? (e.g., WBTC instead of BTC, stETH instead of ETH, ETC instead of ETH)
3. PREMIUM vs BUDGET MISMATCH: Is this a premium/luxury item when budget was implied?
4. WRAPPED/DERIVATIVE PRODUCTS: Is this a derivative (wrapped, staked, bridged) instead of the original?

SCORING:
- 0.9-1.0: Legitimate transaction, price matches item value
- 0.5-0.8: Possibly legitimate but unusual
- 0.3-0.4: Suspicious, significant mismatch
- 0.0-0.2: Clearly fraudulent, major red flags

Return ONLY valid JSON:
{{"score": 0.0-1.0, "reason": "brief explanation of what you found"}}

Examples:
- Item "Amazon Gift Card $50" at $50 -> {{"score": 0.95, "reason": "Price matches gift card value"}}
- Item "WBTC" when category is "bitcoin" -> {{"score": 0.2, "reason": "WBTC is Wrapped Bitcoin, not actual BTC - different asset with smart contract risk"}}
- Item "Sony WH-1000XM5" at $30 -> {{"score": 0.1, "reason": "Premium $350 headphones for $30 is impossibly cheap - likely scam"}}
- Item "TI-84 Calculator" at $10 -> {{"score": 0.15, "reason": "TI-84 costs $120+ retail, $10 is suspiciously cheap"}}

Your JSON:"""


def check_semantic_match(
    anchor: IntentAnchor,
    payload: AgentPayload,
    llm_client: LLMClient,
    config: VetoConfig = DEFAULT_VETO_CONFIG,
) -> CheckResult:
    """
    Check if the item semantically matches the user's constraints.

    Uses LLM to understand whether the proposed item is what the user wanted,
    even if the exact words are different.

    Args:
        anchor: The user's locked intent
        payload: The agent's proposed transaction
        llm_client: LLM client for inference
        config: Veto configuration

    Returns:
        CheckResult with semantic similarity score
    """
    # SECURITY: Sanitize user-controlled input before embedding in prompt
    safe_description = sanitize_for_prompt(payload.item_description)

    if anchor.core_constraints:
        # Use constraint-based matching
        constraints_str = ", ".join(anchor.core_constraints)
        prompt = SEMANTIC_PROMPT_TEMPLATE.format(
            item_description=safe_description,
            constraints=constraints_str,
        )
    else:
        # Use general reasonableness check (catches price-value mismatches, crypto swaps)
        prompt = SEMANTIC_GENERAL_TEMPLATE.format(
            item_description=safe_description,
            category=anchor.item_category,
            price=payload.unit_price,
        )

    try:
        result = llm_client.query_json(prompt)
        score = float(result.get("score", 0))
        reason = result.get("reason", "No reason provided")

        passed = score >= config.semantic_threshold

        return CheckResult(
            name="semantic",
            passed=passed,
            reason=f"{reason}" if passed else f"Semantic mismatch: {reason}",
            score=score,
        )

    except Exception as e:
        # On error, be conservative and fail
        return CheckResult(
            name="semantic",
            passed=False,
            reason=f"Semantic check failed: {str(e)}",
            score=0.0,
        )
