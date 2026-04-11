# KabuSys — README

このドキュメントは、リポジトリ内の主要モジュールを前提とした簡易 README です。日本株自動売買システムのコンポーネント（Execution / Monitoring / Research / AI）を含みます。

概要
- KabuSys は日本株の自動売買・研究・監視を行う小規模なシステムです。
- コア機能は発注エンジン（ExecutionEngine）、監視（MonitoringEngine）、因子計算・研究（research）、およびニュース NLP / レジーム判定（AI）から構成されます。
- DuckDB をデータ分析（時系列・ファクター計算）に使用し、SQLite を監視ログや注文履歴等の永続化に使います。

主な機能
- Execution
  - Signal Queue に基づく発注ループ（ExecutionEngine）
  - ブローカー抽象（BrokerAPIProtocol）と OrderManager による堅牢な注文処理（2 相永続化など）
  - 再起動時リコンシリエーション（Reconciler）
  - レート制限 / サーキットブレーカー / リスクゲート（RiskManager）
- Monitoring
  - システム情報（CPU/MEM/DISK）、データ鮮度、プロセス生存確認（SystemMonitor）
  - 注文滞留・約定異常の検出（TradeMonitor）
  - ドローダウン・ポジション上限監視（RiskMonitor）
  - Kill Switch（外部ファイルにより Execution を停止）
  - LINE 通知（AlertManager）
  - Streamlit を使った監視ダッシュボード
- Research
  - Momentum / Volatility / Value 等のファクター計算（DuckDB ベース）
  - 将来リターン計算、IC（Spearman）や統計サマリー
- AI
  - ニュースを OpenAI（gpt-4o-mini）へ投げて銘柄別センチメントを算出し ai_scores に記録（news_nlp）
  - マクロセンチメント + ETF MA200 を用いた市場レジーム判定（regime_detector）

必要条件（主な依存）
- Python 3.10+
- duckdb
- psutil
- requests
- streamlit（ダッシュボード利用時）
- openai（ニュースNLP / レジーム判定利用時）
- そのほか標準ライブラリ

セットアップ手順（ローカル開発向け）
1. リポジトリをクローン
   - git clone <repo_url>
2. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 必要パッケージをインストール（例）
   - pip install duckdb psutil requests streamlit openai
   - （パッケージ化されている場合）pip install -e .
4. 環境変数の準備
   - プロジェクトルートに `.env` / `.env.local` を置くことが可能（自動ロード）。自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定。
   - 主要な環境変数（例）
     - KABUSYS_ENV: development | paper_trading | live （デフォルト: development）
     - JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須な場合）
     - KABU_API_PASSWORD: kabuステーション API 用（必須）
     - OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合）
     - SQLITE_PATH: 監視 DB（monitoring.db）パス（デフォルト: data/monitoring.db）
     - DUCKDB_PATH: 分析 DB（kabusys.duckdb）パス（デフォルト: data/kabusys.duckdb）
     - PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（分離 DB）
     - PAPER_FILL_MODE: paper_trading の約定挙動（instant|partial|never|reject）
     - PID_FILE_PATH, KILL_FLAG_PATH: 実行制御ファイルのパス
     - MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、デフォルト 60）
     - LOG_LEVEL: ログレベル（DEBUG/INFO/...）
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE 通知用
5. データディレクトリを作成
   - mkdir -p data

データベース初期化
- 監視用 SQLite は run_monitoring / run_execution 実行時に init_monitoring_db() が呼ばれてテーブルを作成します（冪等）。
- DuckDB ファイルは prices_daily / raw_financials / raw_news 等のテーブルが必要です（データロードは別手順）。

使い方（実行例）
- 監視ループを起動
  - 環境変数で必要設定を用意したうえで：
    - python src/kabusys/run_monitoring.py
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で上書き可能（例: export MONITOR_POLL_INTERVAL=30）。
  - 監視は Settings.sqlite_path（デフォルト data/monitoring.db）を使います。run_monitoring は KABUSYS_ENV にかかわらず「本番」sqlite_path を使用する点に注意。
- 発注エンジン（ExecutionEngine）を起動
  - python src/kabusys/run_execution.py
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）を使って本番 DB と分離します。
- Streamlit ダッシュボード
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - 監視 DB を読み取り専用で開き、ダッシュボードを表示します。
- AI / 研究用関数の呼び出し（例: Python REPL）
  - DuckDB 接続を作成して呼び出す例:
    - import duckdb, datetime
    - conn = duckdb.connect("data/kabusys.duckdb")
    - from kabusys.ai.news_nlp import score_news
    - score_news(conn, datetime.date(2026, 3, 20), api_key="YOUR_OPENAI_KEY")
  - レジーム判定:
    - from kabusys.ai.regime_detector import score_regime
    - score_regime(conn, target_date, api_key="...")

重要な運用上の注意
- run_monitoring は Settings.sqlite_path（本番 monitoring.db）を常に使用します。テストで別 DB を使いたい場合は明示的に環境変数 SQLITE_PATH を変更してください。
- run_execution は KABUSYS_ENV=paper_trading のとき paper_sqlite_path を使い、DB を完全に分離します。
- kill.flag（Settings.kill_flag_path）を書き込むことで ExecutionEngine に停止シグナルを送ります。KillSwitch は冪等で既存ファイルがあれば再書き込みしません。ExecutionEngine は起動時に kill.flag をクリアするオプションがあります（Settings.kill_flag_clear_on_start）。
- PID ファイル（Settings.pid_file_path）は ExecutionEngine の稼働検知に使われます。権限やファイル整合性に注意してください（SystemMonitor が stale PID を検出すると削除します）。
- set_process_priority() により起動時に「high」優先度へ設定します。psutil が権限を持たない場合は警告を出してスキップします。
- OpenAI を使う機能はネットワーク/レート制限の影響を受けます。API キーを環境変数 OPENAI_API_KEY に設定してください。AI 呼び出しはエラー時にフォールバックやリトライロジックを持っていますが、完全な保証はありません。

ディレクトリ構成（抜粋）
- src/kabusys/
  - __init__.py
  - config.py — 環境変数 / 設定読み込みロジック
  - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py — ExecutionEngine 起動スクリプト
  - data/ (別ファイル群が想定される)
  - portfolio/
    - portfolio_builder.py — 候補選定・重み計算
    - position_sizing.py — 株数計算・集約キャップ
    - risk_adjustment.py — セクター上限・レジーム乗数
  - monitoring/
    - monitoring_db.py — SQLite テーブル初期化・読み書きラッパー
    - system_monitor.py — CPU/MEM/DISK/データ鮮度/プロセス監視
    - trade_monitor.py — 注文滞留・約定異常検出
    - risk_monitor.py — ドローダウン / ポジション上限監視
    - kill_switch.py — kill.flag の管理
    - alert_manager.py — LINE push 通知
    - monitoring_engine.py — 各 Monitor を束ねるポーリング実行ロジック
    - streamlit_dashboard.py — Streamlit ダッシュボード
  - execution/
    - execution_engine.py — ExecutionEngine（シグナル処理・push-drain）
    - order_manager.py — 発注ワークフロー（create/send/sync/cancel）
    - reconciler.py — 起動時リコンシリエーション
    - order_repository.py, order_record.py, broker_api.py, ...（発注周りの実装）
  - research/
    - factor_research.py — Momentum/Volatility/Value 等
    - feature_exploration.py — 将来リターン・IC・統計サマリ
  - ai/
    - news_nlp.py — ニュースを LLM でスコアリングして ai_scores に書き込む
    - regime_detector.py — 市場レジーム判定（ETF MA + マクロ NLP）
  - utils/
    - process_priority.py — プラットフォーム差を吸収した優先度/affinity 設定ユーティリティ

開発メモ / 補足
- .env パーサは config._load_env_file / _parse_env_line に実装されています。export 形式やクォート・エスケープ、コメントなどに対応します。
- DuckDB を使った research/ai 関数は、price / raw_financials / raw_news 等のテーブル構造に依存します。テーブル作成・データロードは別途実施してください。
- モジュール間で OpenAI 呼び出しのラッパーを分け、テスト時に patch しやすい設計になっています（内部 _call_openai_api を差し替え可能）。

例: 簡単な .env.example（プロジェクトルート）
- KABUSYS_ENV=development
- SQLITE_PATH=data/monitoring.db
- DUCKDB_PATH=data/kabusys.duckdb
- KABU_API_PASSWORD=your_kabu_password
- JQUANTS_REFRESH_TOKEN=your_jquants_token
- OPENAI_API_KEY=sk-...
- LINE_CHANNEL_ACCESS_TOKEN=
- LINE_USER_ID=
- PAPER_FILL_MODE=instant

以上を参考に、実運用ではログ設定・監視・テストを十分に行ってください。必要であれば各モジュールの個別ドキュメント作成も可能です。