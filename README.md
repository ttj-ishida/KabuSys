# KabuSys

日本株向けの自動売買 / データ基盤ライブラリ。J-Quants API や RSS ニュースを取得して DuckDB に保存し、ETL・品質チェック・市場カレンダー管理・監査ログなどの機能を提供します。

主な設計方針:
- データ取得は冪等（ON CONFLICT で更新）かつトレース可能（fetched_at に UTC タイムスタンプを記録）
- API レートリミットとリトライ／トークンリフレッシュを組み込んだ堅牢なクライアント
- RSS ニュースは SSRF／XML 攻撃対策やサイズ制限を備えた収集
- DuckDB をデータ格納に使用し、スキーマ初期化・監査テーブルを提供

---

## 機能一覧

- 環境変数/設定管理
  - .env / .env.local の自動読み込み（プロジェクトルート検出）
  - 必須設定の取得とバリデーション
- J-Quants API クライアント（kabusys.data.jquants_client）
  - 株価日足（OHLCV）、財務データ、JPX マーケットカレンダーの取得
  - レートリミット（120 req/min）制御、指数バックオフによるリトライ、401 時の自動トークンリフレッシュ
  - DuckDB へ冪等に保存する save_* 関数
- ETL パイプライン（kabusys.data.pipeline）
  - 差分更新ロジック（最終取得日から自動算出）
  - 日次 ETL（市場カレンダー → 株価 → 財務 → 品質チェック）
  - 品質チェックの呼び出し（欠損・重複・スパイク・日付不整合）
- ニュース収集（kabusys.data.news_collector）
  - RSS 取得、前処理、記事ID生成（正規化 URL の SHA-256 頭32文字）
  - SSRF 対策、受信サイズ上限、gzip 解凍後サイズ検査
  - raw_news / news_symbols への冪等保存
- マーケットカレンダー管理（kabusys.data.calendar_management）
  - 営業日判定、next/prev trading day、期間内営業日取得、夜間バッチ更新 job
- スキーマ管理（kabusys.data.schema）
  - Raw / Processed / Feature / Execution / Audit 向けのテーブル定義と初期化
  - init_schema(), get_connection()
- 監査ログ（kabusys.data.audit）
  - signal_events, order_requests, executions など監査用テーブルと初期化補助
  - init_audit_db(), init_audit_schema()
- データ品質チェック（kabusys.data.quality）
  - check_missing_data, check_spike, check_duplicates, check_date_consistency, run_all_checks

---

## 要件

- Python 3.10+
- 主な依存パッケージ（例）
  - duckdb
  - defusedxml

（プロジェクトで使用する他ライブラリは運用環境のパッケージ管理定義に合わせてインストールしてください）

---

## セットアップ手順

1. ソースをクローン（またはローカルに配置）
2. 仮想環境を作成して有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 依存パッケージをインストール
   - pip install duckdb defusedxml
   - （必要に応じて他の依存を追加）
4. 環境変数を用意
   - プロジェクトルートに `.env` または `.env.local` を作成（自動で読み込まれます）
   - 必須の環境変数:
     - JQUANTS_REFRESH_TOKEN（J-Quants リフレッシュトークン）
     - KABU_API_PASSWORD（kabuステーション API のパスワード）
     - SLACK_BOT_TOKEN（Slack 通知に使用する bot token）
     - SLACK_CHANNEL_ID（Slack 通知先チャンネル ID）
   - 任意/デフォルト:
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
     - LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL) — デフォルト: INFO
     - KABU_API_BASE_URL — デフォルト: http://localhost:18080/kabusapi
     - DUCKDB_PATH — デフォルト: data/kabusys.duckdb
     - SQLITE_PATH — デフォルト: data/monitoring.db
   - 自動 .env 読み込みは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能
5. データベース用ディレクトリの作成は init_schema() 等が自動で行います

---

## 使い方（クイックスタート）

以下は Python REPL あるいはスクリプトでの利用例です。

1) DuckDB スキーマ初期化
- 既定パスに DB を作る例:
  - from kabusys.data.schema import init_schema
  - conn = init_schema("data/kabusys.duckdb")
- インメモリ DB:
  - conn = init_schema(":memory:")

2) 日次 ETL を実行（市場カレンダー・株価・財務・品質チェックを順に実行）
- from kabusys.data.pipeline import run_daily_etl
- result = run_daily_etl(conn)  # target_date を指定可能
- print(result.to_dict())

run_daily_etl の主な引数:
- target_date: ETL 対象日（省略時 = today）
- id_token: J-Quants の id token を外から渡してテスト可能
- run_quality_checks: 品質チェックを実行するか
- backfill_days: 最終取得日の何日前から再取得するか（デフォルト 3 日）

3) ニュース収集ジョブ
- from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
- saved = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes={"7203","6758"})
- saved は {source_name: 新規保存件数} の辞書

4) カレンダー夜間更新ジョブ
- from kabusys.data.calendar_management import calendar_update_job
- saved = calendar_update_job(conn)

5) 監査ログ初期化（監査専用 DB）
- from kabusys.data.audit import init_audit_db
- audit_conn = init_audit_db("data/audit.duckdb")

6) J-Quants から ID トークンを直接取得
- from kabusys.data.jquants_client import get_id_token
- token = get_id_token()  # settings.jquants_refresh_token を使う

---

## 設定（環境変数の詳細）

自動で読み込まれる設定は kabusys.config.Settings で定義されています。主なキー:

必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD
- SLACK_BOT_TOKEN
- SLACK_CHANNEL_ID

オプション（デフォルト値あり）:
- KABUSYS_ENV (development | paper_trading | live) — 動作モード
- LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL) — ログレベル
- KABU_API_BASE_URL — kabuステーション API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト: data/monitoring.db）

.env ファイル読み込みの挙動:
- プロジェクトルートは .git または pyproject.toml を基準に自動検出
- 読み込み順: OS 環境変数 > .env.local > .env
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動読み込みを無効化

---

## 主要モジュールと API（抜粋）

- kabusys.config
  - settings: 設定オブジェクト（プロパティで環境変数を取得）
- kabusys.data.jquants_client
  - fetch_daily_quotes(...), fetch_financial_statements(...), fetch_market_calendar(...)
  - save_daily_quotes(conn, records), save_financial_statements(...), save_market_calendar(...)
  - get_id_token(refresh_token=None)
- kabusys.data.schema
  - init_schema(db_path), get_connection(db_path)
- kabusys.data.pipeline
  - run_daily_etl(conn, ...)
  - run_prices_etl, run_financials_etl, run_calendar_etl
- kabusys.data.news_collector
  - fetch_rss(url, source, timeout=30)
  - save_raw_news(conn, articles), save_news_symbols(conn, news_id, codes)
  - run_news_collection(conn, sources=None, known_codes=None)
- kabusys.data.calendar_management
  - is_trading_day(conn, d), next_trading_day(...), prev_trading_day(...), get_trading_days(...)
  - calendar_update_job(conn, lookahead_days=90)
- kabusys.data.audit
  - init_audit_schema(conn, transactional=False), init_audit_db(db_path)
- kabusys.data.quality
  - run_all_checks(conn, target_date=None, reference_date=None, spike_threshold=0.5)

設計に関する注記（実装上の特徴）:
- J-Quants クライアントは 120 req/min のレート制限を尊重する RateLimiter を内蔵
- HTTP エラーに対する指数バックオフリトライ（408/429/5xx 対象）
- 401 受信時はリフレッシュトークンによる id_token 更新を自動実行して 1 回だけ再試行
- ニュース収集は SSRF、XML bomb、gzip bomb、サイズ超過対策を実装
- ETL は差分更新＋バックフィル（デフォルト 3 日）で API 後出し修正を吸収
- DuckDB への保存は基本的に ON CONFLICT を用いた冪等操作

---

## ディレクトリ構成

（主要ファイルを抜粋）

- src/kabusys/
  - __init__.py
  - config.py
  - execution/                (発注ロジック等のためのパッケージプレースホルダ)
  - strategy/                 (戦略ロジックのためのパッケージプレースホルダ)
  - monitoring/               (モニタリング/メトリクス用プレースホルダ)
  - data/
    - __init__.py
    - jquants_client.py       # J-Quants API クライアント + DuckDB への保存
    - news_collector.py       # RSS 収集・前処理・保存
    - pipeline.py             # ETL パイプライン（差分更新・日次 ETL）
    - schema.py               # DuckDB スキーマ定義・初期化
    - calendar_management.py  # 市場カレンダー管理
    - audit.py                # 監査ログスキーマ初期化
    - quality.py              # データ品質チェック

---

## 開発 / 貢献

- 仕様や DB スキーマはコメントと DataPlatform.md 等（プロジェクト参照）に従っています。
- テスト駆動で開発する場合は、KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自動 .env 読み込みを無効化してください。
- 大きな DB 操作を行う関数はトランザクション管理を行っている箇所とそうでない箇所があります。init_audit_schema の transactional フラグや save 系関数のトランザクション挙動を確認の上、運用してください。

---

## トラブルシューティング

- .env が読み込まれない / テスト時に値を注入したい場合:
  - 環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 をセット
- J-Quants のリクエストが 401 になる:
  - settings.jquants_refresh_token の値を確認。get_id_token() を単体で試すと原因切り分けに有用
- DuckDB のテーブルが作成されない:
  - init_schema() を呼び出しているか確認。パスの親ディレクトリは init_schema が自動作成するが、ファイルパスを見直してください

---

必要であれば README に .env.example のサンプルや、より詳細な API 使用例、デプロイ手順（systemd / cron / Airflow などでの日次 ETL 登録）を追加します。どの情報を優先して拡張しますか？