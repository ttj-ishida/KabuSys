KabuSys
=======

KabuSys は日本株向けの自動売買システムのコアライブラリです。  
データ取得（J-Quants）、ETL、ファクター計算、特徴量生成、シグナル生成、バックテスト、ニュース収集、DuckDB スキーマ管理などを含むモジュール群を提供します。  
本 README はローカル開発や運用開始のための概要、セットアップ手順、基本的な使い方、ディレクトリ構成を日本語でまとめたものです。

主な特徴
--------
- データ取得
  - J-Quants API クライアント（レートリミット・リトライ・トークン自動リフレッシュ対応）
  - 株価（OHLCV）、財務データ、マーケットカレンダー取得をサポート
- データ基盤
  - DuckDB 用スキーマ定義 / 初期化（raw / processed / feature / execution 層）
  - ETL パイプライン（差分更新、バックフィル、品質チェックを想定）
- リサーチ / ファクター
  - Momentum / Volatility / Value 等のファクター計算（prices_daily / raw_financials を参照）
  - ファクター探索・IC 計算・統計サマリー
- 特徴量エンジニアリング
  - cross-sectional Z スコア正規化、ユニバースフィルタ適用、features テーブルへの UPSERT（冪等）
- シグナル生成
  - 特徴量 + AI スコアを統合して final_score を算出、BUY/SELL シグナルを生成（冪等）
  - Bear レジーム抑制、エグジット条件（ストップロス等）を実装
- バックテスト
  - インメモリでデータをコピーして日次シミュレーションを実行
  - スリッページ・手数料モデル、ポートフォリオサイジング、評価指標（CAGR / Sharpe / MaxDD 等）
- ニュース収集
  - RSS 収集、前処理、記事ID生成、銘柄抽出、SSRF 対策・サイズ制限等の安全対策
- 設計方針（共通）
  - ルックアヘッドバイアス回避（target_date 時点のみ参照）
  - 冪等性（DB への保存は ON CONFLICT/UPSERT 等で安全に）
  - 外部依存を最小化（可能な限り標準ライブラリ中心）

必要要件
--------
- Python 3.10+
- 必須パッケージ（例）
  - duckdb
  - defusedxml
（プロジェクトに合わせて他パッケージが必要になる場合があります。requirements.txt / pyproject.toml がある場合はそちらを参照してください）

セットアップ手順
----------------
1. リポジトリをクローンして仮想環境を作成
   - 例:
     - python -m venv .venv
     - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   - 最低限:
     - pip install duckdb defusedxml
   - 開発用: pip install -e . （プロジェクトに pyproject.toml があれば editable install）

3. DuckDB スキーマ初期化（例）
   - Python REPL やスクリプトで:
     - from kabusys.data.schema import init_schema
     - conn = init_schema("data/kabusys.duckdb")
     - conn.close()
   - :memory: を使ったテスト用初期化も可能:
     - conn = init_schema(":memory:")

4. 環境変数 / .env の準備
   - 環境変数は OS 環境変数 > .env.local > .env の順で読み込まれます（自動ロードはデフォルトで有効）。
   - 自動読み込みを無効化する場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
   - 必要な環境変数（主なもの）:
     - JQUANTS_REFRESH_TOKEN    - J-Quants のリフレッシュトークン（必須）
     - KABU_API_PASSWORD        - kabuステーション API パスワード（必須）
     - KABU_API_BASE_URL        - kabu API ベース URL（省略時: http://localhost:18080/kabusapi）
     - SLACK_BOT_TOKEN          - Slack 通知用 Bot トークン（必須）
     - SLACK_CHANNEL_ID         - Slack チャンネル ID（必須）
     - DUCKDB_PATH              - デフォルト duckdb ファイルパス（例: data/kabusys.duckdb）
     - SQLITE_PATH              - 監視用 sqlite ファイルパス（例: data/monitoring.db）
     - KABUSYS_ENV              - 環境: development | paper_trading | live （デフォルト development）
     - LOG_LEVEL                - ログレベル: DEBUG|INFO|WARNING|ERROR|CRITICAL（デフォルト INFO）
   - .env 例（簡易）:
     - JQUANTS_REFRESH_TOKEN=xxxx
     - KABU_API_PASSWORD=yyyy
     - SLACK_BOT_TOKEN=xxxx
     - SLACK_CHANNEL_ID=xxxx
     - DUCKDB_PATH=data/kabusys.duckdb

基本的な使い方
--------------

- DuckDB スキーマの作成（前述）
  - from kabusys.data.schema import init_schema
  - conn = init_schema("data/kabusys.duckdb")

- データ取得（J-Quants）と保存（例）
  - from kabusys.data import jquants_client as jq
  - records = jq.fetch_daily_quotes(date_from=..., date_to=..., id_token=None)
  - n = jq.save_daily_quotes(conn, records)

- ETL（株価差分更新） — pipeline モジュールを使用
  - from kabusys.data.pipeline import run_prices_etl
  - result_tuple = run_prices_etl(conn, target_date=date.today(), id_token=None)
  - （pipeline 内の API 呼び出しは settings.jquants_refresh_token を使用）

- 特徴量生成（features テーブル作成）
  - from kabusys.strategy import build_features
  - count = build_features(conn, target_date=date(2024, 1, 31))

- シグナル生成
  - from kabusys.strategy import generate_signals
  - total = generate_signals(conn, target_date=date(2024, 1, 31), threshold=0.6)

- バックテスト CLI
  - Python モジュールとして実行:
    - python -m kabusys.backtest.run --start 2023-01-01 --end 2024-12-31 --db data/kabusys.duckdb
  - オプション:
    - --cash 初期資金（デフォルト 10000000）
    - --slippage, --commission, --max-position-pct

- バックテストを Python から実行（API）
  - from kabusys.backtest.engine import run_backtest
  - result = run_backtest(conn, start_date=..., end_date=..., initial_cash=10_000_000)

- ニュース収集
  - from kabusys.data.news_collector import run_news_collection
  - results = run_news_collection(conn, sources=None, known_codes=set_of_codes)

サンプルコード（特徴量生成 + シグナル生成）
----------------------------------------
例: ある日付の特徴量作成とシグナル生成を行う簡単なスクリプト

- from datetime import date
- from kabusys.data.schema import init_schema
- from kabusys.strategy import build_features, generate_signals
- conn = init_schema("data/kabusys.duckdb")
- tgt = date(2024, 1, 31)
- build_features(conn, tgt)
- generate_signals(conn, tgt)
- conn.close()

注意点・設計上の重要事項
-----------------------
- ルックアヘッドバイアス回避:
  - すべての計算関数は target_date 時点のデータのみを参照するよう設計されています。将来データを使用しないようご注意ください。
- 冪等性:
  - DB 書き込みはできるだけ UPSERT / ON CONFLICT / トランザクションで実装されています。定期処理の再実行に耐えられる構成です。
- セキュリティ:
  - ニュース収集では SSRF 対策、受信サイズ制限、XML パースの安全ライブラリ（defusedxml）を利用しています。
- リトライとレート制限:
  - J-Quants クライアントはレート制限（120 req/min）を守る実装と、リトライ / トークン自動リフレッシュを備えています。
- テスト・デバッグ:
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると .env 自動読み込みを無効化できます（ユニットテスト時に便利）。

ディレクトリ構成（主要ファイル）
--------------------------------
以下はソースツリー（src/kabusys 以下）の主なファイルと簡単な説明です。

- src/kabusys/__init__.py
  - パッケージ定義（version 等）
- src/kabusys/config.py
  - 環境変数・設定管理（.env 自動読み込み、settings オブジェクト）
- src/kabusys/data/
  - jquants_client.py      : J-Quants API クライアント（取得・保存関数）
  - news_collector.py     : RSS ニュース収集・保存
  - schema.py             : DuckDB スキーマ定義と init_schema()
  - stats.py              : 統計ユーティリティ（z-score など）
  - pipeline.py           : ETL パイプライン（差分取得など）
- src/kabusys/research/
  - factor_research.py    : Momentum/Volatility/Value 等のファクター計算
  - feature_exploration.py: 将来リターン計算・IC・統計サマリー
- src/kabusys/strategy/
  - feature_engineering.py: 特徴量作成（features テーブルへ保存）
  - signal_generator.py   : final_score 計算と signals テーブルへの保存
- src/kabusys/backtest/
  - engine.py             : run_backtest の実装（インメモリコピー、全体ループ）
  - simulator.py          : PortfolioSimulator（擬似約定・時価評価）
  - metrics.py            : バックテスト評価指標計算
  - run.py                : CLI エントリポイント（python -m kabusys.backtest.run）
  - clock.py              : SimulatedClock（将来拡張用）
- src/kabusys/execution/
  - （発注 / 実行層のプレースホルダ）
- src/kabusys/monitoring/
  - （監視用モジュールのプレースホルダ）

開発者向けメモ
---------------
- 型ヒントとログ出力が豊富に記述されています。既存の関数を呼び出す際は target_date ベースの参照ルールに従ってください。
- DuckDB を利用した SQL 部分はプレースホルダ（?）でバインドされています。複雑なクエリを変更する場合は SQL インジェクションに注意してください（本コードは基本的に安全な形で構築されています）。
- テストや CI 時は KABUSYS_DISABLE_AUTO_ENV_LOAD を使って外部 .env の自動読み込みを止めると安定します。

ライセンス・貢献
----------------
（ライセンスや貢献方法はリポジトリ側で管理してください。本 README に明示されていない場合はリポジトリの LICENSE ファイルや CONTRIBUTING を参照してください。）

お問い合わせ
------------
実運用や拡張に関する質問があれば、リポジトリの Issue を作成してください。コード内のドキュメント（docstring）にも主要な設計意図や注意点を記載していますので、参照してください。