KabuSys — 日本株自動売買システム
================================

このドキュメントはリポジトリ内のコードベース（src/kabusys 以下）についての簡単な概要、セットアップ手順、実行方法、ディレクトリ構成を日本語でまとめた README です。

プロジェクト概要
--------------
KabuSys は日本株の自動売買システムに関するライブラリ／実行スクリプト群です。主な機能は以下の通りです。

- 市場データ（DuckDB）を使ったファクター計算・リサーチ（momentum, volatility, value 等）
- ポートフォリオ構築（候補選定、重み計算、ポジションサイズ決定）
- ExecutionEngine（発注エンジン）と Monitoring（監視）コンポーネント群
- Paper Trading（ペーパートレード）モード（本番 DB と分離）
- ニュースを LLM（OpenAI）で評価し AI スコアを生成する機能（news_nlp）
- 市場レジーム判定（regime_detector）
- 環境設定ウィザード、設定検証ツール、運用用ユーティリティ（ログ設定、プロセス優先度設定 等）
- 監視ログの永続化（SQLite）とレポート生成ツール（paper_verification_report）

主な機能一覧
--------------
- 設定管理
  - .env 自動読み込み / 対話式ウィザード（kabusys.config_setup）
  - 設定検証 CLI（kabusys.validate_config）
- 実行 / 監視
  - ExecutionEngine 起動スクリプト（run_execution.py）
    - KABUSYS_ENV=paper_trading のときはモックブローカーを使用し data/paper_trading.db に記録
  - SystemMonitor（システムリソース・データ鮮度監視）
  - MonitoringEngine（複数モニタのポーリング・KillSwitch 判定 等）
  - run_monitoring.py（監視ポーリングループ起動）
- ポートフォリオ
  - 候補選定、等重・スコア重み計算、リスク制御（セクターキャップ）、サイズ計算（lot rounding）
- リサーチ
  - ファクター計算（momentum, volatility, value）
  - 特徴量探索（forward returns、IC、統計サマリ等）
- AI
  - news_nlp: OpenAI を使ったニュースセンチメントスコアリング
  - regime_detector: MA とマクロニュースを組み合わせた市場レジーム判定
- ツール
  - paper_verification_report: ペーパートレード検証レポート生成

前提 / 必要な依存パッケージ
-------------------------
（プロジェクトに requirements.txt がない場合は下記の主要パッケージをインストールしてください）

- Python 3.9+
- duckdb
- psutil
- openai (AI 機能を使う場合)
- PyYAML（config ファイル検証を行いたい場合に有効）

例:
- 仮想環境作成・有効化（任意）
  python -m venv .venv
  source .venv/bin/activate  （Windows: .venv\Scripts\activate）
- 依存インストール（一例）
  pip install duckdb psutil openai pyyaml

セットアップ手順
----------------

1. リポジトリを取得する
   git clone <repo-url>
   cd <repo-root>

2. 仮想環境を作成して依存をインストール（上記参照）

3. .env の作成（推奨: 対話式ウィザード）
   - ウィザードを実行:
     python -m kabusys.config_setup
     → 対話に従って J-Quants トークン、kabu API パスワード、KABUSYS_ENV などを入力して .env を生成します。

   - 生成後、設定を検証:
     python -m kabusys.validate_config
     --strict を付けると警告も失敗扱いになります:
     python -m kabusys.validate_config --strict

   環境変数（重要なもの）
   - JQUANTS_REFRESH_TOKEN (必須)
   - KABU_API_PASSWORD (必須)
   - KABUSYS_ENV: development | paper_trading | live （デフォルト: development）
   - DUCKDB_PATH: DuckDB のパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
   - PAPER_TRADING_SQLITE_PATH: （paper_trading 用 DB、デフォルト: data/paper_trading.db）
   - LOG_LEVEL: ログレベル（デフォルト: INFO）
   - OPENAI_API_KEY: OpenAI を使う場合に必要
   - PAPER_FILL_MODE: paper_trading 時の注文約定モード（instant|partial|never|reject）

4. ディレクトリの準備（通常は自動作成されますが手動で作る場合）
   - data/ (DB やフラグファイルを置くディレクトリ)
   - logs/ (ログファイル — ローテーションで保存されます)

使い方（主要スクリプト）
-----------------------

1. 監視ループを起動（Monitoring）
   - 簡易実行:
     python -m kabusys.run_monitoring
   - ポーリング間隔を秒単位で上書き:
     MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
     （デフォルト: 60 秒。1 未満や不正な値は無視されてデフォルトが使われます）
   - 監視は settings.sqlite_path（デフォルト data/monitoring.db）を使用します。
   - 停止: リモートで監視ループを停止したい場合はプロジェクトルートの data/stop_requested.flag を作成します（存在を検知してループを終了）。

2. 実行エンジンを起動（Execution）
   - 本番/開発/ペーパーを env で切り替え:
     KABUSYS_ENV=paper_trading python -m kabusys.run_execution
     python -m kabusys.run_execution  （KABUSYS_ENV が .env の値を参照）
   - paper_trading モードでは MockBrokerClient を使用し、データは data/paper_trading.db に記録されます（本番 DB と分離）。
   - 実行停止:
     - Monitoring 側の KillSwitch が異常検出時に data/kill.flag を書き込むと ExecutionEngine に停止シグナルが送られます。
     - また管理者が手動で data/stop_requested.flag を書くと起動スクリプトが検出して停止します。

3. Paper Trading 検証レポートの生成
   - コマンド:
     python -m kabusys.tools.paper_verification_report
   - 期間指定:
     python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
   - DB 指定（デフォルトは環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db）:
     python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

4. AI 関連（OpenAI）
   - news_nlp（ニューススコアリング）と regime_detector（市場レジーム判定）は OPENAI_API_KEY に依存します。未設定の場合は呼び出し時にエラー（ValueError）になります（ただし一部の関数は API 失敗時にフェールセーフ挙動を持ちます）。
   - OpenAI の呼び出しはレートリミット・一時エラーに対して指数バックオフでリトライする実装です。

運用上の注意
-------------
- ログ:
  - 共通のログ設定ユーティリティ（kabusys.utils.logging_setup）により、stdout と logs/<app_name>.log（日次ローテーション、30日分保持）に出力します。
  - ログディレクトリは LOG_DIR 環境変数で上書きできます。
- プロセス優先度:
  - 起動時にプロセス優先度を "high" に設定するユーティリティ（psutil 使用）を呼び出しますが、権限やプラットフォームによって設定できない場合は警告を出して継続します。
- Kill Switch / フラグファイル:
  - kill.flag: KillSwitch により書き込まれる ExecutionEngine 停止用フラグ（実行エンジンはこれを見て停止します）。
  - stop_requested.flag: run_monitoring / run_execution が常時チェックしている停止フラグ（手動で作成すると即座にループを終了します）。
  - Settings.kill_flag_clear_on_start が 1 のときは起動時に kill.flag を自動でクリアします（本番では 0 推奨）。

ディレクトリ構成（抜粋）
-----------------------
下記は src/kabusys 以下の主要ファイル・モジュール構成（リポジトリルートが src/ をパッケージソースとする想定）です。

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数/設定読み込みと Settings クラス
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリングループ起動スクリプト
  - monitoring/
    - monitoring_db.py       — SQLite 永続化層 / MonitoringDB
    - system_monitor.py      — システム状態・データ鮮度監視
    - trade_monitor.py       — （注文監視ロジック: code 参照）
    - risk_monitor.py        — ドローダウン／ポジション上限監視
    - monitoring_engine.py   — 各 Monitor の統合ポーリング
    - kill_switch.py         — kill.flag 書き込みユーティリティ
    - alert_manager.py       — （アラート送信ロジック: code 参照）
  - execution/
    - execution_engine.py    — ExecutionEngine（発注処理）
    - order_manager.py
    - order_repository.py
    - broker_factory.py
    - reconciler.py
    - risk_manager.py
  - portfolio/
    - portfolio_builder.py   — 候補選定・重み
    - position_sizing.py     — 発注株数計算・aggregate cap
    - risk_adjustment.py     — セクター制約・レジーム乗数
  - research/
    - factor_research.py     — momentum/volatility/value 計算（DuckDB 使用）
    - feature_exploration.py — forward returns, IC, 統計サマリ
  - ai/
    - news_nlp.py            — ニュースセンチメント（OpenAI）
    - regime_detector.py     — 市場レジーム判定（OpenAI + MA）
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート生成
  - utils/
    - logging_setup.py       — ログ初期化ユーティリティ
    - process_priority.py    — プロセス優先度 / CPU affinity ユーティリティ

補足 / よくある質問
-------------------
- Q: paper_trading と live の DB は分離されていますか？
  A: はい。paper_trading モードでは paper_sqlite_path（デフォルト data/paper_trading.db）を使用します。監視(DB) は run_monitoring 側では常に sqlite_path（data/monitoring.db）を使用します。

- Q: ログレベルやログ出力先はどう変えますか？
  A: LOG_LEVEL や LOG_DIR の環境変数で変更できます。setup_logging はこれらを参照して stdout とファイルハンドラを設定します。

- Q: OpenAI の呼び出しが失敗したらどうなりますか？
  A: news_nlp / regime_detector はレート制限や一時エラーに対してリトライしますが、最終的に失敗した場合はフェールセーフ（スコア=0 等）で継続するように実装されています。API キー未設定の場合は ValueError を送出します（呼び出し側で捕捉してください）。

- Q: .env が自動で読み込まれますか？
  A: config.py にてプロジェクトルートが検出できれば .env（および .env.local）を自動で読み込みます。自動ロードを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

最後に
------
この README はコードベースの主要な使い方、設定、運用上の注意をまとめたものです。実運用を開始する前に python -m kabusys.validate_config で設定を確認し、本番（KABUSYS_ENV=live）では kill フラグや LINE 通知設定などのガードを必ず確認してください。

必要であれば README に含める具体的なコマンドやサンプル .env 内容のテンプレートなども追加できます。必要があれば教えてください。