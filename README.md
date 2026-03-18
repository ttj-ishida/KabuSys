KabuSys — 日本株自動売買基盤（README）
===================================

概要
----
KabuSys は日本株向けのデータプラットフォームと自動売買基盤のコアライブラリ群です。  
主に以下を提供します。

- J-Quants からのデータ取得（株価日足、財務データ、マーケットカレンダー）
- DuckDB を用いたデータスキーマ定義・永続化（Raw / Processed / Feature / Execution / Audit 層）
- ETL パイプライン（差分取得・保存・品質チェック）
- ニュース収集（RSS）と銘柄抽出、冪等保存
- 研究用ファクター計算（モメンタム、ボラティリティ、バリュー等）と評価（IC、要約）
- 発注／監査ログスキーマ（監査トレース用テーブル）
- 簡易な設定管理（環境変数／.env 自動読み込み）

特徴（主な機能）
----------------
- data/jquants_client: J-Quants API クライアント（レート制御、リトライ、トークン自動リフレッシュ）
- data/schema: DuckDB のスキーマ定義と初期化（冪等）
- data/pipeline: 日次 ETL（差分取得、backfill、品質チェック）
- data/news_collector: RSS 収集、テキスト前処理、記事保存、銘柄抽出（SSRF 対策・サイズ制限あり）
- data/quality: 欠損・スパイク・重複・日付不整合の品質チェック
- research: ファクター計算（calc_momentum / calc_volatility / calc_value）、特徴量探索（calc_forward_returns / calc_ic / factor_summary / rank）、Zスコア正規化ユーティリティ
- audit: 発注から約定までの監査ログ用スキーマ（トレース可能な UUID 連鎖）
- config: 環境変数・.env 管理（プロジェクトルート自動検出、.env/.env.local の優先度制御）

必要条件
--------
- Python 3.10+
- 必要な Python パッケージ（主な例）:
  - duckdb
  - defusedxml
  - （標準ライブラリのみで実装されている部分が多いですが、実行環境に応じて追加パッケージが必要になる場合があります）

セットアップ手順
----------------

1. リポジトリをクローンして仮想環境を作成・有効化
   - 例:
     - git clone <repo>
     - python -m venv .venv
     - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージをインストール
   - 例:
     - pip install duckdb defusedxml

   （プロジェクトに requirements.txt や pyproject.toml があればそちらを使ってください）

3. 環境変数の準備
   - 必須環境変数（Settings 参照）:
     - JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD — kabuステーション API のパスワード
     - SLACK_BOT_TOKEN — Slack 通知に使う Bot トークン
     - SLACK_CHANNEL_ID — Slack チャンネル ID
   - 任意（デフォルト値あり）:
     - KABUSYS_ENV (development | paper_trading | live) — デプロイ環境
     - LOG_LEVEL (DEBUG | INFO | ...)
     - KABU_API_BASE_URL — kabu API のベース URL（デフォルト http://localhost:18080/kabusapi）
     - DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
     - SQLITE_PATH — 監視用 SQLite パス（デフォルト data/monitoring.db）
   - .env 自動ロード:
     - プロジェクトルート（.git または pyproject.toml を基準）に .env/.env.local を置くと自動で読み込みます。
     - 自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

   - 例 .env（最小）:
     JQUANTS_REFRESH_TOKEN=xxxxx
     KABU_API_PASSWORD=xxxxx
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567

4. DuckDB スキーマ初期化
   - Python REPL やスクリプトから初期化します：

     from kabusys.data import schema
     conn = schema.init_schema("data/kabusys.duckdb")

   - 監査ログ専用 DB を作る場合:
     from kabusys.data import audit
     audit_conn = audit.init_audit_db("data/kabusys_audit.duckdb")

使い方（主要なユースケース）
---------------------------

1) 日次 ETL（株価・財務・カレンダーの差分取得＋品質チェック）
   - 例（スクリプト）:

     from datetime import date
     from kabusys.data import schema, pipeline

     conn = schema.init_schema("data/kabusys.duckdb")
     result = pipeline.run_daily_etl(conn, target_date=date.today())
     print(result.to_dict())

   - pipeline.run_daily_etl は次の処理を行います：
     1. カレンダー ETL（先読み）
     2. 株価日足 ETL（差分 + backfill）
     3. 財務データ ETL（差分 + backfill）
     4. 品質チェック（check_missing_data / check_duplicates / check_spike / check_date_consistency）

2) RSS ニュース収集と保存
   - 例:

     from kabusys.data.news_collector import run_news_collection
     from kabusys.data import schema

     conn = schema.get_connection("data/kabusys.duckdb")
     known_codes = {"7203", "6758", "9984"}  # 事前に管理している銘柄コードセット
     results = run_news_collection(conn, known_codes=known_codes)
     print(results)

   - 備考:
     - URL 正規化、トラッキングパラメータ除去、SSRF/プライベートホストブロック、gzip サイズ制限などの安全対策あり
     - raw_news / news_symbols に冪等保存

3) ファクター計算 / 研究用 API
   - DuckDB 接続を渡して呼び出します（prices_daily, raw_financials テーブルのみ参照）
   - 例:

     from datetime import date
     import duckdb
     from kabusys.research import calc_momentum, calc_volatility, calc_value, zscore_normalize

     conn = duckdb.connect("data/kabusys.duckdb")
     target = date(2024, 1, 31)
     mom = calc_momentum(conn, target)
     vol = calc_volatility(conn, target)
     val = calc_value(conn, target)
     # Zスコア正規化（クロスセクション）
     mom_norm = zscore_normalize(mom, ["mom_1m", "mom_3m", "mom_6m"])

4) J-Quants API 直接利用（フェッチ + 保存）
   - 例:

     from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes
     from kabusys.config import settings
     import duckdb

     data = fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
     conn = duckdb.connect("data/kabusys.duckdb")
     save_daily_quotes(conn, data)

注意点 / 設計上のポイント
-----------------------
- DB 操作は基本的に冪等（ON CONFLICT）に配慮して実装されています。
- J-Quants クライアントはレート制御（120 req/min）とリトライ・トークンリフレッシュをサポートします。
- ニュース収集は SSRF 対策やサイズ上限、XML の安全パーサ（defusedxml）を使用しています。
- research モジュールは外部 API にアクセスせず、DuckDB 内の prices_daily/raw_financials のみを参照します（本番口座・発注 API には一切アクセスしない設計）。
- 設定は環境変数ベースで、.env/.env.local の順に読み込まれます（OS 環境変数が優先）。テスト等で自動読み込みを止めたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。
- KABUSYS_ENV の有効値: development, paper_trading, live。live 時は実発注に接続するコードの本番切替等に利用可能です。

ディレクトリ構成
----------------
（主要ファイルを抜粋）

- src/kabusys/
  - __init__.py
  - config.py                      — 環境変数 / .env 管理（settings）
  - data/
    - __init__.py
    - jquants_client.py             — J-Quants API クライアント + 保存ユーティリティ
    - news_collector.py             — RSS 収集・保存・銘柄抽出
    - schema.py                     — DuckDB スキーマ定義 / init_schema
    - pipeline.py                   — ETL パイプライン（run_daily_etl 等）
    - quality.py                    — データ品質チェック
    - stats.py                      — 統計ユーティリティ（zscore_normalize）
    - features.py                   — features の公開ラッパ
    - calendar_management.py        — カレンダー更新 / 営業日ユーティリティ
    - audit.py                      — 監査ログ（signal_events / order_requests / executions）
    - etl.py                        — ETLResult の再エクスポート
  - research/
    - __init__.py
    - feature_exploration.py        — 将来リターン / IC / サマリー等
    - factor_research.py            — momentum / volatility / value の計算
  - strategy/                       — 戦略層（未展開のパッケージ初期化）
  - execution/                      — 発注実行層（未展開のパッケージ初期化）
  - monitoring/                     — 監視関連（パッケージ初期化）

開発・貢献
-----------
- コードは型注釈と単体関数で分割されており、モジュールごとにユニットテストを追加しやすい構造です。
- テストを書く際は config の自動 .env 読み込みを無効化（KABUSYS_DISABLE_AUTO_ENV_LOAD=1）すると安定します。
- DuckDB の :memory: を使うと一時 DB でテスト可能です。

ライセンス / 注意
-----------------
- 本 README はコードベースからの概要説明です。実際に発注・資金を投入する前に必ずテスト口座／ペーパートレード環境で動作を確認してください。
- 実運用では秘密情報（トークン・パスワード等）管理に注意し、ログに機密情報を出力しないでください。

----
必要であれば、README にサンプルスクリプト（ETL ジョブ、news collector、factor 計算）を追加します。どの例を増やしますか？