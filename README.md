KabuSys — 日本株自動売買システム (README)
=====================================

概要
----
KabuSys は日本株の自動売買／研究／監視を行うための Python コードベースです。  
主な目的は以下です。

- 戦略用のファクター計算・リサーチ（DuckDB を利用）
- ポートフォリオ構築（銘柄選定・重み計算・株数決定）
- 発注実行（Broker API 抽象化・注文管理・再同期）
- 監視（プロセス死活、データ鮮度、注文滞留、リスクアラート）
- Paper Trading の検証とレポート生成
- ニュース文章を LLM（OpenAI）でスコアリングして運用に利用

本リポジトリは純粋関数的な部位（ポートフォリオ計算等）と、DB/外部 API に依存する実行部位（ExecutionEngine、AI 呼び出し、監視）から構成されています。

主な機能一覧
-------------
- execution
  - 起動スクリプト: run_execution.py — ExecutionEngine を起動して発注を行う。
  - Broker クライアントファクトリ（paper_trading 時は MockBroker を利用）。
  - OrderManager / OrderRepository / Reconciler — 注文状態管理と起動時の同期ロジック。
  - RiskManager — 各種リスク制約（最大ポジション比率、利用率、回路遮断）を管理。
- monitoring
  - run_monitoring.py — SystemMonitor のポーリングループを起動。
  - MonitoringDB（SQLite）: system_status, trade_logs, positions, risk_logs, dashboard テーブル。
  - SystemMonitor / TradeMonitor / RiskMonitor / MonitoringEngine — 各種監視ロジック。
  - AlertManager — LINE Messaging API によるプッシュ通知（クールダウン管理）。
  - KillSwitch — kill.flag による ExecutionEngine 停止トリガ。
  - streamlit_dashboard.py — 監視データを可視化する Streamlit ダッシュボード。
- research
  - factor_research: Momentum / Volatility / Value ファクター計算（DuckDB）
  - feature_exploration: 将来リターン計算、IC（Information Coefficient）、統計サマリー
- portfolio
  - 銘柄選定（select_candidates）、重み計算（等金額・スコア重み）
  - リスク調整（sector cap、regime multiplier）
  - position sizing（株数決定、lot サイズ丸め、aggregate cap）
- ai
  - news_nlp: OpenAI を用いたニュースセンチメント集約と ai_scores への書き込み
  - regime_detector: MA200 とマクロニュースの LLM センチメントを使った日次市場レジーム判定
- tools
  - paper_verification_report.py — Paper Trading 結果の検証レポート生成（期間指定可能）

セットアップ手順
----------------
前提
- Python 3.10+ を推奨
- DuckDB（Python パッケージ）、psutil、requests、openai、streamlit などを使用

推奨手順（プロジェクトルートに src/ がある想定）:

1. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   - pip install duckdb psutil requests openai streamlit
   - （プロジェクトに requirements.txt がある場合は pip install -r requirements.txt）

3. パス設定（開発時）
   - 実行時に PYTHONPATH=src を指定するか、パッケージを開発インストール:
     - pip install -e .

環境変数 / .env
- 本コードは .env / .env.local や OS 環境変数から設定を読み込みます（config.py 内の自動ロード）。  
  読み込み順: OS 環境変数 > .env.local > .env。自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。
- 主な必須/重要な環境変数:
  - JQUANTS_REFRESH_TOKEN — J-Quants API（必要に応じて）
  - KABU_API_PASSWORD — kabuステーション API パスワード
  - OPENAI_API_KEY — OpenAI 呼び出し (ai.news_nlp / ai.regime_detector を使う場合)
  - KABUSYS_ENV — 起動環境（development | paper_trading | live）。デフォルト: development
  - LOG_LEVEL — ログレベル（DEBUG/INFO/...）
  - DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH — Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
  - PID_FILE_PATH, KILL_FLAG_PATH など（監視/実行制御用）
- PAPER_FILL_MODE（paper_trading 時の動作）: instant | partial | never | reject（デフォルト: instant）

使い方（主要スクリプト）
-----------------------

前提: プロジェクトルートで python -m で実行するか、PYTHONPATH=src を通す。

1) 実注文エンジン（Execution）
- コマンド:
  - PYTHONPATH=src python -m kabusys.run_execution
  - または pip install -e . してから python -m kabusys.run_execution
- 振る舞い:
  - KABUSYS_ENV=paper_trading のときは paper_trading 用の専用 SQLite を使い（data/paper_trading.db）、MockBrokerClient を使用して本番 DB と分離します。
  - 起動時にプロセス優先度を "high" に設定します（psutil による設定、権限がない場合は警告）。
  - duckdb と sqlite に接続し ExecutionEngine を組み立てて run_session() を実行します。
- 注意:
  - 実行前に必要な環境変数（KABU_API_PASSWORD 等）を設定してください。
  - KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に kill flag のクリア挙動を期待できます（ExecutionEngine 側の実装に依存）。

2) 監視ループ（Monitoring）
- コマンド:
  - PYTHONPATH=src python -m kabusys.run_monitoring
- 振る舞い:
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）。0 以下は無効扱いでデフォルトに戻ります。
  - 監視は常に本番用 sqlite_path（Settings.sqlite_path）を使用します（KABUSYS_ENV に依存しない）。
  - SystemMonitor / TradeMonitor / RiskMonitor を用いて定期的に状態を記録し、必要に応じて kill.flag 書き込みや LINE 通知を行います。

3) Streamlit ダッシュボード（監視の可視化）
- コマンド:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
- 説明:
  - read-only で SQLite を開き、Positions / Orders / System / Overview ビューを提供します。
  - MonitoringEngine が作成する DB を参照して使用します。

4) Paper Trading 検証レポート
- コマンド:
  - PYTHONPATH=src python -m kabusys.tools.paper_verification_report
  - 期間指定例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB を直接指定する場合:
    - --db PATH（環境変数 PAPER_TRADING_SQLITE_PATH より優先）
- 出力:
  - 稼働率、注文成功率、送信率、P95 レイテンシなどの指標を集計して PASS/FAIL 判定を出力します。

5) AI 関連機能（ニュース NLP / レジーム判定）
- ニューススコア付け:
  - kabusys.ai.news_nlp.score_news(conn, target_date, api_key=None)
  - OpenAI API キー（引数または OPENAI_API_KEY 環境変数）が必須。
  - raw_news / news_symbols / ai_scores テーブルを参照・更新します。
- レジーム判定:
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - ETF 1321 の MA200 乖離とマクロニュースの LLM 評価を合成して market_regime テーブルへ書き込みます。
- 注意:
  - API 呼び出しはリトライ/フェイルセーフの実装あり（429・タイムアウト・5xx 等に対するエクスポネンシャルバックオフ）。
  - OpenAI API の使用にはコストとレート制限があるため利用には注意してください。

設定の例 (.env)
----------------
（.env.example を参照して作成してください。無ければ下記の最低限を用意する）

- KABUSYS_ENV=development
- KABU_API_PASSWORD=your_kabu_password
- JQUANTS_REFRESH_TOKEN=your_jquants_token
- OPENAI_API_KEY=sk-...
- DUCKDB_PATH=data/kabusys.duckdb
- SQLITE_PATH=data/monitoring.db
- PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
- PID_FILE_PATH=data/execution.pid
- KILL_FLAG_PATH=data/kill.flag
- PAPER_FILL_MODE=instant

ディレクトリ構成（抜粋）
-----------------------
src/
  kabusys/
    __init__.py
    config.py                       # 環境変数読み込み・設定ラッパ
    run_execution.py                # ExecutionEngine 起動スクリプト
    run_monitoring.py               # Monitoring ポーリング起動スクリプト

    ai/
      __init__.py
      news_nlp.py                   # ニュースセンチメント（OpenAI 経由）
      regime_detector.py            # 市場レジーム判定（MA200 + LLM）

    monitoring/
      __init__.py
      monitoring_db.py              # SQLite 永続化層（テーブル作成・操作）
      monitoring_engine.py          # 各 Monitor を束ねるエンジン
      system_monitor.py
      trade_monitor.py
      risk_monitor.py
      alert_manager.py
      kill_switch.py
      streamlit_dashboard.py

    execution/
      order_manager.py
      reconciler.py
      order_repository.py
      order_record.py
      execution_engine.py
      broker_* (broker 関連実装群)

    portfolio/
      __init__.py
      portfolio_builder.py
      position_sizing.py
      risk_adjustment.py

    research/
      __init__.py
      factor_research.py
      feature_exploration.py

    tools/
      __init__.py
      paper_verification_report.py

    utils/
      __init__.py
      process_priority.py

補足と運用上の注意
------------------
- DB のマイグレーション: monitoring_db.init_monitoring_db() は冪等にテーブルを作成し、簡単なスキーマ追加（ALTER TABLE）を実行します。運用 DB での拡張時は事前にバックアップを取ってください。
- プロセス優先度 / CPU affinity：set_process_priority(), set_cpu_affinity() は権限に依存します。失敗時は警告ログのみ出ます。
- kill.flag メカニズム: 監視側が kill.flag を書き込むと ExecutionEngine に停止シグナルを送る設計です。フラグはファイルシステム上に作成されます。
- Paper Trading と本番 DB は分離されています（paper_trading 用 DB を使用）。運用時の誤混入に注意してください。
- LLM / API の呼び出しはコストがかかるため、ローカル開発やテスト時はモックや環境変数未設定で挙動を抑えることを推奨します。

貢献・開発
----------
- 開発時はプロジェクトルートから PYTHONPATH=src を通すか、pip install -e . してください。
- 単体関数（portfolio/*, research/*）は外部依存が少ないためユニットテストが書きやすい設計になっています。
- AI 呼び出しや Broker API 部分は外部依存が強いため、モック可能な設計を優先しています（各モジュールに _call_openai_api 等を分離）。

ライセンス / バージョン
-----------------------
- パッケージバージョンは src/kabusys/__init__.py の __version__ を参照してください（現状: 0.1.0）。

以上です。必要であれば各サブモジュール（ExecutionEngine の詳細設定、OrderRepository のスキーマ、AI 呼び出しのテスト方法など）について README を追記します。どの箇所を詳しく書きたいか教えてください。