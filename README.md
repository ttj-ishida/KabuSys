# KabuSys

日本株向けの自動売買データ基盤 / ETL / ニュース収集ライブラリです。J-Quants API から株価・財務・マーケットカレンダーを取得し、DuckDB に冪等に保存します。ニュースは RSS フィードを収集して前処理・銘柄紐付けし、監査用スキーマや実行レイヤの雛形も備えています。

バージョン: 0.1.0

---

## 主要コンセプト・目的

- J-Quants や各種 RSS からデータを取得して「Raw → Processed → Feature → Execution」までのデータレイヤを DuckDB で管理する。
- API レート制限・リトライ・トークン自動更新などを組み込んだ堅牢なデータ取得ロジック。
- ニュース収集では SSRF 対策、XML の安全パース、レスポンスサイズ制限などのセキュリティ考慮を実装。
- ETL 処理は差分取得（backfill 対応）・品質チェック（欠損・重複・スパイク・日付不整合）を行う。
- 監査ログ用スキーマにより、シグナル→発注→約定までをトレース可能にする。

---

## 主な機能一覧

- 環境設定管理（.env 自動ロード / 必須キー検査）
- J-Quants API クライアント
  - 日足（OHLCV）、財務（四半期）、マーケットカレンダー取得
  - レート制御、リトライ（指数バックオフ）、401時のトークン自動更新
  - DuckDB への冪等保存（ON CONFLICT）
- ニュース収集
  - RSS 取得・XML の安全パース（defusedxml）
  - URL 正規化、トラッキングパラメータ除去、記事ID生成（SHA-256）
  - SSRF 対策（スキーム・プライベートIPチェック）、受信サイズ制限
  - DuckDB への冪等保存／銘柄抽出と紐付け
- ETL パイプライン
  - 差分取得（最終取得日の追跡）、バックフィル、カレンダー先読み
  - 品質チェック（欠損・重複・スパイク・日付整合性）
  - 日次 ETL の統合エントリポイント
- マーケットカレンダー管理（営業日の判定、次/前営業日取得）
- 監査ログ（signal_events / order_requests / executions）向けスキーマ初期化

---

## 必要環境 / 依存

- Python 3.10+
- 必須パッケージ（例）
  - duckdb
  - defusedxml
- （その他）標準ライブラリで多くを賄うが、プロジェクトで別途 requirements.txt を用意している場合はそちらを利用してください。

例:
pip install duckdb defusedxml

---

## セットアップ手順

1. リポジトリをクローン / ソースを配置

2. 仮想環境作成（推奨）
   python -m venv .venv
   source .venv/bin/activate  # macOS/Linux
   .venv\Scripts\activate     # Windows

3. 依存パッケージをインストール
   pip install -U pip
   pip install duckdb defusedxml
   （プロジェクトに requirements.txt / pyproject.toml があればそちらを利用）

4. 環境変数設定
   プロジェクトルートに `.env` と `.env.local` を置くことで自動読み込みされます（読み込みは OS 環境変数 > .env.local > .env の順）。自動読み込みを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

   必須環境変数（例）:
   - JQUANTS_REFRESH_TOKEN  （J-Quants のリフレッシュトークン）
   - KABU_API_PASSWORD      （kabuステーション API パスワード）
   - SLACK_BOT_TOKEN        （Slack 通知に使う Bot トークン）
   - SLACK_CHANNEL_ID       （通知先チャネル ID）

   任意・デフォルト値:
   - KABUSYS_ENV            （development, paper_trading, live。デフォルト: development）
   - KABUSYS_DISABLE_AUTO_ENV_LOAD （自動読み込み無効化フラグ）
   - KABUSYS_LOG_LEVEL / LOG_LEVEL （ログレベル。例: INFO）
   - DUCKDB_PATH            （デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH            （デフォルト: data/monitoring.db）
   - KABU_API_BASE_URL      （デフォルト: http://localhost:18080/kabusapi）

   サンプル `.env`:
   ```
   JQUANTS_REFRESH_TOKEN=your_refresh_token_here
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C12345678
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   ```

---

## 使い方（簡単な例）

以下は Python REPL / スクリプト例です。実運用ではロギングや例外処理を適切に追加してください。

- スキーマ初期化（DuckDB）
  from kabusys.data.schema import init_schema
  conn = init_schema("data/kabusys.duckdb")

- ETL（日次統合パイプライン）
  from kabusys.data.pipeline import run_daily_etl
  result = run_daily_etl(conn)  # target_date を指定可能
  print(result.to_dict())

- ニュース収集（RSS を取得して保存）
  from kabusys.data.news_collector import run_news_collection
  # known_codes は銘柄抽出に使用する有効銘柄コードのセット（省略可）
  res = run_news_collection(conn, sources=None, known_codes={"7203", "6758"})
  print(res)

- カレンダー夜間更新ジョブ
  from kabusys.data.calendar_management import calendar_update_job
  saved = calendar_update_job(conn)
  print(f"saved={saved}")

- 監査スキーマ初期化（既存の DuckDB 接続に追加）
  from kabusys.data.audit import init_audit_schema
  init_audit_schema(conn)

- J-Quants API を直接使う（ID トークン取得）
  from kabusys.data.jquants_client import get_id_token
  token = get_id_token()  # settings.jquants_refresh_token を利用

設定は kabusys.config.settings 経由で参照できます:
  from kabusys.config import settings
  print(settings.duckdb_path)

---

## よく使う API / 関数一覧（抜粋）

- kabusys.config.Settings: 環境設定アクセス（jquants_refresh_token, kabu_api_password, slack_bot_token, duckdb_path, env, log_level 等）
- kabusys.data.schema.init_schema(db_path): DuckDB スキーマ初期化
- kabusys.data.jquants_client.fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
- kabusys.data.jquants_client.save_daily_quotes / save_financial_statements / save_market_calendar
- kabusys.data.news_collector.fetch_rss / save_raw_news / run_news_collection
- kabusys.data.pipeline.run_daily_etl: 日次 ETL（calendar → prices → financials → quality checks）
- kabusys.data.quality.run_all_checks: 品質チェック一括実行
- kabusys.data.calendar_management.is_trading_day / next_trading_day / prev_trading_day / get_trading_days

---

## ディレクトリ構成

以下は主要ファイルのツリー（抜粋）です:

- src/kabusys/
  - __init__.py                 (パッケージ定義、__version__)
  - config.py                   (環境変数 / 設定管理)
  - data/
    - __init__.py
    - jquants_client.py         (J-Quants API クライアント + DuckDB 保存)
    - news_collector.py         (RSS → raw_news + news_symbols)
    - schema.py                 (DuckDB スキーマ定義 & 初期化)
    - pipeline.py               (ETL パイプラインの実装)
    - calendar_management.py    (マーケットカレンダー管理ロジック)
    - audit.py                  (監査ログスキーマ初期化)
    - quality.py                (データ品質チェック)
  - strategy/
    - __init__.py               (戦略関連: 戦略を実装するモジュールを配置)
  - execution/
    - __init__.py               (発注 / 実行層を実装するモジュールを配置)
  - monitoring/
    - __init__.py               (監視・アラート用モジュールを配置)

---

## 運用上の注意 / トラブルシューティング

- API レート制限: J-Quants は 120 req/min を想定しており、fetch は内部で RateLimiter を使って待機します。大量取得時はしきい値を意識してください。
- リトライとトークン更新: HTTP 401 を受けた場合はトークンの自動更新を試みます（1回のみ）。リフレッシュ用トークンが無効だと失敗します。
- .env の自動読み込みはプロジェクトルート（.git または pyproject.toml を基準）を探索して行われます。テスト等で自動読み込みを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB のスキーマ作成は冪等です。既存 DB へは init_schema() を実行するとテーブルがなければ作成されます。
- ニュース収集では RSS の XML が不正な場合やリダイレクト先が内部アドレスの場合、安全のためスキップされます。
- 品質チェックはエラーの重大度に応じた判断を呼び出し元が行います。ETL はできる限り継続し、検出された問題を返却します。

---

## 開発・拡張のヒント

- strategy / execution / monitoring ディレクトリに戦略や約定ロジック、監視ロジックを実装してください。
- 単体テストでは環境変数の自動ロードを無効化し、settings をモックするか必要変数のみセットすることを推奨します。
- jquants_client の _request をモックすると API 呼び出しのエンドツーエンドテストが容易になります。
- ニュースの銘柄抽出は単純な 4 桁数字マッチです。より高度な NER を導入する場合は extract_stock_codes を拡張してください。

---

必要であれば README にサンプル .env.example や requirements.txt のテンプレート、実行スクリプト（systemd / cron / Airflow など）の例を追加します。追加希望があれば教えてください。