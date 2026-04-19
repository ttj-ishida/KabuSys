KabuSys — 日本株自動売買システム（README）
================================

概要
----
KabuSys は日本株の自動売買・リサーチ・監視を目的とした Python ベースのシステムです。本リポジトリは以下の主要機能を備えています。

- 実行エンジン（ExecutionEngine）: 発注・注文管理・リスク管理（本番 / ペーパートレード対応）
- 監視（Monitoring）: システム状態・オーダー・リスク監視、Kill Switch による自動停止
- ポートフォリオ構築・サイズ決定ロジック（純粋関数群）
- 研究（Research）: ファクター計算、将来リターン・IC 計算、特徴量要約
- AI サービス: ニュースの NLP スコアリング、レジーム判定（OpenAI API 経由）
- 運用ツール: 環境設定ウィザード、設定検証、Paper Trading 検証レポート生成

主な設計方針
- モジュールは可能な限り副作用を排し、DuckDB/SQLite 接続を外部から注入することでテスト容易性を確保
- 本番 DB（monitoring）と paper_trading DB は分離
- LLM 呼び出しはフェイルセーフで、失敗時はフォールバック動作を採用
- .env による設定管理と Wizard / Validator を提供

機能一覧
--------
- 環境設定ウィザード（python -m kabusys.config_setup）で .env を対話式生成・更新
- 設定検証 CLI（python -m kabusys.validate_config）
- ExecutionEngine 起動スクリプト（python -m kabusys.run_execution）
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使い、paper_trading DB に記録
  - 停止フラグ（data/stop_requested.flag / data/kill.flag）を検知して安全に停止
- Monitoring 起動スクリプト（python -m kabusys.run_monitoring）
  - システム / 注文 / リスク監視をポーリングして DB（SQLite）に永続化
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を指定可能（デフォルト 60 秒）
- Monitoring の永続化層（monitoring_db）: system_status / trade_logs / positions / risk_logs / dashboard を管理
- RiskMonitor / TradeMonitor / SystemMonitor / KillSwitch / AlertManager の統合（MonitoringEngine）
- ポートフォリオ構築:
  - 候補選定（select_candidates）
  - 重み計算（等分配 / スコア加重）
  - 単元株丸め・リスクベースのポジションサイズ計算（calc_position_sizes）
  - セクター上限・レジーム乗数（apply_sector_cap, calc_regime_multiplier）
- 研究モジュール:
  - モメンタム・ボラティリティ・バリュー計算（calc_momentum, calc_volatility, calc_value）
  - 将来リターン・IC・統計サマリ（calc_forward_returns, calc_ic, factor_summary）
- AI モジュール:
  - ニュース記事の銘柄ごとのセンチメントスコア化（kabusys.ai.score_news）
  - マーケットレジーム判定（kabusys.ai.regime_detector.score_regime）
- 運用ツール:
  - Paper Trading 検証レポート生成（python -m kabusys.tools.paper_verification_report）

セットアップ手順
---------------
前提
- Python 3.9+（できれば最新の安定版）
- システムに依存するライブラリ（psutil 等）が必要

依存パッケージ（例）
- duckdb
- psutil
- openai
- PyYAML（config ファイル検証にのみ必要）
- （必要に応じて）その他 ExecutionEngine が依存するブローカークライアント関連パッケージ

インストール例（仮）
- 仮想環境を作成・有効化
  - python -m venv .venv
  - source .venv/bin/activate  （Windows: .venv\Scripts\activate）
- 必要パッケージをインストール
  - pip install duckdb psutil openai PyYAML

（プロジェクトに requirements.txt がある場合はそれを使ってください。）

環境変数／.env
- 必須:
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- 推奨 / 任意:
  - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
  - DUCKDB_PATH — デフォルト: data/kabusys.duckdb
  - SQLITE_PATH — デフォルト: data/monitoring.db
  - PAPER_TRADING_SQLITE_PATH — paper_trading 専用 DB（デフォルト: data/paper_trading.db）
  - LOG_LEVEL — デフォルト: INFO
  - OPENAI_API_KEY — AI モジュール利用時に必要
  - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — 本番アラート用（任意）
  - PAPER_FILL_MODE — ペーパートレードの約定モード（instant/partial/never/reject）
- .env の作成:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config
  - --strict を付けると警告も失敗扱い（exit 1）

ディレクトリ・ファイルの初期化
- data/ や logs/ は起動時に自動作成される箇所がありますが、権限に注意してください。
- 停止フラグ / PID ファイル:
  - data/stop_requested.flag （起動監視スクリプトが利用）
  - data/execution.pid 他（ExecutionEngine が書き込み）

使い方
------
起動・停止
- ExecutionEngine（発注側）を起動:
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading をセットすると paper_trading 用の DB に記録し、MockBroker を使用
  - ExecutionEngine は data/stop_requested.flag を監視して停止します。KillSwitch により data/kill.flag が書かれると停止条件となります。
- Monitoring（監視側）を起動:
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
    - MONITOR_POLL_INTERVAL: ポーリング間隔（秒、デフォルト 60）
  - Monitoring は常に本番用 sqlite_path（Settings.sqlite_path）を参照します（環境に依存せず監視 DB を使う設計）
- .env の生成／編集:
  - python -m kabusys.config_setup
- 設定の検証:
  - python -m kabusys.validate_config [--strict]

ツール
- Paper Trading 検証レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db オプションで DB パスを指定可能（無指定時は PAPER_TRADING_SQLITE_PATH 環境変数または data/paper_trading.db）
- AI / 研究関数（プログラム内から利用）:
  - 例: ニュース NLP（ai.score_news）
    - import duckdb, datetime
    - conn = duckdb.connect("data/kabusys.duckdb")
    - from kabusys.ai import score_news
    - score_news(conn, datetime.date(2026, 4, 10), api_key="あなたのキー")  # 書き込み対象は ai_scores テーブル
  - 例: レジーム判定（ai.regime_detector.score_regime）
    - from kabusys.ai.regime_detector import score_regime
    - score_regime(conn, target_date, api_key=...)
- 研究モジュール例:
  - from kabusys.research import calc_momentum
  - result = calc_momentum(duckdb_conn, datetime.date(2026, 4, 10))

運用上の注意
- 本番環境（KABUSYS_ENV=live）では Kill Switch / LINE 通知設定を必ず確認してください。
- .env は機密情報を含むため Git 管理対象から除外してください（README 先頭の警告などで注記されています）。
- OpenAI を使う機能は API キー管理とコストに注意してください。失敗時はフォールバック動作が入りますが、設計上 API 呼び出しは外部サービスに依存します。

ディレクトリ構成（抜粋）
-----------------------
以下は src/kabusys 以下の主要なファイル・パッケージ構成（本 README を作成した時点での抜粋）です。

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数 / Settings
  - config_setup.py           — .env 対話式ウィザード
  - validate_config.py        — 設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — Monitoring 起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py
  - ai/
    - __init__.py
    - news_nlp.py             — ニュース NLP スコアリング（OpenAI）
    - regime_detector.py      — 市場レジーム判定（OpenAI）
  - monitoring/
    - monitoring_db.py        — SQLite 永続化層
    - monitoring_engine.py
    - system_monitor.py
    - trade_monitor.py        — （省略されているが監視の一部）
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py        — （実装ファイルが別途存在する想定）
  - portfolio/
    - __init__.py
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - utils/
    - __init__.py
    - logging_setup.py
    - process_priority.py
  - その他:
    - execution/               — ExecutionEngine 周りの実装（OrderManager 等; 実装ファイルが含まれる）
    - data/                    — データパイプライン / DuckDB スキーマ関連（prices_daily 等）

（注）実際のリポジトリには上記以外にも execution や data、strategy に属するモジュールが存在します。上のツリーは本 README 作成時に参照した主要部分の抜粋です。

開発・寄稿のヒント
- 単体テストは副作用を注入（モック）して実行可能にする設計が意図されています（例: OpenAI 呼び出しをラップして差し替え）。
- DuckDB / SQLite のスキーマはモジュール内で明示されているため、テスト用 DB を作って各関数を検証できます。
- ロギングは共通ユーティリティ（kabusys.utils.logging_setup.setup_logging）で統一してください。

ライセンス・バージョン
- パッケージバージョンは kabusys.__version__ = "0.1.0" に設定されています。
- ライセンス情報はリポジトリのルート（LICENSE 等）を参照してください（本コード中にはライセンス記載がありません）。

補足・トラブルシューティング
- ログが出力されない／ファイルハンドラが作れない場合は、logs ディレクトリの権限を確認してください。logging_setup は作成失敗時にコンソール出力へフォールバックします。
- psutil によるプロセス優先度設定は OS に依存します。権限不足で警告が出ることがありますが、致命的ではありません。
- DuckDB / SQLite のファイルパスは Settings（環境変数）で上書きできます。paper_trading 用 DB と本番 DB を混同しないよう注意してください。

以上。必要であれば README に含める具体的なサンプル .env（機密を除く）や systemd / cron の起動例、より詳細なディレクトリツリーを追記します。どの情報を追加したいか教えてください。