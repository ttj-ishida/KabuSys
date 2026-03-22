README
======

概要
----
KabuSys は日本株向けの自動売買／データプラットフォームのための Python ライブラリです。  
DuckDB をデータストアとして用い、J-Quants API や RSS フィードから市場データ・財務データ・ニュースを収集し、ファクター計算、シグナル生成、バックテスト、簡易的な実行（execution 層）をサポートします。  
研究（research）用ユーティリティも含まれ、戦略開発から検証までを一貫して扱える設計になっています。

主な特徴
--------
- データ取得
  - J-Quants API クライアント（株価日足、財務データ、JPX カレンダー）
  - RSS ベースのニュース収集（トラッキングパラメータ除去、SSRF 対策、gzip 対応）
- データ永続化
  - DuckDB スキーマ定義と初期化（冪等：ON CONFLICT / DO UPDATE 等で重複排除）
  - raw / processed / feature / execution の4層テーブル設計
- ETL パイプライン
  - 差分更新・バックフィル対応、品質チェックフック（quality モジュール想定）
- 研究（Research）
  - ファクター計算（モメンタム / ボラティリティ / バリュー 等）
  - ファクター探索ユーティリティ（将来リターン計算、IC 計算、統計サマリー）
  - Z スコア正規化ユーティリティ
- 戦略（Strategy）
  - 特徴量生成（features テーブルの構築）
  - シグナル生成（features と AI スコアを統合、BUY/SELL を生成）
  - Bear 相場抑制、重み指定、閾値調整などをサポート
- バックテスト
  - 日次ループのシミュレータ（手数料・スリッページ・ポートフォリオサイジングを考慮）
  - 戦略を用いた日次シミュレーション、評価指標（CAGR、Sharpe、Max Drawdown 等）
  - CLI 実行スクリプト（python -m kabusys.backtest.run）
- 安全性と堅牢性
  - API レート制御・リトライ（指数バックオフ）
  - RSS パース時の XML 脆弱性対策（defusedxml）
  - URL 正規化・SSRF 対策、サイズ制限

セットアップ
----------
前提
- Python 3.10 以上（型ヒントに | 演算子等を使用）
- DuckDB を使用するため、対応する Python バインディングが必要

最低限の依存パッケージ例
- duckdb
- defusedxml

インストール例（仮にプロジェクトルートで実行）
1. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   - pip install duckdb defusedxml

3. ローカル開発インストール（パッケージ化されている場合）
   - pip install -e .

環境変数
- 自動的にプロジェクトルートの .env / .env.local を読み込みます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
- 主に使用する環境変数:
  - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
  - KABU_API_PASSWORD: kabu API パスワード（必須）
  - KABU_API_BASE_URL: kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
  - SLACK_BOT_TOKEN: Slack 通知用 Bot トークン（必須）
  - SLACK_CHANNEL_ID: Slack チャンネル ID（必須）
  - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH: SQLite（モニタリング用）パス（デフォルト: data/monitoring.db）
  - KABUSYS_ENV: 実行環境（development / paper_trading / live、デフォルト development）
  - LOG_LEVEL: ログレベル（DEBUG, INFO, WARNING, ERROR, CRITICAL）
- サンプル .env（任意）
  - JQUANTS_REFRESH_TOKEN=your_refresh_token
  - KABU_API_PASSWORD=your_kabu_password
  - SLACK_BOT_TOKEN=xoxb-...
  - SLACK_CHANNEL_ID=C12345678
  - DUCKDB_PATH=data/kabusys.duckdb
  - KABUSYS_ENV=development

簡単な使い方（コード例）
------------------------

1) DuckDB スキーマ初期化
- Python REPL / スクリプト内で:
  from kabusys.data.schema import init_schema
  conn = init_schema("data/kabusys.duckdb")
  # 終了時
  conn.close()

2) J-Quants からデータ取得して保存（例: 日足）
  from kabusys.data import jquants_client as jq
  from kabusys.data.schema import init_schema
  conn = init_schema("data/kabusys.duckdb")
  quotes = jq.fetch_daily_quotes(date_from=date(2023,1,1), date_to=date(2023,1,31))
  saved = jq.save_daily_quotes(conn, quotes)
  conn.close()

3) ニュース収集の実行（RSS）
  from kabusys.data.news_collector import run_news_collection
  conn = init_schema("data/kabusys.duckdb")
  # known_codes: 銘柄抽出に使う有効なコード集合（例: {"7203","6758",...}）
  results = run_news_collection(conn, known_codes=set(["7203","6758"]))
  conn.close()

4) 特徴量構築（features テーブルへ書き込む）
  from datetime import date
  from kabusys.strategy import build_features
  from kabusys.data.schema import init_schema
  conn = init_schema("data/kabusys.duckdb")
  count = build_features(conn, target_date=date(2024,1,31))
  conn.close()

5) シグナル生成
  from datetime import date
  from kabusys.strategy import generate_signals
  conn = init_schema("data/kabusys.duckdb")
  total = generate_signals(conn, target_date=date(2024,1,31))
  conn.close()

6) バックテスト（CLI）
  python -m kabusys.backtest.run \
      --start 2023-01-01 --end 2023-12-31 \
      --cash 10000000 --db data/kabusys.duckdb

7) バックテスト（プログラム的に）
  from datetime import date
  from kabusys.data.schema import init_schema
  from kabusys.backtest.engine import run_backtest
  conn = init_schema("data/kabusys.duckdb")
  res = run_backtest(conn, start_date=date(2023,1,4), end_date=date(2023,12,29))
  # res.history, res.trades, res.metrics を利用
  conn.close()

ETL パイプライン（pipeline モジュール）
- 差分取得ロジック、バックフィル、品質チェックを組み合わせた ETL 実行用関数群が用意されています（run_prices_etl など）。
- 例（概略）:
  from kabusys.data.pipeline import run_prices_etl
  conn = init_schema("data/kabusys.duckdb")
  fetched, saved = run_prices_etl(conn, target_date=date.today())
  conn.close()

注意点・設計上のポイント
-----------------------
- 自動環境変数読み込み: .env / .env.local をプロジェクトルートから検出して自動読み込みします。テストなどで無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB の初回は init_schema() を実行してスキーマを作成してください（":memory:" でのインメモリ利用も可能）。
- J-Quants API: リフレッシュトークンから ID トークンを取得するフローを実装済みで、401 時の自動リフレッシュやページネーション処理、レート制御・リトライを含みます。
- News Collector: RSS の取得・解析では SSRF 対策、XML の安全パース、受信サイズ制限、トラッキングパラメータ除去などの対策が盛り込まれています。
- 戦略モジュールは発注 API（execution 層）へ直接依存しない設計です。signals テーブルへ出力して、実行／発注層がそれを消費する想定です。
- バックテストでは本番 DB を汚さないためにインメモリ DuckDB に期間データをコピーして実行します。

ディレクトリ構成
----------------
（主要ファイル / モジュールのみ抜粋）

- src/kabusys/
  - __init__.py
  - config.py                  # 環境変数・設定管理
  - data/
    - __init__.py
    - jquants_client.py        # J-Quants API クライアント + DB 保存
    - news_collector.py        # RSS ニュース収集・保存
    - schema.py                # DuckDB スキーマ定義・初期化
    - stats.py                 # 統計ユーティリティ（zscore 正規化等）
    - pipeline.py              # ETL パイプライン
  - research/
    - __init__.py
    - factor_research.py       # モメンタム/バリュー/ボラティリティ等のファクター計算
    - feature_exploration.py   # IC/将来リターン/統計サマリー
  - strategy/
    - __init__.py
    - feature_engineering.py   # raw factor → features テーブルへの変換
    - signal_generator.py      # features + ai_scores → signals 生成
  - backtest/
    - __init__.py
    - engine.py                # バックテスト全体ループ
    - simulator.py             # 約定シミュレータ・ポートフォリオ管理
    - metrics.py               # バックテスト評価指標
    - clock.py                 # 模擬時計（将来拡張用）
    - run.py                   # CLI エントリポイント
  - execution/                  # 発注実装用のプレースホルダ（空 __init__）
  - monitoring/                 # 監視・モニタリング関連（未記載の詳細）

貢献・拡張
----------
- 新しいデータソース（別 API、別 RSS）や品質チェックルール、execution 層（kabu ステーション連携等）の実装を歓迎します。
- 単体テスト（モジュール単位の関数テスト）や CI 設定を追加すると品質が向上します。
- config.py の自動.envロードの挙動はテスト環境向けに切り替え可能です。

ライセンス
---------
- 本リポジトリ内に明示的なライセンスファイルが無い場合は、使用前にリポジトリ管理者に確認してください。

補足
----
- ドキュメント内の「StrategyModel.md」「DataPlatform.md」「BacktestFramework.md」などはコード内のコメントで参照されています。詳細な設計仕様書が別途ある場合はそちらも参照してください。
- 実運用する際は API トークン、Slack トークン等の機密情報管理に十分注意してください（例: secrets manager、環境変数の管理等）。

以上。プロジェクトの利用開始や開発にあたって不明点があれば、用途（ETL / backtest / live 実行 など）を教えてください。具体的な実行例や .env.example のテンプレートも用意します。