"""Step 5: keep exact invoices distinct from mean field scores."""
import math


def summarize(scores):
    """Summarize eight bounded field scores; an empty report is not a pass."""
    if not isinstance(scores, dict) or len(scores) != 8:
        raise ValueError('A report needs all eight field scores.')
    values = list(scores.values())
    if any(isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) or not 0 <= v <= 1 for v in values):
        raise ValueError('Each field score must be a finite number between zero and one.')
    return {'correct': sum(v == 1 for v in values), 'fields': len(values),
            'exact': all(v == 1 for v in values), 'mean': sum(values) / len(values)}
