# KabuSys

日本株自動売買システムの一部を切り出した Python パッケージです。  
このリポジトリには、環境設定ウィザード、設定検証、監視/実行の起動スクリプト、ポートフォリオ構築・リスク制御・リサーチ・AI 補助モジュールなどが含まれます。

## 概要
- 実運用を想定した自動売買基盤のコンポーネント群（監視、実行、リスク、ポートフォリオ構築、リサーチ、AI ベースのニュース解析等）。
- 設定は `.env` と環境変数で管理。`config_setup` による対話式ウィザードで `.env` を生成可能。
- paper_trading（ペーパートレード）モードでは本番 DB と分離して専用 SQLite に記録。
- 監視（Monitoring）は別プロセスで動作し、異常検知時に kill.flag を書き込んで ExecutionEngine を停止させる仕組みを備えています。
- DuckDB を分析用 DB、SQLite を監視・発注ログ用（および paper_trading 用）に使用。

## 主な機能一覧
- 環境設定ウィザード（python -m kabusys.config_setup）
- 設定検証ツール（python -m kabusys.validate_config）
- 実行エンジン起動スクリプト（python -m kabusys.run_execution）
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用して paper_trading DB に記録
- 監視（System / Trade / Risk）起動スクリプト（python -m kabusys.run_monitoring）
  - ポーリングにより system/trade/risk をチェックし、必要時に kill.flag を作成
- Paper Trading 検証レポート生成ツール（python -m kabusys.tools.paper_verification_report）
- ポートフォリオ構築ユーティリティ（候補選定・重み計算・ポジションサイズ計算）
- AI 帯域: OpenAI を使ったニュースセンチメント（news_nlp）・レジーム判定（regime_detector）
- ログ設定ユーティリティ、プロセス優先度設定ユーティリティ、監視用 SQLite 抽象化層 等

## 前提条件
- Python 3.10+
- 推奨パッケージ（最低限）:
  - duckdb
  - psutil
  - openai (AI 機能を使う場合)
  - PyYAML（config 検証で YAML の内容を検証する場合に必要）
- OS: Linux / macOS / Windows（process priority の一部はプラットフォーム差あり）

例（仮のインストールコマンド）:
- pip install duckdb psutil openai PyYAML

## セットアップ手順
1. リポジトリをクローンしてソースのルートに移動
2. 仮想環境作成・有効化（任意）
3. 必要なパッケージをインストール
   - 例: pip install -r requirements.txt（requirements.txt があれば）
   - または個別に: pip install duckdb psutil openai PyYAML
4. `.env` を用意する
   - 対話式ウィザード: python -m kabusys.config_setup
   - もしくは手動でルートに `.env` を作成

注意:
- 自動的に `.env` を読み込む機能が有効（デフォルト）です。無効化する場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- `.env` は絶対にリポジトリにコミットしないでください。

## 簡易 .env サンプル
（config_setup で作成できます。必須項目は JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD）
例:
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here
KABU_API_PASSWORD=your_kabu_api_password_here
KABU_API_BASE_URL=http://localhost:18080/kabusapi
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
KABUSYS_ENV=development
LOG_LEVEL=INFO
KILL_FLAG_CLEAR_ON_START=0

## 使い方（主要コマンド）
- 環境設定ウィザード
  - python -m kabusys.config_setup
- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告も失敗扱い（exit(1)）
- 実行エンジン起動
  - python -m kabusys.run_execution
  - 挙動:
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使い paper_trading DB（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）に記録
    - 起動時に data/stop_requested.flag が存在すれば起動を中止
    - 実行中に stop flag が作成されると安全停止
- 監視（SystemMonitor）起動
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL によりポーリング間隔秒を上書き（デフォルト 60）
  - run_monitoring は monitoring 用 DB として settings.sqlite_path を使う（環境にかかわらず本番 sqlite_path を使用）
- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]

実行例:
- デバッグ実行（開発環境）:
  - KABUSYS_ENV=development python -m kabusys.run_execution
- ペーパートレードで起動:
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
- 監視を 30 秒間隔に:
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

## 主要な環境変数（抜粋）
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID (任意、アラート通知用)
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (デフォルト: data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH (ペーパートレード専用 DB、デフォルト: data/paper_trading.db)
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL（デフォルト: INFO）
- KILL_FLAG_PATH (デフォルト: data/kill.flag)
- KILL_FLAG_CLEAR_ON_START (0/1、デフォルト 0)
- MONITOR_POLL_INTERVAL (監視ポーリング間隔秒、デフォルト 60)
- OPENAI_API_KEY (AI 機能使用時に必要)

## 動作の注意点 / アーキテクチャ上のポイント
- Paper Trading 分離:
  - 本番の monitoring DB（SQLITE_PATH）と paper_trading DB（PAPER_TRADING_SQLITE_PATH）は分離されています。KABUSYS_ENV=paper_trading のときに実行エンジンは paper_trading DB を使用します。
- Kill Switch:
  - RiskMonitor 等が条件を満たすと KillSwitch が data/kill.flag を書き込み、ExecutionEngine はこのフラグを検知して安全停止します。
  - kill.flag のパスは Settings.kill_flag_path（環境変数 KILL_FLAG_PATH で上書き可能）。
- stop_requested.flag:
  - run_execution と run_monitoring が参照する「停止要求フラグ」（data/stop_requested.flag）。外部から作成するとプロセスを終了させられます。
- ロギング:
  - 共通の setup_logging を使って stdout と日毎ローテートファイル（logs/<app_name>.log）に出力。
  - デフォルトは logs/ ディレクトリ（環境変数 LOG_DIR で変更可能）。
- プロセス優先度:
  - 起動スクリプトは set_process_priority("high") を呼び出し、psutil を使ってプラットフォームに応じて優先度を設定しようとします（権限がない場合は警告を出し継続）。
- AI 機能:
  - news_nlp / regime_detector は OpenAI API を使用するため OPENAI_API_KEY が必要。API 呼び出しはリトライ等を備えていますが、API の可用性に依存します。
- 自動 .env ロード:
  - プロジェクトルート（.git または pyproject.toml を基準）から .env/.env.local を自動読み込みします。無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1。

## 開発者向けテスト / 実行補助
- 単体の監視ループを1回だけ実行する場合:
  - MonitoringEngine をテスト用に組み立てて run_once() を呼ぶことで単発実行が可能（テストを容易にする設計）。
- DB スキーマ初期化:
  - init_monitoring_db(conn) により監視用 SQLite のテーブルとミグレーションを冪等に作成します。

## 主要なディレクトリ構成
（src 以下を示す。パッケージは kabusys）

- src/kabusys/
  - __init__.py
  - config.py                — Settings / .env ロード
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリングループ起動スクリプト
  - monitoring/
    - monitoring_db.py       — SQLite 永続化層（system_status / trade_logs / positions / risk_logs / dashboard）
    - system_monitor.py      — システム・データ鮮度監視
    - trade_monitor.py       — （trade 監視ロジック）
    - risk_monitor.py        — ドローダウン / ポジション上限監視
    - kill_switch.py         — kill.flag 管理
    - monitoring_engine.py   — 各 Monitor を束ねる実行エンジン
    - alert_manager.py       — アラート送信用（LINE 等、別途実装想定）
  - execution/
    - execution_engine.py    — 実行エンジン本体
    - order_manager.py       — 発注管理
    - order_repository.py    — 注文永続化
    - broker_factory.py      — ブローカークライアント生成（Mock/実装分岐）
    - risk_manager.py        — 実行時リスクチェック
    - reconciler.py          — 注文整合処理
  - portfolio/
    - portfolio_builder.py   — 候補選定 / 重み計算
    - position_sizing.py     — 株数決定・丸め・キャップ処理
    - risk_adjustment.py     — セクターキャップ / レジーム乗数
  - research/
    - factor_research.py     — Momentum/Value/Volatility ファクター計算（DuckDB）
    - feature_exploration.py — IC / forward returns / 統計
  - ai/
    - news_nlp.py            — ニュースセンチメント（OpenAI）
    - regime_detector.py     — 市場レジーム判定（MA + macro sentiment）
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート生成
  - utils/
    - logging_setup.py       — 共有ログ設定
    - process_priority.py    — プロセス優先度 / CPU affinity

ルート:
- data/    — DB やフラグファイル（runtime）を置く想定ディレクトリ
- logs/    — ログファイル出力先（デフォルト）

## 補足・運用上の注意
- 本番運用時は KABUSYS_ENV=live に設定し、LINE 通知などの本番設定（LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID）を確実に設定してください。validate_config は本番モード時の追加チェックを行います。
- KILL_FLAG_CLEAR_ON_START=1 は本番で危険（自動クリアにより停止条件が見落とされる可能性）。本番は 0 を推奨します。
- DuckDB / SQLite のファイルパスは .env で変更可能。バックアップや権限、I/O 性能に注意してください。
- OpenAI を利用する機能は API コストとレイテンシ、障害耐性（リトライなど）を考慮して運用してください。

---

この README はコードベースの主要な用途・起動方法・設定をまとめたものです。個別のモジュール（ExecutionEngine の使い方、AlertManager の実装、ブローカー実装など）については該当ファイルの docstring と実装を参照してください。必要であれば、より詳しい運用ガイドやデプロイ手順、ユニットテストガイドを追加します。