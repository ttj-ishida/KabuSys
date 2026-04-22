# KabuSys

日本株向け自動売買システムのサブコンポーネント群。  
このリポジトリには、実行エンジン（ExecutionEngine）、監視（Monitoring）、ポートフォリオ構築、リサーチ、AIを使ったニュースセンチメント評価などのユーティリティが含まれます。

バージョン: 0.1.0

---

## 概要（Project overview）

KabuSys は日本株自動売買に必要な以下の機能群をモジュール化した Python コードベースです。

- 実行エンジン（発注管理・リスク制御）
- 監視モジュール（システム状態、注文状況、リスク監視）
- ポートフォリオ構築（銘柄選定、重み付け、ポジションサイズ計算）
- リサーチ（ファクター計算、特徴量探索）
- AI モジュール（ニュースの NLP スコアリング、レジーム判定）
- 運用ユーティリティ（.env ウィザード、設定検証、検証レポート生成）

設計方針の一部：
- データ永続化は DuckDB（分析）と SQLite（監視 / ペーパートレード）を使用
- 環境変数 / .env による設定管理
- 本番（live） / ペーパートレード（paper_trading）を明確に分離
- OpenAI を用いた NLP 部分は失敗時にフォールバック（フェイルセーフ）

---

## 主な機能一覧（Features）

- run_execution: ExecutionEngine の起動スクリプト（本番 / ペーパー混在対応）
  - KABUSYS_ENV が `paper_trading` の時は MockBrokerClient を使用し、ペーパートレード用 DB に記録
  - 停止フラグ / PID ファイルを使った起動・停止管理
- run_monitoring: SystemMonitor のポーリングループ起動スクリプト
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を指定可能（デフォルト 60 秒）
  - 監視ログは常に本番の sqlite_path に記録
- monitoring_engine: System / Trade / Risk の監視をまとめて実行し、Kill Switch やアラートを発生
- monitoring.monitoring_db: 監視用 SQLite スキーマ定義と永続化 API
- monitoring.risk_monitor / trade_monitor / system_monitor: 各種監視ロジック
- ai.news_nlp / ai.regime_detector: OpenAI（gpt-4o-mini 等）を使ったニューススコア・レジーム判定
- portfolio.*: 候補選定、配分、リスク調整、ポジションサイズ計算の純粋関数群
- research.*: ファクター計算、将来リターン、IC 計算など
- tools.paper_verification_report: ペーパートレード結果の合否判定レポート生成
- config_setup: .env を対話式で生成・更新するウィザード
- validate_config: .env や config/*.yaml の事前検証 CLI

---

## 要件（Requirements）

- Python 3.10 以上（型注釈に | 演算子などを使用）
- 必要ライブラリ（例）:
  - duckdb
  - psutil
  - openai
  - PyYAML（config YAML 検証を行う場合、任意）
- 標準ライブラリ: sqlite3, logging, threading など

インストール例（仮の requirements.txt がある前提）:
- 仮想環境の作成と pip インストール（例）
  - python -m venv .venv
  - source .venv/bin/activate
  - pip install -U pip
  - pip install duckdb psutil openai PyYAML

（リポジトリに requirements.txt があればそれを使用してください）

---

## セットアップ手順（Setup）

1. リポジトリをクローンしてワークディレクトリへ移動
2. Python 仮想環境を作成・有効化
3. 依存パッケージをインストール（上記参照）
4. .env を作成
   - 対話式で作る（推奨）:
     - python -m kabusys.config_setup
     - ウィザードに従い必須項目（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD など）を入力
   - または手動で `.env` を作成（.env.example を参照）
5. 設定の検証（任意だが推奨）:
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗（exit 1）扱いになる
6. データ / ログディレクトリの作成（通常は自動作成されます）
   - デフォルト DB・ログ:
     - DuckDB: data/kabusys.duckdb
     - SQLite (monitoring): data/monitoring.db
     - Paper trading DB: data/paper_trading.db
     - ログディレクトリ: logs/

注意:
- KABUSYS_ENV により挙動が変わります。値は `development`, `paper_trading`, `live` のいずれか。

---

## 主要な環境変数（抜粋）

- KABUSYS_ENV: execution モード（development / paper_trading / live）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト data/paper_trading.db）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）
- LOG_DIR: ログ保存先ディレクトリ（デフォルト logs/）
- OPENAI_API_KEY: OpenAI API キー（AI 関連機能で使用）
- MONITOR_POLL_INTERVAL: SystemMonitor のポーリング間隔（秒、run_monitoring 用、デフォルト 60）
- PAPER_FILL_MODE: paper_trading 時の MockBroker の約定挙動（instant/partial/never/reject）
- KILL_FLAG_CLEAR_ON_START: ExecutionEngine 起動時に kill.flag を自動クリアするか（0/1）

（詳しい説明は config_setup.py / config.py を参照してください）

---

## 使い方（Usage）

基本はモジュールとして起動します。プロジェクトルートで以下を実行してください。

- 環境セットアップウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - エラーが無ければ exit 0（詳細は出力を参照）

- 実行エンジン起動（ExecutionEngine）
  - python -m kabusys.run_execution
  - 注意:
    - 起動前に data/kill.flag があると起動を行わず終了します（kill.flag は停止シグナル）
    - PID ファイルはデフォルトで data/execution.pid に書き込まれます
    - KABUSYS_ENV=paper_trading の場合、ペーパートレード用 DB に記録され本番 DB と分離されます

- 監視モード起動（SystemMonitor ポーリング）
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒単位で変更可能（例: export MONITOR_POLL_INTERVAL=30）
  - 停止はプロセス中断（Ctrl+C）またはプロジェクトルートの data/stop_requested.flag を作成

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD --to YYYY-MM-DD
    - --db PATH （PAPER_TRADING_SQLITE_PATH より優先して指定）

停止シグナルと制御ファイル:
- data/stop_requested.flag: run_monitoring / run_execution のループを終了させるために監視される（存在すれば終了）
- data/kill.flag: KillSwitch（監視側）が書き込む（ExecutionEngine に対する停止シグナル）
- Settings.kill_flag_clear_on_start=1 にすると起動時に kill.flag を自動削除する（本番環境では 0 推奨）

ログ:
- ログは標準出力と logs/<app_name>.log（TimedRotatingFileHandler、日次ローテート）に出力されます。
- setup_logging() により統一的に設定されます。

---

## 開発時のヒント

- DuckDB や SQLite によるデータは data/ に配置されます。必要に応じてバックアップ・削除を行ってください。
- AI 系モジュールは OpenAI API の呼び出しを行うため API キーが必要です。テストでは API 呼び出しをモックできます（関数を patch）。
- YAML 検証は PyYAML がインストールされている場合のみ行われます。未インストール時は警告が表示され検証はスキップされます。
- プロセス優先度・CPU affinity の設定は psutil を使います。権限やプラットフォームによっては設定に失敗する場合があります（警告ログ）。

---

## ディレクトリ構成（Directory structure）

以下は主要ファイル／ディレクトリの抜粋です（src/kabusys 配下）。

- src/
  - kabusys/
    - __init__.py
    - config.py                    — 環境変数 / 設定管理
    - config_setup.py              — .env ウィザード
    - validate_config.py           — 設定検証 CLI
    - run_execution.py             — ExecutionEngine 起動スクリプト
    - run_monitoring.py            — SystemMonitor 起動スクリプト
    - utils/
      - logging_setup.py           — ログ設定ユーティリティ
      - process_priority.py        — プロセス優先度設定
    - monitoring/
      - monitoring_db.py           — 監視 DB スキーマ & 永続化 API
      - system_monitor.py
      - trade_monitor.py
      - risk_monitor.py
      - monitoring_engine.py
      - kill_switch.py
      - alert_manager.py           — （存在すれば）アラート送信処理
    - execution/
      - execution_engine.py        — 実行エンジン本体
      - order_manager.py
      - order_repository.py
      - broker_factory.py
      - reconciler.py
      - risk_manager.py
    - portfolio/
      - portfolio_builder.py
      - position_sizing.py
      - risk_adjustment.py
    - research/
      - factor_research.py
      - feature_exploration.py
    - ai/
      - news_nlp.py
      - regime_detector.py
    - data/                         — スクリプトやパイプライン用（prices/db 処理等）
    - tools/
      - paper_verification_report.py
    - logs/                         — ログが出力されるディレクトリ（実行時に作成）

（実際のファイル数・構成はリポジトリに依存します。上はソース内の主要モジュールを抜粋したものです。）

---

## 注意事項 / 運用上のポイント

- 本番環境（KABUSYS_ENV=live）では kill.flag の自動クリアは無効（推奨: KILL_FLAG_CLEAR_ON_START=0）にしてください。
- paper_trading モードは実際の発注を行わず、ペーパートレード DB（PAPER_TRADING_SQLITE_PATH）に記録します。実運用と混同しないよう注意してください。
- OpenAI の API 呼び出しには課金が発生します。news_nlp, regime_detector の実行は必要に応じて行ってください。
- ログ・DB のバックアップとローテーション運用を行ってください（ログはデフォルト 30 日保持設定）。

---

## 付録：よく使うコマンド例

- .env ウィザード
  - python -m kabusys.config_setup
- 設定検証
  - python -m kabusys.validate_config
- 実行エンジン起動
  - python -m kabusys.run_execution
- 監視ループ起動
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- Paper Trading の検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- 停止（監視 / 実行ループに検知させる）
  - touch data/stop_requested.flag
- Kill Switch を手動で解除（本番注意）
  - rm -f data/kill.flag

---

この README はコードベース（src/kabusys）から主要点を抜粋して作成しています。実装の詳細や追加オプションは各モジュールの docstring（ファイル冒頭の説明）を参照してください。必要があれば README に追記しますので、補足してほしい項目（例: デプロイ手順、systemd サービス定義、CI/CD 設定 など）を教えてください。