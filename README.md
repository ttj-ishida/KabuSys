# KabuSys

日本株自動売買システム（ライブラリ / 実行コンポーネント群）

このリポジトリは、取引エンジン、監視機構、ポートフォリオ構築、リサーチ、AI 補助（ニュース NLP / レジーム判定）等を含む自動売買システムの主要コンポーネントを収めています。本 README は開発者・運用担当者向けの概要、機能、セットアップ、使い方、ディレクトリ構成をまとめたものです。

注意: ここに記載されている設定名・ファイルパスはソース内のデフォルト・挙動に基づきます。運用環境では .env や環境変数で上書きしてください。

---

目次
- プロジェクト概要
- 主な機能一覧
- 必要な環境変数（主要）
- セットアップ手順
- 実行例（使い方）
- ツール類
- ディレクトリ構成（主要ファイルと説明）
- 運用上の注意点

---

プロジェクト概要
- KabuSys は日本株自動売買に必要なコンポーネント群を提供します。
  - 実際の発注を行う ExecutionEngine（ブローカー抽象化）
  - システム状態／注文状況／リスクを監視する Monitoring
  - ポートフォリオ構築（候補選定、重み付け、ポジションサイズ計算）
  - リサーチ（ファクター計算、将来リターン、IC 計算 等）
  - AI 補助（ニュースを LLM でセンチメント化、レジーム判定）
  - 運用補助ツール（Paper Trading 検証レポート、Streamlit ダッシュボード など）

主な機能一覧
- Execution
  - Broker クライアント抽象化（本番 / Paper Trading 切替）
  - OrderManager: 注文作成・状態同期・キャンセル管理
  - Reconciler: 再起動時の自動復旧（Order / Position の突合せ）
  - リスク制御（RiskManager, RiskConfig）
- Monitoring
  - SystemMonitor: CPU / メモリ / ディスク / データ鮮度 / PID チェック
  - TradeMonitor: 滞留注文、約定価格異常検出
  - RiskMonitor: ドローダウン・ポジション上限監視
  - KillSwitch: 条件により ExecutionEngine を停止するフラグ書き込み
  - AlertManager: LINE Push によるアラート通知（クールダウン管理）
  - Streamlit ダッシュボード（監視情報の可視化）
- Portfolio construction
  - 候補選定、等金額・スコア加重配分
  - 単元株丸め、リスクベース配分、セクターキャップ適用、レジーム乗数
- Research
  - ファクター計算（Momentum / Volatility / Value）
  - 将来リターン・IC、統計サマリー
  - DuckDB を使ったオンメモリ/軽量集計
- AI
  - news_nlp.score_news: raw_news から銘柄ごとのセンチメントスコアを生成し ai_scores テーブルへ保存（OpenAI）
  - regime_detector.score_regime: ETF の MA とマクロニュースの LLM センチメントを合成してレジーム判定

主要な環境変数（抜粋）
- KABUSYS_ENV: 起動環境（development | paper_trading | live）。デフォルト: development
- JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（AI モジュールで必須）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: AlertManager（LINE）用
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: paper_trading 時の MockBroker 挙動（instant | partial | never | reject）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、デフォルト 60）
- PID_FILE_PATH / KILL_FLAG_PATH: 実行制御用ファイルパス
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると .env の自動読み込みを無効化

.env の自動ロード
- 起動時に自動で .env / .env.local をロードします（OS 環境変数を保護）。
- プロジェクトルートは .git または pyproject.toml を基準に探索します。
- 自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

セットアップ手順（開発環境向け）
1. Python 環境
   - Python 3.9+ を推奨（duckdb / psutil などが必要）
2. 依存ライブラリをインストール
   - requirements.txt がある場合:
     - pip install -r requirements.txt
   - 主要なパッケージ（例）:
     - pip install duckdb psutil requests openai streamlit
3. .env を用意
   - .env.example を参考にして必要な環境変数を設定してください。
   - 例: KABUSYS_ENV=paper_trading, OPENAI_API_KEY=..., JQUANTS_REFRESH_TOKEN=...
4. データディレクトリ作成（任意）
   - デフォルトでは data/ 以下を使用します。存在しない場合は作成してください。
     - mkdir -p data
5. DB は起動スクリプトが必要なら自動で初期化します
   - Monitoring の初期テーブルは init_monitoring_db により作成されます（冪等）。

実行例（代表的コマンド）
- 監視ループを起動（ポーリング）
  - 環境変数 MONITOR_POLL_INTERVAL で秒数を上書き可能
  - python -m kabusys.run_monitoring
  - 動作: sqlite（Settings.sqlite_path）と DuckDB（Settings.duckdb_path）に接続し SystemMonitor を定期実行
  - 停止方法: Ctrl+C またはプロジェクトルート/data/stop_requested.flag を作成

- ExecutionEngine を起動（注文処理）
  - KABUSYS_ENV=paper_trading の場合は MockBroker を使用し、PAPER_TRADING_SQLITE_PATH に記録します（本番 DB と分離）
  - python -m kabusys.run_execution
  - 停止方法: Ctrl+C または data/stop_requested.flag を作成。実行中は data/execution.pid に PID が書かれます。

- Streamlit ダッシュボード（監視可視化）
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - または実行時に --db オプションで SQLite パスを指定

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db data/paper_trading.db （環境変数 PAPER_TRADING_SQLITE_PATH でも可）
  - レポートは標準出力へ出力され、稼働率・注文成功率・P95 レイテンシ等を評価して PASS/FAIL を算出します。

- AI 関連（プログラムから呼ぶ例）
  - from kabusys.ai.news_nlp import score_news
    - score_news(duckdb_conn, target_date, api_key="...")  # OPENAI_API_KEY が不要な場合
  - from kabusys.ai.regime_detector import score_regime
    - score_regime(duckdb_conn, target_date, api_key="...")

ツール・ユーティリティ（簡単な説明）
- process_priority.set_process_priority(level): プロセスの優先度設定（high/normal/low）。OS に依存する制限あり（psutil を使用）。
- monitoring.monitoring_db.init_monitoring_db(conn): 監視用 SQLite のテーブル作成／マイグレーション
- portfolio.*: 候補選定・重み計算・ポジションサイズ計算・セクターキャップ・レジーム調整
- research.*: DuckDB を使ったファクター計算 / 将来リターン / IC / 統計サマリ

ディレクトリ構成（src/kabusys 以下、抜粋）
- __init__.py
  - パッケージメタ情報（__version__ 等）
- config.py
  - Settings クラス：環境変数読み込み・検証・デフォルト値
  - .env 自動ロードロジック
- run_monitoring.py
  - SystemMonitor をポーリングする起動スクリプト（MONITOR_POLL_INTERVAL で間隔指定）
- run_execution.py
  - ExecutionEngine を起動するスクリプト（paper_trading 環境では MockBroker）
- monitoring/
  - monitoring_db.py : SQLite 永続化層（system_status, trade_logs, positions, risk_logs, dashboard 等）
  - system_monitor.py  : システム状態・データ鮮度チェック
  - trade_monitor.py   : 注文滞留・約定価格異常検出
  - risk_monitor.py    : ドローダウン・ポジション上限チェック
  - kill_switch.py     : kill.flag 書き込みによる停止シグナル
  - alert_manager.py   : LINE Push 通知（クールダウン管理）
  - monitoring_engine.py: 複数 Monitor を束ねる実行器
  - streamlit_dashboard.py: Streamlit ベースの可視化
- execution/
  - order_manager.py, order_repository.py, reconciler.py, execution_engine.py など（注文処理・同期ロジック）
- ai/
  - news_nlp.py: raw_news を LLM でスコアリングして ai_scores に書き込む
  - regime_detector.py: MA とマクロニュースを合成して市場レジームを判定
- portfolio/
  - portfolio_builder.py, position_sizing.py, risk_adjustment.py
- research/
  - factor_research.py, feature_exploration.py
- utils/
  - process_priority.py（プロセス優先度、CPU affinity）
- tools/
  - paper_verification_report.py : Paper Trading の検証レポート生成スクリプト

運用上の注意点
- Paper Trading と本番 DB は分離してください。KABUSYS_ENV=paper_trading では paper_sqlite_path が使用されます。
- AI モジュール（news_nlp / regime_detector）は OpenAI API キー（OPENAI_API_KEY）が必須です。キー未設定時は関数が ValueError を送出します。
- run_monitoring と run_execution はそれぞれ stop flag（data/stop_requested.flag）を監視します。外部から停止をトリガーする場合は該当ファイルを作成してください。
- process_priority の変更は OS 権限に依存します（normal → high へ上げるには権限が必要な場合あり）。失敗すると警告が出ますが起動は継続します。
- .env 自動読み込みは便利ですが、CI / テストでは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して明示的に環境を作ることを推奨します。

最後に
- 本 README はソースコードの注釈と起動スクリプトの実装に基づいて作成しています。詳しい設計方針やアルゴリズムの詳細はソース内の docstring（各モジュール冒頭のコメント）を参照してください。
- 追加の運用スクリプト（systemd ユニット、コンテナ化、監視連携など）が必要な場合は別途記述してください。

必要であれば、この README をベースに運用マニュアル（systemd ユニット例、Dockerfile、CI 設定）を作成します。必要な項目を教えてください。