import re

PHONE_EXAMPLES = {
    "russia": "+7 (903) 123-45-67",
    "uae": "+971 50 123 4567",
}


def validate_phone(raw: str) -> tuple[bool, str]:
    digits = re.sub(r"\D", "", raw)

    if digits.startswith("00971"):
        digits = "971" + digits[5:]

    if digits.startswith("7") and len(digits) == 11:
        formatted = f"+7 ({digits[1:4]}) {digits[4:7]}-{digits[7:9]}-{digits[9:]}"
        return True, formatted

    if digits.startswith("8") and len(digits) == 11:
        formatted = f"+7 ({digits[1:4]}) {digits[4:7]}-{digits[7:9]}-{digits[9:]}"
        return True, formatted

    if digits.startswith("971") and len(digits) == 12:
        formatted = f"+971 {digits[3:5]} {digits[5:8]} {digits[8:]}"
        return True, formatted

    return False, ""
