# KabuSys

日本株向け自動売買／研究プラットフォームのサブセット実装です。本リポジトリは主に以下を含みます: 実行エンジン起動スクリプト、監視（Monitoring）コンポーネント、Portfolio / PositionSizing 等の純粋関数群、AI ニュース NLP・レジーム判定、Research 用ファクター計算、ユーティリティ類。

以下の README はこのコードベースをローカルでセットアップし試すための手順、主要機能、使い方、ディレクトリ構成をまとめたものです。

注意: 本 README はコード内の docstring / コメントに基づいて作成しています。実行には外部パッケージ（duckdb, psutil, openai など）が必要です。

プロジェクト概要
- 名前: KabuSys
- 目的: 日本株の自動売買・研究基盤（発注エンジン、監視、リスク管理、ファクター計算、AI を用いたニューススコアリングなど）
- 主要設計方針:
  - 実行系（Execution）と監視系（Monitoring）を分離
  - Paper Trading と Live を明確に分離（専用 DB 等）
  - LLM（OpenAI）を用いたニュース解析・レジーム判定はフェイルセーフを優先
  - DuckDB を分析用途に、SQLite を軽量な永続化（監視・注文履歴）に使用

主な機能一覧
- Execution 起動スクリプト（run_execution.py）
  - KABUSYS_ENV=paper_trading の場合は MockBroker を使用し、paper_trading.db に記録（本番 DB と分離）
  - プロセス優先度の設定、PID/停止フラグ連携、スレッドで ExecutionEngine を実行
- Monitoring 起動スクリプト（run_monitoring.py）
  - SystemMonitor / TradeMonitor / RiskMonitor を定期ポーリング
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更可能（デフォルト 60 秒）
  - 監視ログは SQLite に永続化（monitoring.db）
  - KillSwitch による停止フラグ（data/kill.flag）生成
- 監視 DB 層（monitoring_db.py）
  - system_status, trade_logs, positions, risk_logs, dashboard を作成・操作する API を提供
- RiskMonitor / KillSwitch / MonitoringEngine
  - ドローダウン検知、ポジション上限検知、アラート発行（AlertManager 経由）
- Portfolio（選定・配分・ポジション決定）
  - select_candidates, calc_equal_weights, calc_score_weights
  - calc_position_sizes（risk_based / equal / score）
  - セクターキャップ適用・レジーム乗数
- Research（ファクター・特徴量）
  - momentum / volatility / value の計算（DuckDB 接続を受け取って SQL で計算）
  - forward returns / IC / 統計サマリー
- AI（ニュース NLP, regime_detector）
  - OpenAI を使ったニュースのセンチメント集約と ai_scores 書き込み
  - マクロニュース + ETF MA を合成した日次の市場レジーム判定
- ユーティリティ
  - ロギングセットアップ（logs/<app>.log、日次ローテーション）
  - プロセス優先度・CPU affinity 設定
  - .env 対話ウィザード（config_setup.py）
  - 設定検証 CLI（validate_config.py）
- ツール
  - Paper Trading 検証レポート生成（tools/paper_verification_report.py）

セットアップ手順（ローカル）
1. リポジトリをクローンして作業ディレクトリへ
   - 仮にプロジェクトルートが得られるように .git または pyproject.toml があることを想定しています。

2. Python 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   - 実装内で言及される主要依存例:
     - duckdb
     - psutil
     - openai
     - PyYAML（設定検証で YAML の内容をチェックする場合）
   - 例:
     ```
     pip install duckdb psutil openai pyyaml
     ```
   - ※ requirements.txt は本リポジトリに含まれていない想定のため、実行に必要なパッケージを適宜インストールしてください。

4. 環境変数設定（.env）
   - 対話式ウィザードで .env を作成する:
     ```
     python -m kabusys.config_setup
     ```
   - あるいはプロジェクトルートに .env を手動で作成。必須環境変数:
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
     - OPENAI_API_KEY（AI 機能を使う場合必須）
   - 設定例（.env、実際は秘密値を入れてください）:
     ```
     JQUANTS_REFRESH_TOKEN=your_token_here
     KABU_API_PASSWORD=your_password_here
     KABU_API_BASE_URL=http://localhost:18080/kabusapi
     DUCKDB_PATH=data/kabusys.duckdb
     SQLITE_PATH=data/monitoring.db
     KABUSYS_ENV=development
     LOG_LEVEL=INFO
     KILL_FLAG_CLEAR_ON_START=0
     ```
   - Paper Trading 用 DB を分離する場合:
     - PAPER_TRADING_SQLITE_PATH（例: data/paper_trading.db）
     - PAPER_FILL_MODE（instant | partial | never | reject）デフォルト: instant

5. 設定検証
   - 自動検証ツールで設定をチェック:
     ```
     python -m kabusys.validate_config
     ```
   - 警告も FAIL 扱いにしたい場合:
     ```
     python -m kabusys.validate_config --strict
     ```

初回起動前の注意点
- .env に secrets（トークン・パスワード）を含めますが、.env は Git にコミットしないでください（config_setup でも警告があります）。
- data/ ディレクトリや logs/ は自動作成されますが、権限やマウント先に注意してください。

使い方（主要コマンド）
- ExecutionEngine を起動する（ローカルで直接実行する場合）
  ```
  python -m kabusys.run_execution
  ```
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し PAPER_TRADING_SQLITE_PATH に記録します（本番 sqlite_path と分離）。
  - 起動前に data/stop_requested.flag が存在する場合、起動をスキップします。
  - 停止は監視側から kill.flag を書き込ませるか、data/stop_requested.flag を作成することで実行スレッドに停止シグナルを送れます。
  - PID ファイル: data/execution.pid（Settings.pid_file_path でオーバーライド可能）

- Monitoring を起動する
  ```
  python -m kabusys.run_monitoring
  ```
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒で指定（例: MONITOR_POLL_INTERVAL=30）。
  - 監視は Settings に指定された sqlite_path（monitoring DB）を使用します。本番/テスト環境にかかわらず同じ sqlite_path を使用する設計です（監視は本番 DB を参照するため）。
  - 監視ループは data/stop_requested.flag が存在すると終了します。

- Paper Trading 検証レポート生成
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  - デフォルト DB: data/paper_trading.db。--db で別ファイルを指定可能。

- .env 作成ウィザード
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  ```

運用上のポイント
- ログ:
  - デフォルト出力先: logs/<app_name>.log（app_name は monitoring / execution など）
  - ログは日次ローテーションで _BACKUP_COUNT（デフォルト 30 日分）保持
  - LOG_DIR 環境変数で保存先を切り替え可能
- 停止フラグ:
  - data/kill.flag: KillSwitch が書き込む停止理由を含むフラグ（ExecutionEngine に停止指示）
  - data/stop_requested.flag: run_* スクリプトの外部停止フラグ（run_monitoring / run_execution が監視）
  - Settings.KILL_FLAG_CLEAR_ON_START が 1 に設定されていると起動時に kill.flag を自動的に削除する（本番では推奨されない）
- Paper Trading:
  - PAPER_FILL_MODE（instant / partial / never / reject）で mock broker の振る舞いを設定
  - PAPER_TRADING_SQLITE_PATH で paper_trading 用 DB を指定（本番 DB と完全分離）
- OpenAI:
  - OPENAI_API_KEY が必要（ai.news_nlp / ai.regime_detector を使う場合）
  - API 呼び出しはリトライ・タイムアウト・パース失敗等を考慮して実装されていますが、料金やレート制限に注意してください

ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / Settings
  - config_setup.py          — .env 対話ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — Monitoring 起動スクリプト
  - monitoring/
    - monitoring_db.py       — SQLite 永続化層（schema/migrations）
    - monitoring_engine.py   — 各 Monitor を束ねるエンジン
    - system_monitor.py      — システム状態 / データ鮮度監視
    - trade_monitor.py       — 発注ログ監視（滞留注文等）  ※（実装ファイルはリポジトリ内に存在）
    - risk_monitor.py        — ドローダウン・ポジション上限監視
    - kill_switch.py         — kill.flag 書き込みユーティリティ
    - alert_manager.py       — アラート送信管理（LINE 等を想定） ※（実装ファイルはリポジトリ内に存在）
  - execution/
    - execution_engine.py    — 実行エンジン（EngineConfig 等）
    - order_manager.py
    - order_repository.py
    - broker_factory.py
    - reconciler.py
    - risk_manager.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py
  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py
  - ai/
    - news_nlp.py            — ニュース NLP スコアリング（OpenAI）
    - regime_detector.py     — レジーム判定（ETF + マクロ NLP）
    - __init__.py
  - tools/
    - paper_verification_report.py
  - utils/
    - logging_setup.py       — 統一的ログ設定
    - process_priority.py    — プロセス優先度 / CPU affinity

（上記はリポジトリの一部を抜粋したものです。詳細な実装は src/kabusys 以下の各モジュールの docstring を参照してください。）

よくある質問（FAQ）
- Q: 監視はどの DB を参照しますか？
  - A: Monitoring は Settings.sqlite_path に指定された SQLite（デフォルト data/monitoring.db）を使用します。run_monitoring は環境にかかわらず本番 sqlite_path を使用する設計です。

- Q: Paper Trading と本番 DB は分離されていますか？
  - A: はい。KABUSYS_ENV=paper_trading の場合、Execution は settings.paper_sqlite_path（デフォルト data/paper_trading.db）を使います。本番 sqlite_path に影響しないよう分離設計です。

- Q: MONITOR_POLL_INTERVAL の単位は？
  - A: 秒（デフォルト 60）。環境変数に 0 以下や不正な値が設定された場合はデフォルトにフォールバックします。

- Q: KillSwitch はどのように動作しますか？
  - A: RiskMonitor 等が条件を満たすと KillSwitch が Settings.kill_flag_path（デフォルト data/kill.flag）へ理由を書き込みます。ExecutionEngine はこのファイルの存在を検知すると安全に停止する設計になっています。

貢献
- ドキュメントやテスト、依存関係の整理、package 配布用設定の整備など歓迎します。

最後に
- 本 README はコード内の注釈に基づく概要ドキュメントです。個々の機能を深く理解するには、対応するモジュールの docstring を参照してください（例: ai/news_nlp.py, research/factor_research.py, monitoring/monitoring_db.py など）。

必要であれば、README に「インストール手順 (pip packaging)」「docker-compose 例」「詳細な API ドキュメント（関数一覧とパラメータ）」「運用 runbook（停止・ログローテーション・バックアップ）」などを追加できます。どの追加情報が必要か教えてください。