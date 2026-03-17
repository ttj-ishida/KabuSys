KabuSys — 日本株向け自動売買・データ基盤ライブラリ
=================================================

概要
----
KabuSys は日本株の自動売買システム向けに設計された Python ライブラリ／モジュール群です。  
主に以下を提供します：

- J-Quants API からの市場データ取得（OHLCV、四半期財務、JPXカレンダー）
- RSS ベースのニュース収集と記事→銘柄紐付け
- DuckDB を用いたスキーマ定義・初期化（Raw / Processed / Feature / Execution / Audit 層）
- ETL パイプライン（差分取得・バックフィル・品質チェック）
- マーケットカレンダー管理、監査ログ構造、品質チェックロジック

設計上の特徴：
- API レート制限・リトライ・トークン自動リフレッシュ対応
- データ取得時の fetched_at によるトレーサビリティ（Look-ahead Bias 対策）
- DuckDB への冪等保存（ON CONFLICT DO UPDATE / DO NOTHING）
- RSS 収集時の SSRF 対策・サイズ制限・XML 爆弾対策（defusedxml 利用）
- 品質チェックは Fail-Fast せず全件評価して呼び出し元で判断可能

主な機能一覧
-------------
- 環境/設定管理: 自動でプロジェクトルートの .env / .env.local を読み込み（KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化可）
- データ取得（kabusys.data.jquants_client）
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - get_id_token（リフレッシュトークンから idToken を取得）
  - DuckDB への保存用関数（save_daily_quotes 等）
- ニュース収集（kabusys.data.news_collector）
  - RSS フィード取得（fetch_rss）
  - raw_news への保存（save_raw_news）
  - 記事→銘柄紐付け（save_news_symbols / _save_news_symbols_bulk）
  - URL 正規化・記事 ID 生成・テキスト前処理・銘柄抽出
- DuckDB スキーマ管理（kabusys.data.schema）
  - init_schema(db_path) で全テーブル・インデックス作成（冪等）
  - get_connection(db_path)
- ETL パイプライン（kabusys.data.pipeline）
  - run_prices_etl / run_financials_etl / run_calendar_etl（差分取得・バックフィル対応）
  - run_daily_etl（カレンダー取得→株価→財務→品質チェックの一括実行）
- カレンダー管理（kabusys.data.calendar_management）
  - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day
  - calendar_update_job（夜間バッチでカレンダー差分更新）
- 品質チェック（kabusys.data.quality）
  - 欠損・スパイク・重複・日付不整合検出（QualityIssue 型で結果を返す）
- 監査ログ（kabusys.data.audit）
  - signal_events / order_requests / executions のテーブル定義と初期化関数

セットアップ手順
----------------

前提
- Python 3.10+ を想定（typing | annotations 等を利用）
- システムにネットワーク接続が必要（J-Quants / RSS など）

1. リポジトリのチェックアウト
   - 開発環境ではソースツリーをクローンして、src/ をパッケージルートとして使います。

2. 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージのインストール
   - 最小依存（本コードで直接使用されるライブラリ）：
     - duckdb
     - defusedxml
   - 例:
     - pip install duckdb defusedxml
   - 他にログ管理やテスト用ライブラリが必要なら追加してください。

4. 環境変数 (.env) の準備
   - プロジェクトルートに .env または .env.local を置くと自動読み込みされます（自動読み込みを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定）。
   - 必須の環境変数（Settings 参照）:
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
     - SLACK_BOT_TOKEN（必須）
     - SLACK_CHANNEL_ID（必須）
   - 任意/デフォルト有り:
     - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（デフォルト: data/monitoring.db）
     - KABUSYS_ENV（development / paper_trading / live。デフォルト: development）
     - LOG_LEVEL（DEBUG/INFO/...。デフォルト: INFO）
   - .env の例（.env.example をプロジェクト側に用意してください）:
     JQUANTS_REFRESH_TOKEN=your_refresh_token
     KABU_API_PASSWORD=your_password
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567
     DUCKDB_PATH=data/kabusys.duckdb
     KABUSYS_ENV=development

使い方（基本例）
---------------

1) DuckDB スキーマ初期化
- 初回はスキーマを作成します。

  from kabusys.data.schema import init_schema
  from kabusys.config import settings

  conn = init_schema(settings.duckdb_path)  # ファイルを作成して全テーブルを生成

2) 日次 ETL 実行（市場データ一括取得 + 品質チェック）
- run_daily_etl を実行するとカレンダー→株価→財務→品質チェックを順に行います。

  from kabusys.data.pipeline import run_daily_etl
  from kabusys.data.schema import get_connection
  from kabusys.config import settings

  conn = get_connection(settings.duckdb_path)
  result = run_daily_etl(conn)  # 引数で target_date, run_quality_checks 等を指定可
  print(result.to_dict())

3) 個別 ETL ジョブ
- 株価だけ更新したい場合:

  from kabusys.data.pipeline import run_prices_etl
  from datetime import date
  fetched, saved = run_prices_etl(conn, target_date=date.today())

- カレンダーのみ更新:

  from kabusys.data.pipeline import run_calendar_etl
  run_calendar_etl(conn, target_date=date.today())

4) RSS ニュース収集
- デフォルト RSS ソース一覧を使って一括収集し、既知銘柄セットで紐付けも行う:

  from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
  from kabusys.data.schema import get_connection

  conn = get_connection(settings.duckdb_path)
  known_codes = {"7203", "6758", "9984"}  # 例: 有効銘柄コードの集合
  results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
  print(results)  # {source_name: 新規保存件数}

5) J-Quants 認証トークンを明示取得
- get_id_token(refresh_token=None) でリフレッシュトークン → idToken を取得できます。
  取得は自動でキャッシュ・リフレッシュされますが、明示的に使いたい場合:

  from kabusys.data.jquants_client import get_id_token
  token = get_id_token()  # settings.jquants_refresh_token を使用

ロギング設定
------------
- Settings.log_level で LOG_LEVEL の妥当性チェックが入ります。アプリ側で logging.basicConfig(level=...) 等を設定して出力を有効にしてください。

環境変数の自動読み込みについて
------------------------------
- パッケージ初期化時にプロジェクトルート（.git または pyproject.toml）を探索し、.env → .env.local の順で読み込みを行います。
- OS 環境変数が優先され、.env.local は .env を上書きします。
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動ロードを無効化できます（テスト等で有用）。

ディレクトリ構成
----------------
リポジトリ内の主要ファイル・ディレクトリ（src/kabusys 配下）:

- src/kabusys/
  - __init__.py              — パッケージ定義（version 等）
  - config.py                — 環境変数／設定読み込み（Settings）
  - data/
    - __init__.py
    - jquants_client.py      — J-Quants API クライアント（取得・保存・認証・レート制御）
    - news_collector.py      — RSS ニュース収集・前処理・DB保存・銘柄抽出
    - schema.py              — DuckDB スキーマ定義・初期化（Raw/Processed/Feature/Execution）
    - pipeline.py            — ETL パイプライン（差分更新・バックフィル・品質チェック）
    - calendar_management.py — カレンダー管理（営業日判定・夜間更新ジョブ）
    - audit.py               — 監査ログ（signal/order/execution の DDL と初期化）
    - quality.py             — データ品質チェック（欠損・スパイク・重複・日付不整合）
  - strategy/
    - __init__.py            — 戦略層（拡張用）
  - execution/
    - __init__.py            — 発注/ブローカー連携層（拡張用）
  - monitoring/
    - __init__.py            — 監視・メトリクス（拡張用）

注意事項・運用上のヒント
-----------------------
- J-Quants の API レート制限（120 req/min）を Respect するため内部でスロットリングとリトライを実装しています。大量の銘柄ループ等を自前で作る場合はレートに注意してください。
- DuckDB のファイルパスは settings.duckdb_path により指定されます。バックアップやアクセス制御を運用で検討してください。
- RSS 収集では外部 URL の検証・リダイレクトの検査を行っていますが、プロキシや特殊ネットワーク環境では追加調整が必要になる場合があります。
- 品質チェックは ETL の一部として実行できますが、検出結果をどのタイミングで自動対応するか（アラート送信・ロールバック・再取得など）は運用ポリシーに従って実装してください。

拡張ポイント
-------------
- strategy / execution / monitoring パッケージは骨組みとして用意されています。実際の戦略ロジック、注文送信ロジック（kabuステーションAPI 等）、監視アラート（Slack連携など）はアプリ側で実装して統合してください。
- NewsCollector の既知銘柄リストや RSS ソースは設定化して外部管理（S3 や DB）にすることも可能です。

ライセンス
----------
（ここにプロジェクトのライセンス記載を追加してください）

────────────────────────
この README はコードベース（src/kabusys）に基づいて生成されています。具体的な運用スクリプトや CI/CD、デプロイ手順などはプロジェクトの方針に合わせて別途用意してください。