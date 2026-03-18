# KabuSys

日本株向けの自動売買基盤ライブラリ（KabuSys）。  
データ取得・ETL、ニュース収集、マーケットカレンダー管理、データ品質チェック、監査ログ（発注〜約定のトレーサビリティ）など、戦略・実行レイヤーの基盤機能を提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は日本株の自動売買システムを構築するための基盤コンポーネント群を含む Python パッケージです。主に以下を提供します。

- J-Quants API を用いた株価日足・財務・カレンダーの取得（レート制御、リトライ、トークン自動更新、fetched_at 記録）
- DuckDB ベースのスキーマ定義と初期化（Raw / Processed / Feature / Execution 層）
- ETL パイプライン（日次差分更新、バックフィル、品質チェック）
- RSS ベースのニュース収集・前処理・DB 保存（SSRF / XML 攻撃対策、トラッキング除去）
- マーケットカレンダー管理（営業日判定・next/prev 営業日取得・夜間更新ジョブ）
- 監査ログ（signal → order_request → executions のトレースを担保するテーブル群）
- データ品質チェックモジュール（欠損・重複・スパイク・日付不整合検出）

---

## 主な機能一覧

- data.jquants_client
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - save_daily_quotes / save_financial_statements / save_market_calendar
  - レートリミット・再試行・401 自動リフレッシュ・fetched_at 記録・DuckDB への冪等保存
- data.schema
  - DuckDB 用スキーマ定義（多層構造）と init_schema / get_connection
- data.pipeline
  - run_daily_etl（カレンダー→株価→財務→品質チェックの一括実行）
  - run_prices_etl / run_financials_etl / run_calendar_etl（差分処理）
- data.news_collector
  - RSS 取得 / 前処理 / raw_news 保存 / 銘柄紐付け
  - SSRF 対策・XML 攻撃対策・サイズ制限・トラッキング除去
- data.calendar_management
  - is_trading_day / next_trading_day / prev_trading_day / get_trading_days
  - calendar_update_job（夜間差分更新）
- data.audit
  - 監査ログ用テーブル群・インデックスと初期化ユーティリティ
- data.quality
  - check_missing_data / check_duplicates / check_spike / check_date_consistency / run_all_checks

（strategy / execution / monitoring パッケージ用のプレースホルダを含みます）

---

## 動作環境・依存

- Python 3.10 以上（typing の | 演算子等を使用）
- 必要パッケージ（最低限）
  - duckdb
  - defusedxml
- 標準ライブラリの urllib 等を利用

プロジェクトに pyproject.toml / requirements.txt がある場合はそれに従ってください。なければ手動でインストールしてください。

例：
pip install duckdb defusedxml

---

## セットアップ手順

1. リポジトリをクローン / ソースを配置
2. 仮想環境を作成して有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 依存パッケージをインストール
   - pip install duckdb defusedxml
4. 環境変数を設定
   - 推奨はプロジェクトルートに .env ファイルを用意すること。config モジュールは自動的にプロジェクトルート（.git または pyproject.toml があるディレクトリ）から `.env` と `.env.local` を読み込みます。
   - 自動ロードを無効化する場合:
     - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定

必須の環境変数:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API パスワード
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID — Slack チャンネル ID

任意（デフォルトあり）:
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- KABUSYS_ENV — environment: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL — DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）

注: config.Settings は足りない必須環境変数があると ValueError を投げます。

---

## スキーマ初期化

DuckDB スキーマを初期化して接続を得る例:

from pathlib import Path
import kabusys.data.schema as schema

db_path = Path("data/kabusys.duckdb")
conn = schema.init_schema(db_path)  # ファイルがなければ親ディレクトリを作成して初期化

監査ログ専用 DB を別で使う場合:

from pathlib import Path
from kabusys.data import audit

audit_db = Path("data/audit.duckdb")
audit_conn = audit.init_audit_db(audit_db)

---

## 使い方（代表的な例）

以下は Python プログラムから主要機能を使う簡単な例です。

1) 日次 ETL を実行する（J-Quants から差分取得して保存・品質チェック）:

from datetime import date
from kabusys.data import schema, pipeline

conn = schema.get_connection("data/kabusys.duckdb")  # 既に init_schema 済みを想定
result = pipeline.run_daily_etl(conn, target_date=date.today())
print(result.to_dict())

2) News Collection（RSS 取得 → raw_news 保存 → 銘柄紐付け）:

from kabusys.data import schema, news_collector

conn = schema.get_connection("data/kabusys.duckdb")
known_codes = {"7203", "6758", "9984"}  # 例: 有効銘柄コードセット
results = news_collector.run_news_collection(conn, known_codes=known_codes)
print(results)  # {source_name: 新規保存数}

3) カレンダー夜間更新ジョブ:

from kabusys.data import schema, calendar_management

conn = schema.get_connection("data/kabusys.duckdb")
saved = calendar_management.calendar_update_job(conn)
print("saved:", saved)

4) J-Quants から株価を直接取得して保存:

from kabusys.data import jquants_client as jq
from kabusys.data import schema

conn = schema.get_connection("data/kabusys.duckdb")
records = jq.fetch_daily_quotes(code="7203", date_from=date(2024,1,1), date_to=date(2024,3,31))
saved = jq.save_daily_quotes(conn, records)
print("fetched:", len(records), "saved:", saved)

注意: get_id_token() は settings.jquants_refresh_token を使って ID トークンを取得します。fetch_* 系はデフォルトでトークンキャッシュを利用し、401 時は自動リフレッシュします。

---

## 開発・デバッグのヒント

- .env 自動読み込み
  - プロジェクトルート（.git または pyproject.toml がある場所）にある `.env` と `.env.local` を自動的に読み込みます。
  - 読み込み順: OS 環境 > .env.local > .env
  - 自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト時に便利）。

- ロギングレベルは LOG_LEVEL で指定できます（デフォルト INFO）。

- DuckDB へは冪等に保存される（INSERT ... ON CONFLICT DO UPDATE / DO NOTHING）ため、再実行で重複が起きにくい設計です。ただし、外部から直接 DB を操作した場合は data.quality のチェックを実行して異常を検知してください。

- テスト時は id_token の注入が可能（pipeline の引数に id_token を渡す）なので、外部 API をモックして単体テストを行えます。

---

## ディレクトリ構成

src/kabusys/
- __init__.py
- config.py                          — 環境変数 / 設定管理 (.env 自動ロード)
- data/
  - __init__.py
  - jquants_client.py                 — J-Quants API クライアント（取得・保存）
  - news_collector.py                 — RSS ニュース収集・保存・銘柄抽出
  - schema.py                         — DuckDB スキーマ定義・初期化
  - pipeline.py                       — ETL パイプライン（差分更新・品質チェック）
  - calendar_management.py            — カレンダー管理・営業日ロジック・更新ジョブ
  - audit.py                          — 監査ログ（signal / order_request / executions）
  - quality.py                        — データ品質チェック
- strategy/
  - __init__.py                       — 戦略実装用パッケージ（拡張ポイント）
- execution/
  - __init__.py                       — 発注実行用パッケージ（拡張ポイント）
- monitoring/
  - __init__.py                       — 監視 / メトリクス用（拡張ポイント）

その他:
- data/ (デフォルトの DB 保存先ディレクトリ：DUCKDB_PATH 等で変更可能)

---

## 注意事項 / セキュリティ

- news_collector は SSRF 対策（リダイレクト時の検査、プライベート IP 拒否）、XML パース時の defusedxml 使用、受信サイズ制限を備えています。外部 URL 取得に伴うリスクを低減していますが、運用時にネットワークアクセス権限やプロキシ設定なども見直してください。
- 全てのタイムスタンプは UTC で取り扱う設計です（監査 DB 初期化時に TimeZone を UTC にセットします）。
- J-Quants のトークン・kabu API のパスワードなどは必ず安全に保管してください。`.env` を使う場合はリポジトリに含めないでください。

---

## ライセンス・貢献

本リポジトリのライセンス・コントリビュート方針はプロジェクトルートの LICENSE / CONTRIBUTING を参照してください（存在する場合）。

---

README に記載したサンプルはあくまで利用例です。実際の運用ではバックテスト・ペーパー取引による検証を十分に行い、live 環境では十分な安全策（リスク管理・モニタリング・アラート）を実装してください。