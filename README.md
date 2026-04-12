# KabuSys — 日本株自動売買システム

本ドキュメントは、提供されているコードベースの概要、主要機能、セットアップ方法、使い方、ディレクトリ構成を日本語でまとめた README です。

概要
- KabuSys は日本株の自動売買／リサーチ／監視を目的とした Python ベースのプロジェクトです。
- 主な機能群は次の通り：
  - 注文実行エンジン（ExecutionEngine）と注文管理（OrderManager, Reconciler）
  - モニタリング（SystemMonitor, TradeMonitor, RiskMonitor）とアラート（LINE 経由）
  - ポートフォリオ構築（選定・重み付け・株数決定・リスク制御）
  - リサーチ（ファクター計算、特徴量探索）
  - AI モジュール（ニュースのセンチメント評価、レジーム判定 — OpenAI を利用）
  - Paper Trading モード（本番 DB と分離された専用 SQLite を使用）
  - 監視ダッシュボード（Streamlit）
  - 検証レポート生成ツール（paper_verification_report）

主な機能一覧
- 実行関連
  - OrderManager: 注文作成、送信、状態同期の高レベル API
  - Reconciler: 起動時の自動復旧（OrderSent などのリコンシリエーション）
- 監視 / 運用
  - SystemMonitor: CPU / メモリ / ディスク / プロセス存在 / データ鮮度の監視
  - TradeMonitor: 注文滞留・約定異常の検出
  - RiskMonitor: ドローダウン・ポジション上限の監視、kill.flag を書いて Execution を止める仕組み
  - AlertManager: LINE Messaging API を用いた通知（クールダウン管理あり）
  - MonitoringEngine: 各モニタを定期実行しアラートや kill 評価を行う
  - streamlit_dashboard: 監視情報の可視化（Streamlit）
- ポートフォリオ構築
  - 候補選定、等金額 / スコア加重、リスクベースの株数算出
  - セクター上限適用、レジーム乗数（bull/neutral/bear）
- リサーチ
  - factor_research: Momentum / Volatility / Value などのファクター計算（DuckDB を利用）
  - feature_exploration: 将来リターン、IC 計算、統計サマリ
- AI（OpenAI）連携
  - news_nlp.score_news: ニュースを集約して LLM に投げ、銘柄ごとのスコアを ai_scores テーブルへ書き込む
  - regime_detector.score_regime: ETF の MA 乖離とマクロニュースを組み合わせて市場レジームを判定
- ツール
  - tools.paper_verification_report: Paper Trading DB を集計して検証レポートを出力

セットアップ手順（ローカル開発向け）
1. Python
   - Python 3.10 以上を推奨（typing の構文などが使われています）。
2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 依存パッケージのインストール
   - 必要な主なパッケージ（例）:
     - duckdb
     - psutil
     - requests
     - streamlit
     - openai
   - 例:
     - pip install duckdb psutil requests streamlit openai
   - （プロジェクトに requirements.txt がある場合はそれを使ってください: pip install -r requirements.txt）
4. 環境変数の設定
   - プロジェクトルートに .env / .env.local を置くと自動でロードされます（自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定）。
   - 必須（使用する機能に応じて設定してください）:
     - JQUANTS_REFRESH_TOKEN — J-Quants API 用トークン
     - KABU_API_PASSWORD — kabuステーション API のパスワード
   - 任意・重要な環境変数（主なもの）:
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
       - paper_trading にすると Execution は mock ブローカーを使い data/paper_trading.db に書き込む
     - OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合）
     - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
     - PAPER_FILL_MODE: instant | partial | never | reject（paper_trading の約定挙動）
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE 通知用
     - PID_FILE_PATH / KILL_FLAG_PATH: プロセス監視 / kill.flag 用パス
     - MONITOR_POLL_INTERVAL: Monitoring のポーリング間隔（秒、run_monitoring で使用、デフォルト: 60）
     - LOG_LEVEL: ログレベル（DEBUG/INFO/...）
     - CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT: 監視閾値
5. データベース初期化
   - monitoring 用の SQLite は init_monitoring_db() により実行時に自動でテーブル作成・マイグレーションされます（run_monitoring や run_execution が DB を接続した際に実行されます）。
   - DuckDB に prices_daily / raw_financials 等のテーブルを用意するのはリサーチや AI 機能を使う場合に必要です。

使い方（主要コマンド）
- ExecutionEngine（実注文件等を扱うプロセス）を起動
  - 環境変数 KABUSYS_ENV を切り替えることで paper_trading モードにできます。
  - 例（本番想定）:
    - export KABUSYS_ENV=live
    - python -m kabusys.run_execution
  - 例（ペーパートレーディング）:
    - export KABUSYS_ENV=paper_trading
    - python -m kabusys.run_execution
  - 特徴:
    - プロセス優先度を high に設定（set_process_priority）
    - paper_trading の場合は MockBrokerClient を使い、別 SQLite に書き込む
    - 実行中は duckdb と sqlite 接続を保持

- Monitoring（監視ポーリング）を起動
  - MONITOR_POLL_INTERVAL を環境変数で上書き可能（秒、デフォルト 60）
  - python -m kabusys.run_monitoring
  - 注意: Monitoring は環境にかかわらず本番 sqlite_path（SQLITE_PATH）を使用して監視ログを保存します

- Streamlit ダッシュボード起動
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - 監視 DB を read-only モードで開き、ポジション・注文・システム状態・リスクログを可視化します

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db PATH で PAPER_TRADING_SQLITE_PATH を上書き可能

- AI 機能（ニューススコア／レジーム判定）
  - OpenAI API キー（OPENAI_API_KEY）を設定しておく必要があります
  - news_nlp.score_news(conn, target_date, api_key=None)
  - regime_detector.score_regime(conn, target_date, api_key=None)
  - 実行はスクリプトやスケジューラ経由で行う設計です（ターゲット日を明示的に渡すためルックアヘッドに強い）

運用に関する注意点
- kill.flag による停止:
  - RiskMonitor や KillSwitch が判定すると、data/kill.flag（デフォルト）を書き込み ExecutionEngine に停止シグナルを送る設計です。kill.flag が存在すると ExecutionEngine 側で停止処理が行われます（詳細は実行エンジン側実装に依存）。
- DB 分離:
  - Paper Trading（KABUSYS_ENV=paper_trading）時は本番監視 DB と注文データ DB を分離して管理します（事故防止）。
- プロセス優先度:
  - 実行スクリプトは起動時に set_process_priority("high") を呼びます。実行環境の権限や OS により設定に失敗する場合がありますが、ログで警告されてスキップされます。
- ロギング:
  - run_* スクリプトは logging.basicConfig(level=logging.INFO) を用いて起動します。LOG_LEVEL 環境変数で Settings.log_level を制御できます（内部で使用）。

ディレクトリ構成（主要ファイル / モジュール）
- src/kabusys/
  - __init__.py — パッケージ定義、バージョン
  - config.py — 環境変数 / Settings 管理、.env の自動読み込みロジック
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor ポーリング起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py — Paper Trading 検証レポート CLI
  - ai/
    - __init__.py
    - news_nlp.py — ニュースの LLM センチメント評価と ai_scores への書き込み
    - regime_detector.py — 市場レジーム判定と market_regime への書き込み
  - monitoring/
    - __init__.py
    - monitoring_db.py — SQLite ベースの監視 DB のスキーマと永続化 API
    - system_monitor.py — システム状態監視
    - trade_monitor.py — 注文滞留・約定異常監視
    - risk_monitor.py — ドローダウン / ポジション制限チェック
    - kill_switch.py — kill.flag 管理
    - alert_manager.py — LINE 通知
    - monitoring_engine.py — 各モニタのオーケストレーション
    - streamlit_dashboard.py — Streamlit ダッシュボード（起動スクリプト）
  - execution/
    - order_manager.py — 発注ロジックと状態遷移の外向け API
    - reconciler.py — 起動時リコンシリエーション
    - （その他 broker_factory, order_repository, order_record, execution_engine 等はコードベースに依存）
  - portfolio/
    - portfolio_builder.py — 候補選定と重み計算
    - position_sizing.py — 株数決定とアルゴリズム
    - risk_adjustment.py — セクターキャップ、レジーム乗数
  - research/
    - factor_research.py — Momentum / Volatility / Value 等のファクター計算（DuckDB 使用）
    - feature_exploration.py — 将来リターン / IC / 統計サマリ
  - utils/
    - process_priority.py — プロセス優先度・CPU affinity 設定ユーティリティ
  - monitoring/monitoring_db.py — 監視 DB 初期化・API（上に記載）
- data/（想定）
  - kabusys.duckdb — DuckDB（prices_daily 等のテーブルを格納）
  - monitoring.db — 監視用 SQLite
  - paper_trading.db — Paper Trading 用 SQLite（paper_trading モード時）

よく使う環境変数（抜粋）
- JQUANTS_REFRESH_TOKEN — J-Quants API（必須／使用する機能に応じて）
- KABU_API_PASSWORD — kabu API（実取引時必須）
- KABUSYS_ENV — 開発/ペーパー/本番（development / paper_trading / live）
- OPENAI_API_KEY — OpenAI（AI 機能を使う場合）
- DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH — DB パス
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID — アラート送信に必要
- MONITOR_POLL_INTERVAL — Monitoring のポーリング間隔（秒）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 自動 .env ロードを無効化（値が設定されると無効）

トラブルシューティング / 注意
- DuckDB / SQLite のテーブルやスキーマは実行時に想定どおり存在している必要があります。リサーチ / AI 機能は DuckDB の prices_daily / raw_financials / raw_news 等のテーブルを参照します。
- OpenAI の API 呼び出しはネットワーク・レート制限・JSON 構造の不整合に対してリトライやフォールバックが組み込まれていますが、API キーの設定が必須です。
- run_monitoring は監視データを本番の monitoring DB に書き込みます。テスト環境で実行する場合は SQLITE_PATH を別ファイルに設定してください。
- process priority / cpu affinity の設定は OS により失敗する場合がありますが、失敗時はログに警告が出て継続します。

ライセンス・貢献
- 本リポジトリに LICENSE が含まれている場合はそちらに従ってください。貢献・バグ報告は issue / PR を使って行ってください。

最後に
- 本 README はコードベースから抽出した情報に基づく要約です。各モジュールの詳細な挙動や追加の設定は、該当するモジュールの docstring やソースコード内コメント（多くは日本語）を参照してください。必要であれば各機能の使い方や設定例をさらに追記できます。