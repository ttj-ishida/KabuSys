KabuSys — 日本株自動売買システム
=================================

概要
----
KabuSys は日本株の自動売買およびそれを補助する監視・リサーチ・AI ツール群を含む Python パッケージです。
主な役割は以下の通りです。

- ExecutionEngine：発注・注文管理・リスク管理を担う実行コンポーネント
- Monitoring：システム稼働監視、取引監視、リスク監視、Kill Switch（停止フラグ）等
- Research：DuckDB を用いたファクター計算・特徴量解析
- Portfolio：銘柄選定、重み付け、ポジションサイズ計算
- AI：ニュースの NLP スコアリング、レジーム判定（OpenAI を利用）
- Tools：ペーパートレード検証レポート等のユーティリティ

主要な設計方針
- 本番とペーパートレードは DB を分離（KABUSYS_ENV=paper_trading のときは paper_trading.db を使用）
- .env ベースの設定管理（自動読込機能あり）
- DuckDB を分析用 DB、SQLite を監視／取引ログに利用
- LLM 呼び出しはフェイルセーフ（API 失敗時はスキップまたはデフォルト値で継続）
- ロギングは統一された setup_logging で stdout と日次ローテーションファイルに出力

機能一覧
--------
- 実行（Execution）
  - Broker クライアント抽象化（paper_trading 時は MockBroker を使用）
  - OrderManager / OrderRepository / RiskManager / Reconciler / ExecutionEngine
  - 起動時の PID 管理・停止フラグ検知

- 監視（Monitoring）
  - SystemMonitor：CPU/MEM/DISK、プロセス生存、データ鮮度の監視
  - TradeMonitor：取引ログや注文の滞留・異常を検出
  - RiskMonitor：ドローダウン監視・ポジション上限監視、ダッシュボード更新
  - KillSwitch：条件に応じて data/kill.flag を書き込み ExecutionEngine を停止
  - MonitoringEngine：上記を束ねてポーリング（run / run_once）

- 研究（Research）
  - ファクター計算（momentum / volatility / value）
  - 将来リターン計算・IC（Information Coefficient）・統計サマリー

- ポートフォリオ（Portfolio）
  - 候補選定（スコア降順）
  - 等配分・スコア加重配分
  - セクター制限・レジーム乗数の適用
  - ポジションサイズ計算（ロット丸め、利用可能現金によるスケールダウン等）

- AI（OpenAI）
  - news_nlp.score_news: ニュース集約 → LLM で銘柄毎センチメント算出 → ai_scores に格納
  - regime_detector.score_regime: ETF MA とマクロニュースを LLM で評価して市場レジーム判定

- ツール
  - paper_verification_report: ペーパートレード DB の検証レポート出力

セットアップ手順
----------------

前提
- Python 3.10 以上（型ヒントに | 記法を使用）
- git, pip 等の基本ツール

1. リポジトリをクローン / ソースを配置
   - プロジェクトルートに src/ と同階層に data/ や logs/ を作成します（スクリプトが自動作成する場合あり）。

2. 仮想環境作成・依存パッケージインストール
   - 例:
     - python -m venv .venv
     - source .venv/bin/activate
     - pip install --upgrade pip
     - 必要なパッケージ（代表例）:
       - duckdb
       - psutil
       - openai
       - PyYAML (設定検証で任意)
     - 具体的な requirements.txt は本リポジトリに含まれていないため、上記を環境に応じてインストールしてください。

3. .env の作成
   - 対話式ウィザード:
     - python -m kabusys.config_setup
   - 手動で作成する場合は .env に主要変数を設定:
     - JQUANTS_REFRESH_TOKEN (必須)
     - KABU_API_PASSWORD (必須)
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
     - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
     - SQLITE_PATH (デフォルト: data/monitoring.db)
     - PAPER_TRADING_SQLITE_PATH (ペーパートレード専用 DB、デフォルト: data/paper_trading.db)
     - LOG_LEVEL (デフォルト: INFO)
     - OPENAI_API_KEY (AI 機能を使う場合)
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（任意、アラート用）
     - その他: PAPER_FILL_MODE, KILL_FLAG_CLEAR_ON_START など

4. 設定検証
   - python -m kabusys.validate_config
   - 警告も含めて厳密にチェックする場合:
     - python -m kabusys.validate_config --strict

5. ディレクトリ/ファイルの確認
   - data/（監視 DB や pid/flag ファイルを置く）
   - logs/（ログファイル: logs/<app_name>.log が生成される）
   - DuckDB / SQLite DB ファイルのパスは .env で変更可能

使い方（主要スクリプト）
-----------------------

- 実行エンジン (ExecutionEngine) 起動
  - python -m kabusys.run_execution
  - 動作:
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用 SQLite（PAPER_TRADING_SQLITE_PATH）を使用し、MockBrokerClient を使って完全に分離された動作を行います。
    - data/execution.pid に PID を書きます。
    - data/stop_requested.flag が存在すると起動を早期終了します。
    - プロセス優先度を high に設定しようとします（psutil に依存）。

- 監視ループ起動
  - python -m kabusys.run_monitoring
  - 動作:
    - Monitoring のポーリングループを起動します（デフォルト間隔 60 秒）。
    - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で上書き可（例: export MONITOR_POLL_INTERVAL=30）。
    - 監視は常に本番用の sqlite_path（Settings.sqlite_path）を使用します（環境に依らず）。
    - stop_requested.flag を検知するとループ停止します。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - オプション:
    - --db PATH （PAPER_TRADING_SQLITE_PATH 環境変数またはデフォルトを上書き）

- 設定ウィザード / 検証
  - python -m kabusys.config_setup
  - python -m kabusys.validate_config [--strict]

ランタイムに関する補足
- ログ:
  - ログ設定は kabusys.utils.logging_setup.setup_logging を使用します。
  - デフォルトのログディレクトリは logs/、ログ名は app_name（例: execution.log / monitoring.log）。
- 停止制御:
  - data/stop_requested.flag：run_* スクリプトが監視している停止フラグ（手動で作成すると次ポーリングで停止）。
  - data/kill.flag：KillSwitch が書き込むフラグ（ExecutionEngine を停止するためのシグナル）。
  - KILL_FLAG_CLEAR_ON_START=1 にすると起動時に kill.flag を自動クリアする（本番では 0 推奨）。
- 権限:
  - プロセス優先度の変更や CPU affinity 設定は権限や OS に依存し、設定に失敗しても警告を出して継続します。

ディレクトリ構成（概要）
---------------------
プロジェクトルート（抜粋）
- src/
  - kabusys/
    - __init__.py
    - config.py               — 環境変数読み込み / Settings クラス
    - config_setup.py         — .env 対話ウィザード
    - validate_config.py      — 起動前設定検証 CLI
    - run_execution.py        — ExecutionEngine 起動スクリプト
    - run_monitoring.py       — Monitoring 起動スクリプト
    - execution/              — 発注関連（BrokerFactory, Engine, OrderManager 等）
    - monitoring/
      - monitoring_db.py      — SQLite 永続化層
      - system_monitor.py
      - trade_monitor.py
      - risk_monitor.py
      - kill_switch.py
      - monitoring_engine.py
      - alert_manager.py
    - portfolio/
      - portfolio_builder.py
      - position_sizing.py
      - risk_adjustment.py
    - research/
      - factor_research.py
      - feature_exploration.py
    - ai/
      - news_nlp.py           — OpenAI を用いたニュースセンチメント
      - regime_detector.py    — 市場レジーム判定
    - tools/
      - paper_verification_report.py
    - utils/
      - logging_setup.py
      - process_priority.py
- config/
  - *.yaml （system_config.yaml 等。validate_config で存在とパースをチェック）
- data/                      — デフォルト DB・PID・フラグの保存先（例: data/monitoring.db）
- logs/                      — ログファイル（logs/<app_name>.log）

主要なファイル / 役割（抜粋）
- Settings（kabusys.config.Settings）
  - 環境変数のラップ。KABUSYS_ENV（development|paper_trading|live）や DB パス、閾値等を提供。
- monitoring/monitoring_db.py
  - system_status / trade_logs / positions / risk_logs / dashboard のスキーマ定義と操作ラッパー
- ai/news_nlp.py / ai/regime_detector.py
  - OpenAI を呼ぶロジックを含む。API キーは OPENAI_API_KEY で指定可能。呼び出し部分はテストで差し替え可能に設計。
- portfolio/*, research/*
  - DuckDB を用いた計算や純粋関数群。DB 参照は主に research と ai、monitoring のみが行う。

よくある質問（FAQ）
------------------
Q: ペーパートレードと本番の DB はどう分かれますか？
A: KABUSYS_ENV=paper_trading の場合、Execution 側は Settings.paper_sqlite_path（デフォルト data/paper_trading.db）を使用します。Monitoring は常に Settings.sqlite_path（data/monitoring.db）を使用して監視します。

Q: MONITOR_POLL_INTERVAL の単位は？
A: 秒です。run_monitoring は環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書きできます。デフォルトは 60 秒。1 未満・不正値は 60 秒にフォールバックします。

Q: LLM（OpenAI）キーがない場合はどうなる？
A: AI 関連関数は API キーが未設定だと ValueError を出すことがあります。score_regime / score_news を呼ぶ場合は OPENAI_API_KEY 環境変数または関数引数でキーを渡してください。API 呼び出しで一時エラーが起きてもリトライやフォールバックが行われる設計です。

開発者向けメモ
----------------
- テストや CI では KABUSYS_DISABLE_AUTO_ENV_LOAD を設定して .env 自動読み込みを無効化できます。
- OpenAI など外部 API 呼び出し箇所は _call_openai_api を patch / mock してユニットテスト可能です。
- DuckDB / SQLite のパスは環境変数で変更可能なため、テスト用に一時ファイルを指定すると良いです。

ライセンス / バージョン
----------------------
- パッケージバージョン: kabusys.__version__ = "0.1.0"
- ライセンス情報はリポジトリに含まれる LICENSE 等を参照してください（このコードスニペットでは明示していません）。

最後に
------
この README はコードベースからの抽出に基づく概要です。実運用前に必ず python -m kabusys.config_setup と python -m kabusys.validate_config で設定を作成・検証し、テスト環境で動作確認を行ってください。必要であれば README に追記する項目（詳細な起動サービス定義や docker-compose 例など）を教えてください。