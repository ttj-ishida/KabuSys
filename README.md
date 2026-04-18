# KabuSys — README

KabuSys は日本株の自動売買・研究・監視を目的とした Python パッケージです。  
このリポジトリは取引エンジン（ExecutionEngine）、監視（Monitoring）、ファクター計算・リサーチ、AI を用いたニュースセンチメント判定、ポートフォリオ構築ユーティリティなどを含みます。

バージョン: 0.1.0

---

## プロジェクト概要

主な目的:
- 日次・リアルタイムでの銘柄選定→発注→約定監視の自動化
- Paper Trading（ペーパートレード）と Live（実口座）を切り替え可能
- システム稼働性・注文状態・リスク（ドローダウン・ポジション上限等）を監視し、必要時に Kill Switch で発注エンジンを停止
- DuckDB を用いた分析用ファクタ計算・研究機能
- OpenAI（gpt-4o-mini）を利用したニュースセンチメント評価・市場レジーム判定（オプション）

設計方針:
- DB（SQLite / DuckDB）と分離されたモジュール構成
- 多くの処理は純粋関数または副作用を明示した I/O 層で実装
- 本番とペーパートレードを明確に分離（DB ファイル等）

---

## 機能一覧

- Execution
  - ExecutionEngine による注文管理（OrderManager / OrderRepository / Reconciler）
  - BrokerClientFactory による実ブローカー / モックブローカーの切り替え（KABUSYS_ENV）
  - Paper Trading モード: MockBrokerClient を使用し、`data/paper_trading.db` に記録
- Monitoring
  - SystemMonitor: CPU/メモリ/ディスク/プロセス状態、データ鮮度チェック
  - TradeMonitor: 注文滞留や約定異常などの監視（trade_logs 参照）
  - RiskMonitor: ドローダウン・ポジション上限の監視とリスクログ登録
  - KillSwitch: 条件に応じて `data/kill.flag` を生成し ExecutionEngine を停止
  - MonitoringEngine: 上記を統合してポーリング（監視ループ）
- Data / Research
  - DuckDB を用いたファクター計算（モメンタム / ボラティリティ / バリュー 等）
  - 将来リターン計算、IC（情報係数）計算、ファクタサマリー
- Portfolio
  - 候補選定、等金額 / スコア加重配分、リスクベースのポジションサイズ計算
  - セクターキャップ適用、レジーム乗数（bull/neutral/bear）
- AI
  - news_nlp: raw_news を集約して LLM に投げ、銘柄ごとのセンチメントを ai_scores に書き込み
  - regime_detector: ETF の MA200 乖離とマクロニュースセンチメントを合成して market_regime を算出
- Tools
  - paper_verification_report: Paper Trading DB を解析して稼働率・注文成功率・レイテンシ等のレポートを生成
- 設定ユーティリティ
  - config_setup: 対話式で `.env` を作成 / 更新
  - validate_config: 起動前に環境変数・config/*.yaml の存在・妥当性をチェック
- ユーティリティ
  - ロギング設定（stdout + 日次ローテートファイル）
  - プロセス優先度 / CPU affinity 設定ユーティリティ

---

## セットアップ手順

前提:
- Python 3.9+（コードは型ヒントを使用）
- OS: Linux / macOS / Windows どれでも動作するよう配慮あり（ただし process priority 周りは権限依存）

1. リポジトリをクローンして作業ディレクトリへ
   ```
   git clone <repo-url>
   cd <repo-root>
   ```

2. 仮想環境の作成（任意）
   ```
   python -m venv .venv
   source .venv/bin/activate  # Linux/macOS
   .venv\Scripts\activate     # Windows
   ```

3. 必要パッケージをインストール
   - 必要な主なライブラリ:
     - duckdb
     - psutil
     - openai (AI 機能を使う場合)
     - PyYAML (validate_config で YAML 検証を行う場合)
   例:
   ```
   pip install duckdb psutil openai PyYAML
   ```
   （requirements.txt がある場合はそれを利用してください）

4. 初期設定ファイル `.env` を作成する
   - 対話式ウィザード:
     ```
     python -m kabusys.config_setup
     ```
   - あるいは `.env.example` を参考に手動作成。

5. 設定検証（起動前確認）
   ```
   python -m kabusys.validate_config
   # 警告をエラー扱いにする場合
   python -m kabusys.validate_config --strict
   ```

6. ディレクトリ / ファイル
   - データ: data/
     - data/kabusys.duckdb (DuckDB, default)
     - data/monitoring.db (監視用 SQLite, default)
     - data/paper_trading.db (Paper トレード用 SQLite)
     - data/execution.pid (ExecutionEngine の PID file)
     - data/kill.flag (Kill Switch 用)
     - data/stop_requested.flag (run_* スクリプトが停止チェックに使う)
   - ログ: logs/（デフォルト。環境変数 LOG_DIR で変更可能）

補足:
- 自動 .env ロードはデフォルトで有効。テストで無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## 使い方

基本的な実行例（パッケージのモジュールを直接起動）:

- ExecutionEngine を起動（本番 / ペーパートレードは KABUSYS_ENV に依存）
  ```
  python -m kabusys.run_execution
  ```
  メモ:
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient が使用され、データは `PAPER_TRADING_SQLITE_PATH`（デフォルト `data/paper_trading.db`）に記録されます。
  - 起動時に `data/stop_requested.flag` が存在するとエンジンは起動せず終了します。
  - 実行中は `data/execution.pid` に PID が書かれます。

- Monitoring（監視ループ）を起動
  ```
  # ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL（秒）で上書き可（デフォルト 60 秒）
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  ```
  メモ:
  - Monitoring は KABUSYS_ENV に関係なく本番の sqlite_path（Settings.sqlite_path）を使用して監視テーブルを初期化します。
  - `data/stop_requested.flag` が作成されると監視ループは終了します。

- Paper Trading 検証レポートを生成
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB パスを指定する場合:
  python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
  ```

- 設定ウィザード / 検証:
  ```
  python -m kabusys.config_setup
  python -m kabusys.validate_config
  ```

主要な環境変数（一部）:
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
- OPENAI_API_KEY (AI 機能を使う場合)
- KABUSYS_ENV: development | paper_trading | live (デフォルト: development)
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (デフォルト: data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH (デフォルト: data/paper_trading.db)
- PAPER_FILL_MODE (instant | partial | never | reject) — MockBroker の挙動
- LOG_LEVEL (DEBUG/INFO/...)
- LOG_DIR (ログ出力先)
- MONITOR_POLL_INTERVAL (監視のポーリング間隔（秒）)
- KILL_FLAG_CLEAR_ON_START (0/1) — 起動時に kill.flag を自動でクリアするか（本番では 0 推奨）

Kill Switch / 停止フラグ:
- KillSwitch は監視結果に応じて `data/kill.flag` を作成します（既存ファイルがある場合は上書きしない）。
- ExecutionEngine / Monitoring は `data/stop_requested.flag`（run_* スクリプトがチェック）を見て、存在すれば安全に停止します。
- 手動で停止するには該当フラグファイルを作成してください（または ExecutionEngine のプロセスを停止）。

ログ:
- setup_logging() により stdout と日次ローテーションファイル（logs/<app_name>.log）に出力されます。
- ログディレクトリは環境変数 `LOG_DIR` または引数で変更可。

---

## ディレクトリ構成

（src 以下を抜粋）

- src/
  - kabusys/
    - __init__.py
    - config.py                — 環境設定/Settings（.env 自動ロード含む）
    - config_setup.py          — .env 対話式ウィザード
    - validate_config.py       — 設定検証 CLI
    - run_execution.py         — ExecutionEngine 起動スクリプト
    - run_monitoring.py        — Monitoring 起動スクリプト
    - tools/
      - paper_verification_report.py  — Paper Trading レポートツール
    - ai/
      - news_nlp.py             — ニュース NLP（OpenAI）・ai_scores 書込み
      - regime_detector.py      — 市場レジーム判定（MA200 + マクロセンチメント）
    - monitoring/
      - monitoring_db.py        — SQLite 永続化レイヤ（system_status, trade_logs, positions, risk_logs, dashboard）
      - system_monitor.py       — システム・データ鮮度監視
      - trade_monitor.py        — （該当ファイル抜粋により機能）
      - risk_monitor.py         — ドローダウン・ポジション上限監視
      - kill_switch.py          — kill.flag 書き込みユーティリティ
      - monitoring_engine.py    — 各 Monitor を束ねるエンジン
      - alert_manager.py        — （アラート送信管理・該当ファイル参照）
    - execution/
      - execution_engine.py     — 実際の ExecutionEngine 実装（起動・run_session 等）
      - broker_factory.py       — Broker クライアントファクトリ（Mock/Real 切替）
      - order_manager.py
      - order_repository.py
      - reconciler.py
      - risk_manager.py
    - portfolio/
      - portfolio_builder.py
      - position_sizing.py
      - risk_adjustment.py
    - research/
      - factor_research.py
      - feature_exploration.py
    - utils/
      - logging_setup.py        — ロギング初期化
      - process_priority.py     — プロセス優先度 / CPU affinity
    - data/                    — 実行時に作られる想定のディレクトリ（リポジトリ直下）
      - *.db, *.pid, kill.flag, stop_requested.flag
    - config/                  — YAML 設定ファイル群（system_config.yaml 等）

---

## 追加の注記 / 実運用上の注意

- 本番（KABUSYS_ENV=live）では必須環境変数・LINE 通知設定等を必ず確認してください。validate_config は live の場合に追加警告を出します。
- Paper Trading は本番 DB と完全分離される設計です（PAPER_TRADING_SQLITE_PATH を使用）。
- OpenAI を利用する機能は API 利用料が発生します。API キーは安全に管理してください。
- process priority の変更や CPU affinity の設定は OS 権限に依存します。権限不足時は警告ログでスキップされます。
- DuckDB / SQLite のファイルパスやログディレクトリは環境変数で簡単に変更可能です。
- 長時間運用する際はログローテーション・ディスク容量・DB バックアップを検討してください。
- モジュールはユニットテストを想定した作り（外部依存は注入・差し替えできる）になっています。テストでは環境変数自動ロードを無効化するか、モックで差し替えてください。

---

README は以上です。必要であれば以下の追加を作成できます:
- quick start のデモ手順（最小構成での起動例）
- example .env（機密値はダミー）
- requirements.txt / docker-compose 定義

どれを追加しますか？