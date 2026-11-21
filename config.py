import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


def _str(name: str, default: str = "") -> str:
    return os.getenv(name, default).strip()


def _int(name: str, default: int) -> int:
    v = _str(name)
    return int(v) if v else default


def _float(name: str, default: float) -> float:
    v = _str(name)
    return float(v) if v else default


def _bool(name: str, default: bool = False) -> bool:
    v = _str(name).lower()
    return v in ("1", "true", "yes", "on") if v else default


@dataclass(frozen=True)
class Config:
    login: int
    password: str
    server: str
    mt5_path: str
    allow_live: bool

    symbol: str
    timeframe: str
    lot: float
    sl_points: int
    tp_points: int
    fast_ma: int
    slow_ma: int
    magic: int
    poll_seconds: int

    max_positions: int
    daily_loss_limit: float

    telegram_token: str
    telegram_chat_id: int | None


def load() -> Config:
    chat_id = _str("TELEGRAM_CHAT_ID")
    return Config(
        login=_int("MT5_LOGIN", 0),
        password=_str("MT5_PASSWORD"),
        server=_str("MT5_SERVER"),
        mt5_path=_str("MT5_PATH"),
        allow_live=_bool("ALLOW_LIVE", False),
        symbol=_str("SYMBOL", "EURUSD"),
        timeframe=_str("TIMEFRAME", "M15").upper(),
        lot=_float("LOT", 0.01),
        sl_points=_int("SL_POINTS", 200),
        tp_points=_int("TP_POINTS", 400),
        fast_ma=_int("FAST_MA", 10),
        slow_ma=_int("SLOW_MA", 30),
        magic=_int("MAGIC", 20261121),
        poll_seconds=_int("POLL_SECONDS", 10),
        max_positions=_int("MAX_POSITIONS", 1),
        daily_loss_limit=_float("DAILY_LOSS_LIMIT", 50.0),
        telegram_token=_str("TELEGRAM_TOKEN"),
        telegram_chat_id=int(chat_id) if chat_id else None,
    )
