KabuSys
=======

日本株向けの自動売買プラットフォーム用ライブラリ（KabuSys）のリポジトリ内ドキュメントです。  
本 README はコードベース（src/kabusys 以下）を元に、プロジェクト概要、機能、セットアップ手順、基本的な使い方、ディレクトリ構成を日本語でまとめています。

プロジェクト概要
---------------
KabuSys は日本株のデータ取得（J-Quants）、ETL、特徴量作成、シグナル生成、ニュース収集、マーケットカレンダー管理、発注/監査などを想定したモジュール群を提供するライブラリです。  
設計上のポイント：

- DuckDB を用いたローカル DB スキーマ（Raw / Processed / Feature / Execution 層）を備える
- J-Quants API クライアント（レート制御・リトライ・トークン自動リフレッシュ）
- ETL パイプラインで差分更新（バックフィル考慮）と品質チェック
- 研究（research）用のファクター計算・解析ユーティリティ
- 戦略層での特徴量合成（Zスコア正規化等）およびシグナル生成（BUY/SELL）
- ニュース収集（RSS）と銘柄紐付け（安全対策付き）
- 自動環境変数読み込み (.env / .env.local)、設定は kabusys.config.Settings 経由で取得

主要機能一覧
--------------
- データ取得・保存
  - J-Quants API クライアント: fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
  - DuckDB へ生データを冪等に保存する save_* 関数
- DB スキーマ管理
  - init_schema(db_path) による DuckDB スキーマ初期化（テーブル・インデックス）
- ETL / パイプライン
  - run_daily_etl: カレンダー→株価→財務の差分 ETL + 品質チェック
  - run_prices_etl / run_financials_etl / run_calendar_etl の個別実行
- 研究（research）
  - calc_momentum / calc_volatility / calc_value：ファクター計算
  - calc_forward_returns / calc_ic / factor_summary / rank：特徴量探索用ユーティリティ
- 特徴量作成 / 戦略
  - build_features(conn, target_date)：features テーブルへ正規化済み特徴量を保存
  - generate_signals(conn, target_date, ...)：features + ai_scores を使って BUY/SELL シグナル生成し signals テーブルへ保存
- ニュース収集
  - fetch_rss / save_raw_news / run_news_collection：RSS 収集から raw_news / news_symbols 保存まで
  - テキスト前処理、SSRF/サイズ上限対策、URL 正規化、銘柄コード抽出
- カレンダー管理
  - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / calendar_update_job
- 統計ユーティリティ
  - zscore_normalize（クロスセクション Z スコア正規化）

セットアップ手順
----------------

1. Python 環境の作成（推奨: venv）
   - Unix/macOS:
     python3 -m venv .venv
     source .venv/bin/activate
   - Windows (PowerShell):
     python -m venv .venv
     .\.venv\Scripts\Activate.ps1

2. 依存パッケージのインストール（本リポジトリに requirements.txt が無い場合の推奨）
   pip install duckdb defusedxml

   （必要に応じてロギングなどの追加パッケージをインストールしてください。）

3. 開発インストール（任意）
   pip install -e .

4. 環境変数 / .env の用意
   - プロジェクトルート（.git または pyproject.toml のあるディレクトリ）に .env を置くと自動で読み込まれます。
   - 自動読み込みを無効にする場合:
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

   必須の環境変数（Settings が要求するもの）
   - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン
   - KABU_API_PASSWORD     : kabuステーション API パスワード（発注等で使用）
   - SLACK_BOT_TOKEN       : Slack 通知用 Bot トークン
   - SLACK_CHANNEL_ID      : Slack チャンネル ID

   任意 / デフォルト値あり
   - KABUSYS_ENV : development / paper_trading / live（デフォルト development）
   - LOG_LEVEL : DEBUG/INFO/...（デフォルト INFO）
   - KABU_API_BASE_URL : kabu API のベース URL（デフォルト http://localhost:18080/kabusapi）
   - DUCKDB_PATH : DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
   - SQLITE_PATH : 監視用 SQLite（デフォルト data/monitoring.db）

   サンプル .env（.env.example を参考に作成してください）
   JQUANTS_REFRESH_TOKEN=your_refresh_token_here
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567

基本的な使い方（サンプル）
------------------------

以下は簡単な Python スニペット例です。実運用の前に必ずテスト環境で動作確認してください。

1) DuckDB スキーマ初期化
   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")  # ディレクトリを自動作成して初期化
   # :memory: も指定可能

2) 日次 ETL を実行
   from kabusys.data.pipeline import run_daily_etl
   result = run_daily_etl(conn)  # 今日を対象に ETL を実行
   print(result.to_dict())

3) 特徴量作成（features テーブルへ保存）
   from kabusys.strategy import build_features
   from datetime import date
   cnt = build_features(conn, target_date=date(2025, 1, 15))
   print(f"features upserted: {cnt}")

4) シグナル生成
   from kabusys.strategy import generate_signals
   from datetime import date
   total = generate_signals(conn, target_date=date(2025, 1, 15))
   print(f"signals written: {total}")

   - weights をカスタマイズして重み付けを変更可能（辞書）。合計は自動スケールされます。
   - threshold を指定して BUY 閾値を調整できます。

5) ニュース収集ジョブ
   from kabusys.data.news_collector import run_news_collection
   results = run_news_collection(conn, known_codes={"7203","6758"})  # known_codes を渡すと銘柄紐付けを実施
   print(results)

6) カレンダー更新バッチ
   from kabusys.data.calendar_management import calendar_update_job
   saved = calendar_update_job(conn)
   print(f"calendar saved: {saved}")

設定（kabusys.config.Settings）
------------------------------
設定は環境変数から読み込まれ、kabusys.config.settings 経由でアクセスします。自動で .env / .env.local をプロジェクトルートから読み込みます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。必須キーが未設定の場合は ValueError が発生します。

注意点（設計上の重要事項）
-------------------------
- DuckDB への書き込みは多くの箇所でトランザクションを使用して原子性を確保しています（BEGIN / COMMIT / ROLLBACK）。
- J-Quants API 呼び出しはレート制御・リトライ・トークン自動更新を内包しており、ページネーションに対応しています。
- ニュース収集には SSRF 対策、レスポンスサイズ上限、gzip 解凍後の再検査などの安全対策が実装されています。
- 研究用モジュール（research）やデータ統計ユーティリティは外部ライブラリに依存せず標準ライブラリのみで実装されています（ただし DuckDB は必須）。
- 実際の発注・execution 層は本リポジトリの抽象設計に従っており、実際のブローカー連携を行う場合は execution 層の実装／接続が必要です。

ディレクトリ構成
----------------
以下は主要ファイル・モジュールの概観（src/kabusys 以下）。実際のリポジトリにはさらにファイルやテスト等が存在する可能性があります。

- src/kabusys/
  - __init__.py
  - config.py              # 環境変数 / 設定管理
  - data/
    - __init__.py
    - jquants_client.py    # J-Quants API クライアント + 保存ユーティリティ
    - news_collector.py    # RSS 収集・前処理・保存
    - schema.py            # DuckDB スキーマ定義と init_schema
    - stats.py             # 統計ユーティリティ（zscore_normalize）
    - pipeline.py          # ETL パイプライン（run_daily_etl 等）
    - features.py          # data レイヤの再エクスポート（zscore_normalize）
    - calendar_management.py # 市場カレンダー管理
    - audit.py             # 監査ログ用 DDL / 初期化
    - (その他: quality, etc. が想定される)
  - research/
    - __init__.py
    - factor_research.py   # calc_momentum / calc_value / calc_volatility
    - feature_exploration.py # forward returns / IC / summary / rank
  - strategy/
    - __init__.py
    - feature_engineering.py # build_features
    - signal_generator.py    # generate_signals
  - execution/              # 発注 / execution 層（インターフェース用）
    - __init__.py
  - monitoring/             # 監視 / Slack 通知等（概念あり）
    - __init__.py

補足・運用メモ
--------------
- 本ライブラリは研究用（backtest / signal generation）と運用（ETL / execution）両面を想定しています。実運用で使う際は必ず paper_trading 環境で十分に検証してください。
- DB（DuckDB）ファイルはバックアップ・ローテーションを検討してください。大規模なデータではファイルサイズが増加します。
- API の認証情報やシークレットは .env で管理し、公開リポジトリへは含めないでください。
- モジュールは例外処理とログ出力に配慮しているため、LOG_LEVEL を調整して詳細ログを取得できます。

ライセンス / 貢献
-----------------
（この README にはライセンス情報を含めていません。リポジトリの LICENSE ファイルを参照してください。）

以上。必要であれば README に追加する実行スクリプト例（cron 用 wrapper、systemd unit、Dockerfile 例など）や、各モジュールの API 使用例を追記します。どの部分を詳しく補足したいか教えてください。