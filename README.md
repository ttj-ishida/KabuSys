# KabuSys

日本株向け自動売買プラットフォームのコアライブラリ（モジュール群）です。  
データ収集（J-Quants / RSS）、ETL パイプライン、データ品質チェック、マーケットカレンダー管理、監査ログ（発注〜約定トレーサビリティ）などの機能を備えています。

> 注意: 本リポジトリはライブラリ/内部モジュール群であり、実行バイナリやUIは含みません。アプリケーションからこれらの API を呼び出して利用します。

---

目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 簡単な使い方（コード例）
- 環境変数
- ディレクトリ構成

---

## プロジェクト概要

KabuSys は、J-Quants API や RSS ニュースを用いた日本株のデータプラットフォームと、自動売買に必要となる ETL・品質検査・監査ログ基盤を提供する Python モジュール群です。  
設計上の主要なポイント:

- J-Quants API に対するレート制御とリトライ、ID トークン自動リフレッシュ
- DuckDB を用いたローカルデータベース（冪等な保存、ON CONFLICT 処理）
- RSS ニュース収集におけるセキュリティ対策（SSRF/XML bomb 対策等）
- データ品質チェック（欠損・重複・スパイク・日付不整合）
- 監査ログ（signal → order_request → execution のトレーサビリティ）

---

## 機能一覧

主な機能（モジュール別）

- kabusys.config
  - 環境変数の自動読み込み（`.env`, `.env.local`）と設定アクセス（Settings）
  - 環境モード・ログレベルの検証

- kabusys.data.jquants_client
  - J-Quants API クライアント（株価日足 / 財務データ / マーケットカレンダー取得）
  - レートリミッタ、指数バックオフリトライ、401 リフレッシュ処理
  - DuckDB へ冪等保存する save_* 関数

- kabusys.data.news_collector
  - RSS フィード取得、前処理、記事ID生成（正規化URL→SHA-256）
  - SSRF/プライベートIP/サイズ上限/defusedxml による安全な収集
  - raw_news と news_symbols への冪等保存

- kabusys.data.schema
  - DuckDB 用スキーマ定義と初期化（Raw / Processed / Feature / Execution 層）
  - インデックス作成・テーブル依存順を考慮した初期化

- kabusys.data.pipeline
  - 日次 ETL（市場カレンダー → 株価 → 財務 → 品質チェック）
  - 差分更新、バックフィル、品質チェックの集約
  - ETL 結果を ETLResult で返却

- kabusys.data.calendar_management
  - market_calendar を使った営業日判定（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）
  - 夜間カレンダー更新ジョブ

- kabusys.data.quality
  - 欠損、スパイク、重複、日付不整合のチェックと QualityIssue 返却
  - run_all_checks による一括実行

- kabusys.data.audit
  - 監査ログ用テーブル（signal_events / order_requests / executions）と初期化
  - 発注〜約定までのトレーサビリティを確保

---

## セットアップ手順

前提: Python 3.9+（typing 機能や型記法を利用しています）

1. リポジトリをクローン（またはソースを取得）
   - (例) git clone ...

2. 仮想環境作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージのインストール
   - ※プロジェクトに requirements.txt / pyproject.toml がある場合はそちらを使用してください。
   - 最低依存例:
     - duckdb
     - defusedxml
   - インストール例:
     - pip install duckdb defusedxml
     - または開発インストール: pip install -e .

4. 環境変数設定
   - プロジェクトルート（.git もしくは pyproject.toml があるディレクトリ）に `.env` / `.env.local` を配置すると、自動でロードされます（無効化: KABUSYS_DISABLE_AUTO_ENV_LOAD=1）。
   - 必須環境変数については後述の「環境変数」参照。

5. DuckDB スキーマ初期化
   - Python REPL またはスクリプトから以下を実行:
     - from kabusys.data import schema
     - conn = schema.init_schema("data/kabusys.duckdb")  # ":memory:" も可
   - 監査ログだけ別 DB にする場合:
     - from kabusys.data import audit
     - audit_conn = audit.init_audit_db("data/kabusys_audit.duckdb")

---

## 簡単な使い方（コード例）

- DuckDB スキーマ初期化（例）

```python
from kabusys.data import schema

conn = schema.init_schema("data/kabusys.duckdb")
```

- 日次 ETL 実行（run_daily_etl）

```python
from kabusys.data.pipeline import run_daily_etl
from kabusys.data import schema

conn = schema.init_schema("data/kabusys.duckdb")
result = run_daily_etl(conn)  # デフォルト: 今日を対象に実行
print(result.to_dict())
```

- RSS ニュース収集（run_news_collection）

```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data import schema

conn = schema.init_schema("data/kabusys.duckdb")
# known_codes を渡すと記事から銘柄コード抽出→news_symbols へ紐付けを行う
known_codes = {"7203", "6758", "9984"}  # 必要に応じて銘柄リストを準備
results = run_news_collection(conn, known_codes=known_codes)
print(results)
```

- J-Quants から株価を直接取得して保存する

```python
from kabusys.data import jquants_client as jq
from kabusys.data import schema
from datetime import date

conn = schema.init_schema("data/kabusys.duckdb")
records = jq.fetch_daily_quotes(date_from=date(2024, 1, 1), date_to=date(2024, 1, 31))
saved = jq.save_daily_quotes(conn, records)
print(saved)
```

- 監査ログの初期化

```python
from kabusys.data import audit
conn_audit = audit.init_audit_db("data/kabusys_audit.duckdb")
```

---

## 環境変数（主なもの）

必須:
- JQUANTS_REFRESH_TOKEN
  - J-Quants の refresh token（get_id_token に使用）
- KABU_API_PASSWORD
  - kabuステーション等の API パスワード
- SLACK_BOT_TOKEN
  - Slack 通知のボットトークン
- SLACK_CHANNEL_ID
  - 通知先チャンネル ID

任意 / デフォルトあり:
- KABUSYS_ENV
  - 有効値: development, paper_trading, live
  - デフォルト: development
- LOG_LEVEL
  - 有効値: DEBUG, INFO, WARNING, ERROR, CRITICAL
  - デフォルト: INFO
- DUCKDB_PATH
  - デフォルト: data/kabusys.duckdb
- SQLITE_PATH
  - デフォルト: data/monitoring.db

自動ロード制御:
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  - .env 自動読み込みを無効化（テストで便利）

.env の例（抜粋）

```
JQUANTS_REFRESH_TOKEN=your_refresh_token_here
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C0123456789
KABUSYS_ENV=development
LOG_LEVEL=INFO
DUCKDB_PATH=data/kabusys.duckdb
```

※ config.Settings._require は未設定時に ValueError を投げます。`.env.example` を参考に設定してください。

---

## 実装上の注意点 / 設計メモ

- J-Quants クライアントは 120 req/min のレート制御を実装しています。大量に連続リクエストする場合は注意してください。
- HTTP エラーやネットワーク障害には指数バックオフと最大リトライを実装しています（408/429/5xx を対象）。401 を受けた場合はリフレッシュトークンから id_token を再取得して一度だけリトライします。
- DuckDB へは冪等性を考慮した INSERT（ON CONFLICT）で保存します。初回ロードや再実行時に重複を防ぎます。
- RSS 収集でのセキュリティ対策:
  - defusedxml を使用し XML ボム対策
  - リダイレクト先検査 / プライベートアドレス検出で SSRF を防止
  - レスポンスサイズ上限を設定（10MB）
- 品質チェックは Fail-Fast ではなく、全チェックを実行して問題リストを返す方式です（ETL 側で結果に応じたアクションを行ってください）。
- 監査ログ（audit）は一切削除しない設計（FOREIGN KEY は ON DELETE RESTRICT）で、発注から約定までを UUID で追跡します。

---

## ディレクトリ構成

リポジトリ内の主要ファイル・ディレクトリ（今回与えられたコードベースに基づく）

- src/
  - kabusys/
    - __init__.py
    - config.py               -- 環境変数 / 設定管理
    - data/
      - __init__.py
      - jquants_client.py     -- J-Quants API クライアント、保存ロジック
      - news_collector.py     -- RSS ニュース収集 / 保存 / 銘柄抽出
      - pipeline.py          -- ETL パイプライン（run_daily_etl 等）
      - schema.py            -- DuckDB スキーマ定義と init_schema
      - calendar_management.py-- カレンダー更新 / 営業日判定
      - audit.py             -- 監査ログスキーマ初期化
      - quality.py           -- データ品質チェック
      - pipeline.py          -- ETL ロジック（重複記載あり）
    - strategy/                -- 戦略関連パッケージ（エントリプレースホルダ）
      - __init__.py
    - execution/               -- 発注 / 実行関連パッケージ（エントリプレースホルダ）
      - __init__.py
    - monitoring/              -- 監視関連（空の __init__ あり）
      - __init__.py

---

補足・連絡事項
- この README はコードベースからの抽出による説明です。実運用では追加の設定・バリデーション、外部サービスとの連携（証券会社 API、Slack 通知等）を組み合わせる必要があります。
- 依存パッケージや CI / packaging の実体はリポジトリの pyproject.toml / requirements.txt を参照してください（本ドキュメントでは最小限の依存を記載しています）。

必要であれば、README に:
- 開発者向けのデバッグ方法やユニットテストの実行方法
- 例となる .env.example の全文
- よくあるトラブルシュート（トークンの更新方法、DuckDB ファイル権限等）

を追記します。どれを追加しますか？