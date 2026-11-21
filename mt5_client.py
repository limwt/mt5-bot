"""MT5 터미널 연결, 시세 조회, 주문/청산을 감싸는 얇은 래퍼."""
from datetime import datetime, timedelta

import MetaTrader5 as mt5
import pandas as pd

from config import Config

TIMEFRAMES = {
    "M1": mt5.TIMEFRAME_M1,
    "M5": mt5.TIMEFRAME_M5,
    "M15": mt5.TIMEFRAME_M15,
    "M30": mt5.TIMEFRAME_M30,
    "H1": mt5.TIMEFRAME_H1,
    "H4": mt5.TIMEFRAME_H4,
    "D1": mt5.TIMEFRAME_D1,
}


class MT5Client:
    def __init__(self, cfg: Config):
        self.cfg = cfg
        if cfg.timeframe not in TIMEFRAMES:
            raise ValueError(f"지원하지 않는 TIMEFRAME: {cfg.timeframe}")
        self.tf = TIMEFRAMES[cfg.timeframe]

    # ---------- 연결 ----------
    def connect(self):
        kwargs = {"login": self.cfg.login, "password": self.cfg.password, "server": self.cfg.server}
        if self.cfg.mt5_path:
            kwargs["path"] = self.cfg.mt5_path
        if not mt5.initialize(**kwargs):
            raise RuntimeError(f"MT5 initialize 실패: {mt5.last_error()}")

        info = mt5.account_info()
        if info is None:
            raise RuntimeError(f"계좌 정보 조회 실패: {mt5.last_error()}")

        # 안전장치: 데모가 아니면 ALLOW_LIVE=true 없이는 실행 거부
        if info.trade_mode != mt5.ACCOUNT_TRADE_MODE_DEMO and not self.cfg.allow_live:
            mt5.shutdown()
            raise RuntimeError("실계정이 감지됐습니다. 데모 검증 후 ALLOW_LIVE=true로 명시해야 실행됩니다.")

        if not mt5.symbol_select(self.cfg.symbol, True):
            raise RuntimeError(f"심볼 선택 실패: {self.cfg.symbol} ({mt5.last_error()})")
        return info

    def shutdown(self):
        mt5.shutdown()

    def account(self):
        return mt5.account_info()

    # ---------- 시세 ----------
    def rates(self, count: int) -> pd.DataFrame:
        data = mt5.copy_rates_from_pos(self.cfg.symbol, self.tf, 0, count)
        if data is None or len(data) == 0:
            raise RuntimeError(f"시세 조회 실패: {mt5.last_error()}")
        df = pd.DataFrame(data)
        df["time"] = pd.to_datetime(df["time"], unit="s")
        return df

    # ---------- 포지션 ----------
    def positions(self):
        """이 봇(MAGIC)이 연 포지션만 반환."""
        pos = mt5.positions_get(symbol=self.cfg.symbol) or ()
        return [p for p in pos if p.magic == self.cfg.magic]

    def open(self, side: str, volume: float):
        info = mt5.symbol_info(self.cfg.symbol)
        tick = mt5.symbol_info_tick(self.cfg.symbol)
        if info is None or tick is None:
            raise RuntimeError(f"심볼 정보 조회 실패: {mt5.last_error()}")

        buy = side == "buy"
        price = tick.ask if buy else tick.bid
        sl_dist = self.cfg.sl_points * info.point
        tp_dist = self.cfg.tp_points * info.point
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": self.cfg.symbol,
            "volume": volume,
            "type": mt5.ORDER_TYPE_BUY if buy else mt5.ORDER_TYPE_SELL,
            "price": price,
            "sl": round(price - sl_dist if buy else price + sl_dist, info.digits),
            "tp": round(price + tp_dist if buy else price - tp_dist, info.digits),
            "deviation": 20,
            "magic": self.cfg.magic,
            "comment": "mt5-bot",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": self._filling(info),
        }
        return self._send(request)

    def close(self, pos):
        info = mt5.symbol_info(pos.symbol)
        tick = mt5.symbol_info_tick(pos.symbol)
        is_buy = pos.type == mt5.POSITION_TYPE_BUY
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": pos.symbol,
            "volume": pos.volume,
            "type": mt5.ORDER_TYPE_SELL if is_buy else mt5.ORDER_TYPE_BUY,
            "position": pos.ticket,
            "price": tick.bid if is_buy else tick.ask,
            "deviation": 20,
            "magic": self.cfg.magic,
            "comment": "mt5-bot close",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": self._filling(info),
        }
        return self._send(request)

    def close_all(self):
        return [self.close(p) for p in self.positions()]

    # ---------- 손익 ----------
    def today_pnl(self) -> float:
        """오늘 실현손익 + 현재 미실현손익 (이 봇 MAGIC 기준).

        MT5 히스토리는 서버 시간 기준이라 '오늘'의 경계가 로컬과 몇 시간 어긋날 수 있다.
        토이 프로젝트 용도로는 로컬 자정 기준 근사값으로 충분하다.
        """
        start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        deals = mt5.history_deals_get(start, datetime.now() + timedelta(days=1)) or ()
        realized = sum(d.profit + d.commission + d.swap for d in deals if d.magic == self.cfg.magic)
        floating = sum(p.profit for p in self.positions())
        return realized + floating

    # ---------- 내부 ----------
    @staticmethod
    def _filling(info):
        # symbol_info.filling_mode 비트마스크: 1=FOK, 2=IOC
        if info.filling_mode & 1:
            return mt5.ORDER_FILLING_FOK
        if info.filling_mode & 2:
            return mt5.ORDER_FILLING_IOC
        return mt5.ORDER_FILLING_RETURN

    @staticmethod
    def _send(request):
        result = mt5.order_send(request)
        if result is None:
            raise RuntimeError(f"order_send 실패: {mt5.last_error()}")
        if result.retcode != mt5.TRADE_RETCODE_DONE:
            raise RuntimeError(f"주문 거부 retcode={result.retcode} ({result.comment})")
        return result
