# KabuSys

日本株向けの自動売買プラットフォーム用ライブラリ/モジュール群です。データ収集（J-Quants）、DuckDB スキーマ管理、特徴量計算、シグナル生成、ニュース収集、マーケットカレンダー管理、監査ログ等のユーティリティを含みます。

主な目的は「研究 → 本番」のワークフローを支えるデータ基盤と戦略ロジックの共通実装を提供することです。

---

## 機能一覧

- 環境設定管理
  - `.env` / 環境変数の自動読み込み（プロジェクトルート検出）
  - 必須設定の明示的チェック

- データ層（DuckDB）
  - DuckDB スキーマ定義・初期化（raw / processed / feature / execution 層）
  - raw データ保存（株価、財務、ニュース、約定 等）
  - 各種インデックス作成

- J-Quants API クライアント
  - 日次株価、財務、マーケットカレンダー取得（ページネーション対応）
  - レート制御、リトライ、401 時のトークン自動リフレッシュ
  - DuckDB への冪等保存（ON CONFLICT）

- ETL パイプライン
  - 差分取得（最終取得日から自動算出 + backfill）
  - 日次 ETL（カレンダー → 株価 → 財務 → 品質チェック）
  - 個別ジョブ（prices / financials / calendar）の実行

- ニュース収集
  - RSS フィード収集（SSRF 対策、gzip・サイズ制限、XML 脆弱性対策）
  - 記事 ID の正規化（URL 正規化 → SHA-256）
  - raw_news・news_symbols への冪等保存
  - テキスト前処理・銘柄コード抽出

- 研究・戦略ユーティリティ
  - ファクター計算（momentum / volatility / value）
  - Z スコア正規化ユーティリティ
  - 特徴量構築（build_features）
  - シグナル生成（generate_signals） — 複数コンポーネントの重み付け合成、Bear レジームフィルタ、エグジット判定（ストップロス等）

- カレンダー管理
  - JPX マーケットカレンダーの差分更新、営業日判定 API（next/prev/get_trading_days 等）

- 監査ログ（audit）
  - signal_events / order_requests / executions 等の監査用スキーマ

---

## 要件

- Python 3.10 以上（型ヒントで `X | None` 形式を使用）
- 推奨ライブラリ（最低限）
  - duckdb
  - defusedxml

実行環境に応じて他の HTTP 標準ライブラリ（urllib）を利用します。実際の運用では J-Quants アクセスに必要なネットワークアクセスが必要です。

インストール例:
```bash
python -m pip install "duckdb" "defusedxml"
# or: pip install -e .
```

（パッケージ化されていれば `pip install -e .` で開発インストールできます）

---

## セットアップ手順

1. リポジトリをクローン / ソースを取得

2. Python 仮想環境を作成・有効化（推奨）
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # macOS/Linux
   .venv\Scripts\activate     # Windows
   ```

3. 依存ライブラリをインストール
   ```bash
   pip install duckdb defusedxml
   ```

4. 環境変数を準備
   - プロジェクトルートに `.env` または `.env.local` を配置すると自動で読み込まれます（CWD に依存せずパッケージ内でプロジェクトルートを探します）。
   - 自動ロードを無効化する場合:
     ```bash
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```

.env の例（`.env.example` 相当）
```
# J-Quants
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxx

# kabuステーション API
KABU_API_PASSWORD=your_kabu_password
KABU_API_BASE_URL=http://localhost:18080/kabusapi

# Slack
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567

# DB パス
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db

# 実行環境 / ログレベル
KABUSYS_ENV=development  # development | paper_trading | live
LOG_LEVEL=INFO
```

- 必須環境変数（Settings クラスで `_require` が使われているもの）
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
  - SLACK_BOT_TOKEN
  - SLACK_CHANNEL_ID

---

## データベース初期化

DuckDB スキーマを作成するには `kabusys.data.schema.init_schema` を使用します。

サンプル:
```python
from kabusys.data.schema import init_schema
from kabusys.config import settings

db_path = settings.duckdb_path  # または "data/kabusys.duckdb"
conn = init_schema(db_path)
# conn は duckdb.DuckDBPyConnection オブジェクト
```

メモリ DB を使う場合:
```python
conn = init_schema(":memory:")
```

既存 DB に接続するだけなら `get_connection()` を利用してください（スキーマ初期化は行いません）。

---

## 使い方（主要ワークフロー例）

以下は代表的なワークフローの例です。

1) 日次 ETL（市場カレンダー、株価、財務）
```python
from datetime import date
from kabusys.data.schema import init_schema
from kabusys.data.pipeline import run_daily_etl

conn = init_schema("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

2) マーケットカレンダーの夜間更新
```python
from kabusys.data.schema import init_schema
from kabusys.data.calendar_management import calendar_update_job

conn = init_schema("data/kabusys.duckdb")
saved = calendar_update_job(conn)
print("saved calendar rows:", saved)
```

3) ニュース収集ジョブ
```python
from kabusys.data.schema import init_schema
from kabusys.data.news_collector import run_news_collection

conn = init_schema("data/kabusys.duckdb")
# known_codes は有効銘柄コードのセット（抽出フィルタ用）
known_codes = {"7203", "6758", "9984", ...}
results = run_news_collection(conn, known_codes=known_codes)
print(results)
```

4) 特徴量構築（戦略層）
```python
from datetime import date
import duckdb
from kabusys.strategy import build_features
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
count = build_features(conn, target_date=date(2025, 1, 31))
print(f"features upserted: {count}")
```

5) シグナル生成
```python
from datetime import date
from kabusys.strategy import generate_signals
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
num_signals = generate_signals(conn, target_date=date(2025, 1, 31))
print(f"signals written: {num_signals}")
```

6) ETL + 特徴量 + シグナルを連結する典型的なバッチ（擬似コード）
```python
# 1. ETL 実行
etl_res = run_daily_etl(conn, target_date=today)

# 2. features を構築
build_features(conn, target_date=today)

# 3. ai_scores がある場合は先に投入してから
# 4. generate_signals で signals を生成
generate_signals(conn, target_date=today)
```

---

## 注意事項 / 実装上の設計ポイント

- 自動環境変数読み込み:
  - パッケージは `.git` または `pyproject.toml` を親ディレクトリに見つけることでプロジェクトルートを特定し、`.env` と `.env.local` を自動読み込みします。
  - テスト等で自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

- 冪等性:
  - J-Quants API から保存する際はいずれも冪等（ON CONFLICT）に対応しています。
  - ETL は最終取得日の差分更新を行うため繰り返し実行可能です。

- ルックアヘッドバイアスへの配慮:
  - 研究・戦略モジュールは target_date 時点で利用可能なデータのみを使用する設計です。
  - API から取得したデータには fetched_at を付与し「いつデータが取得されたか」を追跡できます。

- 安全対策:
  - RSS ニュースの取得は SSRF 対策（リダイレクト・ホスト検証）、XML 脆弱性対策（defusedxml）、レスポンスサイズ制限を実施しています。
  - J-Quants クライアントは API レート制限とリトライ・バックオフを実装しています。

---

## ディレクトリ構成

主要なファイル/モジュール:

- src/kabusys/
  - __init__.py
  - config.py                -- 環境変数 / Settings
  - data/
    - __init__.py
    - jquants_client.py      -- J-Quants API クライアント + 保存ロジック
    - schema.py              -- DuckDB スキーマ定義・初期化
    - pipeline.py            -- ETL パイプライン
    - news_collector.py      -- RSS 取得・記事保存
    - calendar_management.py -- マーケットカレンダー管理
    - features.py            -- データ用ユーティリティ公開
    - stats.py               -- zscore_normalize 等の統計ユーティリティ
    - audit.py               -- 監査ログ用スキーマ
    - (その他: quality.py 等、品質チェックモジュール想定)
  - research/
    - __init__.py
    - factor_research.py     -- momentum/volatility/value の計算
    - feature_exploration.py -- 前方リターン・IC・統計量
  - strategy/
    - __init__.py
    - feature_engineering.py -- build_features（正規化、ユニバースフィルタ等）
    - signal_generator.py    -- generate_signals（final_score 算出、BUY/SELL 決定）
  - execution/                -- 発注/約定関連（今後の実装想定）
  - monitoring/               -- 監視・Slack 通知等（今後の実装想定）

（README に書かれている以外の補助ファイルが存在する場合もあります）

---

## 貢献 / 開発メモ

- 型安全・冪等性・ルックアヘッドバイアスの排除に重点を置いています。改修する際はこれらの観点を優先してください。
- ユニットテストでは `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定して環境依存を切り離すと便利です。
- DuckDB の SQL 実行結果の型（date / timestamp 等）に注意してください（コード内では変換ヘルパーを利用しています）。

---

必要に応じて README にサンプル .env.example、さらに詳細な API ドキュメントや UDF（品質チェックの仕様、StrategyModel.md 等）の参照先を追加できます。追加してほしい項目があれば教えてください。