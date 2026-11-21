# mt5-bot

Infinox MT5 자동매매 토이 프로젝트.

```
[Windows PC/VPS]  MT5 터미널 ← Python 봇 (main.py)
                                   │
                                   ▼ 알림 / 명령
[iPhone]  텔레그램 (/status /pause …)  +  MT5 앱 (같은 계좌로 포지션 확인)
```

## 1. 준비 (최초 1회)

1. **Infinox MT5 데모 계정**: Infinox 사이트에서 MT5 데모 계정을 열고 로그인 번호, 비밀번호, 서버명을 메모해 둡니다.
2. **MT5 터미널 설치**: Infinox가 제공하는 MT5 데스크톱(Windows)을 설치하고 데모 계정으로 로그인합니다.
   - 툴바의 **Algo Trading** 버튼을 켜 둡니다(초록색).
   - 도구 → 옵션 → 전문가 조언자 → "알고리즘 트레이딩 허용"을 체크합니다.
   - 마켓 워치에서 `SYMBOL`(예: EURUSD)의 정확한 이름을 확인합니다. 브로커에 따라 `EURUSD.a`처럼 접미사가 붙습니다.
3. **Python 3.12 설치**
   ```powershell
   winget install Python.Python.3.12
   ```
4. **텔레그램 봇 만들기** (아이폰에서)
   - @BotFather에게 `/newbot`을 보내고 받은 **토큰**을 메모합니다.
   - 만든 봇에게 아무 메시지나 보낸 뒤, 브라우저에서 `https://api.telegram.org/bot<토큰>/getUpdates`를 열어 `"chat":{"id": ...}` 값을 확인합니다. 이 값이 **CHAT_ID**입니다.

## 2. 설치

```powershell
cd C:\workspace\private\mt5-bot
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
```

`.env`에 계좌 정보와 텔레그램 토큰, CHAT_ID를 채웁니다.

## 3. 실행

MT5 터미널을 켜 둔 상태에서 실행합니다.

```powershell
python main.py
```

텔레그램에 "봇 시작" 메시지가 오면 정상입니다.

| 명령 | 동작 |
|---|---|
| `/status` | 실행 상태, 잔고·평가금액, 오늘 손익, 포지션 수 |
| `/positions` | 보유 포지션 목록 |
| `/pause` | 신규 매매 중단 (SL/TP는 유지) |
| `/resume` | 재개 |
| `/closeall` | 이 봇이 연 포지션 전부 청산 |

## 4. 안전장치

- **실계정 차단**: 접속한 계좌가 데모가 아니면 `ALLOW_LIVE=true` 없이는 실행되지 않습니다.
- 모든 주문에 SL/TP가 붙습니다(`SL_POINTS`, `TP_POINTS`).
- `DAILY_LOSS_LIMIT`: 오늘 손익(실현+미실현)이 이 금액 아래로 떨어지면 신규 진입을 멈춥니다.
- `MAX_POSITIONS`: 동시에 보유할 수 있는 최대 포지션 수입니다.
- `MAGIC` 번호로 이 봇이 연 포지션만 관리합니다. 수동 주문은 건드리지 않습니다.

## 5. 전략 바꾸기

`strategy.py`의 `signal(df, fast, slow)`가 `'buy'`, `'sell'`, `None` 중 하나를 돌려주기만 하면 됩니다. 기본으로 들어 있는 이동평균 교차 전략은 **동작 확인용 샘플**입니다.

## 6. 실계정으로 옮기기

1. 데모에서 충분히 포워드 테스트합니다. 최소 몇 주는 돌려 보세요.
2. `.env`에서 계좌, 비밀번호, 서버를 실계정 값으로 바꾸고 `ALLOW_LIVE=true`로 설정합니다.
3. `LOT`은 최소 단위(0.01)부터 시작합니다. 데모와 실계정은 스프레드와 슬리피지가 다를 수 있습니다.

## 7. 24시간 운영

PC가 꺼지면 봇도 멈춥니다. 계속 돌리려면 Windows VPS에 MT5와 이 봇을 같이 올리고, 작업 스케줄러로 로그인 시 `main.py`가 자동 실행되게 설정합니다.
