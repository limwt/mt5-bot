"""예시 전략: 이동평균 교차. 동작 확인용 샘플이지 수익을 보장하는 전략이 아니다.

전략을 바꾸려면 signal()만 같은 시그니처로 교체하면 된다.
"""
import pandas as pd


def signal(df: pd.DataFrame, fast: int, slow: int) -> str | None:
    """마감된 봉 기준으로 'buy' / 'sell' / None 반환."""
    close = df["close"].iloc[:-1]  # 마지막 봉은 아직 진행 중이므로 제외
    if len(close) < slow + 2:
        return None

    f = close.rolling(fast).mean()
    s = close.rolling(slow).mean()
    if f.iloc[-2] <= s.iloc[-2] and f.iloc[-1] > s.iloc[-1]:
        return "buy"
    if f.iloc[-2] >= s.iloc[-2] and f.iloc[-1] < s.iloc[-1]:
        return "sell"
    return None
