KabuSys — 日本株自動売買システム (README)
====================================

概要
----
KabuSys は日本株の自動売買・研究・監視を目的としたモジュール群です。  
主要機能は注文実行エンジン、監視（モニタリング）、ポートフォリオ構築・サイズ決定、ファクター計算・リサーチ、およびニュースを用いた AI 判定などを含みます。  
本リポジトリはライブラリとしての利用と、コマンドラインから起動する実行スクリプト（monitoring / execution / 各種ツール）を両立する構成になっています。

主な特徴
--------
- ExecutionEngine（発注エンジン）:
  - 本番 / ペーパートレード切替（KABUSYS_ENV=paper_trading で MockBroker を使用）
  - リスク管理、オーダー管理、リコンサイル機能を含む
- Monitoring（監視）:
  - システムリソース、プロセス健全性、データ鮮度、注文関連の監視
  - Kill Switch（閾値超過で停止フラグを立てる）
- Portfolio モジュール:
  - 候補選定、等金額 / スコア加重配分、ポジションサイズ計算、セクター制限、レジーム乗数
- Research（リサーチ）:
  - DuckDB を使ったファクター計算（Momentum / Volatility / Value 等）
  - 将来リターン計算、IC（情報係数）計算、統計サマリー
- AI（OpenAI）連携:
  - ニュースセンチメントによる銘柄スコア付与（news_nlp）
  - マクロニュースを用いた市場レジーム判定（regime_detector）
  - OpenAI（gpt-4o-mini 等）に依存（APIキー必須）
- ツール:
  - .env 対話ウィザード（config_setup）
  - 設定検証 CLI（validate_config）
  - ペーパートレード検証レポート生成ツール（paper_verification_report）
- ロギング:
  - コンソール stdout + 日次ローテーションのファイル出力（logs/<app>.log）
- 永続化:
  - DuckDB（分析用）、SQLite（監視・発注履歴 / paper_trading 用）

前提 / 必要パッケージ
--------------------
- Python 3.10+
  - （コードに | 演算子を使った型注釈があるため）
- 推奨インストール（例）:
  - duckdb
  - psutil
  - openai (AI 機能を使う場合)
  - PyYAML (config の詳細検証を行いたい場合)
- 例:
  pip install duckdb psutil openai PyYAML

初期セットアップ
---------------
1. リポジトリをクローンする:
   - git clone <repo-url>

2. 仮想環境・依存パッケージをインストール:
   - python -m venv .venv
   - source .venv/bin/activate
   - pip install -U pip
   - pip install duckdb psutil openai PyYAML

3. .env の作成（対話ウィザード推奨）:
   - python -m kabusys.config_setup
   - ウィザードは J-Quants / kabuステーション のトークンや DB パス等の必要設定を聞いて .env を生成します。
   - 重要な環境変数（最低限必須）:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - OpenAI を使う場合:
     - OPENAI_API_KEY を環境変数にセットしてください（config_setup は OPENAI_API_KEY を扱いません）。

4. 設定検証:
   - python -m kabusys.validate_config
   - 警告を fail として扱いたい場合: python -m kabusys.validate_config --strict

デフォルトのファイル・パス
------------------------
- DuckDB: data/kabusys.duckdb (環境変数 DUCKDB_PATH で変更可能)
- SQLite (監視用): data/monitoring.db (環境変数 SQLITE_PATH)
- Paper Trading SQLite: data/paper_trading.db (PAPER_TRADING_SQLITE_PATH で変更)
- ログディレクトリ: logs/ (LOG_DIR 環境変数で変更可能)
- Kill フラグ: data/kill.flag (Settings.kill_flag_path)
- 停止フラグ（スクリプト終了用）: data/stop_requested.flag
- Execution PID ファイル: data/execution.pid（起動時に記録）

よく使うコマンド・使い方
----------------------

- 監視ループを起動（Monitoring）
  - 簡易:
    python -m kabusys.run_monitoring
  - ポーリング間隔を環境変数で指定:
    export MONITOR_POLL_INTERVAL=30  # 秒
  - 補足:
    - run_monitoring は常に production 用の sqlite_path（Settings.sqlite_path）を使用して監視テーブルを初期化します。
    - 停止するにはプロジェクトルートの data/stop_requested.flag を作成するか、Ctrl+C。

- ExecutionEngine を起動（発注エンジン）
  - 通常起動:
    python -m kabusys.run_execution
  - ペーパートレード:
    export KABUSYS_ENV=paper_trading
    python -m kabusys.run_execution
    - paper_trading の場合、MockBrokerClient を用い、データは paper_sqlite_path（デフォルト data/paper_trading.db）に記録されます（本番 DB と分離）。
  - 停止:
    - data/stop_requested.flag を作成すると起動スレッドに検知されエンジン停止処理が行われます。
    - Kill Switch により data/kill.flag が書き込まれると ExecutionEngine 側で停止処理が発動します（kill.flag の存在は Settings.kill_flag_clear_on_start に依存して自動クリア可）。

- .env の対話作成・更新
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - --strict で警告も失敗とする

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db

- AI 機能（ニュースセンチメント / レジーム判定）
  - OpenAI API キーが必要（環境変数 OPENAI_API_KEY）
  - 関数呼び出し例（Python API 経由）:
    from kabusys.ai.news_nlp import score_news
    # DuckDB 接続（duckdb.connect）を作成して score_news(conn, target_date, api_key=...)
  - 失敗時はフォールバック動作（API失敗時の安全側処理）が組まれていますが、APIキーの設定を推奨します。

運用上の注意
------------
- Kill / Stop フラグ:
  - stop_requested.flag: run_monitoring / run_execution が存在を検知して安全に終了するためのファイル（手動で作成して停止）。
  - kill.flag: KillSwitch が書き込むフラグ。ExecutionEngine に対する「停止命令」として利用される（本番での危険操作に注意）。
- ログ:
  - ログは stdout と logs/<app>.log に日次ローテーションで出力されます。
  - ログディレクトリ作成に失敗した場合はファイル出力をスキップして stdout のみになります。
- 環境の分離:
  - KABUSYS_ENV=paper_trading の場合は発注が仮想化され、本番用 DB を上書きしないよう paper_trading 用 DB に書き込みます。
- DuckDB / SQLite:
  - DuckDB は分析用の高速クエリエンジンとして利用します。prices_daily / raw_financials / raw_news などのテーブルに依存する処理があります。
  - SQLite は監視ログ・トレードログなどの軽量永続化に使用します。

主要ファイル・ディレクトリ構成
----------------------------
（src/kabusys 以下を抜粋）

- src/kabusys/
  - __init__.py
  - config.py               — 環境変数 / 設定読み込みロジック
  - config_setup.py         — .env 対話式ウィザード
  - validate_config.py      — 設定検証 CLI
  - run_monitoring.py       — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py        — ExecutionEngine 起動スクリプト
  - utils/
    - logging_setup.py      — ログ設定ユーティリティ
    - process_priority.py   — プロセス優先度 / CPU affinity
  - monitoring/
    - monitoring_db.py      — SQLite 用永続化層（テーブル定義・CRUD）
    - system_monitor.py     — システムリソース・データ鮮度監視
    - trade_monitor.py      — 注文関連監視（滞留注文等）
    - risk_monitor.py       — ドローダウン・ポジション上限監視
    - kill_switch.py        — kill.flag の生成 / 管理
    - monitoring_engine.py  — 監視コンポーネント統合（Polling Engine）
    - alert_manager.py      — （アラート送信ロジック、LINE 等）
  - execution/              — Execution / Broker 関連（Engine, OrderManager, Reconciler, RiskManager 等）
  - portfolio/
    - portfolio_builder.py  — 候補選定 / 重み計算
    - position_sizing.py    — 株数決定・投下資金スケーリング
    - risk_adjustment.py    — セクターキャップ / レジーム乗数
  - research/
    - factor_research.py    — ファクター計算（momentum / volatility / value）
    - feature_exploration.py— 将来リターン / IC / 統計サマリ
  - ai/
    - news_nlp.py           — ニュースを LLM で評価して ai_scores に書き込む
    - regime_detector.py    — マクロ + ETF MA を使ったレジーム判定
  - tools/
    - paper_verification_report.py — Paper Trading の検証レポート生成

サンプル .env（参考）
--------------------
# --- J-Quants API ---
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here

# --- kabuステーション API ---
KABU_API_PASSWORD=your_kabu_api_password_here
KABU_API_BASE_URL=http://localhost:18080/kabusapi

# --- LINE (任意) ---
LINE_CHANNEL_ACCESS_TOKEN=
LINE_USER_ID=

# --- データベース ---
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
PAPER_TRADING_SQLITE_PATH=data/paper_trading.db

# --- システム設定 ---
KABUSYS_ENV=development
LOG_LEVEL=INFO
KILL_FLAG_CLEAR_ON_START=0

よくある質問（短）
-----------------
Q. どの Python バージョンが必要？
A. Python 3.10 以上を推奨します（型注釈で | 演算子を使用）。

Q. 本番稼働時に注意すべき点は？
A. KABUSYS_ENV=live の設定確認、LINE 通知 / kill flag の扱い、設定ファイル（.env）に機密情報が含まれるので絶対に VCS にコミットしないでください。

Q. AI 機能を使うには？
A. OPENAI_API_KEY を設定し、必要なパッケージ（openai）をインストールしてください。API 呼び出しはレート制限やエラー処理を実装していますが、APIキーの管理に注意してください。

貢献 / 開発
-----------
- コードの拡張・修正は PR を通してください。
- ローカル開発時は .env.local を使って環境上書きできます（.env.auto ロードの優先順あり）。
- ユニットテスト、CI、デプロイ手順等はプロジェクトの運用ポリシーに従って整備してください。

ライセンス・作者
----------------
- (ここにプロジェクトのライセンス表記を入れてください)
- 作者 / メンテナー情報を必要に応じて追記してください。

付記
----
このREADME はソースコードに基づく主要な使い方と設計上の注意点を抜粋してまとめたものです。詳細は各モジュールの docstring とコードを参照してください。