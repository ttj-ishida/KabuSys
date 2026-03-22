KabuSys
=======

日本株向けの自動売買 / データプラットフォーム用ライブラリ群です。  
ファクター計算・特徴量生成・シグナル生成・ニュース収集・ETL・バックテスト等の主要コンポーネントを含み、DuckDB を用いたデータ管理と、J-Quants API や RSS によるデータ取得を想定しています。

本 README はコードベース（src/kabusys）を元にした利用ガイドです。

主な特徴
--------

- データ収集
  - J-Quants API クライアント（差分取得・ページネーション・リトライ・トークン自動更新・レート制御）
  - RSS ベースのニュース収集（トラッキングパラメータ除去、SSRF 対策、gzip / サイズ制限）
- データ基盤
  - DuckDB スキーマの定義と初期化（raw / processed / feature / execution 層）
  - Idempotent な DB 保存（ON CONFLICT / トランザクション・チャンク処理）
- 研究・戦略
  - ファクター計算（モメンタム / ボラティリティ / バリュー 等）
  - 特徴量エンジニアリング（Z スコア正規化、ユニバースフィルタ）
  - シグナル生成（コンポーネントスコア統合、Bear レジーム抑制、BUY/SELL の出力）
- バックテスト
  - ポートフォリオシミュレータ（スリッページ・手数料モデル、約定/決済ロジック）
  - 日次ループを再現する run_backtest（インメモリ DuckDB を用いた安全な検証）
  - バックテスト評価指標（CAGR、Sharpe、最大ドローダウン、勝率、ペイオフ比）
- 汎用ユーティリティ
  - クロスセクションの Z スコア正規化、統計・IC 計算、RSS 前処理など

セットアップ手順
--------------

前提
- Python 3.10+（型注釈で | を使用しているため）
- DuckDB（Python パッケージとしてインストール）
- defusedxml（RSS パース時のセキュリティ対策）

例（venv を使ったローカル開発環境）
1. リポジトリをクローン
   - git clone <repository-url>
2. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  # macOS / Linux
   - .venv\Scripts\activate     # Windows
3. 必要パッケージをインストール
   - pip install duckdb defusedxml
   - （その他必要なパッケージがあれば追加でインストール）
4. データベース初期化
   - Python REPL またはスクリプトから:
     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")  # ":memory:" でインメモリ DB も可
     conn.close()

環境変数
- 自動でプロジェクトルートの .env / .env.local を読み込みます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
- 主な必須環境変数:
  - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
  - KABU_API_PASSWORD: kabuステーション API パスワード（必須）
  - SLACK_BOT_TOKEN: Slack 通知用ボットトークン（必須）
  - SLACK_CHANNEL_ID: Slack 通知先チャンネル ID（必須）
- 任意 / デフォルトあり:
  - KABUSYS_ENV: 実行環境 (development | paper_trading | live)。デフォルト: development
  - LOG_LEVEL: ログレベル (DEBUG|INFO|WARNING|ERROR|CRITICAL)。デフォルト: INFO
  - KABUSYS_DISABLE_AUTO_ENV_LOAD: 1 をセットすると .env の自動ロードを無効化
  - KABUSYS_*（任意に拡張）
- DB パス:
  - DUCKDB_PATH: デフォルト data/kabusys.duckdb
  - SQLITE_PATH: 監視用 DB（デフォルト data/monitoring.db）

使い方（主要ユースケース）
-------------------------

1) DuckDB スキーマ初期化
- Python:
  from kabusys.data.schema import init_schema
  conn = init_schema("data/kabusys.duckdb")
  conn.close()

2) J-Quants から株価を取得して保存
- トークン取得（ライブラリが自動処理するので通常は不要）:
  from kabusys.data.jquants_client import get_id_token
  token = get_id_token()  # settings.jquants_refresh_token を使う
- データ取得と保存:
  from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes
  from kabusys.data.schema import init_schema
  conn = init_schema("data/kabusys.duckdb")
  recs = fetch_daily_quotes(date_from=..., date_to=...)
  saved = save_daily_quotes(conn, recs)

3) ニュース収集（RSS）
- 一括収集:
  from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
  conn = init_schema("data/kabusys.duckdb")
  results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=set(["7203","6758",...]))
  # results はソースごとの新規保存件数を返す

4) 特徴量の構築（features テーブル）
- build_features を実行して features を作成:
  from kabusys.strategy import build_features
  from kabusys.data.schema import init_schema
  from datetime import date
  conn = init_schema("data/kabusys.duckdb")
  n = build_features(conn, target_date=date(2024, 1, 31))
  # n は upsert した銘柄数

5) シグナル生成
- features と ai_scores を用いて signals テーブルを更新:
  from kabusys.strategy import generate_signals
  generate_signals(conn, target_date=date(2024, 1, 31), threshold=0.6)

6) バックテスト
- CLI で実行:
  python -m kabusys.backtest.run --start 2023-01-01 --end 2023-12-31 --db data/kabusys.duckdb
- または API 経由で実行:
  from kabusys.backtest.engine import run_backtest
  result = run_backtest(conn, start_date, end_date, initial_cash=10_000_000)
  # result.metrics に評価指標が入る

7) ETL（パイプライン）
- データ差分取得や品質チェックを実施する ETL モジュールが含まれます（kabusys.data.pipeline）。
- 例: run_prices_etl 等の関数を使って日次差分を取得・保存・チェックします（詳細は pipeline モジュールの API を参照）。

注意点 / 実運用に関するメモ
-------------------------
- J-Quants API はレート制限（120 req/min）を守る実装になっていますが、実行頻度には注意してください。
- DB の初期化 init_schema() は冪等（既存テーブルはスキップ）です。ファイル DB を使う場合は親ディレクトリが自動作成されます。
- ニュース収集は外部 RSS に依存します。SSRF・大容量レスポンス・XML の脆弱性対策を実装していますが、運用時はソース管理・接続先制限を行ってください。
- 環境変数の自動ロードはプロジェクトルート（.git か pyproject.toml）を検出して .env / .env.local を読み込みます。テストや CI では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して無効化できます。
- strategy / execution 層は発注 API との分離を原則としています。実際の発注は execution 層を実装して接続する必要があります。

ディレクトリ構成（概要）
---------------------

src/kabusys/
- __init__.py
- config.py                       # 環境変数 / 設定管理
- data/
  - __init__.py
  - jquants_client.py              # J-Quants API クライアント + 保存関数
  - news_collector.py             # RSS 収集・保存
  - pipeline.py                   # ETL パイプライン（差分取得 / 品質チェック）
  - schema.py                     # DuckDB スキーマ定義 / init_schema
  - stats.py                      # Z スコア等の統計ユーティリティ
- research/
  - __init__.py
  - factor_research.py            # モメンタム/ボラティリティ/バリュー計算
  - feature_exploration.py        # 将来リターン計算 / IC / 統計サマリ
- strategy/
  - __init__.py
  - feature_engineering.py        # features 作成ロジック
  - signal_generator.py           # final_score 計算 → signals 生成
- backtest/
  - __init__.py
  - engine.py                     # run_backtest（インメモリコピー＋日次ループ）
  - simulator.py                  # PortfolioSimulator（擬似約定）
  - metrics.py                    # バックテスト評価指標計算
  - clock.py                      # 将来の拡張用：模擬時計
  - run.py                        # CLI エントリポイント（python -m kabusys.backtest.run）
- execution/                       # 発注関連のエントリ（未実装／拡張ポイント）
- monitoring/                      # 監視・メトリクス関連（拡張ポイント）

貢献 / 開発ガイドライン
-----------------------
- リポジトリの動作を壊さないため、DB スキーマ変更は互換性（既存データ）を考慮してください。
- 外部 API に対する機能追加はレート制御・リトライ・ログ・可観測性（fetched_at）を満たしてください。
- ニュースや外部 URL を扱う箇所では SSRF / XML インジェクション / レスポンスサイズ制限 を必ず考慮してください。

補足
----
- 本 README はコードベースに含まれる docstring / コメントを元に作成しています。各モジュール内に詳細な設計ノート（StrategyModel.md, DataPlatform.md 等）が参照されている箇所があります。追加ドキュメントがリポジトリにある場合はそちらも参照してください。
- 実運用には API キーの管理、監査ログ、権限分離、監視/アラートの実装が推奨されます。

必要な追加情報や、特定の使い方（例: ETL の cron 設定、kabuステーション連携方法、Slack 通知の設定例）を希望される場合は教えてください。具体例を付けて追補します。