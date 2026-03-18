# KabuSys

日本株向けの自動売買基盤ライブラリ（KabuSys）。データ取得（J-Quants）、ETL、データ品質チェック、ニュース収集、マーケットカレンダー管理、監査ログ（発注〜約定のトレース）など、量的運用に必要な基盤コンポーネントを提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は以下の目的で作られた内部ライブラリです。

- J-Quants API から株価・財務・カレンダーを安全に取得し DuckDB に保存する
- RSS ベースのニュース収集と銘柄抽出（SSRF / XML 攻撃対策・サイズ制限あり）
- ETL（差分取得、バックフィル、品質チェック）を行う日次パイプライン
- JPX マーケットカレンダーの管理（営業日判定、次/前営業日の計算など）
- 監査用テーブル群（シグナル -> 発注要求 -> 約定）によるトレーサビリティ
- データ品質チェック（欠損、スパイク、重複、日付不整合）

設計上のポイント:
- API レート制限（J-Quants: 120 req/min）を尊重する RateLimiter を搭載
- リトライ（指数バックオフ）、401 の際のトークン自動リフレッシュ対応
- DuckDB への保存は冪等（ON CONFLICT）で安全
- XML パースに `defusedxml` を使用、受信サイズの上限や SSRF 対策を実装

---

## 機能一覧

- data/jquants_client.py
  - J-Quants から日足・財務・マーケットカレンダー取得（ページネーション対応）
  - id_token 取得（リフレッシュトークン経由）、キャッシュ、401 自動リフレッシュ
  - レートリミット、リトライ、DuckDB への冪等保存関数（raw_prices, raw_financials, market_calendar）
- data/news_collector.py
  - RSS フィード取得、XML 安全パース、テキスト前処理、記事 ID 生成（正規化URL→SHA-256）
  - SSRF対策（スキーム検証、プライベートIP拒否、リダイレクト検査）
  - DuckDB への一括挿入（INSERT ... RETURNING）、銘柄コード抽出・紐付け
- data/schema.py
  - DuckDB のフルスキーマ定義（Raw / Processed / Feature / Execution 層）
  - init_schema(db_path) によるテーブル・インデックス作成
- data/pipeline.py
  - 差分更新ベースの ETL（run_prices_etl, run_financials_etl, run_calendar_etl, run_daily_etl）
  - backfill の実装、品質チェック呼び出し
- data/calendar_management.py
  - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day
  - calendar_update_job による夜間カレンダー更新ジョブ
- data/audit.py
  - 監査ログ（signal_events, order_requests, executions）初期化関数
  - init_audit_db / init_audit_schema（UTC タイムゾーン固定）
- data/quality.py
  - 欠損・スパイク・重複・日付不整合のチェック（QualityIssue を返す）
- config.py
  - 環境変数読み込み（.env/.env.local 自動ロード）、必須キーチェック、settings オブジェクト提供

---

## セットアップ手順（開発/ローカル利用向け）

1. リポジトリをクローン／入手し、Python 仮想環境を作成・有効化します。

   - 推奨 Python バージョン: 3.9+
   - 例:
     python -m venv .venv
     source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージをインストールします（例）。requirements.txt が無い場合は最低限以下を入れてください。

   pip install duckdb defusedxml

   （プロジェクトで Slack や他クライアントを使う場合は必要なライブラリを追加してください）

3. 環境変数 / .env を準備します。
   - 必須環境変数（config.Settings 参照）:
     - JQUANTS_REFRESH_TOKEN : J-Quants の refresh token
     - KABU_API_PASSWORD     : kabuステーション API のパスワード
     - SLACK_BOT_TOKEN       : Slack 通知に使う Bot トークン
     - SLACK_CHANNEL_ID      : Slack 通知先チャンネル ID
   - 任意 / デフォルト:
     - KABUSYS_ENV           : development | paper_trading | live （デフォルト development）
     - KABU_API_BASE_URL     : kabu API ベース URL（デフォルト http://localhost:18080/kabusapi）
     - DUCKDB_PATH           : DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
     - SQLITE_PATH           : 監視用 SQLite パス（デフォルト data/monitoring.db）
     - LOG_LEVEL             : ログレベル（DEBUG/INFO/...）

   自動ロード挙動（config.py）:
   - プロジェクトルート（.git または pyproject.toml があるディレクトリ）から `.env` → `.env.local` の順に読み込み
   - OS 環境変数が優先され、.env.local は既存変数を上書き
   - 自動読み込みを無効化する場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定

4. DB スキーマ初期化（DuckDB）

   - 例: Python から直接初期化する
     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")

   - 監査ログ用 DB（別DBに分けたい場合）
     from kabusys.data.audit import init_audit_db
     audit_conn = init_audit_db("data/kabusys_audit.duckdb")

---

## 使い方（基本的な例）

以下は代表的な利用例です。実際にはロギングやエラーハンドリングを追加してください。

- DuckDB スキーマ初期化

  from kabusys.data.schema import init_schema
  conn = init_schema("data/kabusys.duckdb")

- J-Quants トークン取得（必要時）

  from kabusys.data.jquants_client import get_id_token
  id_token = get_id_token()  # settings.jquants_refresh_token を自動参照

- 日次 ETL 実行（市場カレンダー取得 → 株価・財務の差分取得 → 品質チェック）

  from kabusys.data.pipeline import run_daily_etl
  result = run_daily_etl(conn)  # target_date を指定可能
  print(result.to_dict())

- ニュース収集ジョブ（RSS から記事を保存し、銘柄紐付け）

  from kabusys.data.news_collector import run_news_collection
  # known_codes は既知の銘柄コード集合（例: set(["7203","6758",...])）
  stats = run_news_collection(conn, sources=None, known_codes=known_codes)
  print(stats)  # {source_name: saved_count}

- カレンダー夜間更新ジョブ（cron やワーカーから呼ぶ）

  from kabusys.data.calendar_management import calendar_update_job
  saved = calendar_update_job(conn)
  print(f"saved calendar rows: {saved}")

- 品質チェックを手動で実行

  from kabusys.data.quality import run_all_checks
  issues = run_all_checks(conn)
  for i in issues:
      print(i)

- 監査ログ初期化（監査 DB を別立てする場合）

  from kabusys.data.audit import init_audit_db
  audit_conn = init_audit_db("data/kabusys_audit.duckdb")

---

## 環境変数（まとめ）

必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD
- SLACK_BOT_TOKEN
- SLACK_CHANNEL_ID

推奨 / 任意:
- KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (デフォルト: data/monitoring.db)
- KABUSYS_ENV (development / paper_trading / live)
- LOG_LEVEL (DEBUG/INFO/WARNING/ERROR/CRITICAL)

自動 .env 読み込み:
- プロジェクトルートの `.env` および `.env.local` を読み込む
- 無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1

---

## ディレクトリ構成（主要ファイル）

- src/kabusys/
  - __init__.py                (パッケージのエントリ。__version__ = "0.1.0")
  - config.py                  (環境変数/設定管理: settings オブジェクト)
  - data/
    - __init__.py
    - jquants_client.py        (J-Quants API クライアント・保存ロジック)
    - news_collector.py        (RSS 収集、記事正規化、DB 保存、銘柄抽出)
    - schema.py                (DuckDB スキーマ定義 / init_schema)
    - pipeline.py              (ETL パイプライン: run_daily_etl 等)
    - calendar_management.py   (市場カレンダー操作・バッチ更新)
    - audit.py                 (監査ログテーブルの DDL と初期化)
    - quality.py               (データ品質チェック)
  - strategy/
    - __init__.py              (戦略用パッケージ置き場)
  - execution/
    - __init__.py              (発注/ブローカ接続用プレースホルダ)
  - monitoring/
    - __init__.py

---

## 開発・運用上の注意

- J-Quants のレート制限を厳守する実装が組み込まれていますが、長時間の大量リクエストや別プロセスでの同時呼び出しがある場合は運用側でさらに制御してください。
- DuckDB へはオンコンフリクトで冪等に保存しますが、スキーマ変更や手動操作による不整合がある場合は品質チェック（quality.run_all_checks）を定期実行してください。
- RSS 収集は外部インターネットアクセスを伴うため、企業ネットワーク、プロキシ、セキュリティ要件に注意してください。news_collector は SSRF 対策・受信サイズ制限を導入していますが、運用監視が必要です。
- audit テーブル群は監査証跡として削除しない前提です。保存先のディスク容量やバックアップ方針を運用側で検討してください。
- KABUSYS_ENV の値に応じて振る舞い（本番/ペーパー/開発）を切り替える設計です。live 環境での発注機能を実装する際は十分なテストと安全策を入れてください。

---

## 参考

- 各モジュールの詳細な挙動はソースコード内の docstring とコメントを参照してください。
- DB スキーマや ETL の設計方針はコード内の `DataSchema.md` / `DataPlatform.md` 相当のコメントに従っています（実ファイルは別途管理される想定）。

---

必要なら、README に含める具体的なコマンド例（cron ジョブ、Dockerfile、CI 設定）、推奨パッケージ一覧（requirements.txt）、あるいは戦略/実行モジュールのサンプル実装テンプレートも作成します。どれを追加しますか？