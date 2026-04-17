# KabuSys

KabuSys は日本株の自動売買・研究・監視を目的とした小規模な統合ライブラリです。  
このリポジトリには、注文発行・リコンシリエーション・リスク管理・監視ダッシュボード・ファクター計算・ニュース NLP（OpenAI）連携などのコンポーネントが含まれます。

以下はコードベースから抜粋した README（日本語）です。

---

目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 使い方（起動例）
- 環境変数一覧（主要）
- 停止フラグ / PID
- ディレクトリ構成（主要ファイル説明）

---

## プロジェクト概要

KabuSys は以下の目的を持つ Python パッケージです。

- 注文発行と状態管理（Execution Engine / OrderManager）
- 起動時の自動リコンシリエーション（Reconciler）
- リスク管理（ドローダウン監視・ポジション上限など）
- システム状態・注文ログの監視（MonitoringEngine、SystemMonitor、TradeMonitor、RiskMonitor）
- 監視結果の永続化（SQLite）と可視化（Streamlit dashboard）
- ポートフォリオ構築・ウェイト計算・ポジションサイジング（portfolio モジュール）
- DuckDB を用いたファクター計算・リサーチ（research モジュール）
- ニュースの LLM（OpenAI）によるセンチメント評価・市場レジーム判定（ai モジュール）
- Paper Trading（モックブローカー）に対応した分離 DB 運用

設計方針の一部：
- DB（監視用・Paper Trading 用）はファイルベース（SQLite / DuckDB）
- 外部 API への呼び出し（ブローカー / OpenAI 等）は抽象化され、テスト差し替えが可能
- ルックアヘッドバイアス防止のため、日付参照は明示的に渡す設計

---

## 機能一覧

主な機能（抜粋）:

- Execution
  - OrderManager: 注文作成／送信・状態同期 API
  - Reconciler: 起動時の注文・ポジション突合
  - RiskManager（設定に基づくリスクチェック）
- Monitoring
  - SystemMonitor: CPU / メモリ / ディスク / プロセス状態 / データ鮮度監視
  - TradeMonitor: 滞留注文・約定価格異常検出
  - RiskMonitor: ドローダウン・ポジション上限監視
  - MonitoringEngine: 各 Monitor をまとめてポーリング、KillSwitch 評価、Alert 発行
  - MonitoringDB: SQLite に監視・ログを書き込む層
  - Streamlit ダッシュボード：監視 DB を可視化
  - AlertManager: LINE push によるアラート送信
- Portfolio
  - 候補選定、等金額・スコア加重ウェイト、リスク調整（セクターキャップ / レジーム乗数）、ポジションサイジング
- Research
  - ファクター計算（Momentum / Volatility / Value）
  - 将来リターン計算、IC 計算、ファクター統計サマリ
- AI
  - news_nlp: raw_news を集合し OpenAI で銘柄別センチメントを取得して ai_scores に書き込む
  - regime_detector: ma200 とマクロニュースセンチメントを合成して市場レジームを判定
- Tools
  - paper_verification_report: Paper Trading DB から検証レポートを生成

---

## セットアップ手順

1. 必要な Python（推奨 3.10+）を用意します。

2. 仮想環境を作成して有効化（任意）:
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール。requirements ファイルは同梱されていないため、主要なライブラリを手動でインストールしてください（プロジェクトで使われているもの）:

   pip install duckdb psutil openai requests streamlit

   SQLite は標準ライブラリに含まれます。

4. 環境変数設定:
   - プロジェクトルートに .env ファイルを配置すると自動で読み込まれます（.env.local は上書き）。
   - 自動読み込みを無効にする場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

5. データディレクトリ作成（必要に応じて）:

   mkdir -p data

6. 必須の DB 初期化は各起動スクリプトが行います（init_monitoring_db が呼ばれます）。DuckDB の schema は research / data pipeline 側で別途準備してください。

---

## 使い方（起動例）

基本的な起動コマンド例は以下の通りです。

- 監視ループ起動（Monitoring）
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）。
  - 実行:

    KABUSYS_ENV=development python -m kabusys.run_monitoring

  - 監視は常に本番（settings.sqlite_path）を参照して監視 DB に書き込みます（環境に依存せず本番 DB を使用する設計）。

- Execution Engine 起動
  - Paper Trading（モックブローカー）を使う場合:

    KABUSYS_ENV=paper_trading python -m kabusys.run_execution

    この場合、Paper Trading 用 SQLite DB（デフォルト: data/paper_trading.db）を使用して発注記録を完全に分離します。

  - Live（本番）:

    KABUSYS_ENV=live python -m kabusys.run_execution

  - 起動中は data/execution.pid に PID を書きます。停止は data/stop_requested.flag を作成すると検知して終了します（run_execution も同様に停止フラグを監視）。

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - または DB 指定:

    python -m kabusys.tools.paper_verification_report --db data/paper_trading.db

- Streamlit ダッシュボード（監視 DB を可視化）
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

- AI モジュール（プログラムから）
  - news_nlp.score_news(conn, target_date, api_key=...) を呼んで ai_scores を更新
  - regime_detector.score_regime(conn, target_date, api_key=...) を呼んで market_regime を更新

  これらは DuckDB 接続を受け取る設計なので、スクリプトやバッチジョブから呼び出して運用できます。

---

## 主な環境変数（抜粋）

config.Settings で参照される主な環境変数（必須・任意）:

必須（使用する機能により必要）:
- JQUANTS_REFRESH_TOKEN — J-Quants API のリフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API パスワード
- OPENAI_API_KEY — OpenAI を使う場合に必要（news_nlp / regime_detector）

任意 / デフォルトあり:
- KABU_API_BASE_URL — kabusapi のベース URL（デフォルト http://localhost:18080/kabusapi）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — AlertManager（LINE 通知）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — Paper Trading 用 SQLite（デフォルト data/paper_trading.db）
- PAPER_FILL_MODE — paper broker の fill_mode（instant|partial|never|reject、デフォルト "instant"）
- PID_FILE_PATH — Execution PID ファイルパス（デフォルト data/execution.pid）
- KILL_FLAG_PATH — KillSwitch の flag ファイル path（デフォルト data/kill.flag）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を削除するフラグ（"1" で有効）
- CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT — 監視しきい値
- KABUSYS_ENV — 起動環境（development / paper_trading / live。デフォルト development）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...）

注意: Settings は .env / .env.local / OS 環境変数を自動で読み込みます（プロジェクトルートが特定できる場合）。.env の書式はシェル形式に準拠（クォート・コメント処理あり）。

---

## 停止フラグ / PID

- data/stop_requested.flag: run_monitoring/run_execution がループ内で定期的にチェックする停止フラグ。存在すると安全にループを終了します（人為的に作成して停止を指示可能）。
- data/execution.pid: ExecutionEngine 起動時に PID を書き込みます。SystemMonitor はこの PID を見てプロセスが生きているかを判定します。
- data/kill.flag: KillSwitch が条件に該当すると書き込む停止フラグ（Execution 停止要求）。KillSwitch は RiskMonitor のアラート（ドローダウン、ポジション上限）を元に判定します。

KillSwitch は冪等でファイルを上書きしません（既に存在すれば書き込まない）。

---

## ディレクトリ構成（主要ファイル）

src/kabusys/
- __init__.py — パッケージ定義、バージョン
- config.py — 環境変数 / 設定読み込みロジック（Settings）
- utils/
  - process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ
- monitoring/
  - monitoring_db.py — SQLite のスキーマ初期化と永続化 API（MonitoringDB）
  - system_monitor.py — CPU/メモリ/ディスク/データ鮮度 / Execution プロセス監視
  - trade_monitor.py — 注文滞留・約定価格異常検出
  - risk_monitor.py — ドローダウン / ポジション上限監視
  - kill_switch.py — kill.flag の管理
  - alert_manager.py — LINE 通知
  - monitoring_engine.py — 各 monitor を束ねるポーリング器
  - streamlit_dashboard.py — Streamlit ベースのダッシュボード
  - run_monitoring.py — 監視ループ起動スクリプト
- execution/
  - order_manager.py — 注文管理の外向き API
  - order_repository.py — DB 永続化（Orders）層（存在）
  - reconciler.py — 起動時リコンシリエーション
  - run_execution.py — Execution Engine 起動スクリプト
  - （その他: broker_factory, execution_engine, risk_manager 等）
- portfolio/
  - portfolio_builder.py — 候補選定・重み計算
  - position_sizing.py — 発注株数決定・丸め・aggregate cap
  - risk_adjustment.py — セクターキャップ・レジーム乗数
- research/
  - factor_research.py — Momentum/Volatility/Value 等のファクター計算（DuckDB）
  - feature_exploration.py — 将来リターン・IC・統計サマリ
- ai/
  - news_nlp.py — raw_news を OpenAI でスコアリングして ai_scores に書き込む
  - regime_detector.py — ma200 とマクロニュースを使ったレジーム判定
- tools/
  - paper_verification_report.py — Paper Trading DB から検証レポート生成ツール

（上記は主要ファイルの概要です。実際にはさらに細かい実装ファイルが存在します。）

---

## 運用上の注意

- Paper Trading と本番 DB は明示的に分離されています。KABUSYS_ENV=paper_trading を指定すると paper_sqlite_path を使います。
- モニタリングは production 側の monitoring DB に書き込みます（run_monitoring は環境に関係なく settings.sqlite_path を使用）。
- OpenAI 呼び出しには API キーが必要です。ネットワークエラー / 5xx / レート制限に対しては適切にリトライする実装がありますが、API 呼び出しのコストとレート制限に注意してください。
- process priority / CPU affinity の設定は OS に依存します。権限不足で設定に失敗した場合は警告を出してスキップします。
- DuckDB / SQLite のバージョン互換性に注意してください（executemany の挙動など、コメントに注意点を残しています）。

---

## よく使うコマンドまとめ

- 監視ループ起動:
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- Execution 起動 (paper):
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
- Paper 検証レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- Streamlit ダッシュボード:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

---

この README はコードベースの主要な使い方・設計の要点をまとめたものです。実運用や開発を行う際は、個々のモジュール（monitoring_db、news_nlp、regime_detector、order_manager など）の docstring を参照してください。必要なら起動スクリプトやツールの追加説明、サンプル .env.example を別途作成することをお勧めします。