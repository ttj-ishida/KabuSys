# KabuSys

日本株自動売買システムのサブセット。システム監視、Execution エンジン起動、ポートフォリオ構築、リサーチ用ファクター計算、ニュース NLP（OpenAI）によるセンチメント、ペーパートレード検証レポート生成などのユーティリティ群を含みます。

バージョン: 0.1.0

---

目次
- プロジェクト概要
- 主な機能
- 必要条件
- セットアップ手順
- 使い方（コマンド一覧 / 実行例）
- 環境変数・設定
- 停止・Kill スイッチ
- ディレクトリ構成

---

プロジェクト概要
- KabuSys は日本株自動売買のためのツール群（監視、発注エンジン、ファクター計算、ニュース NLP、ペーパートレード検証など）を提供します。
- 設定は .env / 環境変数および config/*.yaml で管理します。実行時にログ設定やプロセス優先度設定が行われます。
- Paper Trading（KABUSYS_ENV=paper_trading）では発注はモック化され、本番 DB と分離（data/paper_trading.db を使用）されます。

主な機能（抜粋）
- 実行スクリプト
  - run_execution.py: ExecutionEngine の起動（実取引 / ペーパートレードを環境で切替）
  - run_monitoring.py: SystemMonitor をポーリングして監視ログを記録
- 設定支援 / 検証
  - config_setup.py: 対話式 .env 作成ウィザード
  - validate_config.py: 環境変数・config/*.yaml の検証（--strict オプションあり）
- 監視（monitoring）
  - system_monitor, trade_monitor, risk_monitor, monitoring_engine, kill_switch
  - MonitoringDB: SQLite に監視ログを永続化
- ポートフォリオ構築（portfolio）
  - 候補選定 / 重み算出 / ポジションサイズ決定 / セクター制限などの純粋関数
- リサーチ（research）
  - ファクター計算（momentum / volatility / value）、特徴量探索、IC 計算など（DuckDB 接続を受ける）
- AI 関連（ai）
  - news_nlp: OpenAI を使った銘柄別ニュースセンチメント集計と ai_scores への書き込み
  - regime_detector: ETF の MA200 とマクロニュースを合成して市場レジーム判定
- ツール
  - tools/paper_verification_report.py: ペーパートレード結果から検証レポートを生成
- ユーティリティ
  - logging_setup: 一貫したログ出力（stdout + 日次ローテートファイル）
  - process_priority: プロセス優先度 / CPU affinity 設定ユーティリティ

必要条件
- Python 3.9+
- パッケージ（主要）
  - duckdb
  - psutil
  - openai (AI 機能利用時)
  - PyYAML（config/*.yaml の検証を行う場合、任意）
- SQLite は標準ライブラリで使用
- ネットワークアクセス（kabuステーション API / OpenAI を利用する場合）

（開発環境に合わせて requirements.txt を用意している場合はそれを利用してください）

セットアップ手順（ローカル）
1. リポジトリをクローン / 取り込み
2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 依存パッケージをインストール
   - pip install duckdb psutil openai
   - （必要に応じて）pip install pyyaml
4. .env 作成（推奨: 対話ウィザード）
   - python -m kabusys.config_setup
     - ウィザードに従って J-Quants トークン、kabu API パスワードなどを入力
5. 設定検証（起動前チェック）
   - python -m kabusys.validate_config
   - 警告を厳格に扱う場合: python -m kabusys.validate_config --strict
6. デフォルトのデータディレクトリ / ログディレクトリが自動作成されます
   - デフォルト DB パス: data/kabusys.duckdb（DuckDB）, data/monitoring.db（SQLite）, data/paper_trading.db（Paper）
   - ログ: logs/<app_name>.log（TimedRotatingFileHandler）

環境変数（主なもの）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABUSYS_ENV: 実行環境（development / paper_trading / live）デフォルト: development
  - paper_trading: MockBrokerClient を使用し data/paper_trading.db を使用（本番 DB と分離）
- OPENAI_API_KEY: OpenAI API キー（ai.news_nlp / regime_detector 利用時に必須）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト data/paper_trading.db）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- LOG_DIR: ログファイル格納先（デフォルト logs/）
- PID_FILE_PATH, KILL_FLAG_PATH: 実行時の PID ファイル、kill.flag の位置（デフォルト data/…）

使い方（主要コマンド）
- 環境設定ウィザード
  - python -m kabusys.config_setup
- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict
- ExecutionEngine 起動
  - python -m kabusys.run_execution
  - 動作概要:
    - KABUSYS_ENV が paper_trading の場合、MockBrokerClient を使用し data/paper_trading.db に書き込む
    - プロセス優先度を "high" に設定
    - 停止フラグ data/stop_requested.flag があれば起動を中止
- Monitoring 起動（ポーリング）
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書き可能（デフォルト: 60）
  - 監視は KABUSYS_ENV に関わらず本番 sqlite_path を使用してログ記録
- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db PATH または環境変数 PAPER_TRADING_SQLITE_PATH
- AI 系（ライブラリ関数）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - これらは DuckDB の接続を受け取り、内部でテーブルを参照・更新します
  - OPENAI_API_KEY が必要（引数でキーを渡すことも可能）

停止・Kill スイッチ
- 実行中の ExecutionEngine / Monitoring にはフラグファイルで停止指示を与えられます
  - data/stop_requested.flag: 実行ループ（run_execution / run_monitoring）がこのファイルの存在を見て停止する
  - data/kill.flag: KillSwitch が条件を満たすと書き込み、ExecutionEngine を停止させる（evaluate により書かれる）
- Settings にて KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に kill.flag を自動でクリアします（本番では 0 推奨）

ログ
- logging_setup.setup_logging が標準化されたログ出力を行います
  - コンソール stdout 出力
  - 日次ローテーションファイル: logs/<app_name>.log（30 日保持）
- LOG_DIR / LOG_LEVEL で挙動を制御可能

ディレクトリ構成（主要ファイル）
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
    - system_monitor.py
    - trade_monitor.py         (※コード参照)
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py         (※実装参照)
  - execution/
    - execution_engine.py     (エンジン本体)
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
  - data/
    - pipeline.py              (データ取得 / last price date 等)
    - stats.py                 (zscore_normalize 等)
  - utils/
    - logging_setup.py
    - process_priority.py

（上記は本リポジトリの主要モジュールを抜粋したものです。細部の実装や追加ファイルはソースツリーをご参照ください。）

開発 / テスト時の注意
- .env を絶対に Git にコミットしないこと（config_setup にも注意書きあり）
- KABUSYS_ENV=live のときは本番に影響する設定が有効になるため、J-Quants / kabu API の設定や Kill Switch の挙動を慎重に確認してください
- OpenAI を使う機能は API 呼び出し・料金が発生するため事前にキーとコストを確認してください
- DuckDB / SQLite のパスはデフォルトで data/ 配下を使用します。適切なバックアップを推奨します
- run_monitoring は MONITOR_POLL_INTERVAL を秒で指定できます（環境変数）

ライセンス / 貢献
- 本プロジェクトのライセンスや貢献ルールがある場合はリポジトリのルートに LICENSE / CONTRIBUTING を置いてください（この README はコードベースに基づく概要ドキュメントです）。

サンプルコマンドまとめ
- 環境設定ウィザード:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config
- 実行エンジン起動:
  - python -m kabusys.run_execution
- 監視ループ起動:
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- ペーパートレード検証レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- AI スコア更新（例）:
  - Python から kabusys.ai.score_news(conn, target_date, api_key=...) を呼び出し

必要があれば、起動オプションや各モジュールの API 仕様（関数引数／戻り値等）について別途詳細ドキュメントを作成します。どの部分を優先してドキュメント化しましょうか？