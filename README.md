# KabuSys

日本株向けの自動売買システムの一部実装（ライブラリ＋起動スクリプト群）。  
この README は、提供されたコードベース（src/kabusys 以下）を元に、概要・機能・セットアップ・使い方・ディレクトリ構成を日本語でまとめたものです。

注意：実行には外部パッケージ（duckdb, psutil, requests, openai, streamlit 等）が必要です。以下を参照して環境を整備してください。

---

目次
- プロジェクト概要
- 主な機能一覧
- 依存関係
- 環境変数（.env）と設定
- セットアップ手順
- 使い方（起動例 / ツール）
- 主要設定の説明
- ディレクトリ構成

---

プロジェクト概要
- KabuSys は日本株の自動売買・リサーチ・監視を目的としたモジュール群。
- 戦略用のファクター計算、ポートフォリオ構築、発注管理（ExecutionEngine による発注フロー）、監視（MonitoringEngine）、
  AI を使ったニュースセンチメント / レジーム判定などの機能を含む。
- DB は主に DuckDB（時系列・リサーチ用）と SQLite（監視ログ・注文ログ）を利用する設計。

主な機能一覧
- リサーチ
  - ファクター計算（モメンタム / ボラティリティ / バリュー）
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリー
- ポートフォリオ構築
  - 候補選定、等配分／スコア加重配分
  - セクター制約、レジーム依存の乗数適用
  - 発注株数計算（単元株丸め・リスクベース配分・投下上限、aggregate cap）
- 発注（Execution）
  - OrderManager / Reconciler による発注・同期・復旧処理（再起動時のリコン）
  - Broker クライアント切替（本番 / paper_trading 用 Mock）
  - RiskManager（簡易的な発注規制） と OrderRepository（永続化）
- 監視（Monitoring）
  - SystemMonitor：CPU/メモリ/ディスク・プロセス生存・データ鮮度の監視
  - TradeMonitor：滞留注文検出・約定価格異常検出
  - RiskMonitor：ドローダウン・ポジション上限監視
  - KillSwitch：危険検知時にフラグファイルを書き ExecutionEngine 停止を促す
  - AlertManager：LINE Push による一方向通知
  - Streamlit ダッシュボード（監視データ閲覧）
- AI（OpenAI）
  - news_nlp: raw_news から銘柄別にセンチメントを LLM で評価し ai_scores に書き込む
  - regime_detector: ETF の MA 乖離 と マクロ記事の LLM センチメントを合成して market_regime を算出
- ツール
  - paper_verification_report: Paper Trading の履歴（data/paper_trading.db）から検証レポートを出力

依存関係（主なもの）
- Python 3.8+
- duckdb
- psutil
- requests
- openai
- streamlit（ダッシュボード起動時）
- sqlite3（標準ライブラリ）
- その他（実行環境に応じて必要）

環境変数（.env）と設定
- プロジェクトはルートの .env / .env.local を自動で読み込みます（OS 環境変数が優先）。自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。
- 主要な環境変数（Settings クラスに対応）：
  - KABUSYS_ENV: 開発環境。valid: development | paper_trading | live（デフォルト: development）
  - SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
  - DUCKDB_PATH: DuckDB ファイル（デフォルト: data/kabusys.duckdb）
  - PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
  - PAPER_FILL_MODE: paper_trading 時の約定挙動（instant | partial | never | reject、デフォルト: instant）
  - PID_FILE_PATH: ExecutionEngine の PID ファイルパス（デフォルト: data/execution.pid）
  - KILL_FLAG_PATH: Kill Switch 用フラグファイル（デフォルト: data/kill.flag）
  - OPENAI_API_KEY: OpenAI API キー（AI 機能使用時に必要）
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD 等（外部 API 用）
  - LOG_LEVEL: ログレベル（DEBUG|INFO|WARNING|ERROR|CRITICAL）
- 監視ループ用間隔：
  - MONITOR_POLL_INTERVAL: run_monitoring が使用するポーリング間隔（秒、デフォルト 60）。1 未満や不正な値は無視されデフォルトにフォールバック。

セットアップ手順（概略）
1. リポジトリをクローン／配置し、プロジェクトルートに移動（.git または pyproject.toml がある場所が自動検出の基準）。
2. Python 仮想環境を作成・有効化：
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 必要パッケージをインストール（例）：
   - pip install duckdb psutil requests openai streamlit
   - （requirements.txt があれば pip install -r requirements.txt を使用）
4. .env を作成（.env.example を参照して必要なキーを設定）。最低限：
   - OPENAI_API_KEY（AI を使う場合）
   - KABU_API_PASSWORD, JQUANTS_REFRESH_TOKEN（外部 API を使う場合）
   - KABUSYS_ENV（paper_trading / live / development）
5. データディレクトリを作成（必要に応じて）：
   - mkdir -p data

基本的な使い方（起動例）
- 監視ループを起動（SystemMonitor 単体のシンプル起動）：
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL=30 などでポーリング間隔を変更可能
  - 監視は Settings.sqlite_path を使用（監視 DB は環境にかかわらず本番 sqlite_path を使う）
- ExecutionEngine（発注エンジン）を起動：
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient が使用され、Paper Trading DB（PAPER_TRADING_SQLITE_PATH）へ記録され本番 DB と分離される
- Streamlit ダッシュボード（監視 UI）：
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
- Paper Trading 検証レポート生成：
  - python -m kabusys.tools.paper_verification_report
  - オプションで期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB パスを指定する場合:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
- AI スコアリング（プログラム経由で呼ぶ例）
  - ニュースセンチメントを実行（DuckDB 接続を渡して呼び出す）：
    - 例（簡易）:
      python - <<'PY'
      from datetime import date
      import duckdb
      from kabusys.ai.news_nlp import score_news
      conn = duckdb.connect('data/kabusys.duckdb')
      print(score_news(conn, date(2026,4,1), api_key='YOUR_OPENAI_KEY'))
      PY`
  - レジーム判定:
      python - <<'PY'
      from datetime import date
      import duckdb
      from kabusys.ai.regime_detector import score_regime
      conn = duckdb.connect('data/kabusys.duckdb')
      print(score_regime(conn, date(2026,4,1), api_key='YOUR_OPENAI_KEY'))
      PY`
  - 実運用ではこれらはスケジューラやエンジン内から呼び出す想定です。
- 開発・テスト用に個々の pure 関数（ポートフォリオ、研究系関数など）を Python REPL やテストスイートから利用可能：
  - 例: from kabusys.portfolio import select_candidates, calc_equal_weights

主要設定の説明（要点）
- KABUSYS_ENV
  - development: 開発
  - paper_trading: 発注は mock 実装を使い、paper_sqlite_path に記録する（本番 DB と完全分離）
  - live: 本番
- PAPER_FILL_MODE（paper_trading 専用）
  - instant | partial | never | reject — MockBroker の挙動を制御
- PID ファイル / Kill Flag
  - ExecutionEngine は Settings.pid_file_path に PID を書く（デフォルト data/execution.pid）
  - KillSwitch は Settings.kill_flag_path（デフォルト data/kill.flag）へ書き込み、ExecutionEngine 側でこれを検出して安全停止する設計
  - Kill flag の削除は KillSwitch.clear() または手動で行う。起動時に環境変数 KILL_FLAG_CLEAR_ON_START=1 を設定すると挙動を制御する箇所がある（Settings.kill_flag_clear_on_start）
- DB
  - DuckDB: デフォルト data/kabusys.duckdb（リサーチ用）
  - Monitoring SQLite: デフォルト data/monitoring.db（監視ログ）
  - Paper Trading SQLite: data/paper_trading.db（paper_trading 時分離）

注意点 / 運用上のヒント
- .env の読み込みは自動だが、OS 環境変数が優先されます。また .env.local は .env より上書き優先で読み込まれます。
- Settings は起動時に環境変数の検証を行い、不正値で例外を投げます（例: KABUSYS_ENV の不正、PAPER_FILL_MODE の不正値等）。
- MonitoringDB.init_monitoring_db は冪等（テーブル・インデックスの作成、既存 DB へのマイグレーション処理を含む）なので、スクリプト起動時に自動で必要なテーブルが作られます。
- OpenAI API 利用時は API キー管理に注意。API 呼び出しにはリトライとフォールバックの仕組みが組み込まれていますが、コストやレート制限には注意してください。
- process priority / CPU affinity 設定は utils.process_priority で抽象化されています（psutil を利用）。権限不足等で設定できない場合は警告が出てスキップされます。

ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py
  - config.py                — 環境変数/設定管理
  - run_monitoring.py        — SystemMonitor のポーリング起動スクリプト
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py — Paper Trading 検証レポート CLI
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
    - news_nlp.py             — ニュースセンチメント（OpenAI を利用）
    - regime_detector.py      — レジーム判定（MA + マクロセンチメント）
    - __init__.py
  - monitoring/
    - monitoring_db.py        — SQLite ベースの永続化層（監視ログ）
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py
    - monitoring_engine.py
    - streamlit_dashboard.py
    - __init__.py
  - execution/
    - reconciler.py
    - order_manager.py
    - (※ ここに broker_api, order_repository, execution_engine 等の実装が想定される)
  - data/ (not shown in code but expected)
    - kabusys.duckdb (デフォルト)
    - monitoring.db
    - paper_trading.db
  - utils/
    - process_priority.py
    - __init__.py

（上記はソースベースに含まれるファイルを抜粋して構成を示しています）

---

トラブルシューティング（よくある点）
- DB が開けないエラー：
  - paths（DUCKDB_PATH / SQLITE_PATH）が正しいか、ファイルの存在・権限を確認してください。
  - Streamlit は監視 DB を読み取り専用で開くため、パス指定に注意（--db 引数）。
- OpenAI 呼び出し失敗：
  - OPENAI_API_KEY を環境変数または関数引数で渡してください。
  - レート制限やネットワーク障害はログに出力されリトライ体系が働きますが、最終的にフォールバックして 0 やスキップされることがあります。
- PID / kill.flag 周り：
  - stale PID 検出時は PID ファイルを削除する挙動があるため、手動で PID ファイルを操作する際は注意してください。

---

この README はコードベースの主要機能と実行フローをまとめたものです。実際の運用では、Broker クライアント実装・ExecutionEngine の完全な実装・監視閾値調整・テストカバレッジの整備・運用ドキュメント（運転手順・ロールバック手順）などが必要になります。必要であれば README を拡張して、起動例や環境ごとの推奨設定、systemd / supervisor 用のユニットファイル例、CI テスト方法なども追加できます。