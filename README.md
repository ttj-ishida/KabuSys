KabuSys — README
===============

概要
----
KabuSys は日本株自動売買のための内部ユーティリティ群および監視/検証ツール群です。  
本リポジトリには以下の機能が含まれており、取引エンジン（ExecutionEngine）・監視（MonitoringEngine）・ポートフォリオ構築・リサーチ・AI（ニュースセンチメント / レジーム判定）などを提供します。

主な機能
--------
- 実行エンジン起動スクリプト（run_execution）
  - KABUSYS_ENV に応じて本番/ペーパートレードを切替可能（paper_trading 時は専用 DB を使用）
  - ブローカークライアントの生成、リスク管理、発注・再突合（Reconciler）を含む
- 監視（Monitoring）
  - SystemMonitor / TradeMonitor / RiskMonitor を統合した MonitoringEngine
  - system_status / trade_logs / risk_logs / positions / dashboard を保持する SQLite ベースの監視 DB
  - kill.flag による ExecutionEngine 停止シグナルの発行
  - Streamlit ダッシュボード（監視情報の可視化）
- ポートフォリオ構築
  - 候補選定、重み計算（等金額・スコア加重）、ポジションサイズ計算、セクター制限、レジーム乗数
- リサーチ
  - ファクター計算（モメンタム・ボラティリティ・バリュー等）
  - 将来リターン、IC（Information Coefficient）計算、ファクター統計サマリ
- AI（OpenAI を利用したニュース NLP / レジーム判定）
  - raw_news を LLM へ渡してセンチメントを算出し ai_scores に書き込む
  - マクロニュース + ETF MA200 乖離で日次の市場レジーム（bull/neutral/bear）を判定
- ツール
  - Paper Trading 検証レポート生成スクリプト（paper_verification_report）

セットアップ
-----------
前提
- Python 3.10 以上（型注釈の一部で新しい構文を使用）
- SQLite（標準ライブラリ）
- DuckDB（ローカルデータ分析用）

依存パッケージ（例）
- duckdb
- psutil
- requests
- openai
- streamlit

インストール例（開発環境）
1. リポジトリルートに移動（この README はパッケージソース直下を想定）
2. 仮想環境を作成・有効化
3. 必要パッケージをインストール

例:
    python -m venv .venv
    source .venv/bin/activate  # Windows: .venv\Scripts\activate
    pip install duckdb psutil requests openai streamlit

.env 自動読み込み
- config.Settings モジュールはプロジェクトルート（.git または pyproject.toml を探索）を基準に .env / .env.local を自動で読み込みます。
- OS 環境変数が優先され、.env.local は .env を上書きします。
- 自動読み込みを無効化する場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

重要な環境変数（Settings で参照されるもの）
- JQUANTS_REFRESH_TOKEN — J-Quants API 用（必須）
- KABU_API_PASSWORD — kabuステーション API 用（必須）
- KABU_API_BASE_URL — kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- OPENAI_API_KEY — OpenAI API キー（AI モジュール使用時）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID — LINE 通知用（任意）
- KABUSYS_ENV — 実行環境: development | paper_trading | live（デフォルト: development）
- LOG_LEVEL — ログレベル（DEBUG/INFO/…）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード用 SQLite（paper_trading 時に使用、デフォルト: data/paper_trading.db）
- PID_FILE_PATH — ExecutionEngine PID ファイル（デフォルト: data/execution.pid）
- KILL_FLAG_PATH — kill.flag のパス（デフォルト: data/kill.flag）
- PAPER_FILL_MODE — MockBroker のフィル（instant|partial|never|reject）
- その他: CPU/MEM/DISK 閾値や kill_flag 関連

使い方（主要コマンド）
--------------------

注意: 開発中はパッケージをインストールせずにソースを直接実行する場合、PYTHONPATH=src を指定して実行してください。
例:
    PYTHONPATH=src python -m kabusys.run_monitoring

1) 監視ループの起動
- モニタリングポーリングを実行する（デフォルト 60 秒間隔）
    PYTHONPATH=src python -m kabusys.run_monitoring

- ポーリング間隔を変更する:
    export MONITOR_POLL_INTERVAL=30  # 秒

- モニタリングは Settings.env の値に関わらず本番 sqlite_path を使用して監視ログを書きます。

2) ExecutionEngine（取引実行）の起動
- 本番 / ペーパートレード切替:
    - ペーパートレード:
        export KABUSYS_ENV=paper_trading
        PYTHONPATH=src python -m kabusys.run_execution
      この場合、paper_sqlite_path（デフォルト data/paper_trading.db）へ分離して記録します。
    - 本番:
        export KABUSYS_ENV=live
        PYTHONPATH=src python -m kabusys.run_execution

- 実行開始時にプロセス優先度を high に設定します（可能な限り）。

3) Streamlit ダッシュボード（監視）
- read-only で監視 DB を可視化
    streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

4) Paper Trading 検証レポート
- 指定期間のレポートを標準出力に出力
    PYTHONPATH=src python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- DB パスは --db オプションまたは環境変数 PAPER_TRADING_SQLITE_PATH で指定可能

5) AI 関連（ニューススコア / レジーム判定）
- OpenAI API キー（OPENAI_API_KEY）が必須です
- 例: Python スクリプトから呼ぶ場合
    from kabusys.ai.news_nlp import score_news
    # duckdb_conn は duckdb.connect(...) で得る
    score_news(duckdb_conn, target_date, api_key="sk-...")

    from kabusys.ai.regime_detector import score_regime
    score_regime(duckdb_conn, target_date, api_key="sk-...")

その他の挙動メモ
- run_monitoring は MONITOR_POLL_INTERVAL でポーリング。0 以下や不正な値はデフォルトにフォールバック。
- run_execution は起動時にリコンシリエーション（Reconciler）や risk_manager などを組み立ててセッションを実行します。paper_trading 時は MockBroker を用い、paper DB に完全分離して記録します。
- MonitoringDB の init_monitoring_db は冪等でテーブル作成とマイグレーション（カラム追加）を行います。
- KillSwitch は RiskMonitor などの結果に基づいて data/kill.flag を書き込み、ExecutionEngine に停止シグナルを送ります（冪等）。

ディレクトリ構成（抜粋）
----------------------

リポジトリの主要モジュール構成の抜粋（src/kabusys 以下）:

- src/kabusys/
  - __init__.py
  - config.py                      — 環境変数 / 設定読み込み
  - run_monitoring.py              — SystemMonitor ポーリング起動スクリプト
  - run_execution.py               — ExecutionEngine 起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py  — Paper Trading 検証レポート
  - monitoring/
    - __init__.py
    - monitoring_db.py              — SQLite 永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - monitoring_engine.py
    - alert_manager.py              — LINE Push 通知
    - kill_switch.py
    - streamlit_dashboard.py
  - execution/
    - order_manager.py
    - reconciler.py
    - (その他: broker_factory, execution_engine, order_repository, order_record 等が利用される想定)
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
    - news_nlp.py                   — ニュースセンチメント取得（OpenAI）
    - regime_detector.py            — レジーム判定（OpenAI + MA200）
  - utils/
    - __init__.py
    - process_priority.py           — プロセス優先度 / CPU affinity ユーティリティ
  - (その他: data モジュールや execution の詳細実装は別ファイルとして存在する想定)

設計上の注意点 / 運用メモ
------------------------
- .env の読み込みはプロジェクトルートを基準に行われます（.git または pyproject.toml があるディレクトリ）。CI/本番環境では OS 環境変数での設定を推奨します。
- AI モジュールは OpenAI の外部 API を使用します。API 呼び出しはリトライ・バックオフ・レスポンス検証を含む堅牢化がされていますが、API キー漏洩に注意してください。
- run_monitoring は監視ログを書き込む際、常に本番用 sqlite_path を使用します（環境に依らず監視用 DB を集中させる設計）。
- paper_trading モードは本番 DB と完全分離された DB に記録されるため、検証には安全に使用できます。
- process_priority の設定は OS により制限を受ける可能性があります（権限不足時は警告ログを出してスキップ）。

ライセンス / 貢献
-----------------
（ここにライセンスや貢献方法を記載してください。README に必要な場合は追加してください。）

問題報告 / 連絡先
----------------
不具合や改善提案は Issue を立ててください。README の記載内容や使い方で不明点があればお知らせください。

以上。必要であれば各モジュールの API 使用例やデプロイ例（systemd / supervisor での常駐起動、コンテナ化のヒントなど）を追加で作成します。