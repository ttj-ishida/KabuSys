# KabuSys

日本株向けの自動売買プラットフォーム（ライブラリ）。  
データ収集（J-Quants / RSS）、ETLパイプライン、データ品質チェック、マーケットカレンダー管理、監査ログ用スキーマなどを提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株の自動売買インフラ向けに設計された Python パッケージです。主な目的は以下です。

- J-Quants API から株価・財務・カレンダー情報を安全かつ効率的に取得・保存する
- RSS フィードからニュースを収集し、記事と銘柄コードの紐付けを行う
- DuckDB を利用した三層データレイヤ（Raw / Processed / Feature）および実行・監査テーブルを定義・初期化する
- 日次 ETL パイプライン（差分取得・バックフィル・品質チェック）を提供する
- マーケットカレンダー判定（営業日・SQ日など）や夜間更新ジョブを提供する

設計上のポイント:
- レート制限（J-Quants: 120 req/min）の順守
- 冪等性（ON CONFLICT DO UPDATE / DO NOTHING）による安全な保存
- リトライ・トークン自動リフレッシュ
- SSRF や XML インジェクション対策（defusedxml、URL検証など）
- DuckDB による軽量で高速なストレージ

---

## 機能一覧

- data.jquants_client
  - J-Quants API クライアント（株価日足、財務データ、マーケットカレンダー）
  - レートリミッティング、リトライ、トークン自動更新、ページネーション対応
  - DuckDB への冪等保存関数（save_daily_quotes 等）
- data.news_collector
  - RSS 取得、XML パース（defusedxml）、前処理、ID生成（SHA-256 ハッシュ）
  - SSRF 対策、応答サイズ制限、DuckDB への一括保存（INSERT ... RETURNING）
  - 記事と銘柄コードの紐付け保存
- data.schema
  - DuckDB のスキーマ定義（Raw / Processed / Feature / Execution / Audit）
  - init_schema / get_connection による初期化・接続
- data.pipeline
  - 差分ETL（株価・財務・カレンダー）と日次パイプライン run_daily_etl
  - 品質チェック（quality モジュール）との統合
- data.calendar_management
  - is_trading_day / next_trading_day / prev_trading_day / get_trading_days
  - calendar_update_job による夜間カレンダー更新
- data.quality
  - 欠損、重複、スパイク、日付不整合のチェック
  - QualityIssue オブジェクトで問題を報告
- data.audit
  - 監査ログ用テーブル（signal_events / order_requests / executions）と初期化関数

その他:
- 環境変数管理（kabusys.config）: .env / .env.local の自動ロード（無効化可能）

---

## セットアップ手順

前提: Python 3.9+（型アノテーションや union の記法から推奨）

1. リポジトリクローン（例）
   - git clone <repo-url>
2. 仮想環境作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 依存パッケージインストール（最低限）
   - pip install duckdb defusedxml
   - またはパッケージを editable インストール:
     - pip install -e .

注意: 実際に配布するパッケージでは requirements.txt / pyproject.toml を用意して依存を固定してください。

環境変数 (.env) の自動読み込み:
- パッケージはプロジェクトルート（.git または pyproject.toml を探索）にある `.env` / `.env.local` を自動で読み込みます（OS 環境変数が優先）。
- 自動ロードを無効化する場合:
  - 環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定

必須環境変数（例）
- JQUANTS_REFRESH_TOKEN = <J-Quants リフレッシュトークン>
- KABU_API_PASSWORD = <kabuステーション API パスワード>
- SLACK_BOT_TOKEN = <Slack ボットトークン>
- SLACK_CHANNEL_ID = <通知先チャンネルID>

任意 / デフォルト
- KABUSYS_ENV = development | paper_trading | live  (デフォルト: development)
- LOG_LEVEL = DEBUG|INFO|WARNING|ERROR|CRITICAL (デフォルト: INFO)
- KABUSYS_DISABLE_AUTO_ENV_LOAD = 1 で .env 自動読み込みを停止
- KABUSYS 用 DB パス:
  - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
  - SQLITE_PATH (デフォルト: data/monitoring.db)

例: .env（プロジェクトルート）
JQUANTS_REFRESH_TOKEN=your_refresh_token
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C0123456789
KABUSYS_ENV=development
LOG_LEVEL=INFO
DUCKDB_PATH=data/kabusys.duckdb

---

## 使い方

以下は代表的な API の使い方（簡易例）。実際はログ設定や例外処理を追加してください。

1) DuckDB スキーマ初期化
- Python REPL やスクリプトで:
  from kabusys.data.schema import init_schema
  conn = init_schema("data/kabusys.duckdb")
  # ":memory:" も使用可能: init_schema(":memory:")

2) 日次 ETL 実行（市場カレンダー・株価・財務・品質チェック）
  from kabusys.data.pipeline import run_daily_etl
  result = run_daily_etl(conn)  # target_date を指定可能
  print(result.to_dict())

3) 単体 ETL ジョブ（株価のみ）
  from kabusys.data.pipeline import run_prices_etl
  from datetime import date
  fetched, saved = run_prices_etl(conn, target_date=date.today())

4) RSS ニュース収集と保存
  from kabusys.data.news_collector import run_news_collection
  # known_codes は銘柄抽出時の候補セット（例: 上場銘柄コードの set）
  results = run_news_collection(conn, sources=None, known_codes={"7203","6758"})

5) カレンダー更新ジョブ（夜間バッチ）
  from kabusys.data.calendar_management import calendar_update_job
  saved = calendar_update_job(conn)

6) 監査ログスキーマ初期化（監査専用）
  from kabusys.data.audit import init_audit_schema
  init_audit_schema(conn)  # 既存の conn に監査テーブルを追加

7) J-Quants の直接操作（トークン取得・データフェッチ）
  from kabusys.data.jquants_client import get_id_token, fetch_daily_quotes
  token = get_id_token()  # settings.jquants_refresh_token を利用
  rows = fetch_daily_quotes(id_token=token, date_from=date(2023,1,1), date_to=date(2023,1,31))

ログ出力:
- settings.log_level でログレベルを管理できます（環境変数 LOG_LEVEL）。

注意点:
- ETL は差分取得を行います。初回はデータ取得開始日（jquants_client の _MIN_DATA_DATE=2017-01-01）が使われます。
- news_collector は受信サイズ上限やリダイレクト先の検査などセキュリティ対策を行っています。外部 RSS の実行ではタイムアウトやネットワークエラーに注意してください。

---

## ディレクトリ構成

パッケージルート（src/kabusys）を中心に主要ファイルを示します:

- src/kabusys/
  - __init__.py
  - config.py               - 環境変数・設定管理（.env 自動読み込み）
  - data/
    - __init__.py
    - schema.py             - DuckDB スキーマ定義・初期化
    - jquants_client.py     - J-Quants API クライアント（取得・保存ロジック）
    - pipeline.py           - ETL パイプライン（差分更新・日次ETL）
    - news_collector.py     - RSS ニュース収集・保存・銘柄抽出
    - calendar_management.py- マーケットカレンダー管理・ユーティリティ
    - audit.py              - 監査ログスキーマ（signal / order / execution）
    - quality.py            - データ品質チェック
  - strategy/
    - __init__.py           - 戦略関連モジュール（拡張ポイント）
  - execution/
    - __init__.py           - 発注・約定・ブローカー連携（拡張ポイント）
  - monitoring/
    - __init__.py           - 監視関連（将来的な機能）

その他:
- README.md                - このドキュメント
- .env / .env.local         - 環境変数（プロジェクトルートに配置）

---

## 実運用上の注意 / ベストプラクティス

- 秘密情報（API トークン等）は Git に含めないよう .gitignore を設定してください。
- 本番運用では KABUSYS_ENV を `live` に設定し、paper_trading / development と明確に分離してください。
- DuckDB ファイルは定期バックアップを検討してください（特に監査ログを含む場合）。
- J-Quants の API レート・規約を守って利用してください。jquants_client はレート制限に合わせた実装を行っていますが、外部リクエスト設計にも注意してください。
- news_collector は外部の RSS を取り扱うため、タイムアウト・サイズ上限設定を適切に設定してください。
- 品質チェック (data.quality) の結果は運用ルールに従ってアラートや ETL 停止等のハンドリングを実装してください（既定では ETL は継続します）。

---

問題や拡張要望があればソースコード内コメントを参照してください。既存モジュールは戦略（strategy）や実行（execution）などで拡張できるよう設計されています。