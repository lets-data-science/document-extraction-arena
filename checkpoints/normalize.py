"""Step 3: compare amounts without silently changing their meaning."""
import re
from decimal import Decimal, InvalidOperation


def to_decimal(value):
    """Accept a finite number or an unformatted decimal string; otherwise None."""
    if isinstance(value, bool) or value is None:
        return None
    if not isinstance(value, (int, float, str, Decimal)):
        return None
    text = str(value).strip()
    if len(text) > 80 or not re.fullmatch(r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d{1,3})?", text):
        return None
    try:
        number = Decimal(text)
        return number if number.is_finite() and abs(number) <= Decimal('1e15') else None
    except (InvalidOperation, ValueError):
        return None
