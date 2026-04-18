KabuSys — 日本株自動売買システム
================================

このリポジトリは日本株向けの自動売買システム（KabuSys）のコアライブラリおよび起動スクリプト群です。
ここに含まれるのは、実行エンジン、監視（Monitoring）、ポートフォリオ構築、リサーチ、AI（ニュースセンチメント／レジーム判定）、および運用用ユーティリティ類です。

本 README ではプロジェクトの概要、主要機能、セットアップ手順、基本的な使い方、ディレクトリ構成を日本語でまとめます。

前提
----
- Python 3.10+（| 型アノテーション等を使用）
- 必要ライブラリ: duckdb, psutil, openai, PyYAML（任意）、および標準ライブラリの sqlite3 等
  - 依存関係は別途 requirements.txt を用意している想定です。無ければ下記例を参考に個別にインストールしてください。

特徴（機能一覧）
----------------
- ExecutionEngine（本番およびペーパートレード対応）
  - KABUSYS_ENV によって paper_trading（MockBroker）と live を切り替え
  - paper_trading 用に専用 SQLite（デフォルト: data/paper_trading.db）を使用して本番 DB と分離
- Monitoring（System / Trade / Risk の監視）
  - 定期ポーリングで CPU / メモリ / ディスク使用率、プロセス生存、データ鮮度、滞留注文、ドローダウン等を監視
  - 監視結果は SQLite（data/monitoring.db）に永続化
  - Kill Switch（条件を満たすと data/kill.flag を書き込み ExecutionEngine を停止）
- ポートフォリオ構築モジュール
  - 候補選定（スコア順）、等金額／スコア加重、リスクベースのポジションサイジング、セクターキャップ、レジーム乗数
- リサーチ（DuckDB を用いたファクター計算・特徴量解析）
  - Momentum / Value / Volatility 等のファクター計算
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリー
- AI モジュール（OpenAI を利用）
  - ニュースセンチメント（ai_scores テーブル書込）
  - マーケットレジーム判定（market_regime テーブル書込）
  - API 呼び出しはリトライ/バックオフやレスポンス検証を実装
- 運用ユーティリティ
  - .env 対話式ウィザード（config_setup）
  - 起動前設定検証 CLI（validate_config）
  - Paper Trading 検証レポート生成ツール

セットアップ
-----------

1. リポジトリをクローン／チェックアウト

2. Python 環境を用意（推奨: venv）
   - python -m venv .venv
   - source .venv/bin/activate  # (UNIX)
   - .venv\Scripts\activate     # (Windows)

3. 必要パッケージをインストール（例）
   - pip install duckdb psutil openai PyYAML

   （requirements.txt があれば: pip install -r requirements.txt）

4. 初期設定（.env）
   - 対話式ウィザードで .env を生成・更新:
     - python -m kabusys.config_setup
   - あるいは .env を手動作成（.env.example を参照してください）。必須環境変数:
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
   - 主要な環境変数（一部、デフォルト値を示します）
     - KABUSYS_ENV: development | paper_trading | live  （default: development）
     - DUCKDB_PATH: data/kabusys.duckdb
     - SQLITE_PATH: data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
     - LOG_LEVEL: INFO
     - KILL_FLAG_CLEAR_ON_START: 0（本番では 0 を推奨）
     - OPENAI_API_KEY: OpenAI を利用する場合に設定

5. （任意）設定検証
   - python -m kabusys.validate_config
   - 警告も FAIL として扱う場合は --strict を付ける

使い方（起動方法、ツール）
--------------------------

起動スクリプト（モジュールとして実行可能）:

- 実行エンジン（エンジン起動）
  - python -m kabusys.run_execution
  - 動作:
    - KABUSYS_ENV=paper_trading のときは MockBroker を使用し、paper_trading 用 DB に記録
    - 起動時に data/stop_requested.flag が存在すると起動せず終了
    - 実行中に data/stop_requested.flag が作成されると Graceful に停止
    - 実行中は data/execution.pid に PID を書き込み（設定によりパス変更可）

- 監視プロセス（ポーリングループ）
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き（デフォルト: 60）
  - 監視は Settings の sqlite_path（monitoring DB）を使用（環境に依らず本番パスを使用）
  - 停止は親ディレクトリから data/stop_requested.flag を作成

停止・Kill 管理:
- ExecutionEngine を強制停止したい（Kill Switch）場合:
  - kill.flag を作成（通常は Monitoring が条件満足時に書き込む）
  - デフォルトパス: data/kill.flag（Settings.kill_flag_path で上書き可能）
- 外部からの即時停止（いわゆる stop flag）:
  - data/stop_requested.flag を作成すると run_execution / run_monitoring のループが終了する

ログ:
- ログはデフォルトで logs/ ディレクトリへ日次ローテート（logs/<app_name>.log）
- LOG_DIR 環境変数、または setup_logging の引数で変更可能
- ログ設定は errors 時にファイル出力に失敗しても stdout にフォールバック

ツール類:
- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - デフォルト DB パス: 環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db
- 設定ウィザード
  - python -m kabusys.config_setup
- 設定検証
  - python -m kabusys.validate_config [--strict]

ライブラリ API（簡単な使用例）
------------------------------
（モジュールはライブラリとしても利用可能です。いくつかの例を示します）

- ポートフォリオ構築
  - from kabusys.portfolio import select_candidates, calc_equal_weights, calc_position_sizes
  - candidates = select_candidates(buy_signals, max_positions=10)
  - weights = calc_equal_weights(candidates)
  - sizes = calc_position_sizes(weights, candidates, portfolio_value=100_000_000, available_cash=50_000_000, current_positions={}, open_prices=price_map)

- リサーチ（DuckDB 接続を渡して使用）
  - import duckdb
  - conn = duckdb.connect("data/kabusys.duckdb")
  - from kabusys.research import calc_momentum, calc_volatility
  - momentum = calc_momentum(conn, target_date=date(2026,4,1))

- AI スコアリング（News）
  - from kabusys.ai import score_news
  - score_news(conn, target_date=date(2026,4,1), api_key="sk-...")

監視 DB（SQLite）
----------------
- 監視用 DB スキーマは kabusys.monitoring.monitoring_db.init_monitoring_db によって冪等に作成されます。
- 主なテーブル:
  - system_status: CPU/メモリ/ディスク/プロセス状態の履歴
  - trade_logs: 発注イベントログ（latency_ms カラムあり）
  - positions: 現在の保有
  - risk_logs: リスク関連イベント
  - dashboard: 集計（id=1 の1行で管理）

ディレクトリ構成（主要ファイル）
--------------------------------
以下は src/kabusys 配下の主要モジュールと用途の一覧です（抜粋）。

- kabusys/
  - __init__.py                       — パッケージ定義
  - config.py                         — 環境変数 / Settings 管理（.env 自動ロード含む）
  - config_setup.py                   — .env 対話式ウィザード
  - validate_config.py                — 起動前設定検証 CLI
  - run_execution.py                  — ExecutionEngine 起動スクリプト
  - run_monitoring.py                 — SystemMonitor ポーリング起動スクリプト

  - execution/                         — 発注エンジン関連（Factory等はここに配置想定）
    - execution_engine.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
    - broker_factory.py

  - monitoring/
    - monitoring_db.py                — SQLite 永続層
    - system_monitor.py               — CPU/Mem/Proc/Data鮮度監視
    - trade_monitor.py                — 注文滞留や約定異常の検知（実装ファイルあり）
    - risk_monitor.py                 — ドローダウン／ポジション上限監視
    - monitoring_engine.py            — 各 Monitor 結合、ポーリングループ
    - kill_switch.py                  — kill.flag 書込ロジック
    - alert_manager.py                — 通知（LINE など）管理（実装想定）

  - portfolio/
    - portfolio_builder.py            — 候補選定 / 重み計算
    - position_sizing.py              — 発注株数計算
    - risk_adjustment.py              — セクターキャップ・レジーム乗数

  - research/
    - factor_research.py              — Momentum/Value/Volatility ファクター計算
    - feature_exploration.py          — 将来リターン / IC / 統計
    - __init__.py

  - ai/
    - news_nlp.py                     — ニュースセンチメント（OpenAI 呼び出し・DB 書込）
    - regime_detector.py              — マーケットレジーム判定（MA + マクロ NLP）
    - __init__.py

  - tools/
    - paper_verification_report.py    — Paper Trading の検証レポート

  - utils/
    - logging_setup.py                — 共通ログ設定ユーティリティ
    - process_priority.py             — プロセス優先度 / CPU Affinity 設定ユーティリティ

運用上の注意・補足
-------------------
- .env の自動ロード: プロジェクトルート（.git または pyproject.toml を基準）から .env/.env.local を自動ロードします。自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- 本番モード（KABUSYS_ENV=live）では設定を十分に確認してください（LINE 通知や Kill Switch の設定など）。
- OpenAI API など外部 API を使う機能は API キー（OPENAI_API_KEY）を必要とします。失敗時はフェイルセーフ処理を行う実装になっていますが、キーは適切に管理してください。
- ログディレクトリ作成に失敗した場合はファイル出力はスキップされ、標準出力のみになります（警告が出ます）。
- MONITOR_POLL_INTERVAL など一部パラメータは環境変数で上書き可能です（run_monitoring のポーリング間隔等）。

問題が発生したら
----------------
- まず python -m kabusys.validate_config を実行して設定に問題がないか確認してください。
- ログ (logs/<app_name>.log または標準出力) を確認してください。
- DB パスや権限、OpenAI キーの有無、psutil による優先度設定の失敗（権限不足）などがよくある原因です。

---

この README はリポジトリに含まれるソースコードから想定される使い方・運用フローをまとめたものです。実際の運用時は各モジュールの実装や運用ガイド（別ドキュメント）に従ってください。必要があれば README に記載するコマンド例や .env.example を追加してドキュメントを強化できます。