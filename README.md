# KabuSys

KabuSys は日本株の自動売買・研究・監視を目的とした小規模なシステム群です。本リポジトリは以下の主要機能を含みます: 注文実行エンジン、監視・アラート、ポートフォリオ構築ユーティリティ、ファクター研究、ニュース NLP（OpenAI）連携、Paper Trading 用ツールなど。

以下はコードベースから生成した README.md です。

## プロジェクト概要

KabuSys は以下を目的としたコンポーネント群で構成される Python パッケージです。

- 頻度の高い売買や発注管理を行う ExecutionEngine（ブローカ抽象化を持つ）
- 実行状況・システム状態・注文ログを記録・監視する Monitoring（SQLite）
- ポートフォリオ構築（候補選定・重み付け・ポジションサイズ計算）
- 研究用モジュール（ファクター計算・将来リターン・IC 計算など）
- ニュースを LLM（OpenAI）で解析して銘柄別スコアを生成する AI モジュール
- Paper Trading 用 DB と検証レポート生成ツール
- Streamlit を用いた監視ダッシュボード

設計上のポイント:
- 設定は環境変数（および .env / .env.local）を使用。Settings クラス経由で取得。
- Paper Trading（検証）と本番 DB は分離（PAPER_TRADING_SQLITE_PATH を使用）。
- 監視は SQLite（monitoring.db）、分析系は DuckDB を使用。

## 機能一覧

主要機能の概要:

- Execution
  - Broker 抽象化（実ブローカー or MockBroker）
  - OrderManager / OrderRepository / Reconciler（起動時の自動復旧）
  - RiskManager（発注前チェック）
- Monitoring
  - SystemMonitor（CPU/メモリ/ディスク、プロセス生存、データ鮮度）
  - TradeMonitor（滞留注文・約定異常）
  - RiskMonitor（ドローダウン・ポジション上限監視）
  - KillSwitch（条件により停止フラグを書いて Execution を停止）
  - AlertManager（LINE Push による通知）
  - MonitoringEngine（各モニタを定期実行）
  - Streamlit ダッシュボード（監視 DB を可視化）
- Portfolio
  - 候補選定（score 降順）
  - 等重 / スコア加重配分
  - ポジションサイズ計算（risk-based / equal / score）
  - セクターキャップ / レジーム乗数
- Research
  - Momentum / Volatility / Value ファクター計算（DuckDB）
  - 将来リターン計算、IC 計算、統計サマリ
- AI
  - news_nlp: raw_news → OpenAI で銘柄別センチメントを算出して ai_scores に格納
  - regime_detector: ETF (1321) の MA200 とマクロニュースの LLM センチメントを合成して日次レジーム判定
- Tools
  - paper_verification_report: Paper Trading DB を解析して検証レポートを標準出力に生成

## セットアップ手順

前提:
- Python 3.9+（パッケージで typing の新仕様を使用）
- OS によって追加パッケージが必要（例: psutil の一部機能は OS 権限が必要になる場合があります）

例: 簡易セットアップ手順

1. リポジトリをクローン
   - git clone <repo-url>
   - cd <repo>

2. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール（例）
   - pip install duckdb psutil openai requests streamlit

   ※ requirements.txt がある場合は `pip install -r requirements.txt` を使用してください。

4. 環境変数の準備
   - プロジェクトルートに `.env` または `.env.local` を置くと自動で読み込まれます（Settings モジュールの動作）。
   - 自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

主要な環境変数（概要）:
- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（AI 機能使用時）
- KABUSYS_ENV: environment: development | paper_trading | live（デフォルト: development）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: Monitoring DB（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 DB（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: paper_trading の MockBroker の約定挙動（instant|partial|never|reject）
- MONITOR_POLL_INTERVAL: 監視ループの秒間隔（デフォルト 60）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE 通知設定

例の .env（簡易）
    JQUANTS_REFRESH_TOKEN=...
    KABU_API_PASSWORD=...
    OPENAI_API_KEY=...
    KABUSYS_ENV=development
    DUCKDB_PATH=data/kabusys.duckdb
    SQLITE_PATH=data/monitoring.db

注意:
- Settings は OS 環境変数を優先し、.env → .env.local の順で読み込みます（.env.local は上書き可）。
- .env.local は OS 環境変数を上書きできますが、読み込み時に既存 OS 環境変数は保護されます。

## 使い方（主要スクリプト／コマンド）

1. 監視（Monitoring）を起動
   - python -m kabusys.run_monitoring
   - 説明:
     - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書きできます（秒、デフォルト 60）。
     - Monitoring は KABUSYS_ENV に関係なく本番 sqlite_path を使用して監視ログを残します。
     - 停止: プロセスに SIGINT（Ctrl+C）を送るか、プロジェクトの data/stop_requested.flag を作成するとループ終了します。

2. 実行エンジン（ExecutionEngine）を起動
   - python -m kabusys.run_execution
   - 説明:
     - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を利用して paper_trading.db（data/paper_trading.db）に書き込みます（本番 DB と分離）。
     - 起動時に data/stop_requested.flag が存在する場合は起動せず終了します。
     - 実行中、data/execution.pid に PID を書き込みます。stale な pid は SystemMonitor によって検出され削除されます。

3. Streamlit ダッシュボード（監視 UI）
   - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
   - 説明: monitoring.db にアクセスできない（存在しない、またはロック）場合は起動に失敗します。ダッシュボードは read-only URI で接続します。

4. Paper Trading 検証レポート
   - python -m kabusys.tools.paper_verification_report
   - オプション:
     - --from YYYY-MM-DD
     - --to YYYY-MM-DD
     - --db PATH  （PAPER_TRADING_SQLITE_PATH を上書き）
   - 出力: 標準出力に Pass/Fail を含むレポートを表示します。

5. AI / レジーム判定・ニューススコアの利用（プログラムから）
   - ニュース NLP（銘柄別スコア）:
     - from kabusys.ai.news_nlp import score_news
     - score_news(duckdb_conn, target_date, api_key="...")
   - レジーム判定:
     - from kabusys.ai.regime_detector import score_regime
     - score_regime(duckdb_conn, target_date, api_key="...")

6. テスト用: MonitoringEngine を単発実行
   - MonitoringEngine は run_once() を用いて単発実行可能（ユニットテストや CI 用）。

ファイルベースの制御:
- 停止フラグ: data/stop_requested.flag — run_monitoring / run_execution が監視している停止トリガー
- Kill switch（Execution を停止するための永続フラグ）: data/kill.flag — KillSwitch が書き込む
- PID ファイル: data/execution.pid — ExecutionEngine が書き込む

## 簡単な運用シナリオ

- 日中の監視:
  - system_monitor（run_monitoring）を常時稼働して system_status, risk_logs を記録
  - 異常発生時には AlertManager が LINE 通知を送る（設定済みの場合）
- 発注実行:
  - run_execution をデーモンで起動（paper_trading で検証する場合は KABUSYS_ENV=paper_trading）
  - 異常が発生すると KillSwitch によって data/kill.flag が書かれ、Execution が安全停止される
- 検証:
  - Paper Trading の DB を使って tools/paper_verification_report を実行し、性能基準（稼働率、成功率、P95 レイテンシ等）を評価

## ディレクトリ構成

主要なディレクトリとファイル（抜粋）

- src/kabusys/
  - __init__.py
  - config.py             — 環境変数 / 設定読み込みロジック（.env 自動ロード含む）
  - run_monitoring.py     — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py      — ExecutionEngine 起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート生成スクリプト
  - ai/
    - news_nlp.py          — raw_news → OpenAI で銘柄スコアを ai_scores に書き込む
    - regime_detector.py   — マクロ+ETF 指標から市場レジーム判定
  - monitoring/
    - monitoring_db.py     — SQLite テーブルの初期化と読み書きラッパ
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py
    - monitoring_engine.py
    - streamlit_dashboard.py
  - execution/
    - order_manager.py
    - reconciler.py
    - (その他 broker / engine / order_repository 等の実装)
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - utils/
    - process_priority.py   — プロセス優先度 / CPU affinity 設定ユーティリティ
  - data/ (runtime)
    - monitoring.db (default SQLite)
    - paper_trading.db
    - kabusys.duckdb
    - execution.pid
    - kill.flag / stop_requested.flag

注: repository のルートが自動検出されるのは config._find_project_root()（.git または pyproject.toml を基準）によるため、パッケージ配布後も CWD に依存しません。

## 運用上の注意 / 備考

- DB マイグレーション:
  - monitoring_db.init_monitoring_db() は冪等的にテーブルを作成し、一部のカラム追加（マイグレーション）処理を含みます。
- Paper Trading と本番 DB は分離して運用してください（Settings.is_paper 判定）。
- OpenAI を用いる処理は API キーが必要です。キーが未設定だと関数は ValueError を投げます（呼び出し側でハンドリングしてください）。
- process priority 設定（set_process_priority）は psutil を使い OS に依存します。権限や OS により設定できない場合は警告をログに出力してスキップします。
- .env のパースはシェルライクな簡易実装を行いますが、複雑なケースは想定していません。必要に応じて OS 環境変数を使ってください。
- 監視・実行コンポーネントはファイルベースのフラグを利用して相互制御を行います（stop_requested.flag, kill.flag）。運用時はこれらの取り扱いに注意してください。

---

README は上記が基本です。必要であれば次の情報も追加します:
- requirements.txt の推奨内容
- .env.example のテンプレート
- systemd / Supervisor 用のサービスユニット例
- よくあるトラブルシューティング（権限、psutil の挙動、DuckDB ファイルロックなど）

追加希望があれば教えてください。