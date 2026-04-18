# KabuSys — README (日本語)

KabuSys は日本株向けの自動売買 / リサーチ基盤のコード群です。本リポジトリは以下の責務を持つコンポーネントを含みます：市場データ処理（DuckDB）、発注・リスク管理、監視・アラート、ポートフォリオ構築、研究用ファクター計算、AI を使ったニュース解析など。

以下はコードベースの概要、特徴、セットアップ方法、基本的な使い方、ディレクトリ構成の説明です。

---

目次
- プロジェクト概要
- 主な機能一覧
- セットアップ手順
- 使い方（よく使うコマンド）
- 環境変数（重要設定）
- 停止 / Kill スイッチ関連
- ディレクトリ構成（主要ファイルの説明）
- 補足・注意事項

---

プロジェクト概要
- 日本株自動売買システムの基盤ライブラリ群。
- 発注エンジン（ExecutionEngine）、監視（MonitoringEngine）、リスク管理、ポートフォリオ構築、ファクター計算、AI によるニュースセンチメント評価などを含む。
- データベースは DuckDB（分析用）と SQLite（監視・ペーパートレード用）を使用。
- 環境に応じて動作モードを切り替え可能（development / paper_trading / live）。

主な機能一覧
- 発注/実行制御
  - ExecutionEngine を起動して単日セッションの発注を実行（run_execution.py）。
  - paper_trading モードでは MockBrokerClient を使い、paper_trading 用 SQLite に記録して本番 DB と分離。
- 監視・アラート
  - SystemMonitor / TradeMonitor / RiskMonitor を統合した MonitoringEngine（run_monitoring.py で起動）。
  - システム稼働監視、注文滞留チェック、約定価格異常、ドローダウン監視、ポジション上限監視。
  - 必要に応じて kill.flag を出力して ExecutionEngine を停止可能（KillSwitch）。
- データベース
  - DuckDB: prices_daily / raw_financials / raw_news など分析用テーブル（パイプライン側で投入）。
  - SQLite: 監視ログ（monitoring.db）および paper_trading.db（ペーパートレード用）。
- ポートフォリオ構築
  - 候補選定、重み計算（等配分・スコア重み）、ポジションサイズ計算、セクターキャップ適用、レジーム乗数。
- 研究（Research）
  - ファクター計算（モメンタム / ボラティリティ / バリュー）、将来リターン・IC 計算、統計サマリー等（DuckDB 接続を受け取る関数群）。
- AI（OpenAI）
  - news_nlp: ニュース記事を集約し LLM（gpt-4o-mini など）でセンチメントを算出して ai_scores に書き込む。
  - regime_detector: ETF（例: 1321）MA とマクロニュースのセンチメントを合成して市場レジーム（bull/neutral/bear）を算出・永続化。
- ツール
  - 設定ウィザード（config_setup.py）で .env の初期作成・更新支援。
  - 設定検証 CLI（validate_config.py）で必須環境変数や config/*.yaml の存在・簡易パースをチェック。
  - paper_verification_report：ペーパートレード DB を解析して検証レポートを生成。

セットアップ手順（概略）
1. Python 環境を用意
   - Python 3.9+ を推奨（各環境での互換性は確認してください）。
   - 仮想環境作成例:
     - python -m venv .venv
     - source .venv/bin/activate（Windows: .venv\Scripts\activate）

2. 依存パッケージをインストール
   - 必要なパッケージ（主要例）:
     - duckdb
     - psutil
     - openai
     - PyYAML（config の YAML 検証用。任意）
   - 例:
     - pip install duckdb psutil openai pyyaml

   （本リポジトリに requirements.txt が無い場合はプロジェクトに合わせて追加してください）

3. .env を作成
   - python -m kabusys.config_setup を実行して対話的に .env を生成できます。
   - 生成後、python -m kabusys.validate_config で設定を検証してください。

4. データディレクトリの準備
   - デフォルトで期待されるファイル・ディレクトリ:
     - data/kabusys.duckdb （DUCKDB_PATH のデフォルト）
     - data/monitoring.db （SQLITE_PATH のデフォルト）
     - data/paper_trading.db （PAPER_TRADING_SQLITE_PATH のデフォルト）
     - data/execution.pid, data/kill.flag などは実行時に生成・参照されます。
   - 必要に応じてディレクトリを作成してください（多くの箇所で parent.mkdir(parents=True, exist_ok=True) が使用されています）。

使い方（よく使うコマンド例）
- 設定ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 警告をエラー扱いにする: python -m kabusys.validate_config --strict

- 実行エンジン起動（ExecutionEngine）
  - python -m kabusys.run_execution
  - 注意: KABUSYS_ENV により本番 / ペーパーの挙動が変わります。
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し data/paper_trading.db に記録します（本番 DB と分離）。
  - 実行中は data/execution.pid に PID を書きます。停止させるには kill.flag（KillSwitch）を使うかプロセスを終了します。

- 監視ループ起動（MonitoringEngine）
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL（秒）でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 例: MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - 監視は本番 sqlite_path を使用（KABUSYS_ENV に依らず monitoring 用 DB を参照します）。

- ペーパートレード検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db PATH または環境変数 PAPER_TRADING_SQLITE_PATH

- AI 関連（プログラムから呼び出す）
  - kabusys.ai.news_nlp.score_news(conn, target_date, api_key=None)
    - OpenAI API キーは api_key 引数または環境変数 OPENAI_API_KEY。
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)

主要な環境変数（抜粋）
- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
  - paper_trading: 発注はモック、専用の paper DB を使用
  - live: 本番（注意: 実際に発注が行われます）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（デフォルト: data/paper_trading.db）
- LOG_LEVEL（DEBUG/INFO/...、デフォルト INFO）
- OPENAI_API_KEY（AI モジュールが必要な場合）
- PAPER_FILL_MODE（paper_trading 時のフィルモード: instant / partial / never / reject、デフォルト "instant"）
- MONITOR_POLL_INTERVAL（監視ポーリング間隔（秒） — run_monitoring 用、デフォルト 60）
- PID_FILE_PATH（デフォルト data/execution.pid）
- KILL_FLAG_PATH（デフォルト data/kill.flag）
- KILL_FLAG_CLEAR_ON_START（起動時に kill.flag を自動でクリアするか。1=クリア、0=クリアしない）
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 をセットすると .env 自動ロードを無効化

停止 / Kill スイッチ関連
- run_execution.py / ExecutionEngine:
  - data/stop_requested.flag を監視しており存在するとエンジンは安全に停止します（run_execution での停止フラグ）。
  - ExecutionEngine は起動時に pid ファイル（例: data/execution.pid）を書きます。SystemMonitor はこの PID を見てプロセスの健全性をチェックします。
- KillSwitch:
  - リスク条件（ドローダウン超過、ポジション上限など）により data/kill.flag を書き込み、ExecutionEngine に停止指示を出します。
  - KillSwitch は idempotent（既に存在する場合は書き換えない）。
  - KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に kill.flag を自動クリアする設定になります（本番では注意して下さい）。

ディレクトリ構成（主要ファイルと説明）
- src/kabusys/
  - __init__.py
    - パッケージ定義、__version__ など。
  - config.py
    - 環境変数・.env の自動読み込み、Settings クラス（アプリ設定）を提供。
    - 自動ロード順: OS 環境 > .env.local > .env
  - config_setup.py
    - .env を対話的に作るウィザード。
  - validate_config.py
    - 起動前設定検証 CLI（必須環境変数や config/*.yaml の存在チェック）。
  - run_execution.py
    - ExecutionEngine 起動スクリプト。KABUSYS_ENV による挙動差分を管理。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト。MONITOR_POLL_INTERVAL を参照。
  - execution/
    - （発注エンジン関連; EngineConfig, ExecutionEngine, OrderManager, Reconciler, RiskManager, BrokerFactory 等を含む）
  - monitoring/
    - monitoring_db.py — SQLite への永続化層（system_status, trade_logs, positions, risk_logs, dashboard）。
    - system_monitor.py — CPU/メモリ/ディスク/プロセス健全性、データ鮮度チェック。
    - trade_monitor.py — 滞留注文・約定価格異常検知。
    - risk_monitor.py — ドローダウン・ポジション上限監視、dashboard 更新。
    - kill_switch.py — kill.flag の書き込み・管理。
    - monitoring_engine.py — 各モニタを束ねる実行ループ。
    - alert_manager.py — （アラート送信管理。LINE 等への通知を行う想定）
  - portfolio/
    - portfolio_builder.py — 候補選定・重み計算。
    - position_sizing.py — 株数決定・資金配分・ラウンド処理。
    - risk_adjustment.py — セクターキャップ・レジーム乗数。
  - research/
    - factor_research.py — Momentum/Volatility/Value 等のファクター計算（DuckDB 使用）。
    - feature_exploration.py — 将来リターン計算、IC、統計サマリー等。
  - ai/
    - news_nlp.py — ニュース集約 → LLM 呼び出し → ai_scores 書込み。
    - regime_detector.py — ETF MA とマクロニュース LLM を合成して market_regime を算出。
  - tools/
    - paper_verification_report.py — ペーパートレード DB の検証レポート生成。
  - utils/
    - process_priority.py — psutil を用いたプロセス優先度 / CPU affinity ユーティリティ。

補足・注意事項
- データベーススキーマ（monitoring_db.py）は冪等に DB を初期化・マイグレーションします。既存 DB にカラムがなければ ALTER TABLE を行うことがあります。
- DuckDB 接続は分析用途に使う想定で、AI / research モジュールは DuckDB 接続を受け取って SQL を実行します。これらは本番の発注ロジックとは分離されています。
- AI（OpenAI）を利用する機能は API キーが必要です。API 呼び出しはリトライ・フォールバックロジックを持ちますが、API 使用に伴うコストやレート制限に注意してください。
- KABUSYS_ENV=live では設定ミスが重大な影響を与えるため validate_config の確認、LINE 通知などの設定を必ずチェックしてください。
- .env ファイルは機密情報（API トークン等）を含むため、決して Git にコミットしないでください（config_setup.py のヘッダにも注意喚起を記載）。

---

README は以上です。実際の運用にあたっては、環境固有の設定や broker クライアントの実装、データパイプライン（prices_daily / raw_financials / raw_news の投入）等も必要になります。必要であれば、各モジュール（ExecutionEngine、MonitoringEngine、AI モジュール、ポートフォリオ計算関数など）の使い方や実行例をさらに詳細に書いたドキュメントを作成します。どの部分を深掘りしますか？