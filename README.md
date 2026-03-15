KabuSys
=======

日本株向けの自動売買（バックテスト / 実運用補助）向けライブラリです。市場データの取得・格納、特徴量テーブル、発注／約定管理などを想定したスキーマと、環境変数ベースの設定読み込み機構を提供します。

主な目的
- DuckDB を用いたデータレイヤ（Raw / Processed / Feature / Execution）のスキーマ定義と初期化
- 環境変数／.env ファイルからの設定管理（自動ロード機能）
- 戦略（strategy）, 発注（execution）, 監視（monitoring）モジュールの枠組み提供

バージョン
- パッケージバージョン: 0.1.0（src/kabusys/__init__.py）

機能一覧
- 環境変数・設定管理（kabusys.config.Settings）
  - .env, .env.local を自動ロード（OS 環境変数を優先）
  - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  - 必須設定の取得（未設定時は ValueError）
  - サポートする主要設定:
    - JQUANTS_REFRESH_TOKEN (必須)
    - KABU_API_PASSWORD (必須)
    - KABU_API_BASE_URL (省略時デフォルト有)
    - SLACK_BOT_TOKEN (必須)
    - SLACK_CHANNEL_ID (必須)
    - DUCKDB_PATH, SQLITE_PATH（デフォルトパス指定あり）
    - KABUSYS_ENV (development / paper_trading / live)
    - LOG_LEVEL (DEBUG/INFO/WARNING/ERROR/CRITICAL)
- DuckDB スキーマ管理（kabusys.data.schema）
  - Raw / Processed / Feature / Execution 層のテーブル定義（銘柄・日付を扱う構造）
  - インデックス定義
  - init_schema(db_path) による DB 初期化（冪等）
  - get_connection(db_path) で既存 DB へ接続
- パッケージ構成の骨組み（strategy, execution, monitoring パッケージのプレースホルダ）

セットアップ手順
前提
- Python 3.10 以上（型注釈に X | Y 形式を使用しているため）
- pip が利用できること

1) リポジトリをクローン／取得
   git clone <repo-url>
   cd <repo-root>

2) （任意）仮想環境を作る
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows

3) 依存パッケージをインストール
   - 本リポジトリの依存ファイル（requirements.txt / pyproject.toml）が無い場合は最低限 duckdb を入れてください：
     pip install duckdb
   - 他に必要なパッケージ（例: slack-sdk 等）は用途に応じて追加してください。

4) パッケージを編集可能モードでインストール（任意）
   pip install -e .

設定（.env）
- プロジェクトルートに .env および .env.local を置くことで自動読み込みされます。
- 読み込み順:
  OS 環境変数 > .env.local（上書き可） > .env（既存変数は上書きしない）
- 自動読み込みを無効化するには環境変数を設定:
  export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
- .env の書式:
  - コメント行は先頭に # を置く
  - export KEY=VAL の形式も許容
  - 値はシングル／ダブルクォートで囲めます。クォート内ではバックスラッシュエスケープが対応
  - 非クォート時、# の直前が空白またはタブの場合はコメントとして扱います

必須環境変数（例）
- JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
- KABU_API_PASSWORD=your_kabu_station_api_password
- SLACK_BOT_TOKEN=xoxb-...
- SLACK_CHANNEL_ID=C01234567

オプション（例）
- KABUSYS_ENV=development
- LOG_LEVEL=INFO
- DUCKDB_PATH=data/kabusys.duckdb
- SQLITE_PATH=data/monitoring.db
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1

使い方（簡単なコード例）
- 設定を参照する
  from kabusys.config import settings
  token = settings.jquants_refresh_token
  if settings.is_live:
      print("ライブ環境です")

- DuckDB スキーマを初期化する
  from kabusys.data.schema import init_schema
  conn = init_schema("data/kabusys.duckdb")
  # conn は duckdb.DuckDBPyConnection オブジェクト

- 既存 DB に接続する（スキーマ初期化は行わない）
  from kabusys.data.schema import get_connection
  conn = get_connection("data/kabusys.duckdb")

- .env の自動読み込みを無効化してテストする
  import os
  os.environ["KABUSYS_DISABLE_AUTO_ENV_LOAD"] = "1"
  # その上で import kabusys.config すると自動ロードは走りません

ディレクトリ構成
- src/
  - kabusys/
    - __init__.py                # パッケージ定義（__version__ 等）
    - config.py                  # 環境変数・設定読み込み / Settings
    - data/
      - __init__.py
      - schema.py                # DuckDB スキーマ定義・初期化（init_schema, get_connection）
    - strategy/
      - __init__.py              # 戦略モジュールのプレースホルダ
    - execution/
      - __init__.py              # 発注／実行モジュールのプレースホルダ
    - monitoring/
      - __init__.py              # 監視・メトリクス用プレースホルダ

注意点 / 補足
- init_schema() は存在しない親ディレクトリを自動作成します。":memory:" を渡すとインメモリ DB を利用できます。
- schema.py の DDL は外部キーや制約を多用しています。既存データ互換を考える場合は注意して運用してください。
- config の自動読み込みはプロジェクトルート（.git または pyproject.toml を基準）を見つけることで動作します。パッケージ形式で配布後も動作するよう、__file__ を基点に親ディレクトリを探索します。プロジェクトルートが見つからない場合は自動ロードをスキップします。

貢献
- 戦略ロジック、実行インターフェース（kabuステーションやAPIクライアント）、監視ダッシュボードなどの実装を歓迎します。README にないセットアップ要件が増えたら追記してください。

以上。必要であれば README に含めたい追加の使用例（戦略実行フロー、テーブルサンプルクエリ、CI 設定など）を教えてください。