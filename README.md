# KabuSys

日本株向けの自動売買基盤ライブラリ（骨組み）。データ収集・スキーマ定義・環境設定を提供し、戦略・発注・監視モジュールを組み合わせて自動売買システムを構築できます。

バージョン: 0.1.0

---

## 概要

KabuSys は日本株自動売買システムの基盤ライブラリです。環境変数管理、DuckDB を使ったデータスキーマ定義・初期化、戦略／実行／監視用のパッケージ構造（プレースホルダ）を提供します。現時点では主に環境設定周り（.env 読み込み）とデータスキーマ初期化の機能が実装されています。

主な目的:
- 環境変数による設定管理（.env / .env.local の自動読み込み）
- DuckDB によるデータレイヤ（Raw / Processed / Feature / Execution）スキーマ
- strategy / execution / monitoring の土台を提供

---

## 機能一覧

- 環境設定（src/kabusys/config.py）
  - プロジェクトルートを自動検出して `.env` / `.env.local` を読み込む（OS 環境変数優先）
  - export 形式、クォートやエスケープ、インラインコメントの取り扱いに対応したパーサ
  - 必須設定を取得するヘルパ（未設定時は ValueError）
  - 設定項目（例: J-Quants トークン、kabu API パスワード、Slack トークン、DB パス、環境モード、ログレベル）

- データスキーマ（src/kabusys/data/schema.py）
  - DuckDB 用のテーブル DDL を定義・初期化（冪等）
  - レイヤ構成:
    - Raw Layer: raw_prices, raw_financials, raw_news, raw_executions
    - Processed Layer: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature Layer: features, ai_scores
    - Execution Layer: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - インデックス定義（頻出クエリ向け）
  - API:
    - init_schema(db_path) → DuckDB 接続を返し、テーブルを作成
    - get_connection(db_path) → 既存 DB へ接続（スキーマ初期化は行わない）

- パッケージ構成（将来拡張のための空パッケージ）
  - src/kabusys/strategy
  - src/kabusys/execution
  - src/kabusys/monitoring

---

## セットアップ手順

前提:
- Python 3.9+（typing の Union 表記などを想定）
- pip が利用可能

1. リポジトリをクローン
   - git clone <リポジトリURL>
   - cd <repo>

2. 仮想環境を作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - 最低限必要: duckdb
   - pip install duckdb
   - （プロジェクトを editable インストールする場合）
     - pip install -e .

   ※ requirements ファイルがある場合は `pip install -r requirements.txt` を使用してください。

4. 環境変数ファイル（.env）の準備
   - プロジェクトルートに `.env` と（開発用なら）`.env.local` を置きます。
   - 自動読み込みはデフォルトで有効。テスト等で無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

5. DB スキーマ初期化（次節の使い方参照）

---

## 必要な環境変数（主要）

必須（Properties が _require() で取得するもの）:
- JQUANTS_REFRESH_TOKEN — J-Quants API のリフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API パスワード
- SLACK_BOT_TOKEN — Slack ボットトークン
- SLACK_CHANNEL_ID — Slack 送信先チャンネルID

任意・デフォルトあり:
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite（監視用 DB）パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 実行環境: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL — ログレベル: DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 1 をセットすると .env 自動読み込みを無効化

.env の記法（サポート）
- export KEY=VAL 形式をサポート
- シングル/ダブルクォートでの値指定およびエスケープに対応
- コメント: 空行・先頭 # を無視。値の中で '#' は、直前がスペース/タブの場合はコメント開始とみなします

例 (.env):
```
JQUANTS_REFRESH_TOKEN="your-refresh-token"
KABU_API_PASSWORD='passwd-with-\'-escape'
SLACK_BOT_TOKEN= xoxb-...
SLACK_CHANNEL_ID=C0123456789
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## 使い方

基本的な利用例を示します。

- 環境設定を取得する:
```python
from kabusys.config import settings

token = settings.jquants_refresh_token
print("env:", settings.env, "is_live:", settings.is_live)
```

- DuckDB スキーマを初期化する:
```python
from kabusys.data.schema import init_schema
from kabusys.config import settings

# settings.duckdb_path は Path を返します（デフォルト: data/kabusys.duckdb）
conn = init_schema(settings.duckdb_path)
# conn は duckdb.DuckDBPyConnection。SQL 実行可能。
conn.execute("SELECT count(*) FROM prices_daily").fetchall()
```

- 既存 DB に接続する（スキーマ初期化不要時）:
```python
from kabusys.data.schema import get_connection
conn = get_connection("data/kabusys.duckdb")
```

- 自動 .env 読み込みを無効化してプログラム的に設定したい場合:
```bash
export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
python -c "from kabusys.config import settings; print('loaded')"
```

- 例: スクリプトでスキーマ初期化を行う簡単なコマンド
```python
# scripts/init_db.py
from kabusys.config import settings
from kabusys.data.schema import init_schema

if __name__ == "__main__":
    conn = init_schema(settings.duckdb_path)
    print("Initialized DB at", settings.duckdb_path)
```
実行:
```
python scripts/init_db.py
```

注意点:
- init_schema は冪等です。既存テーブルがあればスキップします。
- db_path に ":memory:" を渡すとインメモリ DB が使用できます（テスト用に便利）。

---

## ディレクトリ構成

主要ファイル・ディレクトリ:
```
.
├─ src/
│  └─ kabusys/
│     ├─ __init__.py           # パッケージメタ情報（__version__）
│     ├─ config.py             # 環境変数・設定管理（.env 自動読み込み、Settings）
│     ├─ data/
│     │  ├─ __init__.py
│     │  └─ schema.py          # DuckDB スキーマ定義・初期化（init_schema, get_connection）
│     ├─ strategy/
│     │  └─ __init__.py        # 戦略モジュール（拡張ポイント）
│     ├─ execution/
│     │  └─ __init__.py        # 発注実行モジュール（拡張ポイント）
│     └─ monitoring/
│        └─ __init__.py        # 監視・ロギング用（拡張ポイント）
├─ pyproject.toml / setup.cfg?  # （存在すればパッケージ設定）
└─ .env / .env.local            # 推奨（プロジェクトルートに配置）
```

---

## 今後の拡張ポイント（参考）

- strategy パッケージに戦略実装（シグナル生成・特徴量利用）
- execution パッケージに Order 作成・kabu API 実装（認証、注文管理）
- monitoring に Slack 通知やパフォーマンス計測処理の実装
- テストスイート、CI 設定、requirements.txt の明記

---

## ライセンス・連絡

この README はコードベースの現状を説明するものです。実運用での自動売買はリスクを伴います。実装・設定を行う際は十分に検証し、必要に応じて専門家へ相談してください。

ご不明点があれば、実装したい機能（戦略・発注ロジック・監視要件など）を教えてください。README の改善や例スクリプト作成をサポートします。