# KabuSys — 日本株自動売買システム（README）

概要
- KabuSys は日本株向けの自動売買システム用ライブラリ / 実行スクリプト群です。
- 主な目的はシグナル生成 → ポートフォリオ構築 → 発注実行 → 監視・リスク管理までのワークフローを提供することです。
- モジュールは実行エンジン (ExecutionEngine)、監視 (Monitoring)、リサーチ（ファクター計算、特徴量探索）、ポートフォリオ構築、AI（ニュース NLP / レジーム判定）、ペーパートレード用ツール等で構成されています。

主な機能一覧
- 実行/発注
  - ExecutionEngine（発注ロジック、リスク管理、オーダーマネージャ等）
  - BrokerClientFactory による本番 / ペーパートレード（MockBrokerClient）切替
  - ペーパートレード専用 DB による本番 DB との分離
- 監視
  - SystemMonitor: CPU/メモリ/ディスク／プロセス稼働／データ鮮度監視
  - TradeMonitor / RiskMonitor: 注文滞留・約定異常・ドローダウン・ポジション上限の監視
  - KillSwitch: 監視側からの停止フラグ（data/kill.flag）で ExecutionEngine を停止
  - MonitoringEngine / run_monitoring.py によるポーリングループ実行
- ポートフォリオ構築
  - 候補選定、重み計算（等金額・スコア加重）、セクター制約、レジーム乗数、ポジションサイズ計算（単元丸め・aggregate cap）
- リサーチ
  - ファクター計算（モメンタム、ボラティリティ、バリュー等）
  - 将来リターン、IC（Information Coefficient）計算、統計サマリ
- AI（OpenAI 統合）
  - ニュース NLP（raw_news を LLM でスコアリングし ai_scores に永続化）
  - レジーム判定（ETF ma200 乖離 + マクロニュース LLM）
  - 失敗時のフォールバック・リトライロジック等を実装
- ツール
  - config_setup.py: 対話式 .env 作成ウィザード
  - validate_config.py: 起動前設定検証 CLI
  - tools/paper_verification_report.py: ペーパートレードの検証レポート生成
- ユーティリティ
  - logging_setup: 一元的なロギング設定（コンソール + 日次ローテートファイル）
  - process_priority: プロセス優先度 / CPU affinity 設定ユーティリティ
- 永続化
  - monitoring_db: 監視用 SQLite スキーマとラッパー（system_status、trade_logs、positions、risk_logs、dashboard）

セットアップ手順（開発/ローカル実行向け）
1. リポジトリをクローン
   - git clone <repo-url>

2. Python 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - 必要なライブラリの例:
     - duckdb
     - psutil
     - openai
     - pyyaml（config 検証で任意）
   - 例:
     - pip install duckdb psutil openai pyyaml

   注: プロジェクトに requirements.txt がない場合は上記を手動でインストールしてください。

4. .env の初期作成（対話式ウィザード）
   - python -m kabusys.config_setup
   - もしくは手動でルートの .env を作成
   - 必須環境変数:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - その他よく使う環境変数（例）:
     - KABUSYS_ENV: development | paper_trading | live
     - OPENAI_API_KEY: OpenAI API キー（AI モジュール使用時）
     - DUCKDB_PATH: data/kabusys.duckdb（デフォルト）
     - SQLITE_PATH: data/monitoring.db（監視 DB, デフォルト）
     - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db（KABUSYS_ENV=paper_trading の場合）
     - LOG_LEVEL: INFO（デフォルト）
     - KILL_FLAG_CLEAR_ON_START: 0|1
     - PAPER_FILL_MODE: instant|partial|never|reject（ペーパートレードの約定挙動）

5. 設定の検証
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いになる（exit code 1）

デフォルトファイル/ディレクトリ
- data/: SQLite ファイル、pid/flag ファイルなどを配置（起動時に自動作成されることがある）
  - data/monitoring.db
  - data/paper_trading.db
  - data/kabusys.duckdb（DuckDB は別ファイル）
  - data/kill.flag（Kill Switch）
  - data/stop_requested.flag（run_* スクリプトの停止制御）
  - data/execution.pid（ExecutionEngine の PID）
- logs/: ログファイルが出力される（logs/execution.log, logs/monitoring.log 等）
- config/: YAML 設定ファイル（system_config.yaml 等） — generate スクリプトで作成可能

使い方（主要コマンド）
- 実行エンジン（発注）
  - 開始:
    - python -m kabusys.run_execution
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し PAPER_TRADING_SQLITE_PATH に履歴を保存します。
  - 停止:
    - monitoring 側、もしくは手動で data/stop_requested.flag を作成すると run_execution は検知して停止します。
    - Kill Switch（data/kill.flag）が書かれると ExecutionEngine は発注を停止します。

- 監視（Polling loop）
  - 起動:
    - python -m kabusys.run_monitoring
  - ポーリング間隔:
    - 環境変数 MONITOR_POLL_INTERVAL で秒数を上書き可能（デフォルト 60 秒）
  - 注意:
    - run_monitoring は KABUSYS_ENV にかかわらず Settings.sqlite_path（本番の sqlite_path）を使用して監視テーブルへ接続します。

- ペーパートレード検証レポート
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - デフォルト DB は 環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db

- AI モジュール（スクリプト内 / API として利用）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
    - DuckDB 接続を渡してニューススコアを ai_scores テーブルに書き込み
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
    - レジーム判定を market_regime テーブルに永続化
  - どちらも OPENAI_API_KEY を環境変数で設定するか、api_key 引数で渡してください。

- ライブラリ的利用
  - ポートフォリオ:
    - from kabusys.portfolio import select_candidates, calc_equal_weights, calc_score_weights, calc_position_sizes, apply_sector_cap, calc_regime_multiplier
  - リサーチ:
    - from kabusys.research import calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, factor_summary, rank
  - ユーティリティ:
    - from kabusys.utils.logging_setup import setup_logging
    - from kabusys.utils.process_priority import set_process_priority, set_cpu_affinity

重要な挙動・運用上の注意
- run_monitoring は Monitoring 用 DB（Settings.sqlite_path）を使用する点に注意。環境変数 KABUSYS_ENV に依存しません。
- run_execution は KABUSYS_ENV=paper_trading の場合、paper_sqlite_path（PAPER_TRADING_SQLITE_PATH）を使用します。本番 DB と分離されています。
- Kill Switch（data/kill.flag）は監視から ExecutionEngine に停止シグナルを送ります。デフォルトでは起動時にクリアされません。KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に自動でクリアします（本番では 0 を推奨）。
- .env は絶対に Git にコミットしないでください（API キーなどの機密情報が含まれるため）。
- OpenAI 統合機能を利用する場合は API キー（OPENAI_API_KEY）が必要です。API 呼び出しにはレート制限・リトライロジックがありますが、コストには注意してください。
- psutil によるプロセス優先度設定は OS の権限によって失敗する場合があります（警告ログで継続します）。

ディレクトリ構成（主要ファイル／概要）
- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数の読み込み/設定ラッパー（.env 自動ロード、Settings クラス）
  - config_setup.py
    - 対話式 .env 作成ウィザード
  - validate_config.py
    - 起動前設定検証 CLI
  - run_execution.py
    - ExecutionEngine 起動スクリプト（KABUSYS_ENV による paper/live 切替）
  - run_monitoring.py
    - SystemMonitor をポーリングする監視スクリプト
  - tools/
    - paper_verification_report.py
      - ペーパートレード検証レポート生成ツール
  - portfolio/
    - portfolio_builder.py
      - 候補選定、重み計算
    - risk_adjustment.py
      - セクターキャップ、レジーム乗数
    - position_sizing.py
      - 株数決定、aggregate cap、単元丸め
    - __init__.py
  - research/
    - factor_research.py
      - モメンタム、ボラティリティ、バリュー等のファクター計算（DuckDB 使用）
    - feature_exploration.py
      - 将来リターン、IC、統計サマリ
    - __init__.py
  - ai/
    - news_nlp.py
      - raw_news を LLM でスコアリングして ai_scores に書き込む
    - regime_detector.py
      - ETF MA + マクロニュース LLM を合成した市場レジーム判定
    - __init__.py
  - monitoring/
    - monitoring_db.py
      - SQLite スキーマ初期化 / 永続化 API（system_status, trade_logs, positions, risk_logs, dashboard）
    - system_monitor.py
      - CPU/メモリ/ディスク/プロセス/データ鮮度監視
    - trade_monitor.py
      - （注文周りの監視ロジック）
    - risk_monitor.py
      - ドローダウン・ポジション上限のチェック（Kill 生成や risk_logs 登録）
    - kill_switch.py
      - data/kill.flag の作成・削除インターフェース
    - monitoring_engine.py
      - 各 Monitor を束ねるポーリングエンジン
  - execution/
    - （ExecutionEngine, OrderManager, OrderRepository, Reconciler, RiskManager 等 — 発注処理の中核）
  - utils/
    - logging_setup.py
      - 統一的なロギング設定（コンソール + 日次ローテーション）
    - process_priority.py
      - プロセス優先度・CPU affinity 設定ユーティリティ
    - __init__.py
  - monitoring/（上記と同フォルダ）
  - research/, portfolio/, ai/（上記）

開発・テストのヒント
- モジュールは多くが純粋関数か DI（接続やクライアントを引数に取る）設計になっているため、ユニットテスト時は DB 接続や OpenAI クライアントをモック可能です。
- OpenAI を呼ぶ関数は内部で _call_openai_api をラップしているため、ユニットテストで patch して外部呼び出しを防ぐのが簡単です。
- DuckDB を用いた研究系処理は DB のスナップショットを用意してローカルで再現することを推奨します。

よくあるトラブルシューティング
- .env を正しく読み込めない／設定が反映されない場合:
  - KABUSYS_DISABLE_AUTO_ENV_LOAD を設定しているか、プロジェクトルートが検出できない可能性があります。
  - python -m kabusys.config_setup で .env を再作成し、python -m kabusys.validate_config を実行してください。
- OpenAI 呼び出しが失敗する:
  - OPENAI_API_KEY が正しく設定されているか確認
  - ネットワーク接続、または API レート制限に注意（ログにリトライ情報が出ます）
- ログファイルが作成されない:
  - LOG_DIR 環境変数や権限を確認。ディレクトリ作成に失敗した場合はコンソール出力のみになります（警告が出ます）。

ライセンス・貢献
- 本プロジェクトのライセンス情報はリポジトリルートの LICENSE を参照してください（存在しない場合は管理者に問い合わせてください）。
- 変更を加える際は機密情報（.env）を絶対にコミットしないでください。

以上が本リポジトリの README です。必要であれば、より詳しい各モジュールの API 使用例（コードスニペット）や運用手順（systemd / supervisor / コンテナ化）について追記します。どの部分を詳しく知りたいか教えてください。