KabuSys — 日本株自動売買システム
================================

概要
----
KabuSys は日本株向けのデータプラットフォーム、リサーチ、戦略、バックテスト、実行（Execution）を一貫して扱うための Python パッケージです。  
主に以下の役割を持ちます：

- J-Quants API からのデータ収集（株価・財務・市場カレンダー）
- DuckDB を使ったデータスキーマ／永続化
- ファクター計算（momentum / volatility / value 等）
- 特徴量正規化と戦略シグナル生成（BUY/SELL）
- バックテスト用シミュレータとメトリクス計算
- RSS ベースのニュース収集と銘柄紐付け

重要な設計方針として「ルックアヘッドバイアスの排除」「ETL/保存の冪等性」「ネットワーク／XML 等に対する安全対策」が盛り込まれています。

主な機能
--------
- データ取得・保存
  - J-Quants API クライアント（取得・リトライ・レート制御・トークン自動更新）
  - raw / processed / feature / execution の DuckDB スキーマ定義と初期化
  - RSS ニュース取得（SSRF対策、gzip/サイズ制限、トラッキングパラメータ除去）と DB 保存
- データ処理／研究
  - ファクター計算（momentum, volatility, value, liquidity 等）
  - クロスセクション Z スコア正規化ユーティリティ
  - IC 計算・ファクター統計サマリ（研究向け）
- 戦略
  - feature_engineering.build_features(conn, target_date)
  - signal_generator.generate_signals(conn, target_date, ...)
  - ファクタ合成、AI スコア統合、Bear レジーム抑制、BUY/SELL 判定、冪等的な signals 書き込み
- バックテスト
  - ポートフォリオシミュレータ（擬似約定・スリッページ・手数料）
  - バックテストエンジン（本番 DB をコピーしてインメモリで実行）
  - メトリクス計算（CAGR, Sharpe, Max Drawdown, Win Rate, Payoff Ratio）
  - CLI エントリポイント: python -m kabusys.backtest.run
- ETL パイプライン
  - 差分更新ロジック、品質チェックフック、idempotent 保存

前提・依存
-----------
- Python 3.10 以上（`X | Y` の型ヒント等を使用）
- 必要なライブラリ（代表例）
  - duckdb
  - defusedxml
- ネットワークアクセス（J-Quants API, RSS フィード等）
- 環境変数（下記参照）

環境変数
--------
このパッケージは環境変数または .env（プロジェクトルートにある場合）から設定を読み込みます（自動ロードが有効な場合。無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定）。

主な必須環境変数:
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（jquants_client で使用）
- KABU_API_PASSWORD: kabuステーション API のパスワード（execution 層）
- SLACK_BOT_TOKEN: Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID: 通知先チャンネル ID

任意／デフォルト設定:
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）

セットアップ手順
----------------
1. Python と仮想環境の準備（例）
   - Python >= 3.10 をインストール
   - 仮想環境を作成・有効化
     - python -m venv .venv
     - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージのインストール（例）
   - pip install duckdb defusedxml
   - 実際のプロジェクトでは requirements.txt があればそれを使ってください。

3. 環境変数の設定
   - プロジェクトルートに .env を作成（例）
     JQUANTS_REFRESH_TOKEN=...
     KABU_API_PASSWORD=...
     SLACK_BOT_TOKEN=...
     SLACK_CHANNEL_ID=...
     KABUSYS_ENV=development
   - もしくはシェルで export / set しても可。

4. DuckDB スキーマの初期化
   - Python REPL またはスクリプトで:
     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")
     conn.close()
   - ":memory:" を指定するとインメモリ DB が作られます（バックテスト等で利用）。

基本的な使い方
-------------
以下に代表的なユースケースを示します。すべて DuckDB の接続（kabusys.data.schema.init_schema で作成した conn）を受け取る形です。

1) データ取得（J-Quants）と保存（ETL）
   - jquants_client の関数を直接使うか、data.pipeline の ETL ヘルパーを使います。
   - 例（簡略）:
     from kabusys.data import jquants_client as jq
     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")
     records = jq.fetch_daily_quotes(date_from=..., date_to=...)
     jq.save_daily_quotes(conn, records)
     conn.close()

   - pipeline.run_prices_etl や run_news_collection を使って一括処理できます。

2) 特徴量構築
   - build_features(conn, target_date)
   - 例:
     from kabusys.strategy import build_features
     build_features(conn, target_date=some_date)

   - 処理は冪等（target_date の分は削除して再挿入）です。

3) シグナル生成
   - generate_signals(conn, target_date, threshold=0.6, weights=None)
   - 例:
     from kabusys.strategy import generate_signals
     generate_signals(conn, target_date=some_date)

   - signals テーブルへ BUY/SELL を日付単位で書き込みます。

4) バックテスト（CLI）
   - DB を事前に prices_daily / features / ai_scores / market_regime / market_calendar 等で準備しておきます。
   - 実行例:
     python -m kabusys.backtest.run \
       --start 2023-01-01 --end 2023-12-31 \
       --cash 10000000 --db data/kabusys.duckdb
   - サンプル出力（主要メトリクス）をコンソールに表示します。

5) スクリプト内でのバックテスト API 呼び出し
   - from kabusys.backtest.engine import run_backtest
     result = run_backtest(conn, start_date, end_date, initial_cash=10_000_000)
     # result.history, result.trades, result.metrics を利用

注意点
-------
- 多くの処理は DuckDB のテーブル（prices_daily, raw_financials, features, ai_scores, positions, signals 等）を前提としています。事前のデータ用意が必要です。
- ETL / 保存関数は可能な限り冪等に実装されています（ON CONFLICT 句など）。
- ニュース収集では SSRF 対策、レスポンスサイズ制限、XML の安全パーサ（defusedxml）を採用しています。
- 自動で .env を読み込む仕組みがありますが、テスト等で無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

主なモジュール・ディレクトリ構成
-----------------------------
（リポジトリ内 src/kabusys 以下の主要ファイルを抜粋）

- kabusys/
  - __init__.py
  - config.py                         # 環境変数／設定管理
  - data/
    - __init__.py
    - jquants_client.py               # J-Quants API クライアント + 保存
    - news_collector.py               # RSS 取得・前処理・保存
    - schema.py                       # DuckDB スキーマ定義 / init_schema / get_connection
    - stats.py                        # zscore_normalize 等ユーティリティ
    - pipeline.py                     # ETL パイプライン（差分更新など）
  - research/
    - __init__.py
    - factor_research.py              # momentum/volatility/value の計算
    - feature_exploration.py          # forward returns, IC, summary, rank
  - strategy/
    - __init__.py
    - feature_engineering.py          # build_features
    - signal_generator.py             # generate_signals
  - backtest/
    - __init__.py
    - engine.py                       # run_backtest（本体ループ）
    - simulator.py                    # PortfolioSimulator, DailySnapshot, TradeRecord
    - metrics.py                      # バックテスト評価指標
    - run.py                          # CLI エントリポイント
    - clock.py
  - execution/                         # 発注・実行関連（未詳細化のパッケージ領域）
  - monitoring/                        # 監視・Slack 通知等（未詳細化のパッケージ領域）
  - research/                          # 研究用モジュール群（上記と重複）

開発・拡張メモ
---------------
- 新しいデータソースやフィードを追加する場合、raw layer に挿入 → processed layer へ変換 → feature layer へ集約、という流れを意識してください。
- generate_signals の重みや閾値は外部から注入可能（weights 引数、threshold 引数）なので A/B テストや最適化がしやすい設計です。
- DuckDB のスキーマは schema.py で一元管理しているためフィールド追加はそこに反映してください。
- API へのリトライやレート制御は jquants_client に実装されており、他のクライアントでも同様のパターンを踏襲してください。

ライセンス・連絡
----------------
- 本リポジトリのライセンスやメンテナンス連絡先はソースツリーのトップレベル（LICENSE / MAINTAINERS 等）をご確認ください。

必要であれば README に「.env.example」のテンプレートや、より詳細な ETL 実行手順（run_prices_etl の引数例、run_news_collection の cron 設定例、Slack 通知の設定）を追記します。追加で載せたい内容があれば教えてください。