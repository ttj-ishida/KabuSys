KabuSys
=======

日本株のデータ取得・特徴量生成・シグナル生成・バックテストを想定した自動売買基盤の参照実装です。
このリポジトリは主に以下のレイヤーで構成されています。

- Data: J‑Quants 等からの生データ取得・保存（DuckDB）／ニュース収集
- Research: ファクター計算・特徴量探索
- Strategy: 特徴量から戦略用 feature を作成しシグナルを生成
- Backtest: 日次シミュレータ・バックテストエンジン
- Execution / Monitoring: 実行層や監視用モジュール（骨組み）

この README はプロジェクトの概要、機能、セットアップ／使い方、ディレクトリ構成を説明します。

プロジェクト概要
----------------

KabuSys は日本株向けの自動売買プラットフォームを構成するためのライブラリ群です。主な目的は次のとおりです。

- J‑Quants API などから株価・財務・カレンダーを取得して DuckDB に保存する（ETL）
- 研究環境で計算した raw factor を正規化・合成して features を作成
- features と AI スコア等を統合して売買シグナルを生成
- シグナルに基づく日次バックテスト（擬似約定、スリッページ・手数料モデルを含む）
- RSS を収集してニュースを保存し、銘柄紐付けを行う

主要な設計方針として、ルックアヘッドバイアス回避、冪等性（DB 保存は ON CONFLICT）」、外部依存を最小限にしてテストしやすい構造を採用しています。

機能一覧
--------

主な機能（モジュール単位）

- kabusys.config
  - .env 自動ロード（プロジェクトルート検出）と環境設定管理
  - 必須環境変数の検査（例: JQUANTS_REFRESH_TOKEN 等）
- kabusys.data
  - jquants_client: J‑Quants API クライアント（レートリミット／リトライ／トークン自動更新）
  - news_collector: RSS 取得・前処理・raw_news への保存・銘柄抽出
  - schema: DuckDB のスキーマ定義と init_schema()
  - pipeline: ETL ワークフロー補助（差分取得・品質チェック）
  - stats: zscore_normalize（クロスセクション正規化）
- kabusys.research
  - factor_research: momentum / volatility / value 等のファクターを計算
  - feature_exploration: forward returns, IC（Spearman）や統計要約
- kabusys.strategy
  - feature_engineering.build_features：ファクターを正規化して features テーブルへ書き込み
  - signal_generator.generate_signals：features と ai_scores を統合し BUY/SELL シグナルを生成
- kabusys.backtest
  - engine.run_backtest: DB をコピーしたインメモリ環境で日次バックテストを実行
  - simulator.PortfolioSimulator: 擬似約定・ポートフォリオ管理（スリッページ、手数料考慮）
  - metrics: バックテスト評価指標の計算（CAGR / Sharpe / Max Drawdown など）
  - run: CLI からバックテストを実行するエントリポイント

セットアップ手順
---------------

前提
- Python 3.10 以上（型ヒントの | を使用）
- システムに pip がインストールされていること

1. リポジトリをクローン（例）
   - git clone <repo-url>
2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 依存パッケージをインストール
   - 必須パッケージ（例）:
     - duckdb
     - defusedxml
   - 例:
     - pip install duckdb defusedxml
   - （プロジェクトに requirements.txt があれば pip install -r requirements.txt）
4. パッケージを編集モードでインストール（任意）
   - pip install -e .
5. DuckDB スキーマ初期化
   - Python から:
     - python -c "from kabusys.data.schema import init_schema; init_schema('data/kabusys.duckdb')"
   - またはアプリ側で init_schema('path/to/db') を呼び出す

環境変数（.env）
----------------

config.Settings で参照される主な環境変数（README 用サンプル）:

必須（本番的に必要）
- JQUANTS_REFRESH_TOKEN: J‑Quants のリフレッシュトークン
- KABU_API_PASSWORD: kabuステーション API のパスワード
- SLACK_BOT_TOKEN: Slack 通知に使う Bot Token
- SLACK_CHANNEL_ID: Slack 投稿先チャンネル ID

任意 / デフォルトあり
- KABUSYS_ENV: development | paper_trading | live （デフォルト: development）
- LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL（デフォルト: INFO）
- DUCKDB_PATH: DuckDB のパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB のパス（デフォルト data/monitoring.db）
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 1 を設定すると .env 自動ロードを無効化

.env の自動読み込みについて
- プロジェクトルート（.git または pyproject.toml を含むディレクトリ）を自動検出して .env → .env.local の順で読み込みます（OS 環境変数を保護）。
- テスト時などで自動ロードを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

使い方（主要操作例）
-------------------

1) DuckDB スキーマ初期化
- Python REPL:
  - from kabusys.data.schema import init_schema
  - conn = init_schema("data/kabusys.duckdb")
  - conn.close()

2) J‑Quants からデータ取得・保存（概念）
- jquants_client.fetch_daily_quotes / fetch_financial_statements を呼び、
  jquants_client.save_daily_quotes / save_financial_statements で DuckDB に保存します。
- 例（簡易）:
  - from kabusys.data import jquants_client as jq
    from kabusys.data.schema import init_schema
    conn = init_schema("data/kabusys.duckdb")
    records = jq.fetch_daily_quotes(date_from=..., date_to=...)
    jq.save_daily_quotes(conn, records)
    conn.close()

3) ニュース収集
- from kabusys.data.news_collector import run_news_collection
- run_news_collection(conn, sources=None, known_codes=set_of_codes)

4) 特徴量作成（features テーブルへ書き込み）
- from kabusys.strategy import build_features
- build_features(conn, target_date)  # conn は DuckDB 接続、target_date は datetime.date

5) シグナル生成（signals テーブルへ書き込み）
- from kabusys.strategy import generate_signals
- generate_signals(conn, target_date, threshold=0.60, weights=None)

6) バックテスト（CLI）
- 用意した DuckDB（prices_daily, features, ai_scores, market_regime, market_calendar が存在すること）
- コマンド例:
  - python -m kabusys.backtest.run --start 2023-01-01 --end 2023-12-31 --db data/kabusys.duckdb
  - オプション:
    - --cash 初期資金
    - --slippage スリッページ率（デフォルト 0.001）
    - --commission 手数料率（デフォルト 0.00055）
    - --max-position-pct 1 銘柄あたり最大比率（デフォルト 0.20）

7) Python API を用いたバックテスト実行（ライブラリ呼び出し）
- from kabusys.data.schema import init_schema
  from kabusys.backtest.engine import run_backtest
  conn = init_schema("data/kabusys.duckdb")
  res = run_backtest(conn, start_date, end_date, initial_cash=10_000_000)
  # res.history / res.trades / res.metrics を参照

注意点 / 設計上のポイント
------------------------

- ルックアヘッドバイアス回避: 各処理は target_date 時点で利用可能な情報のみ使用する設計になっています。
- 冪等性: DB への保存は ON CONFLICT や DELETE+INSERT の日付単位置換で冪等性を担保しています。
- ETL の差分取得は市場カレンダーや最終取得日を参照して最小限の範囲で取得する設計です。
- news_collector は SSRF 対策・レスポンスサイズ制限・XML の安全パーシング（defusedxml）等の保護を実装しています。
- jquants_client はレートリミット（120 req/min）とリトライ、401 時のトークン自動再発行を実装しています。

ディレクトリ構成
----------------

主要ファイル・ディレクトリ（src/kabusys 配下を抜粋）

- kabusys/
  - __init__.py
  - config.py                           # 環境変数・設定管理
  - data/
    - __init__.py
    - jquants_client.py                 # J‑Quants API クライアント
    - news_collector.py                 # RSS ニュース収集
    - pipeline.py                       # ETL パイプライン（差分取得等）
    - schema.py                         # DuckDB スキーマ定義・初期化
    - stats.py                          # zscore_normalize 等
  - research/
    - __init__.py
    - factor_research.py                # momentum / volatility / value 計算
    - feature_exploration.py            # forward returns / IC / summary
  - strategy/
    - __init__.py
    - feature_engineering.py            # features 作成（正規化・ユニバースフィルタ）
    - signal_generator.py               # final_score 計算・BUY/SELL 生成
  - backtest/
    - __init__.py
    - engine.py                         # run_backtest（エントリ）
    - simulator.py                      # PortfolioSimulator（擬似約定）
    - metrics.py                        # バックテストメトリクス
    - run.py                            # CLI エントリポイント
    - clock.py                          # SimulatedClock（将来用途）
  - execution/                           # 発注・実行層（骨組み）
    - __init__.py
  - monitoring/                          # 監視・メトリクス（骨組み）
    - __init__.py

ドキュメント参照
---------------

コード内ドキュメントに StrategyModel.md, DataPlatform.md, BacktestFramework.md 等の参照が記載されています。これらの設計仕様（もしリポジトリに含まれる場合）は挙動・パラメータ調整の参考になります。

貢献・拡張案
------------

- 実運用向け: 実際の発注 API（kabuステーション）との接続実装、堅牢な監視・アラート機能、テストカバレッジ強化
- スケジューリング: ETL・feature・signal・execution を定期実行するワークフロー（Airflow 等）
- マルチタイムフレームのバックテスト（分足シミュレーション）
- AI スコアの導入（ai_scores テーブルを活用）

参考コマンドまとめ
-----------------

- DB 初期化:
  - python -c "from kabusys.data.schema import init_schema; init_schema('data/kabusys.duckdb')"
- バックテスト CLI:
  - python -m kabusys.backtest.run --start 2023-01-01 --end 2023-12-31 --db data/kabusys.duckdb
- Python から機能呼び出し（例）:
  - from kabusys.data.schema import init_schema
    conn = init_schema('data/kabusys.duckdb')
    from kabusys.strategy import build_features, generate_signals
    build_features(conn, target_date)
    generate_signals(conn, target_date)
    conn.close()

最後に
------

本 README はコードベースから抽出した情報に基づく簡易ドキュメントです。実装の詳細や設定値は各モジュールの docstring / ソースを参照してください。必要であれば README に含める追加説明（例: .env.example の具体的なテンプレート、requirements.txt の中身、CI/CD の設定など）を追記します。