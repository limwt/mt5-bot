"""신규 진입 전에 확인하는 리스크 한도."""
from config import Config


def check_entry(cfg: Config, open_positions: int, today_pnl: float) -> str | None:
    """진입 불가 사유를 반환. 진입 가능하면 None."""
    if today_pnl <= -abs(cfg.daily_loss_limit):
        return f"일일 손실 한도 도달 ({today_pnl:.2f} <= -{cfg.daily_loss_limit})"
    if open_positions >= cfg.max_positions:
        return f"최대 포지션 수 도달 ({open_positions}/{cfg.max_positions})"
    return None
