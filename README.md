# KabuSys

日本株向けの自動売買基盤ライブラリ（KabuSys）のリポジトリ向け README。  
この README はコードベースの実装に基づき、セットアップ方法・主要機能・使い方（簡単な例）・ディレクトリ構成を日本語でまとめたものです。

## プロジェクト概要

KabuSys は日本株の自動売買プラットフォームに必要なデータ取得・ETL・品質チェック・監査ログ・ニュース収集などの基盤機能を提供する Python パッケージです。  
主に以下を扱います。

- J-Quants API からの株価・財務・市場カレンダー取得（レート制限・リトライ・トークン自動リフレッシュ対応）
- RSS ベースのニュース収集（SSRF・XML攻撃対策・トラッキング除去・銘柄抽出）
- DuckDB によるデータスキーマ・初期化・保存（Raw / Processed / Feature / Execution / Audit 層）
- ETL パイプライン（差分更新・バックフィル・品質チェック）
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログ（シグナル→発注→約定までのトレース）

設計上、データの冪等性やトレーサビリティ、セキュリティ（SSRF・XML Bomb 等）を重視しています。

## 主な機能一覧

- data/jquants_client.py
  - J-Quants API クライアント
  - レート制限（120 req/min）・指数バックオフリトライ・401時のトークン自動リフレッシュ
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - DuckDB への冪等保存関数（save_daily_quotes 等）
- data/news_collector.py
  - RSS 取得、前処理（URL除去、空白正規化）、記事ID(sha256先頭32文字)生成
  - defusedxml を用いた安全な XML パース、SSRF 対策、受信サイズ制限
  - raw_news への冪等保存、news_symbols への銘柄紐付け
- data/schema.py
  - DuckDB のスキーマ定義（Raw / Processed / Feature / Execution 層）と初期化関数 init_schema()
- data/pipeline.py
  - 差分ETL（市場カレンダー → 株価 → 財務）および品質チェックを行う run_daily_etl()
  - バックフィルや営業日調整のロジックを含む
- data/calendar_management.py
  - market_calendar の管理、営業日判定・前後の営業日取得関数
- data/quality.py
  - 欠損・スパイク・重複・日付不整合チェックとまとめ実行 run_all_checks()
- data/audit.py
  - 監査ログ用のテーブル定義（signal_events / order_requests / executions）と初期化
- config.py
  - .env 読み込み（プロジェクトルート自動検出）、環境変数ラッパー settings
  - 必須キーの検査・デフォルト値・KABUSYS_ENV / LOG_LEVEL の検証

その他に strategy/, execution/, monitoring/ のエントリパッケージがあります（実装はこのスナップショットでは未展開）。

## セットアップ手順

前提
- Python 3.9 以上（コードは型ヒントに合わせてモダンな機能を使用）
- duckdb, defusedxml などの外部ライブラリが必要

1. リポジトリをクローンして作業ディレクトリに移動
   - git clone ... && cd <repo>

2. 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存パッケージをインストール
   - pip install duckdb defusedxml
   - （必要に応じて他ライブラリを追加してください）

   ※ requirements.txt がある場合は pip install -r requirements.txt を使用します。

4. 環境変数 / .env の設定
   - プロジェクトルート（.git または pyproject.toml のあるディレクトリ）に `.env` として必要変数を置くと自動で読み込まれます。
   - .env.local を作成すると .env を上書きできます（OS 環境変数は保護されます）。
   - 自動読み込みを無効にする場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

   主な必須環境変数（config.Settings に基づく）
   - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（必須）
   - KABU_API_PASSWORD : kabuステーション API のパスワード（必須）
   - SLACK_BOT_TOKEN : Slack 通知用 Bot トークン（必須）
   - SLACK_CHANNEL_ID : Slack チャンネル ID（必須）
   - （任意）KABUSYS_ENV : development / paper_trading / live （デフォルト: development）
   - （任意）LOG_LEVEL : DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）
   - （任意）DUCKDB_PATH : デフォルト data/kabusys.duckdb
   - （任意）SQLITE_PATH : デフォルト data/monitoring.db

5. データベース初期化（DuckDB）
   - Python スクリプトや REPL からスキーマを初期化します（下記「使い方」を参照）。

## 使い方（簡単なコード例）

以下は最も基本的な使い方の例です。Python スクリプトまたは対話環境で実行できます。

1. DuckDB スキーマ初期化（ファイル DB を作る）
```
from kabusys.data import schema

conn = schema.init_schema("data/kabusys.duckdb")
# conn は duckdb の接続。以後 conn を使って ETL / 保存 等を行う
```

2. 日次 ETL 実行（J-Quants から差分取得して保存・品質チェック）
```
from kabusys.data import pipeline
from kabusys.data import schema
from datetime import date

conn = schema.get_connection("data/kabusys.duckdb")  # 既存 DB への接続
result = pipeline.run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

3. ニュース収集ジョブの実行（RSS 取得 → raw_news 保存 → 銘柄紐付け）
```
from kabusys.data import news_collector, schema

conn = schema.get_connection("data/kabusys.duckdb")
known_codes = {"7203", "6758", "9984", ...}  # 有効な銘柄コードセット
results = news_collector.run_news_collection(conn, sources=None, known_codes=known_codes)
print(results)  # {source_name: saved_count}
```

4. 直接 J-Quants の株価を取得して保存
```
from kabusys.data import jquants_client as jq
from kabusys.data import schema
from datetime import date

conn = schema.get_connection("data/kabusys.duckdb")
records = jq.fetch_daily_quotes(code="7203", date_from=date(2024,1,1), date_to=date(2024,2,1))
saved = jq.save_daily_quotes(conn, records)
print(f"saved: {saved}")
```

注意点
- jquants_client は内部でトークンキャッシュおよび自動リフレッシュを行います。get_id_token() を直接呼ぶときは allow_refresh に注意してください（無限再帰防止）。
- news_collector は SSRF 対策としてリダイレクト先やホストのプライベートアドレス判定を行います。外部の URL を安全に取り扱います。

## ディレクトリ構成

主要ファイル・モジュールのツリー（抜粋）

- src/kabusys/
  - __init__.py
  - config.py
  - data/
    - __init__.py
    - jquants_client.py         — J-Quants API クライアント（取得・保存ロジック）
    - news_collector.py        — RSS ニュース収集・前処理・DB 保存
    - schema.py                — DuckDB スキーマ定義 & init_schema, get_connection
    - pipeline.py              — ETL パイプライン（run_daily_etl 等）
    - calendar_management.py   — 市場カレンダー管理・営業日判定
    - audit.py                 — 監査ログテーブル定義・初期化
    - quality.py               — データ品質チェック
  - strategy/
    - __init__.py              — 戦略層用パッケージ（実装は拡張）
  - execution/
    - __init__.py              — 発注/ブローカー連携層（実装は拡張）
  - monitoring/
    - __init__.py              — 監視・メトリクス・アラート（実装は拡張）

- pyproject.toml / setup.py 等（プロジェクトルートに存在する想定）

各モジュールは責務ごとに分離されており、DuckDB を中心に Raw→Processed→Feature→Execution の層を構築します。監査ログ（audit）テーブルは別途初期化でき、UTC タイムゾーン固定などトレーサビリティ要件に対応します。

## 運用上のポイント / 注意事項

- 環境変数管理:
  - 自動でプロジェクトルートの .env / .env.local を読み込みます（OS 環境変数は保護）。自動読み込みを無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
  - 必須キー未設定時は config.Settings のプロパティ呼び出しで ValueError が送出されます。

- レート制限・リトライ:
  - J-Quants は 120 req/min を想定。jquants_client は固定間隔のスロットリングと指数バックオフを実装しています。
  - HTTP 408/429/5xx 等はリトライ対象、401 はトークン自動更新の上で再試行されます（一回のみ）。

- セキュリティ:
  - news_collector は defusedxml を使用、受信サイズ制限、リダイレクト先の検査、トラッキングパラメータ除去などを実装しています。

- 冪等性:
  - DB 保存は ON CONFLICT DO UPDATE / DO NOTHING を利用し、再実行や重複挿入に耐えます。

## 開発・拡張

- strategy/ や execution/、monitoring/ はプラットフォーム固有の戦略実装やブローカー連携を追加するためのエントリポイントです。各層の API を参照し、テスト駆動で機能を追加してください。
- テスト時は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD を立てて自動 .env 読み込みを抑止し、明示的にモックやテスト用 DB を使用すると扱いやすくなります。

---

この README はソースコード（src/kabusys 以下）の現状実装に基づいた概要ガイドです。個別の API の詳細・パラメータや追加の運用手順は各モジュール（data/jquants_client.py, data/pipeline.py, data/news_collector.py など）のドキュメンテーションコメントを参照してください。必要なら、サンプルスクリプトや CI 用の設定例（cron/airflow など）も追記できます。