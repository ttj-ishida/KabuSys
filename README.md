# KabuSys

日本株自動売買システムのリポジトリ（ライブラリ / 起動スクリプト / ユーティリティ群）。

本 README はコードベースの主要機能、セットアップ手順、使い方、ディレクトリ構成を日本語でまとめたものです。

---

## プロジェクト概要

KabuSys は日本株の自動売買プラットフォーム向けに設計されたモジュール群です。主なコンポーネントは以下です。

- ExecutionEngine（発注エンジン）: ブローカークライアントを通じて発注・オーダー管理・リスク管理を実行
- Monitoring（監視）: システムの稼働状況・データ鮮度・注文ログ・リスク指標を定期的にチェックし、必要に応じて Kill Switch を発動
- Portfolio（ポートフォリオ構築）: 候補選定、重み計算、ポジションサイズ計算、セクター制約等の純粋関数群
- Research（リサーチ）: ファクター計算、将来リターン、IC 計算など
- AI（ニュース NLP / レジーム判定）: OpenAI を使ったニュースセンチメントスコアリング、マクロセンチメント合成による市場レジーム推定
- Tools: ペーパートレーディングの検証レポート生成などの補助スクリプト
- Utilities: ロギング設定、プロセス優先度設定、設定読み込み等のユーティリティ

設計の特徴:
- 本番 DB とペーパートレード DB を分離（KABUSYS_ENV による）
- 多くの処理は純粋関数または DB 書き込みのみ（安全性を重視）
- .env ベースの設定管理 + 対話式ウィザード / 検証 CLI を提供

---

## 主な機能一覧

- 起動スクリプト
  - python -m kabusys.run_execution : ExecutionEngine を起動
  - python -m kabusys.run_monitoring : SystemMonitor のポーリングを実行
- 設定関連
  - python -m kabusys.config_setup : .env の対話式生成・更新ウィザード
  - python -m kabusys.validate_config : 環境変数 / config/*.yaml の静的検証
- モニタリング
  - SystemMonitor, TradeMonitor, RiskMonitor を統合する MonitoringEngine
  - リスク閾値超過時に data/kill.flag を書き込む KillSwitch
- 発注関連
  - BrokerClientFactory により実環境／モック（paper_trading）を選択可能
  - OrderRepository / OrderManager / RiskManager / ExecutionEngine による発注処理
- ポートフォリオ構築
  - 候補選定（スコア順）、等金額 / スコア重み配分、リスクベースの株数算出
  - セクターキャップ適用、レジーム乗数計算
- リサーチ
  - momentum, volatility, value 等のファクター計算（DuckDB を利用）
  - 将来リターン、IC（スピアマンランク相関）算出
- AI（OpenAI 統合）
  - ニュースの銘柄別センチメントスコア化（news_nlp）
  - ETF + マクロニュース合成による市場レジーム判定（regime_detector）
- ツール
  - Paper Trading 検証レポートの生成（tools/paper_verification_report.py）

---

## セットアップ手順

1. リポジトリのクローン / 作業ディレクトリへ移動
   - プロジェクトルートには `pyproject.toml` や `.git` がある想定です。

2. Python 環境（推奨: venv）を用意し依存関係をインストール
   - 必要な主なパッケージ:
     - duckdb
     - psutil
     - openai
     - （任意）PyYAML（config 検証で YAML パースを行う場合）
   - 例:
     - pip install duckdb psutil openai PyYAML

3. .env を作成
   - 推奨: 対話式ウィザードを使用
     - python -m kabusys.config_setup
   - あるいはプロジェクトルートに直接 `.env` を作る。
   - 自動ロード: アプリ起動時にプロジェクトルートの `.env` / `.env.local` が自動で読み込まれます（OS 環境変数が優先）。自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

4. 重要な環境変数（最低限）
   - JQUANTS_REFRESH_TOKEN （必須）
   - KABU_API_PASSWORD （必須）
   - 推奨: KABUSYS_ENV（development / paper_trading / live）
   - その他:
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト: data/paper_trading.db）
     - OPENAI_API_KEY（AI 機能を使う場合）
     - LOG_LEVEL, LOG_DIR, LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID 等
   - PAPER_FILL_MODE（paper_trading 時のモック約定方式）: instant / partial / never / reject

5. ログ / データ用ディレクトリ
   - デフォルトでは `logs/` と `data/` 配下にファイルを作成します。必要に応じて作成／権限を確認してください。`setup_logging` が自動でディレクトリ作成を試みますが、失敗するとファイル出力は無効になります。

---

## 使い方（主要コマンド）

- 設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 厳格モード（警告も失敗扱い）: python -m kabusys.validate_config --strict

- ExecutionEngine（発注エンジン）起動
  - python -m kabusys.run_execution
  - 動作モードは KABUSYS_ENV に依存:
    - paper_trading: MockBrokerClient を使用し、DB は `data/paper_trading.db`（または PAPER_TRADING_SQLITE_PATH）に分離して記録
    - live: 実ブローカーを使用（設定に注意）
  - 停止:
    - run_execution は `data/stop_requested.flag`（プロジェクトルート/data）を監視しており、フラグが存在すると安全に停止します。
    - KillSwitch が発動すると `data/kill.flag` が書き込まれ、ExecutionEngine 内で検知して停止します。
  - PID ファイル: data/execution.pid

- Monitoring（監視）起動
  - python -m kabusys.run_monitoring
  - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を秒単位で上書き（デフォルト 60）
  - 監視は常に（KABUSYS_ENV に関係なく）本番 sqlite_path（Settings.sqlite_path）を使います
  - 停止:
    - `data/stop_requested.flag` を作成するとループを終了して終了します

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - `--db` を省略すると PAPER_TRADING_SQLITE_PATH 環境変数または `data/paper_trading.db` を使用

- AI 機能
  - OPENAI_API_KEY を環境変数で設定（または API キーを関数引数で渡す）
  - news_nlp.score_news、regime_detector.score_regime を使って ai_scores / market_regime テーブルへ書き込み可

---

## 設定（主要環境変数）

主な環境変数（抜粋）:

- JQUANTS_REFRESH_TOKEN （必須）
- KABU_API_PASSWORD （必須）
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（デフォルト: data/paper_trading.db）
- OPENAI_API_KEY（AI 機能用）
- LOG_LEVEL（DEBUG/INFO/...、デフォルト INFO）
- LOG_DIR（ログ保存先、デフォルト logs/）
- MONITOR_POLL_INTERVAL（監視ポーリング間隔秒、デフォルト 60）
- PAPER_FILL_MODE（paper_trading の約定モード: instant|partial|never|reject）
- KILL_FLAG_CLEAR_ON_START（起動時に kill.flag を自動クリアするか。デフォルト 0）

注意:
- .env の自動ロードはデフォルトで有効です（プロジェクトルートに .env/.env.local がある場合）。無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## ログ / DB

- ログファイル:
  - デフォルト: logs/<app_name>.log（例: logs/execution.log, logs/monitoring.log）
  - 日次ローテーション（30日保持）
  - コンソール出力は stdout に出ます

- SQLite / DuckDB:
  - 監視ログ（SQLite）: data/monitoring.db（SQLITE_PATH）
  - Paper trading（SQLite）: data/paper_trading.db（PAPER_TRADING_SQLITE_PATH）
  - 分析用（DuckDB）: data/kabusys.duckdb（DUCKDB_PATH）
  - 起動時に必要なテーブルは自動で作成・マイグレーションされます（init_monitoring_db など）

---

## 停止 / Kill Switch

- 手動停止（どちらのループも監視）:
  - data/stop_requested.flag を作成すると run_execution / run_monitoring は安全に停止します（起動スクリプトがこのファイルをチェックしています）。
- 自動停止（KillSwitch）:
  - Monitoring の RiskMonitor 等が閾値を超えた場合、KillSwitch が `data/kill.flag` に理由を書き込みます。ExecutionEngine はこれを検出して停止します。
  - KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に kill.flag を自動でクリアしますが、本番では 0 を推奨します。

---

## トラブルシューティング

- 設定やパスに不安がある場合:
  - python -m kabusys.validate_config を実行してエラー／警告を確認する
- ログを確認:
  - logs/<app>.log を確認する（logging_setup が出力を管理）
- AI 周りが動かない:
  - OPENAI_API_KEY の設定、ネットワーク接続、API レート制限に注意
- DB に書き込みが行われない:
  - sqlite ファイルのパーミッション、ディレクトリの存在、ログに出るエラーを確認

---

## 開発者向けメモ / 主要モジュールの説明

- kabusys.config
  - .env の自動読み込み / Settings クラス（プロパティとして各種設定を提供）
- kabusys.run_execution
  - ExecutionEngine の起動スクリプト。KABUSYS_ENV に応じて paper_trading 用 DB / モックブローカーを使用
- kabusys.run_monitoring
  - SystemMonitor のポーリング起動スクリプト。MONITOR_POLL_INTERVAL で間隔指定可
- kabusys.monitoring
  - monitoring_db.py: SQLite のテーブル作成 / CRUD ラッパ
  - system_monitor.py, trade_monitor.py, risk_monitor.py, kill_switch.py, monitoring_engine.py, alert_manager.py（アラート送信等）
- kabusys.execution
  - BrokerClientFactory / ExecutionEngine / OrderManager / RiskManager / Reconciler 等（発注フロー）
- kabusys.portfolio
  - portfolio_builder.py, position_sizing.py, risk_adjustment.py（純粋関数で計算）
- kabusys.research
  - factor_research.py, feature_exploration.py（DuckDB を使ったファクター・統計）
- kabusys.ai
  - news_nlp.py, regime_detector.py（OpenAI を使ったスコアリング・レジーム判定）
- kabusys.tools
  - paper_verification_report.py（Paper Trading の検証レポート出力）
- kabusys.utils
  - logging_setup.py（ログ統一設定）
  - process_priority.py（プロセス優先度 / CPU affinity 設定）

---

## ディレクトリ構成

（プロジェクトルートの `src/kabusys` を抜粋）

- src/kabusys/
  - __init__.py
  - config.py
  - config_setup.py
  - validate_config.py
  - run_execution.py
  - run_monitoring.py
  - execution/
    - broker_factory.py
    - execution_engine.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
  - monitoring/
    - monitoring_db.py
    - monitoring_engine.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py
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
  - tools/
    - paper_verification_report.py
  - utils/
    - logging_setup.py
    - process_priority.py
  - data/ (runtime)
    - monitoring.db (デフォルト)
    - paper_trading.db (paper_trading 用)
    - execution.pid
    - stop_requested.flag
    - kill.flag
  - logs/ (runtime)
    - execution.log
    - monitoring.log
    - ...

---

## 最小 .env（例）

例として最低限必要なキー（実運用時は適切に設定してください）:

JQUANTS_REFRESH_TOKEN=your_jquants_token_here
KABU_API_PASSWORD=your_kabu_api_password_here
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
LOG_LEVEL=INFO

（`python -m kabusys.config_setup` で対話的に生成することを推奨します）

---

これで README の概略は以上です。追加で「デプロイ手順」「Dockerfile」「systemd サービス定義」「詳細な API 使用方法（ブローカークライアントの設定等）」などが必要であれば、使い方や運用想定に応じて追記できます。どの情報を詳細化したいか教えてください。