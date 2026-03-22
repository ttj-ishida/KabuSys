KabuSys
=======

KabuSys は日本株のデータ取得、特徴量生成、シグナル生成、バックテスト、ニュース収集を含む自動売買プラットフォームのコアライブラリです。本リポジトリは DuckDB をデータ層に用い、J-Quants API や RSS からのデータ収集、戦略用のファクター計算、バックテストフレームワーク、ニュース収集のユーティリティを提供します。

主な特徴
--------
- データ層
  - DuckDB スキーマ定義・初期化（冪等）
  - J-Quants API クライアント（ページネーション、リトライ、トークン自動リフレッシュ、レートリミット制御）
  - RSS ベースのニュース収集（SSRF 対策、gzip/サイズ制限、トラッキングパラメータ除去）
  - 生データ / 処理済みデータ / 特徴量 / 実行層のテーブル定義（DataSchema.md に準拠）
- 研究・特徴量
  - Momentum / Volatility / Value などのファクター計算（prices_daily / raw_financials を利用）
  - クロスセクション Z スコア正規化ユーティリティ
  - ファクター探索（将来リターン、IC, 統計サマリ）
- 戦略
  - 特徴量の組成とユニバースフィルタ（build_features）
  - 正規化済みファクター + AIスコアを統合して最終スコアを算出し BUY/SELL シグナルを生成（generate_signals）
  - Bear 相場抑制、ストップロスなどのポリシー実装
- バックテスト
  - 日次シミュレーション（擬似約定、スリッページ・手数料モデル）
  - ポートフォリオシミュレータ、トレード記録、日次スナップショット
  - メトリクス算出（CAGR, Sharpe, Max Drawdown, Win rate, Payoff ratio 等）
  - CLI エントリポイントでバッチバックテスト実行可能
- 品質・設計上の配慮
  - DB 書き込みは冪等（ON CONFLICT / INSERT ... DO UPDATE / DO NOTHING）
  - 外部依存を抑えた（標準ライブラリ中心）実装箇所が多い
  - セキュリティ対策（ニュース収集のSSRF対策、XMLパースで defusedxml 使用）

セットアップ手順
---------------
前提
- Python 3.10 以上（型注釈で | 記法を使用しているため）
- DuckDB が利用可能（pip でインストール可能）

推奨手順（ローカル開発）
1. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. pip をアップデートして必要パッケージをインストール
   - pip install --upgrade pip
   - pip install duckdb defusedxml

   （プロジェクトに pyproject.toml / requirements.txt があればそれを使ってください）
   - pip install -e .

3. 環境変数または .env を準備
   - プロジェクトルート（.git または pyproject.toml のあるディレクトリ）に .env/.env.local を置くと自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
   - 主な環境変数（必須）
     - JQUANTS_REFRESH_TOKEN — J-Quants 用リフレッシュトークン
     - KABU_API_PASSWORD — kabu ステーション API パスワード（実行層で使用）
     - SLACK_BOT_TOKEN — Slack 通知用 Bot トークン
     - SLACK_CHANNEL_ID — Slack 通知先チャンネル ID
   - その他（任意 / デフォルトあり）
     - KABUSYS_ENV (development|paper_trading|live) — デフォルト development
     - LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL) — デフォルト INFO
     - KABU_API_BASE_URL — kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
     - DUCKDB_PATH — デフォルト data/kabusys.duckdb
     - SQLITE_PATH — デフォルト data/monitoring.db

4. DuckDB スキーマ初期化
   - Python REPL またはスクリプトで実行:
     from kabusys.data.schema import init_schema
     init_schema("data/kabusys.duckdb")
   - ":memory:" を指定するとインメモリ DB を初期化します（テスト用途）。

使い方（主要ユースケース）
------------------------

1) DB を初期化する
   - 例:
     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")

2) J-Quants API から株価を取得して保存する
   - 例:
     from kabusys.data.jquants_client import get_id_token, fetch_daily_quotes, save_daily_quotes
     token = get_id_token()  # settings.jquants_refresh_token を利用
     records = fetch_daily_quotes(id_token=token, date_from=date(2024,1,1), date_to=date(2024,1,31))
     saved = save_daily_quotes(conn, records)

3) ニュース収集ジョブを実行して保存する
   - 例:
     from kabusys.data.news_collector import run_news_collection
     # known_codes は銘柄抽出に使う有効コード集合（None なら抽出スキップ）
     res = run_news_collection(conn, known_codes={"7203","6758"})

4) 特徴量（features）を構築する
   - 例:
     from kabusys.strategy import build_features
     build_features(conn, target_date=date(2024,1,31))

   - 背景:
     - calc_momentum / calc_volatility / calc_value を呼び出し、ユニバースフィルタ → Zスコア正規化 → features テーブルへ日付単位で UPSERT（冪等）

5) シグナルを生成する
   - 例:
     from kabusys.strategy import generate_signals
     generate_signals(conn, target_date=date(2024,1,31), threshold=0.6)

   - 生成されたシグナルは signals テーブルに書き込まれます（日付単位で置換）。

6) バックテストを実行する（CLI）
   - DB が prices_daily / features / ai_scores / market_regime / market_calendar を含んでいる必要があります。
   - 実行例:
     python -m kabusys.backtest.run \
       --start 2023-01-01 --end 2024-12-31 \
       --cash 10000000 --db data/kabusys.duckdb
   - 結果としてコンソールに CAGR, Sharpe, Max Drawdown, Win Rate, Payoff Ratio, Total Trades が表示されます。
   - run_backtest() は内部で本番 DB からインメモリ DB を構築して日次シミュレーションを行います（signals/positions の汚染を防ぐ）。

7) バックテストを Python API で呼ぶ
   - 例:
     from kabusys.backtest.engine import run_backtest
     result = run_backtest(conn, start_date=date(2023,1,1), end_date=date(2023,12,31))
     metrics = result.metrics

注意点 / 設計上のポリシー
-----------------------
- 自動的に .env / .env.local を読み込みますが、テストや明示的に無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DB 書き込み関数は冪等を意識して実装されています（ON CONFLICT など）。
- ニュース収集では SSRF 回避や XML 攻撃対策（defusedxml）を行っています。
- J-Quants クライアントは 120 req/min のレートリミットに合わせた RateLimiter、リトライ、トークン自動リフレッシュを実装しています。
- generate_signals / build_features / research モジュールはルックアヘッドバイアス回避のため target_date 時点で利用可能なデータのみを参照する設計です。

ディレクトリ構成（主なファイル）
------------------------------
（パッケージルート: src/kabusys 以下）

- __init__.py
- config.py
  - 環境変数読み込み・settings オブジェクト
- data/
  - __init__.py
  - jquants_client.py — J-Quants API クライアント（fetch/save utilities）
  - news_collector.py — RSS 取得・前処理・保存
  - schema.py — DuckDB スキーマ定義と init_schema
  - stats.py — zscore_normalize などの統計ユーティリティ
  - pipeline.py — ETL パイプラインヘルパ（差分更新等）
- research/
  - __init__.py
  - factor_research.py — momentum/volatility/value 計算
  - feature_exploration.py — forward returns / IC / summary
- strategy/
  - __init__.py
  - feature_engineering.py — features 作成（Zスコア正規化・ユニバースフィルタ）
  - signal_generator.py — final_score 計算と BUY/SELL シグナル生成
- backtest/
  - __init__.py
  - engine.py — run_backtest のメインループ
  - simulator.py — PortfolioSimulator（擬似約定・MTM）
  - metrics.py — バックテスト評価指標
  - run.py — CLI エントリポイント
  - clock.py —（将来機能用）模擬時計
- execution/ (空の __init__.py があるだけで実装は外部に依存する想定)
- monitoring/ (パッケージでエクスポートされているが本リポジトリの詳細は実装次第)

API・関数一覧（主な公開関数）
----------------------------
- kabusys.data.schema.init_schema(db_path)
- kabusys.data.jquants_client.get_id_token(refresh_token=None)
- kabusys.data.jquants_client.fetch_daily_quotes(...)
- kabusys.data.jquants_client.save_daily_quotes(conn, records)
- kabusys.data.news_collector.run_news_collection(conn, sources=None, known_codes=None)
- kabusys.research.calc_momentum / calc_volatility / calc_value / calc_forward_returns / calc_ic / factor_summary
- kabusys.strategy.build_features(conn, target_date)
- kabusys.strategy.generate_signals(conn, target_date, threshold=0.6, weights=None)
- kabusys.backtest.run_backtest(conn, start_date, end_date, ...)
- CLI: python -m kabusys.backtest.run --start YYYY-MM-DD --end YYYY-MM-DD --db path/to/db

ライセンス・貢献
----------------
（ここにライセンス情報・貢献方法を記載してください。例: MIT License など。リポジトリに LICENSE があればそれに従ってください。）

最後に
------
この README はコードベースの主要機能と利用手順をまとめた概要です。より詳細な設計仕様（StrategyModel.md, DataPlatform.md, BacktestFramework.md 等）がプロジェクト内にある想定ですので、導入・拡張時はそれらの設計文書も参照してください。質問や使い方の補足が必要であれば教えてください。