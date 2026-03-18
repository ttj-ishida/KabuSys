# KabuSys

日本株向け自動売買基盤ライブラリ "KabuSys" の README。  
本ドキュメントはプロジェクトの概要、機能、セットアップ手順、基本的な使い方、ディレクトリ構成を日本語でまとめたものです。

---

## プロジェクト概要

KabuSys は日本株の自動売買システム構築を支援するライブラリ群です。  
主に以下の役割を担います。

- J-Quants API からのマーケットデータ（株価日足、財務データ、JPX カレンダー）取得
- RSS ベースのニュース収集と記事→銘柄紐付け
- DuckDB を使ったデータスキーマ定義・初期化・ETL パイプライン
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログ（シグナル→発注→約定のトレーサビリティ）用スキーマ
- マーケットカレンダー管理（営業日判定 / 翌営業日などのユーティリティ）

設計上の特徴として、API レート制御・リトライ・冪等性（ON CONFLICT）・Look‑ahead bias 対策（fetched_at の記録）・セキュリティ対策（RSS 収集における SSRF 対策等）を重視しています。

---

## 主な機能一覧

- data/jquants_client.py
  - J-Quants API との通信（株価、財務、カレンダー）
  - レートリミット（120 req/min）制御、リトライ、401 時のトークン自動リフレッシュ
  - DuckDB への冪等保存関数（save_daily_quotes 等）
- data/pipeline.py
  - 日次 ETL（run_daily_etl）：カレンダー→株価→財務→品質チェック
  - 差分更新・バックフィル対応
- data/news_collector.py
  - RSS から記事取得、テキスト前処理、ID（正規化URL の SHA-256 部分）生成
  - SSRF 防止、gzip サイズ上限、防爆（defusedxml）などの安全策
  - raw_news / news_symbols への保存（バルク挿入・冪等）
- data/schema.py
  - DuckDB 用スキーマ定義（Raw / Processed / Feature / Execution 層）
  - init_schema() でテーブル・インデックス作成
- data/calendar_management.py
  - 営業日判定 / next_trading_day / prev_trading_day / get_trading_days
  - calendar_update_job による夜間カレンダー差分更新
- data/quality.py
  - 欠損、スパイク、重複、日付不整合などの品質チェック（run_all_checks）
- data/audit.py
  - 監査ログ用スキーマ（signal_events / order_requests / executions）
  - init_audit_db / init_audit_schema による監査DB初期化

（strategy, execution, monitoring はパッケージプレースホルダとして存在）

---

## 必要条件 / セットアップ

- Python: 3.10 以上（型ヒントに PEP 604（|）等を使用）
- 依存パッケージ（最低限）:
  - duckdb
  - defusedxml

推奨: 仮想環境を使うこと。

例（Unix/macOS）:

```bash
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install duckdb defusedxml
# 開発中であればパッケージを編集可能にインストール
pip install -e .
```

※ requirements.txt や pyproject.toml がある場合はそちらに従ってください。

### 環境変数 / .env

設定は環境変数またはプロジェクトルートの `.env` / `.env.local` から読み込まれます。自動ロードは以下の優先順です:

OS 環境変数 > .env.local > .env

自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します（主にテスト用途）。

主な必須環境変数（例）:

- JQUANTS_REFRESH_TOKEN  — J-Quants リフレッシュトークン（必須）
- KABU_API_PASSWORD      — kabuステーション API 用パスワード（必須）
- SLACK_BOT_TOKEN        — Slack 通知用 Bot トークン（必須）
- SLACK_CHANNEL_ID       — 通知先チャンネル ID（必須）

任意／デフォルト値:

- KABUSYS_ENV            — {development, paper_trading, live}（デフォルト: development）
- LOG_LEVEL              — {DEBUG, INFO, WARNING, ERROR, CRITICAL}（デフォルト: INFO）
- DUCKDB_PATH            — DuckDB ファイル（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH            — 監視用 SQLite（デフォルト: data/monitoring.db）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 自動 .env ロード無効化用フラグ

サンプル .env:

```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
KABUSYS_ENV=development
LOG_LEVEL=INFO
DUCKDB_PATH=data/kabusys.duckdb
```

---

## 基本的な使い方

以下は Python スクリプトからの基本操作例です。実行前に依存ライブラリと環境変数を設定してください。

- DuckDB スキーマ初期化

```python
from kabusys.data import schema

# ファイル DB に初期化（親ディレクトリがなければ自動作成）
conn = schema.init_schema("data/kabusys.duckdb")
# またはインメモリ:
# conn = schema.init_schema(":memory:")
```

- 監査ログ用 DB 初期化（監査専用 DB）

```python
from kabusys.data import audit

audit_conn = audit.init_audit_db("data/kabusys_audit.duckdb")
```

- 日次 ETL の実行

```python
from kabusys.data import pipeline
from kabusys.data import schema
from datetime import date

conn = schema.get_connection("data/kabusys.duckdb")  # 既存DBへ接続
# ETL を実行（target_date を省略すると今日）
result = pipeline.run_daily_etl(conn)
print(result.to_dict())
```

- 単体 ETL ジョブ（価格 / 財務 / カレンダー）の呼び出しにも対応:

```python
from kabusys.data import pipeline
from kabusys.data import schema
from datetime import date

conn = schema.get_connection("data/kabusys.duckdb")
today = date.today()

# カレンダー更新
pipeline.run_calendar_etl(conn, today)

# 株価差分ETL
pipeline.run_prices_etl(conn, today)

# 財務差分ETL
pipeline.run_financials_etl(conn, today)
```

- ニュース収集ジョブ（RSS）

```python
from kabusys.data import news_collector
from kabusys.data import schema

conn = schema.get_connection("data/kabusys.duckdb")

# sources: {source_name: rss_url} の dict を渡せる（省略時は既定のソースを使用）
results = news_collector.run_news_collection(conn, sources=None, known_codes={"7203", "6758"})
print(results)  # 各 source ごとの新規保存件数
```

- カレンダー夜間バッチジョブ

```python
from kabusys.data.calendar_management import calendar_update_job
from kabusys.data import schema

conn = schema.get_connection("data/kabusys.duckdb")
saved = calendar_update_job(conn)
print(f"saved {saved} records")
```

注意点:
- J-Quants へアクセスする際は rate limit（120 req/min）や API レスポンスの HTTP エラーに対して自動 retry が実装されています。
- save_* 系関数は ON CONFLICT による冪等保存を行います。
- run_daily_etl は内部で品質チェック（data.quality.run_all_checks）を呼び出します。品質問題は ETLResult.quality_issues に格納されます。

---

## 環境変数バリデーション

- KABUSYS_ENV は "development", "paper_trading", "live" のいずれか
- LOG_LEVEL は "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"
- 必須の環境変数が不足する場合は起動時に ValueError が発生します（settings オブジェクト経由で取得）

---

## セキュリティと耐障害性の設計メモ

- jquants_client:
  - レート制御（固定間隔スロットリング）
  - リトライ（指数バックオフ、最大 3 回）
  - 401 の場合は refresh_token で id_token を再取得して 1 回リトライ
  - fetched_at を UTC で記録し Look‑ahead bias を抑制
- news_collector:
  - defusedxml による XML パース（XML Bomb 等対策）
  - リダイレクト先のスキーム / ホスト検証（SSRF 対策）
  - レスポンスサイズ上限（10MB）・gzip 解凍後も検査（Gzip bomb 対策）
  - トラッキングパラメータ除去・URL 正規化・SHA-256 による記事 ID 生成

---

## ディレクトリ構成

ソースは `src/kabusys` 配下にあります。主要ファイルは以下のとおりです。

- src/
  - kabusys/
    - __init__.py
    - config.py                — 環境変数 / 設定管理（settings）
    - data/
      - __init__.py
      - jquants_client.py      — J-Quants API クライアント（fetch/save）
      - news_collector.py      — RSS ニュース収集・保存
      - schema.py              — DuckDB スキーマ定義 & init_schema()
      - pipeline.py            — ETL パイプライン（run_daily_etl 等）
      - calendar_management.py — マーケットカレンダー管理
      - audit.py               — 監査ログスキーマ初期化
      - quality.py             — データ品質チェック
    - strategy/
      - __init__.py            — 戦略モジュール（プレースホルダ）
    - execution/
      - __init__.py            — 発注/ブローカー連携（プレースホルダ）
    - monitoring/
      - __init__.py            — 監視用モジュール（プレースホルダ）

---

## 開発 / 貢献メモ

- type hints / 型安全を重視しています。Python 3.10+ を前提にしています。
- DB スキーマやクエリは DuckDB を前提に最適化されています。
- ユニット/統合テストを追加する際は、環境変数自動ロードを無効化する `KABUSYS_DISABLE_AUTO_ENV_LOAD` を使うと良いです。

---

## 参考・問い合わせ

- コード中の docstring・コメントに挙げられた設計原則や DataPlatform.md 等の参照先（本リポジトリ外文書）が実装の意図を説明しています。  
- 実運用での kabu ステーションやブローカー連携、Slack 通知等は本 README に記載の外部設定が必要です。実環境での運用前に sandbox / paper_trading モードで十分に検証してください。

---

以上。必要であれば README に含める具体的なサンプルコマンド（systemd / cron ジョブ例、Dockerfile など）を追加で作成します。どの部分を優先して補足しますか？