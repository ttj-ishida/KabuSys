# KabuSys

日本株向け自動売買システム（プロトタイプ）  
このリポジトリは、データ取得（ETL）→特徴量作成→シグナル生成→発注・監査のワークフローを想定したモジュール群を提供します。内部データストアに DuckDB を用い、J-Quants API や RSS フィードからデータを収集して戦略用の特徴量・シグナルを生成します。

バージョン: 0.1.0

---

## 主な特徴

- データプラットフォーム（DuckDB）向けのスキーマ定義と初期化
- J-Quants API クライアント（レートリミット・リトライ・自動トークンリフレッシュ対応）
- 日次 ETL パイプライン（株価・財務・市場カレンダーの差分取得）
- RSS ベースのニュース収集と銘柄コード抽出（SSRF 対策・サイズ制限・トラッキング除去）
- ファクター計算（Momentum / Volatility / Value 等）と Z スコア正規化
- 戦略用特徴量の構築（features テーブルへの UPSERT、冪等）
- シグナル生成（最終スコア計算、BUY/SELL シグナルの挿入、Bear レジーム抑制）
- マーケットカレンダー管理（営業日判定・次/前営業日の取得）
- 監査ログ（signal → order → execution のトレースを想定したスキーマ）
- 研究ユーティリティ（将来リターン計算、IC 計算、統計サマリー）

---

## 必要条件（開発環境）

- Python 3.9+
- pip
- 推奨ライブラリ（最低限）:
  - duckdb
  - defusedxml

例:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb defusedxml
```

（実際の運用では logging、Slack 通知等の追加ライブラリや実際の発注 SDK が必要になる場合があります）

---

## 環境変数 / 設定

設定は環境変数で行います。.env ファイルをプロジェクトルートに置くと自動で読み込む仕組みがあります（.env.local があれば .env を上書き）。

主な必須環境変数:
- JQUANTS_REFRESH_TOKEN : J-Quants リフレッシュトークン（API 利用時必須）
- KABU_API_PASSWORD : kabuステーション等の API パスワード（実行層で必要）
- SLACK_BOT_TOKEN : Slack 通知用ボットトークン
- SLACK_CHANNEL_ID : Slack 通知先チャンネル ID

その他：
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (デフォルト: data/monitoring.db)
- KABUSYS_ENV: development / paper_trading / live（デフォルト development）
- LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL

自動 env 読み込みを無効化する:
```bash
export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
```

.env の自動パーシングの挙動は .env/.env.local をプロジェクトルート（.git または pyproject.toml のあるディレクトリ）から探して読み込みます。

---

## セットアップ手順（簡易）

1. リポジトリをクローンして仮想環境を作成・有効化
2. 依存パッケージをインストール（上記参照）
3. プロジェクトルートに `.env` を作成して必要な環境変数を設定
4. DuckDB スキーマを初期化

例:
```bash
python - <<'PY'
from kabusys.data.schema import init_schema
init_schema("data/kabusys.duckdb")
print("DuckDB initialized")
PY
```

---

## 使い方（代表的な例）

以下は最小限の実行例です。実運用ではエラーハンドリングやログ設定、スケジューラ（cron / Airflow 等）を併用してください。

1) DuckDB スキーマ初期化
```python
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")
```

2) 日次 ETL（J-Quants へ接続する場合は JQUANTS_REFRESH_TOKEN を設定）
```python
from kabusys.data.pipeline import run_daily_etl
from kabusys.data.schema import init_schema
from datetime import date

conn = init_schema("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

3) マーケットカレンダー更新ジョブ（夜間バッチ）
```python
from kabusys.data.calendar_management import calendar_update_job
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
saved = calendar_update_job(conn)
print("calendar saved:", saved)
```

4) RSS ニュース収集（既知銘柄コードセットを渡して銘柄紐付け）
```python
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
known_codes = {"7203", "6758"}  # 例: 有効な銘柄コードセット
res = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
print(res)
```

5) 特徴量構築 → シグナル生成
```python
from kabusys.data.schema import get_connection
from kabusys.strategy import build_features, generate_signals
from datetime import date

conn = get_connection("data/kabusys.duckdb")
t = date.today()

# features テーブル構築（raw データが必要）
n = build_features(conn, t)
print("features built:", n)

# signals 生成（デフォルト閾値 0.6）
m = generate_signals(conn, t)
print("signals written:", m)
```

---

## よく使う API（概要）

- kabusys.config.settings
  - 環境変数から各種設定を取得します（例: settings.jquants_refresh_token）。
- kabusys.data.schema
  - init_schema(db_path) : DuckDB のスキーマを作成して接続を返す
  - get_connection(db_path) : 既存 DB への接続を返す
- kabusys.data.jquants_client
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - save_daily_quotes / save_financial_statements / save_market_calendar
  - get_id_token(refresh_token)
- kabusys.data.pipeline
  - run_daily_etl(conn, target_date, ...)
  - run_prices_etl / run_financials_etl / run_calendar_etl
- kabusys.data.news_collector
  - fetch_rss(url, source) / save_raw_news / run_news_collection
- kabusys.research
  - calc_momentum / calc_volatility / calc_value / calc_forward_returns / calc_ic / factor_summary
- kabusys.strategy
  - build_features(conn, target_date)
  - generate_signals(conn, target_date, threshold=..., weights=...)

---

## ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py
- config.py
  - 環境変数管理、.env 自動読み込み、settings オブジェクト
- data/
  - __init__.py
  - jquants_client.py       : J-Quants API クライアント（rate limit / retry / save→DuckDB）
  - schema.py               : DuckDB スキーマ定義と init_schema
  - pipeline.py             : ETL パイプライン（差分更新・品質チェックなど）
  - news_collector.py       : RSS ニュース収集・前処理・DB 保存
  - calendar_management.py  : マーケットカレンダー管理（営業日判定・更新ジョブ）
  - features.py             : data.stats の再エクスポート
  - stats.py                : Z スコア正規化など統計ユーティリティ
  - audit.py                : 発注〜約定までの監査ログ用スキーマ（DDL）
- research/
  - __init__.py
  - factor_research.py      : モメンタム/バリュー/ボラティリティ等のファクター計算
  - feature_exploration.py  : 将来リターン・IC・統計サマリー
- strategy/
  - __init__.py
  - feature_engineering.py  : features テーブルの構築ロジック
  - signal_generator.py     : final_score 計算と signals テーブルへの書き込み
- execution/
  - __init__.py
  - （発注・注文管理に関する実装はここに置く想定）
- monitoring/
  - （監視・メトリクス関連の実装を置く想定）

---

## 設計上の注意点 / 運用上の注意

- 多くのモジュールは「ルックアヘッドバイアス防止」の考え方を取り入れ、target_date 時点で利用可能なデータのみで計算する設計です。
- J-Quants API の呼び出しにはレート制限とリトライが組み込まれていますが、実運用時は API 利用制約を確認してください。
- DuckDB のスキーマは冪等に作成されますが、バックアップ・マイグレーション戦略は別途必要です。
- secrets（API トークン等）は .env または本番用シークレット管理により安全に保管してください。
- KABUSYS_ENV により動作モードを切り替え、paper_trading / live のときは十分な検証とリスク管理を行ってください。

---

## 開発／デバッグ

- ログレベルは LOG_LEVEL 環境変数で制御
- 開発時に自動 .env 読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定
- 単体テストや CI を追加する場合は、settings をモックするか KABUSYS_DISABLE_AUTO_ENV_LOAD を設定して環境依存を切り離してください

---

必要であれば README に以下を追加できます：
- .env.example のテンプレート
- 詳細なテーブル定義（DataSchema.md の抜粋）
- デプロイ / cron / Airflow での運用例
- 発注層（execution）の具体的な実装例

要望があれば追記します。