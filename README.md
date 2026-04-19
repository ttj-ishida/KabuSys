# KabuSys

バージョン: 0.1.0

KabuSys は日本株向けの自動売買 / 研究プラットフォームです。戦略・ポートフォリオ構築・実行・監視・研究・AI補助モジュールを含むモジュール化されたコードベースです。

---

## プロジェクト概要

- 自動売買エンジン (ExecutionEngine)／ブローカ接続（paper_trading の場合は MockBroker）による発注ロジック
- 監視サブシステム（SystemMonitor / TradeMonitor / RiskMonitor）と Kill Switch（異常時に Execution を停止するフラグ）
- ポートフォリオ構築（候補選定、重み付け、ポジションサイズ決定、セクター制限、レジーム乗数）
- Research ツール（ファクター計算、特徴量探索、IC 計算）
- AI 補助モジュール（ニュースの NLP スコアリング、レジーム判定） — OpenAI API を使用
- ユーティリティ：.env 初期ウィザード、設定検証、ペーパートレード検証レポート生成 等

---

## 主な機能一覧

- 設定管理（.env の自動読込 / config モジュール）
- .env 対話式ウィザード（`kabusys.config_setup`）
- 設定検証 CLI（`kabusys.validate_config`）
- ExecutionEngine 起動スクリプト（`run_execution.py`）
  - KABUSYS_ENV=paper_trading の場合は paper_trading DB を用い MockBrokerClient を利用
- 監視プロセス起動スクリプト（`run_monitoring.py`）
  - ポーリング間隔の環境変数上書き可能（MONITOR_POLL_INTERVAL）
- 監視・ログ永続化（SQLite / monitoring_db）
- Paper Trading 検証レポート生成（`kabusys.tools.paper_verification_report`）
- Research: momentum / volatility / value ファクター計算、forward returns、IC、統計サマリ
- AI: ニュースセンチメント集約・スコアリング（OpenAI）、レジーム検出（OpenAI）

---

## 必要条件

- Python 3.9+
- 必須（用途により）ライブラリ:
  - duckdb
  - psutil
  - openai（AI 機能を使う場合）
  - PyYAML（config ファイル検証に必要だが必須ではない）
- SQLite（標準ライブラリに含まれます）

（実際のプロジェクトでは requirements.txt を用意している想定です。開発環境では仮想環境を推奨します。）

---

## セットアップ手順（ローカル開発向け）

1. リポジトリをクローンして作業ディレクトリへ移動
   - git clone ... && cd <repo>

2. 仮想環境の作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate  # Unix/macOS
   - .venv\Scripts\activate     # Windows

3. 必要パッケージのインストール
   - pip install duckdb psutil openai
   - 任意で PyYAML: pip install pyyaml

4. .env の初期作成
   - 対話式ウィザードを実行して .env を作成:
     - python -m kabusys.config_setup
   - あるいは .env.example を参考に手動作成

5. 設定検証（任意）
   - python -m kabusys.validate_config
   - --strict を付けると警告もエラー扱いになります:
     - python -m kabusys.validate_config --strict

6. データディレクトリの確認
   - デフォルトの DB / ログパス:
     - DuckDB: data/kabusys.duckdb
     - SQLite (monitoring): data/monitoring.db
     - Paper trading SQLite: data/paper_trading.db
     - ログ: logs/
   - 必要なら .env で上書きしてください（DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH, LOG_DIR 等）

---

## 主要な環境変数（よく使うもの・デフォルト）

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV: execution モード
  - 値: development / paper_trading / live
  - デフォルト: development
- DUCKDB_PATH: data/kabusys.duckdb
- SQLITE_PATH: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
- LOG_LEVEL: INFO（DEBUG, INFO, WARNING, ERROR, CRITICAL が指定可能）
- OPENAI_API_KEY: AI 機能を使う場合に必要
- PAPER_FILL_MODE: paper_trading 時の約定挙動（instant, partial, never, reject）
- MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、デフォルト 60）
- KILL_FLAG_CLEAR_ON_START: Execution 起動時に kill.flag を自動クリアするか（0/1）

注: Settings モジュールに主要なデフォルトおよびバリデーションがまとめられています。

---

## 使い方（起動 / 実行方法）

- 監視プロセスを起動
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で上書き可能（例: export MONITOR_POLL_INTERVAL=30）
  - 監視は常に Settings.sqlite_path（本番 DB）を使用します（監視ログは本番 DB に記録）

- ExecutionEngine を起動（発注処理）
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合、paper_trading 用の SQLite（PAPER_TRADING_SQLITE_PATH）を使用し MockBrokerClient で完全分離された検証が可能

- .env 初期作成ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告は FAIL 扱い（exit code 1）

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - デフォルト DB パスは環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db
  - オプション: --db PATH で DB を直接指定可能

- AI モジュール実行（プログラム的に呼ぶ）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - OPENAI_API_KEY が必要（api_key 引数で明示的に渡すことも可）

---

## 停止 / キルフラグ

- Graceful stop（run_monitoring / run_execution が監視するフラグ）
  - プロジェクトルートの data/stop_requested.flag を作成すると、run_monitoring と run_execution は次のポーリング/ループで検出して終了します
- Kill Switch（実行系の強制停止）
  - 監視モジュールはリスク条件（ドローダウン超過など）を検出した場合、data/kill.flag を書き込みます
  - ExecutionEngine 起動時に KILL_FLAG_CLEAR_ON_START=1 が設定されている場合、起動時に kill.flag を自動でクリアします（本番では 0 推奨）
- PID ファイル
  - ExecutionEngine は data/execution.pid を PID ファイルとして扱います（設定で変更可能）

---

## ログ

- 共通ロギングセットアップは kabusys.utils.logging_setup.setup_logging で行われます
  - コンソール (stdout) と日次ローテートのファイルログ (logs/<app_name>.log) を設定
  - LOG_DIR 環境変数またはデフォルト logs/ に出力
  - ログレベルは LOG_LEVEL 環境変数または引数で指定

---

## ディレクトリ構成（主要ファイル）

- src/kabusys/
  - __init__.py
  - config.py — 環境変数読み込み/Settings クラス
  - config_setup.py — .env 対話式ウィザード
  - validate_config.py — 設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート
  - ai/
    - news_nlp.py — ニュース NLP スコアリング（OpenAI）
    - regime_detector.py — 市場レジーム判定（OpenAI）
  - monitoring/
    - monitoring_db.py — SQLite 永続化（system_status, trade_logs, positions, risk_logs, dashboard）
    - system_monitor.py — CPU/mem/disk、データ鮮度、プロセス監視
    - trade_monitor.py — （trade 関連の監視ロジック）
    - risk_monitor.py — ドローダウン/保有上限監視
    - monitoring_engine.py — 各 Monitor を束ねる
    - kill_switch.py — kill.flag 操作
    - alert_manager.py — （通知管理）
  - execution/
    - execution_engine.py — ExecutionEngine の主要ロジック
    - broker_factory.py — ブローカクライアント生成（本番/Mock 切替）
    - order_manager.py, order_repository.py, reconciler.py, risk_manager.py 等
  - portfolio/
    - portfolio_builder.py, position_sizing.py, risk_adjustment.py
  - research/
    - factor_research.py, feature_exploration.py
  - utils/
    - logging_setup.py, process_priority.py

（上記は主要モジュールの抜粋です。細かい実装ファイルは src/kabusys 内を参照してください。）

---

## 開発上の注意点 / 実装に関するポイント

- Settings は .env 自動読み込みを行いますが、テストや特殊用途では KABUSYS_DISABLE_AUTO_ENV_LOAD を設定して自動読込を抑止できます。
- run_execution.py は paper_trading 環境を本番 DB と完全に分離する設計になっています（PAPER_TRADING_SQLITE_PATH を使用）。
- run_monitoring.py は監視ログ用に常に本番 sqlite_path を使用します（監視は本番データの状態を見たい想定）。
- AI モジュールは OpenAI のレスポンスの不安定性を考慮してリトライ／フォールバック実装が入っています。OpenAI API の利用はコスト・レイテンシに注意してください。
- ローカルでの検証には paper_trading モードと検証レポートを活用してください。

---

## よくあるコマンド例

- .env 作成
  - python -m kabusys.config_setup
- 設定検証
  - python -m kabusys.validate_config
- 監視起動（デーモンや supervisor 等で運用する想定）
  - python -m kabusys.run_monitoring
- 実行エンジン起動
  - python -m kabusys.run_execution
- Paper Trading レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

---

## ライセンス / バージョン

- __version__ = "0.1.0"（パッケージヘッダ参照）
- ライセンス情報はリポジトリの LICENSE ファイルをご確認ください（本 README では記載なし）。

---

README の補足や運用手順、CI / デプロイ手順の追記を希望する場合は、用途（ローカル検証 / 本番デプロイ / systemd / Docker 化 等）を教えてください。必要に応じて起動サービス定義例や systemd ユニット、Dockerfile のサンプルを作成します。