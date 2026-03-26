README
======

プロジェクト概要
---------------
KabuSys は日本株向けの自動売買／研究プラットフォームです。  
主な目的は以下のとおりです。

- DuckDB を用いた時系列データ管理・ETL（株価・財務・ニュース等）
- 研究（ファクター計算・特徴量正規化・IC解析）
- シグナル生成（複数ファクターと AI スコアの統合）
- ポートフォリオ構築（候補選定、重み付け、リスク制約、サイジング）
- バックテスト（擬似約定モデル、パフォーマンス指標）
- ニュース収集（RSS ベースの収集・正規化・銘柄紐付け）

コードはモジュール化されており、ETL・研究・戦略・バックテスト・実運用の各層が分離されています。

機能一覧
--------
- データ取得/保存
  - J-Quants API クライアント（レートリミット / リトライ / トークン自動リフレッシュ対応）
  - 日足・財務・マーケットカレンダーの取得と DuckDB への保存
  - RSS ニュース収集（SSRF 対策、トラッキングパラメータ除去、記事ID生成）
- 研究（research）
  - Momentum / Volatility / Value 等のファクター計算
  - 将来リターン（forward returns）と IC（Spearman）計算
  - ファクター統計サマリー
- 特徴量生成（strategy.feature_engineering）
  - ユニバースフィルタ、Z スコア正規化、features テーブルへ UPSERT
- シグナル生成（strategy.signal_generator）
  - 複数コンポーネントスコアを統合して final_score を算出
  - Bear レジームでの BUY 抑制、SELL（ストップロス / スコア低下）判定
  - signals テーブルへ冪等書き込み
- ポートフォリオ構築
  - 候補選定、等金額/スコア加重配分、リスクベースサイジング
  - セクター上限（apply_sector_cap）・レジーム乗数（calc_regime_multiplier）
  - 単元丸め・コストバッファ・aggregate cap によるスケーリング
- バックテスト
  - run_backtest：DB をコピーしてインメモリでバックテスト実行
  - 擬似約定モデル（スリッページ・手数料・部分約定・マーク・トゥ・マーケット）
  - 指標計算（CAGR、Sharpe、Max Drawdown、勝率、Payoff 等）
  - CLI 入口（python -m kabusys.backtest.run）
- その他
  - 設定管理（kabusys.config: .env ファイル自動読み込み・必須 env チェック）
  - ニュースの銘柄抽出・news_symbols への保存

動作要件（推奨）
----------------
- Python 3.10+
- 主要依存（例）
  - duckdb
  - defusedxml
  - 標準ライブラリ（urllib, logging, typing 等）

セットアップ手順
---------------
1. リポジトリをクローンして開発インストール
   - 例:
     - git clone <repo>
     - cd <repo>
     - python -m pip install -e .

   pyproject.toml / setup.py が存在する前提で editable インストールを推奨します。

2. 必要な環境変数を準備
   - プロジェクトルート（.git または pyproject.toml があるディレクトリ）に .env を置くと自動読み込みされます（kabusys.config が自動でロード）。
   - 自動ロードを無効化する場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

   代表的な環境変数（必須/省略時デフォルトあり）:
   - JQUANTS_REFRESH_TOKEN (必須) — J-Quants リフレッシュトークン
   - KABU_API_PASSWORD (必須) — kabuステーション API パスワード
   - KABU_API_BASE_URL (任意) — デフォルト: http://localhost:18080/kabusapi
   - SLACK_BOT_TOKEN (必須) — Slack 通知用トークン
   - SLACK_CHANNEL_ID (必須) — Slack チャンネル ID
   - DUCKDB_PATH (任意) — デフォルト: data/kabusys.duckdb
   - SQLITE_PATH (任意) — デフォルト: data/monitoring.db
   - KABUSYS_ENV (任意) — 有効値: development / paper_trading / live（デフォルト: development）
   - LOG_LEVEL (任意) — DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）

   .env の簡単な例:
   - JQUANTS_REFRESH_TOKEN=your_refresh_token
   - KABU_API_PASSWORD=your_kabu_password
   - SLACK_BOT_TOKEN=xoxb-...
   - SLACK_CHANNEL_ID=C01234567

3. DuckDB スキーマ初期化
   - 本リポジトリでは kabusys.data.schema.init_schema() を通じてスキーマ初期化が行われる想定です（実装ファイルがプロジェクト内にある場合）。  
   - 事前に prices_daily / raw_financials / market_calendar / stocks / features / ai_scores / signals / positions 等のテーブルが必要になります。ETL を通じてデータを投入してください（J-Quants API 経由等）。

使い方
------

1) バックテスト（CLI）
   - 付属の CLI を使ってバックテストを実行できます（例は python -m での起動）。
   - 例:
     python -m kabusys.backtest.run \
       --start 2023-01-01 --end 2023-12-31 \
       --cash 10000000 \
       --db path/to/kabusys.duckdb

   - 主なオプション:
     - --start / --end: バックテスト期間（YYYY-MM-DD）
     - --cash: 初期資金（JPY）
     - --slippage / --commission: コスト係数
     - --allocation-method: equal | score | risk_based
     - --max-positions: 最大保有数
     - --lot-size: 単元株数（日本株は通常 100）
     - --db: DuckDB ファイルパス（必須）

2) バックテスト（Python API）
   - プログラムから実行する場合:
     from kabusys.data.schema import init_schema
     from kabusys.backtest.engine import run_backtest

     conn = init_schema("path/to/kabusys.duckdb")
     try:
         result = run_backtest(conn, start_date, end_date, initial_cash=10_000_000)
     finally:
         conn.close()

   - run_backtest は BacktestResult を返し、result.metrics に評価指標が入ります。

3) 特徴量作成 / シグナル生成（Python）
   - build_features: features テーブルを構築
     from kabusys.strategy import build_features
     build_features(conn, target_date)

   - generate_signals: signals テーブルを生成
     from kabusys.strategy import generate_signals
     generate_signals(conn, target_date, threshold=0.6)

   - どちらも DuckDB 接続（init_schema が返す接続）と target_date を受けます。

4) J-Quants データ取得（Python）
   - トークン取得:
     from kabusys.data.jquants_client import get_id_token
     token = get_id_token()

   - データ取得と保存:
     from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes
     records = fetch_daily_quotes(id_token=token, date_from=..., date_to=...)
     save_daily_quotes(conn, records)

5) ニュース収集
   - RSS 収集・保存の統合関数:
     from kabusys.data.news_collector import run_news_collection
     result = run_news_collection(conn, sources=None, known_codes=set_of_codes)

   - run_news_collection は各ソースごとの新規保存数を返します。

設定・実装上の注意
-----------------
- .env 自動読み込み:
  - kabusys.config はプロジェクトルート（.git または pyproject.toml）を探索し、.env と .env.local を読み込みます。
  - 読み込み順: OS 環境変数 > .env.local > .env
  - テスト等で自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

- KABUSYS_ENV: development / paper_trading / live のいずれかを指定。live 時は実運用向けの挙動（コード中で is_live 判定が使われます）になります。

- データの冪等性:
  - 多くの保存処理（raw_prices, raw_financials, market_calendar, raw_news など）は ON CONFLICT / DO UPDATE や DO NOTHING を使い冪等性を保っています。

ディレクトリ構成（抜粋）
----------------------
src/kabusys/
- __init__.py
- config.py                             — 環境変数・設定管理
- data/
  - jquants_client.py                    — J-Quants API クライアント, 保存ユーティリティ
  - news_collector.py                    — RSS ニュース収集・保存
  - (schema.py, calendar_management.py 等は実装を参照)
- research/
  - factor_research.py                   — Momentum / Volatility / Value 計算
  - feature_exploration.py               — forward returns / IC / summary
- strategy/
  - feature_engineering.py               — features 作成パイプライン
  - signal_generator.py                  — final_score 計算、signals 作成
- portfolio/
  - portfolio_builder.py                 — 候補選定、重み計算
  - position_sizing.py                   — 発注株数算出（risk_based / weight-based）
  - risk_adjustment.py                   — セクター上限・レジーム乗数
- backtest/
  - engine.py                            — バックテストループとユーティリティ
  - simulator.py                         — 擬似約定・ポートフォリオ管理
  - metrics.py                           — パフォーマンス指標計算
  - run.py                               — CLI エントリポイント
  - clock.py
- portfolio/ (公開 API 経由)
- strategy/ (公開 API)
- research/ (公開 API)
- execution/ (空パッケージ placeholder)
- monitoring/ (placeholder)

（実際のファイル一覧はリポジトリの src/kabusys 以下を参照してください）

開発メモ
--------
- DuckDB を使っているため、データ取得→ETL→features→signals→バックテスト の流れを順に整えることが重要です。
- look-ahead bias を避けるため、各計算は target_date 時点で利用可能なデータのみを参照する設計になっています（fetched_at の管理等）。
- ニュース収集は SSRF・Gzip Bomb 等の攻撃を考慮した設計です（defusedxml, ホスト検査, レスポンス上限など）。

貢献・ライセンス
----------------
- 本 README にライセンス情報は含まれていません。リポジトリの LICENSE ファイルを参照してください。  
- バグ報告・プルリクエストは Issues / PR でどうぞ。

以上。README に不足している詳細（例えば schema の初期化手順や exact requirements.txt）はリポジトリ内の該当ファイルを参照のうえ追記してください。