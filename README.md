README — KabuSys
=================

概要
----
KabuSys は日本株向けの自動売買／リサーチ基盤です。主な目的は以下です。

- 日次のファクター計算・リサーチ（DuckDB を用いた時系列処理）
- ポートフォリオ構築（候補選定、重み付け、株数決定）
- 発注実行（ExecutionEngine）とリスク管理
- 監視（System / Trade / Risk のポーリング、アラート、Kill Switch）
- Paper Trading（本番 DB と完全分離）および検証レポート生成
- ニュース NLP / レジーム判定（OpenAI を利用したセンチメント評価）

このリポジトリは純粋関数群（portfolio, research 等）と実行・監視用のエントリポイント群を含みます。

主な機能
-------
- 設定管理
  - .env ウィザード（python -m kabusys.config_setup）
  - 設定検証 CLI（python -m kabusys.validate_config）
  - Settings クラスで環境変数を安全に取得・検証
- 実行（Execution）
  - ExecutionEngine（run_execution.py）: 本番/ペーパートレード対応
  - BrokerClientFactory 経由で実際のブローカー or MockBroker を切替
  - リスク管理（RiskManager）、OrderManager、Reconciler などの構成
- 監視（Monitoring）
  - SystemMonitor / TradeMonitor / RiskMonitor（監視 DB へ永続化）
  - MonitoringEngine（複数モニタの束ね）
  - Kill Switch（条件に応じて data/kill.flag を書き込み、Engine を停止）
  - run_monitoring.py で常駐ポーリング（MONITOR_POLL_INTERVAL で調整可）
- リサーチ / ファクター計算
  - calc_momentum / calc_volatility / calc_value（DuckDB を用いた純関数）
  - forward returns / IC（feature_exploration）等の研究ユーティリティ
- ポートフォリオ構築
  - 候補選定、等金額・スコア加重配分、リスク調整（セクター上限等）、ポジションサイズ計算
- AI 関連
  - news_nlp.score_news: OpenAI を使ったニュースセンチメントの株別評価（ai_scores に保存）
  - regime_detector.score_regime: ETF（1321）MA とマクロニュースで市場レジーム判定
- ツール
  - paper_verification_report: ペーパートレード DB から性能レポートを生成

セットアップ（開発環境）
---------------------
前提:
- Python 3.9+（プロジェクトの Python 要件に合わせてください）
- git, SQLite（組み込み）, DuckDB

1. リポジトリをクローン
   git clone <repo-url>
   cd <repo-root>

2. 仮想環境作成（推奨）
   python -m venv .venv
   source .venv/bin/activate  # POSIX
   .venv\Scripts\activate     # Windows

3. 必要パッケージをインストール
   以下の主要依存がコード内で使用されます。requirements.txt があればそちらを利用してください。
   pip install duckdb psutil openai

   補助（オプション）
   - PyYAML（config/*.yaml の検証に使用）: pip install PyYAML

4. .env 作成（対話ウィザード推奨）
   python -m kabusys.config_setup
   -> 各種キー（J-Quants / Kabu API / OPENAI_API_KEY 等）や DB パスを設定します。

5. 設定検証
   python -m kabusys.validate_config
   --strict を付けると警告もエラー扱いになります。

重要な環境変数とデフォルト
-------------------------
（Settings クラスのプロパティより抜粋）

- KABUSYS_ENV: 実行環境（development | paper_trading | live）、デフォルト: development
- JQUANTS_REFRESH_TOKEN: 必須（J-Quants API）
- KABU_API_PASSWORD: 必須（kabuステーション API）
- OPENAI_API_KEY: OpenAI を利用する機能で必要
- DUCKDB_PATH: 分析 DB（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 DB（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: ペーパートレードの約定挙動（instant|partial|never|reject、デフォルト: instant）
- LOG_LEVEL: ログレベル（INFO 等）
- MONITOR_POLL_INTERVAL: run_monitoring.py のポーリング間隔（秒、デフォルト: 60）
- KILL_FLAG_PATH: Kill Switch の flag ファイルパス（デフォルト: data/kill.flag）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（"1" でクリア）

使い方（主要コマンド）
---------------------

- .env の作成
  python -m kabusys.config_setup

- 設定検証
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict

- 実行エンジン起動（本番 / paper_trading に応じて .env の KABUSYS_ENV を設定）
  python -m kabusys.run_execution

  挙動:
  - paper_trading の場合、MockBrokerClient を使い、PAPER_TRADING_SQLITE_PATH に記録します（本番 DB と分離）。
  - 停止はプロジェクトルート/data/stop_requested.flag を作成することで検出されます（または kill.flag による停止判定等）。

- 監視ループ起動
  python -m kabusys.run_monitoring

  オプション:
  - 環境変数 MONITOR_POLL_INTERVAL=30 などでポーリング間隔を秒単位で上書き可。

- Paper Trading 検証レポート
  python -m kabusys.tools.paper_verification_report
  期間指定:
    python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  DB 指定:
    python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

- AI 機能（ライブラリ利用）
  - ニューススコア付与:
    from kabusys.ai.news_nlp import score_news
    score_news(duckdb_conn, target_date, api_key="YOUR_OPENAI_KEY")
  - レジーム判定:
    from kabusys.ai.regime_detector import score_regime
    score_regime(duckdb_conn, target_date, api_key="YOUR_OPENAI_KEY")

- 開発・テスト向けユーティリティ
  - 設定自動読み込みを無効化:
    KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると .env 自動読み込みを抑止します（テストで便利）。

停止・Kill Switch
-----------------
- Execution 停止（手動）
  - プロジェクトルート/data/stop_requested.flag を作成すると run_execution / run_monitoring が検出して終了処理を行います（様々なスクリプトで参照）。
- Kill Switch（自動停止）
  - RiskMonitor が閾値超過（ドローダウンなど）を検出すると Kabusys は data/kill.flag に理由を書き込みます。Execution 起動時に KILL_FLAG_CLEAR_ON_START=1 を設定していると自動クリアされる点に注意（本番では 0 推奨）。
  - kill.flag の削除は手動で行うか、KillSwitch.clear() を呼び出してクリアできます。

ディレクトリ構成
----------------
（主要ファイルのみ抜粋）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / Settings
  - config_setup.py          — .env 対話ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py
  - ai/
    - news_nlp.py
    - regime_detector.py
  - monitoring/
    - monitoring_db.py
    - monitoring_engine.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py (実装あり)
  - execution/
    - (ExecutionEngine, BrokerFactory, OrderManager などの実装群)
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py
  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py
  - utils/
    - process_priority.py
  - data/                    — 実行時に使用するファイル置き場（DB, pid, flags 等）

デフォルトのデータパス（.env で上書き可）
- data/kabusys.duckdb (DUCKDB_PATH)
- data/monitoring.db (SQLITE_PATH)
- data/paper_trading.db (PAPER_TRADING_SQLITE_PATH)
- data/execution.pid
- data/stop_requested.flag
- data/kill.flag

実装上の注意・運用メモ
--------------------
- Paper Trading モードは実 DB と分離するよう設計されています（PAPER_TRADING_SQLITE_PATH を使用）。
- OpenAI API を使う機能は API キー（OPENAI_API_KEY）を .env に設定してください。API 呼び出しはリトライ・フォールバック（失敗時は安全側の既定値）を備えています。
- DuckDB を分析用に使用しており、research・ai モジュールは DuckDB 接続を受け取って処理します。DuckDB のスキーマ（prices_daily, raw_financials, raw_news, ai_scores, market_regime 等）に依存します。
- process 優先度や CPU affinity は utils/process_priority.py でプラットフォームを吸収して設定します。権限不足で設定できない場合は警告ログに留まります。
- monitoring_db.init_monitoring_db() は冪等にテーブルを作成し、既存スキーマのマイグレーション（カラム追加）処理も含みます。

貢献・開発
----------
- 新しい設定項目を追加したら config_setup.py と validate_config.py を更新してください。
- DuckDB スキーマ変更は AI / research モジュールに影響します。スキーマ変更時は対応テストを追加してください。
- ユニットテストや CI はこの README の補足に応じて別途整備してください。

ライセンス・バージョン
---------------------
パッケージバージョン:
  src/kabusys/__version__ = 0.1.0

（ライセンス情報はリポジトリルートに LICENSE ファイルを置いてください）

以上。運用や導入で不明点があれば、具体的な実行コマンド・環境（OS, Python バージョン等）を教えてください。追加で README に含めたい手順やサンプル .env を作成して補足します。