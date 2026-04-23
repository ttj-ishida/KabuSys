# KabuSys

日本株向けの自動売買 / リサーチ基盤ライブラリ群。  
このリポジトリは自動売買エンジン（ExecutionEngine）、監視（Monitoring）、ポートフォリオ構築、ファクター計算、AI を用いたニュース評価などの機能を含みます。

バージョン: 0.1.0

---

## 概要

KabuSys は以下を目的としたコンポーネント群を提供します。

- ExecutionEngine：発注・注文管理・リスク管理を行う実行エンジン（本番 / ペーパートレード対応）
- Monitoring：システム状態、注文ログ、リスクを常時監視し、Kill Switch を発動可能
- Portfolio Construction：銘柄選定・重みづけ・株数決定（純粋関数）
- Research：DuckDB 上の価格・財務データからファクターや統計を計算
- AI モジュール：OpenAI を使ったニュースセンチメント評価・レジーム判定
- ユーティリティ：設定ウィザード、設定検証、ログ設定、プロセス優先度制御 等

設計上の特徴：
- 設定は .env / 環境変数経由で行う（自動ロードあり）
- Paper Trading は本番 DB と分離（data/paper_trading.db）
- DuckDB を分析用 DB、SQLite を監視 / トレードログ用に使用
- OpenAI（gpt-4o-mini）を用いた NLP 機能をオプションで利用可能

---

## 主な機能一覧

- run_execution.py
  - ExecutionEngine を起動。KABUSYS_ENV=paper_trading なら MockBrokerClient を使い、paper_trading DB に記録。
  - プロセス優先度設定、PID 管理、停止フラグ読み取り。
- run_monitoring.py
  - SystemMonitor をポーリング実行。監視結果を SQLite に記録。
  - MONITOR_POLL_INTERVAL 環境変数で間隔上書き（デフォルト 60 秒）。
  - 監視は環境にかかわらず本番 sqlite_path を使用する（意図的）。
- config_setup.py
  - 対話式ウィザードで .env を作成 / 更新。
- validate_config.py
  - .env および config/*.yaml の存在・簡易整合性を検証。`--strict` オプションで警告も失敗扱いに。
- tools/paper_verification_report.py
  - ペーパートレード DB を解析して稼働率・注文成功率・レイテンシ等のレポートを出力。
- portfolio/*
  - 銘柄選定、重み計算、リスク調整、ポジションサイズ計算の純粋関数群。
- research/*
  - DuckDB 上の data からファクター（Momentum/Volatility/Value）や forward returns、IC 等を計算。
- ai/*
  - news_nlp: raw_news を LLM へ投げ銘柄別センチメントを生成し ai_scores に書き込む。
  - regime_detector: ETF (1321) の MA200 とマクロニュースの LLM 評価を合成して市場レジーム判定。
- monitoring/*
  - MonitoringDB（SQLite スキーマ／永続化ユーティリティ）、SystemMonitor, TradeMonitor, RiskMonitor, KillSwitch, MonitoringEngine 等。
- utils/*
  - logging 設定（ファイル・コンソール）、プロセス優先度 / CPU affinity 設定。

---

## 前提 / 必要要件

最低限必要な Python パッケージ（導入例）:

- Python 3.9+
- duckdb
- psutil
- openai (AI 機能を使う場合)
- PyYAML（validate_config の YAML 検証オプション、無くても動作はする）

インストール例:
```
pip install duckdb psutil openai PyYAML
```

（プロジェクトに requirements.txt があればそちらを使用してください）

---

## セットアップ手順

1. リポジトリをクローン／配置
2. 必要パッケージをインストール（上記参照）
3. 環境変数設定
   - 対話式で作る（推奨）:
     ```
     python -m kabusys.config_setup
     ```
     これによりプロジェクトルートに `.env` が生成されます。
   - 手動で設定する場合は `.env` または環境変数で以下を指定します（主要なもの）:

     - JQUANTS_REFRESH_TOKEN (必須)
     - KABU_API_PASSWORD (必須)
     - KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
     - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
     - SQLITE_PATH (監視用、デフォルト: data/monitoring.db)
     - PAPER_TRADING_SQLITE_PATH (ペーパートレード DB、デフォルト: data/paper_trading.db)
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
     - LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL) — デフォルト: INFO
     - OPENAI_API_KEY (AI 機能を使う場合)
     - PAPER_FILL_MODE (paper_trading の Mock の約定モード: instant|partial|never|reject) — デフォルト: instant
     - KILL_FLAG_CLEAR_ON_START (起動時に kill.flag を自動クリア: 0/1) — デフォルト: 0

4. 設定検証（推奨）:
   ```
   python -m kabusys.validate_config
   python -m kabusys.validate_config --strict
   ```

5. データディレクトリ等が必要な場合は自動作成されますが、DB ファイルのパスやログディレクトリ（デフォルト logs/）の親ディレクトリが存在するかを確認してください。

---

## 使い方（実行例）

- ExecutionEngine の起動（本番 / ペーパートレード）
  ```
  python -m kabusys.run_execution
  ```
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し PAPER_TRADING_SQLITE_PATH を使用します。
  - 起動時に data/stop_requested.flag が存在すると起動せずに終了します。
  - 実行中は data/execution.pid に PID を書きます。

- Monitoring の起動（SystemMonitor ポーリング）
  ```
  python -m kabusys.run_monitoring
  ```
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を調整できます（デフォルト: 60）。
  - 監視は環境にかかわらず Settings.sqlite_path（監視用 DB）を使用します。
  - 停止するには data/stop_requested.flag を作成するか KeyboardInterrupt。

- 設定ウィザード（.env 作成）
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- Paper Trading 検証レポート生成
  ```
  python -m kabusys.tools.paper_verification_report
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
  ```

- AI 機能（例: ニューススコア付与）
  - 必要: OPENAI_API_KEY 環境変数設定
  - 実行はライブラリ API を通して呼び出します（例: kabusys.ai.score_news）

---

## 運用上の注意 / オペレーション

- Kill Switch
  - KillSwitch は RiskMonitor 等の結果から data/kill.flag を書き込んで ExecutionEngine の停止を指示できます。
  - 本番では KILL_FLAG_CLEAR_ON_START=0 を推奨（起動時に自動でクリアされると誤起動のリスク）。
- 停止フラグ
  - run_execution / run_monitoring はプロジェクトルートの data/stop_requested.flag を監視して安全に停止します。
- ログ
  - デフォルト：logs/<app_name>.log に日次ローテートで保存（30日分保持）。
  - setup_logging() を各スクリプトが起動時に呼び出します。
- Paper Trading と本番 DB は分離
  - ペーパートレード時は paper_sqlite_path（デフォルト data/paper_trading.db）を使用し、本番監視 DB や本番トレード DB と混ざらないよう設計されています。
- Monitoring の注意
  - run_monitoring は「監視」側の DB（SQLITE_PATH）を使ってログします。環境にかかわらず同じ sqlite_path を参照します（意図的な仕様）。実運用時は path 設定に注意してください。

---

## 環境変数（主要なもの）

- KABUSYS_ENV: development | paper_trading | live (default: development)
- JQUANTS_REFRESH_TOKEN: (必須)
- KABU_API_PASSWORD: (必須)
- KABU_API_BASE_URL: http://localhost:18080/kabusapi
- OPENAI_API_KEY: OpenAI を使う場合に設定
- DUCKDB_PATH: data/kabusys.duckdb
- SQLITE_PATH: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
- LOG_LEVEL: INFO (default)
- LOG_DIR: logs/
- MONITOR_POLL_INTERVAL: 監視のポーリング間隔（秒、default: 60）
- PAPER_FILL_MODE: instant | partial | never | reject (paper_trading の約定挙動)
- KILL_FLAG_CLEAR_ON_START: 0 or 1（本番では 0 推奨）

設定の自動ロード:
- プロジェクトルートに .env / .env.local がある場合、自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。

---

## ディレクトリ構成（主要ファイル）

src/kabusys/
- __init__.py
- config.py — 環境変数 / 設定管理（自動 .env ロード含む）
- config_setup.py — 対話式 .env ウィザード
- validate_config.py — 設定検証 CLI
- run_execution.py — ExecutionEngine 起動スクリプト
- run_monitoring.py — SystemMonitor 起動スクリプト

サブパッケージ:
- ai/
  - news_nlp.py — ニュースを LLM でスコアリングして ai_scores に書き込む
  - regime_detector.py — マクロ + MA200 で市場レジーム判定
- monitoring/
  - monitoring_db.py — SQLite スキーマ定義 / 永続化 API
  - system_monitor.py — システム状態・データ鮮度監視
  - trade_monitor.py — （注文監視ロジック; 省略されている箇所あり）
  - risk_monitor.py — ドローダウン / ポジション上限監視
  - kill_switch.py — kill.flag 書き込みユーティリティ
  - monitoring_engine.py — 各 Monitor を束ねるエンジン
  - alert_manager.py — （アラート送信ロジック; 省略されている箇所あり）
- execution/  (Engine・Order 管理等)
  - execution_engine.py
  - order_manager.py
  - order_repository.py
  - reconciler.py
  - risk_manager.py
  - broker_factory.py
- portfolio/
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py
- research/
  - factor_research.py
  - feature_exploration.py
- tools/
  - paper_verification_report.py
- utils/
  - logging_setup.py
  - process_priority.py

data/ (実行時に使用するファイル・フラグ)
- data/monitoring.db (default)
- data/paper_trading.db (paper trading)
- data/kill.flag (Kill Switch)
- data/stop_requested.flag (監視 / 実行の停止フラグ)
- data/execution.pid (ExecutionEngine の PID)

ログ:
- logs/<app_name>.log （デフォルトのログ出力先）

---

## 開発・拡張ポイント（メモ）

- AI モジュールは OpenAI API に依存します。API 呼び出し部分はテスト時にモック可能な設計になっています。
- DuckDB を中心にリサーチ処理を行うため、データロードパイプライン（prices_daily, raw_financials, raw_news 等）が必要です。
- ポジションサイズ計算やリスク制御は純粋関数で設計されているため単体テストが容易です。
- monitor/engine はアラート管理や Kill Switch と連携し、部分故障時の安全停止をサポートします。

---

必要であれば、README に含めるコマンド例（systemd / supervisor 用のユニット例、CI 用の簡単なテストコマンド、よくあるトラブルシュート）やより詳細な設定項目一覧を追加します。どの情報を優先して追記しますか？