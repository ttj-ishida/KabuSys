# KabuSys

日本株向け自動売買基盤（KabuSys）のリポジトリ用 README。  
本プロジェクトはデータ収集・ETL、監査ログ、ニュース収集、戦略・発注管理といった自動売買に必要な基盤機能を提供します。

---

## プロジェクト概要

KabuSys は以下の主要機能を備えた日本株自動売買システムの基盤ライブラリです。

- J-Quants API からの株価・財務・マーケットカレンダー取得（レート制限・リトライ・トークン自動更新対応）
- DuckDB を用いた三層データスキーマ（Raw / Processed / Feature）と冪等な保存ロジック
- RSS からのニュース収集（SSRF 防御、トラッキングパラメータ除去、記事IDの冪等化）
- ETL パイプライン（差分取得、バックフィル、品質チェック）
- 市場カレンダー管理（営業日判定、次/前営業日算出）
- 監査ログ（シグナル→発注→約定のトレーサビリティ）
- データ品質チェック（欠損、重複、スパイク、日付不整合検出）

設計上の特徴：
- API レート制限と堅牢なリトライ（指数バックオフ）により安定した外部 API 呼び出しを実現
- データ永続化は冪等操作（ON CONFLICT）で二重登録を防止
- セキュリティ対策（XML パースに defusedxml、RSS の SSRF 対策、受信サイズ上限など）

---

## 機能一覧

- data/
  - jquants_client.py : J-Quants API クライアント（取得・保存関数、トークン管理、レートリミット、リトライ）
  - news_collector.py : RSS 収集・前処理・DuckDB への保存、銘柄抽出
  - schema.py : DuckDB のスキーマ定義（Raw / Processed / Feature / Execution 層）と初期化 API
  - pipeline.py : 日次 ETL パイプライン（差分取得・保存・品質チェック）
  - calendar_management.py : カレンダー更新ジョブ、営業日判定ユーティリティ
  - audit.py : 監査ログ（signal / order_request / executions）スキーマと初期化
  - quality.py : データ品質チェック（欠損・重複・スパイク・日付不整合）
- config.py : 環境変数読み込みと Settings インターフェース（.env 自動ロード機能付き）
- strategy/ : 戦略モジュール（拡張ポイント）
- execution/ : 発注実行関連（拡張ポイント）
- monitoring/ : 監視関連（拡張ポイント）

---

## セットアップ手順

前提:
- Python 3.10 以上（型ヒントに `X | Y` を使用しているため）
- Git が利用可能ならプロジェクトルートに `.git` があることで `.env` 自動読み込みが有効になります

依存パッケージ（最小）:
- duckdb
- defusedxml

インストール例（仮に venv を使う）:

1. 仮想環境作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要ライブラリをインストール
   - pip install --upgrade pip
   - pip install duckdb defusedxml

3. （任意）パッケージを開発モードでインストール
   - python -m pip install -e .

環境変数（必須）
- JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD     : kabuステーション API のパスワード（必須）
- SLACK_BOT_TOKEN       : Slack 通知用トークン（必須）
- SLACK_CHANNEL_ID      : Slack チャネル ID（必須）

任意/デフォルト
- KABUSYS_ENV           : development / paper_trading / live（デフォルト: development）
- LOG_LEVEL             : DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）
- DUCKDB_PATH           : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH           : 監視 DB などの SQLite パス（デフォルト: data/monitoring.db）

.env の自動ロード
- パッケージ初期化時に .env ファイルを自動ロードします（プロジェクトルートは __file__ の親階層から .git または pyproject.toml で探索）。
- 読み込み順: OS 環境変数 > .env.local > .env
- 自動ロードを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テストでの利用を想定）。

例 .env（プロジェクトルートに配置）
- JQUANTS_REFRESH_TOKEN=xxxxxxxx
- KABU_API_PASSWORD=your_kabu_password
- SLACK_BOT_TOKEN=xoxb-...
- SLACK_CHANNEL_ID=C01234567
- KABUSYS_ENV=development
- LOG_LEVEL=INFO

---

## 使い方（主要な例）

以下はライブラリ内 API の利用例です。実行は Python スクリプト内で行います。

1) DuckDB スキーマ初期化
- データ用 DB を初期化して接続オブジェクトを取得します。

  from kabusys.data import schema
  conn = schema.init_schema("data/kabusys.duckdb")

- 監査ログ専用 DB を初期化する場合:

  from kabusys.data import audit
  audit_conn = audit.init_audit_db("data/kabusys_audit.duckdb")

2) 日次 ETL の実行
- 日次 ETL を呼び出して、株価・財務・カレンダーを差分取得して保存します。

  from kabusys.data.pipeline import run_daily_etl
  result = run_daily_etl(conn)  # target_date を渡さない場合は今日が対象
  print(result.to_dict())

3) 単体ジョブ（価格 ETL）
- 特定日または差分のみ実行したい場合:

  from datetime import date
  from kabusys.data.pipeline import run_prices_etl
  fetched, saved = run_prices_etl(conn, target_date=date.today())

4) ニュース収集
- RSS フィードから記事を収集して raw_news と news_symbols を更新します。

  from kabusys.data.news_collector import run_news_collection
  known_codes = {"7203", "6758", "9984"}  # 有効な銘柄コードセット
  results = run_news_collection(conn, sources=None, known_codes=known_codes)
  print(results)  # {source_name: 新規保存件数}

5) J-Quants ID トークン取得（手動）
- get_id_token() はリフレッシュトークンから idToken を取得します（通常は内部で自動管理）。

  from kabusys.data.jquants_client import get_id_token
  id_token = get_id_token()  # settings.jquants_refresh_token を使用

6) 品質チェックのみ実行
- ETL 後にデータ品質を確認するには:

  from kabusys.data.quality import run_all_checks
  issues = run_all_checks(conn)
  for i in issues:
      print(i)

注意点:
- jquants_client は内部でレート制限（120 req/min）を実装しており、リトライや 401 時のトークン自動更新に対応しています。
- news_collector は XML の脆弱性対策（defusedxml）や SSRF 対策、受信サイズ上限を備えています。

---

## ディレクトリ構成

リポジトリの主要ファイル/モジュール構成（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py
  - data/
    - __init__.py
    - jquants_client.py
    - news_collector.py
    - schema.py
    - pipeline.py
    - calendar_management.py
    - audit.py
    - quality.py
  - strategy/
    - __init__.py
    - ...（戦略実装を配置）
  - execution/
    - __init__.py
    - ...（発注・ブローカー連携を配置）
  - monitoring/
    - __init__.py
    - ...（監視関連を配置）

主な役割:
- config.py : 環境変数読み込みと settings オブジェクト（settings.jquants_refresh_token など）を提供
- data/schema.py : DuckDB スキーマ定義と init_schema / get_connection を提供
- data/jquants_client.py : API 呼び出し、取得・保存関数
- data/pipeline.py : 日次 ETL エントリポイント（run_daily_etl）
- data/news_collector.py : RSS 収集と raw_news 保存、銘柄紐付け
- data/audit.py : 監査テーブルの初期化ユーティリティ
- data/quality.py : データ品質チェックロジック

---

## 運用・開発メモ

- Settings は必須環境変数が未設定の場合 ValueError を送出します。CI/運用環境では .env を正しく配置するか環境変数をセットしてください。
- テストや一時的に自動 .env ロードを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB のスキーマ初期化は冪等です。init_schema() / init_audit_schema() は既存テーブルがあればスキップします。
- news_collector は外部ネットワークにアクセスするため、運用環境ではプロキシやファイアウォールの設定に注意してください。
- ロギングは標準 logging を利用します。LOG_LEVEL 環境変数で出力レベルを調整できます。

---

## 参考（すぐ使えるサンプルスクリプト）

簡単な ETL 実行スクリプト例:

  # sample_run_etl.py
  import logging
  from kabusys.config import settings
  from kabusys.data import schema, pipeline

  logging.basicConfig(level=settings.log_level)
  conn = schema.init_schema(settings.duckdb_path)
  result = pipeline.run_daily_etl(conn)
  print(result.to_dict())

---

ご不明点や追加で README に含めたい情報（例: CI、デプロイ手順、外部サービス連携の詳細）などがあれば教えてください。README をその要件に合わせて拡張します。