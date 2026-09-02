# -*- coding: utf-8 -*-
"""UI 문구 · 업종명 한국어/일본어 사전"""

UI = {
    "ko": dict(
        lang_name="한국어", other_lang="日本語",
        tab_short="단기 시그널", tab_long="중장기 시그널", tab_fund="가치·펀더", tab_all="전 종목",
        strip_label="업종별 당일 등락 중앙값 (탭하면 업종 필터)",
        search_ph="코드 · 종목명 검색", hint="행 클릭 → 트레이딩뷰 차트",
        preset_label="표시 항목", preset_tech="테크니컬", preset_fin="재무", preset_all="전체",
        preset_growth="성장", tab_growth="성장주",
        c_revq="매출YoY(분기)", c_revy="매출YoY(연간)", c_revt="매출YoY(TTM)",
        c_revqq="매출QoQ", c_cagr="매출5년CAGR", c_epsq="EPS YoY(분기)",
        c_opm="영업이익률%", c_roic="ROIC%", c_psr="PSR", c_de="부채비율",
        c_inflow="유입배", c_score="점수", c_peg="PEG", c_ytd="연초대비%", c_hi52="52주고가", c_lo52="52주저가",
        c_pos52="52주위치%", c_perfy="1년%",
        s_growth="고성장", s_accel="이익가속", s_garp="저평가성장", s_inflow="지속유입",
        wl_sel="선택 {n}종목 담기", wl_dl="관심종목 내보내기", wl_all="필터 전체 담기",
        wl_clear="선택 해제", wl_hint="체크 → 내보내기 → 트레이딩뷰 관심목록에서 가져오기",
        foot_toggle="시그널 판정 기준 자세히 보기",
        tab_dis="공시", dis_none="표시할 공시가 없습니다 (오늘·전영업일 기준)",
        dis_hint="행 클릭 → 공시 PDF · 사업내용 클릭 → 회사 소개",
        dis_all="전체", nav_bt="📊 성과분석", nav_rank="📈 순위 추이", nav_dash="🌐 글로벌 대시보드", nav_study="🧠 연상 사고",
        biz_loading="회사 프로필 불러오는 중…",
        biz_none="서술형 소개 수집 대기 중 — 시총 상위부터 매일 자동 수집됩니다 (영문)",
        kw_labels=["상방수정","하방수정","증배·복배","감배·무배","자사주","주식분할",
                   "결산","실적예상","배당예상","제휴","TOB","월차"],
        meta_pre="데이터 기준", meta_up="▲빨강=상승", meta_dn="▼파랑=하락", meta_stocks="종목",
        prev="◀ 이전", next="다음 ▶", stat="필터 결과 {n}종목",
        c_code="코드", c_name="종목명", c_sector="업종", c_seg="구분", c_sig="시그널",
        c_price="주가", c_chg="등락%", c_gap="갭%", c_ext="이격200%", c_vol="거래량",
        c_rsi="RSI", c_w="1주%", c_m="1개월%", c_3m="3개월%", c_per="PER", c_pbr="PBR",
        c_eps="EPS", c_roe="ROE%", c_div="배당%", c_eq="자기자본%", c_macd="MACD-H", c_biz="사업내용",
        s_spike="급증", s_x5="5MA돌파", s_x20="20MA돌파", s_high="신고가권", s_gap="갭업",
        s_over="과매도반등", s_gc="GC직후", s_rec="200탈환", s_trend="정배열", s_macd="MACD골든",
        s_value="저평가", s_dividend="고배당", s_qual="우량",
        foot=("단기: <b>급증</b> 거래량 10일 평균 대비 2.5배↑ · <b>5MA/20MA돌파</b> 당일 상향 통과 · "
              "<b>신고가권</b> 52주 고가 98%↑ · <b>갭업</b> +3%↑ · <b>과매도반등</b> RSI≤32에서 반등<br>"
              "중장기: <b>GC직후</b> 20일선이 200일선을 갓 상향 · <b>200탈환</b> 200일선 회복 직후 · "
              "<b>정배열</b> 주가&gt;5&gt;20&gt;200 · <b>MACD골든</b> 시그널선 상향 직후<br>"
              "가치·펀더: <b>저평가</b> PER≤10 &amp; PBR≤1 · <b>고배당</b> 배당수익률 4%↑ · "
              "<b>우량</b> ROE≥15% &amp; 자기자본비율≥50%<br>"
              "성장: <b>고성장</b> 매출 YoY(분기)≥20% &amp; 5년CAGR≥10% · "
              "<b>이익가속</b> EPS YoY≥10% &amp; 매출 성장의 1.5배↑ · "
              "<b>저평가성장</b> PSR≤2 &amp; 매출 YoY≥10% &amp; 영업이익률≥5%<br>"
              "자금: <b>지속유입</b> 5일 매매대금이 60일 평균의 1.3배↑ 3일 연속 · "
              "<b>유입배</b>=5일/60일 매매대금 비율 · <b>점수</b>=발생 시그널 가중합<br>"
              "지표는 스냅샷 기반 근사치이며 매매 판단의 보조 자료입니다. 데이터: TradingView{credit}"),
    ),
    "ja": dict(
        lang_name="日本語", other_lang="한국어",
        tab_short="短期シグナル", tab_long="中長期シグナル", tab_fund="バリュー・財務", tab_all="全銘柄",
        strip_label="業種別 当日騰落率の中央値（タップで業種フィルタ）",
        search_ph="コード・銘柄名で検索", hint="行をクリック → TradingViewチャート",
        preset_label="表示項目", preset_tech="テクニカル", preset_fin="財務", preset_all="すべて",
        preset_growth="成長", tab_growth="成長株",
        c_revq="売上YoY(四半期)", c_revy="売上YoY(通期)", c_revt="売上YoY(TTM)",
        c_revqq="売上QoQ", c_cagr="売上5年CAGR", c_epsq="EPS YoY(四半期)",
        c_opm="営業利益率%", c_roic="ROIC%", c_psr="PSR", c_de="負債比率",
        c_inflow="流入倍", c_score="スコア", c_peg="PEG", c_ytd="年初来%", c_hi52="52週高値", c_lo52="52週安値",
        c_pos52="52週位置%", c_perfy="1年%",
        s_growth="高成長", s_accel="利益加速", s_garp="割安成長", s_inflow="継続流入",
        wl_sel="選択 {n}銘柄", wl_dl="ウォッチリスト書き出し", wl_all="絞込み全件を選択",
        wl_clear="選択解除", wl_hint="チェック → 書き出し → TradingViewのウォッチリストへインポート",
        foot_toggle="シグナル判定基準を詳しく見る",
        tab_dis="開示", dis_none="表示する開示はありません（当日・前営業日）",
        dis_hint="行クリック → 開示PDF · 事業内容クリック → 会社概要",
        dis_all="すべて", nav_bt="📊 パフォーマンス", nav_rank="📈 ランキング推移", nav_dash="🌐 グローバル指標", nav_study="🧠 連想思考",
        biz_loading="会社プロフィール読み込み中…",
        biz_none="会社概要は時価総額上位から毎日自動収集中です（英文）",
        kw_labels=["上方修正","下方修正","増配・復配","減配・無配","自社株","株式分割",
                   "決算","業績予想","配当予想","提携","TOB","月次"],
        meta_pre="データ基準", meta_up="▲赤=上昇", meta_dn="▼青=下落", meta_stocks="銘柄",
        prev="◀ 前へ", next="次へ ▶", stat="該当 {n}銘柄",
        c_code="コード", c_name="銘柄名", c_sector="業種", c_seg="区分", c_sig="シグナル",
        c_price="株価", c_chg="騰落%", c_gap="ギャップ%", c_ext="200MA乖離%", c_vol="出来高",
        c_rsi="RSI", c_w="1週%", c_m="1ヶ月%", c_3m="3ヶ月%", c_per="PER", c_pbr="PBR",
        c_eps="EPS", c_roe="ROE%", c_div="配当%", c_eq="自己資本%", c_macd="MACD-H", c_biz="事業内容",
        s_spike="出来高急増", s_x5="5MA突破", s_x20="20MA突破", s_high="高値圏", s_gap="ギャップアップ",
        s_over="売られすぎ反発", s_gc="GC直後", s_rec="200MA回復", s_trend="パーフェクトオーダー",
        s_macd="MACDゴールデン", s_value="割安", s_dividend="高配当", s_qual="優良",
        foot=("短期: <b>出来高急増</b> 10日平均比2.5倍↑ · <b>5MA/20MA突破</b> 当日上抜け · "
              "<b>高値圏</b> 52週高値の98%↑ · <b>ギャップアップ</b> +3%↑ · <b>売られすぎ反発</b> RSI≤32で反発<br>"
              "中長期: <b>GC直後</b> 20MAが200MAを上抜けた直後 · <b>200MA回復</b> 回復直後 · "
              "<b>パーフェクトオーダー</b> 株価&gt;5&gt;20&gt;200 · <b>MACDゴールデン</b> シグナル線上抜け直後<br>"
              "バリュー・財務: <b>割安</b> PER≤10 かつ PBR≤1 · <b>高配当</b> 配当利回り4%↑ · "
              "<b>優良</b> ROE≥15% かつ 自己資本比率≥50%<br>"
              "成長: <b>高成長</b> 売上YoY(四半期)≥20% かつ 5年CAGR≥10% · "
              "<b>利益加速</b> EPS YoY≥10% かつ 売上成長の1.5倍↑ · "
              "<b>割安成長</b> PSR≤2 かつ 売上YoY≥10% かつ 営業利益率≥5%<br>"
              "資金: <b>継続流入</b> 5日売買代金が60日平均の1.3倍↑ 3日連続 · "
              "<b>流入倍</b>=5日/60日の売買代金比 · <b>スコア</b>=点灯シグナルの加重合計<br>"
              "指標はスナップショットに基づく概算値であり、投資判断の補助資料です。データ: TradingView{credit}"),
    ),
}

MARKET_I18N = {
    "jp": dict(ko=dict(title="JP<span>스크리너</span>", nav="🇯🇵 일본", label="도쿄증권거래소",
                       segs=["프라임", "스탠다드", "그로스"], turn="대금(억엔)", mcap="시총(억엔)", ebitda="EBITDA(억)"),
               ja=dict(title="JP<span>スクリーナー</span>", nav="🇯🇵 日本", label="東証",
                       segs=["プライム", "スタンダード", "グロース"], turn="売買代金(億円)", mcap="時価総額(億円)", ebitda="EBITDA(億)")),
    "kr": dict(ko=dict(title="KR<span>스크리너</span>", nav="🇰🇷 한국", label="코스피·코스닥",
                       segs=["코스피", "코스닥", "코넥스"], turn="대금(억원)", mcap="시총(억원)", ebitda="EBITDA(억)"),
               ja=dict(title="KR<span>スクリーナー</span>", nav="🇰🇷 韓国", label="KOSPI・KOSDAQ",
                       segs=["KOSPI", "KOSDAQ", "KONEX"], turn="売買代金(億W)", mcap="時価総額(億W)", ebitda="EBITDA(億)")),
    "us": dict(ko=dict(title="US<span>스크리너</span>", nav="🇺🇸 미국", label="NYSE·나스닥·AMEX",
                       segs=["NYSE", "NASDAQ", "AMEX"], turn="대금($M)", mcap="시총($B)", ebitda="EBITDA($M)"),
               ja=dict(title="US<span>スクリーナー</span>", nav="🇺🇸 米国", label="NYSE・NASDAQ・AMEX",
                       segs=["NYSE", "NASDAQ", "AMEX"], turn="売買代金($M)", mcap="時価総額($B)", ebitda="EBITDA($M)")),
}

# 거래대금 필터: 시장별 임계값 + 언어별 단위
MIN_FILTER = {
    "jp": dict(values=[0, 0.1, 0.5, 1, 5, 10, 50], unit=dict(ko="억엔", ja="億円")),
    "kr": dict(values=[0, 0.5, 1, 5, 10, 50, 100], unit=dict(ko="억원", ja="億W")),
    "us": dict(values=[0, 0.1, 0.5, 1, 5, 10, 50], unit=dict(ko="$M", ja="$M")),
}
TURNOVER_LABEL = dict(ko="거래대금", ja="売買代金")
ALL_LABEL = dict(ko="전체", ja="すべて")


def min_options(mkey, lang):
    """[[값, 표시라벨], ...] — 0은 '전체'."""
    m = MIN_FILTER[mkey]
    unit = m["unit"][lang]
    out = [[0, f'{TURNOVER_LABEL[lang]}: {ALL_LABEL[lang]}']]
    for v in m["values"][1:]:
        n = f"{v:g}"
        out.append([v, f"≥ {n}{unit}" if unit != "$M" else f"≥ ${n}M"])
    return out


SEG_JA = {"프라임": "プライム", "스탠다드": "スタンダード", "그로스": "グロース",
          "코스피": "KOSPI", "코스닥": "KOSDAQ", "코넥스": "KONEX", "기타": "その他"}

SECTOR = {  # TradingView sector → (ko, ja)
    "Commercial Services": ("상업서비스", "商業サービス"), "Communications": ("통신", "通信"),
    "Consumer Durables": ("내구소비재", "耐久消費財"), "Consumer Non-Durables": ("필수소비재", "生活必需品"),
    "Consumer Services": ("소비자서비스", "消費者サービス"), "Distribution Services": ("유통", "流通"),
    "Electronic Technology": ("전자·반도체", "電子・半導体"), "Energy Minerals": ("에너지", "エネルギー"),
    "Finance": ("금융", "金融"), "Government": ("공공", "公共"), "Health Services": ("의료서비스", "医療サービス"),
    "Health Technology": ("제약·바이오", "製薬・バイオ"), "Industrial Services": ("산업서비스", "産業サービス"),
    "Miscellaneous": ("기타", "その他"), "Non-Energy Minerals": ("소재·금속", "素材・金属"),
    "Process Industries": ("화학·공정", "化学・素材加工"), "Producer Manufacturing": ("기계·제조", "機械・製造"),
    "Retail Trade": ("소매", "小売"), "Technology Services": ("IT서비스·SW", "ITサービス・SW"),
    "Transportation": ("운송", "運輸"), "Utilities": ("유틸리티", "公益"),
}

INDUSTRY = {  # TradingView industry → (ko, ja)
    "Advertising/Marketing Services": ("광고·마케팅 서비스", "広告・マーケティング"),
    "Aerospace & Defense": ("항공우주·방산", "航空宇宙・防衛"),
    "Agricultural Commodities/Milling": ("농산물·제분", "農産物・製粉"),
    "Air Freight/Couriers": ("항공화물·특송", "航空貨物・宅配"),
    "Airlines": ("항공사", "航空"),
    "Alternative Power Generation": ("신재생 발전", "再生可能エネルギー発電"),
    "Aluminum": ("알루미늄", "アルミ"),
    "Apparel/Footwear": ("의류·신발 제조", "アパレル・靴"),
    "Apparel/Footwear Retail": ("의류·신발 소매", "アパレル・靴 小売"),
    "Auto Parts: OEM": ("자동차 부품(OEM)", "自動車部品(OEM)"),
    "Automotive Aftermarket": ("자동차 애프터마켓", "自動車アフターマーケット"),
    "Beverages: Alcoholic": ("주류", "酒類"),
    "Beverages: Non-Alcoholic": ("음료(비주류)", "清涼飲料"),
    "Biotechnology": ("바이오테크", "バイオテクノロジー"),
    "Broadcasting": ("방송", "放送"),
    "Building Products": ("건축자재", "建築資材"),
    "Cable/Satellite TV": ("케이블·위성방송", "ケーブル・衛星放送"),
    "Casinos/Gaming": ("카지노·게이밍", "カジノ・ゲーミング"),
    "Catalog/Specialty Distribution": ("카탈로그·전문 유통", "通販・専門流通"),
    "Chemicals: Agricultural": ("농업용 화학(비료·농약)", "農業化学(肥料・農薬)"),
    "Chemicals: Major Diversified": ("종합화학", "総合化学"),
    "Chemicals: Specialty": ("정밀·특수화학", "精密・特殊化学"),
    "Coal": ("석탄", "石炭"),
    "Commercial Printing/Forms": ("상업인쇄", "商業印刷"),
    "Computer Communications": ("네트워크 장비", "ネットワーク機器"),
    "Computer Peripherals": ("컴퓨터 주변기기", "コンピュータ周辺機器"),
    "Computer Processing Hardware": ("컴퓨터·서버 하드웨어", "コンピュータ・サーバー"),
    "Construction Materials": ("건설소재(시멘트 등)", "建設資材(セメント等)"),
    "Consumer Sundries": ("생활용품", "生活雑貨"),
    "Containers/Packaging": ("포장·용기", "包装・容器"),
    "Contract Drilling": ("시추 서비스", "掘削サービス"),
    "Data Processing Services": ("데이터 처리 서비스", "データ処理サービス"),
    "Department Stores": ("백화점", "百貨店"),
    "Discount Stores": ("할인점·대형마트", "ディスカウントストア"),
    "Drugstore Chains": ("드럭스토어", "ドラッグストア"),
    "Electric Utilities": ("전력", "電力"),
    "Electrical Products": ("전기제품·전기설비", "電気機器・電設"),
    "Electronic Components": ("전자부품", "電子部品"),
    "Electronic Equipment/Instruments": ("전자장비·계측기", "電子機器・計測器"),
    "Electronic Production Equipment": ("반도체·전자 생산장비", "半導体・電子製造装置"),
    "Electronics Distributors": ("전자부품 유통", "電子部品商社"),
    "Electronics/Appliance Stores": ("가전 유통", "家電量販"),
    "Electronics/Appliances": ("가전제품", "家電"),
    "Engineering & Construction": ("엔지니어링·건설", "エンジニアリング・建設"),
    "Environmental Services": ("환경·폐기물 처리", "環境・廃棄物処理"),
    "Finance/Rental/Leasing": ("여신·렌탈·리스", "ファイナンス・リース"),
    "Financial Conglomerates": ("종합금융지주", "金融コングロマリット"),
    "Financial Publishing/Services": ("금융정보 서비스", "金融情報サービス"),
    "Food Distributors": ("식품 유통", "食品卸"),
    "Food Retail": ("식품 소매·슈퍼", "食品小売・スーパー"),
    "Food: Major Diversified": ("종합식품", "総合食品"),
    "Food: Meat/Fish/Dairy": ("육류·수산·유제품", "食肉・水産・乳製品"),
    "Food: Specialty/Candy": ("제과·특수식품", "菓子・特殊食品"),
    "Forest Products": ("임산물·목재", "林産・木材"),
    "Gas Distributors": ("가스 공급", "ガス供給"),
    "General Government": ("공공기관", "政府機関"),
    "Home Furnishings": ("가구·홈퍼니싱", "家具・インテリア"),
    "Home Improvement Chains": ("홈센터", "ホームセンター"),
    "Homebuilding": ("주택건설", "住宅建設"),
    "Hospital/Nursing Management": ("병원·요양 운영", "病院・介護運営"),
    "Hotels/Resorts/Cruise lines": ("호텔·리조트·크루즈", "ホテル・リゾート・クルーズ"),
    "Household/Personal Care": ("생활용품·퍼스널케어", "日用品・パーソナルケア"),
    "Industrial Conglomerates": ("산업 복합기업", "産業コングロマリット"),
    "Industrial Machinery": ("산업기계", "産業機械"),
    "Industrial Specialties": ("산업용 특수제품", "産業用特殊製品"),
    "Information Technology Services": ("IT 서비스·SI", "ITサービス・SI"),
    "Insurance Brokers/Services": ("보험중개·서비스", "保険仲介・サービス"),
    "Integrated Oil": ("종합 석유", "総合石油"),
    "Internet Retail": ("인터넷 소매(EC)", "ネット通販(EC)"),
    "Internet Software/Services": ("인터넷 소프트웨어·서비스", "インターネットサービス"),
    "Investment Banks/Brokers": ("증권·투자은행", "証券・投資銀行"),
    "Investment Managers": ("자산운용", "資産運用"),
    "Investment Trusts/Mutual Funds": ("투자신탁·펀드", "投資信託"),
    "Life/Health Insurance": ("생명·건강보험", "生命・医療保険"),
    "Major Banks": ("대형은행", "大手銀行"),
    "Major Telecommunications": ("종합 통신", "総合通信"),
    "Managed Health Care": ("건강보험 관리", "マネージドケア"),
    "Marine Shipping": ("해운", "海運"),
    "Media Conglomerates": ("미디어 복합기업", "メディアコングロマリット"),
    "Medical Distributors": ("의료기기·의약품 유통", "医療品卸"),
    "Medical Specialties": ("의료기기·전문의료", "医療機器・専門医療"),
    "Medical/Nursing Services": ("의료·간병 서비스", "医療・介護サービス"),
    "Metal Fabrication": ("금속가공", "金属加工"),
    "Miscellaneous": ("기타", "その他"),
    "Miscellaneous Commercial Services": ("기타 상업서비스", "その他商業サービス"),
    "Miscellaneous Manufacturing": ("기타 제조", "その他製造"),
    "Motor Vehicles": ("완성차", "自動車(完成車)"),
    "Movies/Entertainment": ("영화·엔터테인먼트", "映画・エンタメ"),
    "Multi-Line Insurance": ("종합보험", "総合保険"),
    "Office Equipment/Supplies": ("사무기기·용품", "事務機器・用品"),
    "Oil & Gas Pipelines": ("석유·가스 파이프라인", "石油・ガスパイプライン"),
    "Oil & Gas Production": ("석유·가스 생산", "石油・ガス生産"),
    "Oil Refining/Marketing": ("정유·석유판매", "石油精製・販売"),
    "Oilfield Services/Equipment": ("유전 서비스·장비", "油田サービス・機器"),
    "Other Consumer Services": ("기타 소비자서비스", "その他消費者サービス"),
    "Other Consumer Specialties": ("기타 소비재", "その他消費財"),
    "Other Metals/Minerals": ("기타 금속·광물", "その他金属・鉱物"),
    "Other Transportation": ("기타 운송", "その他運輸"),
    "Packaged Software": ("패키지 소프트웨어", "パッケージソフト"),
    "Personnel Services": ("인재·인력 서비스", "人材サービス"),
    "Pharmaceuticals: Generic": ("제네릭 의약품", "ジェネリック医薬品"),
    "Pharmaceuticals: Major": ("대형 제약", "大手製薬"),
    "Pharmaceuticals: Other": ("기타 제약", "その他製薬"),
    "Precious Metals": ("귀금속", "貴金属"),
    "Property/Casualty Insurance": ("손해보험", "損害保険"),
    "Publishing: Books/Magazines": ("출판(도서·잡지)", "出版(書籍・雑誌)"),
    "Publishing: Newspapers": ("신문", "新聞"),
    "Pulp & Paper": ("펄프·제지", "パルプ・紙"),
    "Railroads": ("철도", "鉄道"),
    "Real Estate Development": ("부동산 개발", "不動産開発"),
    "Real Estate Investment Trusts": ("리츠(REIT)", "REIT"),
    "Recreational Products": ("레저용품", "レジャー用品"),
    "Regional Banks": ("지방은행", "地方銀行"),
    "Restaurants": ("외식·레스토랑", "外食"),
    "Savings Banks": ("저축은행", "貯蓄銀行"),
    "Semiconductors": ("반도체", "半導体"),
    "Services to the Health Industry": ("의료산업 지원서비스", "医療産業向けサービス"),
    "Specialty Insurance": ("특종보험", "特殊保険"),
    "Specialty Stores": ("전문점", "専門店"),
    "Specialty Telecommunications": ("특화 통신", "特化型通信"),
    "Steel": ("철강", "鉄鋼"),
    "Telecommunications Equipment": ("통신장비", "通信機器"),
    "Textiles": ("섬유", "繊維"),
    "Tobacco": ("담배", "たばこ"),
    "Tools & Hardware": ("공구·하드웨어", "工具・金物"),
    "Trucking": ("육상운송·트럭", "陸運・トラック"),
    "Trucks/Construction/Farm Machinery": ("트럭·건설·농기계", "トラック・建機・農機"),
    "Water Utilities": ("수도", "水道"),
    "Wholesale Distributors": ("종합 도매·상사", "総合卸・商社"),
    "Wireless Telecommunications": ("무선통신", "無線通信"),
}


# ─────────── 성과분석(백테스트) 페이지 문구 ───────────
BT_UI = {
    "ko": dict(
        title='시그널 <span>성과 분석</span>', page_title="시그널 성과 분석",
        back="← 스크리너로", gen="생성",
        lead="시그널에 걸린 종목이 이후 실제로 어떻게 움직였는지 (거래대금 하한 적용, 시장평균 대비)",
        days="일", obs="회 관측",
        h1="+1일", h5="+5일", h20="+20일",
        col_sig="시그널", col_n="표본", col_win="승률", col_avg="평균수익",
        col_med="중앙값", col_exc="시장대비", col_minmax="최고/최저",
        acc_title="데이터 축적 중입니다 (현재 {n}일)",
        acc_body=("매 영업일 종가판 실행마다 스냅샷이 자동으로 쌓입니다.<br>"
                  "· 스냅샷 2일차 → <b>+1일 수익률</b> 첫 집계 · 6일차 → +5일 · 21일차 → +20일<br>"
                  "한두 달 뒤에는 \"어떤 시그널이 실제로 먹혔는가\"를 표본 수백~수천 건으로 평가할 수 있습니다."),
        none="이 구간(+{h}일)은 아직 관측치가 없습니다 — 스냅샷 {need}일 이상 필요.",
        howto=("읽는 법: <b>시장대비</b>가 +면 그 시그널이 시장평균보다 잘 갔다는 뜻입니다. "
               "표본이 적을 때(수십 건 이하)는 우연일 수 있으니 표본 수를 함께 보세요."),
        foot=("승률 = 수익률 &gt; 0 비율 · 시장대비 = 같은 기간 유니버스 평균수익 차감(초과수익) · "
              "표본 = (시그널 발생 종목 × 관측일) 누적 · 스냅샷은 매 영업일 종가판에서 자동 축적 · "
              "과거 성과는 미래 수익을 보장하지 않으며 참고 자료입니다."),
        markets=dict(jp="🇯🇵 일본", kr="🇰🇷 한국", us="🇺🇸 미국"),
        other_lang="日本語",
    ),
    "ja": dict(
        title='シグナル <span>パフォーマンス分析</span>', page_title="シグナル・パフォーマンス分析",
        back="← スクリーナーへ", gen="生成",
        lead="シグナルが点灯した銘柄がその後どう動いたか（売買代金の下限を適用・市場平均との比較）",
        days="日", obs="回 観測",
        h1="+1日", h5="+5日", h20="+20日",
        col_sig="シグナル", col_n="サンプル", col_win="勝率", col_avg="平均リターン",
        col_med="中央値", col_exc="市場比", col_minmax="最高/最低",
        acc_title="データ蓄積中です（現在 {n}日）",
        acc_body=("営業日ごとの引け後実行でスナップショットが自動的に蓄積されます。<br>"
                  "・2日目 → <b>+1日リターン</b>の初集計 ・6日目 → +5日 ・21日目 → +20日<br>"
                  "1〜2ヶ月後には「どのシグナルが実際に機能したか」を数百〜数千件のサンプルで評価できます。"),
        none="この期間（+{h}日）はまだ観測値がありません — スナップショットが{need}日分必要です。",
        howto=("見方: <b>市場比</b>がプラスなら、そのシグナルが市場平均を上回ったという意味です。"
               "サンプルが少ない場合（数十件以下）は偶然の可能性があるため、サンプル数も併せて確認してください。"),
        foot=("勝率 = リターン &gt; 0 の比率 ・ 市場比 = 同期間のユニバース平均リターンを差し引いた超過リターン ・ "
              "サンプル =（シグナル点灯銘柄 × 観測日）の累計 ・ スナップショットは各営業日の引け後に自動蓄積 ・ "
              "過去の成績は将来の収益を保証するものではなく、参考資料です。"),
        markets=dict(jp="🇯🇵 日本", kr="🇰🇷 韓国", us="🇺🇸 米国"),
        other_lang="한국어",
    ),
}

SIGNAL_I18N = {
    "sig_spike": ("급증", "出来高急増"), "sig_x5": ("5MA돌파", "5MA突破"),
    "sig_x20": ("20MA돌파", "20MA突破"), "sig_high": ("신고가권", "高値圏"),
    "sig_gap": ("갭업", "ギャップアップ"), "sig_oversold": ("과매도반등", "売られすぎ反発"),
    "sig_gc": ("GC직후", "GC直後"), "sig_reclaim": ("200탈환", "200MA回復"),
    "sig_trend": ("정배열", "パーフェクトオーダー"), "sig_macd": ("MACD골든", "MACDゴールデン"),
    "sig_value": ("저평가", "割安"), "sig_div": ("고배당", "高配当"), "sig_qual": ("우량", "優良"),
    "sig_growth": ("고성장", "高成長"), "sig_accel": ("이익가속", "利益加速"),
    "sig_garp": ("저평가성장", "割安成長"), "sig_inflow": ("지속유입", "継続流入"), "grp_growth": ("성장(아무거나)", "成長(いずれか)"),
    "sig_growth": ("고성장", "高成長"), "sig_accel": ("이익가속", "利益加速"),
    "sig_garp": ("저평가성장", "割安成長"), "sig_inflow": ("지속유입", "継続流入"), "grp_growth": ("성장(아무거나)", "成長(いずれか)"),
    "grp_short": ("단기(아무거나)", "短期(いずれか)"), "grp_long": ("중장기(아무거나)", "中長期(いずれか)"),
    "grp_fund": ("펀더(아무거나)", "財務(いずれか)"), "grp_multi": ("시그널 2개 이상", "シグナル2つ以上"),
}


# ─────────── 거래대금 순위 추이 페이지 ───────────
RANK_UI = {
    "ko": dict(
        title='시장 <span>순위 추이</span>', page_title="시장 순위 추이",
        back="← 스크리너로", gen="생성", other_lang="日本語",
        lead="매 영업일 상위 100위의 순위 변화 (위쪽이 상위) · 거래대금=자금 쏠림 / 시가총액=덩치 판도",
        days="일", rank_unit="위", scroll_hint="← 그래프를 좌우로 밀어 보세요",
        col_rank="순위", col_code="코드", col_name="종목명",
        col_delta="전일대비", col_value="거래대금", col_mcap="시가총액",
        col_chg="증감%", col_best="최고순위",
        m_value="💰 거래대금", m_mcap="🏛 시가총액",
        new_in="신규",
        markets=dict(jp="🇯🇵 일본", kr="🇰🇷 한국", us="🇺🇸 미국"),
        acc_title="데이터 축적 중입니다 (현재 {n}일)",
        acc_body=("매 영업일 종가판 실행마다 순위 스냅샷이 자동으로 쌓입니다.<br>"
                  "2일차부터 선이 그려지고, 2~4주가 지나면 자금이 어느 종목·업종으로 "
                  "옮겨다니는지 흐름이 보입니다."),
        howto=("선이나 표의 행을 클릭하면 그 종목만 강조됩니다. "
               "선이 <b>위로 올라가면 순위 상승</b>(자금 유입), 아래로 내려가면 관심 이탈입니다. "
               "새로 100위 안에 진입한 종목은 선이 중간부터 시작합니다."),
        foot=("거래대금 상위 100위를 매 영업일 종가 기준으로 집계 · 순위는 1위가 위쪽 · "
              "최근 60영업일까지 표시 · 최신일 상위 20종목만 색선으로 강조 · "
              "휴장일 스냅샷은 자동 제외됩니다."),
    ),
    "ja": dict(
        title='市場 <span>ランキング推移</span>', page_title="市場ランキング推移",
        back="← スクリーナーへ", gen="生成", other_lang="한국어",
        lead="各営業日の上位100位の順位変化（上が上位）・売買代金=資金の集中 / 時価総額=規模の勢力図",
        days="日", rank_unit="位", scroll_hint="← グラフを左右にスワイプできます",
        col_rank="順位", col_code="コード", col_name="銘柄名",
        col_delta="前日比", col_value="売買代金", col_mcap="時価総額",
        col_chg="増減%", col_best="最高順位",
        m_value="💰 売買代金", m_mcap="🏛 時価総額",
        new_in="新規",
        markets=dict(jp="🇯🇵 日本", kr="🇰🇷 韓国", us="🇺🇸 米国"),
        acc_title="データ蓄積中です（現在 {n}日）",
        acc_body=("営業日ごとの引け後実行で順位スナップショットが自動的に蓄積されます。<br>"
                  "2日目から線が描かれ、2〜4週間経つと資金がどの銘柄・業種へ移動しているかが見えてきます。"),
        howto=("線または表の行をクリックすると、その銘柄だけが強調されます。"
               "線が<b>上に向かえば順位上昇</b>（資金流入）、下に向かえば関心の離脱です。"
               "新たに100位内に入った銘柄は途中から線が始まります。"),
        foot=("売買代金上位100位を各営業日の引け値基準で集計 ・ 順位は1位が上 ・ "
              "直近60営業日まで表示 ・ 最新日の上位20銘柄のみ色線で強調 ・ "
              "休場日のスナップショットは自動的に除外されます。"),
    ),
}


# ─────────── 컬럼·시그널 도움말 (물음표 아이콘) ───────────
# key: 컬럼/시그널 식별자 → (한국어, 일본어)
HELP = {
    # 컬럼
    "c_chg": ("전일 종가 대비 등락률.", "前日終値比の騰落率。"),
    "c_gap": ("오늘 시가가 어제 종가에서 벌어진 폭. 밤사이 재료를 반영합니다. +3% 이상이면 갭업 시그널.",
              "本日始値と前日終値の差。夜間の材料を反映します。+3%以上でギャップアップ。"),
    "c_ext": ("현재가가 200일선에서 떨어진 정도. 0% 근처는 추세 전환 지점, +100%는 과열 신호.",
              "現在値と200日線の乖離。0%付近は転換点、+100%は過熱シグナル。"),
    "rvol": ("오늘 거래량 ÷ 10일 평균. 2.5배 이상이면 급증. 장중에는 하루치가 덜 차서 낮게 나옵니다.",
             "本日出来高÷10日平均。2.5倍以上で急増。場中は1日分が未完のため低めに出ます。"),
    "c_rsi": ("0~100. 30 이하는 과매도, 70 이상은 과매수로 봅니다.",
              "0〜100。30以下は売られすぎ、70以上は買われすぎ。"),
    "c_pos52": ("52주 최저가를 0%, 최고가를 100%로 놓았을 때 현재 위치. 30%면 밴드 하단에 가깝습니다.",
                "52週安値を0%、高値を100%とした現在位置。30%なら下限寄り。"),
    "c_macd": ("MACD선 − 시그널선. 양수로 바뀌는 순간이 상승 전환 신호로 쓰입니다.",
               "MACD線−シグナル線。プラス転換が上昇シグナルとされます。"),
    "c_per": ("주가 ÷ 주당순이익. 낮을수록 이익 대비 저평가. 적자면 표시되지 않습니다.",
              "株価÷1株利益。低いほど利益比で割安。赤字企業は表示されません。"),
    "c_peg": ("PER ÷ 이익성장률. 1 이하면 성장 대비 싸다고 봅니다. 성장이 없으면 값이 없습니다.",
              "PER÷利益成長率。1以下なら成長比で割安。成長がないと値が出ません。"),
    "c_pbr": ("주가 ÷ 주당순자산. 1 미만은 장부가보다 싸게 거래된다는 뜻.",
              "株価÷1株純資産。1未満は簿価割れ。"),
    "c_roe": ("자기자본 대비 이익률. 15% 이상이면 우량으로 분류합니다.",
              "自己資本利益率。15%以上を優良と分類。"),
    "c_roic": ("투입자본 대비 이익률. ROE보다 부채 착시가 적어 실질 수익성을 봅니다.",
               "投下資本利益率。ROEより負債の影響が少なく実質収益性を示します。"),
    "c_psr": ("시가총액 ÷ 매출. 적자로 PER을 못 쓸 때 성장주 평가에 씁니다.",
              "時価総額÷売上。赤字でPERが使えない成長株の評価に。"),
    "c_eq": ("(총자산−총부채) ÷ 총자산. 높을수록 재무가 안정적입니다. 은행·보험은 낮게 나옵니다.",
             "(総資産−総負債)÷総資産。高いほど財務安定。銀行・保険は低く出ます。"),
    "c_de": ("부채 ÷ 자기자본. 낮을수록 빚 부담이 적습니다.",
             "負債÷自己資本。低いほど借入負担が小さい。"),
    "c_cagr": ("최근 5년간 매출이 연평균 몇 % 성장했는지. 장기 추세를 봅니다.",
               "直近5年の売上の年平均成長率。長期トレンドを見ます。"),
    "c_revq": ("최근 분기 매출을 작년 같은 분기와 비교한 증감률.",
               "直近四半期の売上を前年同期と比較した増減率。"),
    "c_inflow": ("최근 5일 매매대금 ÷ 60일 평균. 1.3 이상이면 평소보다 자금이 몰리는 중. "
                 "데이터가 20일 이상 쌓여야 표시됩니다.",
                 "直近5日の売買代金÷60日平均。1.3以上で資金流入。データ20日以上で表示。"),
    "c_score": ("이 종목에 켜진 시그널 개수의 합. 여러 신호가 겹친 종목을 찾는 용도이며, "
                "점수가 높다고 좋은 종목이라는 뜻은 아닙니다.",
                "点灯したシグナル数の合計。複数シグナルが重なる銘柄を探す用途で、高得点=優良ではありません。"),
    "turn": ("당일 거래된 금액. 이 값이 작으면 사고팔기 어려우니 하한 필터를 쓰세요.",
             "当日の売買代金。小さいと売買しにくいため下限フィルタを推奨。"),
    "mcap": ("발행주식 × 주가. 회사의 시장 평가 규모입니다.",
             "発行済株式×株価。会社の市場規模。"),
    "biz": ("클릭하면 회사 소개 전문이 아래로 펼쳐집니다.",
            "クリックすると会社概要の全文が下に開きます。"),
}

HELP_SIG = {
    "s_spike": ("거래량이 10일 평균의 2.5배 이상. 뭔가 일어나고 있다는 신호.",
                "出来高が10日平均の2.5倍以上。何かが起きている合図。"),
    "s_x5": ("당일 5일선을 아래에서 위로 통과. 단기 반등 시작점.",
             "本日5日線を下から上抜け。短期反発の起点。"),
    "s_x20": ("당일 20일선 상향 통과. 5일선보다 무게 있는 전환 신호.",
              "本日20日線を上抜け。5日線より重みのある転換。"),
    "s_high": ("52주 최고가의 98% 이상. 신고가 경신 직전 구간.",
               "52週高値の98%以上。高値更新の直前圏。"),
    "s_gap": ("시가가 전일 종가보다 3% 이상 높게 시작. 밤사이 재료 발생.",
              "始値が前日終値より3%以上高い。夜間に材料発生。"),
    "s_oversold": ("RSI 32 이하에서 반등 시작. 과매도 구간의 되돌림.",
                   "RSI32以下から反発。売られすぎからの戻り。"),
    "s_gc": ("20일선이 200일선을 갓 넘어섬(골든크로스). 장기 추세 전환 신호.",
             "20日線が200日線を上抜けた直後(ゴールデンクロス)。"),
    "s_reclaim": ("200일선을 회복한 직후. 장기 하락 추세에서 벗어나는 지점.",
                  "200日線を回復した直後。長期下降からの脱出点。"),
    "s_trend": ("주가 > 5일선 > 20일선 > 200일선. 상승 추세가 정렬된 상태(과열 제외).",
                "株価>5日>20日>200日。上昇トレンドが揃った状態。"),
    "s_macd": ("MACD가 시그널선을 갓 상향 돌파. 모멘텀 전환.",
               "MACDがシグナル線を上抜けた直後。モメンタム転換。"),
    "s_value": ("PER 10 이하이면서 PBR 1 이하. 이익·자산 양쪽에서 싼 상태.",
                "PER10以下かつPBR1以下。利益・資産の両面で割安。"),
    "s_dividend": ("배당수익률 4% 이상. 배당성향도 함께 확인하세요.",
                   "配当利回り4%以上。配当性向も併せて確認を。"),
    "s_qual": ("ROE 15% 이상 & 자기자본비율 50% 이상. 잘 벌면서 빚이 적은 회사.",
               "ROE15%以上かつ自己資本比率50%以上。稼ぐ力があり借金が少ない。"),
    "s_growth": ("분기 매출 20%↑ & 5년 연평균 10%↑. 단기·장기 모두 성장 중.",
                 "四半期売上20%↑かつ5年平均10%↑。短期・長期とも成長。"),
    "s_accel": ("EPS 성장이 매출 성장의 1.5배 이상. 이익률이 개선되는 국면.",
                "EPS成長が売上成長の1.5倍以上。利益率が改善する局面。"),
    "s_garp": ("PSR 2 이하 & 매출 10%↑ & 영업이익률 5%↑. 성장하면서도 비싸지 않은 상태.",
               "PSR2以下かつ売上10%↑かつ営業利益率5%↑。成長かつ割高でない。"),
    "s_inflow": ("유입배 1.3 이상이 3일 연속. 하루 반짝이 아니라 자금이 계속 들어오는 중.",
                 "流入倍1.3以上が3日連続。一時的でなく資金が継続流入。"),
}


# ─────────── BTC 실시간 배너 (BTC-DESK 연동) ───────────
# 같은 오리진(ocw-1027.github.io)이라 CORS 불필요.
# 초기값은 btc.json, 이후 OKX WebSocket으로 초 단위 갱신.
BTC_URL = "https://ocw-1027.github.io/BTC-DESK/"
BTC_LABEL = {"ko": "₿ BTC 데스크", "ja": "₿ BTCデスク"}


def btc_link(lang, cls="btc"):
    """상단바에 넣을 앵커 태그."""
    return (f'<a href="{BTC_URL}" target="_blank" rel="noopener" class="{cls}">'
            f'{BTC_LABEL[lang]} <b id="btcNav">—</b></a>')


BTC_CSS = """
a.btc{color:var(--amber);border-color:rgba(255,178,36,.45);background:var(--surface2)}
a.btc:hover{background:var(--amber);color:#2a1f05}
a.btc b{font-variant-numeric:tabular-nums;font-weight:800;margin-left:2px}
a.btc b.up{color:var(--up)} a.btc b.down{color:var(--down)}
"""

BTC_JS = """
<script>
(function () {
  var el = document.getElementById('btcNav');
  if (!el) return;
  var prev = null, ws = null, poll = null, tries = 0;

  function show(px) {
    if (!isFinite(px) || px <= 0) return;
    el.textContent = '$' + Math.round(px).toLocaleString('en-US');
    if (prev != null && px !== prev) el.className = px > prev ? 'up' : 'down';
    prev = px;
  }
  function startPoll() {
    if (poll) return;
    poll = setInterval(function () {
      fetch('https://www.okx.com/api/v5/market/ticker?instId=BTC-USDT-SWAP')
        .then(function (r) { return r.json(); })
        .then(function (j) { var d = j.data && j.data[0]; if (d) show(parseFloat(d.last)); })
        .catch(function () {});
    }, 10000);
  }
  function connect() {
    try { ws = new WebSocket('wss://ws.okx.com:8443/ws/v5/public'); }
    catch (e) { startPoll(); return; }
    ws.onopen = function () {
      tries = 0;
      ws.send(JSON.stringify({ op: 'subscribe', args: [{ channel: 'tickers', instId: 'BTC-USDT-SWAP' }] }));
    };
    ws.onmessage = function (e) {
      try {
        var m = JSON.parse(e.data);
        if (m.data && m.data[0] && m.data[0].last) show(parseFloat(m.data[0].last));
      } catch (_) {}
    };
    ws.onerror = function () { try { ws.close(); } catch (_) {} };
    ws.onclose = function () {
      ws = null;
      if (poll) return;
      tries++;
      if (tries <= 3) setTimeout(connect, 2000 * tries); else startPoll();
    };
  }
  fetch('https://ocw-1027.github.io/BTC-DESK/btc.json', { cache: 'no-store' })
    .then(function (r) { return r.json(); })
    .then(function (j) { show(j.price); })
    .catch(function () {});
  document.addEventListener('visibilitychange', function () {
    if (document.hidden) {
      if (ws) { try { ws.close(); } catch (_) {} ws = null; }
      if (poll) { clearInterval(poll); poll = null; }
    } else if (!ws && !poll) { tries = 0; connect(); }
  });
  connect();
})();
</script>
"""
