# KabuSys

日本株の自動売買システム用ライブラリ（パッケージ骨組み）

バージョン: 0.1.0

概要:
- KabuSys は日本株のデータ取得・特徴量生成・売買信号・発注管理・モニタリングのための共通コンポーネント群を含む Python パッケージの骨組みです。
- 現在の実装は設定管理とデータベーススキーマ定義（DuckDB）を中心に提供しています。戦略・実行・モニタリング用のモジュール用のパッケージエントリポイントが用意されています。

主な特徴
- 環境変数ベースの設定管理（.env 自動読み込み機能）
- DuckDB を用いた多層（Raw / Processed / Feature / Execution）データスキーマの定義と初期化関数
- 開発 / ペーパー / 本番（live）切替を支援する環境変数設計
- Slack や kabuステーション、J-Quants 等の外部サービス用の設定キーを想定

インストール要件
- Python >= 3.10（型記法に Python 3.10 の union 演算子 (|) を使用）
- duckdb
- （任意）kabu API クライアント、Slack クライアント、J-Quants の SDK 等（実装に応じて追加）

セットアップ手順（簡易）
1. 仮想環境とパッケージのインストール
   ```bash
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate.bat  # Windows

   pip install --upgrade pip
   pip install duckdb
   # 開発インストール（プロジェクトに setup / pyproject がある場合）
   # pip install -e .
   ```

2. 環境変数設定
   プロジェクトルートに `.env`（および開発用に `.env.local`）を作成します。
   自動ロード優先順は: OS 環境変数 > .env.local > .env です。
   自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

   必須の環境変数（Settings クラスで必須とされているもの）:
   - JQUANTS_REFRESH_TOKEN
   - KABU_API_PASSWORD
   - SLACK_BOT_TOKEN
   - SLACK_CHANNEL_ID

   任意（デフォルトあり）:
   - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
   - LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL) — デフォルト: INFO
   - DUCKDB_PATH — デフォルト: data/kabusys.duckdb
   - SQLITE_PATH — デフォルト: data/monitoring.db
   - KABUSYS_DISABLE_AUTO_ENV_LOAD — 自動読み込み無効化フラグ

   .env の例:
   ```
   JQUANTS_REFRESH_TOKEN='your_jquants_token'
   KABU_API_PASSWORD='your_kabu_password'
   SLACK_BOT_TOKEN='xoxb-...'
   SLACK_CHANNEL_ID='C01234567'
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   DUCKDB_PATH=data/kabusys.duckdb
   ```

使い方（基本）
- 設定の読み取り
  ```python
  from kabusys.config import settings

  print(settings.jquants_refresh_token)
  print(settings.kabu_api_base_url)
  print(settings.is_live)
  ```

- DuckDB スキーマの初期化
  ```python
  from kabusys.data.schema import init_schema, get_connection
  from kabusys.config import settings

  db_path = settings.duckdb_path  # Path オブジェクト
  conn = init_schema(db_path)     # テーブルがなければ作成して接続を返す

  # 既存 DB へ単に接続する場合
  conn2 = get_connection(db_path)
  ```

- .env の自動ロード挙動の注意点
  - パッケージ初期化時にプロジェクトルート（.git または pyproject.toml を探索）を検出できれば、自動で .env を読み込みます。
  - .env の行解析はシェルライクな書式をサポート（export プレフィックス、シングル/ダブルクォート、エスケープ、行内コメント処理など）。
  - .env.local に記載された値は .env 上書き（OS 環境変数は常に優先され保護されます）。

モジュール構成（主要 API）
- kabusys.config
  - settings: Settings インスタンス（各種環境変数をプロパティとして取得）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード制御
- kabusys.data.schema
  - init_schema(db_path) -> duckdb connection: 全テーブルを作成（冪等）
  - get_connection(db_path) -> duckdb connection: 単に接続を返す
- kabusys.data (パッケージ)
- kabusys.strategy (パッケージ)
- kabusys.execution (パッケージ)
- kabusys.monitoring (パッケージ)

ディレクトリ構成
（プロジェクトルート想定: src/kabusys 以下）
- src/
  - kabusys/
    - __init__.py                # パッケージメタ情報（__version__ 等）
    - config.py                  # 環境変数・設定管理（.env 自動読み込み含む）
    - data/
      - __init__.py
      - schema.py                # DuckDB スキーマ定義 + init_schema()
    - strategy/
      - __init__.py
      # （将来的に戦略モジュールを追加）
    - execution/
      - __init__.py
      # （発注・注文管理モジュールを追加）
    - monitoring/
      - __init__.py

詳細（実装上のポイント）
- DuckDB スキーマは Raw / Processed / Feature / Execution の 3 層＋実行層でテーブルを定義しています。テーブル作成は init_schema() で行い、インデックスも作成します。
- 環境変数のパースはシェルライクで、クォート内のエスケープやインラインコメントの扱いにも注意して実装されています。
- Settings.env は 'development' / 'paper_trading' / 'live' のいずれかのみを許容します。LOG_LEVEL の値も検証されます。

今後の拡張案
- データ取得（J-Quants、ニュース、kabuステーション）モジュールの実装
- 注文実行・約定処理の実装（kabu API 連携）
- 戦略テンプレート / バックテスト機能
- モニタリング用 UI（Slack 通知、ダッシュボード）

ライセンス
- プロジェクトに別途記載がなければ適宜追加してください。

問い合わせ / 開発
- 開発者向けに .env.example を用意しておくとセットアップが容易になります。
- テストや CI を導入する際は KABUSYS_DISABLE_AUTO_ENV_LOAD を使って自動読み込みを無効化してください。

以上。README に追加したい具体的な内容（例: .env.example、依存関係ファイル、用途別の使い方サンプル）があれば教えてください。補足して更新します。