KabuSys
======

日本株向けの自動売買 / データプラットフォーム用ライブラリ（パッケージ化された内部モジュール群）の README です。本リポジトリはデータ収集（J-Quants / RSS）、ETL パイプライン、データ品質チェック、マーケットカレンダー管理、監査ログなどの基盤機能を提供します。

主な用途
- J-Quants API から株価・財務・マーケットカレンダーを取得して DuckDB に保存
- RSS を収集してニュースを保存・銘柄紐付け
- 日次 ETL パイプライン（差分取得・バックフィル・品質チェック）
- マーケットカレンダーの判定・探索ユーティリティ（営業日/前後営業日取得など）
- 監査ログ（シグナル→発注→約定のトレーサビリティ）用スキーマ初期化
- データ品質チェック（欠損・重複・スパイク・日付不整合）

機能一覧
- 環境変数/設定管理（kabusys.config）
  - .env / .env.local を自動ロード（オーバーライドの挙動あり）
  - 必須環境変数をプロパティ経由で取得（例: settings.jquants_refresh_token）
  - KABUSYS_ENV（development / paper_trading / live）、LOG_LEVEL の検証
- J-Quants API クライアント（kabusys.data.jquants_client）
  - 株価（日足）、財務（四半期）、マーケットカレンダーの取得
  - レート制限（120 req/min）の管理、リトライ（指数バックオフ）、401 自動リフレッシュ
  - DuckDB へ冪等保存（ON CONFLICT DO UPDATE）
- ニュース収集（kabusys.data.news_collector）
  - RSS フィード取得（gzip 対応）、XML の安全パース（defusedxml）
  - URL 正規化（トラッキングパラメータ除去）、記事ID は正規化 URL の SHA-256 先頭 32 文字
  - SSRF 対策（スキーム検証・プライベートアドレス拒否）、受信サイズ制限
  - DuckDB へのバルク保存（INSERT ... RETURNING）と銘柄紐付け
- DuckDB スキーマ管理（kabusys.data.schema）
  - Raw / Processed / Feature / Execution / Audit 層のテーブル DDL を定義
  - init_schema() による初期化（冪等）
- ETL パイプライン（kabusys.data.pipeline）
  - 日次 ETL（run_daily_etl）：カレンダー → 株価 → 財務 → 品質チェック（オプション）
  - 差分更新とバックフィル、品質チェック集約、ETLResult に結果を格納
- マーケットカレンダー管理（kabusys.data.calendar_management）
  - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day
  - calendar_update_job による夜間バッチ更新
- 監査ログスキーマ（kabusys.data.audit）
  - signal_events / order_requests / executions の DDL とインデックス、init 関数
- データ品質チェック（kabusys.data.quality）
  - 欠損、重複、スパイク（前日比）、日付整合性を検出し QualityIssue リストを返す

要件
- Python 3.10 以上（PEP 604 のユニオン型などを使用）
- 推奨パッケージ（少なくとも以下をインストールしてください）:
  - duckdb
  - defusedxml
  - （標準ライブラリ以外の HTTP/依存が必要なら各自追加）

セットアップ手順（開発環境向け）
1. リポジトリをクローンして作業ディレクトリへ移動
2. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）
3. 必要パッケージをインストール
   - pip install duckdb defusedxml
   - （プロジェクトに requirements.txt / pyproject.toml がない場合は上記を手動で）
4. 開発時にパッケージとして使う場合:
   - pip install -e .

環境変数（主要）
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API のパスワード（必須）
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN: Slack ボットトークン（必須）
- SLACK_CHANNEL_ID: Slack チャンネル ID（必須）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: SQLite（モニタリング等）ファイルパス（デフォルト: data/monitoring.db）
- KABUSYS_ENV: environment（development / paper_trading / live）（デフォルト: development）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）

.env 自動ロードの挙動
- パッケージはプロジェクトルートを .git または pyproject.toml を基準に探索し、見つかれば .env → .env.local の順に読み込みます。
- 読み込みの優先順位: OS 環境変数 > .env.local > .env
- 自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト等で利用）。

使い方（簡単な例）
- DuckDB スキーマを初期化する
  - Python スクリプトや対話セッションで:
    - from kabusys.data import schema
    - conn = schema.init_schema("data/kabusys.duckdb")
- 日次 ETL を実行する
  - from datetime import date
    from kabusys.data import pipeline, schema
    conn = schema.init_schema("data/kabusys.duckdb")
    result = pipeline.run_daily_etl(conn, target_date=date.today())
    print(result.to_dict())
- RSS（ニュース）収集
  - from kabusys.data import news_collector, schema
    conn = schema.get_connection("data/kabusys.duckdb")  # 既存 DB へ接続
    articles = news_collector.fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
    new_ids = news_collector.save_raw_news(conn, articles)
- カレンダー夜間更新ジョブ
  - from kabusys.data import calendar_management, schema
    conn = schema.init_schema("data/kabusys.duckdb")
    saved = calendar_management.calendar_update_job(conn)
- 監査 DB 初期化（監査専用 DB を分ける場合）
  - from kabusys.data import audit
    conn = audit.init_audit_db("data/kabusys_audit.duckdb")

注意点 / 実装上の特徴
- J-Quants クライアントは API レート制限（120 req/min）を守るため固定間隔のスロットリングを行います。
- HTTP リトライは指数バックオフで最大 3 回。401 を受けた場合は refresh token でトークンを再取得して 1 回リトライします。
- NewsCollector は XML の安全なパース（defusedxml）と SSRF 対策、受信サイズ制限（10MB）を実装しています。
- DuckDB への書き込みはできる限り冪等（ON CONFLICT）にしています。
- 日付処理やマーケットカレンダーは DB の有無に応じてフォールバック（一部は曜日ベース）します。

ディレクトリ構成
- src/kabusys/
  - __init__.py
  - config.py               — 環境変数・設定管理
  - data/
    - __init__.py
    - jquants_client.py     — J-Quants API クライアント（fetch/save）
    - news_collector.py     — RSS ニュース収集・保存・銘柄抽出
    - schema.py             — DuckDB スキーマ定義・初期化
    - pipeline.py           — ETL パイプライン（run_daily_etl 等）
    - calendar_management.py— マーケットカレンダー管理（is_trading_day など）
    - audit.py              — 監査ログスキーマ（signal/order/execution）
    - quality.py            — データ品質チェック（欠損/スパイク/重複/日付整合性）
  - execution/               — 発注・実行モジュールのためのパッケージ（現状 __init__ のみ）
  - strategy/                — 戦略実装モジュールのためのパッケージ（現状 __init__ のみ）
  - monitoring/              — 監視・アラート関連（現状 __init__ のみ）

開発メモ / 注意事項
- Python 型ヒントに最新の構文を使用しているため Python 3.10 以上を推奨します。
- 実行環境では J-Quants の利用規約や証券会社 API（kabuステーション等）のテスト/実取引の設定に注意して下さい。live 環境での不注意な発注を避けるため、KABUSYS_ENV を適切に設定してください。
- ロギングは各モジュールで行っています。運用時は logging.basicConfig や structlog 等で出力先・形式を設定してください。
- ユニットテストや CI においては KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると .env の自動読み込みを無効化できます（テスト用に独自の環境を注入するため）。

問い合わせ / 貢献
- 本 README は内部向けのドキュメントとして提供しています。バグ修正・機能追加はプルリクエストでお願いします。重要な設計方針（冪等性・トレーサビリティ・SSRF 対策・データ品質重視）を尊重してください。

以上。必要であれば README にサンプル .env.example、CLI スクリプト例、詳細な API リファレンス（関数一覧・引数の説明）、運用手順（Cron/バッチの推奨）を追加できます。どの情報を優先して追記しますか？