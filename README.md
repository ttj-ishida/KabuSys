KabuSys — 日本株自動売買プラットフォーム（リポジトリ抜粋）
================================================================================

この README はリポジトリ内の主要スクリプト／モジュール群（config, execution, monitoring, research, portfolio, ai, tools 等）に基づき作成した利用ガイドです。開発・運用に必要な概要、セットアップ手順、使い方、ディレクトリ構成などを日本語でまとめています。

前提
-----
- Python 3.10 以上（型注釈に PEP 604 (X | Y) を使用）
- 推奨パッケージ（本リポジトリ内で import されている主な外部依存）:
  - duckdb
  - psutil
  - openai
  - PyYAML（config 検証で任意）
- SQLite（標準ライブラリ sqlite3 を利用）
- ネットワークアクセス（本番で OpenAI、kabuステーション 等を使う場合）

プロジェクト概要
---------------
KabuSys は日本株向けの自動売買システムのコアライブラリ／起動スクリプト群です。主な機能は以下のとおりです。

機能一覧
--------
- 環境設定管理 (.env の自動/対話式読み書き)
  - 自動ロード：プロジェクトルートの .env / .env.local（OS 環境変数を上書きしない挙動）
  - 対話式ウィザード：python -m kabusys.config_setup
- 設定検証 CLI（.env と config/*.yaml の存在・簡易妥当性チェック）
  - python -m kabusys.validate_config [--strict]
- 実行エンジン（ExecutionEngine）起動スクリプト
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading のときは MockBrokerClient を使い paper_trading DB に分離して記録
- 監視（Monitoring）起動スクリプト
  - python -m kabusys.run_monitoring
  - システム状態、データ鮮度、注文挙動、リスクに応じた監視・ログ記録・アラート送出
  - MONITOR_POLL_INTERVAL でポーリング間隔を指定可能（デフォルト 60s）
- リサーチ用関数群
  - ファクター計算（モメンタム、バリュー、ボラティリティ等）
  - 将来リターン計算、IC（Information Coefficient）算出、統計サマリー
- ポートフォリオ構築
  - 候補選定、重み付け（等金額・スコア加重）、ポジションサイズ計算、セクター制限、レジーム乗数
- AI（LLM）連携モジュール
  - ニュースのセンチメント評価（OpenAI を用いたスコアリング）: kabusys.ai.news_nlp
  - 市場レジーム判定（MA + マクロニュースの LLM 評価の合成）: kabusys.ai.regime_detector
  - OpenAI の呼び出しは堅牢化（リトライ、JSON バリデーション、スコアクリッピング等）
- 運用支援ツール
  - Paper Trading の検証レポート生成スクリプト: python -m kabusys.tools.paper_verification_report

セットアップ手順
----------------
1. リポジトリをクローン
   - git clone <repo-url>

2. 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - 直接 pip で主要パッケージを入れる例:
     - pip install duckdb psutil openai PyYAML
   - 実運用では requirements.txt を用意している場合はそちらを利用してください。

4. データディレクトリ作成（デフォルト）
   - mkdir -p data logs

5. .env の準備
   - 対話式ウィザード（推奨）:
     - python -m kabusys.config_setup
     - ウィザードで J-Quants / kabu API パスワード等を入力して .env を生成します。
   - 手動で設定する場合は .env に以下の環境変数を設定します（代表例）:

.env の例（抜粋）
------------------
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here
KABU_API_PASSWORD=your_kabu_api_password_here
KABU_API_BASE_URL=http://localhost:18080/kabusapi
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
LOG_LEVEL=INFO
KABUSYS_ENV=development
LINE_CHANNEL_ACCESS_TOKEN=
LINE_USER_ID=
KILL_FLAG_CLEAR_ON_START=0
OPENAI_API_KEY=your_openai_api_key_here

- 注意: .env は絶対にリポジトリにコミットしないでください（秘匿情報を含みます）。

6. 設定検証（任意）
   - python -m kabusys.validate_config
   - 本番に入れる前に --strict オプションで警告も FAIL 扱いにできます:
     - python -m kabusys.validate_config --strict

使い方（主要スクリプト）
-----------------------
- ExecutionEngine を起動（通常）
  - python -m kabusys.run_execution
  - KABUSYS_ENV により挙動が変わります:
    - paper_trading: MockBrokerClient を使用し data/paper_trading.db（または PAPER_TRADING_SQLITE_PATH）に書き込み
    - live: 実ブローカーへ接続（設定に応じて）
  - 実行中は data/execution.pid に PID を書き込み、停止は data/stop_requested.flag を作ることで指示できます。

- Monitoring を起動
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書きできます（例: export MONITOR_POLL_INTERVAL=30）
  - 監視は常に本番用 sqlite_path（Settings.sqlite_path）を使用して監視ログを残します。
  - 停止は data/stop_requested.flag を作成するか KeyboardInterrupt（Ctrl+C）で停止します。

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - デフォルト DB は data/paper_trading.db、別パスを使う場合は --db オプションで指定

- 環境設定ウィザード（.env を作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告も失敗扱いで exit code 1 を返します

運用上のフラグ/ファイル
-----------------------
- data/stop_requested.flag
  - run_execution や run_monitoring のループを外部から優雅に停止させるために監視されるフラグファイル
- data/kill.flag
  - KillSwitch（監視による自動停止）で書かれるフラグ
  - Settings.kill_flag_clear_on_start=1 のとき起動時に自動クリアされる（本番では 0 推奨）
- data/execution.pid
  - 実行エンジンが PID を書き込むファイル

主な設定項目（Settings）
-----------------------
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL (デフォルト http://localhost:18080/kabusapi)
- DUCKDB_PATH (デフォルト data/kabusys.duckdb)
- SQLITE_PATH (デフォルト data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH (paper_trading 用 DB、デフォルト data/paper_trading.db)
- KABUSYS_ENV (development|paper_trading|live) — default: development
- LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL)
- OPENAI_API_KEY (AI 機能を使う場合に必要)
- MONITOR_POLL_INTERVAL（環境変数で run_monitoring のポーリング間隔を上書き）

主要モジュール説明（簡易）
-------------------------
- kabusys.config
  - 環境変数の自動ロード/取得/検証を提供する Settings クラス
  - .env/.env.local をプロジェクトルートから自動読み込み（必要なら無効化可）
- kabusys.utils.logging_setup
  - 標準出力と日次ローテートログを統合して設定するユーティリティ
- kabusys.utils.process_priority
  - プラットフォーム差分を吸収したプロセス優先度設定（psutil を使用）
- kabusys.execution.*
  - 発注・注文管理・リスク管理・実行エンジン（run_execution の中核）
- kabusys.monitoring.*
  - system_monitor, trade_monitor, risk_monitor, kill_switch, monitoring_engine, monitoring_db 等
  - 監視ループ、ログ永続化（SQLite）、KillSwitch（自動停止判定）
- kabusys.portfolio.*
  - 候補選び、重み計算、ポジションサイズ計算、セクター制限などの純粋関数群
- kabusys.research.*
  - DuckDB を使ったファクター計算・IC・特徴量探索等
- kabusys.ai.*
  - news_nlp: OpenAI を使ったニュースセンチメント集計（バッチ、リトライ、レスポンス検証済）
  - regime_detector: MA200 と LLM マクロセンチメントの合成による市場レジーム判定
- kabusys.tools
  - 運用・検証用の補助スクリプト（例: paper_verification_report）

ディレクトリ構成
----------------
（リポジトリの src/kabusys 以下を抜粋した構成例）
- src/
  - kabusys/
    - __init__.py
    - config.py
    - config_setup.py
    - validate_config.py
    - run_execution.py
    - run_monitoring.py
    - utils/
      - __init__.py
      - logging_setup.py
      - process_priority.py
    - execution/
      - (ExecutionEngine, BrokerFactory, OrderManager, RiskManager 等)
    - monitoring/
      - monitoring_db.py
      - system_monitor.py
      - trade_monitor.py
      - risk_monitor.py
      - monitoring_engine.py
      - kill_switch.py
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
    - tools/
      - paper_verification_report.py
      - __init__.py
    - data/  (データファイル・フラグファイルを保存する想定ディレクトリ)
    - logs/  (ログファイル保存先)

運用上の注意（要約）
-------------------
- .env は機密情報を含むため絶対にリポジトリへコミットしないこと。
- 本番（KABUSYS_ENV=live）の場合は LINE 通知等の設定を確実に行い、KILL_FLAG_CLEAR_ON_START は 0 にすること。
- run_execution/run_monitoring は stop flag（data/stop_requested.flag）で安全に停止可能。KillSwitch による自動停止もある（data/kill.flag）。
- OpenAI を使用する機能は API 呼び出しのコスト・レイテンシに注意。OPENAI_API_KEY を必ず設定すること。
- DuckDB / SQLite のパスは Settings を用いて柔軟に変更可能。紙上での検証時は paper_trading 用 DB に完全分離する。

開発者向けヒント
----------------
- 単体関数群（portfolio, research 等）は副作用が少なくユニットテストしやすい設計です。
- OpenAI 呼び出し部分は _call_openai_api を patch することでテスト時に差し替え可能です。
- monitoring_db.init_monitoring_db は冪等でスキーママイグレーションも簡易的に行います。

サポート / 追加情報
--------------------
- config/*.yaml テンプレートやより詳細な運用ドキュメントがある場合は README にリンクしてください（本リポジトリ抜粋では含まれていません）。
- 実運用でのデプロイ方法（systemd / docker / k8s など）は本 README の範囲外です。必要に応じてユニット定義や Dockerfile を作成してください。

以上。本リポジトリのコードベースに基づく README です。補足や実例（systemd ユニット / Docker 起動例 / CI 設定など）が必要であれば続けて作成します。