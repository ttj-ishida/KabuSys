KabuSys — 日本株自動売買システム（README）
======================================

概要
----
KabuSys は日本株の自動売買プラットフォーム向けに設計された Python コードベースです。  
主に次の機能群を含みます:

- 注文管理・発注エンジン（Execution）
- 監視（System / Trade / Risk）およびアラート（LINE）
- ポートフォリオ構築（候補選定・重み付け・株数決定）
- リサーチ（ファクター計算・特徴量解析）
- ニュース NLP / 市場レジーム判定（OpenAI を利用したセンチメント評価）
- Paper Trading 用検証レポート生成、Streamlit ダッシュボード

主な設計方針:
- DB（SQLite / DuckDB）を使ったローカル永続化
- Paper Trading と本番（live）を分離可能
- LLM 呼び出しはフェイルセーフ（API 失敗時はフォールバック）

特徴一覧
--------
- ExecutionEngine 起動スクリプト（run_execution）:
  - KABUSYS_ENV=paper_trading の場合は MockBroker を使い paper_trading DB に記録
  - プロセスの優先度設定、PID 管理、停止フラグ対応
- Monitoring（run_monitoring / MonitoringEngine）:
  - システム状態（CPU/MEM/DISK）、データ鮮度、滞留注文、約定異常、ドローダウン等の監視
  - 監視ログは SQLite（data/monitoring.db デフォルト）へ保存
  - LINE によるアラート送信（AlertManager）
  - KillSwitch による安全停止（kill.flag）
  - Streamlit ダッシュボードで可視化
- Portfolio モジュール:
  - 候補選定 (select_candidates)、等配分／スコア配分、リスク調整、ポジションサイズ計算
- Research:
  - DuckDB を用いたファクター計算（Momentum / Volatility / Value）
  - 将来リターン・IC 計算など
- AI:
  - news_nlp.score_news: raw_news を LLM（OpenAI）でセンチメント集約・ai_scores 書き込み
  - regime_detector.score_regime: ETF とマクロ記事を合成して market_regime を決定
- Tools:
  - paper_verification_report: paper_trading DB の検証レポート生成
  - streamlit ダッシュボード（監視用）

セットアップ手順
----------------
前提:
- Python 3.10+ を推奨
- DuckDB、psutil、openai、requests、streamlit などが必要

1. リポジトリを取得
   - git clone ...（省略）

2. 仮想環境を作成・有効化（例）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - pip install duckdb psutil openai requests streamlit
   - （プロジェクトに requirements.txt がある場合は pip install -r requirements.txt）

4. 環境変数 / .env
   - プロジェクトルートに .env を置くと自動読み込みされます（.env.local も利用可）。
   - 自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。
   - 必須（運用に必要）:
     - JQUANTS_REFRESH_TOKEN=...
     - KABU_API_PASSWORD=...
   - OpenAI を使う場合:
     - OPENAI_API_KEY=...
   - 任意:
     - LINE_CHANNEL_ACCESS_TOKEN=...
     - LINE_USER_ID=...
   - 主な設定例:
     - KABUSYS_ENV=development|paper_trading|live
     - PAPER_FILL_MODE=instant|partial|never|reject
     - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
     - SQLITE_PATH=data/monitoring.db
     - DUCKDB_PATH=data/kabusys.duckdb
     - PID_FILE_PATH=data/execution.pid
     - KILL_FLAG_PATH=data/kill.flag
     - LOG_LEVEL=INFO
   - Settings クラスが多くのデフォルト値を提供します（kabusys/config.py を参照）。

5. データディレクトリ
   - data/ 配下に DB や flag を置きます（自動生成されるケースもあります）。

使い方
-----
- 監視ループの起動（Monitoring）
  - デフォルトは MONITOR_POLL_INTERVAL=60 秒（環境変数で上書き可能）
  - 実行:
    - python -m kabusys.run_monitoring
  - 強制停止:
    - プロセスに KeyboardInterrupt（Ctrl+C）を送るか、プロジェクトルート/data/stop_requested.flag を作成するとループが検出して終了します。

- 実行エンジン起動（Execution）
  - KABUSYS_ENV=paper_trading のとき paper_trading DB（PAPER_TRADING_SQLITE_PATH）を使用
  - 実行:
    - python -m kabusys.run_execution
  - 停止:
    - プロジェクトルート/data/stop_requested.flag を作成すると実行中の Engine を停止します。
  - Execution 用一時ファイル:
    - data/execution.pid（PID を書き込む）

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD （開始日）
    - --to YYYY-MM-DD   （終了日）
    - --db PATH         （SQLite DB パス。環境変数 PAPER_TRADING_SQLITE_PATH > デフォルト）
  - 例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

- Streamlit 監視ダッシュボード
  - 起動:
    - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - 読み取り専用で SQLite を開きます（DB が存在しない場合はエラー表示）。

- AI（ニューススコア / レジーム判定）
  - OpenAI API キー（OPENAI_API_KEY）が必要。
  - モジュール関数を直接呼ぶ（サンプル）:
    - from kabusys.ai.news_nlp import score_news
    - score_news(conn, target_date, api_key="...")
  - 同様に regime_detector.score_regime で market_regime を書き込みます。

- 停止・キルシグナル
  - kill.flag: KillSwitch が判断して書き込む（ExecutionEngine に停止指示）
  - stop_requested.flag: 起動スクリプトが検知して自プロセスを終了する汎用フラグ
  - フラグのクリア:
    - rm data/kill.flag
    - rm data/stop_requested.flag
  - KillSwitch を使って手動で停止したい場合は reason を書き込むようなユーティリティを作成しても良いです（KillSwitch クラスを参照）。

ディレクトリ構成（主要ファイル）
-----------------------------
（src/kabusys 内を抜粋）

- kabusys/
  - __init__.py            — パッケージ定義
  - config.py              — 環境変数 / Settings 管理（.env 自動ロード機構含む）
  - run_monitoring.py      — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py       — ExecutionEngine 起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート
  - execution/
    - execution_engine.py  — 実行エンジン（外部参照あり）
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - broker_factory.py
    - …（発注関連実装）
  - monitoring/
    - monitoring_db.py     — SQLite スキーマ初期化・永続化操作
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - monitoring_engine.py
    - alert_manager.py
    - kill_switch.py
    - streamlit_dashboard.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py          — ニュース -> LLM -> ai_scores 書き込み
    - regime_detector.py   — マクロ + ETF MA200 によるレジーム判定
  - data/ （実行時に使用する DB やフラグを格納する想定のディレクトリ）
    - monitoring.db (default)
    - paper_trading.db (default)
    - kabusys.duckdb (default)
    - execution.pid
    - stop_requested.flag
    - kill.flag

補足（実装上の注意点）
--------------------
- Settings:
  - .env / .env.local をプロジェクトルートから自動読み込みします（ただし OS 環境変数が優先）。
  - 自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DB:
  - monitoring 側は init_monitoring_db() でテーブルと簡単なマイグレーションを実行します。
  - run_monitoring は KABUSYS_ENV にかかわらず sqlite_path（本番用）を使用します。run_execution は paper_trading 環境時に paper_sqlite_path を使用します。
- OpenAI:
  - API 呼び出しはリトライ・バックオフを実装していますが、API キー未設定の場合は関数が ValueError を送出します。テスト時は該当関数をモック可能です（コード内でその旨を想定）。
- プロセス優先度: psutil を用いてプラットフォームごとに優先度/nice を設定します。権限不足時は警告を出しスキップします。

トラブルシューティング
----------------------
- DB がない / 開けない:
  - path を確認。Streamlit は読み取り専用で URI を使って開くため、パスの解決に注意。
- 環境変数が読み込まれない:
  - .env の場所はプロジェクトルート（.git / pyproject.toml を含むディレクトリ）を自動検出します。CWD に依存しません。
- OpenAI 関連が失敗する:
  - OPENAI_API_KEY の設定を確認。API レスポンスのパースに失敗した場合はログに出力され、処理はスキップ（フェイルセーフ）されます。

ライセンス / コントリビュート
-----------------------------
- この README にはライセンス情報は含めていません。リポジトリに LICENSE ファイルがあればそちらを参照してください。
- 貢献・修正は PR と issue を通じて行ってください。

以上が主要な利用方法と構成の概要です。詳細は各モジュール（kabusys/ 以下の各ファイル）の docstring とログ出力を参照してください。必要なら運用向けのデプロイ手順（systemd / supervisor の Unit ファイル例、Docker 化など）や example .env を追記しますのでお知らせください。