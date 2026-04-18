KabuSys — 日本株自動売買システム
=============================

このリポジトリは日本株向けの自動売買システム用ライブラリ/実行スクリプト群です。
主要機能はシグナル→ポートフォリオ構築→発注（ExecutionEngine）と、システム/取引の監視（Monitoring）、
研究用ファクター計算、AI を使ったニュースセンチメント評価などを含みます。

本 README はコードベースを参照して作成した概要・セットアップ・利用法・ディレクトリ構成をまとめたものです。

プロジェクト概要
----------------
- 自動売買の実行エンジン（ExecutionEngine）とモニタリング（Monitoring）を分離した設計。
- DuckDB を分析用 DB、SQLite を監視・発注ログ用 DB に使用。
- Paper Trading（検証）モードをサポートし、本番 DB と完全に分離して動作可能。
- ニュースの NLP に OpenAI（gpt-4o-mini）を利用したセンチメント評価機能と、市場レジーム判定。
- ポートフォリオ構築、ポジションサイジング、セクター制約などの純粋関数群を提供（テスト容易）。
- ログはコンソール（stdout）と日次ローテートファイルへ出力する統一ロギング設定を利用。

主な機能一覧
-------------
- 実行起動スクリプト
  - run_execution.py：ExecutionEngine を起動。KABUSYS_ENV=paper_trading のときは MockBroker を使用し data/paper_trading.db に記録。
- 監視起動スクリプト
  - run_monitoring.py：SystemMonitor のポーリングループを起動。MONITOR_POLL_INTERVAL で間隔変更可（デフォルト 60s）。
- 設定管理・ヘルパ
  - config.py：環境変数/.env の読み込み・Settings クラス
  - config_setup.py：.env を対話式で作成・更新するウィザード
  - validate_config.py：起動前チェック（必須環境変数・ファイルの存在・YAML パース等）
- 監視機能（monitoring）
  - system_monitor.py：CPU/メモリ/ディスク、Execution プロセス存在チェック、データ鮮度チェック
  - trade_monitor.py / risk_monitor.py：注文滞留、約定異常、ドローダウン・ポジション上限監視
  - kill_switch.py：条件に応じて data/kill.flag を書き込み ExecutionEngine を停止させる仕組み
  - monitoring_db.py：監視用 SQLite のスキーマ初期化・永続化 API
  - monitoring_engine.py：複数モニタを束ねるエンジン
- Execution 関連（execution モジュール）
  - ブローカーファクトリ、OrderManager、OrderRepository、RiskManager、Reconciler、ExecutionEngine（詳細ロジックは該当モジュール参照）
- ポートフォリオ（portfolio）
  - 銘柄選定（select_candidates）、等重/スコア重み（calc_equal_weights/calc_score_weights）
  - ポジションサイジング（calc_position_sizes）、セクターキャップ/レジーム乗数（apply_sector_cap / calc_regime_multiplier）
- 研究用（research）
  - ファクター計算（momentum, volatility, value）、将来リターン・IC 計算、統計サマリ
- AI（ai）
  - news_nlp.py：ニュース記事を集約して OpenAI に投げ、銘柄別センチメントを ai_scores に書込む
  - regime_detector.py：ETF とマクロ記事の LLM センチメントを合成して market_regime を判定
- ツール
  - tools/paper_verification_report.py：Paper Trading の検証レポートを生成
- ユーティリティ
  - utils/logging_setup.py：共通ログ設定
  - utils/process_priority.py：プロセス優先度 / CPU affinity 設定

セットアップ手順
----------------
前提
- Python 3.9+（コードは typing と新しい構文を使用）
- システムに DuckDB、psutil 等をインストールできること

仮想環境の作成（例）
- python -m venv .venv
- source .venv/bin/activate  # Windows: .venv\Scripts\activate

依存ライブラリのインストール（代表例）
- pip install duckdb psutil openai
- PyYAML があれば validate_config の YAML 検証が有効化されます（pip install PyYAML）
- 必要に応じて他の実行環境依存パッケージを追加してください。

環境変数 / .env
- プロジェクトルートに .env を置くと自動で読み込まれます（OS 環境変数が優先）。
- 自動読み込みを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。
- 主要な環境変数（例）:
  - JQUANTS_REFRESH_TOKEN （必須）
  - KABU_API_PASSWORD （必須）
  - KABUSYS_ENV: development | paper_trading | live（デフォルト development）
  - DUCKDB_PATH（デフォルト data/kabusys.duckdb）
  - SQLITE_PATH（デフォルト data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB, デフォルト data/paper_trading.db）
  - LOG_LEVEL（例: INFO）
  - OPENAI_API_KEY（AI 機能利用時に必要）
- .env の初期作成は対話式ウィザードを推奨:
  - python -m kabusys.config_setup
- 作成後は設定検証を実行:
  - python -m kabusys.validate_config
  - --strict を付けると警告もエラー扱い（exit 1）

DB 初期化
- run_execution / run_monitoring の起動時に必要なテーブルは自動的に作成されます（monitoring_db.init_monitoring_db が冪等で実行されます）。

使い方（主要コマンド）
---------------------
1) ExecutionEngine の起動（通常はサービス化して起動）
- python -m kabusys.run_execution
  - 実行前に .env で KABUSYS_ENV を設定してください。
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient が使われ、data/paper_trading.db に結果を書きます。
  - 起動時に data/stop_requested.flag が存在すると起動せず終了します。
  - 実行中に data/stop_requested.flag を作成するとエンジンを停止します。

2) Monitoring の起動（監視ループ）
- python -m kabusys.run_monitoring
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL（秒）で上書き可能。デフォルト 60 秒。
  - 監視は常に本番の sqlite_path（SQLITE_PATH）を使用する仕様です（環境に依存しない）。
  - 停止はプロジェクトルート/data/stop_requested.flag を作るか Ctrl+C。

3) .env の作成・更新
- python -m kabusys.config_setup

4) 起動前検証
- python -m kabusys.validate_config
  - --strict を付けると警告も FAIL 扱いします。

5) Paper Trading 検証レポート生成
- python -m kabusys.tools.paper_verification_report
- オプション:
  - --from YYYY-MM-DD --to YYYY-MM-DD --db PATH
  - 環境変数 PAPER_TRADING_SQLITE_PATH で DB を指定可能（優先度: --db > env > default）

AI 機能（ニュース NLP / レジーム判定）
- OpenAI API を利用する機能は環境変数 OPENAI_API_KEY を設定して利用します。
- ニューススコアリング: kabusys.ai.news_nlp.score_news を呼ぶか、実装を参照してバッチ処理を行ってください。
- 注意: API 遅延・エラーはリトライとフォールバック（0やスキップ）で安全側に設計されています。

プロセス制御 / Kill Switch
- kill_switch は監視ロジックに基づき data/kill.flag を書き込むことで ExecutionEngine に停止シグナルを送信します。
- ExecutionEngine は起動時に kill_flag_clear_on_start の設定（.env）に基づき kill.flag を自動でクリアするオプションを持ちます（本番では 0 推奨）。
- stop_requested.flag（data/stop_requested.flag）は run_* スクリプトを外部から停止するために使います。

ログ
- logs/<app_name>.log に日次ローテーションでログを保持（logs ディレクトリを作成できない場合はコンソール出力のみ）。
- ログレベルは LOG_LEVEL または setup_logging の引数で制御。

ディレクトリ構成
----------------
以下は主要なファイル／ディレクトリの抜粋（src/kabusys 配下）です。実際のリポジトリルートには pyproject.toml/.git 等がある想定です。

- src/kabusys/
  - __init__.py
  - config.py                -- 環境変数/.env の読み込みと Settings
  - config_setup.py          -- .env 対話式ウィザード
  - validate_config.py       -- 起動前設定検証 CLI
  - run_execution.py         -- ExecutionEngine 起動スクリプト
  - run_monitoring.py        -- SystemMonitor ポーリング起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py
  - execution/               -- Execution 系コンポーネント（BrokerFactory 等）
    - (OrderManager, ExecutionEngine, Reconciler, RiskManager, ...)
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py
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
    - news_nlp.py
    - regime_detector.py
    - __init__.py
  - utils/
    - logging_setup.py
    - process_priority.py
    - __init__.py
  - data/                    -- 実行時生成想定（DB ファイル、PID、flag など）
    - execution.pid
    - stop_requested.flag
    - kill.flag
    - monitoring.db / paper_trading.db / kabusys.duckdb など（デフォルトパス）

補足 / 実運用上の注意
--------------------
- KABUSYS_ENV は development / paper_trading / live のいずれかを使用。live は本番用のため設定値（LINE通知等）を特に慎重に確認してください。
- Paper Trading は本番 DB と完全分離するため検証に便利です（PAPER_TRADING_SQLITE_PATH を利用）。
- OpenAI API を利用する部分は API 料金やレート制限に注意してください。429/5xx は指数バックオフでリトライしますが、運用時はコスト管理を行ってください。
- ローカルでの開発は KABUSYS_ENV=development を推奨。発注処理は行われないよう実装が分離されていますが、live に切り替える際は十分に検証してください。
- ログディレクトリや data ディレクトリは適切なアクセス権で作成しておくこと。

ライセンス / 貢献
-----------------
- 本 README はコードコメントに基づき自動的に作成されたドキュメントです。実際の LICENSE ファイル/貢献フローはリポジトリルートの方針に従ってください。

連絡先 / 参照
--------------
- 実装の詳細は各モジュールファイル内の docstring を参照してください（src/kabusys/*）。
- 設定の初期作成: python -m kabusys.config_setup
- 設定チェック: python -m kabusys.validate_config
- 起動（監視/実行）: python -m kabusys.run_monitoring / python -m kabusys.run_execution

以上。必要なら README にサンプル .env、systemd ユニットファイル例、Dockerfile や requirements.txt のテンプレートの追加を行います。どの形式を追加したいか教えてください。