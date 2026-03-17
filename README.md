# KabuSys — 日本株自動売買システム

KabuSys は日本株の自動売買に必要なデータ収集・ETL・監査・発注管理の基盤を提供するライブラリ群です。J-Quants や RSS を利用したデータ収集、DuckDB を用いたスキーマ定義と差分 ETL、品質チェック、監査ログの仕組みを備えています。

目次
- プロジェクト概要
- 主な機能
- 動作環境 / 依存関係
- セットアップ手順
- 使い方（コード例）
- 環境変数一覧
- ディレクトリ構成（主要ファイル）
- よくある注意点

---

## プロジェクト概要

KabuSys は以下を主目的とした内部ライブラリです。

- J-Quants API からの株価・財務・マーケットカレンダー取得（レート制御・リトライ・トークン自動リフレッシュ対応）
- RSS フィードからのニュース収集と記事・銘柄紐付け（SSRF 対策、XML 防御、サイズ制限、冪等保存）
- DuckDB によるデータレイヤ（Raw / Processed / Feature / Execution）スキーマの定義・初期化
- 日次 ETL パイプライン（差分取得・バックフィル・品質チェック）
- 監査ログ（シグナル→発注→約定のトレーサビリティ）
- 市場カレンダー管理（営業日判定・前後営業日取得等）

設計方針としては「冪等性」「トレーサビリティ」「外部入力に対する堅牢性（SSRF, XML攻撃対策など）」を重視しています。

---

## 主な機能

- jquants_client
  - 株価日足（OHLCV）、財務（四半期 BS/PL）、マーケットカレンダーの取得
  - レート制御（120 req/min）、再試行（指数バックオフ）、401 時のトークン自動リフレッシュ
  - DuckDB へ冪等保存（ON CONFLICT DO UPDATE）
- news_collector
  - RSS フィードからニュース取得、テキスト前処理、記事IDのハッシュ化による冪等保存
  - SSRF 防止のためスキーム/ホストチェック、gzip 展開上限、defusedxml を利用した XML パース
  - 銘柄コード抽出と news_symbols への保存
- data.schema
  - Raw / Processed / Feature / Execution 層を含む DuckDB スキーマ定義と初期化
- data.pipeline
  - 日次 ETL（差分取得・バックフィル・品質チェック）を一括実行
- data.calendar_management
  - 営業日判定、next/prev trading day、カレンダーの夜間更新ジョブ
- data.audit
  - シグナル・発注・約定の監査テーブル（UUID によるトレーサビリティ）
- data.quality
  - 欠損、スパイク、重複、日付不整合などの品質チェック

---

## 動作環境 / 依存関係

- Python 3.10+
- 必須パッケージ（主なもの）
  - duckdb
  - defusedxml

インストール例（仮想環境推奨）:
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb defusedxml
# 開発インストール（プロジェクトルートに pyproject.toml/setup.py がある前提）
pip install -e .
```

必要な外部サービス:
- J-Quants API（リフレッシュトークン）
- kabuステーション API（発注に関する設定。KabuSys 内に発注クライアントは雛形）
- Slack（通知用トークン/チャンネル）

---

## セットアップ手順

1. リポジトリをクローンして仮想環境を用意
2. 必要ライブラリをインストール（上記参照）
3. 環境変数を設定
   - 開発時はプロジェクトルートに `.env` / `.env.local` を用意できます
   - 自動読み込みはデフォルトで有効（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）
4. DuckDB スキーマ初期化
   - 例: Python REPL / スクリプトで実行
     ```python
     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")
     ```
   - 監査ログを別 DB にしたい場合:
     ```python
     from kabusys.data.audit import init_audit_db
     conn_audit = init_audit_db("data/kabusys_audit.duckdb")
     ```
5. ETL 実行やニュース収集の実行準備完了

---

## 使い方（簡単なコード例）

- settings（環境変数参照）
```python
from kabusys.config import settings
print(settings.jquants_refresh_token)  # 未設定なら ValueError
```

- DB 初期化
```python
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")
```

- 日次 ETL を実行（デフォルトでは今日を対象）
```python
from kabusys.data.pipeline import run_daily_etl
result = run_daily_etl(conn)
print(result.to_dict())
```

- ニュース収集（既知銘柄 set を渡して紐付け）
```python
from kabusys.data.news_collector import run_news_collection
known_codes = {"7203", "6758"}  # 例
res = run_news_collection(conn, known_codes=known_codes)
print(res)  # {source_name: 新規保存数}
```

- J-Quants のトークン取得 / API 呼び出し
```python
from kabusys.data.jquants_client import get_id_token, fetch_daily_quotes
token = get_id_token()  # settings.jquants_refresh_token を使用
records = fetch_daily_quotes(id_token=token, date_from=..., date_to=...)
```

---

## 環境変数一覧

必須 (未設定だと起動時に例外を投げる)
- JQUANTS_REFRESH_TOKEN — J-Quants リフレッシュトークン
- KABU_API_PASSWORD — kabu API 用パスワード
- SLACK_BOT_TOKEN — Slack ボットトークン
- SLACK_CHANNEL_ID — 通知先 Slack チャンネル ID

オプション / デフォルトあり
- KABUSYS_ENV — 開発環境。許容値: development, paper_trading, live（デフォルト: development）
- LOG_LEVEL — ログレベル（DEBUG / INFO / WARNING / ERROR / CRITICAL）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト: data/monitoring.db）

自動挙動制御
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 — プロジェクトルートの .env 自動読み込みを無効化

.env の読み込み順序:
OS 環境変数 > .env.local > .env（ただし OS 環境変数は保護され上書きされません）

---

## ディレクトリ構成（主要ファイル）

以下は src/kabusys 以下の主要モジュールと役割の抜粋です。

- kabusys/
  - __init__.py
  - config.py
    - 環境変数の読み込みと Settings クラス（自動 .env ロード、必須チェック）
  - data/
    - __init__.py
    - jquants_client.py
      - J-Quants API クライアント（取得・リトライ・レート制御・保存関数）
    - news_collector.py
      - RSS からニュース収集、前処理、DuckDB 保存、銘柄抽出
    - schema.py
      - DuckDB の全スキーマ定義（Raw/Processed/Feature/Execution）と init_schema
    - pipeline.py
      - 差分 ETL、日次 ETL のエントリポイント（run_daily_etl など）
    - calendar_management.py
      - 市場カレンダー管理、営業日判定、夜間更新ジョブ
    - audit.py
      - 監査ログ用テーブル定義と初期化（トレーサビリティ）
    - quality.py
      - データ品質チェック（欠損・スパイク・重複・日付不整合）
  - strategy/
    - __init__.py （戦略モジュールのプレースホルダ）
  - execution/
    - __init__.py （発注ロジックのプレースホルダ）
  - monitoring/
    - __init__.py （監視・メトリクス関連のプレースホルダ）

---

## よくある注意点 / トラブルシューティング

- 環境変数が足りないと Settings が ValueError を投げます。エラーメッセージの指示に従って .env を準備してください。
- DuckDB のファイルパスの親ディレクトリは init_schema が自動で作成しますが、ファイルシステムの権限に注意してください。
- J-Quants API はレート制限（120 req/min）があります。jquants_client は内部でスロットリングを行いますが、大量並列実行は避けてください。
- news_collector は受信サイズ・gzip 解凍後サイズの上限を設けています。大きなフィードはスキップされることがあります。
- run_daily_etl は個別ステップを独立してエラーハンドリングします。何らかのステップで例外が発生しても他のステップは継続され、ETLResult にエラー情報が蓄積されます。
- テスト時に .env の自動読み込みを無効にしたい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

必要であれば README にサンプル .env.example を追加したり、CI 用の実行例（cron / GitHub Actions）や発注フローのサンプルを追記できます。どの情報を追加したいか教えてください。