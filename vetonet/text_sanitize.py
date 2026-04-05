"""
Shared text normalization utility for VetoNet.

Defeats Unicode homoglyph attacks, leet speak, invisible characters,
and other text obfuscation techniques used to bypass deterministic checks.
"""

import unicodedata

# Cyrillic and Greek homoglyphs → ASCII Latin equivalents
CONFUSABLES_MAP = str.maketrans(
    {
        # Cyrillic lowercase
        "\u0430": "a",  # а → a
        "\u0441": "c",  # с → c
        "\u0435": "e",  # е → e
        "\u0456": "i",  # і → i
        "\u0458": "j",  # ј → j
        "\u043e": "o",  # о → o
        "\u0440": "p",  # р → p
        "\u0455": "s",  # ѕ → s
        "\u0445": "x",  # х → x
        "\u0443": "y",  # у → y
        "\u043a": "k",  # к → k
        "\u043d": "h",  # н → h
        "\u0442": "t",  # т → t
        "\u0432": "b",  # в → b
        # Cyrillic uppercase
        "\u0410": "A",  # А → A
        "\u0421": "C",  # С → C
        "\u0415": "E",  # Е → E
        "\u0406": "I",  # І → I
        "\u0408": "J",  # Ј → J
        "\u041e": "O",  # О → O
        "\u0420": "P",  # Р → P
        "\u0405": "S",  # Ѕ → S
        "\u0425": "X",  # Х → X
        "\u0423": "Y",  # У → Y
        "\u041a": "K",  # К → K
        "\u041d": "H",  # Н → H
        "\u0422": "T",  # Т → T
        "\u0412": "B",  # В → B
        # Greek lowercase
        "\u03b1": "a",  # α → a
        "\u03b5": "e",  # ε → e
        "\u03b9": "i",  # ι → i
        "\u03ba": "k",  # κ → k
        "\u03bd": "v",  # ν → v
        "\u03bf": "o",  # ο → o
        "\u03c1": "p",  # ρ → p
        "\u03c4": "t",  # τ → t
        "\u03c7": "x",  # χ → x
        "\u03c5": "u",  # υ → u
    }
)

# Leet speak / number substitution → ASCII
LEET_MAP = str.maketrans(
    {
        "0": "o",
        "1": "i",
        "3": "e",
        "4": "a",
        "5": "s",
        "7": "t",
        "@": "a",
        "$": "s",
        "!": "i",
    }
)


def normalize_text(
    text: str,
    preserve_hyphens: bool = False,
    skip_leet: bool = False,
) -> str:
    """
    Normalize text through a multi-stage pipeline to defeat obfuscation.

    Args:
        text: Input text to normalize.
        preserve_hyphens: If True, keep hyphens and underscores intact.
        skip_leet: If True, skip leet-speak translation (preserves digits).
            Use for domain names where digits are meaningful.

    Returns:
        Normalized text string.
    """
    # 1. Strip invisible chars
    text = "".join(c for c in text if unicodedata.category(c) not in ("Cf", "Cc", "Zl", "Zp"))
    # 2. Lowercase
    text = text.lower()
    # 3. NFKD decomposition
    text = unicodedata.normalize("NFKD", text)
    # 4. Strip combining marks
    text = "".join(c for c in text if unicodedata.category(c) != "Mn")
    # 5. Apply confusables map
    text = text.translate(CONFUSABLES_MAP)
    # 6. Apply leet map (skip for domains where digits are meaningful)
    if not skip_leet:
        text = text.translate(LEET_MAP)
    # 7. Remove hyphens/underscores unless preserving
    if not preserve_hyphens:
        text = text.replace("-", "").replace("_", "")
    # 8. Collapse whitespace
    text = " ".join(text.split())
    return text.strip()
