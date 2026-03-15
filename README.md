# KabuSys

日本株向け自動売買システムの基盤ライブラリ（プロトタイプ）。  
市場データ収集・整形、特徴量生成、発注管理、モニタリングのための共通ユーティリティや DuckDB スキーマ定義を提供します。

バージョン: 0.1.0

---

## 機能一覧

- 環境変数 / .env 管理
  - プロジェクトルートの `.env` / `.env.local` を自動読み込み（CWD に依存しない）
  - 必須変数チェック（未設定時は例外を発生）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動読み込みを無効化可能
- DuckDB によるデータベーススキーマ
  - 3 層構造（Raw / Processed / Feature）＋ Execution 層を定義
  - 市場価格、財務データ、ニュース、特徴量、シグナル、注文・約定・ポジション管理等のテーブルを用意
  - よく使うクエリ向けのインデックスを作成
  - init_schema() による冪等な初期化
- 設定オブジェクト（settings）
  - J-Quants / kabu API / Slack / DB パス / 実行モード（development / paper_trading / live）等をプロパティで取得
- パッケージ構造の骨組み（strategy / execution / monitoring / data）を提供（拡張可能）

---

## 必要条件

- Python 3.9+
- 依存パッケージ例:
  - duckdb

（プロジェクトの配布方法に応じて requirements.txt / pyproject.toml を利用してください）

---

## セットアップ手順

1. リポジトリをクローン／チェックアウトする
   - 例: git clone <repo-url>

2. 仮想環境を作成して有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - pip install duckdb
   - （その他の依存はプロジェクトの manifest に従ってください）

4. 環境変数の準備
   - プロジェクトルートに `.env`（および任意で `.env.local`）を作成します。
   - 自動読み込みは、パッケージのインポート時にプロジェクトルート（.git または pyproject.toml を基準）を探索して行われます。
   - 自動ロードを無効にしたい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

5. 主要な環境変数（例）
   - JQUANTS_REFRESH_TOKEN=...
   - KABU_API_PASSWORD=...
   - KABU_API_BASE_URL=http://localhost:18080/kabusapi  # 省略時は上記がデフォルト
   - SLACK_BOT_TOKEN=...
   - SLACK_CHANNEL_ID=...
   - DUCKDB_PATH=data/kabusys.duckdb  # 省略時のデフォルト
   - SQLITE_PATH=data/monitoring.db
   - KABUSYS_ENV=development  # 有効値: development, paper_trading, live
   - LOG_LEVEL=INFO  # 有効値: DEBUG, INFO, WARNING, ERROR, CRITICAL

---

## 使い方

以下はライブラリの主要な使い方例です。

- 設定値の取得
  - from kabusys.config import settings
  - settings.jquants_refresh_token などのプロパティでアクセス
  - 必須の値が未設定の場合は ValueError が発生します

- DuckDB スキーマの初期化
  - from kabusys.data.schema import init_schema, get_connection
  - conn = init_schema(settings.duckdb_path)
    - 指定したパスに DuckDB ファイルを作成（親ディレクトリがなければ自動作成）
    - 既にテーブルがあればスキップするため安全に何度でも呼べます
  - 既存 DB に接続する場合:
    - conn = get_connection(settings.duckdb_path)

- 自動 env ロードの挙動
  - 起点ファイル: src/kabusys/config.py
  - 優先順位: OS 環境変数 > .env.local > .env
  - OS 環境変数は保護され、.env ファイルの値で上書きされません（.env.local は override=True で上書き可）
  - 文字列のパースはシェル形式に寄せた処理（export 構文やクォート、コメント対応）

実例（Python）:

```python
from kabusys.config import settings
from kabusys.data.schema import init_schema

# 設定確認
print(settings.env, settings.log_level, settings.duckdb_path)

# DB 初期化
conn = init_schema(settings.duckdb_path)

# SQL 実行例
df = conn.execute("SELECT count(*) FROM prices_daily").fetchdf()
print(df)
```

---

## ディレクトリ構成

（プロジェクトルートからの主要ファイル・モジュール）

- src/
  - kabusys/
    - __init__.py
    - config.py                # 環境変数・設定管理（settings）
    - data/
      - __init__.py
      - schema.py              # DuckDB スキーマ定義・初期化（init_schema, get_connection）
    - strategy/
      - __init__.py            # 戦略ロジック配置場所（拡張用）
    - execution/
      - __init__.py            # 発注関連ロジック配置場所（拡張用）
    - monitoring/
      - __init__.py            # モニタリング用ロジック配置場所（拡張用）

主な役割:
- config.py: .env の自動読み込みと settings オブジェクトによる型チェック・必須チェックを行います。
- data/schema.py: DuckDB のテーブル／インデックス定義を集約し、init_schema() で初期化します。
- strategy, execution, monitoring: 今後の実装で戦略・発注・監視機能を追加するための名前空間です。

---

## スキーマ概要（概念）

データは概念的に次の層に分かれます。

- Raw Layer: 取得した生データ（raw_prices, raw_financials, raw_news, raw_executions 等）
- Processed Layer: 前処理済みの市場データ（prices_daily, market_calendar, fundamentals, news_articles 等）
- Feature Layer: 戦略や AI が利用する特徴量（features, ai_scores）
- Execution Layer: シグナル・注文・約定・ポジション情報（signals, signal_queue, orders, trades, positions, portfolio_performance 等）

各テーブルは外部キーやチェック制約を持ち、頻出クエリ用のインデックスも作成されます。

---

## 注意事項 / ベストプラクティス

- .env ファイルには機密トークンを含めるため、リポジトリにコミットしないでください（.gitignore を利用）。
- 自動読み込みはプロジェクトルートの判定に .git または pyproject.toml を利用します。パッケージ配布後やテスト時に挙動を制御したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。
- 初回は init_schema() でスキーマを作成してからデータ投入やクエリを行ってください。
- ライブラリは拡張用の骨組みを提供します。実際の売買ロジック・リスク管理・接続周りは利用者側で実装してください（ライブ取引の前に十分なテストを行ってください）。

---

必要であれば、README に実際の .env.example（推奨項目）やより詳細な API 使用例、開発ワークフロー（テスト、CI、パッケージ化手順）を追加します。どの内容をさらに盛り込みますか？