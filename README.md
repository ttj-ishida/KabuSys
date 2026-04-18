KabuSys
=======

日本株自動売買システムのコードベース（ライブラリ + 起動スクリプト群）のまとめドキュメントです。  
この README ではプロジェクト概要、機能、セットアップ手順、使い方、主要ディレクトリ構成について日本語で説明します。

※ 本 README は src/kabusys 配下のコードを参照して作成しています。

プロジェクト概要
---------------
KabuSys は日本株自動売買のためのモジュール群と起動スクリプト群を備えたシステムです。主な責務は以下のとおりです。

- 市場データ（DuckDB）を使ったファクター / リサーチ（factor 計算、将来リターン、IC 等）
- ポートフォリオ構築（候補選定、重み付け、ポジションサイジング、セクターキャップ、レジーム補正）
- ExecutionEngine（発注管理・リスク管理・ブローカークライアント抽象化）
- Monitoring（システム稼働監視・トレードログ監視・リスク監視・Kill Switch）
- AI 補助（ニュースの NLP スコアリング、マクロセンチメントによるレジーム判定）
- 開発支援ツール（.env ウィザード、設定検証、ペーパートレード検証レポート生成）

主な設計方針：
- DB（DuckDB / SQLite）や外部 API へのアクセスは明示的で、研究系コードは本番 API に依存しない。
- Paper Trading（KABUSYS_ENV=paper_trading）は本番 DB と分離され、Mock ブローカーを使用。
- AI 呼び出し（OpenAI）は失敗時にフォールバックするフェイルセーフ実装。

主な機能一覧
--------------
- 環境設定（.env）ウィザード: python -m kabusys.config_setup
- 設定検証 CLI: python -m kabusys.validate_config [--strict]
- 実行エンジン起動（ExecutionEngine）: python -m kabusys.run_execution
  - PaperTrading では MockBrokerClient を使用し、data/paper_trading.db に記録
- 監視ループ起動（Monitoring）: python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更可能（デフォルト 60 秒）
  - 監視は monitoring 用 sqlite（デフォルト data/monitoring.db）を使用
- AI:
  - ニュース NLP（銘柄別センチメント -> ai_scores テーブルへの書込み）
  - レジーム判定（ETF MA200 とマクロニュースの LLM 評価を合成）
- 研究用モジュール:
  - ファクター計算（momentum/value/volatility）
  - 将来リターン / IC / ファクタサマリー
- ポートフォリオ構築:
  - 候補選定、等金額・スコア重み、ポジションサイズ計算（単元株・コストバッファ考慮）
  - セクター集中防止、レジーム乗数
- 監視:
  - SystemMonitor / TradeMonitor / RiskMonitor 組み合わせによる定期チェック
  - KillSwitch によるフラグファイルでの ExecutionEngine 停止指示
- ツール:
  - Paper Trading 検証レポート生成: python -m kabusys.tools.paper_verification_report

セットアップ手順
----------------
前提:
- Python 3.10 以上（typing に | を使用しているため）
- SQLite は標準ライブラリで利用可能
- システム依存で psutil（プロセス優先度 / CPU affinity 等）を使用

推奨パッケージ（pip インストール例）:
- duckdb
- psutil
- openai (AI 機能を利用する場合)
- PyYAML (validate_config で config/*.yaml の内容を検証したい場合)

例:
    python -m pip install duckdb psutil openai pyyaml

プロジェクト初期設定:
1. プロジェクトルートに移動（.git または pyproject.toml が存在する場所）。
2. .env を生成 / 更新:
    python -m kabusys.config_setup
   ウィザードに従って J-Quants / kabu API トークン等を入力してください。
3. 設定を検証:
    python -m kabusys.validate_config
   --strict を付けると警告も失敗扱いになります。

主要な環境変数（重要なもののみ）:
- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- OPENAI_API_KEY: OpenAI API キー（AI 機能利用時）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（監視 DB。デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB。デフォルト: data/paper_trading.db）
- LOG_LEVEL（デフォルト: INFO）
- LOG_DIR（デフォルト: logs/）
- MONITOR_POLL_INTERVAL（監視ポーリング秒。デフォルト: 60）
- PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START（Execution/監視関連）
- PAPER_FILL_MODE（paper_trading の約定挙動: instant|partial|never|reject）

使い方（起動 / 実行例）
----------------------

1) 環境設定
- ウィザードで .env を作成:
    python -m kabusys.config_setup

- 設定検証:
    python -m kabusys.validate_config
    python -m kabusys.validate_config --strict

2) 実行エンジン（ExecutionEngine）
- 本番 / 開発 / ペーパートレードの切替は KABUSYS_ENV で行います。
- 起動:
    python -m kabusys.run_execution

- 停止方法:
  - 実行ファイルは data/stop_requested.flag を監視します。停止させたい場合はプロジェクトルートの data/stop_requested.flag を作成してください。
  - KillSwitch による停止は data/kill.flag を書き込むことで行われます（監視側が条件を満たしたときに書き出す）。

3) 監視ループ
- 起動:
    python -m kabusys.run_monitoring
- ポーリング間隔を変更する場合:
    export MONITOR_POLL_INTERVAL=30
    python -m kabusys.run_monitoring
- 監視ループは stop_requested.flag をチェックして終了します。

4) Paper Trading 検証レポート
- paper_trading 用 DB を指定して期間を指定できます:
    python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- DB パスは環境変数 PAPER_TRADING_SQLITE_PATH で指定可能、または --db オプションで上書き可。

5) AI 機能（ニュース NLP / レジーム判定）
- OpenAI API キーが必要です（OPENAI_API_KEY）。
- モジュールをプログラムから呼び出す例:
    from kabusys.ai.news_nlp import score_news
    score_news(conn, target_date, api_key="sk-...")

注意点 / 運用メモ
- run_monitoring は監視用 DB（SQLite）に常に本番の sqlite_path を使います（KABUSYS_ENV にかかわらず）。
- run_execution は KABUSYS_ENV=paper_trading のとき paper_sqlite_path を使用して本番 DB と分離します。
- .env は絶対に Git にコミットしないでください（config_setup の出力ヘッダにも注意書きあり）。
- ログはデフォルト logs/<app_name>.log に日次ローテーションで出力されます。LOG_DIR を指定可能。
- OpenAI 呼び出しはリトライ等のフェイルセーフを備えていますが、API キーのレート制限や料金には注意してください。
- process_priority.set_process_priority() により起動時にプロセス優先度を "high" に設定します（環境によっては失敗して警告が出ます）。

ディレクトリ構成（主要ファイル）
-----------------------------
以下は src/kabusys 配下の主要なモジュール構成（抜粋）です。

- src/kabusys/
  - __init__.py
  - config.py                # 環境変数 / Settings
  - config_setup.py          # .env 対話ウィザード
  - validate_config.py       # 設定検証 CLI
  - run_execution.py         # ExecutionEngine 起動スクリプト
  - run_monitoring.py        # Monitoring 起動スクリプト

  - ai/
    - news_nlp.py            # ニュース NLP スコアリング
    - regime_detector.py     # レジーム判定（MA200 + マクロニュース）
  - monitoring/
    - monitoring_db.py       # SQLite 用永続化層
    - system_monitor.py      # システム / データ鮮度監視
    - trade_monitor.py       # （省略したがトレード監視実装）
    - risk_monitor.py        # ドローダウン / ポジション上限監視
    - kill_switch.py         # kill.flag 管理
    - monitoring_engine.py   # 各監視を束ねるエンジン
    - alert_manager.py       # （アラート送信管理：LINE など）
  - execution/
    - execution_engine.py    # ExecutionEngine 本体（発注ループ）
    - broker_factory.py      # BrokerClientFactory（Mock/実ブローカー切替）
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
  - portfolio/
    - portfolio_builder.py   # 候補選定 / 重み付け
    - position_sizing.py     # 株数決定 / aggregate cap 等
    - risk_adjustment.py     # セクターキャップ・レジーム乗数
  - research/
    - factor_research.py     # Momentum / Value / Volatility
    - feature_exploration.py # IC 等の統計解析
  - data/                     # （実行時生成）data/*.db, flag ファイル など
  - tools/
    - paper_verification_report.py  # ペーパートレード検証レポート

補足: data / logs / config
- デフォルトの DB / PID / flag やログディレクトリ:
  - data/kabusys.duckdb (default DUCKDB_PATH: data/kabusys.duckdb)
  - data/monitoring.db (default SQLITE_PATH: data/monitoring.db)
  - data/paper_trading.db (PAPER_TRADING_SQLITE_PATH)
  - data/execution.pid
  - data/stop_requested.flag
  - data/kill.flag
  - logs/<app_name>.log

最後に
------
本 README はコードコメント・実装をベースにした概要説明です。実運用前に以下を推奨します。

- python -m kabusys.config_setup で .env を作成
- python -m kabusys.validate_config で設定検証（--strict も検討）
- テスト環境で Execution / Monitoring を動作確認（paper_trading モード推奨）
- AI 機能を使う際は OPENAI_API_KEY と利用ポリシー・料金を確認

追加で README に入れたい詳細（例：CLI オプションの全一覧、API の詳細な呼び出し例、ユニットテスト実行方法等）があれば教えてください。必要に応じて追記します。