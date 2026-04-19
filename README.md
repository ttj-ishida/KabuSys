# KabuSys — README (日本語)

本ドキュメントはソースツリー内の主要スクリプト／モジュールを基にした README です。KabuSys は日本株向けの自動売買／リサーチ基盤で、監視・実行・リサーチ・AI スコアリング等の機能を提供します。

注意: この README はコードベースのコメント・実装に基づいて作成しています。実際の運用前に必ず設定ファイル (.env / config/*.yaml) を確認してください。

概要
- KabuSys は日本株の自動売買システムの基盤ライブラリ／スクリプト群です。
- 構成要素: ExecutionEngine（発注実行）、Monitoring（システム・取引の監視 & Kill Switch）、研究モジュール（ファクター計算等）、AI モジュール（ニュースセンチメント評価）、ポートフォリオ構築ユーティリティ、ツール類（ペーパートレード検証レポート生成）など。
- DB: 分析用に DuckDB、監視・ログ用に SQLite を使用。ペーパートレードは本番 DB と分離可能。

主な機能一覧
- 実行（run_execution.py）
  - live / paper_trading / development を切り替え可能（KABUSYS_ENV）。
  - paper_trading では MockBrokerClient を用い、専用 SQLite（data/paper_trading.db）に記録。
  - リスク管理（RiskManager）、OrderManager、Reconciler、ExecutionEngine によるセッション実行。
  - PID ファイル管理、停止フラグ（data/stop_requested.flag）監視。

- 監視（run_monitoring.py と monitoring パッケージ）
  - SystemMonitor: CPU/MEM/DISK、Execution プロセス生存、データ鮮度チェック。
  - TradeMonitor / RiskMonitor: 滞留注文・約定異常・ドローダウン・ポジション上限の監視。
  - KillSwitch: 条件を満たした場合に data/kill.flag を書き込み、ExecutionEngine の停止シグナルを送出。
  - MonitoringEngine: 各モニタをまとめて定期ポーリング（ポーリング間隔は環境変数で上書き可）。

- AI（kabusys.ai）
  - news_nlp: OpenAI（gpt-4o-mini）によるニュースセンチメントスコアリング（ai_scores テーブルへ書き込み）。
  - regime_detector: ETF（1321）MA200 とマクロニュースを合わせて市場レジーム判定を行い market_regime に保存。
  - API 呼び出しはリトライ・バリデーション実装あり。OPENAI_API_KEY を使用。

- 研究（kabusys.research）
  - ファクター計算: momentum / volatility / value 等（DuckDB の prices_daily / raw_financials を参照）。
  - 特徴量探索: 将来リターン計算、IC（スピアマン）、統計サマリー等。

- ポートフォリオ（kabusys.portfolio）
  - 候補選定、重み計算（等金額 / スコア加重）、セクター上限適用、レジーム乗数、ポジションサイズ算出（単元株丸め等）。

- ツール
  - config_setup.py: .env を対話的に作成・更新するウィザード。
  - validate_config.py: .env と config/*.yaml の簡易検証 CLI（--strict オプションあり）。
  - tools/paper_verification_report.py: ペーパートレード DB から検証レポートを生成（稼働率・注文成功率・レイテンシ等）。

セットアップ手順（概略）
1. Python バージョン
   - Python 3.10 以上（型注釈で | を使用しているため）。

2. 依存パッケージのインストール（例）
   - pip install duckdb psutil openai
   - （オプション）PyYAML（config 検証で YAML パースを行う場合）: pip install pyyaml

   実際の requirements.txt がある場合はそれに従ってください。

3. プロジェクトルートに移動し .env を作成
   - 対話式生成:
     python -m kabusys.config_setup
   - 主要な必須環境変数:
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
   - その他:
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（デフォルト: data/paper_trading.db）
     - LOG_LEVEL（デフォルト: INFO）
     - OPENAI_API_KEY（AI 機能使用時に必要）

4. 設定検証
   python -m kabusys.validate_config
   - --strict をつけると警告も失敗扱い（exit code 1）になります。

5. データディレクトリ作成（必要に応じて）
   - data/（SQLite・PID/フラグファイル用）
   - logs/（ログ出力。ログディレクトリ作成に失敗するとコンソールのみにフォールバックします）

使い方（主要スクリプト）
- 実行エンジン起動（デーモン／手動実行）
  python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合、ペーパートレード用 DB（data/paper_trading.db）に分離して記録されます。
  - 実行はバックグラウンドスレッドで Session を開始し、data/stop_requested.flag の検知で停止します。
  - プロセス優先度は起動時に high に設定されます（権限不足で失敗することがあります）。

- 監視起動
  python -m kabusys.run_monitoring
  - デフォルトポーリング間隔: 60 秒
  - 環境変数 MONITOR_POLL_INTERVAL で上書き可（例: MONITOR_POLL_INTERVAL=30）
  - 監視は MonitoringDB（SQLite）へログを残します。Monitoring は KABUSYS_ENV に関わらず sqlite_path（本番）を使用します。

- ペーパートレード検証レポート
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db で DB パスを指定可能（環境変数 PAPER_TRADING_SQLITE_PATH > デフォルト）。
  - レポートは稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）等を出力し PASS/FAIL 判定を行います。

- .env ウィザード / 設定検証
  python -m kabusys.config_setup
  python -m kabusys.validate_config [--strict]

停止 / Kill Switch / フラグについて
- run_execution と run_monitoring はそれぞれ data/stop_requested.flag を監視して優雅に終了します（手動でフラグを作ることで停止可能）。
- KillSwitch（監視側）: リスク条件（ドローダウン閾値超過・ポジション上限超過等）を満たすと data/kill.flag を書き込み、ExecutionEngine 側でこれを検出して停止させる運用を想定しています。
- 設定により KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に kill.flag を自動でクリアします（本番環境では 0 推奨）。

ログ設定
- 共通ユーティリティ: kabusys.utils.logging_setup.setup_logging(app_name="execution" 等)
  - stdout（StreamHandler）と日次ローテーションのファイルハンドラ（logs/<app_name>.log）を設定します。
  - 環境変数 LOG_LEVEL / LOG_DIR で挙動を制御可能。

環境変数（主なもの）
- 必須:
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- 運用:
  - KABUSYS_ENV: development | paper_trading | live
  - DUCKDB_PATH (default: data/kabusys.duckdb)
  - SQLITE_PATH (default: data/monitoring.db)
  - PAPER_TRADING_SQLITE_PATH (default: data/paper_trading.db)
  - LOG_LEVEL (default: INFO)
  - LOG_DIR (default: logs/)
  - OPENAI_API_KEY（AI 機能を使う場合）
  - MONITOR_POLL_INTERVAL（監視のポーリング間隔秒、デフォルト 60）
  - PAPER_FILL_MODE（paper_trading の約定挙動: instant|partial|never|reject、デフォルト instant）
  - KILL_FLAG_CLEAR_ON_START（起動時に kill.flag を消す: 1=消す、0=消さない）

ディレクトリ構成（主要ファイル・モジュール）
- src/kabusys/
  - __init__.py
  - config.py              — 環境変数読み込み・Settings クラス、自動 .env ロード機能
  - config_setup.py        — .env 対話式ウィザード
  - validate_config.py     — 設定検証 CLI
  - run_execution.py       — ExecutionEngine 起動スクリプト
  - run_monitoring.py      — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート生成 CLI
  - ai/
    - news_nlp.py           — ニュースを OpenAI でスコアリングして ai_scores に書き込み
    - regime_detector.py    — マクロ + MA200 による市場レジーム判定
  - portfolio/
    - portfolio_builder.py  — 候補選定・重み計算
    - position_sizing.py    — 発注株数算出・aggregate cap
    - risk_adjustment.py    — セクター制限・レジーム乗数
  - research/
    - factor_research.py    — ファクター計算 (momentum/value/volatility)
    - feature_exploration.py— 将来リターン / IC / 統計サマリー
  - monitoring/
    - monitoring_db.py      — SQLite 用の永続化層（テーブル初期化・CRUD）
    - system_monitor.py     — CPU/MEM/DISK・データ鮮度・PID 監視
    - risk_monitor.py       — ドローダウン / ポジション上限監視
    - trade_monitor.py      — （取引監視ロジック、コード内参照）
    - monitoring_engine.py  — 各 Monitor を束ねるエンジン
    - kill_switch.py        — kill.flag の書込・評価ロジック
    - alert_manager.py      — アラート送信管理（LINE など）（コード参照）
  - utils/
    - logging_setup.py      — ロギング初期化ユーティリティ
    - process_priority.py   — プロセス優先度 / CPU affinity 設定
  - data/                  — （実行時生成される DB / PID / flag 等）
    - monitoring.db (SQLITE_PATH)
    - paper_trading.db (PAPER_TRADING_SQLITE_PATH)
    - kabusys.duckdb (DUCKDB_PATH)
    - execution.pid
    - stop_requested.flag
    - kill.flag

運用上の注意
- 本番（KABUSYS_ENV=live）時は設定や API キー、Kill Switch の取り扱いを厳重に管理してください。
- .env をリポジトリにコミットしないこと（config_setup.py のヘッダにも注意書きあり）。
- OpenAI キーやブローカーパスワード等の秘密情報は環境変数または安全なシークレットマネージャで管理してください。
- Monitoring は監視用 DB（sqlite_path）へログを残します。run_monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する設計です。

トラブルシューティング（簡易）
- ログが出力されない / ファイルハンドラが作れない:
  - LOG_DIR のパーミッションを確認。ディレクトリ作成に失敗するとコンソール出力のみになります。
- .env 自動ロードが効かない:
  - KABUSYS_DISABLE_AUTO_ENV_LOAD を設定していないか確認。またプロジェクトルート判定は .git または pyproject.toml を探索します。
- OpenAI や DuckDB に関連する ImportError:
  - 必要なパッケージがインストールされているか確認してください（duckdb, openai, psutil, pyyaml 等）。

最後に
この README はソースコード内のドキュメント文字列を元に作成しています。実際の運用では config/*.yaml や外部ドキュメント（PortfolioConstruction.md, StrategyModel.md 等）を参照の上、設定値を慎重に決定してください。必要があれば README をプロジェクト固有の手順に合わせて追記・修正してください。