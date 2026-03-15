# KabuSys

バージョン: 0.1.0

KabuSys は日本株向けの自動売買基盤ライブラリです。市場データ取得・加工、特徴量生成、シグナル管理、発注（監査ログ含む）など自動売買システムに必要な土台機能を提供します。

主な設計方針:
- データは DuckDB に永続化（Raw / Processed / Feature / Execution の多層スキーマ）。
- 監査ログ（シグナル→発注→約定のトレース）を別テーブルで厳格に保存。
- 環境変数や .env ファイルから設定を読み込み、実行環境（開発・ペーパー・本番）を切替可能。

---

## 機能一覧

- 環境設定管理 (`kabusys.config`)
  - .env / .env.local をプロジェクトルートから自動ロード（OS 環境変数優先）
  - 必須設定の取得と検証（J-Quants トークン、kabu API パスワード、Slack トークン等）
  - 実行環境（development / paper_trading / live）・ログレベルの検証
- データスキーマ管理 (`kabusys.data`)
  - DuckDB 用テーブル群の定義と初期化（raw / processed / feature / execution）
  - インデックス作成と冪等的な初期化関数 `init_schema`, `get_connection`
- 監査ログ（Audit） (`kabusys.data.audit`)
  - シグナル → 発注要求 → 約定 を UUID で連鎖させ、完全トレースを可能にする監査スキーマ
  - `init_audit_schema`, `init_audit_db` による初期化（UTC タイムスタンプ運用）
- パッケージ化されたモジュール構成（strategy / execution / monitoring のエントリ）

---

## セットアップ手順

前提:
- Python 3.10 以上（型ヒントの構文により）
- pip が利用可能

1. リポジトリをクローン / ダウンロード
   - 例: git clone <リポジトリURL>

2. 仮想環境を作成して有効化（任意だが推奨）
   - python -m venv .venv
   - Unix/macOS: source .venv/bin/activate
   - Windows: .venv\Scripts\activate

3. 依存パッケージをインストール
   - 最低限必要なパッケージ: duckdb
   - 例:
     - pip install duckdb
   - （プロジェクトが pyproject.toml / requirements.txt を持つ場合）
     - pip install -e . あるいは pip install -r requirements.txt

4. 環境変数を準備
   - プロジェクトルート（.git または pyproject.toml を含むディレクトリ）から自動で `.env` および `.env.local` を読み込みます。
   - 必須環境変数（例）:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
     - SLACK_BOT_TOKEN
     - SLACK_CHANNEL_ID
   - 任意 / デフォルトあり:
     - KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
     - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
     - SQLITE_PATH (デフォルト: data/monitoring.db)
     - KABUSYS_ENV (development / paper_trading / live) デフォルト: development
     - LOG_LEVEL (DEBUG / INFO / WARNING / ERROR / CRITICAL) デフォルト: INFO
   - 自動ロードを無効化するには:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1（Unix 系）
     - set KABUSYS_DISABLE_AUTO_ENV_LOAD=1（Windows）

注意: .env のパーシングはシェルライクな振る舞い（export プレフィックス、クォート、インラインコメント一部対応）をサポートします。

---

## 使い方（簡単な例）

- 設定値取得:
  - from kabusys.config import settings
  - token = settings.jquants_refresh_token
  - db_path = settings.duckdb_path

- DuckDB スキーマ初期化（全テーブル）:
  - from kabusys.data.schema import init_schema
  - conn = init_schema(settings.duckdb_path)
  - この関数は親ディレクトリがなければ作成し、DDL を冪等的に実行します。

- 既存 DB へ接続:
  - from kabusys.data.schema import get_connection
  - conn = get_connection(settings.duckdb_path)

- 監査ログ（Audit）スキーマ初期化:
  - 既存の conn に追加:
    - from kabusys.data.audit import init_audit_schema
    - init_audit_schema(conn)
  - 監査専用 DB を作成して初期化:
    - from kabusys.data.audit import init_audit_db
    - audit_conn = init_audit_db("data/kabusys_audit.duckdb")

- 簡単なフロー例:
  - settings を使って DB パスを取得し、スキーマ初期化 -> データ挿入 -> クエリ実行 などが可能です。

---

## ディレクトリ構成

リポジトリの主要ファイル・ディレクトリ:

- src/kabusys/
  - __init__.py           — パッケージ初期化（version）
  - config.py             — 環境変数・設定管理（.env 自動ロード、Settings クラス）
  - execution/            — 発注関連モジュール（エントリ）
    - __init__.py
  - strategy/             — 戦略関連モジュール（エントリ）
    - __init__.py
  - data/                 — データ関連
    - __init__.py
    - schema.py           — DuckDB スキーマ定義 / init_schema / get_connection
    - audit.py            — 監査ログ（signal / order_request / executions）定義と初期化
    - (その他: audit と schema でデータ設計を提供)
  - monitoring/           — モニタリング関連（エントリ）
    - __init__.py

主要 API:
- kabusys.config.settings — アプリ設定取得アクセサ
- kabusys.data.schema.init_schema(db_path)
- kabusys.data.schema.get_connection(db_path)
- kabusys.data.audit.init_audit_schema(conn)
- kabusys.data.audit.init_audit_db(db_path)

---

## 備考 / 開発メモ

- DuckDB を永続化に用いるため、高速なローカル分析やトランザクション無しの軽量ワークロードに適しています。
- 監査ログのタイムスタンプは UTC 保存を前提にしています（init_audit_schema は SET TimeZone='UTC' を実行）。
- .env の読み込みはプロジェクトルート（.git または pyproject.toml を含む親ディレクトリ）から行います。これにより CWD に依存しない挙動を実現しています。
- 将来的に strategy / execution / monitoring に実際のアルゴリズムやブローカー連携を実装していく土台を提供します。

---

貢献・問い合わせ:
- バグ報告や機能提案は Issue を立ててください。README の補足や使用例の追加歓迎します。