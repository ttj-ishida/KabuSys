# KabuSys

日本株向け自動売買システムのモジュール群。  
このリポジトリは戦略・ポートフォリオ構築、実行エンジン、監視、研究用ユーティリティ、AIベースのニュース解析などを含むコンポーネント群で構成されています。

バージョン: 0.1.0

---

目次
- プロジェクト概要
- 主な機能一覧
- セットアップ手順
- 使い方（起動・運用）
- 主要環境変数
- 停止・Kill Switch の仕組み
- ディレクトリ構成

---

プロジェクト概要
- KabuSys は日本株自動売買のためのライブラリ／実行フレームワークです。
- 戦略（ファクター計算等）、ポートフォリオ構築、発注（ExecutionEngine）、監視（Monitoring）、研究用モジュール、AI を用いたニュース分析まで含むフルスタック寄りの構成。
- 開発環境・ペーパートレード・本番環境を切り替えて動作します（KABUSYS_ENV）。

主な機能一覧
- 実行系
  - ExecutionEngine 起動スクリプト（run_execution.py）
  - ブローカークライアントの抽象化（BrokerClientFactory。paper_trading では MockBrokerClient を使用）
  - 注文管理（OrderManager / OrderRepository、trade_logs への永続化）
  - リスク管理（RiskManager）
- 監視系
  - SystemMonitor / TradeMonitor / RiskMonitor を束ねる MonitoringEngine（run_monitoring.py）
  - 監視ログの永続化（SQLite を利用する monitoring_db）
  - Kill Switch（条件に応じて data/kill.flag を書き込み Execution を停止）
- ポートフォリオ構築
  - 候補選定・ウェイト計算（equal / score）
  - リスク調整（セクターキャップ、レジーム乗数）
  - ポジションサイズ計算（単元株丸め、資金制約考慮）
- 研究・分析
  - DuckDB を使ったファクター計算（momentum / volatility / value）
  - 将来リターン計算、IC 計算、統計サマリー（feature_exploration）
- AI（OpenAI 経由）
  - ニュースのセンチメント解析（news_nlp）
  - 市場レジーム判定（regime_detector）
- ツール
  - Paper Trading 検証レポート生成（tools/paper_verification_report.py）
- 設定管理
  - .env を対話式で作成するウィザード（config_setup.py）
  - 起動前に設定を検証する CLI（validate_config.py）
- ユーティリティ
  - 統一ログ設定（utils/logging_setup.py）
  - プロセス優先度 / CPU affinity 設定（utils/process_priority.py）

---

セットアップ手順（開発環境向け）
1. Python 環境
   - Python 3.10+ を推奨（型ヒントや一部機能の利用を想定）。
2. 依存パッケージのインストール（例）
   - pip install duckdb psutil openai
   - YAML 検証を行う場合: pip install pyyaml
   - 必要に応じて他の依存を追加してください（プロジェクトの requirements.txt がある場合はそれを利用）。
3. リポジトリルートをプロジェクトルートとして扱う（.env 自動ロードのため .git や pyproject.toml があることを前提）。
4. 初期設定 (.env) の作成
   - 対話式ウィザードを使う:
     - python -m kabusys.config_setup
   - 生成・編集した .env は絶対に Git にコミットしないでください（シークレット含む）。
5. 設定検証
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱い（exit 1）になります。
6. データディレクトリ作成
   - デフォルトでは data/ 下に DB・PID・flag 等を作成します。必要なら事前に作成してください。
7. ログディレクトリ
   - デフォルト logs/ に日次ローテーションでログが出力されます（utils/logging_setup.py）。

主要環境変数（抜粋）
- 必須（validate_config でチェックされる）
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- 推奨・任意
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
  - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 DB（デフォルト: data/paper_trading.db）
  - LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）
  - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: 本番での通知用（任意）
  - OPENAI_API_KEY: news_nlp / regime_detector で必要
  - PAPER_FILL_MODE: paper_trading の Fill モード（instant / partial / never / reject）
- 監視ループ制御
  - MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）
- Kill Switch 関連
  - KILL_FLAG_PATH: data/kill.flag のパス（デフォルト: data/kill.flag）
  - KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（0/1、デフォルト 0）

使い方（起動・運用）
- 環境設定（例）
  1) python -m kabusys.config_setup
  2) python -m kabusys.validate_config
- 実行エンジン（ExecutionEngine）起動
  - 本番 / ペーパーの切り替えは KABUSYS_ENV で制御（paper_trading では MockBrokerClient を使用し、data/paper_trading.db に記録）。
  - 起動:
    - python -m kabusys.run_execution
  - 実行はバックグラウンドスレッドで行われ、data/execution.pid に PID を書きます。
  - 停止方法:
    - data/stop_requested.flag を作成すると run_execution 側で検出して停止します（スクリプト内で _STOP_FLAG を参照）。
    - また Kill Switch により data/kill.flag が書き込まれると ExecutionEngine を停止します。
- 監視プロセス起動
  - 監視は専用スクリプトを使ってポーリングします（デフォルトは MONITOR_POLL_INTERVAL=60 秒）。
  - 起動:
    - python -m kabusys.run_monitoring
  - 監視は monitoring DB（Settings.sqlite_path）を使用します。Monitoring は KABUSYS_ENV に関係なく本番 sqlite_path を用いる設計です。
  - ポーリング間隔を環境変数で上書き:
    - export MONITOR_POLL_INTERVAL=30
- Paper Trading レポート（ツール）
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - オプション --db で SQLite ファイルを指定可能。環境変数 PAPER_TRADING_SQLITE_PATH も参照します。
- AI 機能
  - news_nlp.score_news / regime_detector.score_regime は OPENAI_API_KEY が必要。API 呼び出しはリトライ・例外吸収の設計になっています。

停止・Kill Switch の仕組み
- KillSwitch（kabusys.monitoring.kill_switch）は RiskMonitor 等の結果を評価して条件を満たすと data/kill.flag を書き込みます。
- ExecutionEngine は起動時・ループ中に kill.flag を検査し、存在する場合は発注処理を停止します。
- 手動で停止したい場合は data/stop_requested.flag を作成すると各 run_* スクリプトが検知して安全に終了します。
- kill.flag を自動でクリアするかは KILL_FLAG_CLEAR_ON_START（0/1）で制御。production では 0 を推奨。

ログと監査
- utils/logging_setup.setup_logging により、stdout（コンソール）出力 + 日次ローテーションのファイル出力（logs/<app_name>.log）が設定されます。
- ログレベルは LOG_LEVEL 環境変数または引数で指定可能。
- 監視データ・取引ログは SQLite（monitoring.db / paper_trading.db）に永続化されます。分析は DuckDB（data/kabusys.duckdb）を利用します。

ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py
  - config.py — 環境変数 / Settings
  - config_setup.py — .env 対話ウィザード
  - validate_config.py — 起動前チェック CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート
  - portfolio/
    - portfolio_builder.py — 候補選定・等重/スコア加重
    - position_sizing.py — 株数・資金配分
    - risk_adjustment.py — セクターキャップ・レジーム乗数
  - monitoring/
    - monitoring_db.py — SQLite スキーマ・永続化
    - monitoring_engine.py — Monitor 合成・ループ
    - system_monitor.py — システム状態 / データ鮮度監視
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - kill_switch.py — kill.flag 管理
    - (その他: trade_monitor.py, alert_manager.py などが想定される)
  - execution/  (実行系: Broker, Engine, OrderManager 等の実装)
  - ai/
    - news_nlp.py — ニュースセンチメント解析（OpenAI）
    - regime_detector.py — マーケットレジーム判定（OpenAI + MA200）
  - research/
    - factor_research.py — ファクター計算（momentum/volatility/value）
    - feature_exploration.py — 将来リターン・IC 等の研究支援
  - utils/
    - logging_setup.py — ログ設定ユーティリティ
    - process_priority.py — プロセス優先度 / CPU affinity
    - (その他ユーティリティ群)

補足・運用上の注意
- .env は機密情報を含みます。絶対に Git へコミットしないでください。
- 本番環境（KABUSYS_ENV=live）では LINE 通知や Kill Switch の設定を慎重に行ってください（validate_config は live 時に保護チェックを行います）。
- OpenAI を使う機能は API コスト・レスポンス安定性の観点から実運用前に十分な試験を行ってください。
- run_monitoring のポーリングはデフォルト 60 秒ですが、環境に応じて MONITOR_POLL_INTERVAL で調整可能です。1 秒未満や 0 は避けてください。

ライセンス・貢献
- （リポジトリに LICENSE ファイル等があればここに記載してください）

以上が本コードベースの概要と運用・セットアップ手順です。必要であれば、起動サンプルや .env.example のテンプレート、各モジュールの詳細ドキュメント（API、設定項目の意味、DB スキーマの説明など）を追加で作成します。どの部分を詳しく書けば良いか指示をください。