# KabuSys

日本株向けの自動売買 / リサーチ基盤（ライブラリおよび起動スクリプト群）です。  
このリポジトリは、シグナル生成・ポートフォリオ構築・ポジションサイジング・発注エンジン（ExecutionEngine）・監視（Monitoring）・AIベースのニュースセンチメント評価・レジーム判定・各種ツールを含みます。

概要
- 設計方針はロバスト性（フェイルセーフ）と再現性（ルックアヘッドバイアス防止）を重視しています。
- DuckDB を分析用データストア、SQLite を監視 / 発注ログ用に利用します。発注先は実際の kabuステーション（live）かモック（paper_trading）を切り替え可能です。
- OpenAI API を用いたニュース NLP（センチメント）・レジーム判定機能を持ちます（APIキー必須）。
- ログはコンソール（stdout）と日次ローテートされたファイル（logs/<app>.log）に出力されます。

主な機能一覧
- ExecutionEngine 起動スクリプト（run_execution）
  - 本番 / ペーパートレード切替（KABUSYS_ENV）
  - BrokerClientFactory によるブローカークライアント生成
  - OrderManager / RiskManager / Reconciler 等の組み立て
  - エンジンは別スレッドで実行、停止はフラグファイルで制御
- Monitoring（監視）
  - SystemMonitor: CPU/メモリ/ディスク、プロセス生存、データ鮮度を監視
  - TradeMonitor: 注文ログの滞留・約定異常の検出（実装ファイルあり）
  - RiskMonitor: ドローダウンやポジション上限を監視し、kill.flag を書き込み可能
  - MonitoringEngine: 各 Monitor を束ねるポーリングループ
  - run_monitoring スクリプト（MONITOR_POLL_INTERVAL で間隔を制御）
- ポートフォリオ構築
  - 候補選定、等重/スコア重み、セクター制限、レジーム乗数、ポジションサイズ計算（単元丸め等）
- リサーチ
  - ファクター計算（モメンタム・バリュー・ボラティリティ等）
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリー
- AI 機能
  - news_nlp: raw_news を集約して OpenAI（gpt-4o-mini）で銘柄別センチメントを生成し ai_scores テーブルへ書込
  - regime_detector: ETF（1321）MA200 とマクロニュースの LLM センチメントを合成して market_regime を判定・永続化
- ツール
  - paper_verification_report: ペーパートレード用 DB を元に稼働率・注文成功率・P95 レイテンシ等の検証レポートを出力
- 設定管理
  - .env 自動読み込み（プロジェクトルートに .env / .env.local がある場合）
  - config_setup: 対話式ウィザードで .env を作成
  - validate_config: 起動前に .env / config/*.yaml の簡易検証

セットアップ手順（ローカル開発向け）
1. Python バージョン
   - Python 3.10 以上を推奨（文法で | 型合成を使用しているため）。
2. 依存ライブラリをインストール
   - 例:
     pip install duckdb psutil openai PyYAML
   - 必要に応じて仮想環境を作成してください。
   - アプリによっては追加パッケージ（requests 等）が必要な場合があります。requirements.txt があればそちらを使用してください（本リポジトリ例では明示的な requirements.txt は含まれていません）。
3. プロジェクトルートで .env を作成
   - 対話式で作る:
     python -m kabusys.config_setup
   - あるいは .env.example を参考に手動で作成（.env はバージョン管理にコミットしないこと）。
4. 設定検証（任意）
   - python -m kabusys.validate_config
   - --strict を付けると警告もエラー扱いになります。
5. データディレクトリ作成
   - デフォルトで使用されるファイルは以下（.env で上書き可能）:
     - data/kabusys.duckdb (DuckDB)
     - data/monitoring.db (監視用 SQLite)
     - data/paper_trading.db (ペーパートレード用 SQLite)
     - logs/ ディレクトリ（ログ出力）
   - 手動でディレクトリを作っておくと安心です（logging_setup が自動作成も試みます）。

主要な環境変数（代表）
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV: execution モード（development / paper_trading / live）。デフォルト: development
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: paper_trading の約定挙動（instant|partial|never|reject）
- OPENAI_API_KEY: OpenAI 呼び出しに使用（news_nlp, regime_detector）
- LOG_LEVEL / LOG_DIR
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）
- KILL_FLAG_CLEAR_ON_START: 本番で Kill Flag を自動クリアする挙動（0/1、本番では0推奨）

使い方（主要コマンド）
- 設定ウィザード
  - python -m kabusys.config_setup
- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict
- 実行エンジン起動（ExecutionEngine）
  - 環境変数で本番/ペーパートレードを切替:
    - 本番: KABUSYS_ENV=live python -m kabusys.run_execution
    - ペーパー: KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  - ペーパー時は専用 DB（PAPER_TRADING_SQLITE_PATH）を使用し、本番 DB と完全に分離されます。
  - 実行中は data/execution.pid に PID を書きます。停止は data/stop_requested.flag を作成することで行えます（外部からの停止シグナル）。
- 監視プロセス起動
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring などで間隔指定可能
  - run_monitoring は常に本番 sqlite_path を参照して監視データを記録します（KABUSYS_ENV に依存しません）。
- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB を明示する場合:
    python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
- AI バッチ処理（プログラム的に呼び出す）
  - kabusys.ai.score_news / kabusys.ai.regime_detector.score_regime を呼び出し、OpenAI API キーを渡すか環境変数 OPENAI_API_KEY を設定します。

停止・Kill Switch の仕組み
- 外部からの停止:
  - data/stop_requested.flag を作成すると run_monitoring/run_execution のループが検出して停止処理を行います。
- Kill Switch:
  - リスク条件（例: ドローダウン超過）で kabusys.monitoring.kill_switch が data/kill.flag を書き込みます。ExecutionEngine はこのフラグを見て安全に停止します。KILL_FLAG_CLEAR_ON_START を 1 に設定すると起動時に自動クリアされますが、本番では 0 を推奨します。

ログについて
- 共通のログ設定ユーティリティ kabusys.utils.logging_setup.setup_logging(app_name=...)
  - stdout にも出力し、logs/<app_name>.log に日次ローテーションで保存（30日分保管）。
  - LOG_LEVEL / LOG_DIR 環境変数で制御可能。

ディレクトリ構成（抜粋）
- src/kabusys/
  - __init__.py
  - config.py               — 環境変数/.env の自動ロードと Settings クラス
  - config_setup.py         — 対話式 .env ウィザード
  - validate_config.py      — 設定検証 CLI
  - run_execution.py        — ExecutionEngine 起動スクリプト
  - run_monitoring.py       — Monitoring 起動スクリプト
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
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py (注: 実装が別ファイルである場合あり)
  - utils/
    - logging_setup.py
    - process_priority.py
  - data/ (実行時に生成されることが多い)
    - *.db, kill.flag, stop_requested.flag, execution.pid など

設計上の注意点 / 運用上の注意
- .env（機密情報）をリポジトリにコミットしないでください。
- 本番環境での KABUSYS_ENV=live 設定は十分にテスト・レビューした上で行ってください。validate_config は live 時に特別な警告を出します。
- OpenAI API 呼び出しはレート制限やエラーを踏まえたリトライが組み込まれていますが、APIキーの管理・コスト管理は運用側で行ってください。
- プロセス優先度設定（set_process_priority）は psutil によって行われます。権限不足で設定に失敗することがあります（警告ログ、動作継続）。
- DuckDB / SQLite のファイルパスは .env で指定可能です。監視 DB は run_monitoring が常に本番 sqlite_path を使うため、意図せず本番 DB を監視対象にしないよう注意してください（paper_trading は paper_sqlite_path を使用）。

開発者向けメモ
- 多くのモジュールは DuckDB 接続や sqlite3.Connection を受け取り外部副作用を最小化する設計です（テスト容易性向上）。
- AI 呼び出し部分はテストのために _call_openai_api を patch して差し替えられるよう実装されています。
- リポジトリルートの検出は config._find_project_root() によって行われ、.git や pyproject.toml を基準にしています。パッケージ配布後も動作するよう CWD に依存しない設計です。

以上が本リポジトリの概要・セットアップ・使い方です。詳細は各モジュールの docstring を参照してください。README の内容で補足が必要な箇所（例: requirements.txt の追加、systemd ユニット例、サンプル .env）などがあれば教えてください。必要に応じて追記します。