KabuSys — 日本株自動売買システム
=================================

このリポジトリは日本株向けの自動売買・リサーチ・監視ツール群をまとめた軽量フレームワークです。  
主要コンポーネントは注文実行エンジン（ExecutionEngine）、監視（Monitoring）、リサーチ／ファクター計算、AI を使ったニュース判定などで構成されています。

以下はこのコードベースに対する README（日本語）です。

プロジェクト概要
----------------
KabuSys は以下のような目的で設計されたモジュール群です。

- 注文実行エンジン（実際のブローカー／モックを切替可能）
- 監視サブシステム（システム稼働、注文ログ、リスク監視、Kill Switch）
- ポートフォリオ構築（候補選定、重み付け、ポジションサイズ計算、セクター制限）
- リサーチ（ファクター計算、将来リターン、IC 計算）
- AI モジュール（ニュース NLP による銘柄センチメント、レジーム判定）
- ユーティリティ（設定管理、ログ設定、プロセス優先度設定、診断ツール）

設計方針のポイント
- 環境依存設定は .env（環境変数）で管理。config_setup によるウィザードで初期化可能。
- 本番・ペーパートレード DB は分離（KABUSYS_ENV により切替）。
- DuckDB をリサーチ用途の分析 DB、SQLite を監視／注文ログに使用。
- OpenAI（gpt-4o-mini）を使った NLP 機能を内蔵（任意、API キー必要）。
- ログはコンソール＋日次ローテートで logs/ 配下に出力。

主な機能一覧
----------------
- 実行（run_execution.py）
  - ExecutionEngine を起動して発注処理を実行。
  - KABUSYS_ENV=paper_trading のときは MockBrokerClient を使い、data/paper_trading.db に記録。
  - stop flag（data/stop_requested.flag）で安全に停止可能。

- 監視（run_monitoring.py / monitoring モジュール）
  - SystemMonitor: CPU/メモリ/ディスク・データ鮮度・Execution プロセスの検知。
  - TradeMonitor: 注文の滞留／約定異常など検出（trade_logs 参照）。
  - RiskMonitor: ドローダウン・ポジション上限の監視、ダッシュボード更新、risk_logs 記録。
  - KillSwitch: 条件により data/kill.flag を生成して ExecutionEngine を停止させる。
  - MonitoringEngine: これらを定期ポーリングしてアラート／KillSwitch 評価。

- ポートフォリオ（portfolio パッケージ）
  - 銘柄選定（select_candidates）
  - 重み計算（等配分 / スコア配分）
  - セクターキャップ適用（apply_sector_cap）
  - ポジションサイズ計算（calc_position_sizes）

- リサーチ（research パッケージ）
  - ファクター計算（momentum / volatility / value）
  - 将来リターン・IC（Information Coefficient）等の統計解析ユーティリティ

- AI（ai パッケージ）
  - news_nlp.score_news: ニュース記事をまとめて LLM に投げ、銘柄別センチメントを ai_scores テーブルへ書き込む。
  - regime_detector.score_regime: MA 乖離とマクロニュースを組み合わせて市場レジーム（bull/neutral/bear）を判定し table に保存。

- ユーティリティ
  - 設定ウィザード（config_setup.py）
  - 設定検証 CLI（validate_config.py）
  - paper_trading 検証レポート（tools/paper_verification_report.py）
  - ロギング設定（utils/logging_setup.py）
  - プロセス優先度設定（utils/process_priority.py）

セットアップ手順
----------------
前提:
- Python 3.9+（コード中型注釈を使っているため 3.9 以上を想定）
- システムに応じて以下パッケージをインストールしてください（最低限）:
  - duckdb
  - psutil
  - openai (AI 機能を使う場合)
  - (任意) PyYAML：validate_config が config/*.yaml のパース検証を行う場合に便利

推奨手順（例）:
1. リポジトリをクローン
   - git clone <repo-url>

2. 仮想環境作成（例）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows では .venv\Scripts\activate)

3. 必要ライブラリをインストール
   - pip install duckdb psutil openai
   - 追加で validate_config の YAML 検証を使うなら pip install PyYAML

4. 環境変数設定（.env）
   - python -m kabusys.config_setup を実行して .env を作成するのが簡単です。
   - または .env を手動作成。主要なキー（デフォルトや必須）:
     - JQUANTS_REFRESH_TOKEN (必須)
     - KABU_API_PASSWORD (必須)
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
     - DUCKDB_PATH (例: data/kabusys.duckdb)
     - SQLITE_PATH (例: data/monitoring.db)
     - PAPER_TRADING_SQLITE_PATH (ペーパートレード用 DB, デフォルト: data/paper_trading.db)
     - LOG_LEVEL (DEBUG/INFO/...)
     - OPENAI_API_KEY (AI 機能使用時)
     - PAPER_FILL_MODE (instant | partial | never | reject) — ペーパートレード時の約定挙動

5. 設定検証
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いになります

6. ディレクトリと初期ファイル
   - run 実行前に data/ と logs/ は自動生成されますが、パーミッション等確認してください。

使い方（起動コマンド・よく使うスクリプト）
----------------
- ExecutionEngine を起動（本番 / ペーパー共通）
  - python -m kabusys.run_execution
  - ペーパートレードを使うには KABUSYS_ENV=paper_trading を .env に設定するか、環境変数で指定します。
  - 起動時に data/stop_requested.flag があると起動しません（安全措置）。
  - エンジンは data/execution.pid を作成します。停止は stop flag (data/stop_requested.flag) または data/kill.flag によって行います。

- Monitoring を起動（ポーリング）
  - python -m kabusys.run_monitoring
  - ポーリング間隔を変更するには環境変数 MONITOR_POLL_INTERVAL（秒）を設定。デフォルト 60 秒。
  - 監視は monitoring DB に常に production 用の sqlite_path を使用します（環境に依らず監視 DB のパスを参照します）。

- 設定ウィザード（対話式）
  - python -m kabusys.config_setup

- 設定検証 CLI
  - python -m kabusys.validate_config [--strict]

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - デフォルト DB は PAPER_TRADING_SQLITE_PATH 環境変数または data/paper_trading.db

- AI 機能（プログラムから呼ぶ）
  - from kabusys.ai import score_news
  - score_news(conn, target_date, api_key=None)

ログとファイル
----------------
- ログ:
  - デフォルトは logs/ ディレクトリにアプリ名単位（execution.log, monitoring.log 等）で日次ローテートされて保存されます。
  - ログ設定は kabusys.utils.logging_setup.setup_logging で各起動スクリプトが初期化します。

- データファイル（デフォルトパス）
  - DuckDB: data/kabusys.duckdb (設定で変更可)
  - 監視用 SQLite: data/monitoring.db
  - ペーパートレード SQLite: data/paper_trading.db
  - プロセス PID: data/execution.pid
  - 停止フラグ: data/stop_requested.flag
  - Kill スイッチ（Execution 停止指示）: data/kill.flag

注意点・安全策
----------------
- KABUSYS_ENV=live の場合は本番口座へ発注されます。LINE 通知設定や kill flag の挙動などを事前に十分確認してください。
- .env は絶対にリポジトリへコミットしないでください。
- OpenAI API キーを設定する場合は秘匿して管理してください。
- process_priority 設定はシステム権限に依存します。権限不足時は警告が出て継続します。

主な環境変数（抜粋）
----------------
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV = development | paper_trading | live (default: development)
- DUCKDB_PATH (default: data/kabusys.duckdb)
- SQLITE_PATH (default: data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH (default: data/paper_trading.db)
- LOG_LEVEL (default: INFO)
- LOG_DIR (default: logs/)
- OPENAI_API_KEY (AI 機能使用時)
- MONITOR_POLL_INTERVAL (run_monitoring のポーリング秒数、default: 60)
- PAPER_FILL_MODE (paper trading の約定モード: instant|partial|never|reject)

ディレクトリ構成
----------------
以下は主要ファイル／ディレクトリの概観（src/kabusys 配下）:

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数 / .env 自動ロード、Settings クラス
  - config_setup.py           — .env 対話式ウィザード
  - validate_config.py        — 起動前検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — SystemMonitor ポーリング起動スクリプト
  - execution/                — 発注エンジン関連（broker, engine, order_manager 等）
  - monitoring/
    - monitoring_db.py        — SQLite 永続化層
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
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py
    - regime_detector.py
  - tools/
    - paper_verification_report.py
  - utils/
    - logging_setup.py
    - process_priority.py

（上記はコードベースの一部を抜粋しています。詳細は各モジュールの docstring を参照してください）

開発・拡張のヒント
----------------
- DuckDB 接続を渡してデータ処理を行う方式のため、テーブル（prices_daily, raw_financials, raw_news など）を事前に準備すればローカルでリサーチ機能を実行できます。
- AI 関連は OpenAI SDK の API 仕様変更に注意してください。テスト時は _call_openai_api をモック化して API 呼び出しを差し替える設計にしています。
- ログや SQLite のマイグレーションは init_monitoring_db に冪等スクリプトとして実装されています。スキーマ変更はそこに追記してください。

サンプルワークフロー
----------------
1. .env を生成（python -m kabusys.config_setup）
2. 設定検証（python -m kabusys.validate_config）
3. （オプション）データを投入してリサーチを実行（research モジュール）
4. 監視を起動（python -m kabusys.run_monitoring）
5. 実行エンジンを起動（python -m kabusys.run_execution）
6. 必要に応じてデバッグ・ログや paper verification report を実行

ライセンス・連絡
----------------
- 本 README ではライセンス情報を省略しています。実際のリポジトリでは LICENSE ファイルを参照してください。
- 実運用前には十分なテストと監査を行ってください。特に KABUSYS_ENV=live の発注系は注意が必要です。

以上がこのコードベースの README（日本語）です。各モジュールの詳細な使い方や API はソースコード内の docstring を参照してください。必要であれば README にサンプル設定ファイル（.env.example）や起動システムd / cron の設定例も追記できます。希望があれば追加で作成します。