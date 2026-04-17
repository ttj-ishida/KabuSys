KabuSys — 日本株自動売買システム
=================================

概要
----
KabuSys は日本株向けの自動売買 / 研究 / 監視を一貫して実行するための Python パッケージ群です。本コードベースは以下の主要機能を含みます。

- 注文発行・状態管理（ExecutionEngine, OrderManager, Reconciler 等）
- 監視（SystemMonitor / TradeMonitor / RiskMonitor / MonitoringEngine）
- ポートフォリオ構築（候補選定・重み付け・ポジションサイズ算出）
- 研究用ファクター計算（モメンタム、バリュー、ボラティリティ等）
- ニュース NLP（OpenAI を用いた記事センチメント評価）
- 市場レジーム判定（ETF MA + マクロセンチメントの混成スコア）
- Paper Trading（モックブローカーによる完全分離DBでの検証）
- レポート / ダッシュボード（paper_verification_report, Streamlit）

主な特徴
---------
- 明確に分離された環境（development / paper_trading / live）と DB パス設定
- DuckDB を用いた時系列・ファクタ集計（研究用途）
- SQLite を用いた監視ログ / 注文ログ（永続化）
- OpenAI（gpt-4o-mini）を使ったニュースセンチメントとレジーム判定（任意）
- LINE API によるアラート送信（AlertManager）
- フェイルセーフ：API リトライ、部分書き込み、データ不足時フォールバックなどを実装
- CLI/モジュール双方で利用できる作り（スクリプトは python -m で起動）

セットアップ
-----------

前提
- Python 3.10 以上推奨（型アノテーションで | 演算子を使用）
- OS: Linux / macOS / Windows（プロセス優先度や CPU affinity はプラットフォーム依存動作）

1. リポジトリをクローンして仮想環境を作成
   - 例:
     - git clone <repo>
     - cd <repo>
     - python -m venv .venv
     - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージをインストール
   - 主要依存例:
     - duckdb
     - psutil
     - openai
     - requests
     - streamlit (ダッシュボード用)
   - 例:
     - pip install duckdb psutil openai requests streamlit

   （実際の requirements.txt がある場合は pip install -r requirements.txt を利用してください）

3. データディレクトリ作成
   - mkdir -p data

4. 環境変数設定 (.env を使用可能)
   - プロジェクトルートの .env / .env.local を自動読み込み（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）
   - 最低限設定が必要なキー:
     - JQUANTS_REFRESH_TOKEN — （必須）
     - KABU_API_PASSWORD — kabuステーション API パスワード（必須）
   - OpenAI 関連（必要に応じて）:
     - OPENAI_API_KEY
   - 他のオプション（デフォルトがあるものも）:
     - KABUSYS_ENV: development | paper_trading | live (デフォルト: development)
     - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
     - SQLITE_PATH (監視用; デフォルト: data/monitoring.db)
     - PAPER_TRADING_SQLITE_PATH (paper_trading 用 DB; デフォルト: data/paper_trading.db)
     - PAPER_FILL_MODE: instant | partial | never | reject (デフォルト: instant)
     - LOG_LEVEL (DEBUG/INFO/...)
     - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID （アラート送信用）
     - PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START, CPU/MEM/DISK 閾値など

使い方（起動例・ツール）
-----------------------

1. 監視ループを起動（Monitoring）
   - python -m kabusys.run_monitoring
   - 挙動:
     - Settings に基づき本番 sqlite_path（monitoring DB）を使用して監視テーブル（init_monitoring_db）を作成
     - SystemMonitor を定期実行（デフォルト 60 秒）
     - ポーリング間隔を環境変数で上書き: MONITOR_POLL_INTERVAL（秒、正の整数）
     - 停止はプロジェクトルートの data/stop_requested.flag を作成すると検知して終了

2. ExecutionEngine（発注エンジン）を起動
   - python -m kabusys.run_execution
   - 挙動:
     - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し data/paper_trading.db に記録（本番 DB と分離）
     - 実行中は data/execution.pid を作成（PID 管理）
     - 停止は data/stop_requested.flag を作成するか、外部から Engine.stop() を呼ぶ仕組み
     - 実行前に data/kill.flag があれば起動をスキップ（KillSwitch）

   - Paper trading の起動例:
     - KABUSYS_ENV=paper_trading python -m kabusys.run_execution

3. Streamlit ダッシュボード（監視情報閲覧）
   - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
   - ブラウザで監視ダッシュボードを表示（read-only 接続）

4. Paper Trading 検証レポート生成
   - python -m kabusys.tools.paper_verification_report
   - 期間指定:
     - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
   - DB 指定:
     - --db /path/to/paper_trading.db
   - デフォルト DB: data/paper_trading.db（PAPER_TRADING_SQLITE_PATH で上書き可）

5. AI（ニュース NLP / レジーム判定）
   - OpenAI API キーが必要（OPENAI_API_KEY または引数で指定）
   - kabusys.ai.score_news / kabusys.ai.regime_detector.score_regime を使用してバッチスコアリング（コード参照）

6. 停止 / 強制停止関連
   - 停止フラグ: data/stop_requested.flag を作成すると run_* スクリプトが検知して安全に終了します
   - KillSwitch: レジームやドローダウン基準のトリガーで data/kill.flag を作成（ExecutionEngine は起動時にこれを検出）
   - kill.flag を削除するにはファイルを削除するか KillSwitch.clear() を呼ぶ（スクリプトでは Settings.kill_flag_clear_on_start を使って起動時に自動クリア可）

監視 DB（SQLite）スキーマ（主要テーブル）
------------------------------------
init_monitoring_db により生成される主要テーブル:

- system_status:
  - recorded_at, cpu_percent, memory_percent, disk_percent, process_ok
- trade_logs:
  - logged_at, event_type, client_order_id, code, side, qty, price, filled_qty, state, latency_ms
- positions:
  - code (PK), qty, avg_price, current_price, updated_at
- risk_logs:
  - logged_at, event_type, metric_name, metric_value, threshold, detail
- dashboard:
  - 単一行（id=1 で保持）: updated_at, portfolio_value, cash, drawdown_pct, open_order_count, position_count, peak_value

ディレクトリ構成（抜粋）
---------------------
以下は src/kabusys 以下の主要モジュールと役割です（完全な構造は実コード参照）。

- kabusys/
  - __init__.py             — パッケージ定義、バージョン
  - config.py               — 環境変数 / Settings
  - utils/
    - process_priority.py   — プロセス優先度 / CPU affinity 設定ユーティリティ
  - monitoring/
    - __init__.py
    - monitoring_db.py      — SQLite 永続化層（init + CRUD）
    - system_monitor.py     — システム / データ鮮度監視
    - trade_monitor.py      — 注文滞留 / 約定異常監視
    - risk_monitor.py       — ドローダウン・ポジション上限監視
    - kill_switch.py        — kill.flag 書き込みロジック
    - alert_manager.py      — LINE 通知送信
    - monitoring_engine.py  — 各モニタ束ね（Polling loop）
    - streamlit_dashboard.py— Streamlit ダッシュボード
  - execution/
    - order_manager.py
    - reconciler.py
    - order_repository.py   — （一部参照済み）
    - broker_factory.py     — ブローカークライアント生成
    - execution_engine.py   — エンジン本体（起動・セッション管理）
  - portfolio/
    - portfolio_builder.py  — 候補選定・配分
    - position_sizing.py    — 株数算出・丸め・利用資金スケーリング
    - risk_adjustment.py    — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py    — Momentum / Value / Volatility 等の計算（DuckDB）
    - feature_exploration.py— 将来リターン・IC 計算・統計サマリ
  - ai/
    - news_nlp.py           — ニュース記事の LLM によるセンチメント集約
    - regime_detector.py    — 市場レジーム判定（MA + マクロセンチメント）
  - tools/
    - paper_verification_report.py — Paper Trading の検証レポート出力
  - run_monitoring.py       — SystemMonitor のポーリングループ起動スクリプト
  - run_execution.py        — ExecutionEngine 起動スクリプト

注意事項 / 運用ガイドライン
--------------------------
- Paper Trading は本番 DB と完全分離されています（PAPER_TRADING_SQLITE_PATH を使用）。
- OpenAI 呼び出しは API 料金とレート制限に注意してください。実装はリトライとバックオフを備えていますが、API キーの管理は運用側で行ってください。
- process priority の設定はプラットフォーム依存で失敗することがあります（権限による）。その場合は警告ログが出力されスキップされます。
- データ鮮度判定やリスクイベントは設定された閾値に依存します（Settings の CPU/MEM/DISK/閾値を環境変数で調整可能）。
- 本リポジトリは安全停止フラグ（data/stop_requested.flag, data/kill.flag）に依存する部分があるため、運用時はデータディレクトリの権限や存在確認を行ってください。
- DB マイグレーション（monitoring_db のカラム追加）は init_monitoring_db 内で簡易的に行われますが、既存データの完全互換性は要注意です。

開発 / テスト
--------------
- モジュールは可能な限り純粋関数／外部副作用を分離して実装されています（研究用関数群などは DuckDB 接続を注入）。
- OpenAI 呼び出し部分は _call_openai_api を patch することでユニットテストで差し替え可能です（例: unittest.mock.patch）。
- Settings は .env / 環境変数から自動読み込みします。テスト時に自動ロードを抑制したい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

補足（便利なコマンド例）
---------------------
- 監視を 30 秒間隔で起動:
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- Paper Trading モードで実行:
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
- Streamlit ダッシュボード:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
- Paper Trading レポート（期間指定）:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

問い合わせ / 貢献
-----------------
ソースコードの修正・機能追加・バグ報告は通常の GitHub プルリクエスト / Issue にてお願いします。コードを読む際は各モジュールの docstring と型注釈を参照してください。

以上。README に記載する内容の追加希望（例: 詳細な環境変数一覧、依存パッケージの pinned バージョン、実運用チェックリスト等）があれば教えてください。