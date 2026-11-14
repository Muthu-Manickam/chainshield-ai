import re

CITATION = re.compile(r"\b[A-Za-z][\w-]*#\d+\b")
# A number not glued to a word, code or citation ("SOP-02", "v2" and "#4" are not numbers).
NUMBER = re.compile(r"(?<![\w#.-])\d(?:[\d,]*\d)?(?:\.\d+)?")
CAUSAL = re.compile(r"\b(caus\w*|led to|result\w* in|due to|because of|responsible for|delayed by)\b", re.IGNORECASE)
SPECIFIC_ORDER = re.compile(r"\border\s*(?:id\s*)?#?\s*\d+", re.IGNORECASE)
SENTENCE_END = re.compile(r"(?<=[.!?])\s+")


def numbers_in(value) -> list[float]:
    if isinstance(value, bool):
        return []
    if isinstance(value, int | float):
        return [float(value)]
    if isinstance(value, str):
        return [float(n.replace(",", "")) for n in NUMBER.findall(CITATION.sub(" ", value))]
    if isinstance(value, dict):
        value = list(value.values())
    if isinstance(value, list | tuple):
        return [n for item in value for n in numbers_in(item)]
    return []


def is_supported(number: str, known: list[float]) -> bool:
    """A number in the text matches a tool value as written, rounded, or as a percentage."""
    decimals = len(number.split(".")[1]) if "." in number else 0
    x = float(number.replace(",", ""))
    return any(x in (round(v, decimals), round(v * 100, decimals)) for v in known)


def validate(text: str, citation_keys: set[str], tool_outputs: list[dict], eligible_codes: set[str] | None = None,
             proposed_codes: list[str] | None = None) -> list[str]:
    errors = []
    cited = CITATION.findall(text)
    errors += [f"Unknown citation {key}" for key in dict.fromkeys(cited) if key not in citation_keys]
    if eligible_codes is not None:
        errors += [f"Action {code} is not eligible" for code in proposed_codes or [] if code not in eligible_codes]
    known = numbers_in(tool_outputs)
    numbers = NUMBER.findall(CITATION.sub(" ", text))
    errors += [f"Number {n} is not in any tool output" for n in dict.fromkeys(numbers) if not is_supported(n, known)]
    errors += [f"Claims an incident delayed a specific order: {s.strip()}" for s in SENTENCE_END.split(text)
               if CAUSAL.search(s) and SPECIFIC_ORDER.search(s)]
    return errors
