KabuSys — 日本株自動売買システム
================================

概要
----
KabuSys は日本株向けの自動売買・リサーチ基盤の一部です。本リポジトリには以下の主要機能を提供するモジュール群が含まれます。

- 実行エンジン（ExecutionEngine）の起動スクリプトと周辺ユーティリティ
- 監視サブシステム（System / Trade / Risk のモニタ、Kill Switch）
- ポートフォリオ構築（銘柄選定・配分・ポジションサイズ計算）
- リサーチ（ファクター計算・特徴量解析）
- AI 支援モジュール（ニュース NLP によるセンチメント、レジーム判定）
- 開発用ツール（.env ウィザード、設定検証、Paper Trading 検証レポート）

本 README はコードベース（src/kabusys/*）に基づく導入・利用方法の要点をまとめたものです。

主な機能
--------
- 環境設定ウィザード (.env 作成 / 更新): kabusys.config_setup
- 設定検証 CLI (.env と config/*.yaml の事前チェック): kabusys.validate_config
- ExecutionEngine 起動: run_execution.py
  - KABUSYS_ENV=paper_trading 時は MockBrokerClient を使用し、paper_trading DB に完全分離で記録
- Monitoring 起動: run_monitoring.py
  - System / Trade / Risk Monitor をポーリングしてログ・アラートを管理
  - Kill Switch による ExecutionEngine 停止制御
- ポートフォリオ構築ライブラリ:
  - 候補選定、等重／スコア重み、ポジションサイズ計算、セクター上限、レジーム乗数
- Research ライブラリ:
  - momentum / volatility / value のファクター計算
  - 将来リターン計算、IC（情報係数）、統計サマリ
- AI モジュール:
  - news_nlp: OpenAI を使ってニュースを銘柄ごとにスコアリング（ai_scores に保存）
  - regime_detector: ma200 とマクロニュースで市場レジーム判定、market_regime に保存
- 開発用レポート:
  - tools.paper_verification_report: Paper Trading DB から検証レポート生成

前提条件
--------
- Python 3.10 以上（型ヒントに PEP 604 の | を使用）
- 主な Python パッケージ（プロジェクトに requirements.txt がない場合は以下を目安にインストール）
  - duckdb
  - psutil
  - openai
  - PyYAML（config/*.yaml の検証を行う場合）
- データ格納ディレクトリ（デフォルト: data/）に書き込み権限

セットアップ手順
----------------

1. リポジトリをクローンして Python 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   - pip install duckdb psutil openai PyYAML
   - （実際のプロジェクトでは requirements.txt を用意して pip install -r requirements.txt を推奨）

3. データディレクトリを準備（任意）
   - mkdir -p data

4. .env の初期作成（ウィザード）
   - python -m kabusys.config_setup
   - ウィザードは J-Quants トークンや kabuAPI パスワード等の必要な環境変数を対話式で入力し .env を生成します。
   - 生成後は python -m kabusys.validate_config で検証してください。

主要な環境変数（抜粋）
---------------------
- 必須
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- 動作モード
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
    - paper_trading 時は発注を模擬し data/paper_trading.db を使用
- DB パス
  - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH（paper_trading 用 SQLite、デフォルト: data/paper_trading.db）
- OpenAI
  - OPENAI_API_KEY（news_nlp / regime_detector の呼び出しに必要）
- ログ / プロセス制御
  - LOG_LEVEL（DEBUG|INFO|...）
  - PID_FILE_PATH（ExecutionEngine 用 pid ファイルパス）
  - KILL_FLAG_PATH（Kill Switch が書き込むパス）
  - KILL_FLAG_CLEAR_ON_START（1 で起動時に kill.flag を自動クリア）
- その他
  - MONITOR_POLL_INTERVAL（監視ループのポーリング間隔（秒）; run_monitoring のデフォルトは 60 秒）
  - PAPER_FILL_MODE（paper_trading の fill 動作: instant|partial|never|reject）

使い方（主要コマンド）
--------------------

- 設定ウィザード
  - python -m kabusys.config_setup
    - .env の作成・更新（対話式）

- 設定検証
  - python -m kabusys.validate_config [--strict]
    - 必須変数や config/*.yaml の妥当性を事前にチェック

- 実行エンジン起動（Execution）
  - python -m kabusys.run_execution
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用 DB に記録し MockBroker を使用
    - 起動前に data/stop_requested.flag が存在すると起動をキャンセル
    - 実行中に停止させたい場合は data/stop_requested.flag を作成（または kill.flag 周りの仕組みを使用）

- 監視プロセス起動（Monitoring）
  - python -m kabusys.run_monitoring
    - 各 Monitor が初期化され、定期ポーリング（デフォルト 60 秒）を開始
    - 環境変数 MONITOR_POLL_INTERVAL で秒数を上書き可能
    - 停止方法: プロセスに SIGINT（Ctrl+C）またはプロジェクトルートの data/stop_requested.flag を作成

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
    - PAPER_TRADING_SQLITE_PATH 環境変数または --db で DB を指定可能

- AI スコアリング / レジーム判定（ライブラリ関数）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
    - OPENAI_API_KEY が必要（引数で渡しても可）

停止・Kill Switch の挙動
-----------------------
- stop_requested.flag（run_monitoring / run_execution が参照）
  - run_monitoring.py / run_execution.py は起動時およびループ中に data/stop_requested.flag をチェックし、存在すると終了または実行停止します（安全停止フラグ）。
- kill.flag（KillSwitch）
  - Monitoring 内の KillSwitch が条件を満たすと settings.kill_flag_path（デフォルト data/kill.flag）に理由を書き込みます。ExecutionEngine はこのファイルを検知して自ら停止します。
  - Settings で KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に kill.flag を自動クリアしますが、本番では 0 を推奨。

データベース & マイグレーション
------------------------------
- run_* スクリプトは起動時に monitoring DB の初期化（init_monitoring_db）を行います。テーブルが存在しない場合は作成され、必要に応じて簡易マイグレーション（カラム追加）を行います。
- paper_trading モードは本番 DB とは分離された PAPER_TRADING_SQLITE_PATH を使用します。

ディレクトリ構成（主要ファイル）
------------------------------
以下は src/kabusys 以下の代表的な構成（抜粋）です。

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / Settings
  - config_setup.py          — .env ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_monitoring.py        — Monitoring ポーリング起動スクリプト
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - tools/
    - paper_verification_report.py
  - ai/
    - news_nlp.py
    - regime_detector.py
  - monitoring/
    - monitoring_db.py
    - monitoring_engine.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py
  - execution/                — Execution エンジン関連（order_repository 等）
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - utils/
    - process_priority.py

（実際のリポジトリにはさらに多くのモジュール・サブパッケージが含まれます）

運用上の注意
------------
- 本番運用時（KABUSYS_ENV=live）は設定を特に慎重に確認してください（LINE 通知設定や Kill Switch 設定など）。validate_config による事前チェックを推奨します。
- OpenAI を利用する処理は API 呼び出しで失敗する可能性があるため、フェイルセーフ（0.0 にフォールバック等）やリトライ処理を組み込んでいます。API キーの管理には注意してください。
- paper_trading モードは本番 DB と完全に分離されるよう設計されています。実際の発注が行われる live モードでは十分な検証の上で運用してください。
- process priority / CPU affinity 設定は OS に依存し権限が必要な場合があります（psutil 使用）。設定に失敗しても警告を出してスキップします。

トラブルシューティング
---------------------
- .env の自動読み込み:
  - config.py はプロジェクトルート（.git または pyproject.toml）を探索して .env/.env.local を自動読み込みします。自動読込を無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- ログレベルは LOG_LEVEL で調整できます（例: DEBUG で詳細ログ）。
- monitoring や execution の起動で既に stop フラグがある場合は起動を中止する挙動があります（安全機構）。

最後に
------
この README は現在のコードベース（src/kabusys/*）の機能・使用方法の要約です。詳細な実装や運用ルールは各モジュールのドキュメント・コード内コメントを参照してください。必要であれば README に追記すべき点（例えば systemd ユニット定義サンプルや docker-compose 設定例、CI/CD 手順など）を教えてください。