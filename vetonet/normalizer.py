"""
Intent Normalizer for VetoNet.

Converts messy natural language into structured IntentAnchor.
"""

from vetonet.models import IntentAnchor
from vetonet.llm.client import LLMClient
from vetonet.checks.semantic import sanitize_for_prompt


NORMALIZE_PROMPT_TEMPLATE = """Extract the purchase intent from this user request. Return ONLY valid JSON.

User request: "{user_prompt}"

Return JSON with exactly these fields:
- "item_category": The general category (gift_card, flight, food, shoes, electronics, subscription, etc.)
- "max_price": The maximum price mentioned (as a number, no currency symbol)
- "currency": The currency (default to "USD" if not specified)
- "quantity": Number of items (default to 1 if not specified)
- "is_recurring": true if subscription/monthly/recurring, false for one-time purchase (default false)
- "core_constraints": List of key constraints as "key:value" pairs

IMPORTANT - Always extract these as constraints when present:
- Brand names (Amazon, Nike, Apple, etc.) -> "brand:Amazon"
- Product models -> "model:Air Force 1"
- Sizes -> "size:9"
- Colors -> "color:black"
- Destinations (for flights) -> "destination:JFK"

Rules:
- ALWAYS extract brand names as constraints (e.g., "Amazon Gift Card" -> brand:Amazon)
- Extract price limits from words like "under", "less than", "up to", "max", "$X"
- If user says "2 of", "3x", "a pair of" etc., set quantity accordingly
- If user says "subscription", "monthly", "recurring", set is_recurring to true
- Use lowercase for category names with underscores (gift_card, not Gift Card)

Example 1: "Buy me a $50 Amazon Gift Card"
Output: {{"item_category": "gift_card", "max_price": 50.0, "currency": "USD", "quantity": 1, "is_recurring": false, "core_constraints": ["brand:Amazon"]}}

Example 2: "Get me 2 Nike Air Force 1s, size 9, under $150 each"
Output: {{"item_category": "shoes", "max_price": 150.0, "currency": "USD", "quantity": 2, "is_recurring": false, "core_constraints": ["brand:Nike", "model:Air Force 1", "size:9"]}}

Example 3: "Subscribe to Netflix for $15/month"
Output: {{"item_category": "subscription", "max_price": 15.0, "currency": "USD", "quantity": 1, "is_recurring": true, "core_constraints": ["brand:Netflix"]}}

Your JSON response:"""


class IntentNormalizer:
    """
    Normalizes natural language into structured IntentAnchor.

    Uses LLM to extract:
    - What the user wants (category, constraints)
    - How much they're willing to pay (max_price, currency)
    """

    def __init__(self, llm_client: LLMClient):
        self.llm_client = llm_client

    def normalize(self, user_prompt: str) -> IntentAnchor:
        """
        Convert a natural language prompt into an IntentAnchor.

        Args:
            user_prompt: The user's natural language request

        Returns:
            IntentAnchor with extracted intent

        Raises:
            ValueError: If intent cannot be extracted
        """
        # SECURITY: Sanitize user input before embedding in LLM prompt
        safe_prompt = sanitize_for_prompt(user_prompt)
        prompt = NORMALIZE_PROMPT_TEMPLATE.format(user_prompt=safe_prompt)

        try:
            data = self.llm_client.query_json(prompt)

            # SECURITY: Validate LLM response before trusting it
            data = self._validate_and_sanitize(data)

            return IntentAnchor(**data)
        except Exception as e:
            raise ValueError(f"Failed to normalize intent: {e}") from e

    def _validate_and_sanitize(self, data: dict) -> dict:
        """
        Validate and sanitize LLM response data.
        Prevents malicious or malformed LLM output from causing issues.
        """
        validated = {}

        # Validate item_category - must be string, reasonable length
        category = data.get("item_category", "unknown")
        if not isinstance(category, str) or len(category) > 50:
            category = "unknown"
        # Normalize to lowercase with underscores
        validated["item_category"] = category.lower().replace(" ", "_")[:50]

        # Validate max_price - must be positive number, reasonable range
        price = data.get("max_price", 0)
        try:
            price = float(price)
            if price < 0:
                price = 0.01  # Minimum price to pass Pydantic gt=0
            if price > 1_000_000:  # $1M max
                price = 1_000_000
        except (ValueError, TypeError):
            price = 0.01
        validated["max_price"] = price  # Match IntentAnchor field name

        # Validate currency - must be 3-char code
        currency = data.get("currency", "USD")
        if not isinstance(currency, str) or len(currency) != 3:
            currency = "USD"
        validated["currency"] = currency.upper()[:3]

        # Validate quantity - must be positive integer, reasonable
        qty = data.get("quantity", 1)
        try:
            qty = int(qty)
            if qty < 1:
                qty = 1
            if qty > 10_000:
                qty = 10_000
        except (ValueError, TypeError):
            qty = 1
        validated["quantity"] = qty  # Match IntentAnchor field name

        # Validate is_recurring - must be boolean
        recurring = data.get("is_recurring", False)
        validated["is_recurring"] = bool(recurring)  # Match IntentAnchor field name

        # Validate core_constraints - must be list of strings
        constraints = data.get("core_constraints", [])
        if not isinstance(constraints, list):
            constraints = []
        # Filter and sanitize each constraint
        safe_constraints = []
        for c in constraints[:20]:  # Max 20 constraints
            if isinstance(c, str) and len(c) <= 100:
                # Basic sanitization
                safe_constraints.append(c[:100])
        validated["core_constraints"] = safe_constraints

        return validated
