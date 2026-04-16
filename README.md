KabuSys — README
=================

概要
----
KabuSys は日本株向けの自動売買 / 研究 / 監視ツール群のサンプル実装です。本リポジトリは以下の主要機能を含みます。

- 注文発行・管理を担う Execution エンジン（本番・Paper Trading 切替対応）
- 監視（System / Trade / Risk）とアラート送信（LINE）
- 市場レジーム判定やニュース NLP を用いた AI モジュール（OpenAI）
- ポートフォリオ構築・サイズ決定ロジック（純粋関数群）
- Research 用ファクター計算（DuckDB を利用）
- Paper Trading 検証レポート出力や Streamlit ダッシュボード等のツール

特徴
----
主な機能・特徴の一覧:

- Execution
  - Broker クライアント抽象化（本番と Paper Trading を分離）
  - OrderManager / Reconciler による起動時の自動復旧（リコンシリエーション）
  - RiskManager による発注前リスクチェック

- Monitoring
  - SystemMonitor: CPU / メモリ / ディスク / データ鮮度 / プロセス生存監視
  - TradeMonitor: 注文滞留（stale）・約定異常の検出
  - RiskMonitor: ドローダウン・保有上限の監視とログ記録
  - KillSwitch: 条件成立時に data/kill.flag を書き込み Execution を停止
  - AlertManager: LINE Messaging API による通知（クールダウン管理）
  - Streamlit ベースの簡易ダッシュボード

- Research / AI
  - ファクター計算（Momentum / Volatility / Value）
  - 将来リターン・IC 計算・統計サマリー
  - ニュース NLP（OpenAI を使用）で銘柄ごとのセンチメントを生成し ai_scores に保存
  - レジーム判定（ETF ma200 とマクロニュースの LLM センチメントの合成）

- Tools
  - paper_verification_report: Paper Trading DB から稼働率・注文成功率・レイテンシ等の検証レポート生成

セットアップ
-----------
前提
- Python 3.10 以上（PEP 604 の型 | を使用しているため）
- SQLite（組み込み）、DuckDB（pip で導入）
- ネットワークアクセス（LINE API / OpenAI を使う場合）

推奨手順（ローカル開発）
1. 仮想環境を作成して有効化
   - python -m venv .venv
   - (Unix) source .venv/bin/activate
   - (Windows) .venv\Scripts\activate

2. 必要パッケージのインストール（例）
   - pip install duckdb psutil openai requests streamlit

   実際のプロジェクトでは requirements.txt を用意して pip install -r で管理してください。

環境変数（主なもの）
- KABUSYS_ENV: 起動環境。development | paper_trading | live（デフォルト: development）
- JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須）
- KABU_API_PASSWORD: kabu ステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI を使う場合に必須
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: AlertManager（LINE）用（未設定ならログのみ）
- MONITOR_POLL_INTERVAL: Monitoring のポーリング間隔（秒、デフォルト 60）
- PAPER_FILL_MODE: Paper Trading の約定モード（instant|partial|never|reject、デフォルト instant）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite パス（デフォルト data/paper_trading.db）
- SQLITE_PATH: 監視 DB パス（デフォルト data/monitoring.db）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- LOG_LEVEL: ログレベル（DEBUG|INFO|WARNING|ERROR|CRITICAL）

.env の自動読み込み
- リポジトリルートに .env / .env.local があれば自動で読み込まれます（OS 環境変数が優先）。
- 自動読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

使い方（主要コマンド）
--------------------

1) 監視プロセス起動
- 監視ループを開始するスクリプト:
  - python -m kabusys.run_monitoring
- 特徴:
  - MONITOR_POLL_INTERVAL でポーリング間隔を指定可能（秒、デフォルト 60）
  - 監視は Settings.sqlite_path（= data/monitoring.db デフォルト）を使用（環境に依らず本番 DB を参照）
  - 停止はプロジェクトルート data/stop_requested.flag を作成することで行える（監視ループは検知して終了）

2) Execution エンジン起動
- 実行スクリプト:
  - python -m kabusys.run_execution
- 特徴:
  - KABUSYS_ENV=paper_trading に設定すると Broker のモックを使用し、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）へ記録します（本番 DB と完全分離）
  - 起動時に data/stop_requested.flag が存在する場合は起動せず終了
  - 実行中に同フラグが作られると安全に停止処理を行います
  - 実行プロセスの PID は data/execution.pid（デフォルト）に書き込まれます（SystemMonitor と連携）

3) Streamlit ダッシュボード
- 起動:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
- read-only モードで監視 DB を開くため、MonitoringEngine を先に動かしてデータを貯めてください。

4) Paper Trading 検証レポート生成
- 実行:
  - python -m kabusys.tools.paper_verification_report
  - 期間指定例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db /path/to/paper_trading.db
- 出力: 稼働率・注文成功率・送信率・レイテンシ等のサマリと PASS/FAIL 判定

5) AI / レジーム判定 / ニューススコアリング
- OpenAI API を使う関数:
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
- 事前準備: OPENAI_API_KEY を設定するか、api_key を明示的に渡すこと

停止・キルフラグについて
------------------------
- data/stop_requested.flag
  - run_monitoring.py / run_execution.py が監視する「即時停止」フラグ。ファイルが存在するとループを抜けて終了します。

- data/kill.flag
  - KillSwitch が条件を満たしたときに書き込むファイル。ExecutionEngine を停止させるためのトリガーとして動作します。

- data/execution.pid
  - ExecutionEngine が起動時に PID を書き込むファイル。SystemMonitor はこのファイルを見てプロセスが生存しているかを判別します（stale PID の検出・削除を行う）。

設定（代表的な Settings）
-------------------------
Settings クラスで取得される主な値（デフォルトを含む）:

- duckdb_path: DUCKDB_PATH, デフォルト data/kabusys.duckdb
- sqlite_path: SQLITE_PATH, デフォルト data/monitoring.db
- paper_sqlite_path: PAPER_TRADING_SQLITE_PATH, デフォルト data/paper_trading.db
- pid_file_path: PID_FILE_PATH, デフォルト data/execution.pid
- kill_flag_path: KILL_FLAG_PATH, デフォルト data/kill.flag
- cpu_threshold_pct / memory_threshold_pct / disk_threshold_pct: 監視閾値
- env: KABUSYS_ENV（development|paper_trading|live）

注意事項 / 実運用でのポイント
-----------------------------
- Paper Trading と本番 DB はデフォルトで分離されています。paper_trading 環境では paper_sqlite_path が使用されます。
- Monitoring はコード内で「環境にかかわらず本番 sqlite_path を使用する」箇所があるため（run_monitoring.py の実装）、運用時はデータの扱いに注意してください。
- OpenAI / LINE API を使用する機能は外部ネットワークに依存し、API キーを適切に管理する必要があります。
- process priority / CPU affinity 設定は psutil に依存し、権限不足により失敗する場合があります（ログに WARNING を出力してスキップ）。
- DuckDB を大量データに使う場合はファイルの I/O と VACUUM 等の運用を検討してください。

ディレクトリ構成
----------------
以下は src/kabusys 以下の主要ファイル・モジュールの説明（抜粋）:

- kabusys/
  - __init__.py — パッケージ定義、バージョン
  - config.py — 環境変数 / 設定の読み込み・検証（.env 自動読み込み）
  - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py — ExecutionEngine 起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading の検証レポート生成スクリプト
  - monitoring/
    - monitoring_db.py — SQLite による監視ログ永続化層（テーブル初期化含む）
    - system_monitor.py — システム／データ鮮度監視
    - trade_monitor.py — 注文滞留／約定異常監視
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - kill_switch.py — kill.flag の書き込みロジック
    - alert_manager.py — LINE への通知
    - monitoring_engine.py — 各モニタを束ねるポーリングエンジン
    - streamlit_dashboard.py — Streamlit を用いた簡易ダッシュボード
  - execution/
    - order_manager.py — 注文作成／FSM の外向き API
    - reconciler.py — 起動時の注文／ポジション整合
    - （その他 BrokerFactory / Engine 等の実装が別ファイルに存在）
  - portfolio/
    - portfolio_builder.py — 候補選定・配列計算（select_candidates, calc_*_weights）
    - position_sizing.py — 単元丸め・リスクベースの数量計算
    - risk_adjustment.py — セクター上限・レジーム乗数
  - research/
    - factor_research.py — Momentum / Volatility / Value 等のファクター計算（DuckDB）
    - feature_exploration.py — 将来リターン / IC / 統計サマリ
  - ai/
    - news_nlp.py — ニュースを OpenAI でスコアリングして ai_scores に書き込む
    - regime_detector.py — ETF ma200 とマクロニュースでレジーム判定
  - utils/
    - process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ

テスト・開発
-------------
- 各モジュールは副作用を避ける実装（純粋関数）と DB との I/O 部分が分かれているため、ユニットテストが書きやすく設計されています。
- AI 関連の外部呼び出しはラッパー関数を介しており、テスト時はモック置換が可能です（例: unittest.mock.patch）。

ライセンス / 貢献
-----------------
本 README はコードベースからの抜粋説明です。実際に運用・商用利用する際は、外部 API 利用規約や金融法規制を確認した上で適切な安全対策（回復手順、監査ログ、フェイルセーフ）を実装してください。

以上がこのコードベースの概要・セットアップ・使い方の要点です。必要であれば、代表的なユースケース（Paper Trading の一連実行手順や、監視のカスタム設定例、Docker 化・systemd ユニット例）を追加で用意します。どの情報がさらに必要か教えてください。