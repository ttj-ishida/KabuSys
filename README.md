# KabuSys

KabuSys は日本株向けの自動売買システム（プロトタイプ）です。戦略・ポートフォリオ構築、発注実行、監視、研究（ファクター計算）および AI ベースのニュース解析等の機能を含みます。本 README はこのリポジトリ内の主要コンポーネントの概観、セットアップ、起動方法、およびディレクトリ構成を説明します。

注意: この README はソースコード（src/kabusys 以下）に基づく記述です。実行には外部ライブラリ／API キー（例: OpenAI）が必要な機能があります。安全のため本番取引で使用する前にコード・挙動を十分に確認してください。

---

目次
- プロジェクト概要
- 機能一覧
- 必要条件（概略）
- セットアップ手順
- 主要環境変数 / .env 例
- 使い方（実行コマンド例）
- ファイル／ディレクトリ構成
- 重要な挙動・運用メモ

---

プロジェクト概要
- 日本株自動売買システムのプロトタイプ。戦略の出力（シグナル）を受けて発注を行い、監視・リスク管理・リコンシリエーションを行う。
- 研究用（DuckDB を用いたファクター計算や特徴量探索）、紙上取引（paper trading）向けモード、OpenAI を用いたニュースセンチメント解析・市場レジーム判定などの補助機能を備える。
- 監視コンポーネントは SQLite にログを残し、Streamlit でダッシュボード表示可能。

機能一覧
- ExecutionEngine 起動（run_execution.py）
  - 本番／paper_trading（モックブローカー）を切り替え可能
  - OrderManager、RiskManager、Reconciler 等を組み合わせて起動
  - 起動中は PID ファイル（data/execution.pid）を作成・確認
- Monitoring（run_monitoring.py）
  - SystemMonitor / TradeMonitor / RiskMonitor をポーリングして監視ログを SQLite に保存
  - KillSwitch（閾値超過などで data/kill.flag を作成し ExecutionEngine を停止させる）
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL（秒）で上書き可能（デフォルト 60 秒）
- Monitoring DB 層（monitoring_db.py）
  - system_status、trade_logs、positions、risk_logs、dashboard 等のテーブル作成と読み書きユーティリティ
- Streamlit 監視ダッシュボード（monitoring/streamlit_dashboard.py）
  - SQLite を読み取り専用で開いて可視化（起動コマンドを参照）
- Research（research パッケージ）
  - ファクター計算（momentum, volatility, value）
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリ等
  - DuckDB 接続を受けて SQL+Python で計算
- Portfolio（portfolio パッケージ）
  - 銘柄候補選択、等配分／スコア加重、リスク調整（セクターキャップ）、ポジションサイズ決定ロジック
- AI 関連（ai パッケージ）
  - news_nlp: raw_news を集約して OpenAI に投げ、銘柄ごとのセンチメントを ai_scores テーブルに書き込む
  - regime_detector: ETF（1321）の MA200 乖離とマクロニュースの LLM 評価を合成して日次レジーム（bull/neutral/bear）を判定
  - OpenAI API を使用するため API キーが必要
- ツール
  - paper_verification_report: paper_trading の検証レポート生成（稼働率、注文成功率、レイテンシ等）

必要条件（概略）
- Python 3.10+
- 外部パッケージ（例）
  - duckdb
  - psutil
  - requests
  - openai
  - streamlit（ダッシュボード使用時）
- SQLite（標準ライブラリで利用可）
- OS によってはプロセス優先度設定に管理者権限が要る場合がある

セットアップ手順（例）
1. リポジトリをクローンし作業ディレクトリへ移動
   - git clone ...
   - cd <project_root>

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 必要パッケージをインストール
   - pip install duckdb psutil requests openai streamlit
   - （requirements.txt があれば pip install -r requirements.txt）

4. data ディレクトリを作成（必要に応じて）
   - mkdir -p data

5. 環境変数設定
   - プロジェクトルートに .env / .env.local を置くと自動読み込み（デフォルト）。自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。
   - 必須の環境変数（実行に必須なもの）
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - OpenAI を使う機能を利用する場合:
     - OPENAI_API_KEY
   - その他の主要設定は「主要環境変数」節参照

主要環境変数（Settings に基づく）
- KABUSYS_ENV: 起動環境（development, paper_trading, live）※デフォルト development
  - paper_trading の場合は MockBrokerClient を使用し、Paper 専用 DB（PAPER_TRADING_SQLITE_PATH）に記録される
- JQUANTS_REFRESH_TOKEN: J-Quants API 用トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（ai.news_nlp / regime_detector を使う場合に必要）
- PAPER_FILL_MODE: paper_trading 時の約定モード（instant / partial / never / reject、デフォルト instant）
- PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（デフォルト data/paper_trading.db）
- SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
- DUCKDB_PATH: DuckDB ファイル（デフォルト data/kabusys.duckdb）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、run_monitoring で使用。デフォルト 60）
- PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START など監視関連設定
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）

.env 例（プロジェクトルート/.env）
- 下記は一例です。実運用では秘密情報管理に注意してください。
  JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
  KABU_API_PASSWORD=your_kabu_password
  OPENAI_API_KEY=sk-xxxx...
  KABUSYS_ENV=development
  PAPER_FILL_MODE=instant
  SQLITE_PATH=data/monitoring.db
  DUCKDB_PATH=data/kabusys.duckdb
  PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
  LINE_CHANNEL_ACCESS_TOKEN=...
  LINE_USER_ID=...

使い方（代表的な起動コマンド）
- 監視プロセスを起動（ポーリングループ）
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL を環境変数で上書き可（秒）
    - 例: MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- 実行エンジン（ExecutionEngine）を起動
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading にすると paper_trading 用 DB（data/paper_trading.db）へ記録され、本番 DB と完全に分離される

- Streamlit ダッシュボードを起動（監視DB を読み取り専用で開く）
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

- Paper Trading 検証レポート（コマンドライン）
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - python -m kabusys.tools.paper_verification_report --db path/to/db

- AI 関連（ニューススコアリング / レジーム判定）
  - 必ず OPENAI_API_KEY を設定してから呼び出す（モジュール関数をアプリから呼ぶ）
  - 例: kabusys.ai.score_news / kabusys.ai.regime_detector.score_regime を利用

停止・制御
- 実行中の Engine / Monitor を外部から停止するにはフラグファイルを使う：
  - data/stop_requested.flag（run_monitoring, run_execution が監視している停止フラグ）
  - data/kill.flag は KillSwitch による Execution 停止トリガー（運用上の緊急停止）
- Execution は起動時に kill_flag_clear_on_start 設定に従って kill.flag を削除するオプションあり

ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py (パッケージ定義)
  - config.py (環境変数 / Settings 管理、自動 .env ロード)
  - run_monitoring.py (SystemMonitor ポーリング起動スクリプト)
  - run_execution.py (ExecutionEngine 起動スクリプト)

  - ai/
    - news_nlp.py (ニュースを OpenAI でスコア化して ai_scores に書き込む)
    - regime_detector.py (ETF MA200 + マクロニュースで市場レジーム判定)
  - monitoring/
    - monitoring_db.py (SQLite テーブルの作成・読み書き)
    - system_monitor.py (CPU/メモリ/ディスク/プロセス監視・データ鮮度)
    - trade_monitor.py (滞留注文・約定異常監視)
    - risk_monitor.py (ドローダウン・ポジション上限監視)
    - kill_switch.py (kill.flag 書込操作)
    - alert_manager.py (LINE push 通知)
    - monitoring_engine.py (各 Monitor を束ねて定期実行)
    - streamlit_dashboard.py (監視ダッシュボード)
  - execution/
    - reconciler.py (再起動時の自動復旧)
    - order_manager.py, order_repository.py, order_record.py, ...（発注・状態管理）
    - broker_factory.py, broker_api.py（ブローカー抽象）
    - execution_engine.py（エンジン本体）
    - risk_manager.py, order_manager.py（実行関連）
  - portfolio/
    - portfolio_builder.py (候補選定・重み計算)
    - position_sizing.py (株数決定)
    - risk_adjustment.py (セクター上限・レジーム乗数)
  - research/
    - factor_research.py (momentum/value/volatility)
    - feature_exploration.py (将来リターン・IC・統計)
  - data/    （実行時に使用する DB 等を置く想定）
    - monitoring.db (SQLite、デフォルト)
    - paper_trading.db (paper trading 用)
    - kabusys.duckdb (DuckDB ファイル)
    - execution.pid / kill.flag / stop_requested.flag 等の制御ファイル
  - tools/
    - paper_verification_report.py

重要な実装・運用メモ
- .env 自動読み込み:
  - プロジェクトルート（.git または pyproject.toml がある場所）から .env を自動ロード（.env.local を上書き読み込み）。自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1。
- 環境分離:
  - KABUSYS_ENV=paper_trading にすると paper_trading 専用 SQLite を使い、ブローカーは Mock を使用して本番 DB と分離。
- 監視の DB 書込み先:
  - Monitoring は KABUSYS_ENV にかかわらずデフォルトの sqlite_path（Settings.sqlite_path）を使用する点に注意（run_monitoring は本番 sqlite_path を使う実装注記あり）。
- OpenAI 使用:
  - news_nlp と regime_detector は OpenAI を呼び出す。API 呼び出しはバックオフ・リトライや応答バリデーションを行う設計だが、API キー未設定時は例外を投げるため必ず環境変数を設定すること。
- プロセス優先度:
  - run_monitoring/run_execution 起動時に set_process_priority("high") を試みる。権限や OS により失敗することがある（ログに警告が出るのみ）。
- DB マイグレーション:
  - init_monitoring_db は既存 DB に対して冪等的にテーブル作成を行い、必要に応じて簡単な ALTER TABLE によるカラム追加（latency_ms, peak_value）を行う。

開発・貢献
- 小さなユーティリティ群と明確な責務分離を意識した設計になっています。各モジュールの docstring に設計方針・注意点が記載されています。
- 新しい機能を追加する場合は既存のテーブル設計や永続化方針、特に「部分失敗時の DB 整合性保持（ex: ai_scores の部分置換）」を尊重してください。

ライセンス
- （ここにプロジェクトのライセンス表記を入れてください）

---

質問や追加で README に入れたい項目があれば教えてください。例えば、より詳細な .env のテンプレート、実行ログの例、ユースケース別の起動手順（開発 / 本番 / paper_trading）などを追記できます。