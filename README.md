# KabuSys

日本株自動売買システムの軽量ライブラリ（ライブラリ本体の一部）。  
このリポジトリはデータ取得・スキーマ定義・監査ログなどの基盤機能を提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株の自動売買パイプラインを構成するための基盤モジュール群です。  
主に以下を提供します。

- J-Quants API からの市場データ（株価日足・財務・マーケットカレンダー）の取得と DuckDB への保存
- DuckDB 用のスキーマ（Raw / Processed / Feature / Execution 層）定義と初期化
- 監査（トレーサビリティ）用テーブルの定義と初期化
- 環境変数を読み込む設定ユーティリティ（.env 自動読み込みを含む）

設計上のポイント：
- J-Quants API はレート制限（120 req/min）を順守するために固定間隔の RateLimiter を使用
- リトライ（指数バックオフ）と 401 時のトークン自動リフレッシュ対応
- データ取得時に fetched_at を UTC で記録し Look-ahead Bias を防止
- DuckDB への保存は冪等（ON CONFLICT ... DO UPDATE）で重複を排除

---

## 機能一覧

- 環境設定管理（kabusys.config）
  - .env / .env.local の自動読み込み（プロジェクトルート検出）
  - 必須変数チェック（_require）
  - KABUSYS_ENV（development / paper_trading / live）や LOG_LEVEL の検証
- J-Quants クライアント（kabusys.data.jquants_client）
  - get_id_token: リフレッシュトークンから idToken を取得
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - save_daily_quotes / save_financial_statements / save_market_calendar（DuckDB へ保存）
  - レート制御・リトライ・ページネーション対応
- DuckDB スキーマ（kabusys.data.schema）
  - init_schema: DB を初期化して全テーブル・インデックスを作成
  - get_connection: 既存 DB への接続取得
- 監査ログ（kabusys.data.audit）
  - init_audit_schema / init_audit_db: 監査用テーブル（signal_events / order_requests / executions）を初期化
  - 監査用インデックスと TIMESTAMP を UTC に固定する設定
- その他の名前空間（strategy / execution / monitoring）用のプレースホルダ

---

## セットアップ手順

前提:
- Python 3.10 以上（typing における "|" 型や型ヒントの使用のため）
- ネットワーク経由の API 呼び出しができること

1. リポジトリをクローン（既にクローン済みなら省略）
   ```
   git clone <repo-url>
   cd <repo-dir>
   ```

2. 仮想環境を作成・有効化（任意）
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

3. 必要なパッケージのインストール（最低限 duckdb）
   - pip でインストール:
     ```
     pip install duckdb
     ```
   - 開発中にパッケージを編集して使う場合:
     ```
     pip install -e .
     ```
     （プロジェクトに setup.py/pyproject.toml がある前提です）

4. 環境変数の設定
   - プロジェクトルートに `.env`（必要に応じて `.env.local`）を作成すると自動で読み込まれます。
   - 自動読み込みを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト用途など）。
   - 主に必要な環境変数（例）:
     - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
     - KABU_API_PASSWORD: kabuステーション API パスワード（必須）
     - KABU_API_BASE_URL: kabu API のベース URL（省略可、デフォルト: http://localhost:18080/kabusapi）
     - SLACK_BOT_TOKEN: Slack 用 Bot トークン（必須）
     - SLACK_CHANNEL_ID: 通知先 Slack チャネル ID（必須）
     - DUCKDB_PATH: DuckDB ファイルパス（省略時 data/kabusys.duckdb）
     - SQLITE_PATH: SQLite 監視 DB パス（省略時 data/monitoring.db）
     - KABUSYS_ENV: development | paper_trading | live（省略時 development）
     - LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL（省略時 INFO）

   例 (.env):
   ```
   JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxx
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

---

## 使い方（基本例）

ここでは J-Quants から日足を取得して DuckDB に保存する流れを示します。

1. DB スキーマ初期化
   ```python
   from kabusys.data.schema import init_schema
   from kabusys.config import settings

   conn = init_schema(settings.duckdb_path)
   ```

2. データ取得と保存
   ```python
   from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes

   # 例: 全銘柄の直近データを取得
   records = fetch_daily_quotes()
   saved = save_daily_quotes(conn, records)
   print(f"saved {saved} rows")
   ```

3. ID トークンを直接取得する（必要に応じて）
   ```python
   from kabusys.data.jquants_client import get_id_token
   token = get_id_token()  # settings.jquants_refresh_token を使用
   ```

4. 財務データやマーケットカレンダーの取得・保存
   ```python
   from kabusys.data.jquants_client import (
       fetch_financial_statements, save_financial_statements,
       fetch_market_calendar, save_market_calendar
   )

   fin = fetch_financial_statements(date_from=..., date_to=...)
   save_financial_statements(conn, fin)

   cal = fetch_market_calendar()
   save_market_calendar(conn, cal)
   ```

注意点:
- fetch_* 系関数はページネーションに対応し、内部で id_token キャッシュ・自動リフレッシュを行います。
- API はレート制限を考慮しており、1分あたり 120 リクエストを超えない実装になっています。
- save_* 系関数は冪等（ON CONFLICT DO UPDATE）なので何度実行しても重複による問題を避けられます。

監査ログ（signal / order / execution）の初期化:
```python
from kabusys.data.audit import init_audit_schema

init_audit_schema(conn)  # 既存の conn に監査テーブルを追加
# または独立した監査専用 DB を作る:
# from kabusys.data.audit import init_audit_db
# audit_conn = init_audit_db("data/kabusys_audit.duckdb")
```

ログ設定と環境モード:
- settings.env によって is_dev / is_paper / is_live を判定できます。運用時は `KABUSYS_ENV=live` を設定してください。
- LOG_LEVEL によりロギングレベルを制御します（ERROR 等）。

---

## ディレクトリ構成

リポジトリの主要ファイル・モジュール:

- src/
  - kabusys/
    - __init__.py
    - config.py                # 環境変数・設定管理（.env 自動読み込み、必須チェック）
    - data/
      - __init__.py
      - jquants_client.py      # J-Quants API クライアント（取得・保存ロジック）
      - schema.py              # DuckDB スキーマ定義・初期化
      - audit.py               # 監査ログ（signal / order_request / executions）
      - (raw_news 等のテーブル定義も含む)
    - strategy/
      - __init__.py            # 戦略関連モジュール（プレースホルダ）
    - execution/
      - __init__.py            # 発注/ブローカー関連（プレースホルダ）
    - monitoring/
      - __init__.py            # 監視関連（プレースホルダ）

（README に含めたのはコードベースに存在した主要モジュールのみです。）

---

## 開発・運用上の注意

- Python バージョンは 3.10 以上を推奨します（型ヒントに | を使用）。
- .env パーサはシェルスタイルのクォートやエスケープ、コメントをある程度サポートしますが、極端に複雑な記述は避けてください。
- 自動 .env 読み込みはプロジェクトルート（.git または pyproject.toml を起点に探索）から行われます。テスト等で自動読み込みを避ける場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- J-Quants のレート制限や HTTP エラー処理は組み込まれていますが、大量データ取得時は外部制御（インターバル・スケジューラ）を考慮してください。
- 監査ログは削除しない前提です。FK 制約は ON DELETE RESTRICT を想定しています。

---

## ライセンス / 貢献

この README はコードベースの説明を目的として生成されています。実際の利用にあたっては各 API（J-Quants / kabu ステーション / Slack 等）の利用規約に従ってください。貢献や拡張は Pull Request を歓迎します。

---

必要であれば README にサンプル .env.example、CI / デプロイ手順、細かい API 使用例（ページネーションやエラーハンドリングの挙動）を追記します。どの部分を詳しく書いてほしいか教えてください。