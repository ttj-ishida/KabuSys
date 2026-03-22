KabuSys
=======

日本株向けの自動売買 / データ基盤ライブラリです。  
DuckDB をデータストアとして用い、J-Quants からの市場データ取得、ETL、特徴量生成、シグナル作成、バックテストフレームワークを備えています。  
本 README はリポジトリ内の主要モジュール群（data / research / strategy / backtest / execution 等）を使い始めるための概要と手順をまとめたものです。

概要
----
KabuSys は以下のレイヤーを持つ設計です。

- Data（data/*）: J-Quants からの取得クライアント、RSS ニュース収集、DuckDB スキーマ定義、ETL パイプライン、統計ユーティリティなど。
- Research（research/*）: ファクター算出・特徴量探索・IC 計算など研究向けユーティリティ。
- Strategy（strategy/*）: 特徴量の正規化・統合と売買シグナル生成ロジック。
- Backtest（backtest/*）: シミュレータ、バックテストループ、評価指標計算、CLI ランナー。
- Execution（execution/*）: 発注・モニタリング層（このコードベースでは層の骨組みを提供）。

特徴
----
主な機能

- J-Quants API クライアント（ページネーション・レート制御・自動トークンリフレッシュ・リトライ実装）
- RSS ベースのニュース収集と記事→銘柄紐付け
- DuckDB ベースのスキーマ（raw / processed / feature / execution 層）
- ファクター計算（Momentum / Volatility / Value 等）とクロスセクショナル Z スコア正規化
- 特徴量作成（build_features）とシグナル生成（generate_signals）
- バックテストエンジン（PortfolioSimulator, run_backtest）とメトリクス計算
- バックテスト用 CLI（python -m kabusys.backtest.run）
- 各モジュールは DB 接続（DuckDB）を受け取り DB を直接操作（テストしやすい設計）

動作要件（例）
--------------
- Python 3.10+
- duckdb
- defusedxml
- （標準ライブラリ：urllib, datetime, logging, math 等）

インストール（開発環境）
----------------------
1. 仮想環境を用意（推奨）
   - python -m venv .venv
   - source .venv/bin/activate もしくは .venv\Scripts\activate

2. 依存ライブラリをインストール
   - pip install duckdb defusedxml
   - （パッケージ化されている場合）pip install -e .

環境変数（設定）
----------------
設定は .env ファイルまたは環境変数から読み込まれます（kabusys.config が自動ロード）。自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

主な必須環境変数
- JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD     : kabuステーション API 用パスワード（必須）
- SLACK_BOT_TOKEN       : Slack 通知用 Bot トークン（必須）
- SLACK_CHANNEL_ID      : Slack チャンネル ID（必須）

任意 / デフォルトあり
- KABUS_API_BASE_URL    : kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH           : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH           : 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV           : 実行環境（development / paper_trading / live。デフォルト: development）
- LOG_LEVEL             : ログレベル（DEBUG/INFO/...。デフォルト: INFO）

セットアップ手順（クイック）
-------------------------
1. DuckDB スキーマ初期化
   - Python REPL で:
     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")
     conn.close()
   - ":memory:" を渡すとインメモリ DB を初期化できます。

2. J-Quants データ取得（例）
   - from datetime import date
     from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes
     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")
     recs = fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
     save_daily_quotes(conn, recs)
     conn.close()

3. ニュース収集（RSS）
   - from kabusys.data.news_collector import run_news_collection
     conn = init_schema("data/kabusys.duckdb")
     run_news_collection(conn, known_codes={"7203","6758", ...})
     conn.close()

使い方（代表的な操作）
--------------------

- DB 初期化（スキーマ作成）
  - from kabusys.data.schema import init_schema
    conn = init_schema("data/kabusys.duckdb")

- ETL パイプライン（差分取得）
  - from datetime import date
    from kabusys.data.pipeline import run_prices_etl
    conn = init_schema("data/kabusys.duckdb")
    # run_prices_etl の引数: conn, target_date, id_token (省略可) など
    res = run_prices_etl(conn, target_date=date.today())
    # ETL 結果の確認
    print(res.to_dict())

  - RSS 収集と保存
    from kabusys.data.news_collector import run_news_collection
    run_news_collection(conn, known_codes=set_of_valid_codes)

- 特徴量構築
  - from kabusys.strategy import build_features
    from datetime import date
    count = build_features(conn, target_date=date(2024,1,31))
    # features テーブルに target_date 分を日付単位で置換（冪等）

- シグナル生成
  - from kabusys.strategy import generate_signals
    total = generate_signals(conn, target_date=date(2024,1,31), threshold=0.6)

- バックテスト（プログラム呼び出し）
  - from kabusys.backtest.engine import run_backtest
    result = run_backtest(conn, start_date, end_date, initial_cash=10_000_000)
    # 戻り値は BacktestResult(history, trades, metrics)

- バックテスト CLI
  - python -m kabusys.backtest.run --start 2023-01-01 --end 2023-12-31 --db data/kabusys.duckdb
  - オプション: --cash, --slippage, --commission, --max-position-pct

設計上の注意点
--------------
- ルックアヘッドバイアス回避:
  - 特徴量生成・シグナル生成は target_date 時点の利用可能な情報のみを使用するよう設計されています。
  - raw データには fetched_at（UTC）を保持し、「いつそのデータを知り得たか」をトレース可能にしています。
- 冪等性:
  - 多くの保存処理は ON CONFLICT DO UPDATE / DO NOTHING を用いて冪等に実装されています。
- テスト容易性:
  - ID トークンや HTTP のオープン関数を注入／モックできるよう配慮されています（例: news_collector._urlopen を差し替え可能）。

トラブルシューティング
----------------------
- .env の自動読み込みを無効化したい／テストで制御したい場合:
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を環境変数に設定してください。
- DuckDB のファイルパスに関する権限:
  - init_schema は親ディレクトリを自動作成しますが、書き込み権限が必要です。
- J-Quants API の認証エラー:
  - get_id_token() はリフレッシュトークンが必要です。環境変数 JQUANTS_REFRESH_TOKEN を確認してください。

ディレクトリ構成（主要ファイル）
--------------------------------
src/kabusys/
- __init__.py
- config.py                    # 環境変数・設定管理（.env 自動ロード）
- data/
  - __init__.py
  - jquants_client.py          # J-Quants API クライアント・保存ユーティリティ
  - news_collector.py          # RSS 収集・DB 保存・銘柄抽出
  - pipeline.py                # ETL パイプライン（差分更新など）
  - schema.py                  # DuckDB スキーマ定義・初期化
  - stats.py                   # Z スコア等の統計ユーティリティ
- research/
  - __init__.py
  - factor_research.py         # Momentum / Volatility / Value の算出
  - feature_exploration.py     # 将来リターン・IC・統計サマリー
- strategy/
  - __init__.py
  - feature_engineering.py     # ファクター正規化・features テーブル書き込み
  - signal_generator.py        # final_score 計算と signals テーブル書き込み
- backtest/
  - __init__.py
  - engine.py                  # バックテストループ（run_backtest）
  - simulator.py               # ポートフォリオシミュレータ（擬似約定）
  - metrics.py                 # バックテスト指標計算
  - run.py                     # CLI エントリポイント
  - clock.py                   # 将来拡張用の模擬時計
- execution/                    # 発注実行層（パッケージ化の土台）
- monitoring/                   # 監視 / 通知関連（Slack 等）

API（主要関数・使いどころ）
--------------------------
- kabusys.data.schema.init_schema(db_path) → DuckDB 接続（スキーマ初期化）
- kabusys.data.jquants_client.fetch_daily_quotes(...) / save_daily_quotes(conn, records)
- kabusys.data.news_collector.fetch_rss(url, source) / save_raw_news(conn, articles)
- kabusys.data.pipeline.run_prices_etl(conn, target_date, ...)  # 差分 ETL
- kabusys.strategy.build_features(conn, target_date) → int (upsert count)
- kabusys.strategy.generate_signals(conn, target_date, threshold, weights) → int (signals count)
- kabusys.backtest.engine.run_backtest(conn, start_date, end_date, ...) → BacktestResult
- kabusys.backtest.run (モジュール実行で CLI 起動)

ライセンス・貢献
----------------
本リポジトリのライセンス情報・貢献方法はプロジェクトルートの LICENSE / CONTRIBUTING ファイルを参照してください（存在する場合）。

最後に
------
この README はコード内の docstring と実装に基づいて作成しています。実運用前に .env 設定、J-Quants トークン、DuckDB のバックアップ計画、Slack トークンの適切な保護などを必ず行ってください。必要であれば README に付け加えたい具体的な運用手順（cron/jupiter ノートブック / CI ワークフロー例）を教えてください。