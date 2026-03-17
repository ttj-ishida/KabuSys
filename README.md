# KabuSys

日本株向けの自動売買・データ基盤ライブラリ（試作版）

バージョン: 0.1.0

概要:
- KabuSys は日本株のデータ収集（J-Quants を利用）、データ品質チェック、ニュース収集、DB スキーマ管理、監査ログなどを備えたデータ基盤／自動売買補助ライブラリです。
- DuckDB をデータストアとして利用し、ETL パイプラインやマーケットカレンダー管理、ニュースの RSS 収集、監査ログ用スキーマなどを提供します。
- 設計上の注力点：API レート制御・リトライ、冪等性（ON CONFLICT）、Look-ahead バイアス対策（fetched_at の記録）、SSRF 対策、トランザクションによる安全な DB 書き込み。

主な機能一覧
- J-Quants API クライアント
  - 株価日足（OHLCV）取得（ページネーション対応、トークン自動リフレッシュ）
  - 財務データ（四半期 BS/PL）取得
  - JPX マーケットカレンダー取得
  - API レート制限（120 req/min）を尊重する内部 RateLimiter、リトライ・バックオフ実装
- DuckDB スキーマ管理
  - Raw / Processed / Feature / Execution / Audit 層のテーブル定義と初期化関数
  - インデックス作成、監査ログ用の専用初期化
- ETL パイプライン
  - 差分更新（最終取得日から未取得分のみ取得／backfill 対応）
  - 市場カレンダー先読み（lookahead）
  - 品質チェックの呼び出し（欠損、重複、スパイク、日付不整合など）
- ニュース収集モジュール
  - RSS フィード取得（gzip 対応）、記事正規化、URL トラッキング除去、記事IDは正規化URLのSHA-256先頭32文字
  - SSRF 対策、XML パースは defusedxml を使用
  - raw_news / news_symbols テーブルへの冪等保存（トランザクション、チャンク挿入）
- マーケットカレンダー管理
  - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day のユーティリティ
  - 夜間バッチでのカレンダー差分更新ジョブ
- 監査ログ（audit）
  - signal_events / order_requests / executions の監査テーブル定義と初期化
  - 発注・約定のトレーサビリティをサポート

セットアップ手順（開発環境向け・最小）
1. Python（3.10+ を想定）を用意
2. 仮想環境作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）
3. 依存パッケージをインストール
   - pip install duckdb defusedxml
   - （パッケージ化されている場合）pip install -e .
   - （requirements.txt がある場合）pip install -r requirements.txt
   - 注: 実運用では jquants の認証手続きや kabuステーション との接続に必要な追加パッケージや SDK を用意してください。
4. 環境変数の設定
   - 必須:
     - JQUANTS_REFRESH_TOKEN : J-Quants リフレッシュトークン
     - KABU_API_PASSWORD     : kabu API 用パスワード
     - SLACK_BOT_TOKEN       : Slack 通知用 Bot トークン
     - SLACK_CHANNEL_ID      : 通知先 Slack チャンネル ID
   - 任意（デフォルトあり）:
     - KABUSYS_ENV (development | paper_trading | live) - default: development
     - LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL) - default: INFO
     - DUCKDB_PATH - デフォルト "data/kabusys.duckdb"
     - SQLITE_PATH - デフォルト "data/monitoring.db"
   - .env 自動読み込み:
     - プロジェクトルート（.git または pyproject.toml を基準）にある `.env` と `.env.local` を自動で読み込みます。
     - 自動読み込みを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
   - サンプル（.env）:
     - JQUANTS_REFRESH_TOKEN=your_refresh_token
     - KABU_API_PASSWORD=your_password
     - SLACK_BOT_TOKEN=xoxb-...
     - SLACK_CHANNEL_ID=C12345678
     - DUCKDB_PATH=data/kabusys.duckdb
     - KABUSYS_ENV=development

使い方（簡易ガイド / Python からの利用例）
- DB スキーマ初期化（DuckDB）
  - from kabusys.data import schema
  - conn = schema.init_schema("data/kabusys.duckdb")
  - これにより必要な全テーブルとインデックスが作成されます。

- 日次 ETL 実行（株価・財務・カレンダー・品質チェック）
  - from datetime import date
    from kabusys.data.pipeline import run_daily_etl
    from kabusys.data import schema
    conn = schema.init_schema("data/kabusys.duckdb")
    result = run_daily_etl(conn, target_date=date.today())
    print(result.to_dict())
  - run_daily_etl は内部で J-Quants クライアントを使いデータ取得して保存します。取得トークンは設定された環境変数から参照されます。

- ニュース収集ジョブ
  - from kabusys.data.news_collector import run_news_collection
    from kabusys.data import schema
    conn = schema.init_schema("data/kabusys.duckdb")
    known_codes = {"7203", "6758", "9984"}  # 事前に用意した有効銘柄コードセット
    results = run_news_collection(conn, known_codes=known_codes)
    print(results)
  - fetch_rss / save_raw_news / save_news_symbols といった低レイヤ API も利用可能です。

- J-Quants API の直接利用
  - from kabusys.data import jquants_client as jq
    id_token = jq.get_id_token()  # settings の refresh token を使用
    quotes = jq.fetch_daily_quotes(id_token=id_token, date_from=..., date_to=...)
    jq.save_daily_quotes(conn, quotes)

- 監査ログの初期化（監査専用 DB を分離する場合）
  - from kabusys.data.audit import init_audit_db
    audit_conn = init_audit_db("data/audit.duckdb")

注意点 / 設計上のポイント
- API レート制御: J-Quants の上限 120 req/min に合わせた内部 RateLimiter があり、pageinate などの連続リクエストでも遵守するようになっています。
- リトライ / トークン更新: HTTP 408/429/5xx 系は指数バックオフで再試行。401 受信時はリフレッシュトークンから id_token を自動取得して 1 回だけ再試行します。
- 冪等性: raw データの保存は ON CONFLICT DO UPDATE / DO NOTHING を使い重複挿入を排除します。
- Look-ahead バイアス対策: 生データ保存時に fetched_at（UTC）を記録し、「いつシステムがそのデータを知り得たか」を記録します。
- セキュリティ: ニュース収集では defusedxml を使った XML パース、SSRF 対策（リダイレクト検査・プライベート IP 拒否）、レスポンスサイズ上限を設ける等の対策があります。
- 品質チェック: ETL 後に run_all_checks を呼ぶことで欠損・重複・スパイク・日付不整合を検出できます。重大度に応じた対処は呼び出し側で実装してください。

ディレクトリ構成（主なファイル/モジュール）
- src/kabusys/
  - __init__.py                （パッケージ定義、バージョン）
  - config.py                  （環境変数・設定読み込みロジック）
  - data/
    - __init__.py
    - jquants_client.py        （J-Quants API クライアント、保存ロジック）
    - news_collector.py        （RSS ニュース収集、保存、銘柄抽出）
    - pipeline.py              （ETL パイプライン、差分更新、日次ジョブ）
    - schema.py                （DuckDB スキーマ定義・初期化）
    - calendar_management.py   （マーケットカレンダー管理）
    - audit.py                 （監査ログ定義・初期化）
    - quality.py               （データ品質チェック）
  - strategy/
    - __init__.py              （戦略関連モジュールのエントリ）
  - execution/
    - __init__.py              （発注・実行管理関連のエントリ）
  - monitoring/
    - __init__.py              （監視・モニタリング関連のエントリ）

よくある運用フロー（例）
1. プロジェクトのセットアップ、環境変数 (.env) を配置
2. schema.init_schema() で DB 初期化
3. 毎日早朝に run_daily_etl() を実行してデータを更新
4. news_collector.run_news_collection() を定期実行して raw_news を集める（銘柄紐付けは既知コードで実施）
5. 品質チェック結果に応じてアラート（Slack 連携など）を出す
6. strategy / execution 層でシグナル生成 → order_requests を生成 → 監査ログ、発注管理を実施

トラブルシューティング
- 環境変数が足りない場合: config.Settings のプロパティ参照時に ValueError が発生します。必須項目を .env に設定してください。
- .env 自動読み込みを無効化したい場合:
  - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
- DuckDB ファイルのパスに親ディレクトリがない場合、schema.init_schema() が自動で作成します。

ライセンスや貢献
- このリポジトリにライセンスファイルが添付されている場合はそちらに従ってください。
- 追加の機能（戦略実装・ブローカー連携など）は strategy/ execution/ monitoring の下に実装してください。

以上が KabuSys の概要と基本的な使い方です。詳細な API（各関数の引数や返り値）は各モジュールの docstring を参照してください。必要があれば README に使い方のサンプルや実運用ガイド（cron / Docker / systemd 例）を追加します。どの部分を詳しく書いてほしいか教えてください。