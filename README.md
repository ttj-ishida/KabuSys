# KabuSys

日本株向けの自動売買プラットフォーム用ライブラリ群（データ収集・ETL・品質チェック・監査ログ等）

## プロジェクト概要
KabuSys は日本株の自動売買システム向けに設計された内部ライブラリです。  
主に以下を提供します。

- J-Quants API を用いた市場データ（株価日足・財務・カレンダー）の取得と DuckDB への保存
- RSS ベースのニュース収集と記事の正規化・DB 保存（SSRF対策・XML安全対策・トラッキング除去）
- ETL パイプライン（差分取得・バックフィル・品質チェック）
- マーケットカレンダー管理（営業日判定・次/前営業日の取得）
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログ（シグナル → 発注 → 約定までのトレーサビリティ）テーブル定義と初期化

設計では冪等性（ON CONFLICT）やネットワークリトライ、レートリミット、セキュリティ対策（SSRF/ XML Bomb/受信サイズ制限）を重視しています。

## 主な機能一覧
- data.jquants_client
  - 株価（daily_quotes）、財務（fins/statements）、市場カレンダー取得
  - レートリミット（120 req/min）、リトライ（指数バックオフ、401時トークン自動更新）
  - DuckDB への保存関数（save_*）は冪等（ON CONFLICT）
- data.news_collector
  - RSS フィード取得・記事正規化（URLトラッキング削除、テキスト前処理）
  - URL スキーム検証、リダイレクト時のホスト検査（プライベートIP拒否）
  - defusedxml による XML パース、受信サイズ上限
  - raw_news / news_symbols への安全なバルク保存（INSERT ... RETURNING）
- data.pipeline
  - 差分ETL（価格・財務・カレンダー）／バックフィル／品質チェック実行（run_daily_etl）
- data.calendar_management
  - market_calendar を基にした営業日判定、next/prev_trading_day、トラブル対策つき夜間更新ジョブ
- data.quality
  - 欠損、スパイク（前日比）、重複、日付不整合の検出。QualityIssue を返却
- data.schema / data.audit
  - DuckDB 用スキーマ定義（Raw / Processed / Feature / Execution 層）
  - 監査ログ用テーブルとインデックス初期化

## セットアップ手順

前提
- Python 3.9+（コードは型ヒントに union 型などを使用）
- DuckDB を使用（pip パッケージ duckdb）
- defusedxml（RSS の安全なパース）
- ネットワーク接続（J-Quants API 等）

1. リポジトリを取得／パッケージをインストール
   - このコードがパッケージ化されている場合は pip でインストールできます（または開発モードでインストール）。
   - 依存パッケージ例:
     pip install duckdb defusedxml

2. 環境変数（.env）を準備
   - 自動でルートの `.env` / `.env.local` をロードします（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると無効化）。
   - 必須環境変数:
     - JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD — kabu ステーション API のパスワード（execution モジュール使用時）
     - SLACK_BOT_TOKEN — Slack 通知用トークン（任意機能で使用）
     - SLACK_CHANNEL_ID — Slack チャンネル ID
   - 任意 / デフォルト:
     - KABUSYS_ENV: development / paper_trading / live （デフォルト development）
     - LOG_LEVEL: DEBUG / INFO / ...
     - DUCKDB_PATH: data/kabusys.duckdb（デフォルト）
     - SQLITE_PATH: data/monitoring.db（デフォルト）

   例 .env（プロジェクトルートに配置）:
   ```
   JQUANTS_REFRESH_TOKEN="your_jquants_refresh_token_here"
   KABU_API_PASSWORD="your_kabu_api_password"
   SLACK_BOT_TOKEN="xoxb-..."
   SLACK_CHANNEL_ID="C01234567"
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   DUCKDB_PATH=data/kabusys.duckdb
   ```

3. DuckDB スキーマ初期化
   - Python から schema.init_schema を呼んで DB を作成／テーブルを準備します。
   - 例:
     ```python
     from kabusys.data import schema
     conn = schema.init_schema("data/kabusys.duckdb")
     ```
   - 監査ログのみ別 DB に分けたい場合:
     ```python
     from kabusys.data import audit
     audit_conn = audit.init_audit_db("data/kabusys_audit.duckdb")
     ```
   - 既存 DB に接続するだけなら:
     ```python
     conn = schema.get_connection("data/kabusys.duckdb")
     ```

## 使い方（主要な例）

1. 日次 ETL を実行（市場カレンダー → 株価 → 財務 → 品質チェック）
   ```python
   from datetime import date
   import logging
   import duckdb
   from kabusys.data import pipeline, schema

   logging.basicConfig(level=logging.INFO)
   conn = schema.init_schema("data/kabusys.duckdb")
   result = pipeline.run_daily_etl(conn, target_date=date.today())
   print(result.to_dict())
   ```

2. 市場カレンダー夜間更新ジョブ（個別）
   ```python
   from kabusys.data import calendar_management, schema
   conn = schema.get_connection("data/kabusys.duckdb")
   saved = calendar_management.calendar_update_job(conn)
   print("saved:", saved)
   ```

3. RSS ニュース収集と DB 保存
   ```python
   from kabusys.data import news_collector, schema
   conn = schema.get_connection("data/kabusys.duckdb")
   results = news_collector.run_news_collection(conn, sources=None, known_codes={"7203","6758"})
   print(results)  # { "yahoo_finance": <新規保存数>, ... }
   ```

4. J-Quants の手動トークン取得 / API 呼び出し
   ```python
   from kabusys.data import jquants_client as jq
   id_token = jq.get_id_token()  # settings の refresh token を使う
   quotes = jq.fetch_daily_quotes(id_token=id_token, code="7203", date_from=date(2024,1,1), date_to=date(2024,2,1))
   ```

5. 品質チェックを個別実行
   ```python
   from kabusys.data import quality, schema
   conn = schema.get_connection("data/kabusys.duckdb")
   issues = quality.run_all_checks(conn, target_date=None)
   for i in issues:
       print(i)
   ```

注意:
- J-Quants API 呼び出しは内部でレートリミット・リトライ・401自動更新を行います。テスト時に id_token を注入すると副作用を抑えられます。
- news_collector は外部から指定された RSS URL のリダイレクト先を検査し、プライベートIPや非 http/https スキームを拒否します。

## 環境変数一覧（主要）
- JQUANTS_REFRESH_TOKEN (必須) — J-Quants リフレッシュトークン
- KABU_API_PASSWORD (必須 for execution)
- KABU_API_BASE_URL (省略可) — デフォルト "http://localhost:18080/kabusapi"
- SLACK_BOT_TOKEN (必須 for Slack notifications)
- SLACK_CHANNEL_ID (必須 for Slack notifications)
- DUCKDB_PATH (省略可) — デフォルト "data/kabusys.duckdb"
- SQLITE_PATH (省略可) — デフォルト "data/monitoring.db"
- KABUSYS_ENV — development / paper_trading / live（検証あり）
- LOG_LEVEL — DEBUG/INFO/WARNING/ERROR/CRITICAL
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 1 を設定すると自動で .env ファイルを読み込まない

## ディレクトリ構成
（主要ファイルのみ抜粋）

- src/kabusys/
  - __init__.py
  - config.py  — 環境変数/設定管理（.env 自動ロード、settings）
  - data/
    - __init__.py
    - jquants_client.py      — J-Quants API クライアント（fetch/save 関数、レート制御）
    - news_collector.py     — RSS ニュース収集・前処理・DB保存
    - schema.py             — DuckDB スキーマ定義・初期化
    - pipeline.py           — ETL パイプライン（差分取得／バックフィル／品質チェック）
    - calendar_management.py— カレンダー更新、営業日判定ユーティリティ
    - audit.py              — 監査ログ（シグナル/発注/約定）の DDL と初期化
    - quality.py            — データ品質チェック
  - strategy/
    - __init__.py
    (戦略実装用のパッケージ領域)
  - execution/
    - __init__.py
    (発注/ブローカ連携の実装領域)
  - monitoring/
    - __init__.py
    (監視／メトリクス用の実装領域)

## 実運用上の注意・設計ポイント
- DuckDB 上の INSERT は可能な限り ON CONFLICT（冪等）で設計されています。ETL を何度実行しても重複を避けることを念頭に設計されています。
- J-Quants API はレート制限があり、モジュール内で固定間隔スロットリングを実装しています。大量リクエスト時は API の制限に注意してください。
- news_collector は外部の RSS を扱うため複数の安全対策（defusedxml、SSRF リダイレクト検査、受信サイズ制限）を導入していますが、運用環境ではさらに監視ログ・例外ハンドリングを組み合わせてください。
- ETL は Fail-Fast ではなく、品質チェック等で検出した問題を収集して上位で判断する設計です。run_daily_etl の戻り値（ETLResult）で issues / errors を確認してください。

---

必要であれば README に「インストール要件（requirements.txt）」や CI の実行方法、より具体的な運用手順（cron/airflow でのスケジュール例）を追記できます。どの情報を追加しますか？