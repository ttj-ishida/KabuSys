# KabuSys — 日本株自動売買システム

簡潔なプロジェクト説明、セットアップ手順、使い方、ディレクトリ構成をまとめた README です。コードベースはデータ取得（J-Quants、RSS）、ETL、品質チェック、DuckDB スキーマ、監査ログなどを含むデータ基盤と、自動売買の各レイヤ（strategy / execution / monitoring）を想定しています。

---

## プロジェクト概要

KabuSys は日本株の自動売買パイプライン基盤です。主な目的は以下です。

- J-Quants API から株価（日足）・財務データ・JPX カレンダーを安全に取得し DuckDB に保存
- RSS フィードからニュースを収集して記事と銘柄紐付けを行う
- ETL（差分取得・バックフィル）・品質チェック（欠損・スパイク・重複・日付不整合）を行う
- 監査ログ（シグナル→発注→約定のトレーサビリティ）を DuckDB に永続化
- 将来的な戦略層・実行層・監視層の統合を想定したモジュール構成

設計上の注力点:
- API レート制限・リトライ・トークン自動リフレッシュを備えた堅牢なデータ取得
- Look-ahead bias を避けるための fetched_at/UTC 時刻管理
- DuckDB による冪等保存（ON CONFLICT を活用）
- RSS 収集での SSRF/Gzip Bomb 対策、XML の安全パース

---

## 機能一覧

- 環境変数管理
  - .env / .env.local の自動読み込み（プロジェクトルート検出）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化
- J-Quants API クライアント（kabusys.data.jquants_client）
  - 日足（OHLCV）、財務データ（四半期 BS/PL）、市場カレンダー取得
  - レートリミット制御、リトライ、トークン自動リフレッシュ
  - DuckDB への冪等保存関数（save_daily_quotes 等）
- ニュース収集（kabusys.data.news_collector）
  - RSS フィード取得・前処理（URL 除去・空白正規化）
  - 記事ID: 正規化 URL の SHA-256（先頭32文字）
  - SSRF 対策、受信サイズ上限、defusedxml による安全パース
  - DuckDB への一括挿入（INSERT ... RETURNING）
  - テキストから銘柄コード（4桁）抽出と news_symbols への紐付け
- スキーマ定義と初期化（kabusys.data.schema）
  - Raw / Processed / Feature / Execution / Audit 層のテーブル定義
  - init_schema() / get_connection() 提供
- ETL パイプライン（kabusys.data.pipeline）
  - 差分更新、バックフィル、品質チェックの統合 run_daily_etl
  - run_prices_etl / run_financials_etl / run_calendar_etl 等
- カレンダー管理（kabusys.data.calendar_management）
  - is_trading_day / next_trading_day / prev_trading_day / get_trading_days
  - calendar_update_job（夜間バッチ）
- 品質チェック（kabusys.data.quality）
  - 欠損、スパイク、重複、日付不整合検出
  - QualityIssue データクラスを返す（severity: error / warning）
- 監査ログ（kabusys.data.audit）
  - signal_events, order_requests, executions の DDL と初期化
  - init_audit_schema / init_audit_db

---

## 前提（推奨環境）

- Python 3.10 以上（型注釈に PEP 604 の Union 表記（A | B）を使用）
- 必須ライブラリ（最低限）
  - duckdb
  - defusedxml
- その他の標準ライブラリ（urllib, logging, hashlib...）を使用

（実際のプロジェクトでは requirements.txt または pyproject.toml に依存関係を記載してください）

---

## セットアップ手順

1. リポジトリをクローンして仮想環境を作成
   - 例:
     - git clone ...
     - python -m venv .venv
     - source .venv/bin/activate

2. 必要パッケージをインストール
   - pip install duckdb defusedxml
   - （プロジェクトに requirements.txt があれば pip install -r requirements.txt）

3. パッケージをインストール（開発モード）
   - pip install -e .

4. 環境変数の設定
   - プロジェクトルートに .env を作成する（.env.example を参考に）
   - 必須の環境変数（少なくとも以下を設定してください）:
     - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD: kabuステーション API 用パスワード
     - SLACK_BOT_TOKEN: Slack 通知用 Bot トークン
     - SLACK_CHANNEL_ID: Slack チャンネル ID
   - オプション:
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
     - LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL（デフォルト: INFO）
     - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
   - 自動 .env ロードを無効化する場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

5. DuckDB スキーマ初期化
   - Python REPL やスクリプトで実行:
     - from kabusys.data import schema
     - conn = schema.init_schema("data/kabusys.duckdb")  # または settings.duckdb_path
   - 監査ログを別 DB に分ける場合:
     - from kabusys.data import audit
     - audit.init_audit_db("data/kabusys_audit.duckdb")  # または audit.init_audit_schema(conn)

---

## 使い方（例）

以下は最小限の利用例です。実行は適切な環境変数設定の上で行ってください。

- DuckDB 接続初期化（スキーマ作成）
  - from kabusys.data import schema
  - conn = schema.init_schema("data/kabusys.duckdb")

- 日次 ETL を実行する
  - from kabusys.data.pipeline import run_daily_etl
  - result = run_daily_etl(conn)
  - print(result.to_dict())  # ETL の結果概要

- 市場カレンダー夜間更新ジョブを実行する
  - from kabusys.data.calendar_management import calendar_update_job
  - saved = calendar_update_job(conn)
  - print("saved", saved)

- RSS ニュース収集
  - from kabusys.data import news_collector as nc
  - articles = nc.fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
  - new_ids = nc.save_raw_news(conn, articles)
  - print("new articles:", len(new_ids))
  - （known_codes を与えて銘柄紐付けを行う場合は run_news_collection を使用）

- J-Quants の ID トークンを明示的に取得する
  - from kabusys.data.jquants_client import get_id_token
  - token = get_id_token()  # settings.jquants_refresh_token が使われる

- 品質チェックを単体で実行
  - from kabusys.data.quality import run_all_checks
  - issues = run_all_checks(conn)
  - for i in issues: print(i)

簡単なコマンドライン実行（スクリプトを作成して実行することを推奨）:
- python -c "from kabusys.data import schema, pipeline; conn=schema.init_schema('data/kabusys.duckdb'); print(pipeline.run_daily_etl(conn).to_dict())"

---

## 環境変数（主要なもの）

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL (任意, デフォルト: http://localhost:18080/kabusapi)
- SLACK_BOT_TOKEN (必須)
- SLACK_CHANNEL_ID (必須)
- DUCKDB_PATH (任意, デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (任意, デフォルト: data/monitoring.db)
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL（デフォルト: INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 1 を設定すると .env 自動読み込みを無効化

settings オブジェクトからこれらを取得できます:
- from kabusys.config import settings
- settings.jquants_refresh_token, settings.duckdb_path, settings.is_live など

---

## 注意点 / 実装のポイント

- Python 3.10+ を想定（A | B の型注釈を使用）。
- J-Quants クライアントは内部で固定レートの RateLimiter（120 req/min）を利用します。大量取得時は間隔が自動調整されます。
- HTTP エラー（408/429/5xx）に対する指数バックオフ付きリトライを行い、401 発生時はリフレッシュトークンから id_token を再取得して一度だけリトライします。
- RSS 収集は SSRF、XML Bomb、Gzip Bomb (サイズ上限) などへの対策を実装しています（defusedxml、受信サイズ制限、ホストプライベート判定、リダイレクト検査など）。
- DuckDB への保存は基本的に冪等（ON CONFLICT DO UPDATE / DO NOTHING）です。
- 品質チェックは fail-fast ではなく、検出結果をリストで返して呼び出し側が対応を判断します。
- 自動読み込みされる .env はプロジェクトルート（.git または pyproject.toml を起点）を探索します。CWD に依存しません。

---

## ディレクトリ構成

以下はコードベースに含まれる主要ファイルの一覧（抜粋）です:

- src/kabusys/
  - __init__.py
  - config.py
  - execution/     (空の __init__.py。実行関連モジュールを配置)
  - strategy/      (空の __init__.py。戦略関連モジュールを配置)
  - monitoring/    (空の __init__.py。監視関連モジュールを配置)
  - data/
    - __init__.py
    - jquants_client.py        # J-Quants API クライアント、取得・保存関数
    - news_collector.py       # RSS ニュース収集・保存・銘柄抽出
    - schema.py               # DuckDB スキーマ定義・初期化
    - pipeline.py             # ETL パイプライン（run_daily_etl 等）
    - calendar_management.py  # 市場カレンダー管理・営業日判定
    - audit.py                # 監査ログ（signal/order/execution）の DDL と初期化
    - quality.py              # データ品質チェック
- pyproject.toml / setup.cfg 等（ある場合）

---

## 開発・拡張のポイント

- strategy / execution / monitoring ディレクトリは将来的な戦略ロジック、ブローカー API 実装、監視 / アラート機能を配置する想定です。
- DuckDB のスキーマは DataPlatform.md に基づく多層設計（Raw / Processed / Feature / Execution / Audit）を採用しています。新しいテーブルを追加する際は schema.init_schema の DDL 配列を拡張してください。
- 大量データ取得を行う場合は rate limit と retry の挙動、また ETL のバックフィルロジックを調整してください（pipeline.run_daily_etl の引数で調整可能）。
- テストを容易にするため、jquants_client._urlopen や news_collector._urlopen 等をモックしてネットワークリクエストを差し替えられる設計です。

---

もし README の別言語版、使用例のスクリプトテンプレート、あるいは CI/CD 用の初期化スクリプト（DB 初期化・ETL の cron 実行例）などが必要であれば、用途に合わせて追加で作成します。