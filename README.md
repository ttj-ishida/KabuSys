KabuSys — 日本株自動売買システム
===============================

概要
----
KabuSys は日本株向けの自動売買 / 研究 / 監視を目的とした Python コードベースです。  
主な役割は以下のとおりです。

- ExecutionEngine：発注・リスク管理・注文再調整を実行（実運用 / ペーパートレード対応）
- Monitoring：システム状態・注文ログ・リスクを監視してアラートや Kill Switch を制御
- Research：DuckDB を用いたファクター計算・特徴量解析
- Portfolio：候補選定・配分・ポジションサイジング等のポートフォリオ構築ロジック
- AI モジュール：ニュース NLP によるセンチメントや市場レジーム判定（OpenAI 利用）
- ユーティリティ：設定読み込み、ログ設定、プロセス優先度設定など

機能一覧
--------
- 環境設定ウィザード（.env の対話生成）: python -m kabusys.config_setup
- 設定検証 CLI（.env / config/*.yaml の事前チェック）: python -m kabusys.validate_config [--strict]
- 実エンジン起動スクリプト（ExecutionEngine）: python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading により MockBroker を用いた分離された paper_trading DB を利用
  - PID ファイル管理（data/execution.pid）、停止フラグ検出（data/stop_requested.flag）
- 監視ループ起動スクリプト（Monitoring）: python -m kabusys.run_monitoring
  - ポーリング間隔は MONITOR_POLL_INTERVAL（秒）で上書き可（デフォルト 60 秒）
  - 監視用 DB の初期化（SQLite）、DuckDB 接続
  - Kill Switch 評価、アラート送信（LINE などの設定があれば）
- Paper Trading 検証レポート生成ツール: python -m kabusys.tools.paper_verification_report
- AI ベース処理:
  - kabusys.ai.news_nlp.score_news: raw_news を OpenAI に送って銘柄ごとのスコアを ai_scores に書込
  - kabusys.ai.regime_detector.score_regime: MA とマクロニュースで市場レジーム判定
- 研究モジュール:
  - ファクター計算（momentum, volatility, value）
  - 将来リターン・IC 計算・統計サマリ
- ポートフォリオ関連:
  - 候補選定、等重・スコア加重配分、リスク調整（セクターキャップ・レジーム乗数）
  - ポジションサイズ計算（リスクベース、丸め・単元考慮、aggregate cap）

セットアップ手順（開発環境向け）
------------------------------
以下は一般的なセットアップ例です（プロジェクトに requirements.txt がある前提）。  
Python 3.10 以上を推奨（PEP 604 の | 型ヒントなどを使用）。

1. リポジトリをクローン
   - git clone <repo-url>

2. 仮想環境作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存パッケージをインストール
   - pip install -r requirements.txt
   - 主要依存（代表例）:
     - duckdb
     - psutil
     - openai
     - PyYAML（config YAML 検証で任意）
   - パッケージ一覧はプロジェクトの配布方法に従ってください（pyproject.toml / requirements.txt 等）。

4. ディレクトリ作成（初回）
   - mkdir -p data logs

5. .env の初期作成（ウィザード推奨）
   - python -m kabusys.config_setup
   - 生成後、必須の環境変数（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD 等）を確認してください。

6. 設定検証
   - python -m kabusys.validate_config
   - 本番前に --strict を使って警告を FAIL 扱いにすることを推奨: python -m kabusys.validate_config --strict

主な環境変数（抜粋）
--------------------
- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE（instant | partial | never | reject、デフォルト: instant）
- LOG_LEVEL（DEBUG|INFO|WARNING|ERROR|CRITICAL、デフォルト: INFO）
- LOG_DIR（ログファイル保存先、デフォルト: logs/）
- OPENAI_API_KEY（AI モジュール利用時に必要）
- MONITOR_POLL_INTERVAL（監視ポーリング間隔、秒。デフォルト 60）
- KILL_FLAG_CLEAR_ON_START（1 で起動時に kill.flag を自動クリア。production では 0 推奨）

使い方（主要コマンド）
--------------------
- .env を対話的に作成 / 更新
  - python -m kabusys.config_setup

- 設定を検証（起動前チェック）
  - python -m kabusys.validate_config
  - 厳格モード（警告も失敗扱い）: python -m kabusys.validate_config --strict

- 実行エンジン起動（Execution）
  - python -m kabusys.run_execution
  - environment を切り替える例（ペーパートレード）:
    - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  - 起動時に data/stop_requested.flag が存在すると起動を停止します
  - 実行中に停止するには data/stop_requested.flag を作成

- 監視ループ起動（Monitoring）
  - python -m kabusys.run_monitoring
  - ポーリング間隔の変更:
    - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - 停止フラグ検出: data/stop_requested.flag を監視して終了

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

停止 / Kill Switch
------------------
- ExecutionEngine を安全に停止させる手段:
  - Kill Switch: data/kill.flag を作成すると Monitoring が条件を満たすと Execution に停止シグナルを送ります（KillSwitch が書き込む/監視する仕組み）。
  - stop_requested.flag（data/stop_requested.flag）でいずれのスクリプトも監視・終了する仕組みがあります（run_*.py 参照）。

ログ
----
- ログ出力は kabusys.utils.logging_setup.setup_logging を経由して一元管理
- デフォルトで stdout（コンソール）と logs/<app_name>.log（日次ローテート）に出力
- LOG_DIR でログ保存先を変更できます。ログレベルは LOG_LEVEL で制御。

ディレクトリ構成（主要ファイル）
------------------------------
以下は src/kabusys ディレクトリ内の主要モジュールと目的の簡易一覧です。

- run_execution.py
  - ExecutionEngine の起動スクリプト（PID ファイル・stop flag 監視・paper_trading 分離）

- run_monitoring.py
  - SystemMonitor のポーリングループ起動スクリプト（MONITOR_POLL_INTERVAL）

- config.py
  - 環境変数・設定読み込みロジック（.env 自動ロード、Settings クラス）

- config_setup.py
  - .env を対話式に生成・更新するウィザード

- validate_config.py
  - 起動前の設定検証 CLI

- tools/
  - paper_verification_report.py: ペーパートレード検証レポート生成

- portfolio/
  - portfolio_builder.py: 候補選定・配分計算
  - position_sizing.py: 発注株数・丸め・aggregate cap
  - risk_adjustment.py: セクターキャップ・レジーム乗数

- research/
  - factor_research.py: モメンタム/ボラ/バリュー等のファクター計算（DuckDB）
  - feature_exploration.py: 将来リターン、IC、統計サマリ

- ai/
  - news_nlp.py: raw_news を OpenAI でスコアリングして ai_scores に書込
  - regime_detector.py: MA とマクロニュースを合成して市場レジーム判定

- monitoring/
  - monitoring_db.py: SQLite を使った監視用 DB 層（テーブル初期化・CRUD ラッパー）
  - system_monitor.py: CPU/メモリ/ディスク・データ鮮度・プロセス監視
  - trade_monitor.py: 注文ログの滞留・約定異常チェック（詳細はソース参照）
  - risk_monitor.py: ドローダウン・ポジション上限監視
  - kill_switch.py: kill.flag 読み書きロジック
  - monitoring_engine.py: 個別監視をまとめるオーケストレータ
  - alert_manager.py: アラート送信（LINE 等、設定により有効化）

- utils/
  - logging_setup.py: ログ初期化ユーティリティ
  - process_priority.py: プロセス優先度 / CPU affinity 設定ユーティリティ

注意事項 / 運用上の留意点
------------------------
- 本番動作時は KABUSYS_ENV を適切に設定し、特に live の場合は .env の内容を慎重に確認してください（validate_config では live 時の追加警告を出します）。
- Monitoring は KABUSYS_ENV にかかわらず本番の sqlite_path を使用して監視テーブルを初期化する設計になっています（run_monitoring の挙動）。
- OpenAI を使用する機能は OPENAI_API_KEY が必要です。API エラー時のフォールバックやリトライロジックが組まれていますが、API 利用量・コストに注意してください。
- PID ファイル・フラグファイル（data/*.flag/.pid）は適切に管理してください（KILL_FLAG_CLEAR_ON_START=1 は本番では危険です）。

貢献 / 拡張
------------
- 研究用途のクエリやファクターは DuckDB の prices_daily / raw_financials に依存します。データパイプラインから正しいテーブルを投入してください。
- BrokerClientFactory を拡張して実ブローカ接続や MockBroker を追加できます。
- ログフォーマット・通知チャネルの追加は utils/logging_setup.py / monitoring/alert_manager.py を拡張してください。

参照
----
- 各モジュールの詳細な挙動・設計はソースコード内の docstring コメントをご参照ください（特に ai/*.py と research/*.py はアルゴリズム設計に関する注釈を含みます）。

問題報告 / 要望
----------------
Issue や Pull Request を通じてご連絡ください。開発時のローカル実行・検証に必要な追加スクリプトやサンプルデータを整備する計画があります。

以上。プロジェクトのその他の詳細はソースを参照してください。