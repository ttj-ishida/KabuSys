KabuSys — 日本株自動売買システム
================================

概要
----
KabuSys は日本株を対象とした自動売買プラットフォームの参照実装です。  
主な機能はデータの収集・整備（ETL）、ファクター計算・特徴量エンジニアリング、シグナル生成、バックテスト、ニュース収集、及び発注/実行シミュレーションを含みます。  
設計上の特徴として、ルックアヘッドバイアス回避、冪等性（DB への upsert／ON CONFLICT）、リトライ・レート制御、シンプルなバックテストフレームワークを重視しています。

主な機能
--------
- データ収集
  - J-Quants API から日次株価（OHLCV）、財務データ、JPXカレンダーを取得（jquants_client）。
  - RSS フィードからニュース記事を収集・前処理・銘柄紐付け（news_collector）。
- データ格納 / スキーマ管理
  - DuckDB ベースのスキーマ定義と初期化（data.schema.init_schema）。
  - Raw / Processed / Feature / Execution の多層スキーマを提供。
- ETL パイプライン
  - 差分更新、バックフィル（backfill）、品質チェックのフレームワーク（data.pipeline）。
- 研究用ファクター計算
  - モメンタム、ボラティリティ、バリュー等のファクター算出（research.factor_research）。
  - 将来リターン・IC（Information Coefficient）計算、統計サマリー（research.feature_exploration）。
- 特徴量エンジニアリング
  - 生ファクターの正規化（Z スコア），ユニバースフィルタ適用、features テーブルへの保存（strategy.feature_engineering）。
- シグナル生成
  - features と ai_scores を統合して final_score を算出、BUY/SELL シグナルを生成し signals テーブルへ保存（strategy.signal_generator）。
- バックテスト
  - 日次ベースのシミュレータ、スリッページ・手数料モデル、メトリクス計算（backtest.*）。CLI エントリポイントあり（backtest.run）。
- 発注・シミュレーション
  - PortfolioSimulator による擬似約定、ポートフォリオ状態管理（backtest.simulator）。
- ユーティリティ
  - 統計ユーティリティ（data.stats）、DB 操作ヘルパー、ログ設定等。

要件
----
- Python 3.10 以上（型注釈で PEP 604 の | を使用）
- 主要ライブラリ（例）
  - duckdb
  - defusedxml
- ネットワークアクセス（API / RSS フェッチ用）
- J-Quants API のリフレッシュトークン等の環境変数（下記参照）

セットアップ手順
----------------
1. リポジトリをクローン／配置
   - 通常はプロジェクトルート（.git または pyproject.toml がある場所）に配置してください。

2. Python 仮想環境の作成とライブラリのインストール
   - 例:
     - python -m venv .venv
     - source .venv/bin/activate
     - pip install duckdb defusedxml

   ※ 実際のプロジェクトでは requirements.txt / pyproject.toml を用意して pip install -r を実行してください。

3. 環境変数の設定
   - .env または OS 環境変数で下記を設定します（config.Settings 参照）。
     - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（必須）
     - KABU_API_PASSWORD     : kabuステーション API パスワード（必須）
     - KABU_API_BASE_URL     : kabu API のベース URL（省略可、デフォルト http://localhost:18080/kabusapi）
     - SLACK_BOT_TOKEN       : Slack Bot トークン（必須）
     - SLACK_CHANNEL_ID      : 通知先 Slack チャンネル ID（必須）
     - DUCKDB_PATH           : DuckDB のファイルパス（省略時 data/kabusys.duckdb）
     - SQLITE_PATH           : 監視用 SQLite（省略時 data/monitoring.db）
     - KABUSYS_ENV           : 実行環境（development / paper_trading / live、デフォルト development）
     - LOG_LEVEL             : ログレベル（DEBUG/INFO/...、デフォルト INFO）
   - 自動 .env ロードを無効化したい場合:
     - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動ロードを無効にできます。

   - .env の書式はシンプルな KEY=VALUE 形式で、' または " で囲った値や export プレフィックスもサポートします。

4. データベーススキーマの初期化
   - Python から:
     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")
   - ":memory:" を指定すればインメモリ DB になります（バックテスト等のテストに便利）。

基本的な使い方（例）
--------------------

1. DuckDB スキーマ初期化（1回）
   - init_schema("data/kabusys.duckdb")

2. ETL（株価差分取得の例）
   - data.pipeline.run_prices_etl(conn, target_date=日付)
     - 差分取得、保存、品質チェックを行います（関数は pipeline モジュール内に定義）。
     - 他にも financials/calen dar の ETL 関数があります。

3. ニュース収集
   - data.news_collector.run_news_collection(conn, sources=..., known_codes=...)

4. 特徴量作成（features テーブル生成）
   - from kabusys.strategy import build_features
     build_features(conn, target_date=日付)

5. シグナル生成
   - from kabusys.strategy import generate_signals
     generate_signals(conn, target_date=日付, threshold=0.6, weights=None)

6. バックテスト（CLI）
   - python -m kabusys.backtest.run --start 2023-01-01 --end 2023-12-31 --db data/kabusys.duckdb
   - オプション: --cash, --slippage, --commission, --max-position-pct
   - 戻り値は CLI 出力と、内部で生成される履歴／トレード／メトリクス（Python API 版: run_backtest）

7. バックテスト（Python API）
   - from kabusys.backtest.engine import run_backtest
     result = run_backtest(conn, start_date, end_date, initial_cash=10000000)
     # result.history, result.trades, result.metrics を参照

追加のサンプル（Python）
- DB 初期化と特徴量→シグナル生成の流れ
  from datetime import date
  from kabusys.data.schema import init_schema
  from kabusys.strategy import build_features, generate_signals

  conn = init_schema("data/kabusys.duckdb")
  target = date(2024, 1, 31)
  # features を作る（prices_daily / raw_financials が必要）
  build_features(conn, target)
  # シグナル生成（ai_scores は省略可）
  generate_signals(conn, target)

ディレクトリ構成（主要ファイル）
------------------------------
src/kabusys/
- __init__.py
- config.py
  - 環境変数・設定管理（自動 .env ロード、Settings クラス）
- data/
  - __init__.py
  - jquants_client.py      : J-Quants API クライアント（取得・保存ユーティリティ）
  - news_collector.py      : RSS フィード収集・前処理・DB 保存
  - schema.py              : DuckDB スキーマ定義・初期化（init_schema）
  - stats.py               : Zスコア等の統計ユーティリティ
  - pipeline.py            : ETL パイプライン（差分更新・品質チェック等）
- research/
  - __init__.py
  - factor_research.py     : モメンタム / バリュー / ボラティリティ等のファクター計算
  - feature_exploration.py : 将来リターン / IC / 統計サマリー
- strategy/
  - __init__.py
  - feature_engineering.py : ファクター正規化・ユニバースフィルタ・features への保存
  - signal_generator.py    : final_score 計算・BUY/SELL シグナル生成
- backtest/
  - __init__.py
  - engine.py              : バックテストループ・データコピー・結果集計
  - simulator.py           : PortfolioSimulator、約定ロジック、スナップショット
  - metrics.py             : バックテスト評価指標計算（CAGR、Sharpe 等）
  - run.py                 : CLI エントリポイント（python -m kabusys.backtest.run）
  - clock.py               : 模擬時計（将来の拡張用）
- execution/
  - __init__.py
  - （発注 / 実行関連モジュールを追加する想定）
- monitoring/
  - （監視・外部通知（Slack等）に関するモジュールを追加する想定）

設計上の注意点 / 運用メモ
------------------------
- ルックアヘッドバイアス対策:
  - ファクター算出やシグナル生成は target_date 時点の利用可能データのみを参照するよう設計されています。
  - J-Quants の取得時は fetched_at を記録して「いつデータが利用可能になったか」を追跡します。
- 冪等性:
  - DB への保存関数は ON CONFLICT / DO UPDATE や DO NOTHING を多用して冪等化しています。
- レート制限とリトライ:
  - jquants_client は固定間隔スロットリング、リトライ（指数バックオフ）、401 時のトークン自動リフレッシュを実装しています。
- セキュリティ & 安全:
  - news_collector は SSRF 対策、最大レスポンスサイズチェック、defusedxml による XML パース保護を実施しています。
- 開発／テスト:
  - KABUSYS_DISABLE_AUTO_ENV_LOAD をセットすると自動的な .env 読み込みを抑止できます（テスト時に環境変数を注入したい場合に便利）。
  - インメモリ DuckDB（":memory:"）を使うと単体テストやバックテスト高速化に便利です。

トラブルシューティング
----------------------
- 環境変数不足で ValueError が発生する場合は .env を確認してください（config._require が未設定時に例外）。
- DuckDB のテーブルが存在しない／空の場合は init_schema() を実行してください。
- J-Quants API 接続失敗時はログ（HTTP エラー / レスポンス内容）を確認し、トークンやネットワークを確認してください。

ライセンス / 貢献
-----------------
（このリポジトリにライセンス情報があればここに記載してください。ない場合はプロジェクトのポリシーに従って追加してください）

最後に
------
この README はコードベースの主要な機能と利用方法をまとめたものです。モジュールの詳細な仕様（StrategyModel.md、DataPlatform.md、BacktestFramework.md 等）はコード内の docstring と合わせて参照してください。必要であれば、環境別の実行手順（paper_trading / live）や CI／デプロイ手順、テストケースの例を別ファイルで補足できます。