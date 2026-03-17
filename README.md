# KabuSys

日本株向けの自動売買・データ基盤ライブラリです。J-Quants や RSS を用いたデータ収集、DuckDB を用いたデータスキーマ定義・初期化、ETL パイプライン、データ品質チェック、監査ログ（発注〜約定のトレーサビリティ）などを提供します。

---

## 主要目的（プロジェクト概要）

- J-Quants API から株価（日次OHLCV）、四半期財務データ、市場カレンダーを安全かつ冪等に取得・保存する
- RSS フィードからニュースを収集して正規化・保存し、銘柄コードとの紐付けを行う
- DuckDB 上に Data Platform 用のスキーマ（Raw / Processed / Feature / Execution / Audit）を定義・初期化する
- ETL パイプライン（差分更新／バックフィル／品質チェック）を提供する
- 発注〜約定の監査ログを UUID 階層でトレース可能に記録する
- 各種設計方針（レート制限、リトライ、SSRF対策、Gzip/サイズ制限、冪等保存など）を実装

---

## 機能一覧

- 環境変数・設定読み込み（.env / .env.local 自動読み込み、無効化フラグあり）
- J-Quants API クライアント
  - レートリミット（120 req/min）管理
  - リトライ（指数バックオフ、最大3回）、401 時の自動トークン更新
  - データ取得（株価日足、財務、マーケットカレンダー）
  - DuckDB へ冪等に保存する `save_*` ヘルパー
- ニュース収集（RSS）
  - URL 正規化・トラッキングパラメータ除去
  - SSRF 対策（スキーム検証／プライベートIP検出／リダイレクト検査）
  - XML の安全パース（defusedxml）
  - 受信サイズ制限（10MB）と Gzip 解凍の安全対策
  - 記事ID は正規化 URL の SHA-256（先頭32桁）で冪等性を確保
  - raw_news / news_symbols への冪等保存（チャンク挿入、INSERT ... RETURNING）
- DuckDB スキーマ管理
  - Raw / Processed / Feature / Execution / Audit 層のテーブル定義
  - インデックス定義
  - `init_schema()` / `init_audit_schema()` による初期化 API
- ETL パイプライン
  - 差分更新・バックフィル（デフォルト backfill_days=3）
  - カレンダーの先読み（デフォルト 90 日）
  - 品質チェック（欠損・重複・スパイク・日付不整合）
  - ETL 実行結果を表す `ETLResult`
- データ品質チェックモジュール（quality）
  - `run_all_checks()` でまとめて実行
  - 各チェックは問題点のサンプルを含む `QualityIssue` を返す
- 監査ログ（audit）
  - signal_events / order_requests / executions など監査用テーブル群
  - 発注フローの完全トレースを想定

---

## 必要条件

- Python 3.10+
- 依存ライブラリ（代表例）
  - duckdb
  - defusedxml
（プロジェクトの pyproject.toml / requirements.txt に従ってください）

インストール例（開発時）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"   # プロジェクトのセットアップ方法に合わせて
```

---

## 環境変数（主なもの）

- JQUANTS_REFRESH_TOKEN （必須）: J-Quants のリフレッシュトークン
- KABU_API_PASSWORD （必須）: kabuステーション API のパスワード
- KABU_API_BASE_URL : kabuapi のベースURL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN （必須）: Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID （必須）: Slack 通知先チャンネル ID
- DUCKDB_PATH : デフォルト DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH : 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV : 実行環境（development / paper_trading / live、デフォルト: development）
- LOG_LEVEL : ログレベル（DEBUG / INFO / WARNING / ERROR / CRITICAL）

自動 .env 読み込み:
- プロジェクトルート（.git または pyproject.toml を基準）にある `.env` と `.env.local` を、自動で読み込みます。
- 読み込み優先順位: OS 環境 > .env.local > .env
- 自動読み込みを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

注意: 必須環境変数が無い場合、Settings プロパティが ValueError を投げます。

---

## セットアップ手順（概要）

1. リポジトリをクローンし Python 環境を構築
2. 依存パッケージをインストール（duckdb, defusedxml など）
3. プロジェクトルートに `.env` を作成し必要な環境変数を設定
4. DuckDB スキーマを初期化

例:
```python
from kabusys.data import schema
conn = schema.init_schema("data/kabusys.duckdb")
# 監査スキーマを追加する場合
from kabusys.data import audit
audit.init_audit_schema(conn)
```

---

## 使い方（主な API / 実行例）

以下はライブラリの典型的な使い方例です（スクリプト/ジョブとして実行）。

1) DuckDB スキーマの初期化
```python
from kabusys.data import schema
conn = schema.init_schema("data/kabusys.duckdb")
```

2) 日次 ETL の実行（市場カレンダー・株価・財務の差分取得＋品質チェック）
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl
from kabusys.data import schema

conn = schema.get_connection("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

3) J-Quants API を直接呼ぶ（テスト／カスタム取得）
```python
from kabusys.data import jquants_client as jq
# トークンを明示的に渡すことも、内部キャッシュを使用することも可能
records = jq.fetch_daily_quotes(code="7203", date_from=date(2024,1,1), date_to=date(2024,1,31))
saved = jq.save_daily_quotes(conn, records)
```

4) RSS ニュース収集と保存
```python
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
from kabusys.data import schema

conn = schema.get_connection("data/kabusys.duckdb")
# known_codes: 抽出対象の有効な銘柄コードセット（例: 運用する銘柄一覧）
known_codes = {"7203", "6758", "9984"}
results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
print(results)  # {source_name: 新規保存数, ...}
```

5) 品質チェックを個別に実行
```python
from kabusys.data import quality
issues = quality.run_all_checks(conn, target_date=None)
for i in issues:
    print(i.check_name, i.severity, i.detail)
```

---

## 主要モジュール説明

- kabusys.config
  - Settings クラスで環境変数を取得。自動 .env 読み込みを行う。
- kabusys.data.jquants_client
  - J-Quants API との通信、レート制御、リトライ、保存ヘルパーを実装。
- kabusys.data.news_collector
  - RSS 取得・前処理・正規化・DuckDB への冪等保存・銘柄抽出機能を提供。
- kabusys.data.schema
  - DuckDB の DDL（Raw/Processed/Feature/Execution 等）を定義し初期化する。
- kabusys.data.pipeline
  - 差分 ETL（prices / financials / calendar）や run_daily_etl のエントリポイントを提供。
- kabusys.data.quality
  - 欠損、重複、スパイク、日付整合性チェックを行う。
- kabusys.data.audit
  - 監査ログ用テーブル（signal_events, order_requests, executions）を初期化する。
- kabusys.strategy, kabusys.execution, kabusys.monitoring
  - 本リポジトリではパッケージのプレースホルダ（拡張ポイント）。戦略/発注/監視ロジックを実装する場所。

---

## ディレクトリ構成

リポジトリ内の主要ファイル構成（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                       -- 環境変数・設定管理
  - data/
    - __init__.py
    - jquants_client.py              -- J-Quants API クライアント & 保存
    - news_collector.py              -- RSS ニュース収集
    - schema.py                      -- DuckDB スキーマ定義・初期化
    - pipeline.py                    -- ETL パイプライン（差分更新・run_daily_etl 等）
    - audit.py                       -- 監査ログテーブル定義・初期化
    - quality.py                     -- データ品質チェック
  - strategy/
    - __init__.py                    -- 戦略層（拡張ポイント）
  - execution/
    - __init__.py                    -- 発注層（拡張ポイント）
  - monitoring/
    - __init__.py                    -- 監視（拡張ポイント）

---

## 設計上の注意点 / 運用上のポイント

- レート制限: J-Quants は 120 req/min を想定。jquants_client は固定間隔スロットリングで制御します。大量取得時は注意。
- 冪等性: raw_* テーブルへの保存は ON CONFLICT 系 SQL による上書き/無視で冪等に設計されています。
- トークン管理: 401 を受けた場合は自動でリフレッシュを試みます（最大1回/試行）。
- セキュリティ:
  - RSS の XML パースは defusedxml を利用（XML Bomb 防御）。
  - RSS の URL はスキーム検証とプライベートIP 判定により SSRF を緩和。
  - HTTP レスポンスサイズや Gzip 解凍後サイズのチェックを行い DoS を緩和。
- テスト:
  - config の自動 .env 読み込みは `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能（単体テスト時に便利）。
  - news_collector._urlopen() をモックしてネットワーク依存を切り分けられます。

---

## トラブルシューティング（よくある問題）

- ValueError: 環境変数が設定されていません
  - 必須環境変数（例: JQUANTS_REFRESH_TOKEN / SLACK_BOT_TOKEN 等）が未設定です。.env を作成して設定してください。
- DuckDB の接続やテーブルが無い
  - 初回は schema.init_schema() を呼んでテーブルを作成してください。get_connection() は既存 DB の接続のみ行います。
- 429 / 5xx エラー
  - jquants_client はリトライしますが、頻発する場合はレートや API 利用状況を確認してください。

---

## 今後の拡張ポイント

- strategy パッケージに実戦用戦略の実装
- execution パッケージで実際のブローカー API 連携実装（kabuステーション等）
- monitoring にアラート・メトリクス収集の実装
- CI 用の DB 初期化・モックを用いたユニットテスト充実化

---

この README はコードベースの主要機能と使い方の概要をまとめたものです。詳細は該当モジュールのドキュメントとソースコードの docstring を参照してください。