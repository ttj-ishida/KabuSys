# KabuSys

日本株向け自動売買システムのコア実装（ライブラリ兼起動スクリプト群）

概要
- KabuSys は日本株自動売買のコアコンポーネント群を含む Python パッケージです。
- 発注/リスク/監視/ポートフォリオ構築/ファクター計算/AI（ニュース NLP）等の機能を持ち、実行スクリプトによりデーモン的に稼働させられます。
- 設定は .env（環境変数）および config/*.yaml で行います。Paper Trading（検証用）と Live の分離が考慮されています。

主な特徴（機能一覧）
- 実行（ExecutionEngine）起動スクリプト
  - run_execution.py：ExecutionEngine を起動。KABUSYS_ENV=paper_trading 時は MockBrokerClient を使用し、paper_trading 用 DB（data/paper_trading.db）に分離して記録。
- 監視（Monitoring）コンポーネント
  - run_monitoring.py：SystemMonitor のポーリングループ起動。MONITOR_POLL_INTERVAL で間隔を指定可能（デフォルト 60 秒）。
  - MonitoringEngine：SystemMonitor / TradeMonitor / RiskMonitor を束ねてアラート・KillSwitch 評価等を行う。
  - MonitoringDB：SQLite ベースの永続化（system_status, trade_logs, positions, risk_logs, dashboard）。
  - RiskMonitor / KillSwitch：ドローダウン監視、ポジション上限監視により kill.flag を発行。
- ポートフォリオ構築
  - 候補選定、等金額／スコア重み、リスク調整（セクター制限・レジーム乗数）、ポジションサイズ計算（単元株丸め、資金制約反映）等を提供する純粋関数群。
- リサーチ / ファクター計算
  - ファクター（Momentum / Volatility / Value）計算、将来リターン・IC 計算、統計サマリ等。DuckDB を用いた高速集計を前提。
- AI（ニュース NLP / レジーム判定）
  - news_nlp.score_news：OpenAI を使いニュース群を銘柄別にセンチメントスコア化して ai_scores テーブルへ保存。
  - regime_detector.score_regime：ETF（1321）MA とマクロニュースを合成して日次レジーム（bull/neutral/bear）を判定。
- ユーティリティ
  - 環境設定ウィザード（config_setup.py）、設定検証 CLI（validate_config.py）、Paper Trading レポート生成ツール（tools/paper_verification_report.py）。
  - ロギング設定（utils.logging_setup）、プロセス優先度設定（utils.process_priority）等。

セットアップ手順（開発 / 簡易）
1. Python（3.9+ 推奨）を用意
2. 必要パッケージをインストール
   - 最低依存例:
     - duckdb
     - psutil
     - openai
     - PyYAML （config YAML 検証時に任意）
   - 例:
     - pip install duckdb psutil openai PyYAML
   - （プロジェクトに requirements.txt がある場合はそれを使用してください。）
3. リポジトリルートで .env を作成
   - 対話式ウィザードを使う:
     - python -m kabusys.config_setup
   - あるいは .env を手動作成（.env.example があれば参照）
4. 設定検証
   - python -m kabusys.validate_config
   - (--strict を付けると警告も失敗扱い)
5. ディレクトリ作成（必要なら）
   - data/（SQLite 等のデータファイル置き場）
   - logs/（ログファイル）
   - ほとんどは起動時に自動作成されることが多いですが権限に注意してください。

主要な環境変数（概要）
- 必須:
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- 運用 / 動作関係:
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
  - SQLITE_PATH: 監視 DB（デフォルト data/monitoring.db）
  - DUCKDB_PATH: DuckDB ファイル（デフォルト data/kabusys.duckdb）
  - PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト data/paper_trading.db）
  - LOG_LEVEL: ログレベル（INFO 等）
  - OPENAI_API_KEY: OpenAI 呼出しに必要（AI 機能を使う場合）
- 監視関連:
  - MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒。デフォルト 60）
  - KILL_FLAG_CLEAR_ON_START: Execution 起動時に既存の kill.flag を自動クリア（1）するか（本番では 0 推奨）
- その他:
  - LOG_DIR: ログ出力先ディレクトリ（デフォルト logs/）

使い方（起動・主要コマンド）
- 環境設定ウィザード（.env の作成）
  - python -m kabusys.config_setup
- 設定検証
  - python -m kabusys.validate_config
- 監視ループ起動
  - python -m kabusys.run_monitoring
  - 環境変数でポーリング間隔変更:
    - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - run_monitoring は data/stop_requested.flag（プロジェクト内 data/stop_requested.flag）を検知するとループを終了します。
- 実行エンジン起動（ExecutionEngine）
  - python -m kabusys.run_execution
  - paper_trading モード例:
    - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  - 実行中に data/stop_requested.flag が作成されると停止を開始します。
- Paper Trading 検証レポート（CLI）
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - オプション --db で DB パスを指定可能（環境変数 PAPER_TRADING_SQLITE_PATH より優先）
- ライブラリ関数の利用例（Python から）
  - ポートフォリオ構築:
    - from kabusys.portfolio import select_candidates, calc_equal_weights, calc_score_weights, calc_position_sizes
  - リサーチ:
    - from kabusys.research import calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic
  - AI:
    - from kabusys.ai import score_news  # OpenAI API キーが必要

データ / ファイルフラグについて（運用メモ）
- stop_requested.flag
  - run_monitoring / run_execution が監視する停止指示ファイル（プロジェクトの data/ 配下に作成）。存在を検知すると安全に停止処理を行います。
- kill.flag
  - KillSwitch が条件を満たした際に書き込むファイル。ExecutionEngine に停止を促します（手動確認/解除が必要）。
- execution.pid / その他 PID ファイル
  - 実行エンジンの PID を記録することで stale PID 検出等に使用されます。

ログ
- ログ設定は kabusys.utils.logging_setup.setup_logging によって統一管理されます。
- デフォルトで console(stdout) と logs/<app_name>.log（TimedRotatingFileHandler、日次ローテート、30日分保持）に出力します。
- ログディレクトリは LOG_DIR 環境変数またはデフォルト logs/。権限によりファイル出力が失敗する場合はコンソール出力のみになります。

ディレクトリ構成（主要ファイル抜粋）
- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数 / Settings 管理（自動 .env ロード機能含む）
  - config_setup.py           — .env を対話式で作成するウィザード
  - validate_config.py        — 設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — SystemMonitor ポーリング起動スクリプト
  - utils/
    - logging_setup.py        — ログ設定ユーティリティ
    - process_priority.py     — プロセス優先度 / CPU affinity 設定
  - monitoring/
    - monitoring_db.py        — SQLite 用永続化層（テーブル初期化 / CRUD）
    - system_monitor.py       — システム状態 / データ鮮度監視
    - risk_monitor.py         — ドローダウン・ポジション上限監視
    - kill_switch.py          — kill.flag 制御
    - monitoring_engine.py    — 各監視を束ねるエンジン
    - (その他: trade_monitor.py, alert_manager.py など想定)
  - execution/                — ブローカー/エンジン/注文管理等（Engine, OrderManager 等）
  - portfolio/
    - portfolio_builder.py    — 候補選定・重み付け
    - position_sizing.py      — 株数決定・集計キャップ・単元処理
    - risk_adjustment.py      — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py      — momentum / volatility / value 等のファクター計算
    - feature_exploration.py  — forward returns / IC / summary
  - ai/
    - news_nlp.py             — ニュースセンチメント（OpenAI）
    - regime_detector.py      — レジーム判定（MA + マクロ NLP）
  - tools/
    - paper_verification_report.py — Paper Trading の検証レポート生成

運用上の注意 / トラブルシューティング
- 環境変数不備
  - 必須キー（JQUANTS_REFRESH_TOKEN / KABU_API_PASSWORD 等）が未設定だと起動に失敗する箇所があります。まず python -m kabusys.validate_config を実行して確認してください。
- OpenAI API
  - AI 関連機能を使用する場合は OPENAI_API_KEY を設定してください。API エラー時はフェイルセーフで進める設計の関数もありますが、期待どおりの結果が得られないことがあります。
- DB ファイルの場所・権限
  - デフォルトは data/ 以下。運用時は永続ストレージ・バックアップ・アクセス権に注意してください。
- process priority / cpu affinity
  - プロセス優先度の設定は psutil を使用して行います。権限不足により設定できない場合があります（警告ログとして落ちます）。
- Kill Switch の自動クリア
  - KILL_FLAG_CLEAR_ON_START=1 は便利ですが、本番環境では危険です。誤って Kill フラグをクリアしてしまう可能性があるためデフォルトは 0 を推奨します。

拡張ポイント / 開発メモ
- Broker クライアントは Factory で抽象化されており、paper_trading 用 Mock 実装と live 実装を切替可能。
- DuckDB を解析・リサーチ向けバックエンドとして使うため、prices_daily / raw_financials 等のテーブルを作成してデータ投入すればリサーチ機能を利用可能。
- テスト時は環境自動ロード（config.py の自動 .env 読み込み）を KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効にできます。

ライセンス / バージョン
- パッケージバージョン: __version__ = "0.1.0"（src/kabusys/__init__.py）
- ライセンス情報はリポジトリの LICENSE を参照してください（存在する場合）。

最後に
- まずは .env を作成 → python -m kabusys.validate_config で検証 → 開発環境では KABUSYS_ENV=development で各モジュール（run_monitoring, run_execution）を実行して挙動を確認してください。
- 追加の質問や各モジュール（ExecutionEngine の設定やブローカー実装、DB スキーマの拡張など）に関する詳細ドキュメントが必要であればお知らせください。