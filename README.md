# KabuSys

日本株向けの自動売買プラットフォーム用ライブラリ（KabuSys）。  
データ収集（J-Quants / RSS）、ETL、データ品質チェック、監査ログなどを備えた基盤コンポーネント群を提供します。

---

## 概要

KabuSys は以下の目的を持つモジュール群です。

- J-Quants API からの時系列・財務データ取得（レート制限・リトライ・トークン自動リフレッシュ対応）
- RSS フィードからのニュース収集（SSRF対策、XMLセーフパース、トラッキングパラメータ除去）
- DuckDB を用いたスキーマ定義・永続化（Raw / Processed / Feature / Execution / Audit 層）
- ETL パイプライン（差分更新・バックフィル・品質チェック）
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログ（シグナル→発注→約定のトレーサビリティ）

設計上のポイント：
- APIレート制御（J-Quants: 120 req/min）と指数バックオフ付きリトライを組み込み
- データ取得時に fetched_at を記録して Look-ahead バイアスを防止
- DuckDB への保存は冪等（ON CONFLICT）で上書き/排除
- RSSはデータサイズ制限・リダイレクト/プライベートアドレス検査により安全性を確保

---

## 主な機能一覧

- データ取得
  - jquants_client.fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - トークン取得 get_id_token（リフレッシュトークン→IDトークン）
- データ保存
  - jquants_client.save_daily_quotes / save_financial_statements / save_market_calendar
  - news_collector.save_raw_news / save_news_symbols
- RSS ニュース収集
  - fetch_rss（gzip、XMLパース安全化、URL正規化、記事ID生成）
  - extract_stock_codes（テキスト中の4桁銘柄コード抽出）
- DuckDB スキーマ管理
  - data.schema.init_schema(db_path) — 全テーブル作成（冪等）
  - data.schema.get_connection(db_path)
  - data.audit.init_audit_schema(conn) / init_audit_db(db_path)
- ETL / パイプライン
  - data.pipeline.run_daily_etl(conn, target_date=..., ...) — 日次ETL（カレンダー→株価→財務→品質チェック）
  - run_prices_etl / run_financials_etl / run_calendar_etl（個別ジョブ）
- 品質チェック
  - data.quality.run_all_checks / check_missing_data / check_spike / check_duplicates / check_date_consistency

---

## 前提・依存関係

推奨 Python バージョン: 3.10+（コードの型注釈や union 型表記に依存）  
主な外部依存パッケージ（インストールしてください）:
- duckdb
- defusedxml

（プロジェクトに pyproject.toml / requirements.txt があればそちらを参照してください）

---

## 環境変数・設定

設定は環境変数またはプロジェクトルートの `.env` / `.env.local` ファイルから自動読み込みされます（ただし `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定すると自動読み込みを無効化できます）。

主に使用する環境変数：

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須) — kabuステーション API 用パスワード
- KABU_API_BASE_URL (任意) — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須) — Slack 通知用 Bot トークン（必要な場合）
- SLACK_CHANNEL_ID (必須) — Slack チャネル ID
- DUCKDB_PATH (任意) — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH (任意) — 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV (任意) — 実行環境: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL (任意) — ログレベル: DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）

Settings オブジェクトからコード内で簡単に参照できます：
from kabusys.config import settings
settings.jquants_refresh_token
settings.duckdb_path

環境値が不足していると Settings のプロパティで ValueError が発生します。

---

## セットアップ手順（ローカル開発向け）

1. リポジトリをクローン
   - git clone <repo-url>

2. Python 仮想環境を用意してアクティベート
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - pip install duckdb defusedxml
   - （プロジェクトに pyproject/requirements があればそれを使用）

4. 環境変数を設定
   - プロジェクトルートに `.env` を作成するか、環境変数をエクスポート
   - 例（.env）:
     JQUANTS_REFRESH_TOKEN=your_refresh_token
     KABU_API_PASSWORD=your_kabu_password
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567
     DUCKDB_PATH=data/kabusys.duckdb
     KABUSYS_ENV=development

   ※自動読み込みはプロジェクトルート（.git または pyproject.toml がある階層）を基準に行われます。

5. DuckDB スキーマを初期化
   - Python スクリプトや REPL で:
     from kabusys.data import schema
     conn = schema.init_schema("data/kabusys.duckdb")

6. 監査ログスキーマ（必要に応じて）
   - from kabusys.data import audit
     conn = schema.get_connection("data/kabusys.duckdb")
     audit.init_audit_schema(conn)
   - または独立DBに: audit.init_audit_db("data/kabusys_audit.duckdb")

---

## 使い方（例）

以下は典型的なワークフロー例です。

1) DB 初期化 + 日次 ETL 実行

```python
from datetime import date
from kabusys.data import schema, pipeline

# DuckDB 初期化（既に存在すればスキップ）
conn = schema.init_schema("data/kabusys.duckdb")

# 日次 ETL（今日分を処理）
result = pipeline.run_daily_etl(conn)
print(result.to_dict())
```

2) ニュース収集ジョブ（RSS -> raw_news）

```python
import duckdb
from kabusys.data import news_collector

conn = duckdb.connect("data/kabusys.duckdb")

# 既定のRSSソースを使用して収集
stats = news_collector.run_news_collection(conn, known_codes={"7203", "6758"})
print(stats)  # {source_name: 新規保存件数}
```

3) J-Quants から日足を直接取得して保存

```python
from kabusys.data import jquants_client as jq
import duckdb
from datetime import date

conn = duckdb.connect("data/kabusys.duckdb")
records = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,3,31))
saved = jq.save_daily_quotes(conn, records)
print(f"保存件数: {saved}")
```

4) 監査ログ追加（例: init audit tables）
```python
from kabusys.data import schema, audit
conn = schema.get_connection("data/kabusys.duckdb")
audit.init_audit_schema(conn)
```

---

## 主要API（抜粋）

- data.schema.init_schema(db_path) -> DuckDB 接続（テーブル作成）
- data.schema.get_connection(db_path) -> DuckDB 接続（スキーマ初期化は行わない）
- data.audit.init_audit_db(db_path) / init_audit_schema(conn)
- data.pipeline.run_daily_etl(conn, target_date=None, id_token=None, run_quality_checks=True, ...)
- data.jquants_client.get_id_token(refresh_token=None)
- data.jquants_client.fetch_daily_quotes(...)
- data.jquants_client.save_daily_quotes(conn, records)
- data.news_collector.fetch_rss(url, source, timeout=30)
- data.news_collector.save_raw_news(conn, articles)
- data.news_collector.run_news_collection(conn, sources=None, known_codes=None)

---

## 注意点 / トラブルシューティング

- J-Quants API のレート制限は 120 req/min に遵守しています。大量API呼び出しは時間がかかる場合があります。
- get_id_token はリフレッシュトークンを元に ID トークンを取得します。401 を受けた際は自動的にリフレッシュして 1 回リトライします。
- .env 自動読み込みはプロジェクトルート（.git または pyproject.toml）を基準に行います。テスト等で無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB のファイルパスはデフォルトで data/kabusys.duckdb。ファイルの所有権やアクセス権に注意してください。
- news_collector は RSS のリダイレクト先やホストがプライベートアドレスである場合、取得を拒否します（SSRF 対策）。
- data.quality のチェックは Fail-Fast ではなく、検出された問題を一覧で返します。ETL の停止判定などは呼び出し側で行ってください。
- Python のバージョンや依存パッケージが不足していると実行時エラーになります。エラーメッセージに従って必要パッケージを追加してください。

---

## ディレクトリ構成

（主要ファイルのみ抜粋）

- src/
  - kabusys/
    - __init__.py
    - config.py                   — 環境設定・自動 .env 読み込み
    - data/
      - __init__.py
      - jquants_client.py         — J-Quants API クライアント（取得・保存）
      - news_collector.py         — RSS ニュース収集・保存
      - pipeline.py               — ETL パイプライン（差分更新・バックフィル・品質チェック）
      - schema.py                 — DuckDB スキーマ定義・初期化
      - audit.py                  — 監査ログスキーマ / 初期化
      - quality.py                — データ品質チェック
    - strategy/
      - __init__.py
    - execution/
      - __init__.py
    - monitoring/
      - __init__.py

---

## ライセンス・貢献

（ここにライセンス情報やコントリビュートの手順を記載してください）

---

README で不明点や追加したい利用例（Slack通知、kabuステーション発注連携、CIジョブの書き方など）があれば教えてください。必要に応じてサンプルスクリプトや systemd / cron 用の実行例も作成します。