KabuSys — README
===============

概要
----
KabuSys は日本株向けの自動売買・リサーチ・監視ツール群です。  
主に以下のコンポーネントを含みます：

- ExecutionEngine: ブローカーへ発注・注文管理・リコンシリエーション
- Monitoring: システム状態 / 注文状態 / リスクを定期的に監視してログ保存・アラート発行
- Research: DuckDB を使ったファクター計算・特徴量解析
- Portfolio: 候補選定・重み付け・ポジションサイジング
- AI (news_nlp / regime_detector): OpenAI を使ったニュースのセンチメント評価と市場レジーム判定
- Tools: Paper Trading 検証レポート生成スクリプト、Streamlit ダッシュボード等

主な設計方針：
- DuckDB / SQLite をローカル DB として使用（分析用と監視用で分離）
- 本番／ペーパー取引は環境変数で切り替え（paper_trading モードは本番 DB と分離）
- LLM 呼び出しには冪等性・リトライ・バリデーションを組み込み

機能一覧
--------
- 注文作成 / 発注管理 / 再起動時のリコンシリエーション（Reconciler）
- リスク監視（ドローダウン・ポジション上限）と kill.flag による停止シグナル
- システム監視（CPU / メモリ / ディスク / プロセス生存チェック / データ鮮度チェック）
- 注文滞留検知・約定価格異常検出
- LINE による一方向プッシュ通知（AlertManager）
- Streamlit による監視ダッシュボード
- DuckDB ベースのファクター計算（モメンタム・ボラティリティ・バリュー等）
- OpenAI を用いたニュースセンチメントスコアの算出（batch・retry・バリデーション付）
- Paper Trading 用の検証レポート生成ツール

セットアップ手順
----------------
前提
- Python 3.9+（ソースは typing/最新構文を想定）
- SQLite は標準ライブラリ
- 推奨パッケージ（主要な依存）:
  - duckdb
  - psutil
  - requests
  - openai
  - streamlit (ダッシュボード利用時)
インストール例（venv を推奨）:
  python -m venv .venv
  source .venv/bin/activate
  pip install -U pip
  pip install duckdb psutil requests openai streamlit

環境変数
- 必須（Settings._require により未設定だと例外になるもの）
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- 任意 / デフォルトあり（Settings に既定値あり）
  - KABUSYS_ENV: development | paper_trading | live （デフォルト: development）
  - LOG_LEVEL: DEBUG | INFO | ...
  - DUCKDB_PATH: data/kabusys.duckdb
  - SQLITE_PATH: data/monitoring.db
  - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
  - PAPER_FILL_MODE: instant | partial | never | reject （デフォルト: instant）
  - PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START など
  - OPENAI_API_KEY: OpenAI を使う機能で必要
- 自動読み込み: プロジェクトルートの .env / .env.local が自動ロードされる（CWD に依存せず .git / pyproject.toml を探索）
- 自動ロードを無効化: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

プロジェクトルートに .env.example を用意しておくことを推奨します（リポジトリ内に例があればそれを参照）。

使い方（主要コマンド）
--------------------

1) 監視ループを起動（Monitoring）
- デフォルトで本番用 SQLITE_PATH を使用して監視 DB を更新します。
- 環境変数でポーリング間隔を変更可: MONITOR_POLL_INTERVAL（秒、デフォルト 60）
- 実行:
  python -m kabusys.run_monitoring
- 停止:
  data/stop_requested.flag を作成するとループが終了します（または Ctrl+C）

2) ExecutionEngine を起動（発注系）
- KABUSYS_ENV=paper_trading にすると MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）へ書き込むため本番 DB と分離されます。
- 実行:
  python -m kabusys.run_execution
- 起動時に data/stop_requested.flag が存在する場合は起動せず終了
- 実行中 stop: data/stop_requested.flag を作成するとエンジンに停止指示が送られます
- ExecutionEngine は起動時に PID ファイル（デフォルト data/execution.pid）を作成します

3) Streamlit ダッシュボード
- 監視 DB を読み取り専用で開いてダッシュボードを表示します（MonitoringEngine を稼働させた状態を想定）。
- 実行例:
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

4) Paper Trading 検証レポート
- data/paper_trading.db の情報から検証レポートを生成します。
- 実行例:
  python -m kabusys.tools.paper_verification_report
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- データベース指定:
  --db PATH または環境変数 PAPER_TRADING_SQLITE_PATH

5) AI モジュール（プログラムから呼び出す）
- kabusys.ai.score_news(conn, target_date, api_key=None)
  - OpenAI API キーは api_key 引数 or OPENAI_API_KEY 環境変数で与える
  - raw_news / news_symbols / ai_scores テーブルを参照・更新します
- kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - 同様に OpenAI を用いたレジーム判定を行い market_regime テーブルへ書込

注意点 / オペレーション
- 本番監視（Monitoring）は Settings.env に関わらず本番 sqlite_path を使って監視ログを記録します（run_monitoring の仕様）。
- Paper Trading モードでは orders/発注に関する DB が本番と分離されます（settings.is_paper を参照）。
- プロセス優先度の設定: 起動時に set_process_priority("high") を呼んでいます（Linux/Windows 対応、権限不足時は警告）。
- stop/kill フラグ:
  - data/stop_requested.flag: 実行ループ停止を指示するローカルフラグ（run_*.py が監視）
  - data/kill.flag: KillSwitch により ExecutionEngine の停止を要求する用途で書き込まれる（KillSwitch はリスク条件で生成）
- OpenAI 呼び出しではリトライ / バリデーション / 出力クリップ等を行います。API キーが未設定の場合は例外またはフェイルセーフ（モジュールにより異なる）になります。

ディレクトリ構成（抜粋）
----------------------
以下は主要なファイル・モジュールの位置（src/kabusys配下）。

- src/kabusys/
  - __init__.py
  - config.py              — 環境変数 / Settings 管理
  - run_monitoring.py      — SystemMonitor ポーリングループ起動
  - run_execution.py       — ExecutionEngine 起動スクリプト
  - tools/
    - paper_verification_report.py  — Paper Trading レポート
  - ai/
    - news_nlp.py           — ニュース NLP（OpenAI）スコアリング
    - regime_detector.py    — 市場レジーム判定（LLM + MA200 合成）
  - monitoring/
    - monitoring_db.py      — SQLite テーブル初期化・永続層
    - system_monitor.py     — CPU/Mem/Disk/データ鮮度監視
    - trade_monitor.py      — 注文滞留 / 約定異常検出
    - risk_monitor.py       — ドローダウン / ポジション上限監視
    - kill_switch.py        — kill.flag の作成・評価
    - alert_manager.py      — LINE push 通知
    - monitoring_engine.py  — 複数モニタを束ねる実行エンジン
    - streamlit_dashboard.py— Streamlit ダッシュボード
  - execution/
    - order_manager.py
    - reconciler.py
    - ... (ブローカーファクトリ / order_repository 等)
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py
  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py
  - utils/
    - process_priority.py
  - data/ (実行時に生成する想定のディレクトリ)
    - monitoring.db (default SQLITE_PATH)
    - paper_trading.db
    - kabusys.duckdb (default DUCKDB_PATH)
    - execution.pid, stop_requested.flag, kill.flag, etc.

開発・デバッグ向け情報
--------------------
- Settings は .env / .env.local を自動でロードします。テストや CI で自動ロードを無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB 接続は分析処理で使用します。prices_daily / raw_financials / raw_news テーブルが前提です。
- テスト時は OpenAI 呼び出し関数をモックする設計になっています（_call_openai_api を patch 可能）。
- monitoring_db.init_monitoring_db(conn) は冪等で必要なカラムがなければマイグレーション（列追加）を行います。

よくある質問（FAQ）
------------------
Q. Paper Trading と本番の DB は混ざりませんか？  
A. paper_trading モードでは Settings.paper_sqlite_path を使い本番の monitoring DB とは分離されます。run_execution は settings.is_paper をチェックして適切な sqlite を開きます。

Q. MONITOR_POLL_INTERVAL の単位は？  
A. 秒です。0 以下や不正値は無視され、デフォルト 60 秒が使われます。

Q. OpenAI API のキーはどこに置く？  
A. 環境変数 OPENAI_API_KEY か、関数呼び出し時に api_key 引数で渡します。

貢献・ライセンス
----------------
- この README はコードの現状に基づく簡潔な導入です。各モジュールには docstring と注釈があり、詳細な設計やアルゴリズムはソース内コメントを参照してください。  
- ライセンス・貢献手順はリポジトリのルート（LICENSE / CONTRIBUTING 等）を参照してください（本リポジトリに含まれている場合）。

付録: 例 .env（参考）
-------------------
# KabuSys example .env
KABUSYS_ENV=development
LOG_LEVEL=INFO
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
JQUANTS_REFRESH_TOKEN=your_jquants_token_here
KABU_API_PASSWORD=your_kabu_password_here
OPENAI_API_KEY=sk-...

以上。README の内容で不明点や追加したい項目（例: 実行例コマンドの拡張、環境別設定例、依存関係ファイルの生成方法など）があれば指示をください。