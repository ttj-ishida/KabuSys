# KabuSys

日本株向けの自動売買・データプラットフォーム用ライブラリです。  
DuckDB を用いたデータレイヤ（Raw / Processed / Feature / Execution）、J-Quants からのデータ取得、RSS ニュース収集、データ品質チェック、研究用ファクター計算などの機能を備えます。

---

## 概要

KabuSys は次の目的を想定した内部ライブラリ群です。

- J-Quants API から株価・財務・市場カレンダーを取得して DuckDB に保存する ETL パイプライン
- RSS ベースのニュース収集と記事→銘柄紐付け
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 研究用ファクター計算（モメンタム・ボラティリティ・バリューなど）とIC計算・統計サマリー
- 監査（signal→order→execution）用テーブルの初期化
- 将来的な発注・実行ロジックを置くための Execution 層の枠組み

設計上のポイント:
- DuckDB をデータ永続化基盤に使用（ファイル/インメモリ両対応）
- 外部依存は最小化（標準ライブラリ中心、ただし duckdb / defusedxml 等は必要）
- 冪等性（ON CONFLICT / INSERT ... DO UPDATE / RETURNING）や Look-ahead-bias 対策、API レート制御などを考慮

---

## 主な機能一覧

- データ取得・保存
  - J-Quants クライアント（株価日足、財務、マーケットカレンダー）
  - DuckDB への冪等保存（raw_prices, raw_financials, market_calendar 等）
- ETL
  - 差分取得 / バックフィル対応 / カレンダー補正を含む日次 ETL（run_daily_etl）
- ニュース収集
  - RSS フィードの安全な取得（SSRF / gzip bomb 対策）
  - 記事正規化・ID生成（URL 正規化 → SHA-256 ハッシュ）と raw_news への保存
  - 記事から銘柄コード抽出と news_symbols への紐付け
- データ品質チェック
  - 欠損、スパイク（前日比閾値）、重複、日付不整合チェック
- 研究（Research）
  - ファクター計算（calc_momentum, calc_volatility, calc_value）
  - 将来リターン計算（calc_forward_returns）と IC（calc_ic）
  - 統計サマリー（factor_summary）、Z スコア正規化（zscore_normalize）
- カレンダー管理
  - 営業日判定 / next/prev/get_trading_days / 夜間カレンダー更新ジョブ
- 監査ログ初期化
  - signal_events / order_requests / executions 等の監査テーブル作成ユーティリティ

---

## 要件

- Python 3.10+
- 必要パッケージ（最低限）
  - duckdb
  - defusedxml

インストール例（仮想環境推奨）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install duckdb defusedxml
# パッケージを開発モードでインストールできる場合
pip install -e .
```

---

## 環境変数（必須 / 任意）

以下は主要な環境変数です。設定は .env/.env.local または OS 環境変数で行えます。パッケージはプロジェクトルートの .env を自動で読み込む挙動があります（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化）。

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD — kabu ステーション API パスワード（発注系を使う場合）
- SLACK_BOT_TOKEN — Slack 通知を使う場合の Bot トークン
- SLACK_CHANNEL_ID — Slack 通知先チャンネル ID

任意（デフォルトあり）:
- KABUSYS_ENV — 実行環境 (development | paper_trading | live)。デフォルト: development
- LOG_LEVEL — ログレベル (DEBUG | INFO | WARNING | ERROR | CRITICAL)。デフォルト: INFO
- DUCKDB_PATH — DuckDB ファイルパス。デフォルト: data/kabusys.duckdb
- SQLITE_PATH — 監視用 SQLite 等（デフォルト: data/monitoring.db）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 1 にすると自動 .env ロードを無効化

例 (.env):
```
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=DEBUG
```

---

## セットアップ手順

1. リポジトリをクローンする
   ```bash
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境・依存インストール
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -U pip
   pip install duckdb defusedxml
   # 任意でパッケージを editable にインストール
   pip install -e .
   ```

3. .env を作成して環境変数を設定（上記参照）

4. DuckDB スキーマ初期化
   Python スクリプトまたは対話環境で次を実行します:
   ```python
   from kabusys.data import schema
   from kabusys.config import settings

   conn = schema.init_schema(settings.duckdb_path)  # ファイルパスまたは ":memory:"
   ```

5. 監査ログ用スキーマ初期化（任意）
   ```python
   from kabusys.data import audit
   # schema.init_schema() で得た conn を渡す
   audit.init_audit_schema(conn)
   ```

---

## 使い方（代表的な API / ワークフロー）

- J-Quants のトークン取得
  ```python
  from kabusys.data import jquants_client as jq
  id_token = jq.get_id_token()  # settings.jquants_refresh_token を利用して取得
  ```

- 日次 ETL の実行
  ```python
  from kabusys.data import pipeline
  from kabusys.data import schema
  from kabusys.config import settings
  from datetime import date

  conn = schema.get_connection(settings.duckdb_path)
  # 初回は schema.init_schema() を呼ぶこと
  res = pipeline.run_daily_etl(conn, target_date=date.today())
  print(res.to_dict())
  ```

- ニュース収集ジョブの実行
  ```python
  from kabusys.data.news_collector import run_news_collection
  from kabusys.data.schema import get_connection

  conn = get_connection("data/kabusys.duckdb")
  # known_codes は既知銘柄コードのセット (例: {"6758", "7203", ...})
  result = run_news_collection(conn, known_codes={"6758","7203"})
  print(result)  # {source_name: new_count, ...}
  ```

- 研究用ファクター計算（例: モメンタム）
  ```python
  from kabusys.research import calc_momentum
  from kabusys.data.schema import get_connection
  from datetime import date

  conn = get_connection("data/kabusys.duckdb")
  recs = calc_momentum(conn, target_date=date(2024, 1, 31))
  # recs は [{"date": ..., "code": ..., "mom_1m": ..., ...}, ...]
  ```

- 将来リターン・IC 計算
  ```python
  from kabusys.research import calc_forward_returns, calc_ic, rank
  # forward = calc_forward_returns(conn, date(2024,1,31), horizons=[1,5,21])
  # factor_records は別途計算したファクターリスト
  ic = calc_ic(factor_records, forward, factor_col="mom_1m", return_col="fwd_1d")
  ```

- カレンダー更新ジョブ（夜間バッチ想定）
  ```python
  from kabusys.data.calendar_management import calendar_update_job
  saved = calendar_update_job(conn)
  ```

---

## ディレクトリ構成（主要ファイル）

以下はソースツリーの主要モジュール構成（抜粋）です。

- src/kabusys/
  - __init__.py
  - config.py  — 環境変数 / 設定管理（.env 自動ロード機構含む）
  - data/
    - __init__.py
    - jquants_client.py       — J-Quants API クライアント（取得＋保存）
    - news_collector.py      — RSS ニュース収集・保存・銘柄抽出
    - schema.py              — DuckDB スキーマ定義・初期化
    - stats.py               — 統計ユーティリティ（zscore_normalize 等）
    - pipeline.py            — ETL パイプライン（run_daily_etl 等）
    - features.py            — features の公開インターフェース
    - calendar_management.py — カレンダー管理（is_trading_day など）
    - quality.py             — データ品質チェック
    - audit.py               — 監査ログ初期化
    - etl.py                 — ETLResult の公開
  - research/
    - __init__.py
    - feature_exploration.py — 将来リターン・IC・サマリー等
    - factor_research.py     — モメンタム/ボラティリティ/バリュー計算
  - strategy/
    - __init__.py
  - execution/
    - __init__.py
  - monitoring/
    - __init__.py

---

## 注意点 / 実運用での考慮事項

- 本リポジトリはデータ取得・解析・監査の基盤を提供しますが、実際の発注（kabu ステーション連携）やリアル口座での運用時は十分なテストとリスク管理が必須です（例: 再現可能性、冪等性、二重発注防止、例外処理、監査ログ）。
- .env の自動ロードはプロジェクトルート（.git または pyproject.toml）を検出して行います。テストや CI で自動ロードを抑制したい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- J-Quants の API レートやレスポンスの欠損、RSS の不正コンテンツなどへの耐性（実装済みのリトライ・サイズ制限・SSRF防止など）がありますが、運用状況に応じたログ監視と警告対応を準備してください。
- DuckDB のバージョン差異により一部の制約やインデックスの扱いが異なることがあります。特に外部キー / ON DELETE 動作に関してはコード内コメントに注意しています。

---

## 貢献・開発

- コードはモジュール単位で分かれているため、ETL / データ保存 / 研究コードそれぞれを独立にユニットテストしやすい設計です。
- 開発時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して環境に依存しないテストを行うとよいです。
- 依存パッケージの更新や DuckDB のバージョンアップに伴う互換性チェックを推奨します。

---

必要であれば README に CLI の例（cron/jupyter/airflow での実行方法）、より詳細な .env.example、テーブルスキーマの ER 図、代表的な SQL クエリサンプルなども追加できます。どの情報を追加したいか教えてください。