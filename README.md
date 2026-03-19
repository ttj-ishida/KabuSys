KabuSys — 日本株自動売買プラットフォーム
=================================

概要
----
KabuSys は日本株向けのデータプラットフォームと戦略層を備えた自動売買基盤のプロジェクトです。  
主に以下を提供します。

- J-Quants API を用いた市場データ（株価・財務・マーケットカレンダー）取得と DuckDB への永続化（冪等保存）
- ニュースの RSS 収集と記事 → 銘柄の紐付け
- 研究（research）用のファクター計算（モメンタム、ボラティリティ、バリュー等）
- 戦略層での特徴量正規化（features テーブル作成）および最終スコア計算→シグナル生成
- ETL パイプライン、マーケットカレンダー管理、監査ログスキーマなどの基盤機能

注意: この README はソースコード（src/kabusys/*）の実装に基づく簡易ドキュメントです。

主な機能
--------
- データ取得・保存
  - J-Quants API クライアント（差分取得 / ページネーション / 再試行・レートリミット対応）
  - raw_prices / raw_financials / market_calendar などの Raw Layer 保存（冪等）
  - DuckDB スキーマ定義と初期化（init_schema）
- ETL
  - 日次 ETL 実行（run_daily_etl）: カレンダー、株価、財務データの差分取得 + 品質チェック
  - run_prices_etl / run_financials_etl / run_calendar_etl の個別ジョブ
- 研究（Research）
  - ファクター計算（calc_momentum, calc_volatility, calc_value）
  - 将来リターン、IC、統計サマリー等のユーティリティ（calc_forward_returns, calc_ic, factor_summary）
  - Z スコア正規化ユーティリティ
- 特徴量・シグナル生成（Strategy）
  - build_features: research の生ファクターをマージしてユニバースフィルタ、Zスコア正規化→features テーブルへ保存
  - generate_signals: features と ai_scores を統合して final_score を計算、BUY/SELL シグナルを signals テーブルへ保存
- ニュース収集
  - RSS フィード取得（SSRF/Size/GZIP/トラッキング削除対応）
  - raw_news / news_symbols への保存（冪等）
  - テキスト前処理・銘柄コード抽出（既知の4桁コード）
- マーケットカレンダー管理
  - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / calendar_update_job
- 監査ログ（Audit）
  - signal_events / order_requests / executions などの監査用スキーマ

前提・要件
----------
- Python 3.10+ 推奨（型ヒントに union | を使用）
- 必要なライブラリ（主なもの）
  - duckdb
  - defusedxml
- 標準ライブラリのみで実装されているユーティリティも多いですが、HTTP・DB 操作に標準機能・上記ライブラリを使用します。
- J-Quants API トークン、kabu API パスワード、Slack トークン等の環境変数が必要（詳細は下記）。

セットアップ手順
--------------
1. リポジトリをクローン（想定: パッケージは src/ 配下）
   - 例: git clone <repo-url>

2. 仮想環境を作成・有効化（任意だが推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存ライブラリをインストール
   - pip install -U pip
   - 必要最小限のライブラリをインストール:
     - pip install duckdb defusedxml
   - プロジェクト配布に setup/pyproject があるなら:
     - pip install -e .

4. 環境変数設定
   - プロジェクトルートに .env（あるいは .env.local）を置くと自動読み込みされます（kabusys.config により .git や pyproject.toml を起点に探索）。
   - 自動読み込みを無効にする場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

例: .env（最小）
    JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
    KABU_API_PASSWORD=your_kabu_api_password
    SLACK_BOT_TOKEN=xoxb-...
    SLACK_CHANNEL_ID=C01234567
    DUCKDB_PATH=data/kabusys.duckdb
    SQLITE_PATH=data/monitoring.db
    KABUSYS_ENV=development
    LOG_LEVEL=INFO

環境変数の主なキー
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API のパスワード（必須）
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN, SLACK_CHANNEL_ID: Slack 通知用（必須）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 sqlite パス（デフォルト data/monitoring.db）
- KABUSYS_ENV: development / paper_trading / live
- LOG_LEVEL: DEBUG|INFO|WARNING|ERROR|CRITICAL

初期化: DuckDB スキーマ作成
-------------------------
Python REPL かスクリプトで DuckDB スキーマを作成します。

例:
    from kabusys.data import schema
    conn = schema.init_schema("data/kabusys.duckdb")

- init_schema は必要なテーブル・インデックスをすべて作成します（冪等）。

基本的な使い方（サンプル）
------------------------

1) 日次 ETL を実行してデータを収集する
    from datetime import date
    from kabusys.data.schema import init_schema
    from kabusys.data.pipeline import run_daily_etl

    conn = init_schema("data/kabusys.duckdb")
    result = run_daily_etl(conn, target_date=date.today())
    print(result.to_dict())

2) 研究用ファクター計算（単体）
    from datetime import date
    import duckdb
    from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

    conn = duckdb.connect("data/kabusys.duckdb")
    mom = calc_momentum(conn, date(2024, 1, 5))
    vol = calc_volatility(conn, date(2024, 1, 5))
    val = calc_value(conn, date(2024, 1, 5))
    # 結果は dict のリスト

3) 特徴量を構築して features テーブルへ保存
    from datetime import date
    from kabusys.data.schema import get_connection
    from kabusys.strategy import build_features

    conn = get_connection("data/kabusys.duckdb")
    n = build_features(conn, date(2024, 1, 5))
    print(f"features saved for {n} codes")

4) シグナル生成
    from datetime import date
    from kabusys.strategy import generate_signals
    from kabusys.data.schema import get_connection

    conn = get_connection("data/kabusys.duckdb")
    total = generate_signals(conn, date(2024,1,5))
    print(f"signals generated: {total}")

5) ニュース収集ジョブ（RSS）
    from kabusys.data.news_collector import run_news_collection
    from kabusys.data.schema import get_connection

    conn = get_connection("data/kabusys.duckdb")
    known_codes = {"7203", "6758", "9984"}  # 既知の銘柄コードセット
    results = run_news_collection(conn, known_codes=known_codes)
    print(results)

6) カレンダー更新バッチ
    from kabusys.data.calendar_management import calendar_update_job
    from kabusys.data.schema import get_connection

    conn = get_connection("data/kabusys.duckdb")
    saved = calendar_update_job(conn)
    print(f"saved calendar entries: {saved}")

設計上の注意点
--------------
- 多くの関数は DuckDB 接続を受け取り、その上で SQL を実行します。トランザクションや BEGIN/COMMIT/ROLLBACK を使用して原子性を保証する実装がされています。
- J-Quants API へのリクエストはレート制限／再試行／トークン自動リフレッシュ等の保護がありますが、実運用では API キーやネットワークの取り扱いに注意してください。
- features / signals / raw_* テーブルの操作は冪等（同一日付を上書き）となるよう設計されています。
- ニュース収集は SSRF・XML bomb・過大サイズ等に対する防御を組み込んでいますが、ソースやフィードの信頼性に依存します。

ディレクトリ構成（主なファイル）
------------------------------
src/kabusys/
- __init__.py
- config.py                      — 環境変数設定 / Settings
- data/
  - __init__.py
  - jquants_client.py             — J-Quants API クライアント + 保存関数
  - schema.py                     — DuckDB スキーマ定義・初期化
  - pipeline.py                   — ETL パイプライン（run_daily_etl 等）
  - news_collector.py             — RSS 収集・保存・銘柄抽出
  - stats.py                      — zscore_normalize 等統計ユーティリティ
  - features.py                   — zscore_normalize の再エクスポート
  - calendar_management.py        — マーケットカレンダーユーティリティ
  - audit.py                      — 監査ログスキーマ定義
  - (その他: quality.py 等想定)
- research/
  - __init__.py
  - factor_research.py            — calc_momentum / calc_volatility / calc_value
  - feature_exploration.py        — calc_forward_returns / calc_ic / factor_summary / rank
- strategy/
  - __init__.py
  - feature_engineering.py        — build_features
  - signal_generator.py           — generate_signals
- execution/
  - __init__.py                   — 発注層（未実装 or別途実装を想定）
- monitoring/                      — 監視・通知用モジュール（存在する場合）
- その他ユーティリティファイル

開発・テスト
------------
- 自動環境変数読み込み: kabusys.config は .env / .env.local をプロジェクトルートから読み込みます。単体テストで自動読み込みを無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB を :memory: で使えば軽量な単体テストが可能です（schema.init_schema(":memory:")）。
- ネットワーク呼び出しを行うモジュールは（例: jquants_client._request / news_collector._urlopen）をモックしてテスト可能です。

付記
----
- この README はコード内の docstring / コメントをベースに作成しています。実際の運用では権限管理・秘密情報管理・監査ポリシー・リスク制御（例: 発注層の安全機構）を別途実装・確認してください。
- 追加の依存や起動スクリプト（CLI、サービス化）はプロジェクト実装状況に応じて用意してください。

お問い合わせ / 貢献
------------------
- バグ報告や機能改善提案はリポジトリの Issue をご利用ください。プルリクエスト歓迎します。