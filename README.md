# KabuSys

日本株向け自動売買システムのコアライブラリ（README）。  
このドキュメントはコードベースの主要コンポーネント、セットアップ、起動手順、使い方、ディレクトリ構成を日本語でまとめたものです。

---

## プロジェクト概要

KabuSys は日本株の自動売買・リサーチ・監視を行うための内部ライブラリ群です。主な機能は以下の通りです。

- 注文実行エンジン（ExecutionEngine）とブローカークライアントの抽象化
- 監視（Monitoring）：システム・注文・リスク監視、Kill Switch
- ポートフォリオ構築（銘柄選定・重み計算・株数決定・セクター制限）
- リサーチ（ファクター計算、特徴量探索、Forward returns、IC）
- AI モジュール（ニュース NLP による銘柄センチメント評価、レジーム判定）
- 各種ユーティリティ（ログ設定、プロセス優先度設定、環境設定ウィザード・検証）
- Paper Trading 用の分離された DB と検証レポート生成ツール

設計上の留意点：
- データ永続化には DuckDB（分析用）と SQLite（監視・注文ログ）を使用
- Paper Trading は本番 DB と分離（別 SQLite ファイル）
- OpenAI を用いた処理は API キーを必要とし、失敗時は安全にフォールバックする設計

---

## 機能一覧（要点）

- 実行スクリプト
  - run_execution.py: ExecutionEngine を起動（KABUSYS_ENV により paper_trading 用の MockBroker を使用）
  - run_monitoring.py: SystemMonitor のポーリングループ起動（MONITOR_POLL_INTERVAL で間隔変更可）
- 環境管理 / 検証
  - config_setup.py: 対話式 .env ウィザード（.env の生成 / 更新）
  - validate_config.py: 環境変数・config/*.yaml の事前検証 CLI（--strict オプションあり）
- 監視
  - monitoring_engine, system_monitor, trade_monitor, risk_monitor, kill_switch, alert_manager（アラート送信を抽象化）
  - MonitoringDB: system_status, trade_logs, positions, risk_logs, dashboard テーブルを持つ
- ポートフォリオ構築
  - portfolio_builder, position_sizing, risk_adjustment
- リサーチ
  - research.factor_research（モメンタム・バリュー・ボラティリティ等）
  - research.feature_exploration（将来リターン / IC / 統計要約）
- AI
  - ai.news_nlp: raw_news を OpenAI でスコアリングして ai_scores に格納
  - ai.regime_detector: ma200 とマクロニュースを合成して市場レジーム判定
- ツール
  - tools.paper_verification_report: Paper Trading の検証レポート生成

---

## 前提・依存関係

主な依存パッケージ（例）：
- Python 3.10+
- duckdb
- psutil
- openai
- PyYAML（config の内容検証を行う場合に必要）
- （他、プロジェクトの extras に準ずる）

例（pip）:
```
pip install duckdb psutil openai PyYAML
```

※ 必要なパッケージはプロジェクトの配布方法により変わるため、配布パッケージの `pyproject.toml` / `requirements.txt` を参照してください。

---

## セットアップ手順（クイックスタート）

1. リポジトリをクローン／配置
2. Python 仮想環境を作成して依存関係をインストール
   ```
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt   # または必要パッケージを個別に pip install
   ```
3. 環境変数設定（.env）を作成
   - 対話式ウィザードを使う：
     ```
     python -m kabusys.config_setup
     ```
   - あるいは `.env` を手動で作成（下記のサンプル参照）
4. 設定検証
   ```
   python -m kabusys.validate_config
   # 警告・エラーを厳密に扱う場合:
   python -m kabusys.validate_config --strict
   ```
5. データディレクトリ/ログディレクトリの確認（デフォルト）
   - DuckDB: data/kabusys.duckdb
   - SQLite (monitoring): data/monitoring.db
   - Paper Trading SQLite: data/paper_trading.db
   - ログ: logs/（アプリ別に日次ローテーション）
   - 必要に応じて環境変数で上書き（下記参照）

---

## 主要環境変数（主なもの）

- 必須（起動前に設定が必要）
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD

- 実行環境
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
    - paper_trading: MockBroker を使用、paper_trading 専用 DB に書き込む
- データベースパス
  - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
  - SQLITE_PATH (監視用、デフォルト: data/monitoring.db)
  - PAPER_TRADING_SQLITE_PATH (paper_trading 用、デフォルト: data/paper_trading.db)
- ログ
  - LOG_LEVEL (DEBUG/INFO/...)
  - LOG_DIR (デフォルト: logs/)
- AI
  - OPENAI_API_KEY（ai.news_nlp / ai.regime_detector が必要）
- 監視/プロセス
  - PID_FILE_PATH（デフォルト: data/execution.pid）
  - KILL_FLAG_PATH（デフォルト: data/kill.flag）
  - KILL_FLAG_CLEAR_ON_START（"0" or "1"。本番では 0 推奨）
- その他
  - MONITOR_POLL_INTERVAL: run_monitoring.py のポーリング間隔（秒。デフォルト 60）
  - PAPER_FILL_MODE: paper_trading の MockBroker の挙動（instant/partial/never/reject）

サンプル .env（最低限）:
```
KABUSYS_ENV=development
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here
KABU_API_PASSWORD=your_kabu_api_password_here
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
LOG_LEVEL=INFO
OPENAI_API_KEY=sk-xxxxxx    # AI 機能を使う場合
```

---

## 使い方（起動・実行例）

- 監視ループ（SystemMonitor）を起動
  ```
  python -m kabusys.run_monitoring
  ```
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒で上書き可能（例: 30 秒）
  - 監視は常に本番の sqlite_path を使用（環境に依らず monitoring DB を参照）
  - 停止方法: プロセスに KeyboardInterrupt（Ctrl+C） またはプロジェクトルートの `data/stop_requested.flag` ファイルを作成するとループを終了します。

- 実行エンジンを起動
  ```
  python -m kabusys.run_execution
  ```
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、paper_trading 用 DB（PAPER_TRADING_SQLITE_PATH）へ書き込みます。
  - 実行エンジンは起動時に `data/execution.pid`（デフォルト）を生成します。停止は `data/stop_requested.flag` を作成するか、プロセスに KeyboardInterrupt。

- 環境検証
  ```
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- 環境設定ウィザード（.env 作成）
  ```
  python -m kabusys.config_setup
  ```

- Paper Trading 検証レポート生成
  ```
  python -m kabusys.tools.paper_verification_report
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB を直接指定する場合:
  python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db
  ```

- AI 関連（プログラムから呼ぶ API）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - いずれも OpenAI API キー（OPENAI_API_KEY）が必要

---

## 停止 / Kill 機構

- グローバル停止フラグ
  - data/stop_requested.flag を作成すると run_monitoring / run_execution の起動ループが検知して停止します（起動時に既に存在すれば実行をスキップする挙動あり）。

- Kill Switch（自動停止）
  - RiskMonitor 等の判定結果に基づき KillSwitch が `data/kill.flag` を書き込みます。
  - ExecutionEngine は kill.flag を監視し、検知時に安全停止します。
  - KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に自動クリアするが、本番では危険なため 0 を推奨します。

---

## ログ

- 共通ログ設定ユーティリティ: kabusys.utils.logging_setup.setup_logging(app_name="execution" など)
  - stdout（StreamHandler）と日次ローテーションのファイルハンドラ（TimedRotatingFileHandler）を設定します。
  - デフォルトログディレクトリ: logs/
  - ログファイル名例: logs/execution.log, logs/monitoring.log

---

## DB スキーマ（監視用/MonitoringDB の主なテーブル）

- system_status: ポーリング時の CPU/MEM/DISK/プロセス生存情報
- trade_logs: 発注イベントログ（event_type: Created/Filled/Sent 等）
- positions: 保有ポジション（code を主キー）
- risk_logs: リスク関連イベント（DRAWDOWN_ALERT など）
- dashboard: 集計値（portfolio_value, cash, drawdown_pct, open_order_count, position_count, peak_value）

MonitoringDB の初期化は init_monitoring_db() が担い、マイグレーション（カラム追加）も行います。

---

## ディレクトリ構成

リポジトリの主要ファイル・ディレクトリ（src/kabusys 以下の抜粋）:

- kabusys/
  - __init__.py
  - config.py                 # 環境変数の読み込み・Settings クラス
  - config_setup.py           # .env 対話ウィザード
  - validate_config.py        # 設定検証 CLI
  - run_monitoring.py         # SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py          # ExecutionEngine 起動スクリプト
  - tools/
    - paper_verification_report.py
  - utils/
    - logging_setup.py        # ログ設定ユーティリティ
    - process_priority.py     # プロセス優先度・CPU affinity 設定
  - monitoring/
    - monitoring_db.py
    - monitoring_engine.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py (実装に応じて)
  - execution/                # ExecutionEngine 周り（Engine, order_manager, broker_factory 等）
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

（上記は主要モジュールの一覧。各ディレクトリにはさらに補助モジュールや実装ファイルがあります）

---

## 補足・運用上の注意

- KABUSYS_ENV が `live` の場合は本番動作になります。起動前に .env / config を十分に確認してください（validate_config はこのためにあります）。
- ログディレクトリ作成に失敗した場合、ファイル出力は無効化されコンソールのみの出力になります。運用時は logs/ を確実に作成してください。
- プロセス優先度変更（set_process_priority("high")）は OS と権限に依存します。権限不足だと警告が出てスキップされます。
- OpenAI 呼び出しにはコストがかかります。news_nlp/regime_detector を実行する際は API 利用状況に注意してください。
- Paper Trading と本番 DB は意図的に分離されていますが、環境変数の設定ミスにより混在させないように注意してください。

---

## さらに詳しく

- 各モジュールの詳細な仕様・アルゴリズム（PortfolioConstruction.md, StrategyModel.md 等の設計文書）を参照すると理解が深まります（リポジトリに同梱されている場合があります）。
- 開発用のテストや CI 設定はプロジェクト固有の方針に従ってください。

---

以上がこのコードベースの README.md です。必要であれば、「導入手順をさらに詳しく（systemd ユニット例 / Docker コンテナ化 / サンプル .env）」「各 CLI の詳細なオプション」「DB スキーマ詳細（CREATE 文）」などの追加セクションも作成できます。どの情報を優先的に追加しますか？