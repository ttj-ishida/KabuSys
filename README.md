KabuSys
=======

日本株向けの自動売買 / データ基盤ライブラリ群です。  
DuckDB を用いたデータレイク、J-Quants API からのデータ収集、ニュース収集、品質チェック、ファクター計算、ETL パイプライン、監査ログ等のユーティリティを提供します。

主な目的
- J-Quants から株価・財務・カレンダーを差分取得して DuckDB に蓄積する
- RSS ベースのニュース収集と銘柄紐付け
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- ファクター（Momentum / Volatility / Value 等）計算と IC や統計サマリー
- 発注・監査レイヤーのスキーマ定義（監査ログの初期化支援）
- 研究（Research）用途のユーティリティ再利用

機能一覧
- env/.env 自動読み込み（プロジェクトルートの .env/.env.local）と Settings による環境変数アクセス
- J-Quants API クライアント（ページネーション・レートリミット・リトライ・トークン自動リフレッシュ）
- DuckDB スキーマ初期化（raw / processed / feature / execution / audit レイヤ）
- ETL パイプライン（市場カレンダー、株価、財務の差分取得と保存）
- データ品質チェック（欠損・スパイク・重複・将来日付 / 非営業日チェック）
- RSS ニュース収集（SSRF 対策・サイズ制限・トラッキング除去・記事ID付与・銘柄抽出）
- ファクター計算（モメンタム、ボラティリティ、バリュー）と z-score 正規化、IC 計算、統計サマリー
- 監査ログスキーマ（signal → order_request → executions のトレーサビリティ）

セットアップ手順（開発用）
- 前提: Python 3.10+（型ヒントで Union 演算子等を使用）
1. レポジトリをクローン
   - git clone <repo-url>
2. 仮想環境作成と依存インストール
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
   - pip install duckdb defusedxml
     - 必要に応じて他の依存（requests など）を追加してください（本コードでは標準 urllib を利用）
3. 環境変数（.env）を用意
   - プロジェクトルートの .env / .env.local を自動読み込みします（CWD に依存しない探索）
   - 自動読み込みを無効化する場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します

推奨の .env（例）
- .env.example から作成してください。主なキー例：
  - JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
  - KABU_API_PASSWORD=your_kabu_password
  - SLACK_BOT_TOKEN=xoxb-...
  - SLACK_CHANNEL_ID=C...
  - DUCKDB_PATH=data/kabusys.duckdb
  - SQLITE_PATH=data/monitoring.db
  - KABUSYS_ENV=development    # development | paper_trading | live
  - LOG_LEVEL=INFO

設定アクセス
- Python からは kabusys.config.settings 経由でアクセスできます。例:
  - from kabusys.config import settings
  - token = settings.jquants_refresh_token
  - db_path = settings.duckdb_path

使い方（主要な操作例）
- DuckDB スキーマの初期化
  - from kabusys.data.schema import init_schema
  - from kabusys.config import settings
  - conn = init_schema(settings.duckdb_path)
    - ":memory:" を渡すとインメモリ DB を使用できます

- 監査ログ用 DB の初期化（別 DB にしたい場合）
  - from kabusys.data.audit import init_audit_db
  - audit_conn = init_audit_db("data/audit.duckdb")

- 日次 ETL 実行（市場カレンダー・株価・財務の差分取得 + 品質チェック）
  - from kabusys.data.pipeline import run_daily_etl
  - result = run_daily_etl(conn)  # 引数で target_date / id_token / run_quality_checks 等を指定可
  - result は ETLResult オブジェクト。result.to_dict() で辞書化できます。

- ニュース収集ジョブ
  - from kabusys.data.news_collector import run_news_collection
  - results = run_news_collection(conn, sources=None, known_codes=set_of_codes)
    - sources を省略するとデフォルト RSS ソースを使用
    - known_codes を渡すと抽出した銘柄コードと記事を紐付けます

- ファクター計算（研究用）
  - from kabusys.research import calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, factor_summary, zscore_normalize
  - from datetime import date
  - mom = calc_momentum(conn, date(2024, 1, 31))
  - vol = calc_volatility(conn, date(2024, 1, 31))
  - val = calc_value(conn, date(2024, 1, 31))
  - fwd = calc_forward_returns(conn, date(2024, 1, 31), horizons=[1,5,21])
  - ic = calc_ic(factor_records=mom, forward_records=fwd, factor_col="mom_1m", return_col="fwd_1d")
  - summary = factor_summary(mom, ["mom_1m","mom_3m","ma200_dev"])
  - normalized = zscore_normalize(mom, ["mom_1m","mom_3m","mom_6m"])

- J-Quants API 呼び出し例（直接）
  - from kabusys.data.jquants_client import fetch_daily_quotes, fetch_financial_statements
  - quotes = fetch_daily_quotes(code="7203", date_from=date(2024,1,1), date_to=date(2024,1,31))

注意点・設計上の方針（抜粋）
- .env の自動読み込みはプロジェクトルート（.git または pyproject.toml）から探索します
- settings で取得する必須値が未設定の場合は ValueError が発生します（例: JQUANTS_REFRESH_TOKEN）
- J-Quants クライアントは 120 req/min のレート制限に合わせたスロットリングと指数バックオフ、401 の場合はリフレッシュトークンで id_token を再取得する仕組みを持ちます
- ETL は差分更新を基本とし、バックフィル日数により最終取得日前後を再取得して後出し修正を吸収します
- ニュース取得は SSRF 対策・受信サイズ上限・トラッキング除去を組み込み、冪等保存を行います
- 監査ログ（audit）では UUID を使ったトレースを前提にしています（すべて UTC で保存）

環境変数一覧（主なもの）
- JQUANTS_REFRESH_TOKEN (必須) — J-Quants 用リフレッシュトークン
- KABU_API_PASSWORD (必須) — kabu ステーション API 用パスワード
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須) — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID (必須) — Slack 送信先チャンネル ID
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト data/monitoring.db）
- KABUSYS_ENV — 環境 (development, paper_trading, live)
- LOG_LEVEL — ログレベル (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 1 をセットすると .env 自動読み込みを無効化

ディレクトリ構成（主なファイル）
- src/kabusys/
  - __init__.py
  - config.py                     — 環境変数 / 設定管理 (Settings)
  - data/
    - __init__.py
    - jquants_client.py           — J-Quants API クライアント（fetch / save / rate limit）
    - news_collector.py           — RSS ニュース収集と保存ロジック
    - schema.py                   — DuckDB スキーマ定義と init_schema / get_connection
    - pipeline.py                 — ETL パイプライン（run_daily_etl 等）
    - features.py                 — 特徴量ユーティリティ（再エクスポート）
    - calendar_management.py      — market_calendar の管理・判定ユーティリティ
    - etl.py                      — ETL 公開インターフェース（ETLResult 再エクスポート）
    - audit.py                    — 監査ログスキーマ定義・初期化
    - stats.py                    — zscore_normalize 等の統計ユーティリティ
    - quality.py                  — データ品質チェック
  - research/
    - __init__.py                 — 研究用 API の再エクスポート
    - feature_exploration.py      — 将来リターン計算 / IC / 統計サマリー
    - factor_research.py          — Momentum / Volatility / Value ファクター計算
  - strategy/
    - __init__.py                 — （戦略層拡張用）
  - execution/
    - __init__.py                 — （発注 / ブローカー連携拡張用）
  - monitoring/
    - __init__.py                 — （監視・メトリクス用拡張）

開発・拡張のヒント
- strategy / execution / monitoring パッケージは拡張ポイントとして用意されています。アルゴリズムや発注ロジックをここに実装してください。
- DuckDB のスキーマは冪等に作成されるため、既存 DB へ安全に追加できます。
- テスト時には KABUSYS_DISABLE_AUTO_ENV_LOAD を有効にして環境依存を切り離すと便利です。

ライセンス・貢献
- 本リポジトリに含まれるファイルに従ってください（ライセンスファイルがある場合はそちらを参照してください）。
- バグ報告や機能提案は Issues へ、プルリクエスト歓迎します。

お問い合わせ
- 本 README の内容に関する質問や、特定の機能の使い方が必要であれば具体的なユースケース（例: ETL の自動化、バックフィルのやり方、特定ファクターの計算例など）を教えてください。具体例に沿ったコードスニペットを提示します。