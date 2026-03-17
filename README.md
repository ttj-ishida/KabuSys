# KabuSys

日本株向け自動売買基盤（KabuSys）の軽量ライブラリです。  
データ取得・ETL、ニュース収集、データ品質チェック、DuckDB ベースのスキーマ定義、監査ログ等を提供します。

バージョン: 0.1.0

概要
- J-Quants や kabuステーション等の外部 API からデータを取得して DuckDB に保存するためのライブラリ群。
- データ層（Raw / Processed / Feature / Execution）に対応するスキーマを備え、ETL パイプライン、品質チェック、ニュース収集、監査ログを扱えます。
- 設計上の特徴：API レート制限の厳守、リトライ・トークン自動リフレッシュ、冪等性を意識した DB 書き込み、SSRF 対策や XML パースの安全化など。

主な機能一覧
- 環境設定管理（kabusys.config）
  - .env / .env.local を自動読み込み（プロジェクトルート検出）
  - 必須環境変数の取得と検証（KABUSYS_ENV / LOG_LEVEL 等）
  - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD=1
- J-Quants クライアント（kabusys.data.jquants_client）
  - 株価日足（OHLCV）、財務データ（四半期 BS/PL）、マーケットカレンダー取得
  - レートリミッタ、リトライ（指数バックオフ）、401 時の自動トークンリフレッシュ
  - DuckDB への冪等保存関数（ON CONFLICT ... DO UPDATE）
- ETL パイプライン（kabusys.data.pipeline）
  - 差分取得（最終取得日から必要分だけ再取得＋バックフィル）
  - 日次 ETL エントリ run_daily_etl()（カレンダー→価格→財務→品質チェック）
  - 品質チェック（kabusys.data.quality）との連携
- データ品質チェック（kabusys.data.quality）
  - 欠損（OHLC 欠損）、スパイク（前日比）、重複、日付不整合（未来日付／非営業日データ）検出
  - QualityIssue データ構造で検出結果を返却
- ニュース収集（kabusys.data.news_collector）
  - RSS フィード取得、テキスト前処理（URL 除去・空白正規化）、記事ID は正規化 URL の SHA-256（先頭32文字）
  - defusedxml を利用した安全な XML パース、SSRF 対策（リダイレクト検査／プライベート IP 拒否）
  - DuckDB への冪等保存（INSERT ... RETURNING）と銘柄コード抽出・紐付け
- スキーマ管理（kabusys.data.schema）
  - Raw / Processed / Feature / Execution / Audit 層の DuckDB DDL 定義と初期化
  - init_schema(db_path) でテーブル・インデックスを作成
- 監査ログ（kabusys.data.audit）
  - signal_events / order_requests / executions テーブルを提供し、発注〜約定のトレーサビリティを確保

セットアップ手順（開発向け）
前提
- Python 3.10 以上（typing における | や型注釈を使用しているため）
- DuckDB を使用（pip パッケージ）

1. リポジトリをクローン & 仮想環境作成
   - python -m venv .venv
   - source .venv/bin/activate  （Windows は .venv\Scripts\activate）

2. 依存パッケージをインストール
   - pip install duckdb defusedxml
   - （プロジェクト化されている場合は pip install -e . を推奨）

3. 環境変数の設定
   - プロジェクトルートに .env を作成（サンプル: .env.example を参考）
   - 最低必要な環境変数:
     - JQUANTS_REFRESH_TOKEN  （J-Quants のリフレッシュトークン）
     - KABU_API_PASSWORD      （kabuステーション API 用パスワード）
     - SLACK_BOT_TOKEN        （Slack 通知用 Bot トークン）
     - SLACK_CHANNEL_ID       （Slack チャンネルID）
   - オプション:
     - KABUSYS_ENV (development | paper_trading | live) 既定: development
     - LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL) 既定: INFO
     - DUCKDB_PATH（例: data/kabusys.duckdb）
     - SQLITE_PATH（例: data/monitoring.db）
   - 自動 .env ロードを無効にする場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

4. DuckDB スキーマ初期化
   - Python から:
     from kabusys.data.schema import init_schema
     from kabusys.config import settings
     conn = init_schema(settings.duckdb_path)

使い方（コード例）
- 設定にアクセスする
  from kabusys.config import settings
  print(settings.duckdb_path, settings.env)

- DB の初期化
  from kabusys.data.schema import init_schema
  conn = init_schema("data/kabusys.duckdb")

- 日次 ETL の実行
  from kabusys.data.pipeline import run_daily_etl
  result = run_daily_etl(conn)  # 戻り値は ETLResult オブジェクト
  print(result.to_dict())

- ニュース収集ジョブを実行して保存
  from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
  # known_codes は有効な銘柄コードのセット（例: {"7203","6758", ...}）
  stats = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=set())
  print(stats)

- J-Quants API を直接利用
  from kabusys.data.jquants_client import fetch_daily_quotes, get_id_token
  token = get_id_token()  # settings.jquants_refresh_token を用いて取得
  recs = fetch_daily_quotes(id_token=token, date_from=date(2024,1,1), date_to=date.today())

主な公開 API（抜粋）
- kabusys.config.settings
  - settings.jquants_refresh_token, settings.kabu_api_password, settings.duckdb_path など
- kabusys.data.schema.init_schema(db_path)
- kabusys.data.jquants_client.fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
- kabusys.data.jquants_client.save_daily_quotes / save_financial_statements / save_market_calendar
- kabusys.data.pipeline.run_daily_etl
- kabusys.data.news_collector.fetch_rss / save_raw_news / run_news_collection
- kabusys.data.quality.run_all_checks

設計上の注意点・セキュリティ留意点
- J-Quants のレート制限（120 req/min）を守るために固定間隔スロットリングを実装しています。
- HTTP エラー（408/429/5xx）に対するリトライ、401 受信時はトークン自動リフレッシュ（1 回）を行います。
- DuckDB への書き込みは冪等性を意識（ON CONFLICT DO UPDATE / DO NOTHING）しています。
- ニュース収集は defusedxml による安全な XML パース、SSRF 対策（リダイレクト検査、プライベート IP 拒否）、取得サイズ制限（最大 10 MB）等を備えています。
- すべての監査タイムスタンプは UTC で取り扱うことを想定しています（audit.init_audit_schema は SET TimeZone='UTC' を行います）。

ディレクトリ構成（概要）
- src/kabusys/
  - __init__.py
  - config.py               # 環境変数 / 設定管理
  - data/
    - __init__.py
    - jquants_client.py     # J-Quants API クライアント（取得・保存）
    - news_collector.py     # RSS ニュース収集
    - schema.py             # DuckDB スキーマ定義・初期化
    - pipeline.py           # ETL パイプライン（差分取得・日次 ETL）
    - calendar_management.py# マーケットカレンダー更新・営業日判定
    - audit.py              # 監査ログ（signal/order/execution）
    - quality.py            # データ品質チェック
  - strategy/                # 戦略関連（拡張ポイント）
    - __init__.py
  - execution/               # 発注・実行関連（拡張ポイント）
    - __init__.py
  - monitoring/              # 監視モジュール（拡張ポイント）
    - __init__.py

拡張ポイント・開発ガイド
- strategy, execution, monitoring パッケージは未実装の拡張ポイントです。戦略ロジックやブローカー連携（kabuステーション API）をここに実装してください。
- テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して .env 自動読み込みを無効化し、テスト用に意図的に環境変数を注入してください。
- ETL やニュース収集の関数は、id_token や HTTP 呼び出し時のオープン関数を注入・モックできるよう設計されています（ユニットテストを書きやすくなっています）。

ライセンス / 貢献
- 本 README ではライセンスファイルを同梱していません。実際のプロジェクトでは LICENSE を追加してください。
- バグ報告・機能提案は Issue を通じてお願いします。

以上。必要であれば、README に含める .env.example のテンプレートや具体的な CI/CD / デプロイ手順、より詳細なサンプルスクリプトを追記します。どの情報を追加しますか？