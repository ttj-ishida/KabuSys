# KabuSys

日本株自動売買プラットフォームのコアライブラリ（KabuSys）。  
データ取得・ETL・品質チェック・ニュース収集・監査ログ等の基盤機能を提供します。

---

## 概要

KabuSys は日本株の自動売買システム向けに設計された内部ライブラリ群です。主に以下を提供します。

- J-Quants API からの市場データ（株価・財務・カレンダー）取得クライアント
- RSS ベースのニュース収集（正規化・SSRF対策・トラッキング除去）
- DuckDB を用いたスキーマ定義・初期化
- 日次 ETL パイプライン（差分取得・バックフィル・品質チェック）
- データ品質チェック（欠損・重複・スパイク・日付整合性）
- 監査ログ（signal → order_request → execution のトレーサビリティ）
- 設定管理（環境変数 / .env ロード）

設計上の特徴：
- API レート制御とリトライ（J-Quants クライアント）
- 冪等性を考慮した DB 保存（ON CONFLICT/DO UPDATE / DO NOTHING）
- Look-ahead bias 防止のため fetched_at 等で取得時刻を記録
- SSRF・XML Bomb 等のセキュリティ対策（news_collector）

---

## 主な機能一覧

- kabusys.config
  - .env ファイルの自動ロード（プロジェクトルート基準）
  - 必須環境変数のラップ（Settings）
- kabusys.data.jquants_client
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - save_daily_quotes / save_financial_statements / save_market_calendar
  - レートリミット、リトライ、トークン自動リフレッシュ等を実装
- kabusys.data.news_collector
  - RSS フィード取得・正規化・保存（raw_news / news_symbols）
  - URL 正規化、トラッキングパラメータ除去、SSRF対策、gzip制限
- kabusys.data.schema
  - DuckDB のテーブル定義（Raw / Processed / Feature / Execution 層）
  - init_schema() で DB 初期化
- kabusys.data.pipeline
  - 差分 ETL（価格・財務・カレンダー）
  - run_daily_etl()：日次パイプライン（品質チェック含む）
- kabusys.data.quality
  - 各種品質チェック（欠損、重複、スパイク、日付不整合）
  - QualityIssue による問題レポート
- kabusys.data.audit
  - 監査ログ用スキーマ（signal_events, order_requests, executions）
  - init_audit_schema / init_audit_db

---

## 前提・依存

推奨環境
- Python 3.10+（型アノテーションの union 演算子（|）等を使用）
- duckdb
- defusedxml

インストール例（仮想環境推奨）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb defusedxml
# パッケージを開発モードでインストールする場合（プロジェクトに setuptools/pyproject があれば）:
# pip install -e .
```

（プロジェクトの packaging に依存するため、実際の要件ファイルがある場合はそちらを参照してください）

---

## 環境変数と .env の自動ロード

KabuSys はプロジェクトルート（.git または pyproject.toml を含むディレクトリ）を探索し、以下の順序で環境変数を読み込みます：

1. OS 環境変数（最優先）
2. .env.local（存在すれば上書き、ただし OS のキーは保護）
3. .env（存在すれば読み込み。ただし OS に既にあるキーは上書きしない）

自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト時などに便利です）。

主な必須環境変数（Settings から）:
- JQUANTS_REFRESH_TOKEN — J-Quants リフレッシュトークン（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）
- SLACK_BOT_TOKEN — Slack ボットトークン（必須）
- SLACK_CHANNEL_ID — Slack チャンネルID（必須）

オプション（デフォルトあり）:
- KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（デフォルト: data/monitoring.db）
- KABUSYS_ENV（development | paper_trading | live、デフォルト: development）
- LOG_LEVEL（DEBUG | INFO | WARNING | ERROR | CRITICAL、デフォルト: INFO）

.env の書式については config._parse_env_line の挙動に従います（export プレフィックス、クォート、コメント処理などに対応）。

---

## セットアップ手順

1. リポジトリをクローンする
   ```bash
   git clone <repo-url>
   cd <repo-dir>
   ```

2. 仮想環境の作成（任意）
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```

3. 依存パッケージをインストール
   ```bash
   pip install duckdb defusedxml
   # その他の依存がある場合は requirements.txt / pyproject.toml を参照
   ```

4. 環境変数を用意
   - プロジェクトルートに `.env`（または `.env.local`）を作成し、必要なキーを設定します。例:
     ```
     JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     KABU_API_PASSWORD=your_kabu_password
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567
     DUCKDB_PATH=data/kabusys.duckdb
     KABUSYS_ENV=development
     LOG_LEVEL=INFO
     ```
   - 必須キーが未設定の場合、settings プロパティは ValueError を投げます。

5. DuckDB スキーマ初期化
   - Python REPL かスクリプトで実行:
     ```python
     from kabusys.data.schema import init_schema
     from kabusys.config import settings
     init_schema(settings.duckdb_path)
     ```
   - 監査ログスキーマを別途初期化する場合:
     ```python
     from kabusys.data.schema import get_connection
     from kabusys.data.audit import init_audit_schema
     conn = get_connection(settings.duckdb_path)
     init_audit_schema(conn)
     ```

---

## 使い方（例）

- 日次 ETL の実行（最も基本的な使用例）:
  ```python
  from kabusys.config import settings
  from kabusys.data.schema import init_schema, get_connection
  from kabusys.data.pipeline import run_daily_etl

  # 初期化（初回のみ）
  conn = init_schema(settings.duckdb_path)

  # 日次 ETL 実行（今日を対象）
  result = run_daily_etl(conn)
  print(result.to_dict())
  ```

- J-Quants から特定銘柄の株価を手動で取得して保存する:
  ```python
  from kabusys.data import jquants_client as jq
  from kabusys.data.schema import get_connection
  from kabusys.config import settings
  from datetime import date

  conn = get_connection(settings.duckdb_path)
  records = jq.fetch_daily_quotes(code="7203", date_from=date(2024,1,1), date_to=date(2024,12,31))
  saved = jq.save_daily_quotes(conn, records)
  print(f"saved: {saved}")
  ```

- RSS ニュース収集ジョブ:
  ```python
  from kabusys.data.news_collector import run_news_collection
  from kabusys.data.schema import get_connection
  from kabusys.config import settings

  conn = get_connection(settings.duckdb_path)
  # known_codes を渡すと記事 → 銘柄紐付けを行う
  known_codes = {"7203", "6758", "9984"}
  results = run_news_collection(conn, known_codes=known_codes)
  print(results)
  ```

- 品質チェックを単独で実行:
  ```python
  from kabusys.data.quality import run_all_checks
  from kabusys.data.schema import get_connection

  conn = get_connection("data/kabusys.duckdb")
  issues = run_all_checks(conn)
  for issue in issues:
      print(issue)
  ```

---

## 注意点 / 実装上のポイント

- J-Quants クライアントはレート制御（120 req/min）と自動リトライを実装しています。429（Too Many Requests）などのレスポンス時は Retry-After ヘッダを尊重します。
- get_id_token() はリフレッシュトークンを使って ID トークンを取得し、401（Unauthorized）時は自動でトークン再取得を試みます（無限再帰を防ぐ設計）。
- news_collector は SSRF・XML 脆弱性対策（ホストのプライベート判定、defusedxml、gzip サイズ制限等）を備えています。
- DB 保存は可能な限り冪等（ON CONFLICT）にしてあり、ETL の再実行が安全に行えるようになっています。
- settings.env の値は `"development" | "paper_trading" | "live"` のいずれかで、is_live / is_paper / is_dev で環境判定可能です。

---

## ディレクトリ構成

（パッケージルートは src/kabusys を想定）

- src/kabusys/
  - __init__.py
    - パッケージのバージョン・公開 API
  - config.py
    - 環境変数 / .env ロード、Settings クラス
  - data/
    - __init__.py
    - jquants_client.py
      - J-Quants API クライアント（取得 / 保存）
    - news_collector.py
      - RSS ニュース収集・前処理・保存・銘柄抽出
    - schema.py
      - DuckDB のスキーマ定義と初期化（init_schema / get_connection）
    - pipeline.py
      - 日次 ETL パイプライン（差分取得、backfill、品質チェック）
    - audit.py
      - 監査ログ関連テーブルの初期化（init_audit_schema / init_audit_db）
    - quality.py
      - データ品質チェック（QualityIssue 定義と各チェック）
  - strategy/
    - __init__.py
    - （戦略ロジックを置くためのスペース）
  - execution/
    - __init__.py
    - （注文実行・ブローカー連携ロジックのスペース）
  - monitoring/
    - __init__.py
    - （監視・アラート用コードのスペース）

---

## 開発・拡張のヒント

- strategy/、execution/、monitoring/ はフレームワーク部分を切り出すための空モジュールです。各戦略の実装や発注ロジックはここに追加してください。
- DB スキーマは schema.py に集約されています。新しいテーブル追加やカラム変更時は init_schema の DDL を更新してください（冪等性を保つため CREATE TABLE IF NOT EXISTS を使用）。
- テスト時に .env の自動ロードを抑止するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- 単体テストでは jquants_client のネットワーク呼び出しや news_collector._urlopen をモックすると容易です。

---

この README はコードベースに含まれる実装に基づいて作成しています。実際の運用・デプロイ時は追加の設定（証券会社 API の資格情報、Slack 設定、監視設定など）やセキュリティ運用を必ず行ってください。