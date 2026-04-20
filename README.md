KabuSys — README
=================

概要
----
KabuSys は日本株向けの自動売買 / 研究プラットフォームの一部を構成する Python パッケージです。
このコードベースには以下を含みます:

- 実行系（ExecutionEngine）起動スクリプト（実売買 / ペーパートレード対応）
- 監視系（Monitoring）ポーリングループと監視コンポーネント（システム・取引・リスク監視）
- ポートフォリオ構築（候補選定、重み計算、ポジションサイズ算出、セクター制限など）
- リサーチ（ファクター計算、将来リターン・IC 等の解析）
- AI 補助（ニュース NLP によるセンチメント、レジーム判定）
- 開発用ツール（.env ウィザード、設定検証、ペーパートレード検証レポート等）
- 共通ユーティリティ（ログ設定、プロセス優先度設定など）

各コンポーネントは可能な限り副作用を抑え、テストしやすい純粋関数や明確な DB 入出力層で実装されています。

主な機能一覧
--------------
- 実行エンジン起動（run_execution.py）
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使い paper_trading DB に隔離して記録
  - プロセス PID ファイル管理・停止フラグ検出
  - RiskManager / OrderManager / Reconciler 等の組み立てとスレッド実行

- 監視ループ（run_monitoring.py / MonitoringEngine）
  - SystemMonitor: CPU/メモリ/ディスク、Execution プロセスの生存、データ鮮度監視
  - TradeMonitor: 取引ログの整合性・滞留注文・約定異常検出 (実装ファイル参照)
  - RiskMonitor: ドローダウンやポジション上限チェック、risk_logs への記録
  - KillSwitch: 一定条件で data/kill.flag を書き込み ExecutionEngine を停止させる
  - AlertManager 経由で外部通知（LINE 等）を送るフックあり

- ポートフォリオ構築（kabusys.portfolio）
  - 候補選定（スコア/順位ベース）
  - 重み計算（等金額・スコア加重）
  - セクター集中制限の適用
  - ポジションサイズ算出（リスクベース／等分配／スコア分配、単元株丸め、aggregate cap）

- リサーチ（kabusys.research）
  - Momentum / Volatility / Value 等のファクター計算（DuckDB を利用）
  - 将来リターン計算、IC（スピアマン）や統計サマリー等

- AI（kabusys.ai）
  - ニュース NLP（OpenAI）で銘柄別センチメントを算出・ai_scores へ書き込み
  - レジーム判定（ETF MA とマクロニュースの混成スコア）

- 開発ユーティリティ
  - .env 対話ウィザード（kabusys.config_setup）
  - 設定検証 CLI（kabusys.validate_config）
  - Paper Trading 検証レポート生成（kabusys.tools.paper_verification_report）

セットアップ
------------
前提
- Python 3.10 以上（types | を利用）
- 仮想環境推奨（venv / virtualenv / conda 等）

依存パッケージ（主要）
- duckdb
- psutil
- openai
- PyYAML（config 検証で任意）
- そのほか標準ライブラリのみで動作するモジュールが多いです

インストール例（venv + pip）
1. 仮想環境作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   - pip install duckdb psutil openai pyyaml

（プロジェクトに requirements.txt があればそれを使ってください。）

初期設定
1. プロジェクトルートに移動（README と同じ階層に src/ がある構成を想定）。
2. .env を作成
   - 対話式で作る: python -m kabusys.config_setup
     - このウィザードは .env に API キーや DB パス等の初期設定を書き込みます。
   - もしくは .env.example を参照して手動作成
3. 設定検証（起動前に必ず実行推奨）
   - python -m kabusys.validate_config
   - 警告も厳密に扱う場合: python -m kabusys.validate_config --strict

初回実行に必要なディレクトリ
- data/ （デフォルト DB 等を保存）
- logs/ （ログ出力先。setup_logging が自動作成を試みますが権限等で失敗する場合があります）

環境変数（主なもの）
- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- OPENAI_API_KEY（AI 機能を使う場合必須）
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
  - paper_trading の場合、実行エンジンは PAPER_TRADING_SQLITE_PATH (デフォルト data/paper_trading.db) を使用
- DUCKDB_PATH（デフォルト data/kabusys.duckdb）
- SQLITE_PATH（監視 DB、デフォルト data/monitoring.db）
- LOG_LEVEL（デフォルト INFO）
- MONITOR_POLL_INTERVAL（監視ポーリング間隔 秒、デフォルト 60（run_monitoring 用））
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると .env 自動ロードを無効化

使い方（起動・コマンド）
------------------------

実行環境に応じた起動例

- 監視ループを起動
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（秒、1 以上）
  - 監視は常に settings.sqlite_path（デフォルト data/monitoring.db）を使用

- 実行エンジン（ExecutionEngine）を起動
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、paper_trading 専用 DB に記録
  - 起動時に data/stop_requested.flag が存在すると起動を中止します
  - 実行中は PID ファイル（data/execution.pid 等）を生成

- .env ウィザード（対話式設定）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると warning も失敗扱いで exit(1)

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - オプション: --from YYYY-MM-DD --to YYYY-MM-DD --db PATH
  - 環境変数 PAPER_TRADING_SQLITE_PATH で DB パスを指定可能

ログ・監視・停止
- ログ: logs/<app_name>.log（setup_logging により生成、日次ローテーション）
  - 例: logs/execution.log, logs/monitoring.log
- 停止（外部からの停止要求）
  - data/stop_requested.flag を作成すると run_execution/run_monitoring のループが検知して終了
  - KillSwitch（監視側）が条件を満たすと data/kill.flag を書き込んで ExecutionEngine を停止させる設計
  - ExecutionEngine 起動時に KILL_FLAG_CLEAR_ON_START=1 を設定していると起動時に kill.flag を自動クリアする（本番では 0 推奨）

データベース
- デフォルト
  - DuckDB: data/kabusys.duckdb
  - SQLite (monitoring): data/monitoring.db
  - SQLite (paper trading): data/paper_trading.db（paper_trading 時）
- monitoring_db.init_monitoring_db() が必要なテーブルを冪等に作成・マイグレーションを実行します

注意点 / 運用上のヒント
------------------------
- KABUSYS_ENV が live の場合は設定ミスが大きな影響を与えるため validate_config によるチェックを厳格に行ってください。
- OpenAI API を使う機能（ニュース NLP / レジーム判定）は API キーが必要で、レート制限や一時エラーへのリトライ処理を組み込んでいますが、運用時はコストとレート制限に注意してください。
- プロセス優先度は起動直後に set_process_priority("high") が呼ばれます。権限不足等で設定に失敗する場合はログに警告が出ます。
- DuckDB の executemany に空リストを渡すとエラーになることに注意して、ai 関連処理は空チェックを行ってから executemany を実行します。

ディレクトリ構成（抜粋）
-----------------------
以下はこの README 作成時点の主なファイル・パッケージ構成（src/kabusys 内）です。実際のリポジトリには他のファイルも存在する可能性があります。

- src/kabusys/
  - __init__.py
  - config.py                 # 環境変数ロード・Settings 定義
  - config_setup.py           # .env 対話式ウィザード
  - validate_config.py        # 設定検証 CLI
  - run_monitoring.py         # 監視ポーリングループ起動スクリプト
  - run_execution.py          # 実行エンジン起動スクリプト
  - monitoring/
    - monitoring_db.py        # monitoring 用 SQLite 抽象化層
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - monitoring_engine.py
    - kill_switch.py
    - alert_manager.py
  - execution/
    - execution_engine.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
    - broker_factory.py
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
  - tools/
    - paper_verification_report.py
  - utils/
    - logging_setup.py
    - process_priority.py

（補足）data/ や logs/ 等は実行時に作成されることが多いです。

Contributing / 開発メモ
---------------------
- コードは可能な限り純粋関数・副作用の限定を心がけています。ユニットテストを書きやすい設計です。
- .env 自動ロードはデフォルトで有効です（.env / .env.local）。テストや CI で無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB を使ったリサーチ関数群は外部 API に依存せず DB のテーブル（prices_daily 等）だけで動作する想定です。

ライセンス / 著作権
------------------
リポジトリ内の LICENSE を参照してください（この README では省略）。

以上。必要であれば、特定モジュール（例: ExecutionEngine の起動オプションや MonitoringEngine の alert 統合方法など）についてさらに詳細なドキュメントを作成します。どの部分を深掘りしますか？