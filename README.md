KabuSys — 日本株自動売買システム
================================

概要
----
KabuSys は日本株の自動売買・研究パイプラインを想定した小規模なシステムです。本リポジトリには、実行エンジン（ExecutionEngine）、監視コンポーネント（Monitoring）、ポートフォリオ構築・資金配分ロジック、リサーチ用ファクター計算、AI を使ったニュース NLP／レジーム判定、及びユーティリティスクリプトが含まれます。

設計上のポイント
- 実行ロジックとモニタリングはファイルベース（SQLite / DuckDB）で永続化。
- Paper Trading（ペーパートレード）モードでは本番 DB と完全分離（デフォルト: data/paper_trading.db）。
- .env (環境変数) による設定管理。対話式ウィザードと起動前検証用スクリプトを提供。
- OpenAI を用いた NLP / レジーム判定モジュールを含む（API キー必須）。
- ロギングは統一されたユーティリティで日次ローテーションを行う。

主な機能
---------
- ExecutionEngine 起動スクリプト（run_execution.py）
  - 環境ごとに BrokerClient を切り替え（paper_trading では MockBrokerClient を使用）
  - 独立した SQLite（paper_trading 用）と DuckDB を利用
- Monitoring（run_monitoring.py / monitoring パッケージ）
  - SystemMonitor / TradeMonitor / RiskMonitor を組み合わせた監視ループ
  - Kill Switch（条件に応じて data/kill.flag を書き込み、ExecutionEngine を停止）
  - 監視ログ永続化（SQLite）
- ポートフォリオ構築（kabusys.portfolio）
  - 候補選定、等金額/スコア比率配分、リスク調整、ポジションサイズ計算
- 研究・リサーチ（kabusys.research）
  - ファクター（モメンタム、ボラティリティ、バリュー）計算、将来リターン、IC 計算
  - DuckDB を使った高速集計
- AI（kabusys.ai）
  - ニュースのセンチメント評価（OpenAI）
  - 市場レジーム判定（ETF MA とマクロニュースの組合せ）
- ツール
  - .env 初期作成ウィザード（config_setup.py）
  - 起動前設定検証（validate_config.py）
  - Paper Trading 検証レポート生成（tools/paper_verification_report.py）
- ユーティリティ
  - 統一ロギング設定（kabusys.utils.logging_setup）
  - プロセス優先度・CPU affinity 設定（kabusys.utils.process_priority）

セットアップ手順
----------------

前提
- Python 3.10 以上（型注釈に | を使用）
- pip が使用可能

依存パッケージ（主要）
- duckdb
- psutil
- openai (AI 機能を使用する場合)
- PyYAML（config/*.yaml の検証を行う場合）

インストール（例）
1. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. 必要パッケージをインストール
   - pip install duckdb psutil openai PyYAML

（注）実際の requirements.txt / setup.py は本コード断片に含まれていません。利用する機能に応じて上のパッケージを追加してください。

環境変数（.env）
- 対話式で .env を作成:
  - python -m kabusys.config_setup
- 主要な環境変数（例）
  - JQUANTS_REFRESH_TOKEN (必須)
  - KABU_API_PASSWORD (必須)
  - KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
  - OPENAI_API_KEY (AI 機能を使う場合)
  - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
  - SQLITE_PATH (デフォルト: data/monitoring.db) — Monitoring が使用する DB（monitoring は環境にかかわらずこの sqlite_path を使用）
  - PAPER_TRADING_SQLITE_PATH (ペーパートレード用 DB; デフォルト: data/paper_trading.db)
  - KABUSYS_ENV (development | paper_trading | live; デフォルト: development)
  - LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL)
  - KILL_FLAG_CLEAR_ON_START (0|1) — 本番で 1 は危険

起動前検証
- python -m kabusys.validate_config
  - --strict を付けると警告も FAIL（exit 1）扱いになる

使い方
------

1) ExecutionEngine を起動する
- 通常（環境に応じた挙動）
  - python -m kabusys.run_execution
- ペーパートレードモード:
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  - paper_trading の場合は MockBrokerClient を使用し、デフォルトで data/paper_trading.db を使用します
- 実行中の停止:
  - data/stop_requested.flag を作成すると実行エンジンは検知して停止します
  - また監視側の KillSwitch が条件を満たした場合 data/kill.flag を書き込み ExecutionEngine に停止指示を出します

2) Monitoring を起動する
- python -m kabusys.run_monitoring
- ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で秒指定（デフォルト 60）
  - 0 以下や不正値はデフォルト値にフォールバック
- 監視は KABUSYS_ENV に関わらず settings.sqlite_path（デフォルト data/monitoring.db）を使用してログを書きます
- 停止:
  - data/stop_requested.flag を作成すると監視ループも終了します

3) Paper Trading 検証レポート
- python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
- デフォルト DB: 環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db

4) AI 機能
- OpenAI API を使用するモジュール（kabusys.ai.news_nlp, kabusys.ai.regime_detector）では OPENAI_API_KEY を環境変数に設定するか、関数引数でキーを渡してください。
- API 呼び出しはリトライ・バックオフやレスポンス検証を実装していますが、課金／レート制限に注意してください。

ログ
----
- ログは kabusys.utils.logging_setup で統一的に設定されます。
- デフォルト出力先:
  - コンソール（stdout）
  - 日次ローテーションファイル: logs/<app_name>.log（30 日分保持）
- ログレベルは .env の LOG_LEVEL または引数で設定可能。LOG_DIR 環境変数でログディレクトリを上書きできます。

重要なファイル / フラグ
- data/stop_requested.flag — 双方向の停止監視に使用（run_execution / run_monitoring が参照）
- data/kill.flag — KillSwitch が書き込む Execution 停止フラグ（存在すると実行エンジン停止）
- data/execution.pid — 実行エンジン用 PID ファイル（ExecutionEngine 起動時に使用）

ディレクトリ構成
-----------------
以下は src/kabusys 配下の主なファイル・パッケージ構成の概要です。

- src/kabusys/
  - __init__.py
  - config.py                — .env 読み込み / Settings クラス
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 起動前設定検証
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — Monitoring 起動スクリプト
  - utils/
    - logging_setup.py       — ログ設定ユーティリティ
    - process_priority.py    — プロセス優先度 / CPU affinity
  - execution/               — 実行関連（Engine, OrderManager 等）（省略コード）
  - monitoring/
    - monitoring_engine.py
    - system_monitor.py
    - trade_monitor.py       — （該当コード断片では省略）
    - risk_monitor.py
    - kill_switch.py
    - monitoring_db.py
    - alert_manager.py       — （該当コード断片では省略）
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py
    - regime_detector.py
  - data/                    — （実行時に生成されることが想定されるパス。DB・フラグ等）
  - tools/
    - paper_verification_report.py

補足 / 運用上の注意
-------------------
- 本番運用（KABUSYS_ENV=live）では .env の内容や KILL_FLAG_CLEAR_ON_START の設定に特に注意してください。validate_config.py の警告は見落とさないでください。
- Monitoring は sqlite_path を使用するため、Monitoring が本番 sqlite を参照することに留意してください（run_monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用）。
- Paper Trading は本番 DB と明確に分離されるようデフォルトで別ファイルを使用します（PAPER_TRADING_SQLITE_PATH）。
- OpenAI を使う機能は API キーやリクエスト量に依存します。テスト時はモック (unittest.mock.patch) を利用してください（コード内にモック用の差替えが想定された箇所があります）。

トラブルシューティング
---------------------
- .env が正しく読み込まれない / 設定不足がある場合:
  - python -m kabusys.validate_config を実行して不足項目・警告を確認
  - python -m kabusys.config_setup で再生成・修正
- ログファイルが出力されない:
  - LOG_DIR のパーミッションを確認。logging_setup はディレクトリ作成失敗時にコンソール出力のみで継続します。
- OpenAI 呼び出しで 429 / タイムアウトが発生する:
  - レート制限に達している可能性があります。API キーとレート制限の確認、リトライ設定の調整を検討してください。

ライセンス / 貢献
-----------------
この README はコード断片に基づいて生成されています。実際のライセンスや貢献ルールはリポジトリルートの LICENSE / CONTRIBUTING を参照してください（本断片には含まれていません）。

以上。README の補足・修正や、特定の起動例（systemd / supervisor 用の unit ファイル、Dockerfile、CI 設定など）が必要であれば教えてください。