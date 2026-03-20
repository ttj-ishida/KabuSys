# KabuSys

日本株向け自動売買プラットフォームのライブラリ群です。データの取得・ETL、特徴量計算、シグナル生成、ニュース収集、マーケットカレンダー管理、DuckDB スキーマ／監査ログなど、戦略実装に必要な基盤機能を提供します。

## 目次
- プロジェクト概要
- 機能一覧
- 動作要件 / 依存関係
- セットアップ手順
- 簡単な使い方（コード例）
- 環境変数（.env）について
- ディレクトリ構成

---

## プロジェクト概要
KabuSys は、日本株市場向けの自動売買システムに必要なデータ基盤・戦略基盤機能を提供する Python パッケージです。主な目的は以下です。

- J-Quants API から株価・財務・カレンダー等の市場データを取得し DuckDB に保存する（差分取得・冪等保存）
- 研究結果（raw factor）を基に特徴量を構築し features テーブルに保存する
- 正規化済みファクターと AI スコアを統合して売買シグナルを生成する
- RSS ベースのニュース収集と銘柄紐付け
- マーケットカレンダー管理（営業日判定、次/前営業日取得）
- 監査ログ（signal → order → execution のトレーサビリティ）を保持するスキーマ

設計の要点：
- ルックアヘッドバイアス回避（target_date 時点のデータのみ使用）
- 冪等性（DB 保存は ON CONFLICT / DO UPDATE 等で重複を避ける）
- 外部発注 API への直接依存を持たず、execution 層と分離した設計
- DuckDB を中心とする軽量オンディスク DB

---

## 機能一覧
主な機能（モジュール／機能名）:

- kabusys.config
  - .env / .env.local / 環境変数から設定を自動読み込み
  - settings オブジェクト経由で設定値取得（例: settings.jquants_refresh_token）
- kabusys.data.jquants_client
  - J-Quants API クライアント（レート制御、リトライ、トークン自動更新）
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - save_* 関数で DuckDB へ冪等保存
- kabusys.data.schema
  - DuckDB スキーマ定義と初期化（init_schema）
  - get_connection
- kabusys.data.pipeline
  - 日次 ETL 実行（run_daily_etl）および個別ジョブ（run_prices_etl 等）
  - 差分取得・品質チェック連携
- kabusys.data.news_collector
  - RSS フィード収集、記事正規化、raw_news 保存
  - 銘柄コード抽出・news_symbols 保存
- kabusys.data.calendar_management
  - market_calendar 更新、is_trading_day / next_trading_day / prev_trading_day 等
- kabusys.research
  - ファクター計算（calc_momentum, calc_volatility, calc_value）
  - 研究用ユーティリティ（calc_forward_returns, calc_ic, factor_summary, rank）
- kabusys.strategy
  - build_features(conn, target_date): ファクター正規化と features への保存
  - generate_signals(conn, target_date, ...): features / ai_scores を統合して signals を生成
- kabusys.data.audit
  - 監査ログ用スキーマ（signal_events, order_requests, executions 等）

---

## 動作要件 / 依存関係
- Python 3.10 以上（コード内での型アノテーションに PEP 604 形式を使用しています）
- 必要なパッケージ（最低限）:
  - duckdb
  - defusedxml
- そのほか標準ライブラリを多用しています（urllib, datetime, logging 等）。

インストール例（ローカル開発）:
```bash
python -m pip install -e .   # パッケージとしてセットアップする場合
python -m pip install duckdb defusedxml
```

※プロジェクトの setup/pyproject に依存関係が記載されている場合はそちらを参照してください。

---

## セットアップ手順

1. リポジトリをクローン / ワークディレクトリに配置
2. Python 3.10+ の仮想環境を作成して有効化
   ```bash
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```
3. 必要パッケージのインストール
   ```bash
   python -m pip install -e .
   python -m pip install duckdb defusedxml
   ```
4. 環境変数設定（.env をプロジェクトルートに作成）
   - 自動的に .env/.env.local がプロジェクトルートからロードされます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）
   - 必須項目は下記「環境変数（.env）」参照
5. DuckDB スキーマ初期化
   - デフォルトの DuckDB ファイルパスは settings.duckdb_path（既定: data/kabusys.duckdb）
   - 例:
     ```python
     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")
     ```
6. ETL や戦略処理を実行

---

## 簡単な使い方（コード例）

以下は最小限の実行フロー例です（Python スクリプトや REPL で実行）:

- DuckDB 初期化:
```python
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
```

- 日次 ETL 実行（J-Quants トークンは settings.jquants_refresh_token で自動取得）:
```python
from kabusys.data.pipeline import run_daily_etl
from datetime import date

result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- 特徴量作成:
```python
from kabusys.strategy import build_features
from datetime import date

n = build_features(conn, target_date=date.today())
print(f"features upserted: {n}")
```

- シグナル生成:
```python
from kabusys.strategy import generate_signals
from datetime import date

count = generate_signals(conn, target_date=date.today())
print(f"signals written: {count}")
```

- ニュース収集（既知の銘柄コード set を渡すと紐付けも行う）:
```python
from kabusys.data.news_collector import run_news_collection

# sources を省略するとデフォルトの RSS ソースを使用
# known_codes は set[str]（例: {'7203', '6758', ...}）
res = run_news_collection(conn, known_codes={'7203', '6758'})
print(res)
```

- カレンダー夜間更新:
```python
from kabusys.data.calendar_management import calendar_update_job

saved = calendar_update_job(conn)
print(f"calendar saved: {saved}")
```

注意:
- 各 API は target_date としてその日時点で利用可能なデータのみを参照する設計です（ルックアヘッドを防止）。
- 多くの関数は DuckDB 接続オブジェクト（duckdb.DuckDBPyConnection）を受け取ります。

---

## 環境変数（.env）について

自動読み込み:
- パッケージはプロジェクトルート（.git または pyproject.toml を基準）にある `.env` / `.env.local` を自動ロードします。
- 読み込み順: OS 環境変数 > .env.local > .env
- 自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

主な必須設定（.env に設定が必要なキー）:
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（API 認証用）
- KABU_API_PASSWORD: kabuステーション API 用パスワード（発注連携を行う場合）
- SLACK_BOT_TOKEN: Slack 通知を行う場合に必要
- SLACK_CHANNEL_ID: Slack 通知先チャンネル

任意 / デフォルト:
- KABUSYS_ENV: development / paper_trading / live （デフォルト: development）
- LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 1（自動 .env ロードを無効化）
- DUCKDB_PATH: デフォルト data/kabusys.duckdb
- SQLITE_PATH: デフォルト data/monitoring.db
- KABUS_API_BASE_URL: kabusapi のベース URL（デフォルト: http://localhost:18080/kabusapi）

.example（参考）:
```
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C12345678
KABUSYS_ENV=development
LOG_LEVEL=INFO
DUCKDB_PATH=data/kabusys.duckdb
```

---

## ディレクトリ構成（主要ファイル）
リポジトリ配下の主なモジュール構成（src/kabusys 以下）:

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / 設定管理
  - data/
    - __init__.py
    - jquants_client.py      — J-Quants API クライアント & DuckDB 保存
    - news_collector.py      — RSS ニュース収集・保存・銘柄抽出
    - schema.py              — DuckDB スキーマ定義・初期化
    - stats.py               — 統計ユーティリティ（zscore_normalize 等）
    - pipeline.py            — ETL パイプライン（run_daily_etl 等）
    - features.py            — features の公開インターフェース
    - calendar_management.py — market_calendar 管理
    - audit.py               — 監査ログスキーマ
    - execution/              — execution 層（空の __init__.py が含まれる）
  - research/
    - __init__.py
    - factor_research.py     — ファクター計算（mom/vol/value）
    - feature_exploration.py — 研究用ユーティリティ（forward returns, IC, summary）
  - strategy/
    - __init__.py
    - feature_engineering.py — build_features（正規化・UPSERT）
    - signal_generator.py    — generate_signals（final_score 計算・BUY/SELL 生成）
  - monitoring/              — 監視系 DB / スクリプト（実装は監視用）
  - その他ドキュメントやユーティリティファイル

---

## 備考 / 運用上の注意
- DuckDB のバージョンや SQL 構文の互換性により、環境によっては細部の調整が必要になる場合があります。
- J-Quants の API レート制限・認証仕様は外部仕様であり、変更があった場合は jquants_client の挙動を確認してください。
- 本ライブラリは発注（実際の資金運用）へ直接接続する部分を限定的に持ちます。ライブ運用／実トレードを行う場合は十分な監査・リスク管理を実装してください。
- ログレベル・環境（development/paper_trading/live）は settings で制御できます。live 環境では特に注意して操作してください。

---

必要に応じて README に実行例スクリプト、.env.example、CI/デプロイ手順、開発用テスト手順などを追記できます。どの情報を優先して追加したいか教えてください。