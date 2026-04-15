from __future__ import annotations

from decimal import Decimal


def decision_label_for_roas(roas: Decimal, *, min_roas: Decimal, ideal_roas: Decimal) -> str:
    """决策标签：PASS / HOLD / REJECT（与 DecisionLog.decision_label 一致）。"""
    if roas >= ideal_roas:
        return "PASS"
    if roas >= min_roas:
        return "HOLD"
    return "REJECT"
