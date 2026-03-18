# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ群です。  
DuckDB をデータ層として用い、J-Quants API や RSS からデータ収集 → ETL → 特徴量生成 → 研究 / 発注監査までのワークフローを想定したモジュール群を提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は以下の目的を持つ内部ライブラリ群です。

- J-Quants API から株価・財務・市場カレンダーを取得して DuckDB に保存（冪等）
- RSS からニュースを収集して正規化・保存、銘柄紐付け
- データ品質チェック（欠損、スパイク、重複、日付不整合）
- 研究用のファクター計算（モメンタム、ボラティリティ、バリュー等）と評価ユーティリティ（IC、サマリ等）
- ETL パイプラインの実行ユーティリティ（差分更新、バックフィル）
- 監査ログ（シグナル → 発注 → 約定のトレーサビリティ）スキーマ

設計方針として、外部依存を最小限にし（標準ライブラリと DuckDB、defusedxml 等）、API 呼び出しはレート制御・リトライ・トークンリフレッシュを含む堅牢な実装になっています。

---

## 主な機能一覧

- data/
  - jquants_client: J-Quants API クライアント（ページネーション、リトライ、トークンリフレッシュ、レート制御）
  - news_collector: RSS 収集（SSRF/サイズ制限/トラッキング除去/銘柄抽出）
  - schema: DuckDB スキーマ定義と初期化（Raw / Processed / Feature / Execution 層）
  - pipeline / etl: 差分 ETL（prices, financials, calendar）と日次 ETL 実行
  - quality: 品質チェック（欠損/スパイク/重複/日付不整合）
  - calendar_management: 市場カレンダー管理（営業日判定・前後営業日取得・夜間更新ジョブ）
  - audit: 発注〜約定の監査ログスキーマ（トレーサビリティ）
  - stats: 汎用統計ユーティリティ（Zスコア正規化 など）
- research/
  - factor_research: モメンタム / ボラティリティ / バリューの計算
  - feature_exploration: 将来リターン計算、IC（Spearman ρ）、統計サマリ
- config.py: 環境変数管理と settings API（自動 .env ロード機能あり）
- strategy/, execution/, monitoring/ の基礎モジュール（エントリポイントとなるパッケージ）

---

## 動作環境

- Python 3.10 以上（モジュール内で | 型注釈等を使用）
- 必要パッケージ（最低限）
  - duckdb
  - defusedxml

pip インストール例（仮想環境を推奨）:

```bash
python -m venv .venv
source .venv/bin/activate
pip install "duckdb" "defusedxml"
# または requirements.txt を用意している場合は pip install -r requirements.txt
```

（プロジェクトをパッケージ化していれば `pip install -e .` などでインストール可能です）

---

## 環境変数 / 設定

config.Settings 経由で利用される主な環境変数:

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須) — kabu API パスワード
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須) — Slack 通知用ボットトークン
- SLACK_CHANNEL_ID (必須) — Slack チャンネル ID
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 実行環境 ("development" | "paper_trading" | "live")（デフォルト: development）
- LOG_LEVEL — ログレベル ("DEBUG", "INFO", ...)

自動 .env 読み込み:
- パッケージはプロジェクトルート（.git または pyproject.toml の存在）を探索し、`.env` と `.env.local` を自動読み込みします（既定で OS 環境変数 > .env.local > .env の優先順）。
- 自動読み込みを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

サンプル .env（README 用テンプレート）:

```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
KABU_API_PASSWORD=your_kabu_password
KABU_API_BASE_URL=http://localhost:18080/kabusapi
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## セットアップ手順

1. リポジトリをクローンする（もしくはパッケージを取得）。
2. Python 仮想環境を作成して有効化。
3. 必要パッケージをインストール（上記参照）。
4. 環境変数（または .env）を準備する。
5. DuckDB スキーマを初期化する（例を次節に示します）。

例: DuckDB スキーマ初期化（Python）

```python
from kabusys.data.schema import init_schema
from kabusys.config import settings

conn = init_schema(settings.duckdb_path)  # settings.duckdb_path は Path を返す
```

初期化は冪等なので複数回実行しても問題ありません。`:memory:` を渡すとインメモリ DB を使用します。

---

## 使い方（代表的な例）

- 日次 ETL を実行する（市場カレンダー・株価・財務の差分取得＋品質チェック）:

```python
from datetime import date
import duckdb
from kabusys.data.schema import init_schema
from kabusys.data.pipeline import run_daily_etl
from kabusys.config import settings

conn = init_schema(settings.duckdb_path)
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- 単体で株価差分 ETL を実行する:

```python
from datetime import date
from kabusys.data.schema import init_schema
from kabusys.data.pipeline import run_prices_etl

conn = init_schema("data/kabusys.duckdb")
fetched, saved = run_prices_etl(conn, target_date=date.today())
print(f"fetched={fetched}, saved={saved}")
```

- RSS ニュース収集ジョブを実行する:

```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")

# known_codes を渡すと記事と銘柄の紐付けを行います（例: {'7203', '6758', ... }）
results = run_news_collection(conn, sources=None, known_codes=None)
print(results)
```

- 研究用: モメンタム計算・IC 計算の例:

```python
from datetime import date
from kabusys.research import calc_momentum, calc_forward_returns, calc_ic
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
target = date(2024, 1, 31)

factors = calc_momentum(conn, target)
fwd = calc_forward_returns(conn, target, horizons=[1,5,21])
ic = calc_ic(factors, fwd, factor_col="mom_1m", return_col="fwd_1d")
print("IC:", ic)
```

- カレンダー関連ユーティリティ:

```python
from datetime import date
from kabusys.data.calendar_management import is_trading_day, next_trading_day
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
d = date(2024, 1, 1)
print(is_trading_day(conn, d))
print(next_trading_day(conn, d))
```

---

## ディレクトリ構成

（リポジトリルートに README.md や pyproject.toml 等がある想定）

- src/
  - kabusys/
    - __init__.py
    - config.py
    - data/
      - __init__.py
      - jquants_client.py
      - news_collector.py
      - schema.py
      - pipeline.py
      - etl.py
      - quality.py
      - stats.py
      - features.py
      - calendar_management.py
      - audit.py
      - audit/... (監査関連の追加モジュール)
    - research/
      - __init__.py
      - factor_research.py
      - feature_exploration.py
    - strategy/
      - __init__.py
      - (戦略実装用モジュール)
    - execution/
      - __init__.py
      - (発注/ブローカー連携用モジュール)
    - monitoring/
      - __init__.py

上記はコードベースの主要ファイルを抜粋した構成です。各モジュールは DuckDB 接続を受け取る設計になっており、本番 API（kabu / J-Quants）へのアクセスはそれぞれのクライアントを通して行われます。

---

## 注意事項 / 補足

- Python バージョン要件は 3.10 以上です（`X | Y` の型注釈を使用）。
- J-Quants API のレート制限（120 req/min）やリトライ方針は jquants_client 内で考慮されています。
- RSS の取得では SSRF 対策や gzip 解凍サイズ制限、defusedxml による安全な XML パースを行っています。
- DuckDB スキーマの DDL は厳密な CHECK 制約や PRIMARY KEY、INDEX を含みます。既存 DB に追加する際は互換性に注意してください。
- 環境変数・秘密情報は .env ファイルや CI シークレットなどで安全に管理してください。
- 本ライブラリは研究やペーパー取引などの用途に便利なユーティリティを多数含みますが、実際のライブ取引で使用する際は十分な検証とリスク管理を行ってください。

---

不明点や README に追加して欲しい具体的な使用例（例: 発注フロー、戦略実装のテンプレートなど）があれば教えてください。必要に応じてサンプルスクリプトや .env.example の完全テンプレートを作成します。