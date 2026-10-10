import unicodedata
import re


def normalize_company_name(name: str) -> str:
    normalized = unicodedata.normalize("NFKD", name)
    normalized = normalized.lower()
    normalized = re.sub(r"[^a-z0-9_\s]", "", normalized)
    normalized = normalized.strip()
    normalized = re.sub(r"\s+", "_", normalized)
    return normalized if normalized else "unknown"


def normalize_email(email: str) -> str:
    normalized = email.lower().strip().strip("<>,;")
    # Some copied contact chips append their SVG icon label directly after a
    # normal domain (for example, `person@company.comsvg`). Treat that exact
    # presentation artifact as the intended standard domain before validating.
    match = re.fullmatch(r"(.+\.(?:com|net|org|edu|gov|co|io))svg", normalized)
    return match.group(1) if match else normalized


def normalize_phone(phone: str) -> str | None:
    """Return a comparable phone value, preserving a leading international +."""
    value = phone.strip()
    has_plus = value.startswith("+")
    digits = re.sub(r"\D", "", value)
    if not 7 <= len(digits) <= 15:
        return None
    return f"+{digits}" if has_plus else digits


def company_from_business_email(email: str) -> tuple[str, str] | None:
    """Infer a display name and domain from a non-public email address."""
    if "@" not in email:
        return None
    domain = email.rsplit("@", 1)[1].lower().strip()
    public_domains = {
        "gmail.com", "googlemail.com", "yahoo.com", "outlook.com", "hotmail.com",
        "icloud.com", "proton.me", "protonmail.com",
    }
    labels = domain.split(".")
    if domain in public_domains or len(labels) < 2 or not labels[0]:
        return None
    return labels[0].replace("-", " ").replace("_", " ").title(), domain


def name_from_email(email: str) -> str | None:
    """Build a readable fallback name from a conventional email local-part."""
    if "@" not in email:
        return None
    local_part = email.split("@", 1)[0]
    words = [word for word in re.split(r"[._+\-]+", local_part) if word]
    if not words:
        return None
    readable_words = [re.sub(r"\d+", "", word) for word in words]
    readable_words = [word for word in readable_words if word]
    return " ".join(word.capitalize() for word in readable_words) or None


def is_valid_email(email: str) -> bool:
    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    return bool(re.match(pattern, email))


def extract_email_from_text(text: str) -> str | None:
    match = re.search(r"([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})", text)
    return match.group(1) if match else None


def extract_phone_from_text(text: str) -> str | None:
    match = re.search(r"(\+?[\d\s\-()]{7,})", text)
    return match.group(1).strip() if match else None
