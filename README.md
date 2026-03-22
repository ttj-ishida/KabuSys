KabuSys — 日本株自動売買基盤（README）
=================================

概要
----
KabuSys は日本株向けのデータプラットフォーム・リサーチ・戦略・バックテスト・実行層を備えた自動売買フレームワークです。  
主な設計方針は「ルックアヘッドバイアス回避」「冪等性」「明示的なトランザクション制御」「外部ライブラリ最小化（STL優先）」です。  
データ取得は J-Quants API を想定し、DuckDB を内部データストアとして使用します。研究（research）→特徴量（features）→シグナル（signals）→発注/約定（execution）という典型的ワークフローを提供します。

主な機能
--------
- データ取得・保存
  - J-Quants API クライアント（レート制御、リトライ、トークン自動リフレッシュ）
  - RSSベースのニュース収集（SSRF対策、トラッキングパラメータ除去、記事IDの冪等化）
  - DuckDB スキーマ定義と初期化（init_schema）
- データ処理 / ETL
  - 差分取得・バックフィルを意識した ETL パイプライン（data.pipeline）
  - 生データ → 整形テーブル（raw / processed / feature / execution 層）
- リサーチ / ファクター
  - Momentum / Volatility / Value 等のファクター計算（research.factor_research）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー（research.feature_exploration）
  - Zスコア正規化など統計ユーティリティ（data.stats）
- 特徴量エンジニアリング / シグナル生成
  - features テーブル構築（strategy.feature_engineering.build_features）
  - 正規化済みファクター + AIスコアを統合して BUY/SELL シグナル生成（strategy.signal_generator.generate_signals）
  - Bear相場検知やストップロス等のルールを含む
- バックテスト
  - インメモリ DuckDB を用いた日次バックテストエンジン（backtest.engine.run_backtest）
  - ポートフォリオシミュレータ（スリッページ/手数料モデル、PortfolioSimulator）
  - バックテストメトリクス（CAGR、Sharpe、MaxDrawdown、勝率、PayoffRatio）
  - CLI 実行スクリプト（python -m kabusys.backtest.run）
- 実行・監視（骨組み）
  - 発注・orders/trades/positionsスキーマが定義済み（execution 層の実装拡張を想定）

セットアップ手順
----------------

前提
- Python 3.10+（typing の | や型注釈を多用しているため）
- ネットワークアクセス（J-Quants / RSS）

1. リポジトリをクローン（あるいはパッケージを取得）
   - 例: git clone <repo>

2. 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 必要パッケージのインストール（最小セット例）
   - pip install duckdb defusedxml

   ※ requirements.txt がある場合は pip install -r requirements.txt を推奨します。

4. パッケージのインストール（開発モード）
   - pip install -e .

5. 環境変数の準備
   - プロジェクトルートに .env ファイルを置くと自動で読み込まれます（.git または pyproject.toml を基準にルートを探索）。  
   - 自動ロードを無効化する場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

必須環境変数（最低限）
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
- KABU_API_PASSWORD: kabuステーション API のパスワード（execution 層を使う場合）
- SLACK_BOT_TOKEN: Slack 通知を使う場合
- SLACK_CHANNEL_ID: Slack 通知先チャンネル ID

任意 / 推奨
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- LOG_LEVEL: DEBUG|INFO|WARNING|ERROR|CRITICAL（デフォルト: INFO）
- DUCKDB_PATH / SQLITE_PATH: DB ファイルパスの上書き（デフォルトは data/ 配下）

.env の最小例 (.env.example)
- JQUANTS_REFRESH_TOKEN=xxxxx
- KABU_API_PASSWORD=xxxxx
- SLACK_BOT_TOKEN=xoxb-xxxxx
- SLACK_CHANNEL_ID=C01234567
- KABUSYS_ENV=development
- LOG_LEVEL=INFO

基本的な使い方
-------------

1. DuckDB スキーマ初期化
   - Python REPL / スクリプト内で:
     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")  # ":memory:" でも可

2. データ取得（J-Quants）と保存
   - jquants_client の fetch_* / save_* を組み合わせて ETL を行います。あるいは pipeline モジュールの ETL ヘルパーを使用:
     from kabusys.data.pipeline import run_prices_etl
     result = run_prices_etl(conn, target_date=date.today())

   - jquants_client は自動的にトークンを取得/リフレッシュし、レート制御・リトライを行います。

3. ニュース収集
   - from kabusys.data.news_collector import run_news_collection
     results = run_news_collection(conn, sources=None, known_codes=set_of_codes)

4. 特徴量構築
   - from kabusys.strategy import build_features
     count = build_features(conn, target_date=date(2024,1,1))

   - build_features は research のファクター計算結果（calc_momentum, calc_volatility, calc_value）を用いてユニバースフィルタ、Zスコア正規化、features テーブルへの UPSERT を行います。

5. シグナル生成
   - from kabusys.strategy import generate_signals
     n = generate_signals(conn, target_date=date(2024,1,1), threshold=0.6)

   - AI スコア（ai_scores テーブル）が存在する場合は統合され、Bear レジーム検知などが適用されます。

6. バックテスト実行（CLI）
   - python -m kabusys.backtest.run --start 2023-01-01 --end 2023-12-31 --db data/kabusys.duckdb
   - オプション: --cash, --slippage, --commission, --max-position-pct
   - 内部で run_backtest が呼ばれ、インメモリ DB に必要データをコピーして日次ループを回します。

7. バックテスト API（プログラムから）
   - from kabusys.backtest.engine import run_backtest
     result = run_backtest(conn, start_date, end_date, initial_cash=10_000_000)
     # result.history, result.trades, result.metrics を参照

ディレクトリ構成（主要ファイル）
--------------------------------
以下はソースツリー（src/kabusys）のおおまかな構成です。実際のリポジトリでは追加ファイル / テスト等が存在する可能性があります。

- src/kabusys/
  - __init__.py
  - config.py                     # 環境変数 / 設定読み込みロジック
  - data/
    - __init__.py
    - jquants_client.py           # J-Quants API クライアント（取得・保存）
    - news_collector.py           # RSS ニュース収集・保存
    - pipeline.py                 # ETL パイプライン（差分更新等）
    - schema.py                   # DuckDB スキーマ初期化（init_schema）
    - stats.py                    # zscore_normalize 等の統計ユーティリティ
  - research/
    - __init__.py
    - factor_research.py          # Momentum/Volatility/Value の計算
    - feature_exploration.py      # forward returns / IC / summary
  - strategy/
    - __init__.py
    - feature_engineering.py      # features テーブル構築
    - signal_generator.py         # final_score 計算と signals テーブル生成
  - backtest/
    - __init__.py
    - engine.py                   # run_backtest（全体エンジン）
    - simulator.py                # PortfolioSimulator / 約定ロジック
    - metrics.py                  # バックテスト評価指標
    - clock.py                    # SimulatedClock（将来拡張用）
    - run.py                      # CLI ランナー
  - execution/                     # 発注実行層（骨組み）
    - __init__.py
  - monitoring/                    # 監視・アラート用モジュール（プレースホルダ）
    - (可能性あり)

運用上の注意 / 実装上のポイント
------------------------------
- ルックアヘッドバイアス: 各計算は target_date 時点の「利用可能データ」のみを利用する設計です（fetched_at を用いたトレーサビリティ）。
- 冪等性: DB への保存は基本的に ON CONFLICT / UPSERT、トランザクションを使って日付単位で置換する実装が多く用意されています。
- ETL の差分取得: 最終取得日からの再取得（backfill_days）を行い API の後出し修正を吸収する設計です。
- セキュリティ: ニュース収集で SSRF 対策、XML パース保護（defusedxml）などを実装しています。
- DB 初期化: init_schema は ":memory:" を受け付けるため、単体テストやバックテストで DB 汚染を避けられます。

よくある操作例（コードスニペット）
---------------------------------
- スキーマ初期化:
  from kabusys.data.schema import init_schema
  conn = init_schema("data/kabusys.duckdb")

- 特徴量作成:
  from kabusys.strategy import build_features
  build_features(conn, target_date=date(2024,1,1))

- シグナル生成:
  from kabusys.strategy import generate_signals
  generate_signals(conn, target_date=date(2024,1,1), threshold=0.6)

- バックテスト（プログラム実行）:
  from kabusys.backtest.engine import run_backtest
  result = run_backtest(conn, date(2023,1,4), date(2023,12,29))

サポート / 貢献
----------------
- バグ報告、機能提案は GitHub Issues をご利用ください。  
- 貢献: コードスタイルに沿ったプルリクエストを歓迎します。ユニットテスト、ドキュメント、型注釈の追加が助かります。

ライセンス
---------
- 本 README はコードベースに基づいた説明を含みます。実際のライセンスはリポジトリ内の LICENSE ファイルを参照してください。

以上。必要であれば「.env.example」のテンプレートや、より詳細な運用手順（ETL スケジューリング、監視/通知設定、kabuステーションとの接続手順）を追加で作成します。どの情報を優先してドキュメント化しますか？