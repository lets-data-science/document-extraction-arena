"""Step 4: a predicted row may satisfy only one expected row."""
import re
from decimal import Decimal
from learner.normalize import to_decimal


def equal_amount(a, b):
    left, right = to_decimal(a), to_decimal(b)
    return left is not None and right is not None and abs(left - right) < Decimal('0.005')


def row_matches(expected, predicted):
    if not isinstance(expected, dict) or not isinstance(predicted, dict):
        return False
    def text(value):
        return re.sub(r'\s+', ' ', value.strip()).casefold() if isinstance(value, str) else None
    label = text(expected.get('description'))
    return bool(label) and label == text(predicted.get('description')) and all(
        equal_amount(expected.get(key), predicted.get(key))
        for key in ('quantity', 'unit_price', 'amount')
    )


def match_rows(expected, predicted):
    """Return (expected index, predicted index) pairs using maximum matching.

    Augmenting paths avoid a greedy error when rounding tolerances overlap.
    Inputs are bounded to 100 rows by the invoice schema.
    """
    if not isinstance(expected, list) or not isinstance(predicted, list):
        raise ValueError('Line items must be lists.')
    if len(expected) > 100 or len(predicted) > 100:
        raise ValueError('Use at most 100 line items.')
    candidates = [[j for j, item in enumerate(predicted) if row_matches(row, item)] for row in expected]
    owners = {}
    def assign(i, seen):
        for j in candidates[i]:
            if j in seen:
                continue
            seen.add(j)
            if j not in owners or assign(owners[j], seen):
                owners[j] = i
                return True
        return False
    for i in range(len(expected)):
        assign(i, set())
    return sorted((i, j) for j, i in owners.items())
