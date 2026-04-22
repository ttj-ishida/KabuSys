README
======

概要
----
KabuSys は日本株向けの自動売買・リサーチ基盤のコアライブラリ群です。本リポジトリは以下の主要機能を含みます。

- 実行エンジン（ExecutionEngine）を起動・管理するランナー
- システム / 注文 / リスク監視（Monitoring）と Kill Switch（停止フラグ）
- ポートフォリオ構築・銘柄選定・株数決定ロジック（純粋関数群）
- 研究用ファクター計算・特徴量解析ユーティリティ（DuckDB 経由）
- ニュース NLP / レジーム判定（OpenAI を用いたセンチメント評価）
- 開発支援ツール（.env 設定ウィザード、設定検証、Paper Trading 検証レポート 等）
- ロギング / プロセス優先度設定ユーティリティ

主な設計方針：
- 本番 DB とペーパートレード DB を分離（KABUSYS_ENV=paper_trading の場合は専用 sqlite を使用）
- ルックアヘッドバイアスを避ける（date.today()/datetime.today() を直接参照しない設計）
- フェイルセーフ：外部 API 失敗時は安全にフォールバックする

機能一覧
--------
主な機能（抜粋）：

- 起動スクリプト
  - run_execution.py: ExecutionEngine を起動。KABUSYS_ENV=paper_trading のときは MockBroker を用い paper_trading.db を使用
  - run_monitoring.py: SystemMonitor のポーリングループを開始（MONITOR_POLL_INTERVAL で間隔変更可能）
- 環境設定
  - config_setup.py: 対話式で .env を作成・更新するウィザード
  - validate_config.py: .env と config/*.yaml の検証（--strict オプションあり）
- 監視
  - monitoring_engine.py: System/Trade/Risk monitor を束ねるエンジン
  - monitoring_db.py: SQLite に監視ログを永続化（テーブル初期化・マイグレーション含む）
  - risk_monitor.py / system_monitor.py / trade_monitor.py / kill_switch.py: 各種監視ロジック
- ポートフォリオ構築
  - portfolio/*.py: 候補選定 (select_candidates)、重み計算 (calc_equal_weights / calc_score_weights)、リスク調整 (apply_sector_cap / calc_regime_multiplier)、株数決定 (calc_position_sizes)
- 研究ツール
  - research/*.py: ファクター計算（momentum/value/volatility）、将来リターン計算、IC（スピアマン）等
- AI（OpenAI）連携
  - ai/news_nlp.py: ニュースを集約して OpenAI でセンチメント評価 → ai_scores に書き込み
  - ai/regime_detector.py: ETF の MA200 とマクロセンチメントを合成して market_regime を算出
- ツール
  - tools/paper_verification_report.py: ペーパートレード DB を解析して PASS/FAIL の検証レポートを出力
- ユーティリティ
  - utils/logging_setup.py: 統一的なロギング設定（stdout + 日次ローテートファイル）
  - utils/process_priority.py: クロスプラットフォームでのプロセス優先度・CPU affinity 設定

セットアップ手順
---------------
前提
- Python 3.9+（プロジェクトの実行環境に合わせて適宜）
- システムにより追加のネイティブ依存（psutil など）が必要な場合があります

推奨手順（例）
1. 仮想環境を作る
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要なパッケージをインストール
   - 以下は主要依存の例（requirements.txt がない場合の例示）
     pip install duckdb psutil openai

   - オプション
     - PyYAML: config/*.yaml の検証を行いたい場合にインストール（pip install pyyaml）

3. 初期設定 (.env) の作成
   - 対話式ウィザードを使う:
     python -m kabusys.config_setup
   - あるいは .env.example を参考に手動作成

4. 設定検証
   - python -m kabusys.validate_config
   - --strict を付けると警告も FAIL 扱い:
     python -m kabusys.validate_config --strict

環境変数（代表的なもの）
- 必須
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- 推奨 / 主要
  - KABUSYS_ENV: development | paper_trading | live （デフォルト: development）
  - DUCKDB_PATH: 分析用 DuckDB（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH: 監視 DB（デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH: ペーパートレード用 sqlite（デフォルト: data/paper_trading.db）
  - PAPER_FILL_MODE: instant | partial | never | reject（デフォルト: instant）
  - LOG_LEVEL: DEBUG|INFO|WARNING|ERROR|CRITICAL
  - OPENAI_API_KEY: OpenAI を使う機能（news_nlp / regime_detector）
  - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: アラート通知（任意）
- 監視関連
  - MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒。デフォルト 60）
  - KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリア（0/1、本番では 0 推奨）

最小 .env の例（テンプレート）
- 必要なものだけ記載（実運用ではシークレットは安全に保管）
  JQUANTS_REFRESH_TOKEN=your_jquants_token
  KABU_API_PASSWORD=your_kabu_password
  KABUSYS_ENV=development
  DUCKDB_PATH=data/kabusys.duckdb
  SQLITE_PATH=data/monitoring.db
  LOG_LEVEL=INFO

使い方
------

起動（代表例）
- ExecutionEngine を起動（ローカルで直接起動する場合）:
  python -m kabusys.run_execution

  挙動ポイント:
  - KABUSYS_ENV=paper_trading の場合、settings.paper_sqlite_path（デフォルト data/paper_trading.db）を使って発注を記録し、本番 DB とは分離されます。
  - 起動時に data/stop_requested.flag が存在すると起動せず終了します。
  - エンジンは data/execution.pid を作成します。停止は stop フラグファイルやアプリ内 API 経由で行います。

- Monitoring を起動:
  python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可（秒、デフォルト 60）
  - 監視は監視用 sqlite_path を使います（Monitoring は環境にかかわらず本番 sqlite_path を参照する実装）

- .env 作成ウィザード:
  python -m kabusys.config_setup

- 設定検証:
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict

- Paper Trading 検証レポート:
  python -m kabusys.tools.paper_verification_report
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  オプションで --db に PAPER_TRADING_SQLITE_PATH を指定可能

ログ
- デフォルトで stdout にログを出力し、logs/<app_name>.log に日次ローテートで出力します（utils/logging_setup.py）
- LOG_DIR 環境変数でログディレクトリを変更できます

停止 / Kill Switch / フラグ
- ExecutionEngine や Monitoring はプロジェクトの data ディレクトリ下のフラグファイルで制御する設計です。
  - data/kill.flag: Kill Switch によって ExecutionEngine 停止指示を出す（存在すれば停止対象）
  - data/stop_requested.flag: run_monitoring/run_execution のループを中断するための外部停止フラグ
  - data/execution.pid: ExecutionEngine の PID 管理
- kill.flag は KillSwitch により自動生成されることがあり、本番環境では KILL_FLAG_CLEAR_ON_START を 0 に設定することを推奨します

ディレクトリ構成
----------------
主要なファイル・ディレクトリ（src/kabusys 以下）:

- __init__.py
- config.py
  - Settings クラス: 環境変数の読み取り / バリデーション
- config_setup.py
  - .env 対話式ウィザード
- validate_config.py
  - 起動前の設定検証 CLI
- run_execution.py
  - ExecutionEngine 起動スクリプト（proc priority 設定、DB 接続、スレッド管理等）
- run_monitoring.py
  - SystemMonitor のポーリングループ起動スクリプト

- execution/
  - execution_engine.py (Execution エンジン本体) *
  - order_manager.py, order_repository.py, reconciler.py, risk_manager.py, broker_factory.py (発注/リスク管理) *
  - （※ execution ディレクトリは本 README のスニペットでは一部のみ参照されている想定）

- monitoring/
  - monitoring_db.py       : SQLite スキーマ初期化 + MonitoringDB ラッパー
  - monitoring_engine.py   : 各 Monitor を束ねるエンジン
  - system_monitor.py      : システム・データ鮮度チェック
  - trade_monitor.py       : 注文ログ監視（滞留注文、約定異常など）
  - risk_monitor.py        : ドローダウン / ポジション上限監視
  - kill_switch.py         : kill.flag 書き込み・評価
  - alert_manager.py       : （アラート送信ロジック）

- portfolio/
  - portfolio_builder.py   : 候補選定 / 重み算出
  - position_sizing.py     : 株数計算（lot 丸め / aggregate cap）
  - risk_adjustment.py     : セクター制限・レジーム乗数

- research/
  - factor_research.py     : Momentum / Volatility / Value 等のファクター算出（DuckDB）
  - feature_exploration.py : 将来リターン・IC・統計サマリ
  - __init__.py

- ai/
  - news_nlp.py            : ニュース集約 → OpenAI でスコア化 → ai_scores 書き込み
  - regime_detector.py     : MA200 とマクロセンチメントで市場レジーム判定

- tools/
  - paper_verification_report.py : ペーパートレード検証レポート出力
  - __init__.py

- utils/
  - logging_setup.py       : 共通ログ設定
  - process_priority.py    : プロセス優先度 / CPU affinity
  - __init__.py

- その他
  - data/                  : 実行時に生成される sqlite / flag / pid / etc（git 管理対象外にすること）
  - logs/                  : ログファイル出力先（デフォルト）

（*）上記 README 中には execution 配下のファイルは参照されていますが、この README は配布されたコードスニペットに基づく説明です。実行時は execution 実装全体が必要です。

注意事項 / ベストプラクティス
----------------------------
- .env は機密情報を含むため絶対にリポジトリにコミットしないでください
- 本番（KABUSYS_ENV=live）環境では KILL_FLAG_CLEAR_ON_START を 0 に設定することを強く推奨します
- OpenAI API を使う機能は API キー（OPENAI_API_KEY）を設定してください。API 呼び出しに失敗してもフェイルセーフで継続する設計ですが、キー未設定だと一部機能は動作しません
- ローカルテストではペーパートレードモード（KABUSYS_ENV=paper_trading）を活用して本番資金を保護してください

サポート / 開発メモ
-------------------
- 設定の検証は validate_config.py で行えます。初回導入ではまず config_setup.py で .env を作成 → validate_config を実行してください
- DuckDB のテーブル（prices_daily / raw_financials / raw_news 等）は research / ai モジュールが参照します。データがない場合は当該機能は結果を返さないか N/A を返すよう設計されています
- テスト時は外部 API 呼び出し関数（OpenAI 等）をモックすることを推奨します（score_news の _call_openai_api 等は差し替えやすく設計）

ライセンス・バージョン
---------------------
- パッケージバージョンは kabusys.__version__ = "0.1.0"
- ライセンス情報はリポジトリの LICENSE / pyproject.toml 等をご参照ください

以上。必要ならば README にサンプル .env、より細かい CLI オプション一覧、または各モジュールの API ドキュメント（関数一覧と引数説明）を追記します。どの情報を追加しますか？