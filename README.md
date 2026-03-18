# KabuSys — 日本株自動売買システム

日本株向けのデータ取得・ETL・監査・ニュース収集・カレンダー管理を行う内部モジュール群です。J-Quants / kabuステーション等の外部サービスと連携して、DuckDB を中心としたデータ基盤を構築し、自動売買や監視に必要なデータを安全に収集・保存します。

## 概要
- J-Quants API から株価日足（OHLCV）、四半期財務データ、JPXマーケットカレンダーを取得して DuckDB に保存します。
- RSS からニュース記事を収集し、正規化・前処理して保存、記事と銘柄コードを紐付けます（ニュース → シグナルの入力などに利用）。
- ETL パイプラインは差分取得・バックフィル・品質チェック（欠損・スパイク・重複・日付不整合）をサポートします。
- 監査ログ（シグナル→発注→約定のトレース）用スキーマを提供します。
- ネットワーク・セキュリティ対策（レート制限・リトライ・トークン自動リフレッシュ、SSRF 対策、XML パースの安全化、レスポンスサイズ制限 等）が組み込まれています。

## 主な機能
- jquants_client
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar（ページネーション対応）
  - レートリミット（120 req/min）、指数バックオフによるリトライ、401 時の自動トークンリフレッシュ
  - DuckDB への冪等保存（ON CONFLICT DO UPDATE）
- data.pipeline
  - 日次 ETL（run_daily_etl）：カレンダー取得 → 株価差分取得 → 財務差分取得 → 品質チェック
  - 差分更新ロジック・バックフィル対応
- data.news_collector
  - RSS 収集（defusedxml を利用して安全にパース）
  - URL 正規化・トラッキングパラメータ除去・記事 ID の SHA-256 ベース生成
  - SSRF 対策（スキーム検証・プライベートホスト拒否・リダイレクト検査）
  - メモリ DoS を防ぐ受信サイズ上限（デフォルト 10 MB）
  - DuckDB への冪等保存（INSERT ... RETURNING を利用）
- data.schema / data.audit
  - DuckDB のスキーマ定義（Raw / Processed / Feature / Execution / Audit 層）
  - 監査ログ用テーブル（signal_events, order_requests, executions 等）とインデックス
- data.quality
  - 欠損、スパイク、重複、日付不整合のチェックと QualityIssue レポート

## 要件
- Python 3.10 以上（型注釈で | を使用）
- 依存パッケージ（代表例）
  - duckdb
  - defusedxml
- （任意）J-Quants / kabuステーション 等の API アクセス用クレデンシャル

インストール例:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb defusedxml
# パッケージとして扱う場合:
# pip install -e .
```

（プロジェクト配布時には requirements.txt / pyproject.toml を用意してください）

## 環境変数 / 設定
config.Settings 経由で環境変数を参照します。プロジェクトルートにある `.env`、`.env.local` を自動で読み込みます（OS 環境 > .env.local > .env）。自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

必須変数:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API パスワード
- SLACK_BOT_TOKEN — Slack ボットトークン（通知用）
- SLACK_CHANNEL_ID — Slack チャンネル ID

任意／デフォルト:
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH — DuckDB ファイルパス（例: data/kabusys.duckdb）
- SQLITE_PATH — モニタリング用 SQLite パス（例: data/monitoring.db）
- KABUSYS_ENV — 環境（development / paper_trading / live、デフォルト development）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...）

例（.env）:
```
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

## セットアップ手順（簡易）
1. Python 仮想環境を作成して有効化
2. 依存パッケージをインストール（duckdb, defusedxml 等）
3. 必要な環境変数を `.env` に設定
4. DuckDB スキーマを初期化

例:
```python
from kabusys.data import schema

# ファイル DB を初期化（親ディレクトリがなければ自動作成）
conn = schema.init_schema("data/kabusys.duckdb")
conn.close()
```

監査ログ専用 DB を初期化する例:
```python
from kabusys.data import audit
conn = audit.init_audit_db("data/kabusys_audit.duckdb")
```

## 使い方（主要な呼び出し例）
- 日次 ETL 実行
```python
from datetime import date
from kabusys.data import pipeline, schema

conn = schema.get_connection("data/kabusys.duckdb")  # 事前に init_schema しておく
result = pipeline.run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- ニュース収集ジョブの実行（既知銘柄セットを与えて紐付け）
```python
from kabusys.data import news_collector, schema

conn = schema.get_connection("data/kabusys.duckdb")
known_codes = {"7203", "6758", "9984"}  # 例: 有効な銘柄コードセット
results = news_collector.run_news_collection(conn, known_codes=known_codes)
print(results)  # {source_name: 新規保存数}
```

- JPX カレンダーの夜間更新ジョブ
```python
from kabusys.data import calendar_management, schema

conn = schema.get_connection("data/kabusys.duckdb")
saved = calendar_management.calendar_update_job(conn)
print(f"saved: {saved}")
```

- J-Quants から直接データ取得（単発テスト）
```python
from kabusys.data import jquants_client as jq
quotes = jq.fetch_daily_quotes(code="7203", date_from=date(2024,1,1), date_to=date(2024,1,31))
```

## 設計上の注意 / セキュリティ
- jquants_client は API レート制限（120 req/min）を守るために固定間隔スロットリングを利用します。リトライは指数バックオフと HTTP ステータスに基づいた処理を行います。401 は自動的にトークンをリフレッシュして1回リトライします。
- news_collector は defusedxml を使用し XML Bomb 等を防ぎ、SSRF を防止するためスキームチェック・プライベートホスト拒否・リダイレクト検査を実施します。また受信データのサイズ上限を設けています。
- DuckDB への保存は基本的に冪等性を保つように SQL（ON CONFLICT DO UPDATE / DO NOTHING）を使用しています。
- 全ての監査用 TIMESTAMP は UTC を前提としています（audit.init_audit_schema は TimeZone を UTC に固定します）。
- .env/.env.local を用いた設定はデフォルトで自動読み込みされますが、テスト環境等で無効化したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

## ディレクトリ構成
プロジェクトの主要ファイル一覧（抜粋）:
- src/kabusys/
  - __init__.py
  - config.py  — 環境変数 / 設定管理（.env 自動読み込み）
  - data/
    - __init__.py
    - jquants_client.py  — J-Quants API クライアント（取得・保存）
    - news_collector.py  — RSS/ニュース収集と保存ロジック
    - schema.py  — DuckDB スキーマ定義と初期化
    - pipeline.py  — ETL パイプライン（差分取得・品質チェック）
    - calendar_management.py — カレンダー管理 / 営業日判定 / 更新ジョブ
    - audit.py  — 監査ログスキーマ（シグナル→発注→約定トレーサビリティ）
    - quality.py  — データ品質チェック
  - strategy/
    - __init__.py  — 戦略関連モジュールを配置するためのパッケージ
  - execution/
    - __init__.py  — 発注/約定連携（kabu 等）を実装するためのパッケージ
  - monitoring/
    - __init__.py  — モニタリング / アラート系モジュール用パッケージ

（上記はコードベースの抜粋です。実際のリポジトリではドキュメントやスクリプト類を追加してください）

## 開発メモ / 拡張ポイント
- strategy / execution / monitoring パッケージは骨組みのみ存在します。実運用の発注ロジック（kabu ステーション API の送信、再送制御、約定受信処理）や戦略実装はここに追加します。
- CI / デプロイ時に .env を適切に管理し、秘匿情報はシークレットストアで管理してください。
- DuckDB をファイルで運用する場合はバックアップ／排他制御（並行接続）に注意してください。大規模運用では永続 DB 構成の検討が必要です。

---

追加したいセクションや、実行スクリプト（CLI）/サンプル Notebook などがあれば、README を拡張して具体的な運用手順や例を追記します。必要であれば `.env.example` のテンプレートや初期化用スクリプトのサンプルも作成できます。