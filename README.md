# KabuSys — 日本株自動売買システム (README)

このリポジトリは日本株自動売買システム「KabuSys」のコアライブラリ群です。ポートフォリオ構築、注文管理、監視、Paper Trading の検証、LLM を用いたニュースセンチメント / レジーム判定などの機能を含みます。

以下はコードベースを参照して作成した README です。

目次
- プロジェクト概要
- 主な機能一覧
- セットアップ手順
- 基本的な使い方（実行例）
- 環境変数（主要な設定）
- ディレクトリ構成（主要ファイルの説明）
- 補足（注意事項）

---

## プロジェクト概要
KabuSys は以下を目的としたコンポーネント群です。

- 研究（ファクター計算 / 特徴量解析）用の DuckDB ベースの処理
- ポートフォリオ構築（候補選定・重み算出・株数決定）
- 注文管理（OrderState マシン、ブローカー抽象化、再起動時のリコンシリエーション）
- 実行エンジン（ExecutionEngine）と監視コンポーネント（MonitoringEngine）
- Paper Trading 向けの分離された SQLite DB と検証レポート
- ニュースを LLM でスコアリングする AI モジュール（OpenAI）
- 監視ダッシュボード（Streamlit）と LINE によるアラート通知

設計方針として、ルックアヘッドバイアス回避、DB への冪等な書き込み、フェイルセーフ（API失敗時のフォールバック）などに配慮しています。

---

## 主な機能一覧
- portfolio: 候補選定（select_candidates）、重み付け（equal / score）、ポジションサイズ計算（risk_based 等）
- research: ファクター（momentum / volatility / value）計算、将来リターン、IC 計算
- execution:
  - 注文作成・送信・同期を担当する OrderManager、OrderRepository、Reconciler 等
  - Broker クライアントは環境に応じて切替可能（paper_trading では Mock）
- monitoring:
  - SystemMonitor（CPU/メモリ/ディスク/プロセス/データ鮮度監視）
  - TradeMonitor（滞留注文、約定異常）
  - RiskMonitor（ドローダウン・ポジション上限）
  - KillSwitch（フラグファイルで ExecutionEngine 停止）
  - AlertManager（LINE Push）
  - Streamlit ダッシュボード
- ai:
  - news_nlp.score_news: OpenAI を用いたニュースセンチメント集計 → ai_scores に書込
  - regime_detector.score_regime: MA + マクロニュースで市場レジーム判定 → market_regime に書込
- tools:
  - paper_verification_report: Paper Trading DB を解析して PASS/FAIL レポートを標準出力に出力

---

## セットアップ手順

前提
- Python 3.10+ を推奨（型注釈や未来の構文を広く利用）
- SQLite は標準で利用可能
- DuckDB を利用（ローカルファイル data/kabusys.duckdb を想定）
- ネットワークアクセスが必要な機能（OpenAI、LINE）あり

1. 仮想環境の作成（任意）
   - Unix/macOS:
     - python -m venv .venv
     - source .venv/bin/activate
   - Windows:
     - python -m venv .venv
     - .\.venv\Scripts\activate

2. 依存パッケージをインストール
   - 例（必要な最低限のパッケージ）:
     - pip install duckdb psutil openai requests streamlit
   - 実際のプロジェクトでは requirements.txt を用意している想定です:
     - pip install -r requirements.txt

3. プロジェクトルートに .env を配置（任意）
   - Settings モジュールはプロジェクトルート（.git または pyproject.toml が存在するディレクトリ）を探索して `.env` / `.env.local` を自動ロードします。
   - 自動ロードを無効化する場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

4. データディレクトリ（例）
   - data/ 以下に DB 等が作られます（デフォルト: data/kabusys.duckdb, data/monitoring.db, data/paper_trading.db 等）
   - 実行スクリプトは必要に応じて DB を初期化します（init_monitoring_db を呼ぶため監視テーブルは自動で作成されます）。

---

## 環境変数（主要なもの）

- KABUSYS_ENV: 起動環境（development | paper_trading | live）。デフォルト: development
- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
- KABU_API_PASSWORD: kabuステーション API 用（必須）
- OPENAI_API_KEY: OpenAI 呼び出しに必要（ai.news_nlp / ai.regime_detector）
- LINE_CHANNEL_ACCESS_TOKEN: LINE Push 用（AlertManager）
- LINE_USER_ID: LINE Push 送信先ユーザ ID
- DUCKDB_PATH: DuckDB ファイル（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: Monitoring 用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 専用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: Paper Trading の約定モード（instant | partial | never | reject）
- PID_FILE_PATH: ExecutionEngine の PID ファイル（デフォルト: data/execution.pid）
- KILL_FLAG_PATH: KillSwitch のフラグファイル（デフォルト: data/kill.flag）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト: 60）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）

Settings クラス（kabusys.config.Settings）が上記環境変数を読み取ります。必須変数が未設定だと ValueError を投げます。

読み込み優先順: OS 環境変数 > .env.local > .env

---

## 基本的な使い方（実行例）

- 監視ループ（Monitoring）
  - 意図: SystemMonitor を起動して定期モニタリングを行う
  - 実行:
    - Unix/macOS:
      - export MONITOR_POLL_INTERVAL=30
      - python -m kabusys.run_monitoring
    - Windows (PowerShell):
      - $env:MONITOR_POLL_INTERVAL="30"; python -m kabusys.run_monitoring
  - 補足:
    - MONITOR_POLL_INTERVAL が 1 未満（または不正）ならデフォルト 60 秒にフォールバックします。
    - run_monitoring は Settings で指定された sqlite_path を使って監視ログを永続化します（環境にかかわらず本番 sqlite_path を使用）。

- 実行エンジン（ExecutionEngine）
  - Paper Trading（モックブローカー）で実行（DB は data/paper_trading.db に分離）
    - Unix/macOS:
      - export KABUSYS_ENV=paper_trading
      - python -m kabusys.run_execution
  - Live/Development は KABUSYS_ENV をそれぞれ指定して実行します。
  - 実行開始時にプロセス優先度を上げる処理が行われます（psutil 必須）。

- Paper Trading 検証レポート（ツール）
  - 使い方:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - オプション:
    - --db PATH: PAPER_TRADING_SQLITE_PATH を指定する代わりに使えます

- Streamlit ダッシュボード（監視 UI）
  - 実行:
    - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

- AI 系（プログラムから呼ぶ例）
  - news_nlp.score_news(conn, target_date, api_key=None)
    - DuckDB 接続を渡し、target_date に対してニューススコアを ai_scores テーブルへ書き込みます。
    - api_key が None の場合は環境変数 OPENAI_API_KEY を参照します。
  - regime_detector.score_regime(conn, target_date, api_key=None)
    - MA200 とマクロニュースの LLM スコアを合成して market_regime に書き込みます。

---

## ディレクトリ構成（主要ファイルと説明）

（パスは src/kabusys/ 以下を想定）

- __init__.py
  - パッケージエクスポート設定（version 等）
- config.py
  - Settings クラス: 環境変数/.env の読み込み・検証を行う
- run_monitoring.py
  - SystemMonitor のポーリングループ起動スクリプト
- run_execution.py
  - ExecutionEngine 起動スクリプト（paper_trading 時は MockBroker を使用）
- portfolio/
  - portfolio_builder.py: 候補選定（select_candidates）・重み計算（equal/score）
  - position_sizing.py: 株数計算・利用キャッシュ制約・単元丸め
  - risk_adjustment.py: セクターキャップ・レジーム乗数
- research/
  - factor_research.py: momentum / volatility / value の計算（DuckDB）
  - feature_exploration.py: 将来リターン・IC・統計サマリ
- ai/
  - news_nlp.py: raw_news を OpenAI で解析し ai_scores に書込
  - regime_detector.py: マクロニュース + MA200 でレジーム判定
- monitoring/
  - monitoring_db.py: SQLite 監視テーブルの初期化と CRUD（MonitoringDB）
  - system_monitor.py: CPU/メモリ/プロセス/データ鮮度監視
  - trade_monitor.py: 注文滞留・約定異常監視
  - risk_monitor.py: ドローダウン・ポジション上限監視
  - kill_switch.py: kill.flag を書き込むロジック
  - alert_manager.py: LINE Push 通知（クールダウン管理）
  - monitoring_engine.py: 各 Monitor を束ねる高レベル実行器
  - streamlit_dashboard.py: Streamlit ベースの簡易ダッシュボード（起動用スクリプト）
- execution/
  - order_manager.py: 注文の作成/送信/同期ロジック
  - reconciler.py: 起動時の注文・ポジション整合処理
  - （他: broker_factory, order_repository 等はコード内に存在）
- tools/
  - paper_verification_report.py: Paper Trading DB 用の検証レポート生成ツール
- utils/
  - process_priority.py: プロセス優先度設定・CPU affinity ヘルパ

---

## 補足（運用上の注意）
- Paper Trading と本番 DB は分離されています（PAPER_TRADING_SQLITE_PATH を使用）。
- OpenAI 呼び出しには API キーが必須。ネットワークや API の一時失敗に対しリトライやフォールバックが組まれていますが、API コストやレート制限に注意してください。
- run_monitoring / run_execution はプロセス優先度変更（psutil）を試みます。権限不足や未対応 OS の場合はログ警告を出してスキップします。
- KillSwitch はフラグファイル (KILL_FLAG_PATH) を書き込んで ExecutionEngine に停止指示を出します。運用時に意図せぬフラグの存在がないか確認してください。
- .env のパースはシェル風のルール（export / quoted values / inline comments 等）に対応していますが、特殊な書式は期待どおりに解釈されない可能性があります。

---

必要があれば、README に含めるコマンドの具体例（systemd / supervisord のユニット例、Dockerfile のサンプル、requirements.txt の推定内容）や、各モジュールのより詳細な使用例（関数シグネチャと戻り値の例）を追記します。どの情報を追加したいか教えてください。