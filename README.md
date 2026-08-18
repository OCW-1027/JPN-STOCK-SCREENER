# JP Market Screener — 일본 전 종목 데일리 스크리닝 대시보드

매일 장 마감 후, 도쿄증권거래소 **전 종목(약 3,800개)**의 시세·이동평균·거래대금을
수집하고 단기/중장기 시그널을 계산해 대시보드 HTML 하나로 만들어 줍니다.

- 데이터: TradingView Screener(무료) + JPX 공식 상장종목일람(일본어 종목명·33업종·시장구분)
- 표시: 코드/종목명/업종/구분/시그널/주가/등락%/갭%/5·20·200일선/이격도/거래량/RVOL/거래대금(억엔)/RSI/1주·1개월·3개월 수익률
- 행 클릭 → 트레이딩뷰 차트 새 탭

---

## A. GitHub 자동 배포 (추천 — PC 꺼져 있어도 매일 갱신)

GitHub Actions가 **평일 16:30(JST)** 에 클라우드에서 자동 실행하고,
결과를 GitHub Pages 고정 주소로 배포합니다. 완전 무료입니다.

### 최초 설정 (웹브라우저만으로 가능, 약 10분)

1. **리포지토리 생성** — github.com 로그인 → 우상단 `+` → *New repository*
   - 이름: `jp-screener` / **Public** 선택 (무료 Pages는 Public 필수)
   - *Add a README* 체크는 하지 않아도 됨 → **Create repository**

2. **파일 업로드** — 리포 화면의 *uploading an existing file* 클릭 →
   압축 푼 폴더 안의 **모든 항목**( `.github` 폴더 포함, `screener.py`,
   `template.html`, `requirements.txt`, `README.md`, `.gitignore` )을
   드래그해 넣고 → **Commit changes**
   - 만약 `.github` 폴더가 안 올라가면: *Add file → Create new file* →
     파일명 칸에 `.github/workflows/daily.yml` 이라고 입력하고
     zip 안의 `daily.yml` 내용을 붙여넣어 커밋하면 됩니다.

3. **첫 실행** — 상단 **Actions** 탭 → 왼쪽 *Daily Screener* →
   **Run workflow** 버튼 → 1~2분 뒤 초록 체크가 뜨면 성공.
   리포에 `index.html`과 `history/` 가 자동 커밋됩니다.

4. **Pages 켜기** — **Settings → Pages** →
   *Source: Deploy from a branch* → Branch `main` / `/ (root)` → **Save**

5. 1~2분 후 접속: **`https://<내아이디>.github.io/jp-screener/`**
   → 폰 홈 화면에 북마크해 두면 매일 아침 확인 끝.

### 운영 참고
- 스케줄: `.github/workflows/daily.yml`의 `cron: '30 7 * * 1-5'`(UTC) = 평일 16:30 JST.
  GitHub 사정으로 10~20분 지연될 수 있습니다.
- **수동 갱신**: Actions 탭 → Run workflow (폰 브라우저에서도 가능).
- 실행 실패 시 GitHub가 이메일로 알려줍니다.
- Public 리포라 주소를 아는 사람은 볼 수 있지만, 내용은 공개 시세 데이터뿐입니다.
  완전 비공개가 필요하면 GitHub Pro(유료)에서 Private+Pages가 가능합니다.
- `history/날짜.csv.gz` 스냅샷이 매일 리포에 쌓입니다(일 약 0.6MB) —
  추후 스파크라인·백테스트 재료입니다.

---

## B. 로컬 실행 (보조)

```bat
pip install -r requirements.txt
python screener.py
```
`dashboard.html` 생성 후 브라우저 자동 오픈. Windows 작업 스케줄러로
평일 16:30 등록하면 로컬에서도 자동화됩니다:

```bat
schtasks /create /tn "JP Screener" /tr "py C:\경로\jp-screener\screener.py" /sc weekly /d MON,TUE,WED,THU,FRI /st 16:30
```

---

## 시그널 정의 (screener.py 상단 CONFIG에서 임계값 조정)

| 구분 | 시그널 | 조건 | 키 |
|---|---|---|---|
| 단기 | 급증 | 거래량 10일 평균 대비 2.5배↑ | `RVOL_SPIKE` |
| 단기 | 5MA/20MA돌파 | 당일 저가≤이평선≤종가 & 상승 | — |
| 단기 | 신고가권 | 52주 고가의 98%↑ | `NEAR_HIGH_RATIO` |
| 단기 | 갭업 | 시가 갭 +3%↑ | `GAP_UP_PCT` |
| 중장기 | GC직후 | 20일선이 200일선을 갓 상향(2% 이내) | `GC_MAX_SPREAD` |
| 중장기 | 200탈환 | 200일선 회복 직후 | `RECLAIM_MAX` |
| 중장기 | 정배열 | 주가>5>20>200 & 이격 20% 이내 | `TREND_MAX_EXT` |

시그널 탭의 거래대금 하한(기본 1억엔)은 대시보드 안에서 변경 가능 —
0.1억까지 내리면 초소형 '숨은 보석'까지 훑을 수 있습니다.

## 대시보드 사용법
탭(단기/중장기/전 종목) · 33업종 히트스트립 클릭=업종 필터 ·
컬럼 헤더 클릭=정렬 · 시그널 칩 복수 선택=OR ·
색상은 일본·한국식(빨강=상승, 파랑=하락).

## 한계
- 무료 스냅샷 기반이라 "돌파" 판정은 당일 저가/종가 근사치 (정밀 판정은 v2 J-Quants에서)
- JPX 종목일람은 월 1회 갱신 → 직전 신규상장주는 'その他'로 표시될 수 있음
- 결과는 참고 자료이며 투자 판단·책임은 본인에게 있습니다

## v2 로드맵
1. J-Quants 라이트(월 1,650엔) → 히스토리 기반 정밀 판정 + 스파크라인
2. TDnet 적시공시 탭 (상방수정·자사주매입·증배 태깅)
3. 상위 시그널 텔레그램 봇 푸시
4. history 축적분으로 시그널 적중률 백테스트
