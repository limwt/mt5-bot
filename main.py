"""MT5 자동매매 봇 진입점.

- 매매 루프: POLL_SECONDS마다 새 봉이 마감됐는지 확인하고 전략 신호대로 진입/청산
- 텔레그램: 아이폰에서 /status /positions /pause /resume /closeall 로 확인·제어
  (TELEGRAM_TOKEN이 비어 있으면 텔레그램 없이 매매 루프만 돈다)
"""
import asyncio
import logging

import MetaTrader5 as mt5

import config
import risk
import strategy
from mt5_client import MT5Client

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[logging.StreamHandler(), logging.FileHandler("bot.log", encoding="utf-8")],
)
log = logging.getLogger("bot")

cfg = config.load()
client = MT5Client(cfg)


class State:
    running = True        # /pause, /resume 로 토글
    last_bar_time = None  # 같은 봉에서 중복 매매 방지
    halt_notified = False  # 일일 손실 한도 알림은 한 번만


state = State()
_app = None  # 텔레그램 Application (없으면 None)


async def notify(text: str):
    log.info(text)
    if _app and cfg.telegram_chat_id:
        try:
            await _app.bot.send_message(chat_id=cfg.telegram_chat_id, text=text)
        except Exception:
            log.exception("텔레그램 전송 실패")


def _side(pos) -> str:
    return "buy" if pos.type == mt5.POSITION_TYPE_BUY else "sell"


# ---------------- 매매 루프 ----------------
async def tick():
    df = client.rates(cfg.slow_ma + 5)
    closed_bar_time = df["time"].iloc[-2]
    if closed_bar_time == state.last_bar_time:
        return  # 새로 마감된 봉 없음
    state.last_bar_time = closed_bar_time

    if not state.running:
        return

    sig = strategy.signal(df, cfg.fast_ma, cfg.slow_ma)
    if sig is None:
        return

    # 반대 방향 포지션은 청산
    for p in client.positions():
        if _side(p) != sig:
            client.close(p)
            await notify(f"청산 {_side(p)} {p.volume} @ {p.price_current} (손익 {p.profit:.2f})")

    positions = client.positions()
    if any(_side(p) == sig for p in positions):
        return  # 이미 같은 방향 보유

    reason = risk.check_entry(cfg, len(positions), client.today_pnl())
    if reason:
        if not state.halt_notified:
            await notify(f"진입 보류: {reason}")
            state.halt_notified = True
        return
    state.halt_notified = False

    result = client.open(sig, cfg.lot)
    await notify(f"진입 {sig} {cfg.symbol} {cfg.lot} @ {result.price}")


async def trading_loop():
    await notify(f"봇 시작: {cfg.symbol} {cfg.timeframe}, MA {cfg.fast_ma}/{cfg.slow_ma}")
    while True:
        try:
            await tick()
        except Exception as e:
            log.exception("tick 에러")
            await notify(f"에러: {e}")
        await asyncio.sleep(cfg.poll_seconds)


# ---------------- 텔레그램 명령 ----------------
def build_telegram_app():
    from telegram import Update
    from telegram.ext import Application, CommandHandler, ContextTypes, filters

    async def status(update: Update, _: ContextTypes.DEFAULT_TYPE):
        acc = client.account()
        await update.message.reply_text(
            f"{'실행 중' if state.running else '일시정지'}\n"
            f"계좌 {acc.login} ({'데모' if acc.trade_mode == mt5.ACCOUNT_TRADE_MODE_DEMO else '실계정'})\n"
            f"잔고 {acc.balance:.2f} / 평가 {acc.equity:.2f} {acc.currency}\n"
            f"오늘 손익 {client.today_pnl():.2f}\n"
            f"포지션 {len(client.positions())}개"
        )

    async def positions(update: Update, _: ContextTypes.DEFAULT_TYPE):
        ps = client.positions()
        if not ps:
            await update.message.reply_text("보유 포지션 없음")
            return
        lines = [f"#{p.ticket} {_side(p)} {p.volume} @ {p.price_open} → {p.price_current} ({p.profit:.2f})" for p in ps]
        await update.message.reply_text("\n".join(lines))

    async def pause(update: Update, _: ContextTypes.DEFAULT_TYPE):
        state.running = False
        await update.message.reply_text("일시정지: 신규 매매 중단 (보유 포지션의 SL/TP는 그대로 유지)")

    async def resume(update: Update, _: ContextTypes.DEFAULT_TYPE):
        state.running = True
        await update.message.reply_text("재개")

    async def closeall(update: Update, _: ContextTypes.DEFAULT_TYPE):
        n = len(client.positions())
        client.close_all()
        await update.message.reply_text(f"{n}개 포지션 청산 요청 완료")

    async def post_init(app):
        app.create_task(trading_loop())

    app = Application.builder().token(cfg.telegram_token).post_init(post_init).build()
    # 내 채팅방에서 온 명령만 받는다
    only_me = filters.Chat(chat_id=cfg.telegram_chat_id)
    for name, fn in [("status", status), ("positions", positions), ("pause", pause),
                     ("resume", resume), ("closeall", closeall)]:
        app.add_handler(CommandHandler(name, fn, filters=only_me))
    return app


def main():
    global _app
    acc = client.connect()
    log.info("MT5 접속: %s %s (trade_mode=%s)", acc.login, acc.server, acc.trade_mode)
    try:
        if cfg.telegram_token and cfg.telegram_chat_id:
            _app = build_telegram_app()
            _app.run_polling()
        else:
            log.warning("TELEGRAM_TOKEN/CHAT_ID 없음: 텔레그램 없이 실행")
            asyncio.run(trading_loop())
    finally:
        client.shutdown()


if __name__ == "__main__":
    main()
