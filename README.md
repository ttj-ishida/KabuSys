KabuSys
=======

日本株向け自動売買・研究フレームワーク（パッケージ内部ドキュメント）
この README はリポジトリ内の主要スクリプト・モジュール群をまとめた利用ガイドです。

概要
----
KabuSys は日本株の自動売買・リサーチ・監視のためのモジュール群です。  
主要機能は以下を含みます：

- 実行エンジン（ExecutionEngine）: 発注・リスク管理・注文管理を統括
- 監視モジュール（Monitoring）: システム状態・注文ログ・リスクをポーリングして永続化・アラート化
- ポートフォリオ構築: 候補選定、重み付け、株数決定（等金額・スコア・リスクベース）
- 研究モジュール: ファクター（モメンタム／ボラティリティ／バリュー）計算、特徴量解析
- AI モジュール: ニュース NLP によるセンチメント評価、レジーム判定（OpenAI 利用）
- 開発用ツール: Paper Trading 検証レポート生成、.env ウィザード、設定検証 CLI 等

主な設計方針:
- 設定は環境変数（.env / .env.local 経由で自動ロード）で管理
- 本番/ペーパー売買は環境変数 KABUSYS_ENV により明確に分離
- DB は DuckDB（分析用途）と SQLite（監視/トレードログ）を用途別に利用
- 外部 API 呼び出し（OpenAI 等）は明示的にキー指定可能で、安全なフォールバック実装あり

機能一覧
--------
- 実行
  - run_execution.py: ExecutionEngine を起動（KABUSYS_ENV=paper_trading の場合は MockBroker を使用し、paper_trading DB を使用）
- 監視
  - run_monitoring.py: SystemMonitor を定期ポーリング（MONITOR_POLL_INTERVAL で間隔変更可）
  - MonitoringEngine: System / Trade / Risk Monitor を束ねてアラート判定、Kill Switch の発動
  - MonitoringDB: SQLite に system_status / trade_logs / positions / risk_logs / dashboard を管理
- ポートフォリオ構築
  - 候補選定・重み付け・位置サイズ決定・セクターキャップ・レジーム調整
- 研究（Research）
  - ファクター算出（momentum/volatility/value）、将来リターン、IC 計算、統計サマリ
- AI（OpenAI）
  - news_nlp.score_news: ニュースから銘柄別センチメントを生成して ai_scores に書き込み
  - regime_detector.score_regime: ETF 指標 + マクロニュースで市場レジーム判定し market_regime に記録
- ツール
  - config_setup.py: 対話式 .env ウィザード
  - validate_config.py: 環境変数・config/*.yaml の事前検証 CLI
  - tools.paper_verification_report: Paper Trading の検証レポート生成

セットアップ手順
----------------
1. リポジトリをクローンして作業ディレクトリに移動
   - プロジェクトルートは .git または pyproject.toml を基準に自動検出されます。

2. Python 仮想環境（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   - 基本的に以下をインストールしてください（環境に応じて必要なもののみ）
     - duckdb
     - psutil
     - openai (AI 機能を使う場合)
     - pyyaml (validate_config の YAML 検証を行う場合)
   - 例:
     - pip install duckdb psutil openai pyyaml

4. 環境変数の用意
   - プロジェクトルートに .env を作成（手動またはウィザードで）
   - 自動ロード: config.py が起動時にプロジェクトルートの .env / .env.local を読み込みます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）
   - 推奨: python -m kabusys.config_setup を実行して対話的に .env を生成

5. .env に設定すべき主なキー（抜粋）
   - JQUANTS_REFRESH_TOKEN (必須)
   - KABU_API_PASSWORD (必須)
   - KABUSYS_ENV: development | paper_trading | live （デフォルト: development）
   - DUCKDB_PATH: data/kabusys.duckdb（デフォルト）
   - SQLITE_PATH: data/monitoring.db（監視 DB）
   - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db（paper_trading 用 DB）
   - LOG_LEVEL, LOG_DIR（ログ出力設定）
   - OPENAI_API_KEY（AI 機能を使用する場合）
   - PAPER_FILL_MODE （ペーパートレードの約定挙動: instant|partial|never|reject）

使い方（主要コマンド）
--------------------

- 環境ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告もエラー扱い（exit 1）になります

- 実行エンジン起動（本番 / ペーパー同様に実行）
  - python -m kabusys.run_execution
  - 動作:
    - Settings に基づき sqlite/duckdb に接続
    - KABUSYS_ENV=paper_trading の場合は paper_sqlite_path（デフォルト data/paper_trading.db）を使用し、MockBrokerClient を使用
    - プロセス優先度を high に設定し、ExecutionEngine をスレッドで起動
    - data/stop_requested.flag を検知するとシャットダウン
    - 実行中に data/execution.pid を作成

- 監視ループ起動
  - python -m kabusys.run_monitoring
  - 動作:
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書き可能（デフォルト 60）
    - 監視は環境に関係なく本番 sqlite_path を使って記録（monitoring 用 DB）
    - data/stop_requested.flag を検知すると終了

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - オプション:
    - --db PATH で SQLite ファイルを指定（環境変数 PAPER_TRADING_SQLITE_PATH より優先）

設定・挙動のポイント
--------------------
- .env 自動読み込み
  - config._find_project_root() によりプロジェクトルートを探索し、.env/.env.local を自動読み込みします（OS 環境変数 > .env.local > .env）。自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

- KABUSYS_ENV の意味
  - development: 開発（発注なし）
  - paper_trading: ペーパートレード（MockBroker を使用、データ分離）
  - live: 本番（実発注）

- DB パスのデフォルト
  - DUCKDB_PATH: data/kabusys.duckdb
  - SQLITE_PATH: data/monitoring.db
  - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db

- ログ設定
  - kabusys.utils.logging_setup.setup_logging を利用してログを統一管理
  - デフォルトは logs/<app_name>.log に日次ローテーション（30 日保持）
  - LOG_LEVEL / LOG_DIR で変更可能

- プロセス制御・Kill Switch
  - KillSwitch は data/kill.flag を書き込むことで ExecutionEngine を停止させる仕組み
  - run_execution/run_monitoring は data/stop_requested.flag を検知すると優雅に停止
  - KILL_FLAG_CLEAR_ON_START=1 により起動時に自動クリアする設定があるが、本番では 0 推奨

依存関係（主な外部ライブラリ）
-----------------------------
- Python 標準: sqlite3, logging, threading, datetime, pathlib 等
- 推奨外部ライブラリ:
  - duckdb: 分析用 DB
  - psutil: CPU / メモリ / プロセス優先度制御
  - openai: AI 機能（news_nlp, regime_detector）
  - pyyaml: validate_config の YAML 検証（任意）

ディレクトリ構成（主要ファイル・モジュール説明）
--------------------------------------------
src/kabusys/
- __init__.py
  - パッケージ定義・バージョン

- config.py
  - 環境変数/.env の自動読み込みロジックと Settings クラス（全設定アクセス）

- config_setup.py
  - .env を対話式に作成するウィザード

- validate_config.py
  - 起動前の設定検証 CLI（必須 env の確認、DB パスのチェック、YAML の検証など）

- run_execution.py
  - ExecutionEngine の起動スクリプト。paper_trading 環境は専用 DB・MockBroker を使用

- run_monitoring.py
  - SystemMonitor のポーリング起動スクリプト。MONITOR_POLL_INTERVAL で間隔指定可

- utils/
  - logging_setup.py: ログ初期化ユーティリティ（Stream + TimedRotatingFileHandler）
  - process_priority.py: プロセス優先度設定（Windows / POSIX を吸収）
  - 他ユーティリティ

- monitoring/
  - monitoring_db.py: SQLite スキーマ初期化 / 永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
  - system_monitor.py: システム状態（CPU/Memory/Disk）、データ鮮度、プロセス生存チェック
  - trade_monitor.py: （省略）注文滞留・約定異常などの検出ロジック
  - risk_monitor.py: ドローダウン / ポジション数上限監視
  - kill_switch.py: kill.flag 書き込みロジック
  - monitoring_engine.py: 各 Monitor を束ねるエンジン
  - alert_manager.py: （省略）通知管理（LINE/メール等と連携する想定）

- execution/
  - execution_engine.py: 実行エンジンのコア（発注ループ、セッション管理）
  - broker_factory.py, order_manager.py, order_repository.py, reconciler.py, risk_manager.py
    - 発注・リスク・注文履歴の各責務実装

- portfolio/
  - portfolio_builder.py: 候補選定・重み付け（equal/score）
  - position_sizing.py: 株数算出・資金配分・単元丸め
  - risk_adjustment.py: セクターキャップ、レジーム乗数

- research/
  - factor_research.py: momentum / volatility / value 等のファクター計算（DuckDB を利用）
  - feature_exploration.py: 将来リターン計算、IC、統計サマリ

- ai/
  - news_nlp.py: raw_news を OpenAI に投げて銘柄別 ai_score を生成し ai_scores テーブルへ書き込み
  - regime_detector.py: ETF ma200 とマクロニュースで市場レジーム判定し market_regime に保存

- tools/
  - paper_verification_report.py: Paper Trading DB を解析して PASS/FAIL 判定するレポートを標準出力

運用上の注意
-------------
- 本番（KABUSYS_ENV=live）での運用は慎重に:
  - validate_config で警告が出る項目（LINE 通知未設定、KILL_FLAG_CLEAR_ON_START=1 など）は要確認
- kill.flag / stop_requested.flag の取り扱い:
  - kill.flag は Execution を強制停止させるための重要な安全スイッチです。取り扱いに注意してください。
- ログディレクトリの作成に失敗した場合はコンソールログのみで継続します（ログ設定が自己回復する実装）

サンプル起動例
--------------
- .env を作って検証:
  - python -m kabusys.config_setup
  - python -m kabusys.validate_config
- 監視を起動（ポーリング間隔 30 秒に設定して起動）:
  - export MONITOR_POLL_INTERVAL=30
  - python -m kabusys.run_monitoring
- 実行エンジンを起動（ペーパートレード）:
  - export KABUSYS_ENV=paper_trading
  - python -m kabusys.run_execution
- Paper Trading レポート生成:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - または: python -m kabusys.tools.paper_verification_report --db data/paper_trading.db

ライセンス / 貢献
-----------------
本 README はコードベースから自動生成した概要ドキュメントです。実際のライセンスや貢献ルールはリポジトリのトップレベルの LICENSE / CONTRIBUTING を参照してください。

補足・問い合わせ
----------------
- 実装に関する詳細な設計ノートは各モジュールの docstring を参照してください。
- 実行時の環境や依存ライブラリのバージョンによって挙動が変わる場合があります。問題が出たらエラーログ（logs/ 以下）と validate_config の出力を確認してください。