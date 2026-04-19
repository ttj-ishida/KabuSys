KabuSys
=======

日本株向けの自動売買・リサーチ基盤（プロトタイプ実装）。  
このリポジトリは、発注実行エンジン、監視（モニタリング）、ポートフォリオ構築・ポジションサイジング、ファクター計算 / 研究、AI 補助（ニュースセンチメント / レジーム判定）、および運用支援ツール群を含みます。

主な設計方針
- 運用（Execution）と監視（Monitoring）は分離されたプロセスで動作
- DuckDB を分析・ファクタ計算に使用、SQLite を監視ログ・発注履歴に使用
- Paper Trading モードは本番 DB と完全分離（MockBrokerClient を使用）
- OpenAI を利用したニュース NLP / レジーム判定をサポート（API キー必須）
- ログ、PID、停止フラグなど運用に必要なファイルは data/ や logs/ に保存

機能一覧
- 実行系
  - ExecutionEngine（発注・注文管理・リスク管理・レコンシリエーション）
  - BrokerClientFactory による本番 / ペーパートレード切り替え
- 監視（Monitoring）
  - SystemMonitor: CPU / メモリ / ディスク / プロセス生存チェック、データ鮮度チェック
  - TradeMonitor: 注文滞留・約定異常などの検出（ログ参照）
  - RiskMonitor: ドローダウン、ポジション数上限監視とダッシュボード更新
  - MonitoringEngine: 各 Monitor を束ねたポーリングループ、KillSwitch 評価、AlertManager 経由で通知
- ポートフォリオ構築
  - 候補選定、等金額 / スコア加重、ポジションサイズ計算（単元丸め含む）
  - セクター集中制限、レジーム乗数
- 研究（Research）
  - ファクター計算（Momentum、Volatility、Value など）
  - 将来リターン、IC（Information Coefficient）、統計サマリー
  - DuckDB を使った SQL + Python 実装
- AI 機能
  - news_nlp: ニュース記事を OpenAI でスコアリングして ai_scores テーブルに登録
  - regime_detector: ETF (1321) の MA200乖離 + マクロニュースで日次レジーム判定
- 運用ツール
  - .env 対話ウィザード（config_setup）
  - 設定検証 CLI（validate_config）
  - Paper Trading 検証レポート生成スクリプト
- ユーティリティ
  - 統一的なログ設定（logs 日次ローテート）
  - プロセス優先度・CPU affinity 設定ユーティリティ
  - 設定読み込み (.env / .env.local 自動ロード)

前提・依存
- Python 3.9+
- 主要依存パッケージ（例）
  - duckdb
  - psutil
  - openai
  - （任意）PyYAML（validate_config の YAML 検証に必要）
- SQLite は標準ライブラリで提供

セットアップ手順（開発 / ローカル）
1. リポジトリをクローンしてワークディレクトリへ移動
2. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 必要パッケージをインストール（requirements.txt がない場合は手動で）
   - pip install duckdb psutil openai
   - PyYAML を使いたい場合: pip install pyyaml
4. 環境変数の準備
   - 対話ウィザードで .env を作成:
     - python -m kabusys.config_setup
   - あるいは .env を直接作成（デフォルトはプロジェクトルートの .env）
   - 必須環境変数:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - AI 機能を使う場合:
     - OPENAI_API_KEY を設定
   - その他の主な環境変数（省略可）
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
     - DUCKDB_PATH — デフォルト: data/kabusys.duckdb
     - SQLITE_PATH — デフォルト: data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH — デフォルト: data/paper_trading.db
     - LOG_LEVEL — デフォルト: INFO
     - LOG_DIR — デフォルト: logs/
     - PID_FILE_PATH, KILL_FLAG_PATH などは Settings から確認可能
5. 設定検証（推奨）
   - python -m kabusys.validate_config
   - 警告も失敗扱いにする場合は --strict オプションを付ける

起動 / 使い方
- 実行エンジン（Execution）
  - 本番・開発・ペーパーに応じて KABUSYS_ENV を設定
    - ペーパートレード（MockBrokerClient を使用し、data/paper_trading.db を使用）:
      - export KABUSYS_ENV=paper_trading
  - 起動:
    - python -m kabusys.run_execution
  - 停止:
    - run_execution は data/stop_requested.flag の存在を監視します。停止するにはこのファイルを作成するか、プロセスに SIGINT（Ctrl+C）を送って終了してください。
  - 実行時の PID ファイル: data/execution.pid（Settings.pid_file_path で参照）

- 監視プロセス（Monitoring）
  - 起動:
    - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒単位で上書きできます（デフォルト 60 秒）
    - export MONITOR_POLL_INTERVAL=30
  - 監視は本番 sqlite_path を使う設計（KABUSYS_ENV にかかわらず monitoring は本番 DB を参照）
  - 監視ループは data/stop_requested.flag を検出すると終了します

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from YYYY-MM-DD --to YYYY-MM-DD
  - デフォルト DB: 環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db

- AI 機能
  - news_nlp / regime_detector などを呼び出す際は OPENAI_API_KEY が必要
  - モジュール関数として使用することを想定（例: kabusys.ai.score_news）

運用関連ファイル・フラグ
- logs/: 日次ローテーションされるログ（デフォルト）
- data/execution.pid: ExecutionEngine の PID（起動時に設定）
- data/stop_requested.flag: 起動スクリプトが監視する停止フラグ（存在するとループを終了）
- data/kill.flag: KillSwitch が条件を満たした際に書き込むフラグ（ExecutionEngine を止めるために用いる）
- データベース
  - DuckDB: data/kabusys.duckdb（分析・ファクタ計算）
  - SQLite (monitoring): data/monitoring.db（監視ログ）
  - SQLite (paper trading): data/paper_trading.db（ペーパートレード専用）

重要な挙動・注意点
- run_execution は KABUSYS_ENV=paper_trading のときに MockBrokerClient を使い、paper_trading.db に記録して本番 DB と完全分離します。
- run_monitoring のポーリングは MONITOR_POLL_INTERVAL により上書き可能。0 以下の値はデフォルトにフォールバックします。
- ログディレクトリ作成に失敗するとファイル出力ハンドラは無効化され、コンソール出力のみになります。
- process priority の設定は OS の権限に依存します。権限不足で設定できない場合は警告ログが出ます。
- validate_config は config/*.yaml の存在確認・簡易パース（PyYAML がある場合）を行い、本番環境向けのガードチェックも実施します。
- .env の自動読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定することで無効化できます（主にテスト用途）。

ディレクトリ構成（抜粋）
- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数読み込み / Settings
  - config_setup.py           — .env 対話式ウィザード
  - validate_config.py        — 設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — SystemMonitor 起動スクリプト
  - utils/
    - logging_setup.py        — ログ設定ユーティリティ
    - process_priority.py     — プロセス優先度 / CPU affinity 設定
  - execution/                — ExecutionEngine 関連（broker, order_manager, risk_manager 等）
  - monitoring/
    - monitoring_db.py        — SQLite スキーマと簡易永続化 API
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - monitoring_engine.py
    - kill_switch.py
    - alert_manager.py
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
  - data/                     — （運用時）logs / sqlite / duckdb 等を配置する想定
  - tools/
    - paper_verification_report.py

開発のヒント
- 単体関数群（portfolio、research）は DuckDB 接続やシンプルな引数で呼べるように作られており、ユニットテストを書きやすい設計です。
- OpenAI を用いる機能は外部 API に依存するため、テスト時は API 呼び出し箇所をモックすることを推奨します（コード内でも _call_openai_api の差し替えを想定）。
- SQLite / DuckDB のファイルパスは Settings 経由で取得するため、テスト用に一時ファイルを指定して分離できます。

ライセンス・バージョン
- パッケージバージョン: src/kabusys/__version__ = "0.1.0"
- ライセンス情報はリポジトリに別途追加してください（LICENSE ファイル等）。

問い合わせ・貢献
- バグ報告・機能要望は Issue を作成してください。
- コントリビュートする場合は fork → プルリクエストをお願いします。スタイルやテストがあるとスムーズにマージされます。

以上。必要であれば README に「設定例（.env.example）」や「起動スクリプトの systemd ユニット例」など運用向けの追加セクションを追記します。どの情報を補足しますか？