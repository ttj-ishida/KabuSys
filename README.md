# KabuSys

日本株向け自動売買システム（モジュール断片のREADME）。本リポジトリは取引実行、監視、ポートフォリオ構築、研究、AI（ニュースセンチメント／レジーム判定）などを含むモジュール群で構成されています。

以下はプロジェクトの概要、機能、セットアップ、実行方法、ディレクトリ構成のまとめです。

---

## プロジェクト概要

KabuSys は日本株の自動売買に関する以下の機能群を備えた Python モジュール群です（代表的な実装ファイルを含む）:

- 注文作成・送信・状態管理（OrderManager / Reconciler）
- 実行エンジン（ExecutionEngine 起動スクリプト）
- 監視（SystemMonitor / TradeMonitor / RiskMonitor / MonitoringEngine）
- 監視データの永続化（SQLite via MonitoringDB）
- ポートフォリオ構築（候補選定、重み計算、ポジションサイジング、セクター制限）
- 研究用ファクター計算（DuckDB を用いたファクター群）
- ニュース NLP によるセンチメントスコアリング（OpenAI API）
- マーケットレジーム判定（MA200 + マクロニュース + LLM）
- Paper Trading 向け検証レポート生成ツール
- Streamlit ダッシュボード（監視データの可視化）

設計方針として、データ参照（DuckDB / SQLite）と取引 API 呼び出しの分離、ルックアヘッドバイアス対策、フェイルセーフ（API失敗等のフォールバック）を重視しています。

---

## 主な機能一覧

- Execution（実行）
  - run_execution.py：ExecutionEngine のエントリーポイント。`KABUSYS_ENV=paper_trading` 時は MockBroker を使用し、paper_trading DB に完全分離して動作します。
  - Reconciler：再起動後の注文 / ポジション整合処理

- Monitoring（監視）
  - run_monitoring.py：SystemMonitor のポーリングループ起動スクリプト（デフォルト60秒間隔、MONITOR_POLL_INTERVAL で上書き可）
  - SystemMonitor：CPU/メモリ/ディスク/プロセス存続/データ鮮度チェック
  - TradeMonitor：滞留注文、約定異常（価格偏差）検出
  - RiskMonitor：ドローダウン監視、ポジション上限監視
  - KillSwitch：フラグファイル（data/kill.flag）による ExecutionEngine 停止シグナル
  - AlertManager：LINE Messaging API へのプッシュ通知（クールダウン管理）
  - MonitoringDB：SQLite に対するテーブル作成・読み書きラッパー
  - streamlit_dashboard.py：Streamlit で監視ダッシュボードを表示

- Portfolio（配分・ポジション決定）
  - 候補選定（スコア/ランク基準）
  - 重み計算（等金額／スコア加重）
  - セクターキャップ適用
  - ポジションサイズ算出（リスクベース、単元丸め、投下上限、コストバッファ）

- Research（研究）
  - ファクター計算（モメンタム・ボラティリティ・バリュー 等）
  - 将来リターン計算、IC 計算、統計サマリ

- AI（LLM）
  - news_nlp.score_news：raw_news を集約して OpenAI に投げ、銘柄別センチメントを ai_scores に書き込む
  - regime_detector.score_regime：ETF の MA200 とマクロニュースの LLM 評価を合成して market_regime を計算・永続化

- Tools
  - paper_verification_report.py：Paper Trading DB（data/paper_trading.db）から検証レポートを生成（稼働率、成功率、レイテンシ等の判定）

---

## セットアップ手順

前提：
- Python 3.10+ を推奨（標準ライブラリに sqlite3 を使用）
- システムにより追加の権限が必要（プロセス優先度設定など）

1. リポジトリをクローン・移動
   - git clone ... && cd <repo>

2. 仮想環境（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 必要パッケージをインストール
   - pip install duckdb psutil openai requests streamlit
   - （プロジェクトに requirements.txt があれば `pip install -r requirements.txt`）

4. 環境変数の準備
   - プロジェクトルートに .env / .env.local を置くと自動で読み込まれます（OS 環境変数が優先）。
   - 自動ロードを無効化する場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

5. 主要な環境変数（例）
   - JQUANTS_REFRESH_TOKEN=...
   - KABU_API_PASSWORD=...
   - OPENAI_API_KEY=...  （AI 機能を使う場合必須）
   - KABUSYS_ENV=development|paper_trading|live  （デフォルト: development）
   - DUCKDB_PATH=data/kabusys.duckdb
   - SQLITE_PATH=data/monitoring.db
   - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
   - PAPER_FILL_MODE=instant|partial|never|reject
   - PID_FILE_PATH=data/execution.pid
   - KILL_FLAG_PATH=data/kill.flag
   - MONITOR_POLL_INTERVAL=60  （run_monitoring のポーリング間隔（秒））
   - LINE_CHANNEL_ACCESS_TOKEN=...  （通知用）
   - LINE_USER_ID=...  （通知先）

6. データディレクトリの作成（必要時）
   - mkdir -p data

注意:
- run_monitoring は「監視」用 DB（SQLITE_PATH）を使用します。監視は KABUSYS_ENV に関係なく本番 sqlite_path を使用する設計になっています（監視データは常に同一の DB に残すため）。
- run_execution は KABUSYS_ENV=paper_trading の場合、paper_trading 用の SQLite（PAPER_TRADING_SQLITE_PATH）を使用して本番 DB と分離します。

---

## 使い方

いくつかの代表的な起動・利用方法を示します。

1. 監視（SystemMonitor のポーリングループ）
   - デフォルト: ポーリング間隔 60 秒（MONITOR_POLL_INTERVAL で上書き可）
   - 実行:
     - python src/kabusys/run_monitoring.py
     - または環境変数を指定して: MONITOR_POLL_INTERVAL=30 python src/kabusys/run_monitoring.py
   - 注意:
     - 実行時にプロセス優先度を high に変更しようとします（set_process_priority）。権限により警告が出ることがあります。

2. 実行（ExecutionEngine）
   - 本番モード:
     - export KABUSYS_ENV=live
     - python src/kabusys/run_execution.py
   - Paper Trading（モックブローカー & 分離 DB）:
     - export KABUSYS_ENV=paper_trading
     - python src/kabusys/run_execution.py
   - 起動フロー:
     - Broker クライアント生成 → OrderRepository 等の組み立て → ExecutionEngine.run_session()

3. Streamlit ダッシュボード（監視可視化）
   - 起動:
     - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
   - 既存の monitoring DB を read-only で開き、Overview / Positions / Orders / System を表示します。

4. Paper Trading 検証レポート
   - python -m kabusys.tools.paper_verification_report
   - 期間指定例:
     - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
   - DB 指定:
     - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

5. AI（ニューススコアリング / レジーム判定）
   - 必須: OPENAI_API_KEY を環境変数または引数で指定
   - モジュール関数例:
     - kabusys.ai.score_news(conn, target_date, api_key=None)
     - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
   - 実行前に DuckDB に必要なテーブル（raw_news, news_symbols, ai_scores, prices_daily, market_regime 等）を用意してください。

6. その他ユーティリティ
   - set_process_priority(level): utils/process_priority によりプロセス優先度を OS 関係なく設定します（Windows / POSIX に対応）。失敗した場合は警告でスキップします。

---

## 環境変数一覧（主要）

- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、デフォルト 60）
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 1 にすると .env 自動読み込みを無効化
- SQLITE_PATH: 監視 DB（data/monitoring.db デフォルト）
- DUCKDB_PATH: DuckDB ファイル（data/kabusys.duckdb デフォルト）
- PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（data/paper_trading.db デフォルト）
- PAPER_FILL_MODE: instant | partial | never | reject（paper trading の fill 動作）
- OPENAI_API_KEY: OpenAI API キー（AI 機能で必須）
- JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD: 各種外部 API トークン/パスワード
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: アラート送信用

---

## ディレクトリ構成（抜粋）

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数の自動ロード（.env/.env.local）、Settings クラス
  - run_monitoring.py
    - SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py
    - ExecutionEngine 起動スクリプト（paper_trading モードで MockBroker）
  - tools/
    - paper_verification_report.py
  - monitoring/
    - monitoring_db.py         — MonitoringDB（SQLite テーブル作成・読み書き）
    - system_monitor.py        — CPU/メモリ/ディスク/プロセス/データ鮮度チェック
    - trade_monitor.py         — 滞留注文 / 約定異常検出
    - risk_monitor.py          — ドローダウン / ポジション上限監視
    - kill_switch.py           — kill.flag による Execution 停止トリガ
    - alert_manager.py         — LINE 送信ラッパー（クールダウン）
    - monitoring_engine.py     — 各 Monitor を結合してポーリングするエンジン
    - streamlit_dashboard.py   — Streamlit ダッシュボード
  - execution/
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - ...（broker インターフェース等）
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
  - utils/
    - process_priority.py

（上は主要ファイルの抜粋です。実際のリポジトリにはさらに多くのモジュール／ファイルが含まれます。）

---

## 運用上の注意事項

- 監視（run_monitoring）は常に本番の sqlite_path（SQLITE_PATH）を使う設計です。paper_trading を用いる場合でも監視 DB は同一を使う点に注意してください。
- run_execution が paper_trading の場合は PAPER_TRADING_SQLITE_PATH を使い、本番 DB と分離します。
- OpenAI を呼ぶ処理は外部 API に依存するため、API 失敗時はフォールバック（0.0 など）する実装が多く含まれています。API キー漏洩に注意してください。
- PID ファイル（PID_FILE_PATH）を用いて実行プロセスの生存確認／stale PID 検出を行います。ファイルの配置および実行権限に注意してください。
- set_process_priority によりプロセスの優先度を上げようとしますが、OS 権限により失敗することがあります（警告ログのみ）。

---

## 参考コマンドまとめ

- 監視起動:
  - MONITOR_POLL_INTERVAL=30 python src/kabusys/run_monitoring.py
- 実行（paper_trading）:
  - export KABUSYS_ENV=paper_trading
  - python src/kabusys/run_execution.py
- Streamlit ダッシュボード:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
- Paper Trading レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- AI スコアリング（ライブラリ関数を直接呼ぶ／スクリプト化して利用）:
  - kabusys.ai.score_news(conn, target_date, api_key=OPENAI_API_KEY)

---

この README はリポジトリ内のソースコード（主要ファイル）を基に作成しました。実際のデプロイ／運用時は各種設定（.env、DB 構成、Broker 実装、権限など）を適切に準備してください。不明点があればソースコードの該当ファイル（config.py / monitoring/* / execution/* / ai/*）を参照してください。