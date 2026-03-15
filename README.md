# KabuSys

日本株向けの自動売買システム用ライブラリ。市場データの保存・加工、特徴量生成、取引シグナル・発注管理、監視・通知などの基盤を提供します。

バージョン: 0.1.0

## 概要
- DuckDB を用いたローカルデータベーススキーマを提供し、生データ → 整形済みデータ → 特徴量 → 発注/約定 という多層構造でデータを管理します。
- 環境変数による設定管理、.env/.env.local の自動読み込み機能を備えています。
- 将来的な戦略モジュール（strategy）、実行モジュール（execution）、監視モジュール（monitoring）向けのパッケージ分割を想定しています。

## 主な機能
- 環境変数/設定管理（kabusys.config）
  - .env/.env.local の自動読み込み（プロジェクトルートを .git または pyproject.toml で検出）
  - 必須環境変数の取得（未設定時は例外）
  - 実行環境（development / paper_trading / live）やログレベル検証
- データベーススキーマ管理（kabusys.data.schema）
  - DuckDB の初期化関数 init_schema(db_path)
  - 接続取得関数 get_connection(db_path)
  - Raw / Processed / Feature / Execution の4層に分かれたテーブル定義
  - 頻出検索のためのインデックス作成
- パッケージ骨組み（strategy / execution / monitoring）を準備済み

## 必要条件
- Python 3.10+
- duckdb（Python パッケージ）
- （プロジェクト固有）J-Quants, kabuステーション, Slack など外部 API の資格情報

例:
pip install duckdb

プロジェクト実行用に他のライブラリが必要な場合は、適宜 requirements.txt を用意してインストールしてください。

## セットアップ手順

1. リポジトリをクローン／取得
2. 仮想環境を作成して有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 必要パッケージをインストール
   - pip install duckdb
   - （他に必要な依存があれば追加でインストール）
4. 環境変数を用意
   - プロジェクトルートに .env, または .env.local を作成
   - 自動読み込みはプロジェクトルートを .git または pyproject.toml で検出します
   - 自動読み込みを無効にする場合:
     - 環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定
5. DuckDB スキーマ初期化（例は下記「使い方」を参照）

## 環境変数（設定）
kabusys.config.Settings が参照する主な環境変数:

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL (任意、デフォルト: http://localhost:18080/kabusapi)
- SLACK_BOT_TOKEN (必須)
- SLACK_CHANNEL_ID (必須)
- DUCKDB_PATH (任意、デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (任意、デフォルト: data/monitoring.db)
- KABUSYS_ENV (任意、デフォルト: development)
  - 有効な値: development, paper_trading, live
- LOG_LEVEL (任意、デフォルト: INFO)
  - 有効な値: DEBUG, INFO, WARNING, ERROR, CRITICAL

.env の読み込みルール:
- 優先順位: OS 環境変数 > .env.local > .env
- .env/.env.local はプロジェクトルート（.git または pyproject.toml のあるディレクトリ）から読み込まれます
- .env のパースは一般的な shell 形式（export を許容、クォート・エスケープを考慮）

自動ロードを無効化する:
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると .env 自動ロードをスキップします（テスト等で便利）

例（.env）
JQUANTS_REFRESH_TOKEN="your_jquants_refresh_token"
KABU_API_PASSWORD="your_kabu_password"
SLACK_BOT_TOKEN="xoxb-..."
SLACK_CHANNEL_ID="CXXXXXXX"
DUCKDB_PATH="data/kabusys.duckdb"
KABUSYS_ENV=development
LOG_LEVEL=INFO

## 使い方（簡単な例）

- 設定を参照する：
```python
from kabusys.config import settings

token = settings.jquants_refresh_token
print("環境:", settings.env)
print("DuckDB path:", settings.duckdb_path)
```

- DuckDB スキーマの初期化：
```python
from kabusys.data.schema import init_schema
from kabusys.config import settings

# settings.duckdb_path は Path を返す
conn = init_schema(settings.duckdb_path)
# conn は duckdb.DuckDBPyConnection
```

- 既存 DB への接続（スキーマ初期化は行わない）：
```python
from kabusys.data.schema import get_connection
from kabusys.config import settings

conn = get_connection(settings.duckdb_path)
```

- 取得した DuckDB 接続で SQL を実行：
```python
with conn:
    df = conn.execute("SELECT date, code, close FROM prices_daily WHERE code = '7203' ORDER BY date DESC LIMIT 10").fetchdf()
    print(df)
```

## データベーススキーマ（概観）
データは以下の4層で管理されます。

- Raw Layer
  - raw_prices, raw_financials, raw_news, raw_executions
  - API 等から取得した生データを保持（fetched_at などのメタ情報あり）
- Processed Layer
  - prices_daily, market_calendar, fundamentals, news_articles, news_symbols
  - 生データを集計・整形後に格納
- Feature Layer
  - features, ai_scores
  - 戦略・AI用の特徴量やスコア
- Execution Layer
  - signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - シグナル管理、注文キュー、約定/ポジション/パフォーマンス管理

主な注意点:
- 各テーブルの制約（主キー・チェック制約）が定義されており、init_schema は冪等でテーブルを作成します
- 初回起動時は init_schema() を呼びスキーマを作成してください

## ディレクトリ構成
以下は主要ファイルとモジュールの一覧（このリポジトリの状態に基づく）:

- src/kabusys/
  - __init__.py                # パッケージのメタ情報（__version__ = "0.1.0"）
  - config.py                  # 環境変数・設定管理（.env 自動ロード）
  - data/
    - __init__.py
    - schema.py                # DuckDB スキーマ定義と初期化関数（init_schema, get_connection）
  - strategy/
    - __init__.py              # 戦略モジュール用プレースホルダ
  - execution/
    - __init__.py              # 発注実行モジュール用プレースホルダ
  - monitoring/
    - __init__.py              # 監視/通知モジュール用プレースホルダ

プロジェクトルートには通常 .env/.env.local、pyproject.toml（ある場合）、README.md などが置かれます。

## 開発メモ / 注意事項
- .env の自動読み込みは作業ディレクトリ（CWD）には依存せず、パッケージ内のファイル位置からプロジェクトルートを探索して決定します。
- .env の読み込みでは OS の既存環境変数は保護され、.env.local は .env より優先して上書きされます（ただし OS 環境変数は上書きされません）。
- 環境変数の必須値が未設定の場合、Settings の該当プロパティで ValueError が投げられます。
- DuckDB を ":memory:" で指定するとインメモリ DB が使用されます。

---

不明点や追加したいドキュメント（API 詳細、DataSchema.md、実行例、テストの説明 等）があれば教えてください。README を拡張して含めます。