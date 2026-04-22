# KabuSys

日本株向け自動売買 / 研究プラットフォームのサブセット実装ドキュメント（README）。  
この README はリポジトリ内の主要スクリプト・モジュールの使い方、セットアップ手順、ディレクトリ構成をまとめたものです。

---

## プロジェクト概要

KabuSys は日本株の自動売買エンジン、監視、バックテスト／リサーチ用ユーティリティ、AI を使ったニュースセンチメント評価などを含む小規模なトレーディングプラットフォームです。  
このコードベースでは主に次を提供します:

- ExecutionEngine（発注エンジン）の起動スクリプト（本番 / ペーパートレード切替）
- Monitoring（システム監視・アラート・Kill Switch）
- Portfolio 構築・ポジションサイズ計算（純粋関数群）
- Research（ファクター計算・特徴量解析）
- AI モジュール（ニュース NLP / レジーム判定：OpenAI を利用）
- 各種 CLI ユーティリティ（設定ウィザード・設定検証・検証レポート生成）

---

## 機能一覧

- Execution
  - run_execution.py: ExecutionEngine を起動。`KABUSYS_ENV=paper_trading` なら MockBroker を使い、ペーパートレード用 SQLite に記録。
  - PID ファイル / stop flag による起動管理。
- Monitoring
  - run_monitoring.py: SystemMonitor のポーリングを行うデーモン風スクリプト。
  - MonitoringDB に system_status, trade_logs, positions, risk_logs, dashboard を記録。
  - Kill Switch（条件に応じて data/kill.flag を書く）・アラート通知フック。
- Portfolio
  - 銘柄選定 / 重み計算 / セクター制約 / ポジションサイズ計算（純粋関数実装）。
- Research
  - ファクター計算（Momentum / Volatility / Value など）。
  - 将来リターン、IC 計算、統計サマリー。
- AI
  - news_nlp: OpenAI（gpt-4o-mini 等）を用いたニュースセンチメント集約・ai_scores への書き込み。
  - regime_detector: ETF の MA およびマクロニュースでレジーム判定し market_regime に書き込み。
- ツール
  - config_setup.py: 対話式 .env ウィザード生成。
  - validate_config.py: .env / config/*.yaml の検証 CLI。
  - tools/paper_verification_report.py: ペーぱートレードの検証レポート生成（稼働率・成立率・レイテンシなど）。

---

## セットアップ手順（ローカル開発向け）

1. Python と仮想環境
   - 推奨: Python 3.10+
   - 仮想環境を作成・有効化:
     - python -m venv .venv
     - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージのインストール
   - requirements.txt がある想定で:
     - pip install -r requirements.txt
   - 主要な依存例（プロジェクトで使われている主なライブラリ）:
     - duckdb, psutil, openai, PyYAML（検証でオプション）

3. リポジトリルートに data / logs ディレクトリを作成（多くは自動作成されますが手動で準備しておくと権限エラーを回避できます）
   - mkdir -p data logs

4. .env の用意
   - 対話式に作る:
     - python -m kabusys.config_setup
   - 必須環境変数:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - 重要: .env は Git にコミットしないでください（config_setup も同旨のヘッダを出力します）。

5. 設定検証（任意だが推奨）
   - python -m kabusys.validate_config
   - --strict をつけると警告もエラー扱いになります:
     - python -m kabusys.validate_config --strict

6. OpenAI を使う機能を利用する場合
   - OPENAI_API_KEY を .env に設定するか、関数呼び出し時に api_key 引数を渡す。

---

## 環境変数（主要）

- KABUSYS_ENV: 実行環境（development / paper_trading / live）デフォルト: development
  - paper_trading の場合、run_execution は MockBroker を使い PAPER_TRADING_SQLITE_PATH に記録する。
- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- OPENAI_API_KEY: OpenAI API キー（AI 機能で必要）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: ペーパートレードの約定モード（instant / partial / never / reject）
- LOG_LEVEL: ログ出力レベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- LOG_DIR: ログ保存ディレクトリ（デフォルト: logs）
- KILL_FLAG_CLEAR_ON_START: Execution 起動時に kill.flag を自動クリアするか（0/1）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒）。デフォルト 60。
  - 0 以下や不正値はデフォルトにフォールバックします。

---

## 使い方（主要コマンド）

- 設定ウィザード（.env 生成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 厳格モード（警告も失敗にする）:
    - python -m kabusys.validate_config --strict

- ExecutionEngine 起動
  - python -m kabusys.run_execution
  - 特記事項:
    - KABUSYS_ENV=paper_trading の場合、MockBroker を使用し data/paper_trading.db に記録（本番 DB と分離）。
    - 起動時に data/stop_requested.flag が存在すると起動しません。
    - PID ファイル: data/execution.pid（Settings.pid_file_path で変更可能）
    - 停止は data/stop_requested.flag を作成することで行います（存在検知で安全に停止）。

- Monitoring 起動
  - python -m kabusys.run_monitoring
  - オプション:
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可能。デフォルト 60 秒。
    - Monitoring は環境（KABUSYS_ENV）にかかわらず production の sqlite_path（Settings.sqlite_path）を使用します（監視ログは本番 DB を想定）。
    - 停止フラグ: data/stop_requested.flag を検知するとループを終了します。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - デフォルト DB: 環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db

- AI 関連（プログラムから呼び出し）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)

---

## ロギング

- 共通ユーティリティ: kabusys.utils.logging_setup.setup_logging(app_name="execution")
  - stdout（StreamHandler）と日次ローテートファイル（logs/<app_name>.log）を設定します。
  - LOG_DIR 環境変数でログ保存先を変更可能。
  - ログレベルは引数、環境変数 LOG_LEVEL、デフォルト INFO の順で解決されます。

---

## 監視 DB（SQLite）スキーマ概要

monitoring_db.init_monitoring_db が作成するテーブル（冪等）

- system_status
  - recorded_at, cpu_percent, memory_percent, disk_percent, process_ok
- trade_logs
  - logged_at, event_type, client_order_id, code, side, qty, price, filled_qty, state, latency_ms
- positions
  - code (PK), qty, avg_price, current_price, updated_at
- risk_logs
  - logged_at, event_type, metric_name, metric_value, threshold, detail
- dashboard
  - id=1 固定行、portfolio_value, cash, drawdown_pct, open_order_count, position_count, peak_value

これらは MonitoringDB クラス経由で読み書きしてください（トランザクションやマイグレーションも含む）。

---

## ディレクトリ構成

リポジトリの主要ファイル／ディレクトリ（src/kabusys を基準）

- src/kabusys/
  - __init__.py
  - config.py               — 環境変数 / Settings
  - config_setup.py         — 対話式 .env ウィザード
  - validate_config.py      — 設定検証 CLI
  - run_execution.py        — ExecutionEngine 起動スクリプト
  - run_monitoring.py       — SystemMonitor 起動スクリプト
  - tools/
    - paper_verification_report.py
  - ai/
    - news_nlp.py
    - regime_detector.py
    - __init__.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py
  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py (実装あり)
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py (実装あり)
  - utils/
    - logging_setup.py
    - process_priority.py
    - __init__.py
  - execution/               — Execution に関する実装群（broker_factory, engine 等）
  - data/                    — （ランタイム）data/stop_requested.flag や DB ファイル等を置く既定の場所
  - logs/                    — ログ出力先（デフォルト）

---

## 便利な運用メモ / 注意事項

- .env の自動ロード:
  - config.py はリポジトリルート（.git または pyproject.toml）を起点に .env / .env.local を自動読み込みします。
  - テスト等で自動読み込みを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- kill.flag / stop_requested.flag:
  - Kill Switch（重大アラートによる停止）は data/kill.flag を書き込みます（Settings.kill_flag_path）。
  - 手動停止（安全に停止させたいとき）は data/stop_requested.flag を作成すると run_execution/run_monitoring が検知して終了します。
- ペーパートレードと本番 DB の分離:
  - paper_trading 環境では PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）が使われ、本番の monitoring.db とは分離されます。
- OpenAI 使用時のフェイルセーフ:
  - AI モジュールは API 呼び出し失敗時にフェイルセーフの動作（スコア 0 で継続 など）を行う設計です。ただし API キー未設定は例外になります。
- ローカル・本番差異:
  - run_monitoring はコード中で「Monitoring は環境にかかわらず本番 sqlite_path を使用する」と明示されています。意図した環境を確認してください。
- Docker / systemd などで運用する場合:
  - PID ファイル、ログディレクトリ、data/ のパーミッションを運用ユーザーが書き込めるようにしてください。
- 依存ライブラリ:
  - duckdb, psutil, openai, PyYAML などがコードから参照されています。requirements.txt をプロジェクトに用意してインストールしてください。

---

## 例: 最低限の .env（例示）

以下は最小構成の例（秘密値は適切に設定してください）:

JQUANTS_REFRESH_TOKEN=your_jquants_token_here
KABU_API_PASSWORD=your_kabu_api_password_here
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
LOG_LEVEL=INFO
OPENAI_API_KEY=sk-xxxx...

（.env.example をプロジェクトに置いてある場合はそれを参照してください）

---

この README はコードベースの現状に基づいて作成しています。追加の詳細（ExecutionEngine の内部挙動、Broker 実装、strategy 等）は個別ドキュメントやソースコードの docstring を参照してください。必要であれば起動例、systemd ユニットファイル、Dockerfile のテンプレート等の運用ガイドも作成できます。どの部分を掘り下げたいか教えてください。