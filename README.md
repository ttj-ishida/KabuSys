KabuSys
=======

日本株向けの自動売買 / データ基盤ライブラリ（部分実装）。  
DuckDB をデータレイクとして用い、J-Quants API／RSS 等からデータを取得して加工し、戦略用の特徴量作成・シグナル生成までを行うモジュール群を含みます。

なお本リポジトリはライブラリ本体の一部（strategy / data / research / execution 等）を提供する実装であり、実際の運用では外部設定・認証情報・ブローカー連携・監視基盤を組み合わせて使用します。

主な機能
--------

- データ取得・永続化（J-Quants API クライアント）
  - 株価日足、財務データ、JPX カレンダーのページネーション対応取得
  - レート制限、リトライ、トークン自動リフレッシュを備えた堅牢な HTTP 層
- DuckDB ベースのスキーマ定義・初期化（冪等）
  - Raw / Processed / Feature / Execution 層のテーブルを定義
- ETL パイプライン
  - 差分取得（最終取得日を確認して差分を取る）、バックフィル、品質チェック統合
  - 日次 ETL 実行エントリポイント（run_daily_etl）
- ニュース収集（RSS）
  - RSS 取得・XML パース（defusedxml）・前処理・記事ID生成（URL 正規化 + SHA256）
  - 銘柄コード抽出・news テーブルへの冪等保存
  - SSRF / 大容量レスポンス / Gzip bomb などへの防御ロジック
- 特徴量計算（research）
  - Momentum / Volatility / Value 等のファクター計算（prices_daily / raw_financials を参照）
  - クロスセクション Z スコア正規化ユーティリティ
- 戦略層（strategy）
  - features テーブルを構築する build_features()
  - features と ai_scores を統合して最終スコアを算出し signals テーブルを生成する generate_signals()
  - SELL（エグジット）ロジック（ストップロス等）を実装
- マーケットカレンダー管理（営業日判定 / next/prev / update ジョブ）
- 監査ログ（audit）用テーブル定義（signal_events / order_requests / executions 等）

動作環境・依存
---------------

- Python >= 3.10（型注釈に | を使用しているため）
- 必要な主要ライブラリ（例）
  - duckdb
  - defusedxml
- 標準ライブラリの urllib / datetime / logging 等を多用

インストール（開発環境の例）
------------------

1. Python 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール（例）
   - pip install duckdb defusedxml

3. （ローカルでパッケージ化している場合）editable install
   - pip install -e .

設定（環境変数）
----------------

設定は .env または環境変数から読み込まれます。プロジェクトルート（.git または pyproject.toml を検出）を基準に .env/.env.local を自動ロードします。テスト等で自動ロードを無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

主要な環境変数（README 用サンプル）
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション等の API パスワード（必須）
- KABU_API_BASE_URL: kabu API の base URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN: Slack 通知用 Bot トークン（必須）
- SLACK_CHANNEL_ID: Slack チャンネル ID（必須）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV: 実行環境 ("development" | "paper_trading" | "live"), default "development"
- LOG_LEVEL: ログレベル ("DEBUG","INFO",...)

例 (.env)
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here
KABU_API_PASSWORD=your_kabu_api_password_here
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

セットアップ手順（DB 初期化等）
------------------------------

1. DuckDB スキーマ初期化
   - Python で以下を実行（デフォルトのパスを使う場合）
     from kabusys.config import settings
     from kabusys.data.schema import init_schema
     conn = init_schema(settings.duckdb_path)
   - またはメモリ DB で試す:
     from kabusys.data.schema import init_schema
     conn = init_schema(":memory:")

2. （任意）既存 DB に接続
   - from kabusys.data.schema import get_connection
     conn = get_connection("data/kabusys.duckdb")

基本的な使い方（コード例）
-------------------------

- 日次 ETL の実行（市場カレンダー・株価・財務・品質チェック）
  from datetime import date
  from kabusys.config import settings
  from kabusys.data.schema import init_schema
  from kabusys.data.pipeline import run_daily_etl

  conn = init_schema(settings.duckdb_path)
  result = run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())

- features（特徴量）構築
  from datetime import date
  from kabusys.config import settings
  from kabusys.data.schema import get_connection
  from kabusys.strategy import build_features

  conn = get_connection(settings.duckdb_path)
  n = build_features(conn, target_date=date(2025, 1, 31))
  print(f"upserted features: {n}")

- シグナル生成
  from datetime import date
  from kabusys.config import settings
  from kabusys.data.schema import get_connection
  from kabusys.strategy import generate_signals

  conn = get_connection(settings.duckdb_path)
  total = generate_signals(conn, target_date=date(2025, 1, 31))
  print(f"signals written: {total}")

- ニュース収集ジョブ
  from kabusys.config import settings
  from kabusys.data.schema import get_connection
  from kabusys.data.news_collector import run_news_collection

  conn = get_connection(settings.duckdb_path)
  known_codes = {"7203","6758", ...}  # 事前に把握している有効銘柄コード集合
  results = run_news_collection(conn, known_codes=known_codes)
  print(results)

- カレンダー更新ジョブ（夜間バッチ）
  from kabusys.data.calendar_management import calendar_update_job
  saved = calendar_update_job(conn)
  print(f"calendar saved: {saved}")

補足: run_daily_etl は内部で calendar_etl → prices_etl → financials_etl → 品質チェック の順で実行します。ETL は各ステップで独立して例外を捕捉し、結果オブジェクトにエラー情報を格納します。

設計上の注意点
--------------

- ルックアヘッドバイアス対策
  - 各モジュールは target_date 時点で利用可能なデータのみを参照する設計になっています（fetched_at の記録等も行っています）。
- 冪等性
  - raw データの保存関数は ON CONFLICT / DO UPDATE や INSERT ... DO NOTHING を使い冪等性を担保します。
- ネットワーク安全性
  - RSS 取得は SSRF 対策、受信サイズ制限、defusedxml による XML パースを行っています。
- ログ・モード
  - KABUSYS_ENV と LOG_LEVEL によって実行モード・ログレベルを制御します。
- 実運用ではブローカー API（kabu ステーション等）・Slack 通知・ジョブスケジューラ（cron / Airflow / etc.）等を組み合わせて使用してください。

ディレクトリ構成（主要ファイル）
--------------------------------

src/kabusys/
- __init__.py
- config.py                      - 環境変数 / 設定管理
- data/
  - __init__.py
  - jquants_client.py            - J-Quants API クライアント + 保存ユーティリティ
  - news_collector.py            - RSS 収集・保存
  - schema.py                    - DuckDB スキーマ定義・初期化
  - stats.py                     - 統計ユーティリティ（zscore_normalize 等）
  - pipeline.py                  - ETL パイプライン（run_daily_etl 等）
  - calendar_management.py       - マーケットカレンダー管理
  - audit.py                     - 監査ログテーブル定義
  - features.py                  - data.stats の公開ラッパ
- research/
  - __init__.py
  - factor_research.py           - Momentum/Volatility/Value の計算
  - feature_exploration.py       - IC / forward returns / summary 等
- strategy/
  - __init__.py
  - feature_engineering.py       - features 作成（build_features）
  - signal_generator.py          - signals 作成（generate_signals）
- execution/                      - 発注 / execution 層（空 shell ファイルあり）
- monitoring/                     - 監視関連（未実装/補完想定）

ドキュメント参照
----------------

コード中に参照される設計ドキュメント（例: StrategyModel.md, DataPlatform.md, DataSchema.md）に仕様の根拠や詳細なアルゴリズム説明があります。実運用ではそれらドキュメントに従い設定・パラメータ調整を行ってください。

貢献と拡張案
--------------

- 品質チェックモジュールの実装（quality）
- AI スコア生成パイプライン（ai_scores の算出）
- 発注層（execution）とブローカー API 連携（kabuステーション等）の実装
- モニタリング・アラート（Slack 通知の実装）
- 単体テスト・統合テストの整備

ライセンス
----------

（ここにプロジェクトのライセンスを明記してください）

最後に
------

この README はコードベースの現状実装をもとに作成しました。実行前に .env の各種キーを正しく設定し、DuckDB の初期化を行ってください。運用環境での実行は十分な検証とリスク管理（バックテスト・ポジション管理の検証）を行ってから行ってください。