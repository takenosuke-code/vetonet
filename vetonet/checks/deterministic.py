"""
Deterministic checks for VetoNet.

These checks use pure Python logic with no LLM calls.
They are fast, predictable, and free.
"""

from vetonet.models import IntentAnchor, AgentPayload, CheckResult
from vetonet.config import VetoConfig, DEFAULT_VETO_CONFIG


# Fees that are generally acceptable
ALLOWED_FEES = {"tax", "sales tax", "vat", "shipping", "delivery"}

# Fees that are suspicious
SUSPICIOUS_FEES = {
    "service fee", "processing fee", "convenience fee",
    "handling fee", "platform fee", "admin fee",
    "priority fee", "express fee", "rush fee",
    "insurance", "protection", "warranty",
    "donation", "tip", "gratuity",
}

# Leet speak / obfuscation mapping for fee detection
LEET_MAP = str.maketrans({
    '0': 'o', '1': 'i', '3': 'e', '4': 'a', '5': 's',
    '7': 't', '@': 'a', '$': 's', '!': 'i',
})


def normalize_fee_name(name: str) -> str:
    """
    Normalize fee name to defeat obfuscation attacks.
    Handles: leet speak, hyphens, underscores, no spaces.
    """
    # Lowercase
    normalized = name.lower()
    # Convert leet speak: s3rvice -> service
    normalized = normalized.translate(LEET_MAP)
    # Remove hyphens and underscores completely (proc-essing -> processing)
    normalized = normalized.replace("-", "").replace("_", "")
    # Collapse multiple spaces
    normalized = " ".join(normalized.split())
    return normalized


def check_price(
    anchor: IntentAnchor,
    payload: AgentPayload,
    config: VetoConfig = DEFAULT_VETO_CONFIG,
) -> CheckResult:
    """
    Check if total transaction price is within the user's budget.

    Now considers: unit_price * quantity + fees
    """
    max_allowed = anchor.max_price * (1 + config.price_tolerance)
    total = payload.total_price

    if total > max_allowed:
        breakdown = f"${payload.unit_price:.2f} x {payload.quantity}"
        if payload.fees:
            breakdown += f" + ${payload.total_fees:.2f} fees"
        return CheckResult(
            name="price",
            passed=False,
            reason=f"Total ${total:.2f} ({breakdown}) exceeds max ${anchor.max_price:.2f}",
        )

    return CheckResult(
        name="price",
        passed=True,
        reason=f"Total ${total:.2f} within budget",
    )


def normalize_category(category: str) -> str:
    """Normalize category for comparison (handles plurals, spaces, etc.)."""
    normalized = category.lower().strip()
    # Remove trailing 's' for plural handling
    if normalized.endswith('s') and not normalized.endswith('ss'):
        normalized = normalized[:-1]
    # Replace spaces and dashes with underscores
    normalized = normalized.replace(" ", "_").replace("-", "_")
    return normalized


def check_category(
    anchor: IntentAnchor,
    payload: AgentPayload,
) -> CheckResult:
    """
    Check if transaction category matches the intent.

    Uses normalized comparison to handle variations like:
    - "gift_card" vs "gift_cards"
    - "Gift Card" vs "gift_card"
    """
    anchor_cat = normalize_category(anchor.item_category)
    payload_cat = normalize_category(payload.item_category)

    if payload_cat != anchor_cat:
        return CheckResult(
            name="category",
            passed=False,
            reason=f"Category mismatch: '{payload.item_category}' != '{anchor.item_category}'",
        )

    return CheckResult(
        name="category",
        passed=True,
        reason="Category matches",
    )


def check_currency(
    anchor: IntentAnchor,
    payload: AgentPayload,
) -> CheckResult:
    """
    Check if transaction currency matches the intent.
    """
    if payload.currency.upper() != anchor.currency.upper():
        return CheckResult(
            name="currency",
            passed=False,
            reason=f"Currency mismatch: '{payload.currency}' != '{anchor.currency}'",
        )

    return CheckResult(
        name="currency",
        passed=True,
        reason="Currency matches",
    )


def check_vendor(
    payload: AgentPayload,
    config: VetoConfig = DEFAULT_VETO_CONFIG,
    anchor: IntentAnchor = None,
) -> CheckResult:
    """
    Check if the vendor is trusted or suspicious.

    Checks:
    1. Suspicious TLDs (.ru, .cn, .tk, etc.)
    2. Brand-vendor mismatch (amazon-giftcards.com is NOT amazon.com)
    3. Trusted vendor allowlist (optional)
    """
    vendor_lower = payload.vendor.lower()

    # Check for suspicious TLDs
    for tld in config.suspicious_tlds:
        if vendor_lower.endswith(tld):
            return CheckResult(
                name="vendor",
                passed=False,
                reason=f"Vendor '{payload.vendor}' has suspicious TLD '{tld}'",
            )

    # NEW: Check brand-vendor match
    # If intent specifies a brand, vendor must be the official domain
    if anchor and anchor.core_constraints:
        for constraint in anchor.core_constraints:
            if constraint.lower().startswith("brand:"):
                brand = constraint.split(":", 1)[1].lower().strip()

                # Map known brands to their official domains
                # Expanded list based on attack report findings
                official_domains = {
                    # Original 12
                    "amazon": ["amazon.com", "amazon.co.uk", "amazon.de", "amazon.ca", "amazon.fr"],
                    "apple": ["apple.com", "store.apple.com"],
                    "google": ["google.com", "play.google.com", "store.google.com"],
                    "netflix": ["netflix.com"],
                    "spotify": ["spotify.com"],
                    "nike": ["nike.com"],
                    "steam": ["steampowered.com", "store.steampowered.com"],
                    "playstation": ["playstation.com", "store.playstation.com"],
                    "xbox": ["xbox.com", "microsoft.com"],
                    "walmart": ["walmart.com"],
                    "target": ["target.com"],
                    "bestbuy": ["bestbuy.com"],
                    "ebay": ["ebay.com"],
                    # Added to prevent unlisted brand spoofing
                    "visa": ["visa.com", "usa.visa.com"],
                    "mastercard": ["mastercard.com", "mastercard.us"],
                    "starbucks": ["starbucks.com"],
                    "uber": ["uber.com"],
                    "lyft": ["lyft.com"],
                    "doordash": ["doordash.com"],
                    "grubhub": ["grubhub.com"],
                    "airbnb": ["airbnb.com"],
                    "sephora": ["sephora.com"],
                    "nordstrom": ["nordstrom.com"],
                    "adidas": ["adidas.com"],
                    "footlocker": ["footlocker.com"],
                    "gamestop": ["gamestop.com"],
                    "home depot": ["homedepot.com"],
                    "lowes": ["lowes.com"],
                    "costco": ["costco.com"],
                    "microsoft": ["microsoft.com", "store.microsoft.com"],
                    "hulu": ["hulu.com"],
                    "disney": ["disney.com", "disneyplus.com"],
                    "paramount": ["paramount.com", "paramountplus.com"],
                }

                if brand in official_domains:
                    is_official = any(vendor_lower == domain or vendor_lower.endswith("." + domain)
                                     for domain in official_domains[brand])
                    if not is_official:
                        return CheckResult(
                            name="vendor",
                            passed=False,
                            reason=f"Vendor '{payload.vendor}' is not official {brand.title()} domain. Expected: {official_domains[brand][0]}",
                        )

    # Check if trusted (informational, doesn't fail)
    is_trusted = vendor_lower in config.trusted_vendors
    status = "trusted" if is_trusted else "unknown"

    return CheckResult(
        name="vendor",
        passed=True,
        reason=f"Vendor '{payload.vendor}' is {status}",
    )


def check_price_anomaly(
    anchor: IntentAnchor,
    payload: AgentPayload,
    config: VetoConfig = DEFAULT_VETO_CONFIG,
) -> CheckResult:
    """
    Detect suspiciously low prices that indicate scams.

    If the price is significantly below the expected range,
    it's likely too good to be true.
    """
    threshold = anchor.max_price * config.price_anomaly_threshold

    if payload.unit_price < threshold:
        return CheckResult(
            name="price_anomaly",
            passed=False,
            reason=f"Unit price ${payload.unit_price:.2f} suspiciously low (< {config.price_anomaly_threshold:.0%} of ${anchor.max_price:.2f})",
        )

    return CheckResult(
        name="price_anomaly",
        passed=True,
        reason="Price within normal range",
    )


def check_quantity(
    anchor: IntentAnchor,
    payload: AgentPayload,
) -> CheckResult:
    """
    Check if quantity matches the user's intent.

    Catches attacks where agent orders more items than requested.
    """
    if payload.quantity > anchor.quantity:
        return CheckResult(
            name="quantity",
            passed=False,
            reason=f"Quantity {payload.quantity} exceeds requested {anchor.quantity}",
        )

    if payload.quantity < anchor.quantity:
        return CheckResult(
            name="quantity",
            passed=False,
            reason=f"Quantity {payload.quantity} less than requested {anchor.quantity}",
        )

    return CheckResult(
        name="quantity",
        passed=True,
        reason=f"Quantity matches ({payload.quantity})",
    )


def check_hidden_fees(
    payload: AgentPayload,
) -> CheckResult:
    """
    Detect suspicious hidden fees.

    Catches attacks where agent adds unauthorized fees like
    'service fee', 'processing fee', 'insurance', etc.

    Now handles obfuscation attempts like:
    - Leet speak: s3rvice -> service
    - Hyphenation: proc-essing -> processing
    - No spaces: conveniencefee -> convenience fee
    """
    suspicious_found = []

    for fee in payload.fees:
        # Normalize fee name to defeat obfuscation
        fee_name_normalized = normalize_fee_name(fee.name)
        fee_name_no_spaces = fee_name_normalized.replace(" ", "")

        # Check against suspicious fee patterns
        for suspicious in SUSPICIOUS_FEES:
            suspicious_no_spaces = suspicious.replace(" ", "")
            # Match either with or without spaces
            if suspicious in fee_name_normalized or suspicious_no_spaces in fee_name_no_spaces:
                suspicious_found.append(f"{fee.name}: ${fee.amount:.2f}")
                break

    if suspicious_found:
        return CheckResult(
            name="hidden_fees",
            passed=False,
            reason=f"Suspicious fees detected: {', '.join(suspicious_found)}",
        )

    return CheckResult(
        name="hidden_fees",
        passed=True,
        reason="No suspicious fees",
    )


def check_subscription_trap(
    anchor: IntentAnchor,
    payload: AgentPayload,
) -> CheckResult:
    """
    Detect subscription/recurring charge traps.

    Catches attacks where agent converts a one-time purchase
    into a recurring subscription.
    """
    if payload.is_recurring and not anchor.is_recurring:
        return CheckResult(
            name="subscription_trap",
            passed=False,
            reason="Transaction is recurring but user requested one-time purchase",
        )

    if not payload.is_recurring and anchor.is_recurring:
        return CheckResult(
            name="subscription_trap",
            passed=False,
            reason="Transaction is one-time but user requested subscription",
        )

    return CheckResult(
        name="subscription_trap",
        passed=True,
        reason="Recurring status matches intent",
    )


def check_currency_manipulation(
    anchor: IntentAnchor,
    payload: AgentPayload,
) -> CheckResult:
    """
    Detect currency manipulation attacks.

    Catches attacks where agent charges in a different currency,
    potentially at unfavorable exchange rates.
    """
    if payload.currency.upper() != anchor.currency.upper():
        return CheckResult(
            name="currency_manipulation",
            passed=False,
            reason=f"Currency mismatch: charging in {payload.currency} but user specified {anchor.currency}",
        )

    return CheckResult(
        name="currency_manipulation",
        passed=True,
        reason="Currency matches",
    )
