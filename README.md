KabuSys
=======

日本株向けの自動売買システム（ミニマル実装）です。  
このリポジトリには取引実行（Execution）、監視（Monitoring）、ポートフォリオ構築、リサーチ、AI（ニュース NLP / レジーム判定）などの主要コンポーネントが含まれています。設計方針として「本番 API へ不要なアクセスをしない」「ルックアヘッドバイアスを避ける」「フェイルセーフ（失敗しても安全に継続）」を重視しています。

主な特徴
-------
- ExecutionEngine：ブローカー経由での発注、リスク管理、再同期（Reconciler）機能
- Monitoring：システム状態（CPU/メモリ/ディスク）、データ鮮度、滞留注文・約定異常、ドローダウン監視
- KillSwitch：監視による停止シグナル（flag ファイル）発行
- Streamlit ダッシュボード：監視データの可視化（read-only）
- Paper Trading モード：本番 DB と分離された SQLite を使った模擬取引
- AI モジュール：ニュースを LLM（OpenAI）で評価して銘柄スコア化、マクロセンチメントと ETF 指標を使ったレジーム判定
- リサーチ用関数群：ファクター計算・将来リターン・IC 計算など（DuckDB ベース）
- 純粋関数群で構成されたポートフォリオ構築ライブラリ（候補選定・重み付け・ポジションサイジング・セクター制限）

動作前提（推奨）
----------------
- Python 3.10+
- SQLite（標準ライブラリ）
- DuckDB（pip install duckdb）
- psutil（プロセス優先度 / CPU affinity）
- requests（LINE 通知）
- openai（LLM 呼び出し、score_news / score_regime）
- streamlit（ダッシュボード）

セットアップ（開発向け）
---------------------
1. リポジトリをクローン
   - git clone ... 

2. 仮想環境を作成・有効化（例）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール（簡易例）
   - pip install duckdb psutil requests openai streamlit

   実際には requirements.txt を用意している場合はそちらを使ってください。

4. データディレクトリを準備
   - mkdir -p data

5. 環境変数の設定
   - プロジェクトルートの .env / .env.local を利用できます（自動読み込みあり）。
   - 自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

主要な環境変数（抜粋）
---------------------
- KABUSYS_ENV: 起動環境（development / paper_trading / live）。デフォルト: development
  - paper_trading の場合、MockBroker を使い data/paper_trading.db に書き込みます（本番 DB と分離）。
- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（AI 機能で必須）
- PAPER_FILL_MODE: paper_trading の約定モード（instant/partial/never/reject）
- PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite パス（デフォルト: data/paper_trading.db）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）
- DUCKDB_PATH: DuckDB ファイル（デフォルト: data/kabusys.duckdb）
- PID_FILE_PATH: ExecutionEngine の PID ファイル（デフォルト: data/execution.pid）
- KILL_FLAG_PATH: KillSwitch のフラグファイル（デフォルト: data/kill.flag）
- MONITOR_POLL_INTERVAL: run_monitoring が使うポーリング間隔（秒、デフォルト: 60）

注意点
- Settings（kabusys.config.Settings）は起動時に .env を自動ロードします（プロジェクトルートは .git または pyproject.toml を基準に探索）。必須 env が欠けているとエラーになります。
- run_monitoring は KABUSYS_ENV に関わらず監視用 DB（Settings.sqlite_path）を使用します（監視ログは本番 DB に記録する想定）。
- run_execution は paper_trading 時に paper_sqlite_path を使用し、本番 DB と完全に分離します。
- 実行スクリプトは起動時にプロセス優先度を "high" に設定しようとします（権限により失敗する場合は警告ログ）。

使い方（代表コマンド）
--------------------
- 実行エンジン起動（本番 / 開発 / paper_trading）
  - KABUSYS_ENV=development python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution  # MockBroker + data/paper_trading.db に書き込み

- 監視ループ起動（ポーリング）
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- Streamlit ダッシュボード（read-only）
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

- Paper Trading 検証レポート（ツール）
  - python -m kabusys.tools.paper_verification_report
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db オプションで DB パスを指定可能（PAPER_TRADING_SQLITE_PATH 環境変数でも可）

- AI 機能（プログラム的呼び出し）
  - kabusys.ai.score_news(conn, target_date, api_key=...)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=...)
  - いずれも DuckDB 接続（duckdb.connect(...)）を引数に取ります。

監視・アラート動作概要
--------------------
- SystemMonitor が CPU/MEM/DISK、プロセス生存、データ鮮度をチェックして monitoring DB の system_status に記録します。
- TradeMonitor が滞留注文・約定異常価格をチェックし risk_logs に記録します。
- RiskMonitor が drawdown（ハイウォーターマーク管理）とポジション上限をチェックし、必要時に risk_logs に通知します。
- KillSwitch は risk の閾値超過などで data/kill.flag を書き込み、ExecutionEngine 停止を指示します（冪等）。
- AlertManager は LINE Messaging API で一方向通知を送ります（設定されていない場合はログに留める）。

ディレクトリ構成（抜粋）
---------------------
- src/kabusys/
  - __init__.py                — パッケージ定義（__version__ 等）
  - config.py                  — 環境変数 / Settings 管理（.env 自動ロード）
  - run_execution.py           — ExecutionEngine 起動スクリプト
  - run_monitoring.py          — SystemMonitor 単体ポーリングスクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート生成 CLI
  - execution/
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - execution_engine.py      — （主要ロジックファイル群、実行・リスク管理）
    - broker_factory.py
    - broker_api.py
    - order_record.py
    - ... (他)
  - monitoring/
    - monitoring_db.py         — SQLite テーブル初期化 / CRUD
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py
    - monitoring_engine.py
    - streamlit_dashboard.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py
  - research/
    - factor_research.py       — ファクター計算（momentum/volatility/value）
    - feature_exploration.py   — 将来リターン・IC・統計
  - ai/
    - news_nlp.py              — ニュース NLP（OpenAI を使ったセンチメント）
    - regime_detector.py       — 市場レジーム判定
  - data/
    - pipeline.py              — DuckDB の prices_daily 参照ユーティリティ等
    - stats.py                 — zscore_normalize 等ユーティリティ
  - utils/
    - process_priority.py      — プロセス優先度 / CPU affinity ユーティリティ

開発・運用上の注意
-----------------
- Settings のプロパティは必須 env をチェックして ValueError を投げます。起動前に .env を整備してください（.env.example を参照）。
- Paper Trading モードは本番データベースと完全に分離するよう設計されています。paper_trading 用 DB パスを確認してください。
- OpenAI 等の外部 API 呼び出しはネットワークエラーやレート制限に対しリトライやフォールバック（0.0 等）でフェイルセーフ化されていますが、API キーは必ず管理してください。
- run_execution / run_monitoring は起動時にプロセス優先度を上げようとします。権限が足りない場合は警告が出ますが実行は継続します。

トラブルシューティング（よくある原因）
----------------------------------
- 起動時に ValueError: 環境変数 'XXX' が設定されていません
  - 必須環境変数が不足しています。.env を確認してください。自動ロードを無効化している場合は手動で設定してください。
- OpenAI API に関する例外
  - OPENAI_API_KEY が未設定、もしくはレート制限／ネット障害。ログにバックオフと警告が出ます。
- Streamlit で DB を読み込めない
  - monitoring DB が存在しない、もしくは別プロセスがロックしている可能性。まず MonitoringEngine を起動して DB を作成してください。

貢献・ライセンス
----------------
- この README 内では特にライセンス指定をしていません。運用時は適切なライセンスファイルを追加してください。

補足
----
- この README はコードベースの主な機能と起動方法を簡潔にまとめたものです。詳細なアルゴリズム説明（PortfolioConstruction.md、StrategyModel.md 等）は別ドキュメントを参照してください（リポジトリに含まれる場合）。

何か追加で README に入れたい情報（例えば実際の .env.example、requirements.txt の内容、起動サンプルログ等）があれば教えてください。README をそれに合わせて更新します。