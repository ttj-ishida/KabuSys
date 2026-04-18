README
======

概要
----
KabuSys は日本株向けの自動売買システム（プロトタイプ）です。  
市場データの集計・ファクター計算、ポートフォリオ構築、ポジションサイズ計算、発注エンジン、監視／アラート、そして AI を使ったニュースセンチメントや市場レジーム判定などのコンポーネントを含みます。

主な特徴
--------
- ポートフォリオ構築（候補選定、等重・スコア重み付け）
- ポジションサイズ計算（リスクベース／重みベース、単元丸め、aggregate cap）
- セクター上限・レジーム乗数などのリスク調整
- DuckDB を使ったリサーチ（ファクター計算、将来リターン、IC 等）
- OpenAI（gpt-4o-mini）を用いたニュース NLP（銘柄センチメント）と市場レジーム判定
- ExecutionEngine（発注処理）と Monitoring（状態監視／Kill Switch）
- 監視ログの永続化（SQLite）とレポート生成ツール（Paper Trading 検証レポート）
- 簡易 CLI ツール：.env ウィザード、設定検証、レポート生成など
- ロギングはコンソール＋日次ローテートファイルで一元管理

必須／推奨環境変数（抜粋）
-----------------------
必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

主要なオプション／設定例:
- KABUSYS_ENV: 実行環境（development / paper_trading / live）デフォルト: development
- DUCKDB_PATH: DuckDB ファイル（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視 SQLite（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 SQLite（デフォルト data/paper_trading.db）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- LOG_DIR: ログ保存ディレクトリ（デフォルト logs/）
- OPENAI_API_KEY: OpenAI API キー（AI 機能を利用する場合）
- PAPER_FILL_MODE: ペーパートレード時の約定挙動（instant / partial / never / reject）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、run_monitoring 用、デフォルト 60）

セットアップ
-----------
1. Python 環境を用意（推奨: 3.10+）
2. 依存パッケージをインストール
   - 最低限必要なパッケージ（抜粋）:
     - duckdb
     - psutil
     - openai（AI 機能を使う場合）
     - PyYAML（config 検証を実施したい場合）
   例:
     pip install duckdb psutil openai pyyaml

3. プロジェクトルートに .env を用意
   - 対話式ウィザードで作成:
     python -m kabusys.config_setup
   - 既存の .env があればその値を使用します。自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。

4. 設定の検証（起動前に推奨）
   python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いになります。

使い方（主要コマンド）
--------------------

- ExecutionEngine（発注エンジン）を起動
  - paper_trading 環境では MockBrokerClient を使用し、data/paper_trading.db に記録されます
  - run:
    python -m kabusys.run_execution
  - 停止方法:
    - 実行中に data/stop_requested.flag を作成すると安全に停止します（run_execution と monitoring の両方で利用）
    - ExecutionEngine が参照する kill.flag は Settings.kill_flag_path（デフォルト data/kill.flag）

- Monitoring（監視ループ）を起動
  - run:
    python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒で指定（デフォルト 60）
  - 監視は KABUSYS_ENV にかかわらず本番 sqlite_path を使用して監視ログを記録します
  - 停止: data/stop_requested.flag を作成

- .env 設定ウィザード
  python -m kabusys.config_setup

- 設定検証 CLI
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict

- Paper Trading 検証レポート（SQLite を指定してレポート出力）
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-10
  - デフォルト DB: data/paper_trading.db（環境変数 PAPER_TRADING_SQLITE_PATH または --db で上書き可能）

ログ・監視・停止ファイル
-----------------------
- ログ:
  - デフォルト: logs/<app_name>.log（TimedRotatingFileHandler で日次ローテート、30日分保持）
  - ログ設定は kabusys.utils.logging_setup.setup_logging で統一

- 監視データベース:
  - SQLite: data/monitoring.db（Settings.sqlite_path）
  - DuckDB: data/kabusys.duckdb（Settings.duckdb_path）

- 停止フラグ:
  - data/stop_requested.flag: run_execution / run_monitoring の外部停止制御に使用
  - data/kill.flag: KillSwitch により ExecutionEngine の停止トリガーとして書き込まれる（監視コンポーネントが作成）

ディレクトリ構成（主要ファイル）
-----------------------------
以下は src/kabusys 配下の主要モジュールと用途の一覧です（抜粋）。

- src/kabusys/
  - __init__.py               — パッケージ定義（バージョン等）
  - config.py                 — 環境変数 / 設定読み込み・Settings
  - config_setup.py           — .env 対話式ウィザード
  - validate_config.py        — 設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — Monitoring 起動スクリプト

- src/kabusys/execution/
  - execution_engine.py       — 発注エンジン本体（EngineConfig, run_session 等）
  - order_manager.py
  - order_repository.py
  - reconciler.py
  - risk_manager.py
  - broker_factory.py         — ブローカークライアント（Mock / 実装）

- src/kabusys/monitoring/
  - monitoring_db.py          — SQLite 永続化層（テーブル初期化、ログ書込）
  - system_monitor.py         — システム状態・データ鮮度監視
  - trade_monitor.py          — 注文ログ監視（滞留注文／約定異常等）
  - risk_monitor.py           — ドローダウン・ポジション上限監視
  - kill_switch.py            — kill.flag の作成/評価
  - monitoring_engine.py      — 各 Monitor を束ねるループ
  - alert_manager.py          — （通知管理：LINE 等を想定）

- src/kabusys/portfolio/
  - portfolio_builder.py      — 候補選定、等重・スコア重み
  - position_sizing.py        — 発注株数計算（単元・aggregate cap 等）
  - risk_adjustment.py        — セクターキャップ、レジーム乗数

- src/kabusys/research/
  - factor_research.py        — ファクター計算（momentum / volatility / value）
  - feature_exploration.py    — 将来リターン、IC、統計サマリ
  - __init__.py

- src/kabusys/ai/
  - news_nlp.py               — ニュースセンチメント（OpenAI 連携）
  - regime_detector.py        — 市場レジーム判定（MA + マクロセンチメント）
  - __init__.py

- src/kabusys/utils/
  - logging_setup.py          — ログ設定ユーティリティ
  - process_priority.py       — プロセス優先度 / CPU affinity 設定ユーティリティ

- src/kabusys/tools/
  - paper_verification_report.py — Paper Trading 検証レポート生成スクリプト

注意点 / 運用上のヒント
----------------------
- 環境変数は .env / .env.local を自動ロードします。OS 環境変数は保護され上書きされません。自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。
- run_execution は KABUSYS_ENV が paper_trading の場合、paper_trading 用の SQLite（PAPER_TRADING_SQLITE_PATH）を使用し、本番データと完全分離されます。
- 監視（run_monitoring）は監視用 SQLite（Settings.sqlite_path）を使用し、KABUSYS_ENV に関係なく同じ監視 DB を使います（運用で意図した仕様）。
- ログディレクトリ作成に失敗した場合はコンソール出力のみで継続します。ログの永続化を確実に行うには LOG_DIR のパーミッション・存在を事前に確認してください。
- OpenAI を使う機能は API キーが必須です。API 呼び出しはリトライ・フォールバック設計がなされていますが、鍵／課金設定は十分注意してください。
- Kill Switch（リスク閾値を超えた際に data/kill.flag を書き込む）により発注を停止できます。設定やテスト時は KILL_FLAG_CLEAR_ON_START を確認してください（本番では自動クリアを推奨しません）。

開発・拡張
-----------
- DuckDB を用いる研究モジュールや AI 部分は外部データテーブル（prices_daily / raw_financials / raw_news 等）に依存します。テストデータを用意して単体テストを書くと良いです。
- ローカル開発では KABUSYS_ENV=development を使うとリスクのある機能（発注等）が抑制されている想定です（コード内での振る舞いに従う）。
- モジュールは比較的小さな責務で分割されています。ユニットテストは各純粋関数（portfolio/*, research/*, ai/* の一部）から追加を推奨します。

ライセンス・その他
------------------
- 本リポジトリ内のドキュメントやコードの利用条件はリポジトリの LICENSE を参照してください（本 README の記載はコードベースに基づく説明です）。

以上。何か特定のコマンドや設定ファイルのテンプレート（.env.example）を生成したい場合は教えてください。