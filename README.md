# KabuSys

日本株自動売買システムのワークスペース（ライブラリ / 起動スクリプト群）

このリポジトリは、データ解析（DuckDB）、ポートフォリオ構築、発注実行（kabuステーション 経由またはペーパートレード）、監視・リスク管理、LLM を使ったニュース NLP などのコンポーネントを含む自動売買システムのコードベースです。

## 概要

- DuckDB と SQLite を併用して履歴・分析データ・監視ログを扱います。
- KABUSYS_ENV によって動作モードが切り替わります（development / paper_trading / live）。
- execution エンジンは paper_trading モード時にモックブローカーを使い、本番 DB と分離して動作します。
- monitoring コンポーネントは実行プロセスや注文状態、リスク（ドローダウン・ポジション数）を定期的にチェックし、必要なら kill.flag を書き込んで ExecutionEngine を停止させます。
- AI コンポーネントは OpenAI API（gpt-4o-mini など）を使ってニュースのセンチメントや市場レジーム判定を行います（APIキー必須）。
- 各種ユーティリティ（ログ設定、プロセス優先度設定、.env ウィザード、設定検証、ペーパートレード検証レポート生成など）を提供します。

## 主な機能一覧

- 実行 / 監視
  - run_execution.py: ExecutionEngine 起動スクリプト
  - run_monitoring.py: SystemMonitor ポーリング起動スクリプト
- 設定管理・検証
  - config_setup.py: 対話式 .env 生成ウィザード
  - validate_config.py: 環境・YAML 設定検証 CLI
- データ & 研究
  - research: ファクター計算（モメンタム / ボラティリティ / バリュー 等）
  - portfolio: 候補選定、重み算出、ポジションサイズ計算、セクター制限など
- AI
  - ai.news_nlp: ニュースのセンチメントスコアリング（OpenAI）
  - ai.regime_detector: 市場レジーム判定（MA + マクロセンチメント）
- 監視
  - monitoring: system_monitor / trade_monitor / risk_monitor / kill_switch / monitoring_engine
  - monitoring_db: SQLite ベースの永続化層（system_status / trade_logs / risk_logs / positions / dashboard）
- ツール
  - tools.paper_verification_report: ペーパートレード検証レポート生成

## セットアップ手順

1. Python 環境を準備（推奨: 3.9+）
2. 必要パッケージをインストール
   - 最低限の依存例:
     - duckdb
     - psutil
     - openai (AI 機能を使う場合)
     - PyYAML（config 検証で YAML 内容検査を行う場合）
   - 例:
     ```
     pip install duckdb psutil openai PyYAML
     ```
3. プロジェクトルートに移動（.git または pyproject.toml があるディレクトリ）
4. .env の初期作成（対話式ウィザード）
   ```
   python -m kabusys.config_setup
   ```
   - あるいは手動で `.env` を作成してください（下の「環境変数」を参照）
5. 設定検証
   ```
   python -m kabusys.validate_config
   ```
   - 警告もエラー扱いにしたい場合は `--strict` を付けます
6. データディレクトリ・ログディレクトリを必要に応じて作成（多くのスクリプトは起動時に自動作成します）

## 環境変数（主なもの）

- 必須（主に本番/分析で必要）
  - JQUANTS_REFRESH_TOKEN: J-Quants API 用リフレッシュトークン
  - KABU_API_PASSWORD: kabuステーション API パスワード
- オプション / 重要
  - KABUSYS_ENV: 実行モード（development / paper_trading / live） — デフォルト: development
    - paper_trading: MockBroker を使用し DB は data/paper_trading.db に分離
  - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH: SQLite（監視 DB）パス（デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
  - LOG_LEVEL: ログレベル（DEBUG/INFO/…、デフォルト INFO）
  - OPENAI_API_KEY: OpenAI API キー（ai モジュールで必須）
  - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: 通知用 LINE 設定（任意）
  - MONITOR_POLL_INTERVAL: run_monitoring および MonitoringEngine 間隔（秒、デフォルト 60）
  - KILL_FLAG_CLEAR_ON_START: Execution 起動時に kill.flag をクリアするか（0|1、デフォルト 0）
- Kill / Stop
  - data/kill.flag: KillSwitch が書き込むと ExecutionEngine に停止シグナルを送ります
  - data/stop_requested.flag: run_execution / run_monitoring の外部停止フラグ（起動スクリプトで使用）

（.env の自動作成は config_setup.py を利用ください。.env は絶対に Git にコミットしないでください）

## 使い方（主要コマンド）

- .env を作る（対話式）
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- ExecutionEngine を起動
  ```
  python -m kabusys.run_execution
  ```
  - KABUSYS_ENV=paper_trading の場合、MockBroker を使用し data/paper_trading.db に記録します
  - 起動時に data/execution.pid を使用／更新します
  - data/stop_requested.flag が存在する場合は起動しない、または実行中は停止します

- Monitoring を起動（SystemMonitor ポーリングループ）
  ```
  python -m kabusys.run_monitoring
  ```
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書きできます（デフォルト 60）
  - 監視は常に本番 sqlite_path（Settings.sqlite_path）を使用してログを残します
  - 停止は data/stop_requested.flag を作成することで行います

- Paper Trading 検証レポート生成
  ```
  python -m kabusys.tools.paper_verification_report
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
  ```

- AI 関連（プログラム経由）
  - OpenAI API キーを設定し、ai モジュールの関数（score_news, score_regime 等）を呼び出してください

## ログ設定

- 全起動スクリプトは共通のユーティリティ `kabusys.utils.logging_setup.setup_logging` を使います
- デフォルトで stdout に StreamHandler を出力し、logs/<app_name>.log に日次ローテーションでログを保存します（30 日分保持）
- LOG_DIR 環境変数でログ保存先を変更できます

## Kill Switch / 停止フラグ

- kill.flag（Settings.kill_flag_path、デフォルト data/kill.flag）:
  - KillSwitch が安全上の理由で ExecutionEngine を停止させるために書き込みます（例: ドローダウン超過）
  - ExecutionEngine はこれを検知して安全停止します
- stop_requested.flag（data/stop_requested.flag）:
  - 外部から run_execution / run_monitoring の起動ループを止めるための簡易フラグ（起動スクリプトでチェック）

## ディレクトリ構成

（抜粋 — 主要モジュールを表示）

- src/
  - kabusys/
    - __init__.py
    - config.py                — 環境変数 / Settings 管理 (.env 自動ロード機能)
    - config_setup.py          — .env 対話式ウィザード
    - validate_config.py       — 設定検証 CLI
    - run_execution.py         — ExecutionEngine 起動スクリプト
    - run_monitoring.py        — SystemMonitor 起動スクリプト
    - ai/
      - news_nlp.py            — ニュース NLP / OpenAI 呼び出し
      - regime_detector.py     — 市場レジーム判定
    - portfolio/
      - portfolio_builder.py
      - position_sizing.py
      - risk_adjustment.py
      - __init__.py
    - research/
      - factor_research.py
      - feature_exploration.py
      - __init__.py
    - monitoring/
      - monitoring_db.py
      - system_monitor.py
      - trade_monitor.py
      - risk_monitor.py
      - kill_switch.py
      - monitoring_engine.py
      - alert_manager.py (※実装参照)
    - tools/
      - paper_verification_report.py
    - utils/
      - logging_setup.py
      - process_priority.py
      - __init__.py
    - execution/
      - execution_engine.py    (Execution 実装)
      - order_manager.py
      - order_repository.py
      - broker_factory.py
      - reconciler.py
      - risk_manager.py
      - ... (その他)
    - data/                     — 実行時に使用する DB / flag / pid 等（通常はルートの data/）
  - pyproject.toml / setup.py 等

（実際のツリーはリポジトリ内を参照してください）

## 開発時の注意点・設計上のポイント

- .env の自動読み込みはプロジェクトルート (.git または pyproject.toml) を基準に行われます。必要に応じて KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
- paper_trading モードでは発注処理を分離し本番 DB に書き込まない設計になっています（PAPER_TRADING_SQLITE_PATH）。
- AI モジュールは API エラーに寛容（リトライやフォールバック）で、API キーが未設定だと明示的に例外を出す箇所があります。OpenAI API 利用時は OPENAI_API_KEY を設定してください。
- Logging は各スクリプト共通のセットアップ関数を使うことで出力を統一しています。
- Monitoring の DB スキーマは init_monitoring_db() で冪等に作成・マイグレーションを行います。
- process priority / CPU affinity の設定は psutil を使い OS に依存しないインターフェースを提供しています。権限が足りない場合は警告が出てスキップします。

## よく使うコマンドまとめ

- .env 作成:
  ```
  python -m kabusys.config_setup
  ```
- 設定検証:
  ```
  python -m kabusys.validate_config
  ```
- 実行エンジン起動:
  ```
  python -m kabusys.run_execution
  ```
- 監視起動:
  ```
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  ```
- ペーパートレード検証レポート:
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```

---

README の内容はコードベースの現状（主要モジュールの役割・設定・起動方法）をまとめたものです。追加したい項目（例: セットアップ用の requirements.txt、ユニットテストの実行方法、デプロイ手順、CI 設定など）があれば指示してください。