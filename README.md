# KabuSys

日本株向けの自動売買システム（KabuSys）のコードベース README（日本語）。

概要、主要機能、セットアップ手順、使い方、ディレクトリ構成をまとめています。

---

## プロジェクト概要

KabuSys は日本株の自動売買・リサーチ・監視を目的としたモジュール群です。  
主な設計方針は以下の通りです。

- 発注ロジックと監視ロジックを分離（ExecutionEngine / MonitoringEngine）
- DuckDB を用いた解析用データと SQLite を用いた監視・ログ永続化
- Paper Trading（模擬発注）と Live（実発注）を環境変数で切替可能
- LLM（OpenAI）を使ったニュースセンチメントやレジーム判定の統合（オプション）
- 設定ウィザード/検証ツールを備え、運用開始を支援

バージョン: 0.1.0（パッケージ定義内）

---

## 機能一覧

- Execution（ExecutionEngine）
  - ブローカークライアント挿抜可能（実運用 / Mock に対応）
  - 注文管理、リスク管理、照合（reconciler）などの起動ループ
  - Paper Trading では専用 SQLite DB（デフォルト: `data/paper_trading.db`）に記録

- Monitoring（System / Trade / Risk Monitors）
  - CPU / メモリ / ディスク / プロセス存否の監視
  - データ鮮度チェック（DuckDB の prices_daily を参照）
  - 注文滞留 / 約定異常 / ドローダウン検出
  - KillSwitch（条件を満たすと `data/kill.flag` を作成）

- ポートフォリオ構築（純粋関数）
  - 候補選定、等重/スコア加重、ポジションサイズ計算、セクター上限制御、レジーム乗数

- リサーチ
  - ファクター計算（モメンタム、ボラティリティ、バリュー等）
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリー

- AI
  - ニュースの NLP スコアリング（OpenAI 使用）
  - 市場レジーム判定（MA200 乖離 + マクロセンチメント）
  - API 呼び出しはフェイルセーフ／リトライつき

- ユーティリティ
  - ログ設定（コンソール + 日次ローテートファイル）
  - プロセス優先度 / CPU affinity 設定
  - 設定ウィザード（`.env` 生成）および設定検証 CLI
  - Paper Trading の検証レポート生成ツール

---

## 前提（Requirements）

- Python 3.10 以上（型ヒントで | 演算子等を使用しているため）
- 推奨ライブラリ（最低限）:
  - duckdb
  - psutil
  - openai （AI 機能を使う場合）
  - PyYAML（config YAML 検証を行う場合）
- OS: Linux / macOS / Windows（プロセス優先度周りはプラットフォーム差分処理あり）

インストール例（仮）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai pyyaml
```
（実際はプロジェクトに requirements.txt があればそちらを使用してください）

---

## セットアップ手順（初期）

1. リポジトリをクローン／配置
2. Python 仮想環境を作成し依存をインストール
3. `.env` を作成
   - 対話式ウィザード:
     ```bash
     python -m kabusys.config_setup
     ```
   - もしくは `.env` を手動で作成（例は下記参照）

4. 設定検証:
   ```bash
   python -m kabusys.validate_config
   # 警告を FAIL 扱いにする場合:
   python -m kabusys.validate_config --strict
   ```

5. DB ファイルは起動時に自動で作成／マイグレーションされます（`data/` 下）。DuckDB のパスも `.env` で指定可能。

---

## 環境変数（主要）

主な環境変数（一覧）:

- 必須
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD

- 実行環境
  - KABUSYS_ENV: `development` | `paper_trading` | `live` （デフォルト: `development`）

- データベース
  - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト: data/paper_trading.db）

- ログ / PID / Kill
  - LOG_LEVEL（例: INFO）
  - LOG_DIR（デフォルト: logs/）
  - PID_FILE_PATH（デフォルト: data/execution.pid）
  - KILL_FLAG_PATH（デフォルト: data/kill.flag）
  - KILL_FLAG_CLEAR_ON_START（"1" にすると起動時に kill.flag を自動クリア）

- Monitoring 専用
  - MONITOR_POLL_INTERVAL（秒、デフォルト: 60。0以下は無効。）

- Paper Trading
  - PAPER_FILL_MODE: `instant` | `partial` | `never` | `reject`（デフォルト: `instant`）

- OpenAI
  - OPENAI_API_KEY（AI 機能を使う際に必要）

必要な値は `python -m kabusys.validate_config` でチェック可能です。

例（最小 .env の抜粋）:
```
JQUANTS_REFRESH_TOKEN=your_token_here
KABU_API_PASSWORD=your_kabu_password
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
LOG_LEVEL=INFO
```

---

## 使い方（実行例）

プロセスは複数のスクリプト／モジュールで構成されています。プロジェクトルートで実行する想定です。

- ExecutionEngine を起動
  - Paper trading:
    ```bash
    export KABUSYS_ENV=paper_trading
    python -m kabusys.run_execution
    ```
  - Live:
    ```bash
    export KABUSYS_ENV=live
    python -m kabusys.run_execution
    ```
  - 実行中に停止させたい場合はプロセスに stop フラグファイルを渡す:
    - 監視側・オペレータが停止要求する場合:
      ```bash
      touch data/stop_requested.flag
      ```
    - ExecutionEngine は起動時/ループ中に `data/stop_requested.flag` をチェックして安全に停止します。

- Monitoring を起動
  - ポーリング間隔を変更する場合:
    ```bash
    export MONITOR_POLL_INTERVAL=30
    python -m kabusys.run_monitoring
    ```
  - 監視ループは `data/stop_requested.flag` を検出すると終了します。

- 設定ウィザード（.env を作成／更新）
  ```bash
  python -m kabusys.config_setup
  ```

- 設定検証
  ```bash
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- Paper Trading 検証レポート生成
  ```bash
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB パスを直接指定する場合:
  python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db
  ```

- AI 機能（ニュース NLP / レジーム判定）
  - `OPENAI_API_KEY` を環境変数に設定してから呼び出してください。
  - 例（モジュール関数呼び出し、スクリプトは用意されている場合あり）:
    ```bash
    export OPENAI_API_KEY="sk-..."
    # Python REPL などから:
    from kabusys.ai.news_nlp import score_news
    # duckdb コネクションを作成して呼び出す
    ```

---

## 停止・Kill Switch の運用

- 一時停止／終了（オペレータ側）
  - `data/stop_requested.flag` を作成すると run_monitoring / run_execution のループが検出して停止します。

- 自動停止（システム側）
  - KillSwitch（監視モジュール）が条件を検出すると `data/kill.flag` を作成します。`KILL_FLAG_CLEAR_ON_START` による自動クリアが有効でない限り本番では注意が必要です。

---

## ログ

- ログはデフォルトで stdout（コンソール）と日次ローテートファイル（logs/<app_name>.log）に出力されます。
- ログ出力設定は `kabusys.utils.logging_setup.setup_logging` で統一管理されます。
- ログディレクトリは `LOG_DIR` 環境変数またはデフォルト `logs/`。

---

## ディレクトリ構成（主要ファイル）

以下はリポジトリ内の主要なディレクトリ / ファイルのスニペット（src/kabusys 以下）。実際のファイル数はこの README に示されたもの以外も存在する場合があります。

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数 / Settings
  - config_setup.py           — .env 対話式ウィザード
  - validate_config.py        — 起動前設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — SystemMonitor ポーリング起動スクリプト

  - execution/ (発注関連)
    - broker_factory.py
    - execution_engine.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py

  - monitoring/
    - monitoring_db.py         — SQLite スキーマ & 永続化層
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
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

- config/
  - (system_config.yaml, data_config.yaml, strategy_config.yaml, risk_config.yaml, execution_config.yaml, monitoring_config.yaml)
    - YAML は検証対象。自動生成スクリプトが用意されている場合あり。

- data/ (実行時に DB / フラグ / pid 等が置かれる、デフォルト)
  - monitoring.db (SQLite)
  - paper_trading.db (paper_trading 用 SQLite)
  - kabusys.duckdb (DuckDB)
  - execution.pid
  - stop_requested.flag
  - kill.flag

- logs/ (ログ出力先)

---

## 主要 DB スキーマ（監視用：monitoring_db.py）

`monitoring_db.init_monitoring_db` は以下のテーブルを作成します（冪等）:

- system_status:
  - recorded_at, cpu_percent, memory_percent, disk_percent, process_ok
- trade_logs:
  - logged_at, event_type (Created/ Filled / Sent など), client_order_id, code, side, qty, price, filled_qty, state, latency_ms
- positions:
  - code (PK), qty, avg_price, current_price, updated_at
- risk_logs:
  - logged_at, event_type, metric_name, metric_value, threshold, detail
- dashboard:
  - id (=1), updated_at, portfolio_value, cash, drawdown_pct, open_order_count, position_count, peak_value

これらは Monitoring および Execution の運用に利用されます。

---

## 開発／運用上の注意

- KABUSYS_ENV が `live` の場合は特に注意してください（validate_config で警告が出ます）。
- `KILL_FLAG_CLEAR_ON_START=1` は本番では危険です（自動で kill.flag をクリアしてしまうため）。
- OpenAI を利用する機能は API コスト・レート制限に注意。API キーの管理は `.env` で行ってください。
- DuckDB / SQLite のファイルパスは環境変数で変更できます。バックアップ・アクセス権に注意してください。
- ログディレクトリに権限問題があるとファイルハンドラの設定が失敗し、コンソールログのみになる旨の警告が出ます。

---

## 参考コマンド一覧

- .env 作成
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- 実行エンジン起動
  - python -m kabusys.run_execution

- 監視起動
  - python -m kabusys.run_monitoring

- Paper Trading レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

---

必要があれば、README にサンプル .env、より詳しい起動フロー図、各コンポーネントの API（関数シグネチャ）やユースケース別の運用手順（開発環境／本番環境）を追加します。どの情報を優先して追記するか教えてください。