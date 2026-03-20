KabuSys
=======

KabuSys は日本株のデータ取得・ETL・特徴量生成・シグナル生成・ニュース収集を想定した
小規模な自動売買／研究フレームワークです。DuckDB をデータ層に使い、J-Quants API や
RSS フィードからデータを収集して特徴量（features）を作り、戦略レイヤーで売買シグナルを
生成するモジュール群を提供します。

バージョン: 0.1.0

主な設計方針（抜粋）
- ルックアヘッドバイアスを避けるため、target_date 時点の情報のみで計算
- DuckDB をデータベースに利用し、DDL は冪等に作成
- API 呼び出しはレート制御／リトライを想定
- DB 保存は冪等（ON CONFLICT）で更新

機能一覧
--------
- 環境設定読み込み（.env / .env.local / OS 環境変数）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD で自動ロード無効化可能
- J-Quants API クライアント（差分取得、ページネーション、トークン自動更新、保存）
  - 株価日足、財務データ、マーケットカレンダー取得
- DuckDB スキーマ定義・初期化（init_schema）
- ETL パイプライン（run_daily_etl）
  - 市場カレンダー / 株価 / 財務 の差分取得と保存、品質チェック呼び出し
- 研究（research）
  - ファクター計算（momentum, volatility, value） & 特徴量探索（forward returns, IC, summary）
- 特徴量エンジニアリング（strategy.feature_engineering.build_features）
  - Zスコア正規化、ユニバースフィルタ、features テーブルへの書き込み（冪等）
- シグナル生成（strategy.signal_generator.generate_signals）
  - features / ai_scores / positions を元に BUY/SELL シグナルを生成して signals テーブルへ保存（冪等）
- ニュース収集（data.news_collector）
  - RSS 取得、テキスト前処理、raw_news 保存、記事と銘柄コードの紐付け（news_symbols）
  - SSRF 対策、XML 暴露対策（defusedxml）、受信サイズ制限
- マーケットカレンダー管理（data.calendar_management）
  - 営業日判定 / next/prev trading day / calendar 更新ジョブ
- 監査テーブル初期化（data.audit）など発注・約定追跡用スキーマ群

セットアップ手順
----------------

1. 必要条件
   - Python 3.10 以上（| 型注釈などを使用）
   - pip
   - DuckDB Python パッケージ
   - defusedxml（RSS パース用）

2. リポジトリをクローン
   - git clone <repo-url>
   - （本ドキュメントはコードベースの一部のみを想定）

3. 仮想環境作成（例）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

4. 依存ライブラリをインストール
   - pip install duckdb defusedxml

   （プロジェクト実際の requirements.txt があればそれを使ってください）

5. 環境変数（.env）を準備
   - プロジェクトルートに .env または .env.local を置くと自動でロードされます。
     自動ロードを無効にする場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

   主要な環境変数（必須/デフォルト）:
   - JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
   - KABU_API_PASSWORD (必須) — kabuステーション API パスワード
   - SLACK_BOT_TOKEN (必須) — Slack 通知に使用する Bot トークン
   - SLACK_CHANNEL_ID (必須) — Slack チャネル ID
   - DUCKDB_PATH (省略可) — デフォルト: data/kabusys.duckdb
   - SQLITE_PATH (省略可) — デフォルト: data/monitoring.db
   - KABUSYS_ENV (省略可) — development / paper_trading / live（デフォルト development）
   - LOG_LEVEL (省略可) — DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト INFO）
   - KABUS_API_BASE_URL (省略可) — kabu API ベース URL（デフォルト http://localhost:18080/kabusapi）

   .env の書式はシンプルな KEY=VALUE。export KEY=VALUE やクォートも一部サポート。

使い方（主要な API）
--------------------

以下はいくつかの典型的な実行例です。Python スクリプトや REPL から呼び出して使えます。

1) データベース初期化
   - DuckDB ファイルを作成しスキーマを初期化します。

   Python:
   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")  # ":memory:" も可能

2) 日次 ETL を実行（J-Quants から差分取得 → 保存 → 品質チェック）
   from datetime import date
   from kabusys.data.schema import init_schema
   from kabusys.data.pipeline import run_daily_etl

   conn = init_schema("data/kabusys.duckdb")
   result = run_daily_etl(conn, target_date=date.today())
   print(result.to_dict())

   run_daily_etl は市場カレンダー → 株価 → 財務 → 品質チェックの順に処理します。
   エラーは個別ステップで捕捉され、ETLResult に記録されます。

3) 特徴量構築（features テーブルへ保存）
   from kabusys.strategy import build_features
   from kabusys.data.schema import init_schema
   from datetime import date

   conn = init_schema("data/kabusys.duckdb")
   n = build_features(conn, target_date=date(2025, 1, 1))
   print(f"features updated: {n} rows")

4) シグナル生成（signals テーブルへ保存）
   from kabusys.strategy import generate_signals
   from kabusys.data.schema import init_schema
   from datetime import date

   conn = init_schema("data/kabusys.duckdb")
   count = generate_signals(conn, target_date=date(2025, 1, 1), threshold=0.6)
   print(f"signals generated: {count}")

   生成ロジックは features, ai_scores, positions を参照します。
   weights を渡すことで factor ウェイトの上書きが可能（合計は自動で再スケールされます）。

5) ニュース収集ジョブ実行（RSS → raw_news, news_symbols）
   from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
   from kabusys.data.schema import init_schema

   conn = init_schema("data/kabusys.duckdb")
   results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes={"7203","6758"})
   print(results)

6) 市場カレンダー更新ジョブ
   from kabusys.data.calendar_management import calendar_update_job
   from kabusys.data.schema import init_schema

   conn = init_schema("data/kabusys.duckdb")
   saved = calendar_update_job(conn)
   print(f"market_calendar saved: {saved}")

運用上の注意
-------------
- 環境: settings クラスは実行時に環境変数から値を取得します。開発環境では .env を用意してください。
- API レート制御: J-Quants クライアントは 120 req/min を想定した RateLimiter を実装しています。
- 冪等性: DB 保存は基本的に ON CONFLICT で冪等に動作します（再実行安全）。
- ルックアヘッド対策: 戦略・研究コードは基本的に target_date 時点の情報のみを参照する設計になっています。
- ロギング: 各モジュールで logging を使用しています。LOG_LEVEL 環境変数で制御してください。
- テスト: KABUSYS_DISABLE_AUTO_ENV_LOAD を設定すると .env の自動ロードを無効化してテストを容易にできます。

ディレクトリ構成（主要ファイル）
--------------------------------

src/
  kabusys/
    __init__.py                    # パッケージバージョン等
    config.py                      # 環境変数 / 設定読み込み
    data/
      __init__.py
      jquants_client.py            # J-Quants API クライアント + 保存ユーティリティ
      news_collector.py            # RSS ニュース収集・保存
      schema.py                    # DuckDB スキーマ定義・init_schema
      stats.py                     # 統計ユーティリティ（zscore_normalize 等）
      pipeline.py                  # ETL パイプライン（run_daily_etl 等）
      calendar_management.py       # market_calendar 管理・ジョブ
      audit.py                     # 監査ログ用スキーマ定義
      features.py                  # data 層の features 再エクスポート
    research/
      __init__.py
      factor_research.py           # momentum/volatility/value の計算
      feature_exploration.py       # forward returns / IC / summary
    strategy/
      __init__.py
      feature_engineering.py       # features 作成（正規化・ユニバースフィルタ）
      signal_generator.py          # final_score 計算 → signals 生成
    execution/                      # 発注/実行に関するモジュール群（空ファイルあり）
    monitoring/                     # 監視・メトリクス収集等（存在想定）
    research/                       # （重複名: 上記 research）研究用モジュール群

設定・環境変数の一覧（まとめ）
-----------------------------
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- SLACK_BOT_TOKEN (必須)
- SLACK_CHANNEL_ID (必須)
- DUCKDB_PATH (省略可, default: data/kabusys.duckdb)
- SQLITE_PATH (省略可, default: data/monitoring.db)
- KABUSYS_ENV (development | paper_trading | live)（デフォルト development）
- LOG_LEVEL (DEBUG|INFO|...)（デフォルト INFO）
- KABUS_API_BASE_URL (kabu ステーション API のベース URL)
- KABUSYS_DISABLE_AUTO_ENV_LOAD (1 を設定すると .env 自動ロードを無効化)

補足
----
- この README は提供されたコードベースの一部をもとに作成しています。実際に運用する際は追加の依存関係（例: HTTP クライアント、Slack 通知用ライブラリ、テスト用ツール等）が必要になる場合があります。
- 本コードは「研究用 / バックテスト補助」および自動売買基盤の一部として設計されています。実運用ではリスク管理・接続監視・堅牢なエラーハンドリングや証券会社 API の仕様確認が必須です。

ライセンス / 貢献
-----------------
（リポジトリに LICENSE ファイルがあればここに記載してください）

以上。必要なら各コマンドの具体的なスクリプト例や .env.example のテンプレートを追加で作成します。どの部分を詳しく説明しましょうか？