KabuSys — 日本株自動売買システム
================================

概要
----
KabuSys は日本株の自動売買とそれを支える監視・検証機能群を持つ軽量なプロジェクトです。
主要機能は注文発行・状態同期・リコンシリエーション（Execution）と、
システム・注文・リスク監視（Monitoring）、ポートフォリオ構築・ポジションサイズ計算（Portfolio）、
ファクター計算・リサーチ（Research）、およびニュースを用いたAIスコアリング（AI）です。

主な設計方針
- DB（SQLite / DuckDB）を用いたオフラインでの検証と本番運用を想定
- Paper Trading（本番と分離）モードをサポート
- OpenAI を用いたニュース分析・レジーム判定をオプションで統合
- .env / .env.local による環境変数自動読み込み（任意で無効化可能）

機能一覧
-------
- Execution
  - ブローカークライアントを使った発注管理（OrderManager / ExecutionEngine）
  - 再起動時のリコンシリエーション（Reconciler）
  - Paper Trading 用に本番DBと分離した挙動
- Monitoring
  - SystemMonitor: CPU/メモリ/ディスク・プロセス存在確認・データ鮮度確認
  - TradeMonitor: 滞留注文・約定異常価格の検出
  - RiskMonitor: ドローダウン・ポジション上限監視とリスクログの記録
  - KillSwitch / AlertManager: 条件に応じた停止フラグ書き込み・LINE通知
  - Streamlit ダッシュボード（read-only で監視DBを表示）
- Portfolio
  - 候補抽出（スコア順）、等配分／スコア加重配分、ポジションサイズ計算（リスクベース等）
  - セクター上限適用、レジーム乗数
- Research
  - Momentum / Volatility / Value 等のファクター計算（DuckDB を使った実装）
  - 将来リターン・IC（Information Coefficient）計算、特徴量サマリ
- AI
  - ニュースセンチメントの LLM（OpenAI）によるスコアリング（ai_scores テーブルへ書込）
  - マクロニュース＋ETF MA を使った市場レジーム判定（regime_detector）
- ツール
  - Paper Trading 検証レポート生成スクリプト（kabusys.tools.paper_verification_report）

前提・依存
----------
- Python 3.10+
- 主要ライブラリ（例）
  - duckdb
  - psutil
  - requests
  - openai
  - streamlit (ダッシュボード起動時)
- 環境変数 / .env を使用
  - 自動ロード: プロジェクトルートに .env / .env.local があれば起動時に読み込まれます
  - 自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定

セットアップ手順
---------------
1. Python 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. 必要パッケージのインストール（例）
   - pip install duckdb psutil requests openai streamlit

   プロジェクトに requirements.txt がある場合は:
   - pip install -r requirements.txt

3. 環境変数の設定
   - プロジェクトルートに .env を作成するか、OS環境変数として設定します。
   - 主要な環境変数（例）:
     - JQUANTS_REFRESH_TOKEN=...
     - KABU_API_PASSWORD=...
     - OPENAI_API_KEY=...           # AI 機能を使う場合に必須
     - KABUSYS_ENV=development|paper_trading|live
     - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
     - SQLITE_PATH=data/monitoring.db
     - DUCKDB_PATH=data/kabusys.duckdb
     - LINE_CHANNEL_ACCESS_TOKEN=...  # LINE 通知を使う場合
     - LINE_USER_ID=...
     - MONITOR_POLL_INTERVAL=60       # 監視ループの秒間隔（デフォルト 60）
     - PAPER_FILL_MODE=instant|partial|never|reject

4. データディレクトリの作成（必要に応じて）
   - mkdir -p data

使い方
------
基本的な起動・運用コマンド例を示します。src 配下がそのまま参照される開発環境を想定しています。

- 監視ループを起動（Monitoring）
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で上書き可能（デフォルト 60 秒）。
  - 監視は KABUSYS_ENV に関わらず本番 sqlite_path（SQLITE_PATH）を使用します。
  - 停止手段: プロジェクトルートの data/stop_requested.flag を作成するとループが検知して停止します。

- 実行エンジンを起動（Execution）
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を用い、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に記録します。
  - 起動時、data/stop_requested.flag が存在すると起動せず終了します。
  - 実行プロセスは data/execution.pid に PID を書きます（プロセス存在チェックに利用）。

- Streamlit ダッシュボード（監視DB を読み取り専用で表示）
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - ダッシュボードは読み取り専用で監視テーブルを表示します（DB はロックされません）。

- Paper Trading 検証レポートの生成
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD
    - --to YYYY-MM-DD
    - --db PATH  （PAPER_TRADING_SQLITE_PATH / data/paper_trading.db を上書き）

- AI 関連（ニューススコアリング / レジーム判定）
  - OPENAI_API_KEY が必要です（引数で key を渡すことも可能）。
  - Python から直接呼ぶ例:
    - from kabusys.ai.news_nlp import score_news
      score_news(conn, target_date, api_key="...")  # conn は duckdb 接続
    - from kabusys.ai.regime_detector import score_regime
      score_regime(conn, target_date, api_key="...")

プロセス停止 / Kill フラグ
- KillSwitch は data/kill.flag を作成して ExecutionEngine を停止させるために使います（KillSwitch クラスは理由を書き込みます）。
- Kill flag は Settings.kill_flag_path（デフォルト data/kill.flag）で参照されます。
- Execution 側は起動時に kill flag を検出した場合、起動せず終了します。

設定の自動読み込み
- kabusys.config モジュールはプロジェクトルート（.git または pyproject.toml があるディレクトリ）を起点に .env/.env.local を自動ロードします。
- OS 環境変数は優先され、.env.local は .env を上書きする形で読み込まれます。
- 自動読み込みを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

ディレクトリ構成
----------------
以下は主要ファイル・ディレクトリの簡易ツリー（src/kabusys 配下）です。実際のファイルや追加パッケージはこの一覧に加わる可能性があります。

- src/
  - kabusys/
    - __init__.py
    - config.py                       — 環境変数／設定管理
    - run_monitoring.py               — SystemMonitor ポーリング起動スクリプト
    - run_execution.py                — ExecutionEngine 起動スクリプト
    - tools/
      - __init__.py
      - paper_verification_report.py  — Paper Trading 検証レポート CLI
    - monitoring/
      - __init__.py
      - monitoring_db.py              — SQLite 監視DB レイヤ
      - monitoring_engine.py
      - system_monitor.py
      - trade_monitor.py
      - risk_monitor.py
      - kill_switch.py
      - alert_manager.py
      - streamlit_dashboard.py
    - execution/
      - order_manager.py
      - reconciler.py
      - ... (broker, engine, repository 等)
    - portfolio/
      - portfolio_builder.py
      - position_sizing.py
      - risk_adjustment.py
      - __init__.py
    - research/
      - factor_research.py
      - feature_exploration.py
      - __init__.py
    - ai/
      - news_nlp.py
      - regime_detector.py
      - __init__.py
    - utils/
      - process_priority.py
      - __init__.py
    - data/  (推奨/自分で作成)
      - monitoring.db (default SQLITE_PATH)
      - paper_trading.db (paper trading 用)
      - kabusys.duckdb (default DUCKDB_PATH)
      - execution.pid
      - stop_requested.flag
      - kill.flag

補足・運用上の注意
-----------------
- Paper Trading モード（KABUSYS_ENV=paper_trading）は本番 DB と完全に分離されるよう設計されています（PAPER_TRADING_SQLITE_PATH を使用）。
- MONITOR_POLL_INTERVAL は監視ループの待機秒数を制御します。0 以下や不正値は無視されデフォルト（60 秒）にフォールバックします。
- process priority（優先度）は起動時に set_process_priority("high") を試みますが、権限不足や未対応 OS の場合はログ警告が出てスキップされます。
- AI（OpenAI）呼び出しは外部API依存かつコストがかかるため、APIキーの管理・呼出頻度に注意してください。
- DB スキーマのマイグレーションは一部（monitoring_db.init_monitoring_db）が実装されています。既存DBにカラムがない場合の追加処理が含まれます。

ライセンス・貢献
----------------
（ここにライセンス情報・貢献ガイドラインを追記してください）

お問い合わせ
------------
バグ報告・機能提案・その他はリポジトリの Issue を利用してください。

--- 
README はプロジェクトの現状コード（src/kabusys）を基に作成しています。実運用前に .env の設定、DB の初期化、依存ライブラリのインストール、及びブローカークライアントの設定（本番用 API 認証情報等）を必ず行ってください。