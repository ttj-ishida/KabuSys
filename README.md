KabuSys — 日本株自動売買システム (README)
======================================

概要
----
KabuSys は日本株向けの自動売買／リサーチ基盤のコアライブラリです。本リポジトリは以下の主要機能を持つモジュール群で構成されています。

- 実行エンジン（ExecutionEngine）: 発注・注文管理・リスク制御を行うランタイム
- 監視（Monitoring）: システム状態・注文状態・リスク監視と Kill Switch
- ポートフォリオ構築: シグナル選別、重み付け、株数決定（単体関数群）
- リサーチ / ファクター計算: モメンタム／バリュー／ボラティリティ等の算出
- AI 製品: ニュースの NLP によるセンチメント評価／市場レジーム判定（OpenAI）
- ユーティリティ: ロギング設定、プロセス優先度設定、設定読み込みウィザード等
- ツール: ペーパートレード検証レポート生成スクリプト 等

特徴
----
- SQLite / DuckDB を使ったローカル DB 構成（データ永続化と分析を分離）
- 環境切替: KABUSYS_ENV により development / paper_trading / live を分離
- Paper Trading モードでは本番 DB と分離して data/paper_trading.db を使用
- .env ウィザード・設定検証 CLI を提供し、起動前チェックが可能
- OpenAI を使ったニュース NLP、レジーム判定を実装（フェイルセーフ・リトライ付き）
- ロギングは統一的に設定（コンソール + 日次ローテートファイル）

必要条件
-------
- Python 3.10+
- 主要依存パッケージ（例）
  - duckdb
  - psutil
  - openai
  - PyYAML（config 検証時に必要、任意）
- （プロジェクトによっては追加パッケージが必要になります）

インストール例
--------------
仮想環境を作成して必要なパッケージをインストールしてください（requirements.txt は付属しない想定）。

1. 仮想環境作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. パッケージインストール（例）
   - pip install duckdb psutil openai PyYAML

設定（.env）
-----------
- 設定は環境変数またはルートの .env / .env.local で行います。自動で .env をプロジェクトルートから読み込みます（CWD に依存しない探索）。
- 自動ロードを無効にする場合: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

主要な環境変数（抜粋）
- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
- OPENAI_API_KEY（AI 機能を使う場合に必要）
- KABUSYS_ENV（development / paper_trading / live、デフォルト: development）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（paper_trading モードの DB、デフォルト: data/paper_trading.db）
- LOG_LEVEL（デフォルト: INFO）
- MONITOR_POLL_INTERVAL（Monitoring ポーリング間隔（秒）、デフォルト: 60）
- PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START などの監視関連設定

.env の作成支援・検証
---------------------
- 対話式ウィザードで .env を作る:
  - python -m kabusys.config_setup
- 設定の検証:
  - python -m kabusys.validate_config
  - --strict を付けると警告も失敗扱い（exit code 1）

使い方（実行スクリプト）
-----------------------
1. 監視プロセスを起動（SystemMonitor のポーリング）
   - python -m kabusys.run_monitoring
   - 環境変数 MONITOR_POLL_INTERVAL を設定するとポーリング間隔を上書きできます（秒、デフォルト 60）。
   - 監視プロセスは Settings.sqlite_path（monitoring.db）と DuckDB を接続して動作します。
   - 停止はプロジェクトルート/data/stop_requested.flag を作成することで安全に停止できます。

2. 実行エンジン（ExecutionEngine）を起動
   - python -m kabusys.run_execution
   - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使い data/paper_trading.db に記録します（本番 DB と分離）。
   - プロセス起動時に data/execution.pid を使う仕組みがあります。停止は data/stop_requested.flag を作成する等で制御します。

3. Paper Trading 検証レポート生成
   - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
   - デフォルト DB: data/paper_trading.db （PAPER_TRADING_SQLITE_PATH で変更可）
   - 稼働率 / 注文成功率 / レイテンシ等を集計し PASS/FAIL 判定を表示します。

AI 機能（ニュース NLP / レジーム検出）
------------------------------------
- OpenAI API を利用します。API キーは OPENAI_API_KEY 環境変数か関数引数で指定してください。
- news_nlp.score_news / regime_detector.score_regime は API 呼び出しに対してリトライ・フェイルセーフを実装しています。
- API キー未設定時は例外を投げますので運用時は必ず設定してください。

ログ・データパス
----------------
- ログディレクトリ: デフォルト logs/。setup_logging() で指定可能。
- DuckDB: data/kabusys.duckdb（分析用）
- SQLite (監視): data/monitoring.db
- Paper Trading DB: data/paper_trading.db
- フラグ・PID: data/kill.flag, data/stop_requested.flag, data/execution.pid

注意点 / 実運用向けメモ
---------------------
- .env は機密情報を含むため Git へコミットしないでください（config_setup でも注意書きを出力します）。
- KABUSYS_ENV=live の際は特に設定を慎重に確認してください（validate_config が警告します）。
- process_priority.set_process_priority() により起動スクリプトは優先度を "high" に設定しようとします（権限がない場合は警告で続行）。
- OpenAI 呼び出しはレート制限・サーバエラーに対してバックオフリトライを行いますが、費用管理・レート制御は運用側で注意してください。

ディレクトリ構成（主要ファイル）
------------------------------
以下は src/kabusys 以下の主要モジュールと役割（抜粋）です。

- kabusys/
  - __init__.py (パッケージ定義)
  - config.py (環境変数の読み込み・Settings クラス)
  - config_setup.py (.env 対話ウィザード)
  - validate_config.py (起動前チェック)
  - run_monitoring.py (SystemMonitor ポーリングループ起動)
  - run_execution.py (ExecutionEngine 起動)
  - utils/
    - logging_setup.py (ロギング初期化)
    - process_priority.py (プロセス優先度・CPU affinity)
  - monitoring/
    - monitoring_db.py (SQLite テーブル初期化と読み書き)
    - system_monitor.py (システム状態・データ鮮度監視)
    - trade_monitor.py (trade 関連監視 — 注釈: 実装ファイルあり)
    - risk_monitor.py (ドローダウン・ポジション上限監視)
    - kill_switch.py (kill.flag を管理)
    - monitoring_engine.py (複数モニタの束ね)
    - alert_manager.py (アラート送信管理 — 実装ファイルあり)
  - execution/ (発注エンジン関連: BrokerFactory, ExecutionEngine, OrderManager, RiskManager 等)
  - portfolio/
    - portfolio_builder.py (候補選定・重み)
    - position_sizing.py (株数計算・スケーリング)
    - risk_adjustment.py (セクターキャップ・レジーム乗数)
  - research/
    - factor_research.py (momentum/value/volatility)
    - feature_exploration.py (forward returns, IC, summary)
  - ai/
    - news_nlp.py (ニュース NLP -> ai_scores 書込)
    - regime_detector.py (市場レジーム判定)
  - tools/
    - paper_verification_report.py (ペーパートレード検証レポート)

追加情報
--------
- モジュールのドキュメント文字列（docstring）に設計方針・注意事項が書かれています。実装を改変する際は docstring を参照してください。
- DB スキーマのマイグレーションは簡易的にコード内で行われます（monitoring_db.init_monitoring_db）。
- テスト時には環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自動 .env 読み込みを無効化できます。

問い合わせ / 開発メモ
--------------------
- 開発者向けには、まず python -m kabusys.config_setup で .env を作成 → python -m kabusys.validate_config で検証 → ログを確認しながら python -m kabusys.run_execution / run_monitoring を起動するワークフローを推奨します。
- AI 機能や外部 API 呼び出し部分はモック化しやすい設計になっています（テストで _call_openai_api を差し替える等）。

以上が本コードベースの README 相当の説明です。必要であれば「インストール用 requirements.txt の提案」「docker-compose での実行例」「より詳細な起動・運用手順（systemd / Supervisor）」なども作成できます。どれを追加しますか？