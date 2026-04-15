class RoasCalculationError(Exception):
    """ROAS 无法计算（例如总成本为 0 导致分母为 0）。"""
