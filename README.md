# KabuSys

日本株向け自動売買システムのコアライブラリ（プロトタイプ）

バージョン: 0.1.0

概要
---
KabuSys は日本株の自動売買システムのための基盤コンポーネント群です。  
主に以下を提供します。

- 環境変数 / 設定の安全な読み込みと検証（.env 自動ロード）
- DuckDB を使った多層データスキーマ定義（Raw / Processed / Feature / Execution）
- 戦略・発注・監視のためのパッケージ分割（strategy / execution / monitoring の骨組み）
- DB 初期化ユーティリティおよび接続ヘルパー

特徴一覧
---
- 環境設定管理（src/kabusys/config.py）
  - .env / .env.local をプロジェクトのルート（.git または pyproject.toml を探索）から自動読込
  - OS 環境変数を保護しつつ .env.local で上書き可能
  - 必須値の取得メソッド・バリデーション（例: KABUSYS_ENV, LOG_LEVEL の妥当性チェック）
  - 自動ロードは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能（テスト用）
- DuckDB スキーマ定義（src/kabusys/data/schema.py）
  - Raw / Processed / Feature / Execution の各レイヤーのテーブル DDL を用意
  - インデックス定義・テーブル作成順を考慮した初期化関数 `init_schema(db_path)` を提供
  - 既存テーブルはスキップするため冪等
- モジュール分割
  - strategy, execution, monitoring のパッケージ骨組みを含む（実装は容易に拡張可能）

動作に必要な主な環境変数
---
必須（Settings._require で検査される）
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD
- SLACK_BOT_TOKEN
- SLACK_CHANNEL_ID

オプション（デフォルトあり）
- KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (デフォルト: data/monitoring.db)
- KABUSYS_ENV (有効値: development, paper_trading, live; デフォルト: development)
- LOG_LEVEL (DEBUG, INFO, WARNING, ERROR, CRITICAL; デフォルト: INFO)

セットアップ手順
---
前提
- Python 3.10 以上（| 型ヒント等を使用）
- duckdb パッケージ

1. リポジトリをクローンしてパッケージをインストール（開発モード）
   ```bash
   git clone <repo-url>
   cd <repo-root>
   pip install -e .
   ```
   必要な依存が記載された要件ファイルがあればそちらを使ってください（本コードベースには duckdb のみ必須として参照されています）。
   例:
   ```bash
   pip install duckdb
   ```

2. .env ファイルを作成
   - プロジェクトルート（.git または pyproject.toml のあるディレクトリ）に `.env` または `.env.local` を置くと自動で読み込まれます。
   - 自動ロードを無効化したい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

   サンプル（.env.example として作成する例）
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   KABU_API_PASSWORD=your_kabu_api_password
   KABU_API_BASE_URL=http://localhost:18080/kabusapi
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C0123456789
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

.env 読み込みの挙動（補足）
- 読み込み優先順位は OS 環境変数 > .env.local > .env です（実装では .env を先に読み、.env.local を override=True で上書き。ただし OS 環境変数は保護されます）。
- .env のパースはシンプルなシェル互換を意識しており、`export KEY=val`、シングル/ダブルクォート、エスケープやインラインコメント（スペースの前の # はコメント扱い）等に対応しています。

使い方（基本例）
---
設定の参照
```python
from kabusys.config import settings

token = settings.jquants_refresh_token
if settings.is_live:
    print("LIVE mode")
```

DuckDB スキーマ初期化
```python
from kabusys.data.schema import init_schema
from kabusys.config import settings

# settings.duckdb_path は Path を返す（デフォルト data/kabusys.duckdb）
conn = init_schema(settings.duckdb_path)

# conn は duckdb.DuckDBPyConnection。SQL 実行やクエリが可能
rows = conn.execute("SELECT name FROM sqlite_master").fetchall()  # 例
```

既存 DB への接続
```python
from kabusys.data.schema import get_connection
conn = get_connection("data/kabusys.duckdb")
```

サブパッケージ拡張
- strategy, execution, monitoring パッケージに戦略ロジック、発注実装、監視処理を実装してください。
- データは DuckDB のテーブルに保存し、features / ai_scores / signals / orders / trades / positions 等のテーブルを通してワークフローを構成できます。

ディレクトリ構成
---
（主要ファイルのみ抜粋）

- src/
  - kabusys/
    - __init__.py            # パッケージ初期化、__version__ = "0.1.0"
    - config.py              # 環境変数・設定管理（自動 .env ロード、Settings クラス）
    - data/
      - __init__.py
      - schema.py            # DuckDB スキーマ定義・初期化関数（init_schema, get_connection）
    - strategy/
      - __init__.py          # 戦略ロジック用パッケージ（拡張先）
    - execution/
      - __init__.py          # 発注/約定処理用パッケージ（拡張先）
    - monitoring/
      - __init__.py          # 監視用パッケージ（拡張先）

主要 API リファレンス（抜粋）
---
- kabusys.__version__: パッケージバージョン
- kabusys.config.settings: Settings インスタンス
  - jquants_refresh_token, kabu_api_password, kabu_api_base_url, slack_bot_token, slack_channel_id
  - duckdb_path (Path), sqlite_path (Path)
  - env, log_level, is_live, is_paper, is_dev
- kabusys.data.schema.init_schema(db_path) -> duckdb.DuckDBPyConnection
  - DuckDB DB を初期化し、全テーブル／インデックスを作成（冪等）
- kabusys.data.schema.get_connection(db_path) -> duckdb.DuckDBPyConnection
  - 既存 DB への接続（スキーマ初期化は行わない）

注意事項 / 今後の拡張
---
- strategy / execution / monitoring パッケージは骨組みのみで、実際の売買ロジック、kabu API との通信、Slack 通知などは実装が必要です。
- 本リポジトリは基盤（設定管理・スキーマ定義）を提供することを目的としており、リアルマネーを扱う場合は十分なテスト・バリデーションを行ってください。
- 環境変数に機密情報（API トークン等）を置く際は取り扱いに注意してください。

ライセンス
---
（プロジェクトに応じたライセンス情報をここに記載してください）

お問い合わせ / 貢献
---
プルリクエストや issue は歓迎します。README に書かれていない利用方法や期待する機能があれば Issue を投げてください。