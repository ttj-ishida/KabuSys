# KabuSys — README (日本語)

このリポジトリは日本株自動売買システム「KabuSys」のコアライブラリ群です。戦略（Research / Portfolio）、Execution（発注エンジン/リコンシリエーション）、Monitoring（監視・アラート）、AI（ニュースNLP／レジーム判定）などの主要コンポーネントを含みます。本 README はローカルでのセットアップ、主要な実行方法、ディレクトリ構成を日本語でまとめたものです。

注意: この README はソースコードの公開部分に基づく概要です。実運用では外部ブローカー資格情報や API キーの管理、十分なテスト、リスク管理を必ず行ってください。

概要
- 名称: KabuSys
- 目的: 日本株向け自動売買プラットフォームのコアライブラリ群（研究・ポートフォリオ構築・発注・監視・AI 補助）
- 実装言語: Python（型アノテーションを使用）
- 主な外部依存:
  - duckdb（時系列価格などの分析用）
  - psutil（プロセス / リソース監視）
  - openai（LLM 呼び出し：ニュースセンチメント / マクロ判定）
  - requests（LINE push 通知）
  - streamlit（監視ダッシュボード）
  - 標準ライブラリの sqlite3 を永続化に使用

主要機能一覧
- Research / Factor
  - モメンタム / ボラティリティ / バリュー等のファクター計算（DuckDB 経由で prices_daily, raw_financials を参照）
  - 将来リターン計算、IC（情報係数）算出、統計サマリ
- Portfolio
  - 候補選定（スコア順）・重み計算（等金額 / スコア加重）
  - セクターキャップ適用、レジーム乗数
  - ポジションサイジング（risk_based / equal / score）
- Execution
  - OrderManager / Reconciler：発注フロー管理、再起動時の照合作業（ブローカーとローカル DB の整合）
  - Broker クライアントを抽象化して paper_trading（モック）と live を切り替え可能
- Monitoring
  - SystemMonitor: CPU / メモリ / ディスク / データ鮮度 / 実行プロセス存在チェック
  - TradeMonitor: 滞留注文・約定価格異常検出
  - RiskMonitor: ドローダウン・ポジション上限監視、dashboard 更新
  - MonitoringEngine: 各モニタを束ねたポーリングループ、KillSwitch による実行停止シグナルの発行
  - AlertManager: LINE へのプッシュ通知（クールダウン機能あり）
  - streamlit ダッシュボード（data/monitoring.db を表示）
- AI
  - news_nlp: raw_news をまとめ、OpenAI（gpt-4o-mini）で銘柄ごとのセンチメントを算出して ai_scores に保存
  - regime_detector: ma200 とマクロニュースの LLM センチメントを合成して市場レジーム（bull/neutral/bear）を判定
- Tools
  - paper_verification_report: Paper Trading の検証レポート生成（稼働率・注文成功率・レイテンシ等）

セットアップ手順（ローカル開発用）
1. Python 環境
   - 推奨: Python 3.10 以上（型ヒントの union | を使用）
   - 仮想環境作成（例）:
     - python -m venv .venv
     - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージをインストール
   - 最低限インストール例:
     - pip install duckdb psutil openai requests streamlit
   - （プロジェクトに requirements.txt がある場合は pip install -r requirements.txt を使用）

3. プロジェクトルートの認識と .env
   - config モジュールはプロジェクトルート（.git または pyproject.toml を基準）を探索し、自動で
     .env → .env.local を読み込みます（ただし環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。
   - 重要な環境変数（最低限設定が必要なもの）:
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
     - OPENAI_API_KEY（AI 機能を使う場合）
     - KABUSYS_ENV（development | paper_trading | live） ← デフォルトは development
   - データベースやパスのデフォルト:
     - DUCKDB_PATH: data/kabusys.duckdb
     - SQLITE_PATH: data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
     - PID_FILE_PATH: data/execution.pid
     - KILL_FLAG_PATH: data/kill.flag

4. データディレクトリ
   - data/ 配下に DB やフラグファイルが作成されます。必要に応じて手動で data/ ディレクトリを作成してください（実行時に自動作成されることもあります）。

基本的な使い方（コマンド例）
- 監視ループを起動（Monitoring）
  - デフォルトポーリング間隔は 60 秒。環境変数 MONITOR_POLL_INTERVAL で秒数を上書き可。
  - 実行:
    - python -m kabusys.run_monitoring
  - 動作:
    - Settings に従い sqlite(monitoring) と duckdb に接続し、SystemMonitor.check_once を定期実行します。
    - MONITOR_POLL_INTERVAL が 1 未満や無効な場合は 60 秒にフォールバックします。
    - stop フラグ: プロジェクトルート/data/stop_requested.flag が存在するとループを終了します。

- Execution Engine を起動（発注エンジン）
  - paper_trading 環境の場合は MockBrokerClient を使用し、paper_trading 用 DB に書き込みます（実稼働と分離）。
  - 実行:
    - python -m kabusys.run_execution
  - 動作:
    - プロセス優先度を high に設定（可能な場合）
    - Reconciler による起動時の照合・自動回復を含む ExecutionEngine をスレッドで実行
    - stop フラグ: data/stop_requested.flag があれば起動をスキップ、実行中にフラグが立てば停止します。

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db /path/to/paper_trading.db （環境変数 PAPER_TRADING_SQLITE_PATH より優先）

- Streamlit 監視ダッシュボード
  - 起動コマンド:
    - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - デフォルトは data/monitoring.db（read-only で開く）。MonitoringEngine がデータを書き込んでいることを確認してください。

- AI 機能の呼び出し（例）
  - news_nlp.score_news や regime_detector.score_regime は DuckDB 接続と target_date、OPENAI_API_KEY を渡して使います。簡易的には REPL やスクリプトから呼び出します（API キーは環境変数 OPENAI_API_KEY または引数で指定）。

重要な環境変数（主なもの）
- KABUSYS_ENV: development | paper_trading | live（デフォルト development）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（AI 機能を利用する場合）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト data/paper_trading.db）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、デフォルト 60）
- PAPER_FILL_MODE: paper_trading のモック約定モード（instant | partial | never | reject）
- PID_FILE_PATH / KILL_FLAG_PATH: 各種ファイルパス

停止 / Kill スイッチ
- KillSwitch は data/kill.flag を書き込むことで ExecutionEngine に停止シグナルを送ります（Execution 側は設定された kill_flag_path を参照）。
- monitoring の内部ロジックによりドローダウン閾値やポジション上限などで kill.flag を書くことがあります（デフォルト閾値はコード内に記載）。

実装上のメモ / 注意点
- Settings モジュールはプロジェクトルートから .env を自動読み込みしますが、OS 環境変数は優先されます。.env.local は .env を上書きする仕組みです。
- Monitoring は MonitoringDB.init_monitoring_db() を使って必要テーブルを冪等に作成します。既存 DB の簡単なマイグレーション（カラム追加）も実装されています。
- process priority / cpu affinity の設定は psutil のアクセス権限に依存します。権限不足の場合は警告を出してスキップされます。
- AI 呼び出しは OpenAI SDK を利用しており、429/ネットワーク断/タイムアウト/5xx に対しては指数バックオフでリトライする実装があります。失敗時はフェイルセーフ（0.0 等にフォールバック）を行います。
- Paper Trading（KABUSYS_ENV=paper_trading）は本番データベースとは分離された paper_trading 用 SQLite を使用します。

ディレクトリ構成（抜粋）
- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / 設定の読み込みと Settings クラス
  - run_monitoring.py        — SystemMonitor のポーリングループ起動スクリプト
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - data/ (実行時生成される)
- src/kabusys/monitoring/
  - monitoring_db.py         — SQLite 永続化レイヤ（system_status, trade_logs, positions, risk_logs, dashboard）
  - system_monitor.py        — リソース・プロセス・データ鮮度監視
  - trade_monitor.py         — 注文滞留・約定異常検出
  - risk_monitor.py          — ドローダウン / ポジション上限監視
  - kill_switch.py           — kill.flag 管理
  - alert_manager.py         — LINE 通知ラッパ
  - monitoring_engine.py     — 各 Monitor を束ねるエンジン
  - streamlit_dashboard.py   — Streamlit での監視ダッシュボード
- src/kabusys/execution/
  - order_manager.py
  - reconciler.py
  - order_repository.py      — （DB 層。ソース全体の一部）
  - execution_engine.py
  - broker_factory.py
  - broker_api.py
  - order_record.py
  - order_repository.py
- src/kabusys/portfolio/
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py
- src/kabusys/research/
  - factor_research.py
  - feature_exploration.py
- src/kabusys/ai/
  - news_nlp.py
  - regime_detector.py
- src/kabusys/tools/
  - paper_verification_report.py
- src/kabusys/utils/
  - process_priority.py

よくある運用コマンドまとめ
- 監視開始:
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- 実行エンジン（paper_trading）:
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
- Paper 検証レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- Streamlit ダッシュボード:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

ライセンス / 責任
- この README はコードコメントに基づく説明です。実運用前に適切なテストと監査を行ってください。
- ブローカー API の呼び出しや資金の実運用は重大なリスクを伴います。十分な確認・監視と責任ある運用をお願いします。

もし README に追加してほしい詳しい情報（例: .env.example のテンプレート、CI 手順、より詳細なデプロイ手順、テスト方法など）があれば教えてください。必要に応じて追記します。