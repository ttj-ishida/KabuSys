# KabuSys

日本株向けの自動売買システム（骨組み）。データ取得・加工、特徴量生成、取引実行、モニタリングのための共通モジュール群を提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は、ローカルで実行する日本株の自動売買基盤のためのライブラリ的なプロジェクトです。  
主な目的は以下のとおりです。

- 市場データ・財務データ・ニュース・約定履歴などの Raw データ保存
- 日次データや特徴量（feature）、AI スコアの格納
- 発注キュー／注文／約定／ポジションなど実行関連テーブルの管理
- 環境変数による設定管理（自動 .env ロード機能）
- DuckDB を用いたローカル DB スキーマ定義と初期化

現時点ではモジュールの骨格（package layout）と DB スキーマ、設定周りの実装が中心です。

---

## 主な機能一覧

- 環境変数/設定管理（kabusys.config）
  - .env / .env.local の自動読み込み（プロジェクトルートを .git または pyproject.toml から検出）
  - 必須設定の取得ラッパー（未定義時は例外を送出）
  - 環境（development / paper_trading / live）判定、ログレベル検証
- DuckDB スキーマ定義・初期化（kabusys.data.schema）
  - Raw / Processed / Feature / Execution レイヤーのテーブル DDL を定義
  - インデックス作成、外部キー依存を考慮したテーブル作成順序
  - init_schema(db_path) で DB 初期化、get_connection() で既存 DB へ接続
- パッケージ骨子（strategy, execution, monitoring）を用意（各機能の拡張場所）

---

## セットアップ手順（ローカル開発向け）

前提: Python 3.9+ を想定（typing オプション等に依存）

1. リポジトリをクローン（またはソースを取得）
   ```
   git clone <repository-url>
   cd <repository-dir>
   ```

2. 仮想環境を作成・有効化（推奨）
   - macOS / Linux:
     ```
     python -m venv .venv
     source .venv/bin/activate
     ```
   - Windows (PowerShell):
     ```
     python -m venv .venv
     .\.venv\Scripts\Activate.ps1
     ```

3. 必要なパッケージをインストール
   - 最小で DuckDB が必要です:
     ```
     pip install duckdb
     ```
   - 実際の運用では Slack API、kabuステーション連携等が必要になるため、
     それらのクライアントライブラリ（例: slack-sdk など）を追加してください。
   - 開発中にパッケージとして使う場合:
     ```
     pip install -e .
     ```
     （pyproject.toml / setup が存在する場合に有効）

4. 環境変数を設定
   - プロジェクトルート（.git または pyproject.toml が存在するディレクトリ）に `.env` または `.env.local` を作成すると自動で読み込まれます（起動時）。
   - 自動ロードを無効にする場合:
     ```
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```

必須の環境変数（少なくとも以下は設定することを想定）:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD
- SLACK_BOT_TOKEN
- SLACK_CHANNEL_ID

オプション / デフォルト:
- KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (デフォルト: data/monitoring.db)
- KABUSYS_ENV (development / paper_trading / live、デフォルト: development)
- LOG_LEVEL (DEBUG/INFO/WARNING/ERROR/CRITICAL、デフォルト: INFO)

.env のサンプル（.env.example を参考に作成してください）
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
KABU_API_PASSWORD=your_kabu_station_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C0123456789
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## 使い方（簡単な例）

1) 設定値の取得
```python
from kabusys.config import settings

# 必須キーが未設定の場合は ValueError が発生します
token = settings.jquants_refresh_token
print("env:", settings.env)
print("is_live:", settings.is_live)
```

2) DuckDB スキーマ初期化
```python
from kabusys.config import settings
from kabusys.data.schema import init_schema

# settings.duckdb_path は Path オブジェクトを返します
conn = init_schema(settings.duckdb_path)  # ファイル DB を作成・初期化

# メモリ DB を使う場合
mem_conn = init_schema(":memory:")
```

3) 既存 DB へ接続
```python
from kabusys.data.schema import get_connection
conn = get_connection("data/kabusys.duckdb")
# conn.execute(...) でクエリ実行可能
```

4) 自動 .env 読み込みを無効化してプログラム起動（テスト等）
```
export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
python your_app.py
```

---

## ディレクトリ構成

以下は主要ファイル・ディレクトリ（src 配下）です。

- src/
  - kabusys/
    - __init__.py          # パッケージトップ（__version__ 等）
    - config.py            # 環境変数 / 設定管理（自動 .env ロード、Settings クラス）
    - data/
      - __init__.py
      - schema.py         # DuckDB スキーマ定義と init_schema / get_connection
    - strategy/
      - __init__.py        # 戦略関連モジュール（拡張ポイント）
    - execution/
      - __init__.py        # 発注・実行関連（拡張ポイント）
    - monitoring/
      - __init__.py        # モニタリング関連（拡張ポイント）

DB スキーマ（data/schema.py）には以下のレイヤーが定義されています:
- Raw Layer: raw_prices, raw_financials, raw_news, raw_executions
- Processed Layer: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
- Feature Layer: features, ai_scores
- Execution Layer: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance

インデックスも頻出クエリに合わせて作成されます。

---

## 開発・拡張のヒント

- strategy / execution / monitoring は現在プレースホルダです。各機能を実装する際は既存の DB スキーマ（features / ai_scores / signal_queue / orders など）を参照してください。
- settings クラスはプロパティベースなので、環境変数のバリデーションや追加設定は config.py に集中して実装してください。
- .env のパースはシェル風（export プレフィックス、クォート、コメント等）に対応していますが、極端に複雑な記述は避けてください。
- DuckDB はシングルファイル DB として扱えるため、ローカルでの実行やバックテストに適しています。大量データを扱う場合はコネクションやクエリの最適化を検討してください。

---

## ライセンス・貢献

（この README にはライセンス情報を含めていません。リポジトリに LICENSE ファイルを追加してください。）

貢献する場合は Issue / PR を送ってください。機能追加の際は DB スキーマの互換性に注意してマイグレーション方針を明記してください。

---

必要であれば、README に使い方のサンプルスクリプトや .env.example の完全なテンプレート、よくあるエラーと対処法（例: 環境変数不足、DuckDB ファイルアクセス権限）を追加します。どの情報を優先して追加しますか？