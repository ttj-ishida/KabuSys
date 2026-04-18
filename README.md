KabuSys — 日本株自動売買システム（README）
====================================

概要
----
KabuSys は日本株の自動売買システムのためのライブラリ兼起動スクリプト群です。  
主な機能は以下の通りです。

- 発注実行エンジン（ExecutionEngine）とペーパートレード切替
- システム監視（モニタリング）と Kill Switch（条件により Execution を停止）
- ポートフォリオ構築・ポジションサイズ計算（純粋関数群）
- ファクター計算・リサーチユーティリティ（DuckDB 経由）
- ニュース NLP（OpenAI）を使った銘柄センチメント評価および市場レジーム判定
- 設定ウィザード（.env 作成）と設定検証 CLI
- 紙トレード検証レポート生成ツール

主な設計方針：
- 本番とペーパートレードは DB を分離（KABUSYS_ENV に依る）
- 可能な限り副作用を避けた純粋関数（portfolio / research）
- DuckDB を分析用途に使用、SQLite を監視・トレース用途に使用
- OpenAI 呼び出しは最大リトライ・結果検証を行いフェイルセーフ化

機能一覧
--------
- 起動スクリプト
  - run_execution.py — ExecutionEngine を起動（KABUSYS_ENV=paper_trading で MockBroker）
  - run_monitoring.py — SystemMonitor のポーリングループ起動（MONITOR_POLL_INTERVAL で間隔指定）
- 設定管理
  - config_setup.py — 対話式 .env ウィザード
  - validate_config.py — .env / config/*.yaml の事前検証
  - config.Settings — 環境変数アクセスラッパ
- モニタリング
  - monitoring_engine.py — 各 Monitor を束ねるエンジン
  - system_monitor.py / trade_monitor.py / risk_monitor.py — 個別監視ロジック
  - monitoring_db.py — SQLite スキーマと永続化ユーティリティ
  - kill_switch.py — kill.flag 操作（Execution 停止）
- 実行・発注関連（execution パッケージ）
  - BrokerClientFactory, ExecutionEngine, OrderManager, Reconciler, RiskManager 等（起動ロジックは run_execution）
- ポートフォリオ構築（portfolio パッケージ）
  - 銘柄選定・重み算出・位置決め（select_candidates, calc_equal_weights, calc_score_weights, calc_position_sizes など）
  - セクターキャップ、レジーム乗数（apply_sector_cap, calc_regime_multiplier）
- リサーチ（research パッケージ）
  - ファクター計算（momentum / volatility / value）
  - 将来リターン・IC 計算、統計サマリ
- AI（ai パッケージ）
  - news_nlp.score_news — OpenAI を使ってニュースから銘柄ごとセンチメントを生成
  - regime_detector.score_regime — ETF ma200 とマクロニュースからレジーム判定
- ユーティリティ
  - logging_setup.setup_logging — 一貫したログ設定（コンソール + 日次ローテーションファイル）
  - process_priority.set_process_priority / set_cpu_affinity — プラットフォーム差分を吸収する優先度設定
- ツール
  - tools.paper_verification_report — Paper Trading の集計 & PASS/FAIL レポート生成

セットアップ手順
---------------
1. Python 環境
   - Python 3.9+ を想定（利用ライブラリで互換差異がある場合あり）
2. 依存パッケージ（例）
   - pip install duckdb psutil openai
   - （任意）PyYAML: validate_config で config/*.yaml を検証したい場合に必要
   - 実際のプロジェクトでは requirements.txt を用意している想定です。無ければ上記を個別にインストールしてください。
3. プロジェクトルートとディレクトリ
   - data/ および logs/ ディレクトリは自動作成されますが、権限設定が必要な環境では事前に作成してください。
4. 環境変数（必須）
   - JQUANTS_REFRESH_TOKEN
   - KABU_API_PASSWORD
   - これらは .env ファイルで管理するのが推奨です（.env は絶対に Git にコミットしないでください）。
5. .env の作成（対話式ウィザード）
   - python -m kabusys.config_setup
   - これにより .env を作成できます（既存値の読み込み・編集可）
6. 設定検証
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱い（exit(1)）になります
7. DB 初期化
   - 起動スクリプトが自動的に必要テーブルを作成します（monitoring_db.init_monitoring_db で冪等処理）。

主な環境変数（抜粋）
- KABUSYS_ENV: development | paper_trading | live （デフォルト: development）
- DUCKDB_PATH: data/kabusys.duckdb（デフォルト）
- SQLITE_PATH: data/monitoring.db（デフォルト）
- PAPER_TRADING_SQLITE_PATH: data/paper_trading.db（paper_trading 用）
- LOG_LEVEL: DEBUG|INFO|WARNING|ERROR|CRITICAL
- OPENAI_API_KEY: OpenAI 呼び出しに必要
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）
- PAPER_FILL_MODE: ペーパートレードでの約定モード（instant|partial|never|reject）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（0/1）

使い方
------
基本的な実行例（プロジェクトルートで実行）:

- .env 作成（対話式）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- ExecutionEngine 起動（本番/ペーパーは KABUSYS_ENV に依存）
  - python -m kabusys.run_execution
  - 注意: 起動中は data/execution.pid が作られます。停止は data/stop_requested.flag を作成するか、システムの通常の終了方法で。

- Monitoring 起動（ポーリング）
  - MONITOR_POLL_INTERVAL 環境変数で秒数を指定可能（デフォルト 60 秒）
  - python -m kabusys.run_monitoring
  - 監視は monitoring DB に system_status / trade_logs / risk_logs / positions / dashboard を書き込みます。
  - 監視プロセスは data/stop_requested.flag を検知するとループを終了します。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db で別 DB を指定可能（デフォルトは PAPER_TRADING_SQLITE_PATH または data/paper_trading.db）

- AI 系機能（コードから呼び出し）
  - 例: from kabusys.ai import score_news; score_news(conn, target_date, api_key=...)
  - OpenAI API キーは引数で渡すか環境変数 OPENAI_API_KEY を使用

Kill Switch / 停止フロー
- リスク監視が閾値を超えると kill.flag（Settings.kill_flag_path, デフォルト data/kill.flag）を書き込みます。  
  ExecutionEngine は起動時と実行中にこのフラグをチェックし、検出時に安全に停止します。
- 手動停止用フラグ（起動スクリプトが参照）: data/stop_requested.flag を作ることで run_monitoring/run_execution のループが終了します。

ログ
- setup_logging により stdout と logs/<app_name>.log（日次ローテーション）が出力されます。
- LOG_DIR 環境変数でログディレクトリを変更できます。

注意点 / 運用メモ
- KABUSYS_ENV=paper_trading 時は paper_trading 用 SQLite（デフォルト data/paper_trading.db）に書き込まれ、本番 DB と分離されます。
- config._find_project_root により .env 自動読み込みはプロジェクトルート（.git または pyproject.toml）から行われます。自動読み込みを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- OpenAI 呼び出しはネットワーク/429/5xx に対してリトライを実装していますが、API キーや通信の健全性を監視してください。
- データ鮮度チェックや各種閾値は Settings で環境変数から調整可能です（CPU/MEM/DISK閾値など）。

ディレクトリ構成（主要ファイル）
----------------------------
以下は主要モジュールのツリー（src/kabusys 配下）です。実際のリポジトリでは pyproject.toml 等がルートにあります。

- src/kabusys/
  - __init__.py
  - run_execution.py            — ExecutionEngine 起動スクリプト
  - run_monitoring.py          — SystemMonitor ポーリング起動スクリプト
  - config.py                  — Settings / .env 自動読込ロジック
  - config_setup.py            — .env 対話式ウィザード
  - validate_config.py         — 設定検証 CLI
  - utils/
    - logging_setup.py         — ログセットアップ
    - process_priority.py      — 優先度 / CPU affinity
  - monitoring/
    - monitoring_db.py         — SQLite スキーマ & DB API
    - monitoring_engine.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py         — （アラート周り、詳細は実装参照）
  - execution/                  — Execution 関連（OrderManager 等）
    - broker_factory.py
    - execution_engine.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
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
    - news_nlp.py
    - regime_detector.py
    - __init__.py
  - data/                       — （実行時に生成される）DBファイル、フラグ、pid 等が置かれる
  - logs/                       — ログ出力先（デフォルト）

追加情報
--------
- コード内のドキュメント（docstring）に多数の設計注記・注意事項があります。詳細は該当モジュールを参照してください。
- 本 README は開発者向けの概要です。運用時の細かい手順（デーモン化、systemd/cron での起動、証跡保存等）は運用ポリシーに従って構築してください。

お問い合わせ / コントリビュート
------------------------------
コードの改善や不具合報告はリポジトリの Issue / Pull Request を利用してください。開発者向けのドキュメント追加やテストの充実を歓迎します。

以上。必要であれば「環境変数一覧の詳細」「運用チェックリスト」などの追加ドキュメントを作成します。どの情報を優先して展開しますか？