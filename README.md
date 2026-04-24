README
=====

概要
----
KabuSys は日本株向けの自動売買 / リサーチ基盤のプロジェクトです。本リポジトリは次の役割を持つモジュール群を含みます。

- 実行エンジン（ExecutionEngine）起動スクリプトとペーパートレード分離
- 監視（Monitoring）コンポーネント（システム状態、注文・リスク監視、Kill Switch）
- ポートフォリオ構築・ポジションサイジングの純粋関数群
- DuckDB を用いたリサーチ（ファクター計算、特徴量探索）
- ニュース NLP / レジーム判定（OpenAI を利用するモジュール）
- 設定ウィザード / 設定検証ツール / 各種ユーティリティ

主な設計方針は「環境依存を最小化」「検証可能な純粋関数」「本番とペーパートレードの明確な分離」「ログ・監視を統一して安定運用を支援する」ことです。

主な機能
--------
- 実行エンジン起動（run_execution.py）
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用して data/paper_trading.db に記録（本番 DB と分離）。
  - プロセス優先度設定、PID ファイル管理、停止フラグ監視を備える。
- 監視ループ起動（run_monitoring.py）
  - システムリソース・プロセス存在チェック、注文/リスクのチェック、Kill Switch 判定、アラート送信。
  - MONITOR_POLL_INTERVAL でポーリング間隔を指定可能（デフォルト 60 秒）。
- 監視 DB（monitoring_db.py）
  - system_status、trade_logs、positions、risk_logs、dashboard テーブルを持つ SQLite 永続化層。必要なマイグレーション処理を含む。
- リスク監視（risk_monitor.py） / トレード監視（trade_monitor.py） / システム監視（system_monitor.py）
  - ドローダウンやポジション上限、滞留注文、異常約定などの検出とログ化・アラート発行。
- Kill Switch（kill_switch.py）
  - data/kill.flag を書き込むことで ExecutionEngine に停止シグナルを送る仕組み。
- ポートフォリオ構築（portfolio/）
  - 候補選定、等配分・スコア配分、ポジションサイズ計算、セクター制限、レジーム乗数など。
- リサーチ（research/）
  - DuckDB 接続を利用したモメンタム / ボラティリティ / バリュー計算、将来リターン・IC 計算、統計サマリー。
- AI モジュール（ai/）
  - ニュースを OpenAI に投げて銘柄ごとのセンチメントを算出して ai_scores テーブルへ書き込む（news_nlp）。
  - マクロニュースと ETF MA200 を組み合わせて市場レジームを判定し market_regime テーブルへ格納する（regime_detector）。
- 設定ユーティリティ
  - 対話式 .env 作成ウィザード（config_setup.py）
  - 起動前の設定検証 CLI（validate_config.py）
- ツール
  - Paper Trading の検証レポート生成スクリプト（tools/paper_verification_report.py）

セットアップ手順
----------------

前提
- Python 3.9+（typing の式などに依存）
- 必要パッケージの一部（例）
  - duckdb
  - psutil
  - openai（AI 機能を使う場合）
  - PyYAML（config ファイル検証を行う場合、任意）
- Git リポジトリルートに置いて実行すること（Settings はプロジェクトルートを自動検出します）

1) 仮想環境の作成（推奨）
  python -m venv .venv
  source .venv/bin/activate  # Unix
  .venv\Scripts\activate     # Windows

2) パッケージのインストール（例）
  pip install duckdb psutil openai

  （PyYAML を使う場合）
  pip install pyyaml

3) .env の作成
- 対話式ウィザードで生成:
  python -m kabusys.config_setup

- 生成後、設定内容を検証:
  python -m kabusys.validate_config
  # --strict を付けると警告もエラー扱い

4) データディレクトリの配置
- デフォルトでは以下のファイルを使用します（変更可）:
  - data/monitoring.db (Settings.sqlite_path)
  - data/paper_trading.db (PAPER_TRADING_SQLITE_PATH, paper_trading 環境用)
  - data/kabusys.duckdb (Settings.duckdb_path)
  - data/execution.pid (PID ファイル)
  - data/kill.flag (Kill Switch 用)
  - data/stop_requested.flag (手動停止フラグ)
- 必要なら data/ と logs/ ディレクトリを作成してください。ログディレクトリは自動作成される場合がありますが、権限等で失敗するとコンソールのみ出力されます。

主な環境変数（代表）
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV (development | paper_trading | live) — デフォルト development
  - paper_trading: MockBroker + 別 SQLite（PAPER_TRADING_SQLITE_PATH）を使用
  - live: 本番モード（注意喚起あり）
- DUCKDB_PATH（デフォルト data/kabusys.duckdb）
- SQLITE_PATH（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）
- LOG_LEVEL（デフォルト INFO）
- OPENAI_API_KEY（AI 機能を使う場合必須）
- MONITOR_POLL_INTERVAL（監視ループ間隔 秒、run_monitoring で参照。デフォルト 60）
- KILL_FLAG_CLEAR_ON_START（起動時に kill.flag を自動クリアするか、0/1。production では 0 推奨）

使い方
------

起動スクリプト
- 監視ループ（Monitoring）
  python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒で上書き可能（デフォルト 60 秒）。
  - 監視は本番の sqlite_path を常に使用します（監視は環境に依存せず本番 DB を参照）。

- 実行エンジン（ExecutionEngine）
  python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し data/paper_trading.db に記録します。
  - 起動時に data/stop_requested.flag があればエンジンは起動せず終了します。
  - 実行はスレッドで実働し、stop_requested.flag を検知すると停止します。

設定・検証
- .env を作る（ウィザード）
  python -m kabusys.config_setup

- 設定検証
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict

ツール
- Paper Trading 検証レポート
  python -m kabusys.tools.paper_verification_report
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  --db オプションで DB パスを指定可能（環境変数 PAPER_TRADING_SQLITE_PATH より優先）

AI 関連
- ニュース NLP によるスコア算出（プログラムから呼ぶ）
  from kabusys.ai.news_nlp import score_news
  score_news(conn, target_date, api_key="...")

- レジーム判定
  from kabusys.ai.regime_detector import score_regime
  score_regime(conn, target_date, api_key="...")

注意点
- Settings は起動時に .env（および .env.local）を自動ロードします。自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト用途）。
- 本番運用時は KABUSYS_ENV=live とし、LINE 通知設定や Kill Switch の扱いを慎重に行ってください（validate_config は live 時のガードをチェックします）。
- OpenAI API を使う機能は API キーを必要とし、レート制限やエラーに対するリトライ処理を組み込んでいますが、API 呼び出し失敗時はフェイルセーフ（スコア 0.0 など）で継続する実装です。

ディレクトリ構成
----------------

src/kabusys/
- __init__.py
- __version__: 0.1.0

起動 / 設定関連
- run_execution.py         — ExecutionEngine 起動スクリプト
- run_monitoring.py       — SystemMonitor ポーリング起動スクリプト
- config.py               — Settings / .env 自動読み込みロジック
- config_setup.py         — 対話式 .env ウィザード
- validate_config.py      — 設定検証 CLI

ユーティリティ
- utils/
  - logging_setup.py      — 共通ログ設定（console + 日次ローテートファイル）
  - process_priority.py   — プロセス優先度 / CPU affinity 設定ユーティリティ

監視関連
- monitoring/
  - monitoring_db.py      — SQLite テーブル作成・読み書きラッパー
  - system_monitor.py     — システムリソース・データ鮮度・プロセス監視
  - trade_monitor.py      — （注文監視、ファイルに含まれます）
  - risk_monitor.py       — ドローダウン・ポジション上限監視
  - kill_switch.py        — kill.flag の管理
  - monitoring_engine.py  — 監視コンポーネント束ねループ
  - alert_manager.py      — （アラート送信用、実装により LINE 等へ送信）

実行・注文関連
- execution/
  - execution_engine.py
  - order_manager.py
  - order_repository.py
  - reconciler.py
  - risk_manager.py
  - broker_factory.py
  （注: 実際のブローカー実装は環境により差し替え）

ポートフォリオ構築
- portfolio/
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py

リサーチ
- research/
  - factor_research.py
  - feature_exploration.py
  - __init__.py

AI
- ai/
  - news_nlp.py
  - regime_detector.py
  - __init__.py

ツール
- tools/
  - paper_verification_report.py

データ / 設定
- config/                  — 各種 YAML テンプレート（system_config.yaml 等、generate スクリプトで生成）
- data/                    — DB / PID / flag 等（実行時に生成・参照）
- logs/                    — ログファイル（logs/<app_name>.log、日次ローテーション）

追加情報 / 運用メモ
- ロギング: setup_logging(app_name) を各起動スクリプトで呼び出すことで統一されたログ出力（stdout + 日次ファイルローテーション）になります。
- 停止フラグ: 停止を要求するには data/stop_requested.flag を作成します（run_execution/run_monitoring が検知して終了します）。Kill Switch は data/kill.flag を使って ExecutionEngine の強制停止を行います。
- DB マイグレーション: monitoring_db.init_monitoring_db は冪等でテーブル作成と簡易マイグレーション（カラム追加）を行います。

ライセンスや貢献ガイドライン等がある場合はプロジェクトルートに追記してください。

以上。運用や機能の詳細（ExecutionEngine の内部設計、ブローカ実装、AlertManager の具体的接続先など）は各モジュールのドキュメント / コメントを参照してください。必要であれば README に追記します。