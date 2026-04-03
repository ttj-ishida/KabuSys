# KabuSys

KabuSys は日本株のデータプラットフォームと自動売買パイプラインを想定した Python ライブラリです。  
J-Quants / RSS / OpenAI（LLM）を用いたデータ取得・品質チェック・ニュースセンチメント評価・市場レジーム判定・ファクター計算・監査ログ保存など、取引システム基盤に必要な各機能をモジュール化して提供します。

注意: このリポジトリはライブラリ本体のみを含み、実行環境（DBスキーマ作成スクリプトや CLI、実運用用のジョブスケジューラ等）は別途用意する想定です。

主な特徴
- J-Quants API クライアント（株価、財務、マーケットカレンダー取得、トークン自動リフレッシュ、レートリミット・リトライ）
- DuckDB を用いた ETL パイプライン（差分取得、バックフィル、品質チェック）
- ニュース収集（RSS）と前処理、記事の冪等保存
- OpenAI を利用したニュースセンチメント（銘柄ごと）およびマクロセンチメント評価（市場レジーム判定）
- 研究用ユーティリティ（ファクタ計算、将来リターン、IC、統計サマリー、Zスコア正規化）
- 監査ログ（シグナル → 発注 → 約定のトレーサビリティ用スキーマ初期化ユーティリティ）
- データ品質チェック（欠損・重複・スパイク・日付不整合）

機能一覧
- kabusys.config: 環境変数/.env の自動読み込み・設定管理
- kabusys.data.jquants_client: J-Quants API の取得・保存ロジック（fetch_* / save_*）
- kabusys.data.pipeline: 日次 ETL 実行 run_daily_etl と個別 ETL ジョブ（prices, financials, calendar）
- kabusys.data.news_collector: RSS フィード取得・前処理・冪等保存ロジック
- kabusys.data.quality: データ品質チェック群（run_all_checks 等）
- kabusys.data.audit: 監査ログ用テーブル作成・DB初期化（init_audit_schema / init_audit_db）
- kabusys.ai.news_nlp: 銘柄別ニュースを LLM でスコア化（score_news）
- kabusys.ai.regime_detector: マクロセンチメントと ETF MA を組み合わせ市場レジームを判定（score_regime）
- kabusys.research: ファクター計算（momentum/volatility/value）、特徴量解析ユーティリティ

セットアップ手順（開発向け）
1. リポジトリをクローン
   - git clone <repo_url>
2. Python 仮想環境を作成・有効化（例）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）
3. 必要パッケージをインストール
   - pip install duckdb openai defusedxml
   - （パッケージ配布用の pyproject/requirements があればそれを利用してください）
   - 開発中にパッケージとしてインストールする場合:
     - pip install -e .
4. 環境変数 / .env の準備
   - プロジェクトルート（.git または pyproject.toml のあるディレクトリ）から自動で `.env` / `.env.local` を読み込みます。自動読み込みを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
   - 主要な環境変数:
     - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
     - KABU_API_PASSWORD: kabu API 用パスワード（必須）
     - OPENAI_API_KEY: OpenAI API キー（score_news / score_regime 実行時に必要）
     - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: 通知用（任意）
     - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH: 監視 DB パス（デフォルト: data/monitoring.db）
     - PID_FILE_PATH, KILL_FLAG_PATH 等の監視用設定
     - KABUSYS_ENV: development | paper_trading | live（デフォルト development）
     - LOG_LEVEL: DEBUG|INFO|WARNING|ERROR|CRITICAL
   - .env の書式はシェル形式（KEY=VALUE、コメント行は # で開始）に準じます。クォートやエスケープもサポートしています。

使い方（コード例）
- DuckDB 接続を使って日次 ETL を実行する
  - 例:
    from datetime import date
    import duckdb
    from kabusys.config import settings
    from kabusys.data.pipeline import run_daily_etl

    conn = duckdb.connect(str(settings.duckdb_path))
    result = run_daily_etl(conn, target_date=date.today())
    print(result.to_dict())

- OpenAI を用いたニューススコアリング（銘柄ごと）
  - 例:
    from datetime import date
    import duckdb
    from kabusys.ai.news_nlp import score_news

    conn = duckdb.connect("path/to/db.duckdb")
    written = score_news(conn, target_date=date(2026, 3, 19), api_key="sk-...")
    print(f"written scores: {written}")

- 市場レジーム判定（ETF 1321 MA + マクロLLM）
  - 例:
    from datetime import date
    import duckdb
    from kabusys.ai.regime_detector import score_regime

    conn = duckdb.connect("path/to/db.duckdb")
    score_regime(conn, target_date=date(2026, 3, 19), api_key="sk-...")

- 監査ログ DB 初期化（監査専用 DB）
  - 例:
    from kabusys.data.audit import init_audit_db
    conn = init_audit_db("data/audit.duckdb")
    # テーブルが作成され、UTC タイムゾーンが設定されます

- RSS フィード取得（ニュースコレクタの一部API）
  - 例:
    from kabusys.data.news_collector import fetch_rss, DEFAULT_RSS_SOURCES
    articles = fetch_rss(DEFAULT_RSS_SOURCES["yahoo_finance"], source="yahoo_finance")
    for a in articles:
        print(a["id"], a["datetime"], a["title"])

実装上の注意 / 設計方針（抜粋）
- Look-ahead bias を避けるため、日付演算は target_date を明示的に受け取り、内部で現在日を参照しないよう設計しています。
- DuckDB を主要な永続ストレージとして使用し、高速な SQL ウィンドウ関数や executemany を併用して処理します。
- 外部 API 呼び出し（J-Quants, OpenAI）はレート制御とリトライを組み込み、フェイルセーフ（失敗時にゼロ/スキップして継続）を基本方針としています。
- ニュース取得では SSRF 対策、最大受信バイト制限、トラッキングパラメータの除去などセキュリティに配慮した実装です。

主要ファイル / ディレクトリ構成
- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数 / .env 読み込みと Settings
  - ai/
    - __init__.py
    - news_nlp.py             — 銘柄別ニューススコア（score_news）
    - regime_detector.py      — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py       — J-Quants API クライアント（fetch/save ロジック）
    - pipeline.py             — ETL パイプライン（run_daily_etl 等）
    - etl.py                  — ETLResult のエクスポート
    - news_collector.py       — RSS 収集・前処理
    - quality.py              — データ品質チェック群
    - stats.py                — スタティスティクスユーティリティ（zscore_normalize）
    - calendar_management.py  — 市場カレンダー管理（is_trading_day など）
    - audit.py                — 監査ログスキーマ初期化（init_audit_schema / init_audit_db）
  - research/
    - __init__.py
    - factor_research.py      — ファクター計算（momentum/volatility/value）
    - feature_exploration.py  — 将来リターン / IC / 統計要約
  - research/*（その他ユーティリティ）

追加の運用ヒント
- テスト時に環境変数の自動ロードを無効にする:
  - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
- OpenAI の呼び出しは内部で retries/backoff を行いますが、コスト管理のためバッチサイズやトークン制限に注意してください（news_nlp は1チャンク最大 20 銘柄）。
- J-Quants API はレート制限があるため、並列化には注意してください。jquants_client は固定間隔の RateLimiter を内蔵しています。

ライセンス・貢献
- 本 README ではライセンスや貢献ガイドは含めていません。リポジトリの LICENSE / CONTRIBUTING ファイルを参照してください（存在する場合）。

問題報告 / 要望
- バグや機能改善の要望は issue を立ててください。可能であれば再現手順と最小限のコード例／ログを添付してください。

以上が KabuSys の概要と使い方です。  
必要であれば、セットアップ用の requirements.txt や実運用向けの例（systemd ユニット、cron ジョブ、Dockerfile、DB スキーマ初期化スクリプト）を追加で作成します。どれを優先して欲しいか教えてください。