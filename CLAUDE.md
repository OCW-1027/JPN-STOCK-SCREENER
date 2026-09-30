# JPN-STOCK-SCREENER — Claude Code 작업 지침

일본·한국·미국 전 종목 데일리 스크리너. GitHub Actions가 15분마다 페이지를 생성해
GitHub Pages와 Cloudflare Pages(gh-pages 브랜치)에 동시 배포한다.

- 라이브: https://stock-screener-ev3.pages.dev (한국어 `/jp/ /kr/ /us/`, 일본어 `/ja/jp/` …)
- 연결 사이트: 마켓 지표 https://daiji-data.streamlit.app · 연상 사고 · 글로벌 대시보드 · BTC 데스크

## 파일 역할

| 파일 | 역할 | 주의 |
|---|---|---|
| `screener.py` | 데이터 수집 → 시그널 계산 → `template.html` 치환 → 6페이지 생성 | 행 배열 인덱스(0~67)가 `template.html`과 결합. 컬럼 추가 시 양쪽 동시 수정 |
| `template.html` | 프론트엔드 전체 (JS 포함). `__PLACEHOLDER__`를 `screener.py`가 치환 | f-string 아님. `replace()` 치환 |
| `i18n.py` | 한/일 문구 사전 `UI`, 컬럼·시그널 도움말 `HELP` `HELP_SIG`, BTC 배너 코드 | 새 문구는 ko/ja 둘 다 추가 |
| `supply.py` | 일본 수급: JPX 신용잔고(주간 PDF, `margin/01.html`) + 공개 숏포지션(일별 xls, 기관명 상위5 `s_who`) + 역일보(`margin/02.html` Premium_Charges.xlsx) → `supply/jp.json` | pdfplumber·openpyxl 필요 |
| `supply_kr.py` | 한국 수급: 네이버 투자자별 매매 → `supply/kr.json` | 종목당 1회 호출, 21분 소요 |
| `supply_us.py` | 미국 수급: FINRA 일별 공매도 + 나스닥 SI → `supply/us.json` | |
| `profiles.py` | 회사 소개문 수집 (야후) → `profiles/` | 250건/일, 40분 소요 |
| `backtest.py` | history/ 스냅샷으로 시그널별 +1/+5/+20일 성과 → `/backtest/` | |
| `ranking.py` | 거래대금·시총 상위 100위 순위 추이 → `/ranking/` | |
| `brief.py` | 운용 데스크 브리프 → `/brief/`. 상세에 **포지션 계산기**(계좌·리스크%·손절→수량, 단원주·갭·기대값)와 테크니컬 레벨 14종 | 계산기 데이터는 스냅샷의 ATR·SMA50·BB·Ichimoku·Pivot·ADX·Stoch (2026-09-30 이후 스냅샷) |
| `volcurve.py` | 장중 거래량 곡선 기록 (RVOL 보정용 재료 수집 중) | 아직 보정 미적용 |

## 워크플로 — 반드시 분리 유지

| 워크플로 | 주기 | 하는 일 |
|---|---|---|
| `daily.yml` | 15분 (cron-job.org dispatch) | 스크리너·순위·백테스트·브리프 페이지 생성, 종가판 history 저장, gh-pages 푸시 |
| `profiles.yml` | 04:00 JST | 프로필 수집 |
| `kr-supply.yml` | 16:20 JST | 한국 수급 |
| `us-supply.yml` | 07:30 JST | 미국 수급 |
| `brief.yml` | 종가판 직후 dispatch | 브리프 데이터 |

**절대 하지 말 것**: 오래 걸리는 작업(프로필·한국 수급 등)을 `daily.yml`에 넣지 않는다.
15분 주기를 넘기면 다음 실행과 겹쳐 연쇄 취소되고 화면 갱신이 멈춘다. 실제로 겪었다.

**커밋 단계**: 여러 워크플로가 같은 리포에 커밋하므로 push 실패 시 `git fetch → rebase → push`
재시도 루프(5회)를 쓴다. `git pull --rebase || true`는 실패를 삼키므로 금지.

## JPX 사이트는 예고 없이 재편된다 (2026-09 실사례)
- 종목별 신용잔고 PDF가 `margin/05.html → 01.html`로 이동, 종목일람이 `data_j.xls → .xlsx`로 변경.
  둘 다 조용히 실패하며 폴백(TV 업종 대체)으로 가려져 있었다.
- **수집 스크립트는 고정 URL 대신 페이지에서 링크를 찾도록** 작성한다. 실패 시 로그에 반드시 남긴다.
- 라이브 확인: `supply/jp.json`의 `meta.margin_asof`가 최근 금요일인지, 스크리너 로그에 "JPX 종목일람 N종목"이 찍히는지.

## 데이터 흐름의 함정

- **종가판 판정**: 16:30~17:59 JST(일·한), 06:30~07:59(미). `history/{m}/{date}.csv.gz`가 이미
  있으면 건너뜀. 수급 수집은 `HM`(종가판 플래그)과 분리돼 있음 — 파일에 오늘 날짜가 있는지로 판정.
- **네이버·KRX는 개발 컨테이너에서 403**이지만 GitHub Actions에서는 열린다. 로컬 실패 ≠ 실제 실패.
- **TradingView RVOL은 시간 보정 없음**. 장중엔 눌려 나옴. 선형 보정(경과분/300)은 오탐 폭증
  (검증: 44종목 → 735종목) — 실측 곡선(`volcurve/`)이 쌓인 뒤 적용할 것.
- **대차배율 1배 미만 ≠ 숏스퀴즈**. 외식·소매는 주주우대 크로스(優待つなぎ売り). 3·9월에 대량 발생.
- **공개숏포지션%**는 JPX 0.5% 공개 기준 이상만 합산. 시장 전체 공매도 잔고가 아님.
  기관명(`s_who`)은 바클레이즈·골드만·모건MUFG가 대부분 — 헤지펀드 고객의 프라임 브로커 명의이므로
  "그 증권사의 견해"로 해석하지 말 것. 증권사별 **신용잔고**는 공시 대상이 아니라 어디에도 없다.
- **역일보(gy_rate)**는 우대·배당 권리일 직전(3·9월 말)에 크로스 거래로 대량 발생 — 이때는 숏스퀴즈 신호로 보지 말 것.
- **FINRA 공매도비중%**는 잔고가 아닌 당일 거래 중 숏 비중. 40~60%도 흔함. 절대치보다 Δ를 볼 것.

## 화면 규칙

- 행 배열은 현재 71열(0~70). 68=숏 기관 배열, 69=역일보(엔), 70=역일보 연율%.
- 시그널 21종은 비트마스크(`r[18]`). 추가 시 `SIG_KEYS`·`SIG_WEIGHT`(screener.py),
  `SIGS`·마스크(template.html), `UI.s_*`·`HELP_SIG`·`SIGNAL_I18N`(i18n.py), `SIGNALS`(backtest.py) 전부 수정.
- 컬럼은 `COLS`에 `g:`(프리셋 그룹)·`m:`(시장 한정) 속성. 수급 컬럼은 `m:'jp'|'kr'|'us'`로 해당 시장에만 표시.
- 모든 컬럼·시그널에 물음표 도움말(`HELPMAP` → `CFG.help`). 새 지표엔 반드시 붙일 것.
- URL 필터: `?tab=&sector=&min=&sig=&and=&sort=&dir=` — `readURL()/writeURL()`.
- 상세(사업내용 클릭) 행은 `.dtext{position:sticky;left:0}`로 가로 스크롤 시 왼쪽 고정.
- 모바일 390px에서 `document.documentElement.scrollWidth === window.innerWidth`여야 한다. 넘치면 브라우저가 축소함.

## 검증 방법

```bash
pip install -r requirements.txt playwright && playwright install chromium
python screener.py          # site/ 생성 (한국 시세는 로컬에서 403 — 정상)
python backtest.py; python ranking.py
# Playwright로 site/jp/index.html 열어 JS 오류·컬럼·모바일 폭 확인
```
페이지 생성 후 **반드시 브라우저로 렌더링 확인**. 정적 검사만으로 넘기지 말 것 (여러 번 당했다).

## 커밋 규칙

- 바꾼 파일만 커밋. 메시지는 한국어로 무엇을 왜 바꿨는지 한 줄.
- `README.md` 하단에 버전 기록(v11~v27 형식)을 이어서 추가.
- 워크플로 파일 수정 시 `yaml.safe_load`로 유효성 확인 후 커밋.
