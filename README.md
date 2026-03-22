KabuSys
=======

KabuSys は日本株向けの自動売買 / データプラットフォームの参照実装です。  
DuckDB をデータ基盤に、J-Quants API や RSS ニュースを取り込み、ファクター計算、シグナル生成、バックテストを行うモジュール群を含みます。

この README はコードベース（src/kabusys）に基づいた使い方、セットアップ手順、主要機能の説明を日本語でまとめたものです。

要点
----
- 言語: Python（3.10 以上を推奨）
- DB: DuckDB（ファイルまたは ":memory:"）
- 主な依存: duckdb, defusedxml（その他は標準ライブラリ中心に実装）
- 環境変数により API トークン等を管理（.env / .env.local 自動読み込み対応）

プロジェクト概要
--------------
KabuSys は以下のレイヤーで構成される小規模な自動売買プラットフォームです。

- Data Layer: J-Quants API、RSS からのデータ取得、DuckDB スキーマ/ETL（raw → processed → feature）
- Research: ファクター計算（モメンタム、ボラティリティ、バリュー等）や特徴量探索用ユーティリティ
- Strategy: feature を元に final_score を算出し BUY/SELL シグナルを生成
- Backtest: シミュレータ・バックテストエンジン・メトリクス計算
- Execution（プレースホルダ）: 発注／モニタリング周りの実装を想定

主な機能一覧
-------------
- J-Quants API クライアント（data/jquants_client.py）
  - 日足（OHLCV）、財務データ、マーケットカレンダーの取得
  - レートリミット管理・リトライ・トークン自動リフレッシュ・ページネーション対応
  - DuckDB への冪等保存（ON CONFLICT / upsert）
- RSS ニュース収集（data/news_collector.py）
  - RSS 取得、SSRF 対策、URL 正規化、記事ID生成、raw_news 保存、銘柄抽出
- スキーマ定義・初期化（data/schema.py）
  - Raw / Processed / Feature / Execution レイヤーのテーブルを定義
  - init_schema(db_path) による初期化（":memory:" も可）
- ETL パイプライン補助（data/pipeline.py）
  - 差分取得、バックフィル対応、品質チェックフック（quality モジュール）
- ファクター計算（research/factor_research.py）
  - Momentum / Volatility / Value 等を prices_daily / raw_financials から算出
- 特徴量生成（strategy/feature_engineering.py）
  - cross-section の正規化（Z スコア）やユニバースフィルタ適用、features テーブルへの upsert
- シグナル生成（strategy/signal_generator.py）
  - 各コンポーネントスコアの計算、重み付け合算、Bear フィルタ、BUY/SELL 判定、signals テーブルへの書き込み
- バックテスト（backtest/*）
  - PortfolioSimulator（約定・手数料・スリッページモデル）
  - run_backtest()：本番 DB から必要データをコピーして日次ループでシミュレーション
  - metrics（CAGR, Sharpe, MaxDD, 勝率等）
  - CLI: python -m kabusys.backtest.run

セットアップ手順
----------------

1. Python 環境準備
   - Python 3.10 以上を推奨します。
   - 仮想環境を作成して有効化してください。
     - 例:
       - python -m venv .venv
       - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   - 最小依存は duckdb と defusedxml（RSS XML の安全パース用）
   - 例:
     - pip install duckdb defusedxml

   （プロジェクトに requirements.txt / pyproject.toml がある場合はそちらに従ってください。）

3. リポジトリ（パッケージ）のインストール（開発モード推奨）
   - プロジェクトルートで:
     - pip install -e .

4. 環境変数 / .env の準備
   - 自動でプロジェクトルート（.git または pyproject.toml を探索）から .env / .env.local をロードします。
   - 自動ロードを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト時等）。
   - 必須環境変数（config.Settings が参照するもの）
     - JQUANTS_REFRESH_TOKEN  — J-Quants のリフレッシュトークン（必須）
     - KABU_API_PASSWORD      — kabuステーション API のパスワード（必須）
     - SLACK_BOT_TOKEN        — Slack 通知用トークン（必須）
     - SLACK_CHANNEL_ID       — Slack 通知先チャネル ID（必須）
   - 任意 / デフォルト値
     - KABUSYS_ENV            — development / paper_trading / live（デフォルト：development）
     - LOG_LEVEL              — DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト：INFO）
     - KABU_API_BASE_URL      — デフォルト http://localhost:18080/kabusapi
     - DUCKDB_PATH            — デフォルト data/kabusys.duckdb
     - SQLITE_PATH            — デフォルト data/monitoring.db
   - .env の例（.env.example を作る場合のテンプレート）:
     - JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     - KABU_API_PASSWORD=your_kabu_password
     - SLACK_BOT_TOKEN=xoxb-...
     - SLACK_CHANNEL_ID=C01234567
     - DUCKDB_PATH=data/kabusys.duckdb
     - KABUSYS_ENV=development

5. DuckDB スキーマ初期化
   - Python REPL / スクリプトで：
     - from kabusys.data.schema import init_schema
     - conn = init_schema("data/kabusys.duckdb")  # ディレクトリは自動作成されます
     - conn.close()

使い方（主要ワークフロー例）
--------------------------

1. データ取得（ETL）：株価・財務・カレンダーを取得して保存
   - ETL の個別関数を呼ぶ例（Python スクリプト）:
     - from datetime import date
       from kabusys.data.schema import init_schema
       from kabusys.data.pipeline import run_prices_etl
       conn = init_schema("data/kabusys.duckdb")
       result = run_prices_etl(conn, target_date=date.today())
       conn.close()
     - run_prices_etl は J-Quants API トークン（settings.jquants_refresh_token）を使用します。

2. 特徴量の構築（features 作成）
   - DuckDB 接続と日付を与えて実行:
     - from kabusys.data.schema import init_schema
       from kabusys.strategy import build_features
       conn = init_schema("data/kabusys.duckdb")
       cnt = build_features(conn, target_date=date(2024, 1, 4))
       conn.close()
     - build_features は prices_daily / raw_financials を参照し features テーブルを upsert します。

3. シグナル生成
   - generate_signals を呼ぶと features / ai_scores / positions を参照して signals テーブルへ書き込みます:
     - from kabusys.strategy import generate_signals
       generate_signals(conn, target_date=date(2024, 1, 4), threshold=0.6)

4. ニュース収集
   - RSS 取得→ raw_news 挿入、銘柄紐付け:
     - from kabusys.data.news_collector import run_news_collection
       res = run_news_collection(conn, sources=None, known_codes=set_of_valid_codes)
     - sources を指定しなければデフォルトの RSS ソース群を使用します。

5. バックテスト（CLI/モジュール）
   - CLI 例:
     - python -m kabusys.backtest.run --start 2023-01-01 --end 2023-12-31 --db data/kabusys.duckdb
     - 事前条件: 指定 DB に prices_daily, features, ai_scores, market_regime, market_calendar が用意されていること
   - API 例（スクリプト）:
     - from datetime import date
       from kabusys.data.schema import init_schema
       from kabusys.backtest.engine import run_backtest
       conn = init_schema("data/kabusys.duckdb")
       result = run_backtest(conn, start_date=date(2023,1,4), end_date=date(2023,12,29))
       conn.close()
     - run_backtest は内部でデータをコピーしてインメモリ DuckDB を作成し日次ループでシミュレーションを行います。

開発・運用時の注意点 / トラブルシューティング
---------------------------------------------
- .env 自動読み込み
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動ロードを無効化できます（テスト時に便利）。
  - パッケージはプロジェクトルート（.git または pyproject.toml）を基準に .env/.env.local を探索します。
- 環境変数未設定時は config.Settings のプロパティが ValueError を投げます（必須トークン等）。
- J-Quants API はレート制限があるため大量リクエスト時は間引き（pipeline 側で差分取得）を推奨します。
- DuckDB のテーブル構造は data/schema.py に定義されています。スキーマ変更時は互換性に注意してください。
- RSS 取得では SSRF 回避や最大レスポンスサイズチェックなど安全対策を盛り込んでいます。ローカル内部 URL を渡すと取得を拒否します。

ディレクトリ構成（抜粋）
-----------------------
src/kabusys/
- __init__.py
- config.py                        — 環境変数 / 設定管理（.env 自動ロード）
- data/
  - __init__.py
  - jquants_client.py               — J-Quants API クライアント + 保存ロジック
  - news_collector.py               — RSS 収集・正規化・保存
  - pipeline.py                     — ETL パイプライン（差分取得、バックフィル）
  - schema.py                       — DuckDB スキーマ定義 / init_schema
  - stats.py                        — z-score 等の統計ユーティリティ
- research/
  - __init__.py
  - factor_research.py              — モメンタム / ボラティリティ / バリュー計算
  - feature_exploration.py          — IC / forward returns / summary 等
- strategy/
  - __init__.py
  - feature_engineering.py          — features 作成（正規化・ユニバースフィルタ）
  - signal_generator.py             — final_score 計算・BUY/SELL 判定・signals 書き込み
- backtest/
  - __init__.py
  - engine.py                       — run_backtest（メインループ）
  - simulator.py                    — PortfolioSimulator（約定・履歴管理）
  - metrics.py                      — バックテスト評価指標
  - run.py                          — CLI エントリポイント
  - clock.py                        — 将来拡張用の模擬時計
- execution/                        — 発注／実行層（現状プレースホルダ）
- monitoring/                       — 監視・通知（将来）

主要モジュールの短説明
- config.Settings: 必須/任意の環境変数をプロパティ経由で扱う。is_live / is_paper / is_dev を提供。
- data.schema.init_schema(db_path): DuckDB のテーブルを全て作成（冪等）。parent ディレクトリ自動作成。
- data.jquants_client: rate limiter、retry（指数バックオフ）、token refresh、save_* 系で DuckDB に保存。
- strategy.feature_engineering.build_features(conn, target_date): features テーブルへ日付単位で置換保存（冪等）。
- strategy.signal_generator.generate_signals(conn, target_date, threshold, weights): signals を日付単位で置換保存。
- backtest.engine.run_backtest(conn, start_date, end_date, ...): 本番 DB から必要データをコピーしてシミュレーションを行う。

ライセンス / コントリビューション
----------------------------------
本 README に含まれる情報はコードベースの解析に基づくドキュメントです。実運用にあたってはテスト・セキュリティレビュー、依存パッケージの整備を行ってください。README 上にライセンス表記がないため、リポジトリの LICENSE ファイルやプロジェクトポリシーに従ってください。

最後に
------
何をしたいか（例: 「バックテストの実行方法を詳しく知りたい」「ETL の自動化スケジュール化を知りたい」「特定の機能の API サンプルがほしい」）を教えていただければ、該当部分を詳しく掘り下げたドキュメントや実行スクリプト例を作成します。