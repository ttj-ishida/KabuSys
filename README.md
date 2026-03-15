kabusys
=======

日本株向けの自動売買システム用ライブラリ（パッケージ）です。市場データの保存・整形、特徴量生成、発注・約定の管理、監視など、自動売買システムの基盤となる機能群を提供することを目的としています。

バージョン
---------
0.1.0

概要
----
kabusys は以下の主要な責務を持ちます。

- 環境変数・設定の管理（自動で .env/.env.local をロード）
- DuckDB を用いた多層スキーマ（Raw / Processed / Feature / Execution）の定義と初期化
- 戦略（strategy）、発注/実行（execution）、監視（monitoring）などのモジュールの枠組み

主な機能
--------
- 設定管理（kabusys.config.Settings）
  - J-Quants / kabuステーション / Slack / DB パスなどを環境変数から取得
  - KABUSYS_ENV（development / paper_trading / live）や LOG_LEVEL の検証
  - is_dev / is_paper / is_live の便利プロパティ

- 自動 .env 読み込み
  - プロジェクトルート（.git または pyproject.toml を検索）を基準に .env と .env.local を自動読み込み
  - 読み込み優先順位: OS 環境変数 > .env.local > .env
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能
  - export 形式、引用符、行末コメント等に対応したパーサを実装

- DuckDB スキーマ定義・初期化（kabusys.data.schema）
  - Raw / Processed / Feature / Execution の各レイヤに対応するテーブルDDLを定義
  - init_schema(db_path) でスキーマを冪等に作成。親ディレクトリがなければ自動作成
  - get_connection(db_path) で既存DBへの接続を取得
  - インデックス・外部キー制約を含む設計

セットアップ手順
----------------

1. Python と仮想環境の作成（例）
   - Unix/macOS:
     ```
     python -m venv .venv
     source .venv/bin/activate
     ```
   - Windows (PowerShell):
     ```
     python -m venv .venv
     .\.venv\Scripts\Activate.ps1
     ```

2. 必要パッケージのインストール
   - duckdb が必須です。プロジェクトに pyproject.toml / requirements 指定がある想定で、
     開発中は以下のようにします:
     ```
     pip install duckdb
     pip install -e .
     ```
     （プロジェクト配布方法に応じて pip install 先を調整してください）

3. 環境変数の設定
   - プロジェクトルートに .env（および必要に応じて .env.local）を用意すると自動的に読み込まれます。
   - 自動ロードを無効化するには:
     ```
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1   # Unix/macOS
     setx KABUSYS_DISABLE_AUTO_ENV_LOAD 1    # Windows（再起動が必要）
     ```

推奨される .env の例
--------------------
以下は使用される主な環境変数の例です（実際の値は各自の環境に合わせて設定してください）。

J-Quants / kabu / Slack / DB 関連:
```
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxxxxxx
KABU_API_PASSWORD=your_kabu_password
KABU_API_BASE_URL=http://localhost:18080/kabusapi   # 任意（デフォルトあり）
SLACK_BOT_TOKEN=xoxb-xxxxxxxxxxxxxxxx
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
KABUSYS_ENV=development   # または paper_trading / live
LOG_LEVEL=INFO
```

重要な環境変数（必須）
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD
- SLACK_BOT_TOKEN
- SLACK_CHANNEL_ID

使い方（基本例）
---------------

- 設定の読み取り:
```python
from kabusys.config import settings

print(settings.jquants_refresh_token)
print(settings.duckdb_path)
print(settings.is_dev)
```

- DuckDB スキーマの初期化:
```python
from kabusys.config import settings
from kabusys.data.schema import init_schema, get_connection

# ファイルパスとして settings.duckdb_path（Path オブジェクト）を渡せます
conn = init_schema(settings.duckdb_path)

# 既存 DB に接続する場合（初回は init_schema を呼ぶこと）
conn2 = get_connection(settings.duckdb_path)
```

- インメモリ DB の利用（テストなど）:
```python
conn = init_schema(":memory:")
```

- 自動 .env ロードを無効にしてプログラムから環境を設定したい場合:
```bash
export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
```

データベーススキーマの概要
--------------------------
スキーマは 4 層構造（Raw / Processed / Feature / Execution）になっています。主なテーブル（抜粋）:

- Raw Layer: raw_prices, raw_financials, raw_news, raw_executions
- Processed Layer: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
- Feature Layer: features, ai_scores
- Execution Layer: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance

また、クエリ性能を考慮したインデックスが複数作成されます（例: idx_prices_daily_code_date, idx_signal_queue_status など）。

ディレクトリ構成
----------------
（プロジェクトルートの src 配下を抜粋）

- src/
  - kabusys/
    - __init__.py              (パッケージ初期化: __version__, __all__ 等)
    - config.py                (環境変数／設定管理)
    - data/
      - __init__.py
      - schema.py             (DuckDB スキーマ定義・init_schema / get_connection)
    - strategy/
      - __init__.py
    - execution/
      - __init__.py
    - monitoring/
      - __init__.py

補足・運用メモ
--------------
- init_schema() は冪等的（既存テーブルがあればスキップ）なので、本番・開発どちらでも安全に実行できます。
- settings のプロパティは環境変数の妥当性チェックを行います（KABUSYS_ENV, LOG_LEVEL 等）。
- .env パーサは引用符／エスケープ／行末コメント／export 形式に対応していますが、複雑なケースでは .env.example を参考にシンプルな記述を推奨します。
- 戦略（strategy）、実行（execution）、監視（monitoring）はモジュールの枠組みとして用意されています。これらの実装はプロジェクトの要件に応じて拡張してください。

ライセンス・貢献
----------------
（本 README には記載されていません。必要に応じて LICENSE ファイルや CONTRIBUTING ガイドを追加してください。）

---

何か追加で README に入れたい内容（例: CI 設定、ユニットテストの実行方法、具体的な戦略テンプレートなど）があれば教えてください。必要に応じて追記します。