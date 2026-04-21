README
=====

概要
----
KabuSys は日本株の自動売買システム（プロトタイプ）です。  
アルゴリズム的な銘柄選定・ポートフォリオ構築、ポジションサイズ計算、リスク判定、注文実行（実売買/ペーパートレード切替）、監視（プロセス死活・データ鮮度・注文異常検出）および AI を用いたニュースセンチメント／レジーム判定機能を備えています。

主な設計方針：
- 生データ参照と分析は DuckDB を用いる（prices_daily / raw_financials 等）。
- 発注部分は BrokerClient 抽象を介して実装され、KABUSYS_ENV によって paper_trading（モック）／live（実際のブローカー）を切替可能。
- 監視は SQLite（monitoring DB）に永続化し、Kill Switch による安全停止をサポート。
- OpenAI（gpt-4o-mini）を用いたニュース NLP / レジーム判定を実装（API キー必須、フェイルセーフあり）。

機能一覧
--------
- 実行ベース
  - ExecutionEngine 起動スクリプト（python -m kabusys.run_execution）
  - Paper trading と live モードの切替（KABUSYS_ENV）
  - PID / stop フラグによる起動制御
- 監視
  - SystemMonitor（CPU/Mem/Disk、プロセス死活、データ鮮度）
  - TradeMonitor / RiskMonitor（約定異常・滞留注文・ドローダウン・ポジション上限監視）
  - KillSwitch（条件に応じて data/kill.flag を書込 → Execution 停止）
  - MonitoringEngine（各モニタのポーリング統合）
  - run_monitoring 起動スクリプト（ポーリングループ、MONITOR_POLL_INTERVAL で間隔変更可）
- ポートフォリオ構築
  - 銘柄候補選定（スコア順）
  - 重み算出（等重／スコア加重）
  - セクター上限の適用（apply_sector_cap）
  - レジーム乗数（calc_regime_multiplier）
  - ポジションサイズ計算（risk_based / equal / score）
- 研究用 / データ処理
  - ファクター計算（Momentum, Volatility, Value 等）
  - 将来リターン・IC 計算・統計サマリ
  - DuckDB を用いた SQL ベースの処理
- AI
  - ニュースセンチメント集計（news_nlp.score_news）
  - 市場レジーム判定（regime_detector.score_regime）
  - OpenAI API（gpt-4o-mini）との連携（API キーが必要）
- ユーティリティ
  - 環境設定ウィザード（python -m kabusys.config_setup）
  - 設定検証 CLI（python -m kabusys.validate_config）
  - ログ設定ユーティリティ（kabusys.utils.logging_setup）
  - プロセス優先度設定・CPU affinity（kabusys.utils.process_priority）
  - Paper Trading 検証レポート（python -m kabusys.tools.paper_verification_report）

セットアップ手順
---------------
1. リポジトリをクローン
   - git clone <repo-url>
   - プロジェクトルートは .git または pyproject.toml を基準に自動検出されます。

2. Python 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - 必要な主要モジュール（一例）:
     - duckdb
     - psutil
     - openai
     - pyyaml (設定ファイル検証用)
   - 例:
     - pip install duckdb psutil openai pyyaml

   （実際の requirements.txt があればそれを使用してください）

4. .env の作成
   - 対話式ウィザード:
     - python -m kabusys.config_setup
   - もしくは .env を手動作成（.env.example を参照してください）。
   - 必須環境変数:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - OpenAI 機能を使う場合:
     - OPENAI_API_KEY を設定

5. 設定検証（起動前チェック）
   - python -m kabusys.validate_config
   - 問題がある場合は出力に従って修正してください。
   - --strict オプションで警告も失敗扱いにできます。

6. ディレクトリ作成（任意）
   - data/（デフォルト DB・フラグファイル）
   - logs/（ログファイル: logs/<app_name>.log）
   - これらは起動時に自動作成される場合がありますが、手動で用意しておくと権限周りで安心です。

使い方
------
起動スクリプト
- 実行エンジン（発注処理）を起動
  - python -m kabusys.run_execution
  - 挙動:
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient が使われ、デフォルトで data/paper_trading.db に記録（本番 DB と分離）。
    - 起動時に ExecutionEngine は data/execution.pid（デフォルト）に PID を書きます。
    - data/stop_requested.flag が存在すると起動を行わない／走っている場合は停止します。

- 監視ループを起動
  - python -m kabusys.run_monitoring
  - 環境変数:
    - MONITOR_POLL_INTERVAL: ポーリング間隔（秒）。デフォルト 60。
  - 監視は常に本番用 sqlite_path を使用して monitoring DB を初期化します（env に依存しない）。

停止・制御
- Graceful stop（run_monitoring / run_execution の両方が監視する停止フラグ）:
  - プロジェクトルートの data/stop_requested.flag を作成するとループは検知して終了します。
- Kill Switch（リスクが閾値を超えた場合、監視側が Execution を停止するために書き込むフラグ）:
  - data/kill.flag が作成されると ExecutionEngine は停止対象になります（KillSwitch により生成）。
  - KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に kill.flag を自動クリアできます（本番では 0 推奨）。
- PID ファイル:
  - Execution はデフォルトで data/execution.pid を使用します。

Paper Trading 検証レポート
- python -m kabusys.tools.paper_verification_report --from YYYY-MM-DD --to YYYY-MM-DD
- デフォルト DB: data/paper_trading.db（環境変数 PAPER_TRADING_SQLITE_PATH で上書き可）
- 出力内容: 稼働率、注文成功率、送信率、レイテンシ指標、判定 PASS/FAIL

AI 機能
- news_nlp.score_news / regime_detector.score_regime を使用する場合は OPENAI_API_KEY が必要です。API 呼出しはリトライ・フェイルセーフ実装あり。
- モデル: gpt-4o-mini（設定で変更可能）

ログ
- ログ出力は kabusys.utils.logging_setup.setup_logging を経由して統一して行われます。
- デフォルト出力先:
  - コンソール (stdout)
  - ファイル: logs/<app_name>.log（日次ローテーション、30世代保存）
- 環境変数:
  - LOG_LEVEL（例: INFO, DEBUG）
  - LOG_DIR（ログ保存先ディレクトリ）

ディレクトリ構成
----------------
（プロジェクトの主要なファイル/モジュールを抜粋）

- src/
  - kabusys/
    - __init__.py
    - config.py             — 環境変数・Settings 管理（.env 自動ロード）
    - config_setup.py       — .env 作成ウィザード
    - validate_config.py    — 設定検証 CLI
    - run_execution.py      — ExecutionEngine 起動スクリプト
    - run_monitoring.py     — Monitoring ポーリング起動スクリプト
    - tools/
      - paper_verification_report.py
    - ai/
      - news_nlp.py
      - regime_detector.py
    - portfolio/
      - portfolio_builder.py
      - position_sizing.py
      - risk_adjustment.py
    - research/
      - factor_research.py
      - feature_exploration.py
    - monitoring/
      - monitoring_db.py
      - monitoring_engine.py
      - system_monitor.py
      - risk_monitor.py
      - trade_monitor.py    (参照実装あり)
      - kill_switch.py
      - alert_manager.py    (参照実装あり)
    - execution/
      - execution_engine.py
      - order_manager.py
      - order_repository.py
      - broker_factory.py
      - reconciler.py
      - risk_manager.py
    - utils/
      - logging_setup.py
      - process_priority.py
    - data/ (ランタイムで利用するディレクトリ、DB・フラグ等)
    - logs/ (ログ出力先)

補足・運用上の注意
-----------------
- 本リポジトリは自動売買システムの骨格（アルゴリズムや安全装置の設計方針）を示す実装であり、本番運用時はさらに厳密なテスト・監査・リスク管理が必要です。
- KABUSYS_ENV を "live" に設定する場合は、APIキーや通知設定（LINE）等が正しく設定されていることを validate_config で必ず確認してください。
- OpenAI の利用はコストとレイテンシが発生します。news_nlp と regime_detector はフェイルセーフ（API失敗時のデフォルト値）を備えていますが、実運用ではコスト管理・レート制御が重要です。
- データベースファイル（DuckDB / SQLite）は適切にバックアップ・管理してください。

バージョン
---------
- パッケージバージョン: kabusys.__version__ = "0.1.0"

ライセンス等
------------
- この README にはライセンス情報を含めていません。プロジェクトの LICENSE ファイルを参照してください。

以上。必要であれば、README に含めるコマンド例や環境変数のテンプレート（.env.example）を追記します。どのレベルの詳細を追加しますか？