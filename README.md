# KabuSys

日本株自動売買システムの一部コンポーネント群（モニタリング、Execution 起動スクリプト、ポートフォリオ構築、リサーチ、AI 補助機能 等）。

以下はこのコードベースの README (日本語) です。

---

目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 環境変数 / 設定
- 使い方（実行例）
- ディレクトリ構成
- 注意事項 / 補足

---

プロジェクト概要
- KabuSys は日本株の自動売買に関連するコンポーネント群の実装です。
- 本リポジトリには、実行エンジン起動スクリプト、監視（Monitoring）機能、ポートフォリオ構築ロジック、ファクター計算・リサーチモジュール、AI（ニュース NLP / レジーム判定）統合、Paper Trading 検証ツール、監視ダッシュボード（Streamlit）などが含まれます。
- DB 層は SQLite（監視ログ・注文ログ）と DuckDB（時系列ファクター計算・リサーチ用）を組み合わせて使用します。

---

主な機能一覧
- run_execution.py: ExecutionEngine 起動スクリプト（本番 / Paper Trading 切替対応）
  - KABUSYS_ENV=paper_trading のときは MockBrokerClient を利用し、paper_trading 用 SQLite に記録して本番 DB と分離
  - リスク管理（RiskManager）、発注管理（OrderManager）、リコンシリエーション（Reconciler）を組み合わせてセッション実行
- run_monitoring.py: SystemMonitor のポーリングループ起動スクリプト
  - MONITOR_POLL_INTERVAL によるポーリング間隔上書き
  - 監視ログは常に本番 sqlite_path を使用
- monitoring パッケージ:
  - SystemMonitor: プロセス・リソース・データ鮮度の監視
  - TradeMonitor: 注文滞留・約定異常の検出
  - RiskMonitor: ドローダウン・ポジション上限監視
  - KillSwitch: フラグファイルを用いた ExecutionEngine 停止シグナル
  - AlertManager: LINE Messaging API によるアラート（push）
  - MonitoringDB: SQLite テーブル（system_status / trade_logs / positions / risk_logs / dashboard）の初期化・読み書き
  - streamlit_dashboard: Streamlit ベースの監視ダッシュボード
- portfolio パッケージ:
  - 候補選定、重み計算（等配分・スコア加重）、ポジションサイズ計算、セクターキャップ、レジーム乗数など
- research パッケージ:
  - ファクター計算（momentum, volatility, value）、将来リターン、IC 計算、統計サマリ等（DuckDB を用いた計算）
- ai パッケージ:
  - news_nlp: OpenAI を使ったニュースセンチメント集約・ai_scores 書き込み
  - regime_detector: ETF（1321）MA200 とマクロニュースの LLMセンチメントを合成して市場レジーム判定・market_regime テーブルへ書き込み
- tools:
  - paper_verification_report: Paper Trading DB の検証レポート生成（稼働率、注文成功率、レイテンシ等）
- utils:
  - process_priority: クロスプラットフォームなプロセス優先度 / CPU affinity 設定ユーティリティ

---

セットアップ手順（ローカル開発向け）
1. Python 環境
   - Python 3.10+ を推奨（typing, match 機能などの互換性）
2. 依存パッケージ（例）
   - duckdb
   - psutil
   - requests
   - openai
   - streamlit (ダッシュボードを使う場合)
   - （仮想環境を使うことを推奨）
   例:
     pip install duckdb psutil requests openai streamlit
   ※ 実プロジェクトでは requirements.txt / poetry 等で依存管理してください。
3. プロジェクトルートに .env を置く（任意）
   - config モジュールはプロジェクトルートを .git または pyproject.toml で探索して .env / .env.local を自動読み込みします（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
4. データディレクトリ
   - デフォルトの DB / pid / flag 等は data/ 以下に保存されます。必要に応じてディレクトリを作成してください。
     mkdir -p data

---

環境変数 / 設定（主要なもの）
- KABUSYS_ENV: 起動環境（development / paper_trading / live）。デフォルト: development
- SQLITE_PATH: 監視 DB（monitoring）パス。デフォルト: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（paper_trading 環境で使用）。デフォルト: data/paper_trading.db
- DUCKDB_PATH: DuckDB ファイルパス。デフォルト: data/kabusys.duckdb
- PID_FILE_PATH: ExecutionEngine の PID ファイルパス。デフォルト: data/execution.pid
- KILL_FLAG_PATH: kill.flag のパス。デフォルト: data/kill.flag
- KILL_FLAG_CLEAR_ON_START: Execution 起動時に kill.flag を自動クリアする場合は "1"
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）。デフォルト: INFO
- JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD: 各種外部 API 用必須トークン（Settings で必須化）
- OPENAI_API_KEY: AI 機能（news_nlp, regime_detector）を使う際に必要
- PAPER_FILL_MODE: Paper Trading の Mock ブローカーの約定モード（instant|partial|never|reject）。デフォルト: instant
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒）。デフォルト: 60（0 以下は無効扱いでデフォルトにフォールバック）

例 (.env)
  KABUSYS_ENV=paper_trading
  SQLITE_PATH=data/monitoring.db
  PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
  DUCKDB_PATH=data/kabusys.duckdb
  OPENAI_API_KEY=sk-...
  LOG_LEVEL=INFO

---

使い方（代表的な実行例）
- 実行時にはプロセス優先度を high に設定するユーティリティが呼ばれます（psutil による設定。権限や OS により無効化されることがあります）。

1) ExecutionEngine を起動する（本番 / Paper Trading）
- Python モジュールとして（パッケージとしてインストール済みを想定）:
    python -m kabusys.run_execution
- 直接スクリプトを実行する場合:
    python src/kabusys/run_execution.py
- Paper Trading（環境切替）:
    export KABUSYS_ENV=paper_trading
    python -m kabusys.run_execution
  ※ paper_trading の場合は PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に記録され、本番 DB と分離されます。

2) SystemMonitor のポーリングループを起動する
    python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で変更できます（例: export MONITOR_POLL_INTERVAL=30）。
  - 監視は常に Settings.sqlite_path（本番 sqlite）を使用します（環境にかかわらず）。

3) Streamlit 監視ダッシュボードを起動
    streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - DB は読み取り専用で開かれます。MonitoringEngine を先に起動してデータを作成してください。

4) Paper Trading 検証レポート生成
    python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - デフォルト DB: data/paper_trading.db。--db オプションで別ファイルを指定できます。
  - レポートは標準出力へ表示（稼働率、注文成功率、レイテンシ等を表示）。

5) AI 機能（ニュース NLP / レジーム判定）
- OpenAI API キーが必要です（OPENAI_API_KEY または関数呼び出し時に渡す）。
- news_nlp.score_news / regime_detector.score_regime を呼び出すことで DuckDB 上の raw_news 等を解析して結果を書き込みます。
  - 例（Python から）:
      from kabusys.ai.news_nlp import score_news
      score_news(duckdb_conn, target_date=date(2026,4,1), api_key="sk-...")
  - API 呼び出しはリトライやエラー時のフェイルセーフ処理が入っていますが、API 制限やキー設定には注意してください。

---

ディレクトリ構成（抜粋）
- src/kabusys/
  - __init__.py
  - config.py                      — 環境変数/.env の読み込みと Settings 定義
  - run_execution.py               — ExecutionEngine 起動スクリプト
  - run_monitoring.py              — SystemMonitor ポーリング起動スクリプト
  - utils/
    - process_priority.py          — プロセス優先度 / CPU affinity ユーティリティ
  - monitoring/
    - __init__.py
    - monitoring_db.py             — SQLite テーブル作成・永続化 API
    - system_monitor.py            — CPU/MEM/DISK / プロセス / データ鮮度監視
    - trade_monitor.py             — 滞留注文・約定異常検出
    - risk_monitor.py              — ドローダウン・ポジション上限監視
    - kill_switch.py               — kill.flag の書き込み/評価
    - alert_manager.py             — LINE push 通知管理
    - monitoring_engine.py         — 複数モニタの束ね・ポーリング
    - streamlit_dashboard.py       — Streamlit ダッシュボード
  - execution/
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - ... (broker_factory 等、ExecutionEngine 関連)
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
  - data/ (期待されるデータファイル / DB が置かれる場所（手動作成）)
    - kabusys.duckdb (デフォルト DUCKDB_PATH)
    - monitoring.db (デフォルト SQLITE_PATH)
    - paper_trading.db (Paper Trading 用 DB)

---

注意事項 / 補足
- .env の自動ロード:
  - config.py はプロジェクトルートを .git または pyproject.toml で探索し、.env（次に .env.local）を自動読み込みします。OS 環境変数が優先され、.env.local は上書きオプションです。
  - 自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DB マイグレーション:
  - init_monitoring_db はテーブルを冪等に作成します。既存スキーマに足りないカラムがある場合、簡単な ALTER を行うことがあります（例: latency_ms, peak_value）。
- 権限・環境差:
  - process_priority の設定は OS（Windows / POSIX）と権限に依存します。失敗時は警告が出て処理は継続されます。
- Paper Trading:
  - Paper Trading モードは本番 DB と分離される設計です（PAPER_TRADING_SQLITE_PATH を使用）。PAPER_FILL_MODE により約定動作をエミュレートできます。
- OpenAI の使用:
  - API キーは厳重に管理してください。AI 機能はネットワーク呼び出しのため、料金や利用制限にご注意ください。
- ログレベル:
  - LOG_LEVEL または logging.basicConfig の設定により出力レベルを調整できます。

---

問題報告 / 貢献
- バグや改善案があれば issue を作成してください。設計思想や外部 API の取り扱いに関しては README に追記していきます。

---

以上がこのコードベースの README（日本語要約）です。必要であれば、具体的なコマンド例（systemd ユニットファイル、Dockerfile、CI 設定）や詳細な環境変数一覧・サンプル .env を追加で作成します。どの情報を優先して追記しましょうか？