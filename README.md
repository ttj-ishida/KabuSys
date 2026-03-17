# KabuSys

日本株向けの自動売買／データ基盤ライブラリです。J‑Quants や RSS 等から市場データ・ニュースを収集し、DuckDB に保存・整形して戦略・実行層へ提供することを目的としています。

## プロジェクト概要
- パッケージ名: kabusys
- 目的: J‑Quants API 等からのデータ収集（株価、財務、マーケットカレンダー、ニュース）およびその ETL、データ品質チェック、監査ログの管理を行うライブラリ。
- 設計方針の要点:
  - API レート制限・リトライ制御・トークン自動リフレッシュを備えた堅牢なクライアント実装
  - DuckDB を用いた三層（Raw / Processed / Feature）データ・スキーマ
  - ETL は差分更新（バックフィル対応）かつ冪等（ON CONFLICT）保存
  - ニュース収集は SSRF 対策・XML 脆弱性対策（defusedxml）・トラッキングパラメータ除去等の安全対策を実施
  - 品質チェック（欠損・重複・スパイク・日付不整合）を提供
  - 監査ログ（signal → order_request → execution）のスキーマと初期化機能

## 主な機能一覧
- J-Quants API クライアント
  - 株価日足（OHLCV）、四半期財務、マーケットカレンダーの取得
  - レートリミット（120 req/min）、リトライ（指数バックオフ）、401 時のトークン自動更新
  - 取得時刻（fetched_at）の記録、DuckDB への冪等保存
- ニュース収集
  - RSS フィードの取得・前処理（URL 除去、空白正規化）
  - 記事ID を正規化 URL の SHA256 先頭32文字で生成（冪等）
  - SSRF / XML Bomb / レスポンスサイズ制限などの安全対策
  - raw_news / news_symbols への保存（チャンク挿入、INSERT ... RETURNING を利用）
  - テキストからの銘柄コード抽出（既知銘柄セットに基づく）
- ETL パイプライン
  - 差分更新（最終取得日からのバックフィル）
  - prices / financials / calendar の個別 ETL と日次一括 ETL run_daily_etl
  - 品質チェックの実行（quality モジュール）
- カレンダー管理
  - market_calendar 更新ジョブ（夜間バッチ）
  - 営業日判定・前後営業日取得・期間の営業日リスト取得等
- データ品質チェック
  - 欠損データ、重複、株価スパイク、日付不整合の検出
  - QualityIssue オブジェクトで詳細を返す
- 監査ログ（audit）
  - signal_events / order_requests / executions 等の監査テーブル定義と初期化
  - すべての TIMESTAMP は UTC に統一

## セットアップ手順

前提
- Python 3.9+（型ヒントに | を使っているため 3.10 以上を想定している可能性がありますが、少なくとも 3.9+ を推奨）
- DuckDB を利用（Python パッケージ duckdb）
- defusedxml（RSS パース時に使用）

1. リポジトリをクローン／チェックアウト
   - 例: git clone <repo-url>

2. 仮想環境作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. パッケージと依存のインストール
   - pip install -e .            # setup.py / pyproject.toml がある前提で開発インストール
   - 必要パッケージ（明示的）:
     - pip install duckdb defusedxml

   （プロジェクトに requirements.txt / pyproject.toml があればそちらを利用してください）

4. 環境変数の設定
   - パッケージは起動時にプロジェクトルートの `.env` / `.env.local` を自動読み込みします（OS 環境変数が優先されます）。
   - 自動ロードを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

   必須の環境変数（最低限）
   - JQUANTS_REFRESH_TOKEN       — J‑Quants のリフレッシュトークン
   - KABU_API_PASSWORD           — kabu API パスワード（execution 周りで使用）
   - SLACK_BOT_TOKEN             — Slack 通知用トークン（通知機能を使う場合）
   - SLACK_CHANNEL_ID            — Slack チャネル ID

   任意 / 既定値あり
   - KABUSYS_ENV                 — development | paper_trading | live （既定: development）
   - LOG_LEVEL                   — DEBUG | INFO | WARNING | ... （既定: INFO）
   - KABU_API_BASE_URL           — kabu API のベース URL（既定: http://localhost:18080/kabusapi）
   - DUCKDB_PATH                 — DuckDB ファイルパス（既定: data/kabusys.duckdb）
   - SQLITE_PATH                 — 監視用 SQLite パス（既定: data/monitoring.db）

   .env（例）
   - .env:
     JQUANTS_REFRESH_TOKEN=xxxxx
     KABU_API_PASSWORD=your_kabu_password
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567
     KABUSYS_ENV=development
     LOG_LEVEL=INFO
     DUCKDB_PATH=data/kabusys.duckdb

5. DuckDB スキーマ初期化
   - Python REPL やスクリプトで実行:
     from kabusys.data.schema import init_schema
     from kabusys.config import settings
     conn = init_schema(settings.duckdb_path)
   - テストや一時利用では init_schema(":memory:") でインメモリ DB を作れます。

6. 監査ログテーブルの初期化（必要に応じて）
   - from kabusys.data.audit import init_audit_schema
     init_audit_schema(conn)

## 使い方（主要な API / 例）

基本的に関数群はモジュール単位で提供されています。以下はいくつかの典型的な利用例です。

- DuckDB スキーマの初期化
  - 例:
    from kabusys.data.schema import init_schema
    from kabusys.config import settings
    conn = init_schema(settings.duckdb_path)

- 日次 ETL の実行（株価・財務・カレンダーの差分取得 + 品質チェック）
  - 例:
    from datetime import date
    from kabusys.data.pipeline import run_daily_etl
    from kabusys.data.schema import init_schema
    from kabusys.config import settings

    conn = init_schema(settings.duckdb_path)
    result = run_daily_etl(conn, target_date=date.today())
    print(result.to_dict())

  - run_daily_etl は ETLResult を返し、取得件数・保存件数・品質問題やエラーの概要を含みます。

- 個別 ETL ジョブの実行
  - run_prices_etl / run_financials_etl / run_calendar_etl を直接呼ぶことも可能です（テストや部分更新用）。

- マーケットカレンダーの夜間更新ジョブ
  - 例:
    from kabusys.data.calendar_management import calendar_update_job
    saved = calendar_update_job(conn)

- ニュース収集ジョブ
  - ニュース収集を一括で実行する:
    from kabusys.data.news_collector import run_news_collection
    results = run_news_collection(conn, sources=None, known_codes=set(['7203','6758']), timeout=30)
    # results は {source_name: saved_count} の辞書

  - 単一 RSS フィードをフェッチする:
    from kabusys.data.news_collector import fetch_rss
    articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")

- J‑Quants クライアントを直接使う（テストやカスタム取得）
  - 例:
    from kabusys.data.jquants_client import fetch_daily_quotes, get_id_token
    token = get_id_token()  # settings.jquants_refresh_token を使用して取得
    recs = fetch_daily_quotes(id_token=token, date_from=date(2024,1,1), date_to=date(2024,1,31))

- 品質チェックを個別実行
  - 例:
    from kabusys.data.quality import run_all_checks
    issues = run_all_checks(conn, target_date=None)
    for i in issues:
        print(i)

- 設定の取得
  - from kabusys.config import settings
    settings.duckdb_path, settings.is_live などのプロパティで設定値を取得できます。
  - 自動 .env 読み込みの挙動:
    - プロジェクトルートを .git または pyproject.toml を基準に探索し、.env を読み込みます。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env
    - 環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 でオートロードを無効化可能

ログレベルや挙動は settings.log_level / settings.env を利用してアプリ側で制御してください。

## ディレクトリ構成

（主要ファイル抜粋）

- src/
  - kabusys/
    - __init__.py
    - config.py                -- 環境変数 / 設定管理（.env 自動読み込み、Settings クラス）
    - data/
      - __init__.py
      - jquants_client.py      -- J‑Quants API クライアント（レート制御・リトライ・保存）
      - news_collector.py      -- RSS 取得 / 前処理 / raw_news 保存 / 銘柄抽出
      - schema.py              -- DuckDB スキーマ定義・初期化
      - pipeline.py            -- ETL パイプライン（差分更新・日次 ETL）
      - calendar_management.py -- カレンダー管理・営業日判定・更新ジョブ
      - audit.py               -- 監査ログテーブル定義・初期化
      - quality.py             -- データ品質チェック
    - strategy/
      - __init__.py            -- 戦略層（拡張ポイント）
    - execution/
      - __init__.py            -- 発注 / 実行層（拡張ポイント）
    - monitoring/
      - __init__.py            -- 監視用モジュール（拡張ポイント）

README に記載のないが重要な実装ノート
- J‑Quants API: レート制限 120 req/min を固定間隔スロットリングで守ります。
- リトライ: 408 / 429 / 5xx に対して指数バックオフで最大3回リトライ。429 の場合は Retry-After ヘッダを尊重。
- トークン: 401 受信時には refresh token から id_token を自動再取得して 1 回リトライします。
- ニュース: XML パースに defusedxml を使用して XML Bomb 等を防止。レスポンスサイズは MAX_RESPONSE_BYTES (10MB) で制限。

## 開発・運用上の注意
- DuckDB ファイルは既定で data/kabusys.duckdb に作成されます。バックアップやアクセス制御を適切に行ってください。
- 監査ログ（audit）は削除しない前提の設計です。運用時にディスク容量やローテーション方針を検討してください。
- KABUSYS_ENV による挙動切替（development / paper_trading / live）を利用して、本番とテスト環境を分離してください。
- 外部 API の認証情報は必ず安全に管理し、リポジトリに直書きしないでください。

---

必要であれば以下を追加で作成できます
- 例となる .env.example ファイル
- 起動用 CLI スクリプト（ETL の定期実行や calendar_update_job を呼ぶエントリポイント）
- Unit tests / CI ワークフローのドキュメント

ご希望があれば README にサンプル .env.example や CLI の利用例、systemd / cron / Airflow の運用サンプルなども追記します。