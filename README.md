# KabuSys

日本株向けの自動売買基盤（ライブラリ）。  
主にデータ取得・永続化、スキーマ定義、監査ログの基盤機能を提供します。  
（戦略実装・発注ドライバ等はモジュールを分離しており、ここから組み合わせて利用します）

バージョン: 0.1.0

---

## 概要

KabuSys は、J-Quants 等のマーケットデータを取得して DuckDB に蓄積し、戦略・発注・監査のための基盤を提供するライブラリです。設計上の重要ポイントは次のとおりです。

- J-Quants API 用クライアント（ページネーション対応、リトライ、トークン自動リフレッシュ、レート制御）
- 取得データに対して取得時刻（fetched_at）を UTC で記録し、Look-ahead bias を防止
- DuckDB に対する冪等な INSERT（ON CONFLICT DO UPDATE）で重複データを上書き
- 監査ログ（signal → order_request → execution のトレーサビリティ）を専用テーブルで保持
- 環境変数／.env の自動読み込み機能（テスト用に無効化可能）

---

## 主な機能

- data.jquants_client
  - 株価日足（OHLCV）取得（fetch_daily_quotes）
  - 財務データ（四半期 BS/PL）取得（fetch_financial_statements）
  - JPX マーケットカレンダー取得（fetch_market_calendar）
  - rate limiting（120 req/min 固定スロットリング）
  - リトライ（指数バックオフ、最大3回、408/429/5xx 対応）
  - 401 を受けた場合の id_token 自動リフレッシュ
  - DuckDB へ冪等に保存するユーティリティ（save_daily_quotes, save_financial_statements, save_market_calendar）
- data.schema
  - Raw / Processed / Feature / Execution 層を想定した DuckDB DDL 定義と初期化（init_schema）
  - インデックス作成
- data.audit
  - 信号生成・発注要求・約定の監査ログ（UUID ベースのトレーサビリティ）を作成・初期化（init_audit_schema / init_audit_db）
- config
  - .env / .env.local をプロジェクトルートから自動読み込み（OS環境変数優先、.env.local が .env を上書き）
  - 必須環境変数取得時の検証ラッパ（Settings クラス）
  - 自動読み込みは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能

（execution, strategy, monitoring パッケージはエントリだけ存在し、各種機能は拡張して利用します）

---

## 要件

- Python 3.10+
- duckdb（DuckDB の Python バインディング）
- 標準ライブラリで HTTP に urllib を使用

必要に応じて Slack / kabu API 用クライアント等を追加で導入してください（本リポジトリでは環境変数の取り扱いを定義しています）。

---

## セットアップ

1. リポジトリをクローンしてワークディレクトリへ移動

   git clone <repo-url>
   cd <repo-dir>

2. 仮想環境を作成・有効化（推奨）

   python -m venv .venv
   source .venv/bin/activate  # Unix/macOS
   .venv\Scripts\activate     # Windows

3. 依存パッケージをインストール

   python -m pip install --upgrade pip
   python -m pip install duckdb

   ※ 開発中は `pip install -e .` 形式でインストールすることを想定しています（setup.py/pyproject があれば）。

4. 環境変数の設定

   プロジェクトルートに `.env` または `.env.local` を置くと自動で読み込まれます（OS環境変数が優先）。自動読み込みを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

   必須となる主な環境変数（Settings で参照）:

   - JQUANTS_REFRESH_TOKEN    (必須)
   - KABU_API_PASSWORD        (必須)
   - SLACK_BOT_TOKEN          (必須)
   - SLACK_CHANNEL_ID         (必須)
   - DUCKDB_PATH              (任意、デフォルト: data/kabusys.duckdb)
   - SQLITE_PATH              (任意、デフォルト: data/monitoring.db)
   - KABUSYS_ENV              (development | paper_trading | live, デフォルト: development)
   - LOG_LEVEL                (DEBUG | INFO | WARNING | ERROR | CRITICAL, デフォルト: INFO)

   例 (.env):

   JQUANTS_REFRESH_TOKEN=xxxxx
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C12345678
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=DEBUG

---

## 使い方（サンプル）

以下は基本的なワークフロー例です。

- DuckDB のスキーマ初期化と接続

   from kabusys.data import schema
   from kabusys.config import settings

   conn = schema.init_schema(settings.duckdb_path)

- J-Quants から日足を取得して保存

   from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes

   records = fetch_daily_quotes(code="7203")  # トヨタの例
   n = save_daily_quotes(conn, records)
   print(f"保存件数: {n}")

- 財務データやカレンダーも同様に fetch_* → save_* を利用

- 監査ログテーブルの初期化（既存 conn に追加）

   from kabusys.data.audit import init_audit_schema
   init_audit_schema(conn)

- 設定値の参照

   from kabusys.config import settings
   token = settings.jquants_refresh_token
   is_live = settings.is_live

- id_token を直接取得（必要な場面に応じて）

   from kabusys.data.jquants_client import get_id_token
   id_token = get_id_token()  # settings.jquants_refresh_token を使用して取得

注意:
- fetch_* 系は内部でレートリミット・リトライ・トークン管理を行います。大量リクエスト時は設計上のレート制御（120 req/min）に従ってください。
- DuckDB への保存関数は冪等になるよう実装されています（主に ON CONFLICT DO UPDATE を使用）。

---

## 主要モジュール説明 / ディレクトリ構成

src/kabusys/
- __init__.py
  - パッケージエクスポート（data, strategy, execution, monitoring）
- config.py
  - 環境変数の自動ロード (.env/.env.local) と Settings クラス

src/kabusys/data/
- __init__.py
- jquants_client.py
  - J-Quants API クライアント（取得・保存ユーティリティ）
- schema.py
  - DuckDB の DDL 定義と init_schema / get_connection
- audit.py
  - 監査ログテーブル（signal_events, order_requests, executions）の初期化
- other modules...
  - audit, schema, jquants_client に主要実装

src/kabusys/strategy/
- __init__.py
  - 戦略関連モジュールを置くためのパッケージ（実装は拡張）

src/kabusys/execution/
- __init__.py
  - 発注・ブローカーインターフェース等を置くパッケージ（実装は拡張）

src/kabusys/monitoring/
- __init__.py
  - モニタリング/アラート機能用のパッケージ（実装は拡張）

プロジェクトルートに .env(.local) を置くことで自動読み込みされます。自動読み込みはプロジェクトルートの判定に .git または pyproject.toml を使用します。

---

## 注意事項 / 補足

- Python バージョンは 3.10 以上を想定（型アノテーションに | ユニオン等を使用）。
- DuckDB ファイルのデフォルトパスは settings.duckdb_path で `data/kabusys.duckdb`。
- 監査ログではすべての TIMESTAMP を UTC に保存することを前提としています（init_audit_schema は SET TimeZone='UTC' を実行します）。
- .env のパースは Bourne shell ライクな形式を考慮しており、クォート・エスケープ・コメント処理に対応しています。
- 自動環境読み込みを無効化する: export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

---

必要であれば以下も作成します：
- さらに詳しい API リファレンス（関数一覧・引数の詳細）
- デプロイ手順（paper/live 環境での運用ガイド）
- 開発用の Makefile / docker-compose 例

ご希望があれば追記します。