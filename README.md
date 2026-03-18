# KabuSys

日本株向けの自動売買プラットフォーム用ライブラリ（モジュール群）。  
J-Quants / kabuステーション 等の外部 API からデータを取得し、DuckDB を用いたデータレイク構築、ETL、品質チェック、ニュース収集、監査ログ（発注〜約定のトレーサビリティ）などの基盤機能を提供します。

バージョン: 0.1.0

---

## 主要な特徴（Overview / Features）

- J-Quants API クライアント
  - 株価日足（OHLCV）、財務（四半期 BS/PL）、JPX マーケットカレンダーの取得
  - API レート制限順守（120 req/min 固定間隔スロットリング）
  - リトライ（指数バックオフ、最大 3 回）、401 での自動トークンリフレッシュ対応
  - Look-ahead bias 対策のため fetched_at を UTC で記録

- ETL / データパイプライン
  - 差分更新（最終取得日を基に未取得分のみ取得）
  - backfill オプションにより数日前から再取得して後出し修正を吸収
  - 市場カレンダー先読み（デフォルト 90 日）

- DuckDB スキーマ管理
  - Raw / Processed / Feature / Execution の多層スキーマを提供
  - 冪等性を考慮した DDL（ON CONFLICT や PRIMARY KEY 等）

- ニュース収集（RSS）
  - RSS フィード取得、URL 正規化（utm_* 除去）、SHA-256 ベースの記事 ID 生成
  - SSRF 対策、受信サイズ制限、XML の安全パース（defusedxml）
  - raw_news / news_symbols への冪等保存

- 品質チェック（Data Quality）
  - 欠損値検出、スパイク検出、重複チェック、日付整合性チェック
  - QualityIssue を返し、致命度に応じた監査可能な結果

- 監査ログ（Audit）
  - signal / order_request / execution 等の監査テーブルを提供
  - UUID によるトレース（signal → order_request → broker_order → execution）
  - タイムゾーンは UTC 固定（SET TimeZone='UTC'）

- 簡易的な実行層（テーブル群）定義
  - signal_queue / orders / trades / positions / portfolio_performance 等

---

## セットアップ手順

※ ここでは一般的な手順を示します。プロジェクトに requirements.txt / pyproject.toml がある場合はそちらを優先してください。

1. Python（推奨: 3.10+）をインストール

2. 依存パッケージをインストール（例）
   - duckdb
   - defusedxml

   例:
   ```bash
   pip install duckdb defusedxml
   ```

3. パッケージをプロジェクトにインストール（編集可能モード等）
   ```bash
   pip install -e .
   ```
   または開発環境に合わせて適宜インストールしてください。

4. 環境変数 / .env ファイルの準備  
   - プロジェクトルートに `.env`（必要に応じ `.env.local`）を配置すると、自動で読み込まれます。
   - 自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

   推奨する .env の内容（例）:
   ```
   JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
   KABU_API_PASSWORD=your_kabu_password
   KABU_API_BASE_URL=http://localhost:18080/kabusapi
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

---

## 使い方（基本の流れ・API）

以下は代表的な利用例です。実際の運用ではエラーハンドリング・ログ設定等を追加してください。

1. DuckDB スキーマ初期化
   ```python
   from kabusys.data.schema import init_schema

   conn = init_schema("data/kabusys.duckdb")  # ファイルを自動作成して接続を返す
   ```

2. 監査ログ用スキーマ初期化（監査専用に分けたい場合）
   ```python
   from kabusys.data.audit import init_audit_db

   audit_conn = init_audit_db("data/audit.duckdb")
   ```

3. 日次 ETL 実行（市場カレンダー / 株価 / 財務 / 品質チェック）
   ```python
   from kabusys.data.pipeline import run_daily_etl

   result = run_daily_etl(conn)  # 引数で target_date / id_token / その他を指定可能
   print(result.to_dict())
   ```

4. 市場カレンダー夜間更新ジョブ
   ```python
   from kabusys.data.calendar_management import calendar_update_job

   saved = calendar_update_job(conn)
   print(f"saved calendar rows: {saved}")
   ```

5. RSS ニュース収集ジョブ
   ```python
   from kabusys.data.news_collector import run_news_collection
   # known_codes は銘柄抽出に使う有効な4桁銘柄コードの集合
   stats = run_news_collection(conn, sources=None, known_codes={"7203", "6758"})
   print(stats)
   ```

6. J-Quants API の直接呼び出し（トークン取得 / データ取得）
   ```python
   from kabusys.data import jquants_client as jq
   # id_token は省略可（モジュール内キャッシュを使用）
   quotes = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
   saved = jq.save_daily_quotes(conn, quotes)
   ```

---

## 重要な環境変数

- JQUANTS_REFRESH_TOKEN (必須)
  - J-Quants のリフレッシュトークン。get_id_token で使用されます。

- KABU_API_PASSWORD (必須)
  - kabuステーション API パスワード

- KABU_API_BASE_URL (任意)
  - デフォルト: http://localhost:18080/kabusapi

- SLACK_BOT_TOKEN (必須)
  - Slack 通知用（プロジェクト内で使用箇所に応じて）

- SLACK_CHANNEL_ID (必須)

- DUCKDB_PATH (任意)
  - デフォルト: data/kabusys.duckdb

- SQLITE_PATH (任意)
  - デフォルト: data/monitoring.db

- KABUSYS_ENV (任意)
  - 有効値: development, paper_trading, live
  - デフォルト: development

- LOG_LEVEL (任意)
  - 有効値: DEBUG, INFO, WARNING, ERROR, CRITICAL
  - デフォルト: INFO

自動ロード:
- パッケージ起点で .git または pyproject.toml を探索し、プロジェクトルートを特定して `.env` → `.env.local` の順で読み込みます。
- OS 環境変数は上書きされません（`.env.local` は上書き可能だが OS 環境変数は保護されます）。
- 自動ロードを無効にする: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

---

## 主要モジュールと API 概要

- kabusys.config
  - settings: 環境変数ラッパー（プロパティ経由で各種値を取得）

- kabusys.data.jquants_client
  - get_id_token(refresh_token=None)
  - fetch_daily_quotes(...)
  - fetch_financial_statements(...)
  - fetch_market_calendar(...)
  - save_daily_quotes(conn, records)
  - save_financial_statements(conn, records)
  - save_market_calendar(conn, records)
  - 設計: レートリミット, リトライ, 401リフレッシュ, fetched_at 記録

- kabusys.data.schema
  - init_schema(db_path)
  - get_connection(db_path)

- kabusys.data.pipeline
  - run_prices_etl(...)
  - run_financials_etl(...)
  - run_calendar_etl(...)
  - run_daily_etl(...)

- kabusys.data.news_collector
  - fetch_rss(url, source, timeout=30)
  - save_raw_news(conn, articles)
  - save_news_symbols(conn, news_id, codes)
  - run_news_collection(conn, sources=None, known_codes=None)

- kabusys.data.calendar_management
  - is_trading_day(conn, d)
  - next_trading_day(conn, d)
  - prev_trading_day(conn, d)
  - get_trading_days(conn, start, end)
  - is_sq_day(conn, d)
  - calendar_update_job(conn, lookahead_days=90)

- kabusys.data.quality
  - run_all_checks(conn, target_date=None, reference_date=None, spike_threshold=0.5)
  - check_missing_data(...)
  - check_spike(...)
  - check_duplicates(...)
  - check_date_consistency(...)

- kabusys.data.audit
  - init_audit_schema(conn, transactional=False)
  - init_audit_db(db_path)

---

## ディレクトリ構成（抜粋）

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
  - execution/
    - __init__.py
  - monitoring/
    - __init__.py

主要なファイルの役割:
- config.py: 環境設定・.env 自動読み込みロジック
- data/schema.py: DuckDB の DDL（テーブル定義）と初期化処理
- data/jquants_client.py: J-Quants API クライアント（取得＋保存）
- data/pipeline.py: ETL のオーケストレーション（差分更新・品質チェック）
- data/news_collector.py: RSS 収集→前処理→DuckDB 保存
- data/calendar_management.py: カレンダー管理・営業日判定ロジック
- data/quality.py: データ品質チェック
- data/audit.py: 監査ログ（signal/order_request/execution）初期化

---

## 運用上の注意点

- DuckDB のファイル（`DUCKDB_PATH`）はバックアップを検討してください。監査ログは消さない前提です。
- J-Quants のレート制限（120 req/min）を厳守するため、jquants_client の内部 RateLimiter が適切にスロットリングします。外側での並列リクエストは制限に注意してください。
- ニュース収集は外部 HTTP を多用するため、ネットワーク負荷や RSS ソース側のレート制限に配慮してください。
- 品質チェックで検出された QualityIssue をもとに運用ルール（自動停止・アラート）を設計してください（ETL は Fail-Fast にならない設計）。
- タイムゾーン: 監査ログでは UTC に固定しています。時刻の扱いに注意してください。

---

## 開発・テスト時のヒント

- 自動 .env 読み込みを無効にする:
  ```bash
  export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  ```
  テスト時に環境を汚染したくない場合に有用です。

- jquants_client のユニットテストではネットワーク呼び出しをモックしてください（_urlopen / urllib を差し替えられる箇所あり）。

---

## ライセンス / 貢献

本リポジトリのライセンスおよび貢献ルールはプロジェクトルートの LICENSE / CONTRIBUTING を参照してください（存在しない場合はプロジェクト管理者に問い合わせてください）。

---

以上。README の草案です。必要であれば次の点を追記します:
- 実際の requirements.txt（想定依存パッケージの明示）
- よくあるエラーと対処法
- CI / デプロイ手順（systemd / Docker / k8s 等の実行例）
- strategy / execution 層のサンプルコードやテンプレート

どれを追加しますか？