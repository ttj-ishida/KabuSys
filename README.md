KabuSys — 日本株自動売買プラットフォーム（README）
概要
KabuSys は日本株向けのデータパイプライン、リサーチ（ファクター計算）、AI を用いたニュースセンチメント評価、監査ログ（発注トレーサビリティ）などを備えた自動売買支援のライブラリ群です。
設計上のポイント
- DuckDB を中心としたローカル DB にデータを保存・処理する
- J-Quants API からの差分 ETL（株価・財務・市場カレンダー）
- OpenAI を用いたニュース NLP（gpt-4o-mini）による銘柄センチメント付与とマクロレジーム判定
- 監査ログ（signal → order_request → execution）の強いトレーサビリティ
- ルックアヘッドバイアス対策（実行日参照を明示的に行う設計）とフォールトトレランス

主な機能一覧
- data
  - ETL（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - J-Quants クライアント（fetch_* / save_*）
  - カレンダー管理（is_trading_day / next_trading_day / get_trading_days / calendar_update_job）
  - ニュース収集ユーティリティ（fetch_rss, preprocess_text 等、安全対策あり）
  - データ品質チェック（check_missing_data / check_spike / check_duplicates / check_date_consistency / run_all_checks）
  - 統計ユーティリティ（zscore_normalize）
  - 監査ログスキーマ初期化・DB作成（init_audit_schema / init_audit_db）
- ai
  - ニュースセンチメント（score_news）
  - 市場レジーム判定（score_regime）
  - LLM 呼び出しは OpenAI SDK を使いリトライやフォールトトレランス実装
- research
  - ファクター計算（calc_momentum / calc_value / calc_volatility）
  - 特徴量探索（calc_forward_returns / calc_ic / factor_summary / rank）
- config
  - 環境変数読み込み（.env/.env.local 自動ロード、必要な設定値の取得用 Settings）

セットアップ手順
前提
- Python 3.10+（typing の | 演算子や型注釈を使用）
- ネットワーク接続（J-Quants / OpenAI 等への API アクセス）

1) リポジトリをクローン / 開発環境へ配置
    git clone <repo-url>
    cd <repo>

2) 仮想環境を作成して有効化（推奨）
    python -m venv .venv
    source .venv/bin/activate  # macOS/Linux
    .venv\Scripts\activate     # Windows

3) 依存パッケージをインストール
    pip install duckdb openai defusedxml
（プロジェクトに requirements.txt があればそれを使ってください。上は最低限の依存例です。）

4) 環境変数設定
ルートに .env または .env.local を置くと自動読み込みされます（パッケージ配布後も __file__ を基点にプロジェクトルートを探索します）。自動ロードを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

必須（例）
- JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxx
- OPENAI_API_KEY=sk-xxxxxxxxxxxx
- KABU_API_PASSWORD=your_kabu_password
- SLACK_BOT_TOKEN=xoxb-...
- SLACK_CHANNEL_ID=C01234567

任意・デフォルト
- KABUSYS_ENV=development|paper_trading|live  （デフォルト development）
- LOG_LEVEL=INFO
- DUCKDB_PATH=data/kabusys.duckdb
- SQLITE_PATH=data/monitoring.db
.env の例（ルートに .env を作る）
    JQUANTS_REFRESH_TOKEN=your_refresh_token
    OPENAI_API_KEY=sk-...
    KABU_API_PASSWORD=passw0rd
    SLACK_BOT_TOKEN=xoxb-...
    SLACK_CHANNEL_ID=C01234567
    DUCKDB_PATH=~/kabusys/data/kabusys.duckdb
    KABUSYS_ENV=development

使い方（主要なサンプル）
- DuckDB 接続例（デフォルトパスを settings から取得）
    from kabusys.config import settings
    import duckdb
    conn = duckdb.connect(str(settings.duckdb_path))

- 日次 ETL 実行
    from kabusys.data.pipeline import run_daily_etl
    from kabusys.config import settings
    import duckdb
    from datetime import date

    conn = duckdb.connect(str(settings.duckdb_path))
    result = run_daily_etl(conn, target_date=date(2026, 3, 20))
    print(result.to_dict())

run_daily_etl はカレンダー → 株価 → 財務 → 品質チェックの順で実行し、ETLResult を返します。

- OpenAI を使ったニューススコアリング（銘柄別 ai_score の書込み）
    from kabusys.ai.news_nlp import score_news
    from kabusys.config import settings
    import duckdb
    from datetime import date

    conn = duckdb.connect(str(settings.duckdb_path))
    written = score_news(conn, target_date=date(2026,3,20))  # OPENAI_API_KEY は env から参照
    print(f"wrote {written} scores")

- 市場レジーム（マクロセンチメント + ETF MA200）判定
    from kabusys.ai.regime_detector import score_regime
    from kabusys.config import settings
    import duckdb
    from datetime import date

    conn = duckdb.connect(str(settings.duckdb_path))
    score_regime(conn, target_date=date(2026,3,20))

score_news / score_regime は api_key を引数で渡すこともできます（テスト時のキー差し替えに有効）。

- 監査ログ（監査 DB 初期化）
    from kabusys.data.audit import init_audit_db
    conn = init_audit_db("data/audit.duckdb")
    # 以降 conn を使って監査テーブルに書き込み・検索が可能

- ニュース RSS 取得（保存は呼び出し側で実装）
    from kabusys.data.news_collector import fetch_rss
    articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
    for a in articles:
        print(a["id"], a["title"], a["datetime"])

注意点
- OpenAI / J-Quants などの API 呼び出しは課金やレート制限があります。各クライアントにリトライ・バックオフ・レートリミット制御が実装されていますが、運用設計は利用者側で行ってください。
- research モジュール（ファクター計算・特徴量解析）は DB の prices_daily / raw_financials 等を参照するだけで、実際の発注は行いません。バックテスト時は Look-ahead を防ぐために target_date を明示してください。
- news_collector は RSS パースや外部 URL ダウンロードを行います。SSRF や XML 攻撃対策（defusedxml、ホスト検証、最大バイト数検査等）が組み込まれていますが、実運用ではソースの管理を推奨します。
- config モジュールはプロジェクトルート（.git / pyproject.toml を基準）を探索して .env / .env.local を自動で読み込みます。テスト中に自動読み込みを抑止する際は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。

ディレクトリ構成（概要）
src/kabusys/
- __init__.py
- config.py                — 環境変数/設定管理
- ai/
  - __init__.py
  - news_nlp.py            — 銘柄別ニュースセンチメント付与（score_news）
  - regime_detector.py     — マクロ＋ETF MA200 を用いた市場レジーム判定（score_regime）
- data/
  - __init__.py
  - jquants_client.py      — J-Quants API クライアント（fetch / save）
  - pipeline.py            — ETL パイプライン（run_daily_etl 等）
  - etl.py                 — ETL 結果型の公開
  - calendar_management.py — 市場カレンダー管理（is_trading_day など）
  - news_collector.py      — RSS 収集ユーティリティ（fetch_rss 等）
  - quality.py             — データ品質チェック
  - stats.py               — z-score 正規化等の統計ユーティリティ
  - audit.py               — 監査ログスキーマ初期化（init_audit_schema / init_audit_db）
- research/
  - __init__.py
  - factor_research.py     — モメンタム/バリュー/ボラティリティ計算
  - feature_exploration.py — 将来リターン計算 / IC / サマリー
- research/* 他モジュール

運用上のヒント
- 本番運用（ライブ板発注）を行う場合は KABUSYS_ENV=live を設定し、発注前に設定値（パスワード・APIキー・DBパス）およびログレベルを明確にしてください。
- 監査ログは削除しない方針です。init_audit_db で専用の DB を作り、監査専用に運用することを推奨します。
- DuckDB ファイルは定期的にバックアップしてください（特に監査DBや履歴データ）。

テスト
- OpenAI 呼び出し部分は _call_openai_api のような内部関数をモックしやすく設計されています（unittest.mock.patch を使用）。
- config の自動 .env 読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化できます。

ライセンス・貢献
（ここにライセンス情報や貢献方法を記載してください。実リポジトリでは LICENSE や CONTRIBUTING.md を用意することを推奨します。）

以上が KabuSys の README の要点です。追加でサンプルスクリプトや CI/デプロイ手順、requirements.txt／pyproject.toml など README に追記したい内容があれば教えてください。