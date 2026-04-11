# KabuSys (README)

このリポジトリは日本株自動売買システム「KabuSys」の一部モジュール群を含みます。戦略のファクター計算、ポートフォリオ構築、発注エンジン、監視・アラート、AI（ニュースセンチメント／レジーム判定）などをモジュール化しています。

以下にプロジェクト概要、主要機能、セットアップ手順、使い方、ディレクトリ構成を日本語でまとめます。

---

プロジェクト概要
- KabuSys は日本株の自動売買を目的としたモジュール群です。  
- 主な責務：
  - データ処理（DuckDB を利用した時系列データ処理）
  - ファクター計算・特徴量解析（research）
  - ポートフォリオ構築（候補選定・重み計算・ポジションサイズ算出）
  - ExecutionEngine による発注管理（ブローカ API 経由）
  - 起動時のリコンシリエーション（注文・ポジション同期）
  - 監視（System / Trade / Risk）と LINE 通知
  - ニュースを LLM（OpenAI）でスコアリングしてテーブルに保存
  - 市場レジーム判定（MA + マクロニュースセンチメントの組合せ）
- 設定は環境変数またはプロジェクトルートの .env / .env.local から読み込まれます（自動読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。

---

機能一覧
- execution
  - ExecutionEngine：シグナル処理（Pull 型）＋ WebSocket push ドレイン
  - OrderManager：発注の状態遷移管理（作成 → 送信 → 同期 → キャンセル等）
  - Reconciler：再起動時の注文・ポジション照合（自動復旧）
  - RiskManager：発注 Gate（レート制限、回路遮断、ポジション・ドローダウン管理）※設定を参照
- monitoring
  - SystemMonitor：CPU / メモリ / ディスク / プロセス・データ鮮度監視
  - TradeMonitor：滞留注文・約定異常価格の検出
  - RiskMonitor：ドローダウンとポジション上限の監視
  - KillSwitch：条件該当時に kill.flag を書き込み、ExecutionEngine 停止を促す
  - AlertManager：LINE push による一方向通知（クールダウン管理）
  - MonitoringDB：SQLite による監視ログ永続化（system_status, trade_logs, positions, risk_logs, dashboard）
  - Streamlit ダッシュボード（read-only で監視 DB を表示）
- portfolio
  - 候補選定（スコアソート）、等金額・スコア加重配分、セクターキャップ適用、ポジションサイズ計算（単元株丸め / aggregate cap / cost buffer 等）
- research
  - ファクター計算（モメンタム / ボラティリティ / バリュー）
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリ
- ai
  - news_nlp.score_news(): raw_news を OpenAI に渡して銘柄ごとのセンチメントを ai_scores テーブルへ書込
  - regime_detector.score_regime(): ETF(1321) MA200 乖離 + マクロニュースセンチメントで日次レジーム判定
- utils
  - process_priority: プロセス優先度・CPU affinity 設定ユーティリティ（psutil 使用）

---

セットアップ手順（開発環境向け）
1. 必要条件
   - Python 3.10+
   - SQLite（標準ライブラリ）
   - DuckDB（Python パッケージ）
   - ネットワーク接続（LINE / OpenAI を使う場合）
2. リポジトリを取得
   - git clone して作業ディレクトリへ移動
3. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
4. 必要パッケージをインストール
   - 代表的な依存例:
     - pip install duckdb psutil requests openai streamlit
   - 実際にはプロジェクトの requirements.txt があればそれを使用してください。
5. 環境変数設定
   - プロジェクトルートに .env（または .env.local）を配置すると自動読み込みされます。
   - 自動ロードを無効化する場合: export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
   - 主要な環境変数（必須 / 重要）:
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須、kabuステーション用）
     - OPENAI_API_KEY（AI 機能を使う場合）
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
     - SQLITE_PATH（デフォルト: data/monitoring.db）
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト: data/paper_trading.db）
     - PAPER_FILL_MODE（paper_trading のモック挙動: instant|partial|never|reject）
     - PID_FILE_PATH（デフォルト: data/execution.pid）
     - KILL_FLAG_PATH（デフォルト: data/kill.flag）
     - MONITOR_POLL_INTERVAL（run_monitoring のポーリング間隔（秒））
     - LOG_LEVEL（DEBUG, INFO, ...）
6. DB 初期化
   - 監視 DB（SQLite）は起動スクリプトが自動で init_monitoring_db を実行します。専用スクリプトは不要です。
   - DuckDB は価格テーブル（prices_daily 等）を準備する必要があります。データ取り込みは別途用意してください。

注意:
- paper_trading モードでは発注は MockBroker を使い、paper_trading 用 SQLite に記録されます（本番 DB と分離）。
- process_priority は psutil を使用し、権限により設定に失敗することがあります（警告ログのみ）。

---

使い方（起動例・コマンド）
- パッケージとして実行する前提（src を PYTHONPATH に含める / pip install -e . が便利）

1) ExecutionEngine を起動（取引実行）
- デフォルト（開発）:
  - export KABUSYS_ENV=development
  - python -m kabusys.run_execution
- Paper trading（本番 DB とは分離してモックを使用）:
  - export KABUSYS_ENV=paper_trading
  - export PAPER_FILL_MODE=instant
  - python -m kabusys.run_execution
- 注意: 起動時に Settings で必要な環境変数が未設定だとエラーになります（JQUANTS_REFRESH_TOKEN や KABU_API_PASSWORD など）。

2) Monitoring（監視ループ）を起動
- MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で上書きできます（デフォルト 60 秒）。
- 起動:
  - export MONITOR_POLL_INTERVAL=30
  - python -m kabusys.run_monitoring
- Monitoring は KABUSYS_ENV に関係なく本番 sqlite_path を使用します（監視ログは一元管理）。

3) Streamlit ダッシュボード（監視 DB を可視化）
- 起動:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
- read-only URI を用いて SQLite を開きます。MonitoringEngine が data/monitoring.db を更新している前提。

4) AI 機能の利用（プログラム内での呼び出し）
- ニューススコアリング:
  - from kabusys.ai.news_nlp import score_news
  - score_news(duckdb_conn, target_date, api_key="...")  # api_key 省略時は OPENAI_API_KEY を参照
- レジーム判定:
  - from kabusys.ai.regime_detector import score_regime
  - score_regime(duckdb_conn, target_date, api_key="...")

5) 設定ファイル（.env）例（抜粋）
- .env（プロジェクトルート）
  - KABUSYS_ENV=development
  - JQUANTS_REFRESH_TOKEN=xxxx
  - KABU_API_PASSWORD=xxxx
  - OPENAI_API_KEY=sk-...
  - SQLITE_PATH=data/monitoring.db
  - DUCKDB_PATH=data/kabusys.duckdb
  - LOG_LEVEL=INFO

6) kill.flag / PID の扱い
- ExecutionEngine は起動時に Settings.kill_flag_path（デフォルト data/kill.flag）を確認します。
- KillSwitch は条件に該当した場合そのファイルを書き込み、ExecutionEngine に停止を促します。
- kill.flag を手動で削除するには data/kill.flag を削除してください（KillSwitch.clear が同等の操作）。

---

開発・テストに関するメモ
- Settings モジュールはプロジェクトルート（.git または pyproject.toml を基準）を探索して .env / .env.local を自動ロードします（OS 環境変数は上書きされません）。
- 一部の関数は外部 API（OpenAI、ブローカー API）に依存します。テストではモックによる差し替えが想定されています（コード内に差し替えを想定した設計あり）。
- process priority / cpu affinity はプラットフォーム依存（Windows / POSIX）。権限不足時は警告を出してスキップします。

---

ディレクトリ構成（主要ファイル）
- src/
  - kabusys/
    - __init__.py
    - config.py  — 環境変数 / .env ロード、Settings
    - run_execution.py  — ExecutionEngine 起動スクリプト
    - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト
    - portfolio/
      - __init__.py
      - portfolio_builder.py
      - position_sizing.py
      - risk_adjustment.py
    - research/
      - __init__.py
      - factor_research.py
      - feature_exploration.py
    - ai/
      - __init__.py
      - news_nlp.py
      - regime_detector.py
    - monitoring/
      - __init__.py
      - monitoring_db.py
      - system_monitor.py
      - trade_monitor.py
      - risk_monitor.py
      - alert_manager.py
      - kill_switch.py
      - monitoring_engine.py
      - streamlit_dashboard.py
    - execution/
      - execution_engine.py
      - order_manager.py
      - reconciler.py
      - (その他 broker / order_repository 等のモジュールが同階層に存在する想定)
    - data/ (想定: データファイル配置)
      - kabusys.duckdb (DuckDB ファイル)
      - monitoring.db (SQLite 監視 DB)
      - paper_trading.db (paper_trading 用 SQLite)
    - utils/
      - __init__.py
      - process_priority.py
    - research/, portfolio/, ai/ などは上記参照

---

よくある注意事項 / FAQ
- Q: .env を読み込ませたくない（テスト等）
  - A: KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- Q: OpenAI API キーがない場合は？
  - A: news_nlp.score_news / regime_detector.score_regime は API キーが未設定だと ValueError を投げます（明示的にエラーされる仕様）。AI 機能を使わない場合は OPENAI_API_KEY を設定しなくて良いです。
- Q: MONITOR_POLL_INTERVAL に 0 や負の値を入れたら？
  - A: run_monitoring は不正な値を検出するとデフォルト（60秒）に戻します。
- Q: paper_trading モードで本番 DB を汚染しないか？
  - A: paper_trading の場合、Execution は settings.paper_sqlite_path（デフォルト data/paper_trading.db）を利用するため、本番監視 DB（settings.sqlite_path）とは分離されます。ただし monitoring 自体は常に本番 sqlite_path を参照します。

---

貢献・拡張の案
- ブローカ API の実装を追加（kabuステーション実装や証券会社 SDK のラッパー）
- 単元株数の銘柄別対応（stocks マスタに lot_size を持たせる）
- AI レスポンスの堅牢性向上（応答フォーマット検証の改善）
- テスト用モック / CI 用の DB 初期化スクリプト追加
- requirements.txt、Dockerfile、systemd ユニット等の運用向け資産追加

---

以上がこのコードベースの README です。必要があれば、インストール要件（requirements.txt）や具体的な .env.example、運用時の systemd / docker compose 例なども追記します。どの情報を優先して追加しましょうか？