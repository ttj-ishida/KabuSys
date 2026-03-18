# KabuSys

日本株向けの自動売買／データ基盤ライブラリです。J-Quants や RSS を用いたデータ収集、DuckDB によるスキーマ管理、ETL パイプライン、データ品質チェック、監査ログなど、量的投資の基盤処理を包括的に提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は以下の用途を想定したライブラリです。

- J-Quants API からの株価日足・財務データ・JPX カレンダーの取得
- RSS フィードからのニュース記事収集と銘柄紐付け
- DuckDB を用いた三層データレイヤ（Raw / Processed / Feature）と実行層（Execution）
- 日次 ETL パイプライン（差分取得、バックフィル、品質チェック）
- 監査ログ（シグナル→発注→約定のトレーサビリティ）用スキーマ
- レート制限・リトライ・トークン自動リフレッシュ等の堅牢な API 呼び出し処理

設計方針として、冪等性（ON CONFLICT を用いた INSERT/UPDATE）、Look-ahead バイアス回避のための fetched_at 記録、SSRF や XML Bomb 対策などのセキュリティ・信頼性対策が組み込まれています。

---

## 主な機能一覧

- data/jquants_client.py
  - J-Quants API クライアント（レート制御、リトライ、トークン自動リフレッシュ）
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - DuckDB への保存関数（save_daily_quotes 等、冪等）

- data/news_collector.py
  - RSS フィード取得（gzip 対応、SSRF/プライベートホスト対策）
  - 記事正規化・ID 発行（URL 正規化＋SHA-256 部分）
  - raw_news / news_symbols への冪等保存

- data/schema.py
  - DuckDB のスキーマ定義（Raw / Processed / Feature / Execution）
  - init_schema(db_path) による初期化

- data/pipeline.py
  - 日次 ETL 実装（差分取得・バックフィル・品質チェック）
  - run_daily_etl() が主要エントリポイント

- data/calendar_management.py
  - 営業日判定、next/prev_trading_day、calendar_update_job（夜間ジョブ）

- data/quality.py
  - 欠損・スパイク・重複・日付不整合などデータ品質チェック

- data/audit.py
  - 監査ログ用テーブル（signal_events / order_requests / executions）初期化

- 設定管理: config.py
  - 環境変数の自動読み込み（.env / .env.local）、必須設定の取得、環境判定（development / paper_trading / live）

その他: strategy/, execution/, monitoring/ のプレースホルダ

---

## 前提条件

- Python 3.9+（型ヒントに Union | Optional を使用するため推奨）
- 必要なパッケージ（例）
  - duckdb
  - defusedxml
  - （標準ライブラリで完結する部分も多い）

パッケージはプロジェクトの pyproject.toml / requirements.txt に従ってインストールしてください。手元で開発する場合は editable install が便利です。

例:
```bash
pip install -e .
# または
pip install duckdb defusedxml
```

---

## セットアップ手順

1. リポジトリをクローン／配置

2. 環境変数の設定
   - プロジェクトルート（.git や pyproject.toml があるディレクトリ）に `.env` または `.env.local` を置くことで自動読み込みされます。
   - 自動ロードを無効にしたい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します（テスト等で使用）。

3. 必須環境変数（少なくとも以下を設定）
   - JQUANTS_REFRESH_TOKEN: J-Quants の refresh token（get_id_token 用）
   - KABU_API_PASSWORD: kabuステーション API パスワード（実行層で利用）
   - SLACK_BOT_TOKEN: Slack 通知用トークン（必要な場合）
   - SLACK_CHANNEL_ID: Slack 通知先チャンネルID
   - オプション:
     - KABUSYS_ENV: development / paper_trading / live（デフォルト development）
     - LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL
     - KABUSYS_DISABLE_AUTO_ENV_LOAD: 1 で自動 .env 読み込みを無効化
     - KABU_API_BASE_URL: kabu API のベース URL（デフォルト http://localhost:18080/kabusapi）
     - DUCKDB_PATH / SQLITE_PATH: DB 保存先パス（デフォルト data/kabusys.duckdb, data/monitoring.db）

4. DuckDB スキーマ初期化
   - data/schema.init_schema(db_path) を呼んでファイルを作成します（親ディレクトリ自動作成）。

例（Python スクリプト）:
```python
from kabusys.data import schema
from kabusys.config import settings

conn = schema.init_schema(settings.duckdb_path)
```

---

## 使い方（主要な API と実行例）

以下は代表的な利用例です。実環境での運用ではログ設定、例外ハンドリング、スケジューリングを適切に行ってください。

- J-Quants トークン取得
```python
from kabusys.data.jquants_client import get_id_token
token = get_id_token()  # settings.jquants_refresh_token を使用して ID トークンを取得
```

- DuckDB の初期化（1回だけ実行）
```python
from kabusys.data import schema
from kabusys.config import settings

conn = schema.init_schema(settings.duckdb_path)
```

- 日次 ETL の実行
```python
from kabusys.data.pipeline import run_daily_etl
from kabusys.data.schema import get_connection
from kabusys.config import settings
from datetime import date

conn = get_connection(settings.duckdb_path)
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- RSS ニュース収集ジョブ（既知銘柄セットを渡して銘柄紐付け）
```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
known_codes = {"7203", "6758", "9984"}  # 例: 有効な銘柄コードセット
res = run_news_collection(conn, known_codes=known_codes)
print(res)  # {source_name: saved_count}
```

- カレンダー夜間更新ジョブ（cron 等で定期実行）
```python
from kabusys.data.calendar_management import calendar_update_job
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
saved = calendar_update_job(conn)
print("saved:", saved)
```

- 監査ログスキーマの初期化（監査専用 DB を作る）
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
```

---

## 環境変数一覧（主なもの）

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL (任意、デフォルト: http://localhost:18080/kabusapi)
- SLACK_BOT_TOKEN (必須)
- SLACK_CHANNEL_ID (必須)
- DUCKDB_PATH (任意、デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (任意、デフォルト: data/monitoring.db)
- KABUSYS_ENV (development / paper_trading / live、デフォルト development)
- LOG_LEVEL (DEBUG/INFO/WARNING/ERROR/CRITICAL、デフォルト INFO)
- KABUSYS_DISABLE_AUTO_ENV_LOAD (1 を設定すると .env 自動読み込みを無効化)

config.Settings クラスから簡単にアクセスできます:
```python
from kabusys.config import settings
print(settings.jquants_refresh_token)
```

---

## ディレクトリ構成

リポジトリの主要ファイル／ディレクトリは以下のとおりです（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                     : 環境変数・設定管理
  - data/
    - __init__.py
    - jquants_client.py            : J-Quants API クライアント（取得・保存）
    - news_collector.py            : RSS ニュース収集・保存・銘柄抽出
    - schema.py                    : DuckDB スキーマ定義と初期化
    - pipeline.py                  : ETL パイプライン（run_daily_etl など）
    - calendar_management.py       : 市場カレンダー管理（営業日判断／更新）
    - audit.py                     : 監査ログ（signal/order/execution）スキーマ
    - quality.py                   : データ品質チェック
  - strategy/                      : 戦略関連モジュール（プレースホルダ）
  - execution/                     : 発注・約定周り（プレースホルダ）
  - monitoring/                    : 監視／メトリクス（プレースホルダ）

主要な DuckDB テーブル（schema.py に定義）
- Raw: raw_prices, raw_financials, raw_news, raw_executions
- Processed: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
- Feature: features, ai_scores
- Execution: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
- Audit: signal_events, order_requests, executions

---

## 運用・開発上の注意

- API レート制御: J-Quants は 120 req/min を仮定しており、jquants_client は内部でスロットリングを実装しています。
- リトライ: ネットワーク/サーバエラーに対して指数バックオフで複数回リトライします。401 はトークン自動リフレッシュを行い一度だけリトライします。
- セキュリティ:
  - RSS の XML パースに defusedxml を使用し XML 攻撃対策。
  - RSS フェッチ時はリダイレクト先のスキーム・ホストを検証しプライベートアドレスへのアクセスを防止します（SSRF 対策）。
  - URL の正規化でトラッキングパラメータを除去して記事 ID を生成します。
- 品質チェック: ETL 後に quality.run_all_checks() を呼び、検出結果に基づいてアラートや手動介入を行うことを推奨します。
- トランザクション: news_collector は大きなバルク挿入をトランザクションでまとめて行います。失敗時はロールバックされます。
- テスト: config の自動 .env 読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD により無効化可能。HTTP 呼び出し箇所はモックしやすい設計（_urlopen など）になっています。

---

## 参考・さらなる拡張

- strategy/ と execution/ はプレースホルダとして用意されています。戦略ロジック（シグナル生成）やブローカ接続（kabuステーション API 経由の実注文）をここに実装してください。
- Slack 通知や監視（monitoring）は実運用で重要です。SLACK_TOKEN 等を用いた通知処理を追加すると運用性が向上します。
- ai_scores / features テーブルは将来的な機械学習モデル出力の格納用です。

---

質問や、README に追加したいサンプル（例: docker-compose、CI / デプロイ手順、より詳細な .env.example）などがあれば教えてください。必要に応じて README を拡張します。