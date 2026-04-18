KabuSys — 日本株自動売買システム
================================

このリポジトリは、日本株向けの自動売買システム（KabuSys）のコアライブラリ群です。
ここに含まれるモジュールは、データ処理（DuckDB）、ポートフォリオ構築、発注エンジン、
監視・アラート、AI（ニュースセンチメント・レジーム判定）などの機能を提供します。

主な特徴
--------
- 戦略（ファクター計算、特徴量解析）とポートフォリオ構築用の純粋関数群
  - momentum / value / volatility 等のファクター計算（duckdb ベース）
  - 候補選定・重み付け・ポジションサイズ計算（等分配／スコア加重／リスクベース）
- 発注・実行エンジン（ExecutionEngine）と Broker クライアント抽象
  - 本番（kabuステーション）とペーパートレード（MockBrokerClient）を切替可能
  - paper_trading モードは専用の SQLite（data/paper_trading.db）を使用して本番 DB と分離
- 監視フレームワーク
  - SystemMonitor / TradeMonitor / RiskMonitor を束ねる MonitoringEngine
  - kill.flag による安全な緊急停止（Kill Switch）
  - 監視ログ保存用の SQLite（data/monitoring.db）
- AI 補助機能
  - ニュースの LLM（OpenAI）によるセンチメントスコアリング（ai_scores）
  - マクロ + 指数の MA を使った市場レジーム判定（regime_detector）
- 運用ユーティリティ
  - .env 対話式ウィザード（config_setup）
  - 起動前チェック（validate_config）
  - Paper Trading 検証レポート生成ツール（tools/paper_verification_report）
- ログ管理
  - 共通の setup_logging() による stdout + 日次ローテートログ出力（logs/*.log）

必要な環境 / 依存ライブラリ
----------------------------
- Python 3.10 以上（型注釈に | を使用）
- 必要なパッケージ（参考）
  - duckdb
  - psutil
  - openai
  - （任意）PyYAML（config/*.yaml の構文検証用）
- SQLite（標準ライブラリで利用）
- 環境に応じて kabuステーション API など外部サービスの準備

例:
pip install duckdb psutil openai PyYAML

主要環境変数
-------------
（.env を用意して管理することを推奨）

必須（実行前に設定）
- JQUANTS_REFRESH_TOKEN — J-Quants API 用トークン
- KABU_API_PASSWORD — kabuステーション API パスワード

運用・挙動指定
- KABUSYS_ENV: execution モード
  - development / paper_trading / live
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: ペーパートレードの約定挙動（instant / partial / never / reject）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）
- OPENAI_API_KEY: OpenAI 呼び出し用（AI 機能を使う場合）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE 通知設定（任意）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（0/1）
- MONITOR_POLL_INTERVAL: monitoring のポーリング間隔（秒、デフォルト 60）

運用上のファイル
- data/kill.flag — KillSwitch が書き込む停止フラグ（ExecutionEngine 停止トリガ）
- data/stop_requested.flag — run_monitoring/run_execution の外部停止フラグ（存在でループ終了）
- data/execution.pid — 実行エンジンの PID（起動時に書き込まれる）
- logs/ — ログ出力ディレクトリ（デフォルト）

セットアップ手順（ローカル）
-------------------------
1. リポジトリを取得し、仮想環境を作成・有効化
   python -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate

2. 依存パッケージをインストール
   pip install duckdb psutil openai PyYAML

3. .env の作成（対話式ウィザード推奨）
   python -m kabusys.config_setup
   - ウィザードで入力した値はプロジェクトルートの .env に保存されます。
   - その後、設定を検証:
     python -m kabusys.validate_config
     # 警告も含めて厳密にチェックする:
     python -m kabusys.validate_config --strict

4. データディレクトリの作成（自動で作成されることが多いですが念のため）
   mkdir -p data logs

起動/使い方
-----------

- ExecutionEngine を起動（本番 / ペーパー共通）
  - モジュールとして実行:
    python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading のときは MockBrokerClient を使い、DB は data/paper_trading.db に記録され本番 DB と分離されます。
  - 起動時に data/stop_requested.flag が存在すると起動せず終了します。
  - 停止は kill.flag（KillSwitch が書く）または data/stop_requested.flag を作ることで行います。

- Monitoring を起動（定期ポーリング）
  python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き（デフォルト 60 秒）。
  - 監視は常に本番の sqlite_path（SQLITE_PATH）を使います（監視 DB は環境に依存しない）。

- 設定検証
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict

- Paper Trading 検証レポート（ツール）
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - デフォルト DB: 環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db

- AI 機能（ニューススコアリング / レジーム判定）
  - 必要: OPENAI_API_KEY を設定
  - ニューススコアリング:
    from kabusys.ai.news_nlp import score_news
    score_news(conn, target_date, api_key="...")  # DuckDB 接続と日付を渡す
  - レジーム判定:
    from kabusys.ai.regime_detector import score_regime
    score_regime(conn, target_date, api_key="...")

運用上の注意
-------------
- paper_trading モードは本番 DB と完全分離することを目的としています。環境切り替えに注意してください（KABUSYS_ENV）。
- kill.flag は冪等に書かれるため、存在確認の上で再書き込みは行われません。実行時の自動クリア設定（KILL_FLAG_CLEAR_ON_START）は本番運用では 0 を推奨します。
- ログは stdout と logs/<app_name>.log（日次ローテート）に出力されます。ログディレクトリが作成できない場合はファイル出力が無効化され、コンソールのみになります。
- OpenAI API 呼び出しはレート制限やネットワークエラーに対してリトライ実装がありますが、APIキーやコストに注意してください。
- データのルックアヘッドバイアス対策として、AI/ファクター計算は target_date の取り扱いに注意しています（コード内の注記を参照）。

ディレクトリ構成（主要ファイル）
-------------------------------
src/kabusys/
- __init__.py
- config.py                — 環境変数/.env ロード・Settings
- config_setup.py          — .env 対話式ウィザード
- validate_config.py       — 起動前設定チェック CLI
- run_execution.py         — ExecutionEngine 起動スクリプト
- run_monitoring.py        — Monitoring 起動スクリプト
- tools/
  - paper_verification_report.py — Paper Trading 検証レポート生成
- utils/
  - logging_setup.py       — 共通ログ設定
  - process_priority.py    — プロセス優先度 / CPU affinity ユーティリティ
- monitoring/
  - monitoring_db.py       — 監視 DB（SQLite）永続化レイヤ
  - monitoring_engine.py   — 各 Monitor を束ねるエンジン
  - system_monitor.py      — システム状態・データ鮮度監視
  - risk_monitor.py        — ドローダウン・ポジション上限監視
  - trade_monitor.py       — （存在する場合の）約定・滞留監視
  - kill_switch.py         — kill.flag の生成 / 評価
  - alert_manager.py       — （存在する場合）通知管理
- execution/
  - execution_engine.py    — 実行エンジン本体（EngineConfig 等）
  - broker_factory.py      — BrokerClient 作成ファクトリ
  - order_manager.py
  - order_repository.py
  - reconciler.py
  - risk_manager.py
- portfolio/
  - portfolio_builder.py   — 候補選定・重み計算
  - position_sizing.py     — 株数決定・リスク制限
  - risk_adjustment.py     — セクターキャップ・レジーム乗数
- research/
  - factor_research.py     — factor 計算（momentum/value/volatility）
  - feature_exploration.py — forward returns / IC / summary
- data/ (スクリプトから使用される想定パス)
  - monitoring.db (default SQLITE_PATH)
  - paper_trading.db (paper trading 用)
- logs/ (ログ出力先)

ドキュメント / 追加参照
----------------------
- 各モジュール内には実装方針や注意点が docstring とコメントで記載されています。特に
  - portfolio/*.py（PortfolioConstruction.md に基づく）
  - research/*.py（StrategyModel.md 等に対応）
  - ai/*.py（OpenAI API の使用・リトライ・レスポンス検証）
  を参照してください。

問い合わせ / 貢献
-----------------
問題報告（バグ／改善提案）は Issue を通してください。プルリクエスト歓迎です。
コードの設計思想（運用・フェイルセーフの扱い、ルックアヘッドバイアス対策等）は
コメントに詳細があるため、変更時は既存の設計方針に従うようお願いします。

以上。README の補足や特定機能（例: ExecutionEngine の引数や OrderRepository の仕様）の詳細を追加希望であれば教えてください。