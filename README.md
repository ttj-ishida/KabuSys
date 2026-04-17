# KabuSys — 日本株自動売買システム (README)

このリポジトリは日本株の自動売買システム「KabuSys」のコードベースです。  
本 README はリポジトリ内の主要コンポーネントと使い方、セットアップ手順、ディレクトリ構成を日本語でまとめたものです。

注意: 実際に発注を行う機能は本番環境 (KABUSYS_ENV=live) で有効になります。安全のため本番運用前に必ずローカル / ペーパートレードで検証してください。

---

## プロジェクト概要

KabuSys は以下の主要機能を持つモジュール群で構成されています。

- Execution エンジン: 発注ロジック、オーダー管理、リスク管理、約定の調整（reconciler）など。
- Monitoring: システム状態、注文滞留、約定異常、ドローダウン・ポジション数監視、Kill Switch。
- Portfolio construction: 候補選定、重み計算、ポジションサイズ決定、セクター制限、レジーム乗数。
- Research: ファクター計算（Momentum / Value / Volatility 等）、将来リターン、IC 計算など。
- AI モジュール: ニュースセンチメント (OpenAI) を使ったスコアリング、マクロニュースを使った市場レジーム判定。
- Tools: ペーパートレード検証レポート生成など。
- 設定管理: .env ウィザード（config_setup）・設定検証 CLI（validate_config）・Settings クラスによる環境変数管理。

主要言語: Python。データストアに SQLite / DuckDB を利用します。

---

## 機能一覧

- run_execution: ExecutionEngine を起動（KABUSYS_ENV による paper_trading / live 運用切替）
  - paper_trading: MockBrokerClient を使用し、data/paper_trading.db にデータを分離して記録
  - 本番では実ブローカークライアントを使用
- run_monitoring: SystemMonitor をポーリング起動（MONITOR_POLL_INTERVAL 環境変数で間隔指定）
- monitoring_engine: 各モニター（System / Trade / Risk）をまとめてポーリング。アラート送信や Kill Switch 評価を行う
- monitoring_db: 監視用 SQLite スキーマ作成（system_status, trade_logs, positions, risk_logs, dashboard）
- RiskMonitor / TradeMonitor / SystemMonitor: それぞれの監視ロジック
- KillSwitch: data/kill.flag の書き込みで ExecutionEngine に停止シグナルを送る仕組み
- AI: news_nlp.score_news / regime_detector.score_regime — OpenAI を使ったニュースセンチメント・レジーム判定
- portfolio モジュール: 銘柄候補選定、等金額/スコア重み、ポジションサイズ計算、セクター制限、レジーム乗数
- research モジュール: ファクター計算（momentum/value/volatility）、将来リターン、IC 計算、統計サマリ
- tools: paper_verification_report — ペーパートレード DB から検証レポートを生成
- 設定ユーティリティ: config_setup（対話式 .env 作成）、validate_config（設定検証 CLI）

---

## 必要条件（概略）

- Python 3.10 以上（型ヒントの構文に依存）
- 推奨パッケージ（主要なもの）:
  - duckdb
  - psutil
  - openai
  - PyYAML（config 検証時に YAML 検証を行う場合）
- 標準ライブラリ: sqlite3, logging, threading, datetime など

（実際の requirements.txt がない場合は下記コマンドでインストールしてください）

例:
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai PyYAML
```

---

## セットアップ手順

1. リポジトリをクローンしてワークディレクトリへ移動
2. 仮想環境を作成・有効化し、依存パッケージをインストール（上記参照）
3. .env ファイルの作成
   - 対話式ウィザードを使う:
     ```
     python -m kabusys.config_setup
     ```
     ウィザードで JQUANTS_REFRESH_TOKEN や KABU_API_PASSWORD など必須値を入力します。
   - 自動ロード:
     - Settings モジュールはプロジェクトルートにある `.env` / `.env.local` を自動で読み込みます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。
4. 設定の検証:
   ```
   python -m kabusys.validate_config
   ```
   必須環境変数や config/*.yaml（存在する場合）の構文などをチェックします。`--strict` を付ければ警告も失敗扱いになります。
5. データディレクトリの確認:
   - デフォルトの DB パス:
     - DuckDB: data/kabusys.duckdb
     - SQLite（監視）: data/monitoring.db
     - Paper Trading SQLite: data/paper_trading.db
   - 必要に応じて `.env` で `DUCKDB_PATH` / `SQLITE_PATH` / `PAPER_TRADING_SQLITE_PATH` を上書きしてください。
6. （AI 機能を使う場合）OpenAI API キーを設定:
   - 環境変数 `OPENAI_API_KEY` を設定してください。関数呼び出し時に引数で渡すこともできます。

---

## 使い方（コマンド例）

- Execution エンジンを起動
  - Paper trading（MockBroker）
    ```
    export KABUSYS_ENV=paper_trading
    python -m kabusys.run_execution
    ```
  - 本番（注意して使用）
    ```
    export KABUSYS_ENV=live
    python -m kabusys.run_execution
    ```
  - 実行中に停止したい場合は `data/stop_requested.flag` を作成するとループが検知して停止します（run_execution と run_monitoring 両方で使用）。
  - Execution 用の PID ファイル: `data/execution.pid`（デーモン管理などで参照）

- Monitoring を起動
  ```
  export MONITOR_POLL_INTERVAL=60   # オプション（秒）
  python -m kabusys.run_monitoring
  ```
  - MONITOR_POLL_INTERVAL を設定してポーリング間隔を変更できます（デフォルト 60 秒）。
  - 監視は常に本番用の sqlite_path（Settings.sqlite_path）を使用します。

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
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-10
  ```
  - `--db PATH` で DB を指定できます（環境変数 `PAPER_TRADING_SQLITE_PATH` より優先）。

- AI モジュールをスクリプト内で使用する例（モジュール呼び出し）:
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.news_nlp import score_news
  conn = duckdb.connect("data/kabusys.duckdb")
  count = score_news(conn, target_date=date(2026, 4, 11), api_key="sk-...")
  ```

---

## 主要環境変数（抜粋）

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV (development | paper_trading | live) — default: development
- DUCKDB_PATH — default: data/kabusys.duckdb
- SQLITE_PATH — default: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH — default: data/paper_trading.db
- OPENAI_API_KEY — AI 機能で必須（関数引数で渡すことも可）
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒）
- PAPER_FILL_MODE — ペーパートレードの fill 振る舞い（instant / partial / never / reject）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...）
- KILL_FLAG_CLEAR_ON_START — Execution 起動時に kill.flag を自動クリアするか（0/1）

Settings クラスは .env と環境変数の自動読み込みを行います（.env.local は .env を上書き）。

---

## Kill/Stop フラグ

- data/stop_requested.flag:
  - run_execution.py / run_monitoring.py はこのファイルの存在を検知してループを停止します（外部からの停止要求用）。
- data/kill.flag:
  - KillSwitch が検出条件を満たした場合に書き込むファイル。ExecutionEngine はこの flag の存在を検知して停止します（本番保護機構）。
- PID ファイル:
  - `data/execution.pid` に ExecutionEngine の PID を書くことで SystemMonitor がプロセス生存チェックを行います。

---

## 監視 DB（monitoring_db）スキーマ概要

monitoring_db モジュールは以下のテーブルを作成します（冪等）:

- system_status:
  - recorded_at, cpu_percent, memory_percent, disk_percent, process_ok
- trade_logs:
  - logged_at, event_type, client_order_id, code, side, qty, price, filled_qty, state, latency_ms
- positions:
  - code (PK), qty, avg_price, current_price, updated_at
- risk_logs:
  - logged_at, event_type, metric_name, metric_value, threshold, detail
- dashboard:
  - 単一行（id = 1）で集計: portfolio_value, cash, drawdown_pct, open_order_count, position_count, peak_value

これらは MonitoringDB クラスを通じて読み書きされます。

---

## ディレクトリ構成

以下は主要ファイル/ディレクトリのツリー（抜粋）です:

```
src/
└─ kabusys/
   ├─ __init__.py
   ├─ config.py                # Settings および .env 自動ロードロジック
   ├─ config_setup.py         # 対話式 .env ウィザード
   ├─ validate_config.py      # 設定検証 CLI
   ├─ run_execution.py        # ExecutionEngine 起動スクリプト
   ├─ run_monitoring.py       # SystemMonitor ポーリング起動スクリプト
   ├─ utils/
   │   └─ process_priority.py # psutil ベースの優先度/affinity 設定
   ├─ monitoring/
   │   ├─ monitoring_db.py
   │   ├─ system_monitor.py
   │   ├─ trade_monitor.py
   │   ├─ risk_monitor.py
   │   ├─ kill_switch.py
   │   ├─ monitoring_engine.py
   │   └─ alert_manager.py    # （アラート送信ロジック：未表示）
   ├─ execution/
   │   ├─ execution_engine.py
   │   ├─ order_manager.py
   │   ├─ order_repository.py
   │   ├─ reconciler.py
   │   └─ broker_factory.py
   ├─ portfolio/
   │   ├─ portfolio_builder.py
   │   ├─ position_sizing.py
   │   └─ risk_adjustment.py
   ├─ research/
   │   ├─ factor_research.py
   │   └─ feature_exploration.py
   ├─ ai/
   │   ├─ news_nlp.py
   │   └─ regime_detector.py
   ├─ tools/
   │   └─ paper_verification_report.py
   └─ ... (その他モジュール)
```

---

## 開発・運用に関する注意点

- 本番運用前に validate_config で設定を確認してください。KABUSYS_ENV=live の場合は特に LINE 通知設定や Kill Switch の設定を慎重に確認してください。
- AI モジュールは OpenAI API を使用します。API 料金とレート制限に注意してください。429 / 5xx に対しては指数バックオフを実装していますが、運用中のリトライ設定は検討の余地があります。
- Paper Trading モードは本番データベースとは分離されます（PAPER_TRADING_SQLITE_PATH を使用）。
- .env ファイルは機密情報を含むため、絶対に VCS にコミットしないでください。config_setup.py のコメントにも注意書きがあります。
- process_priority の設定は OS に依存します。権限不足で設定に失敗する場合がありますが、その場合はログに警告が出ます。

---

この README はコード内の docstring と実装に基づいて作成しました。更に詳しい内部仕様・設計思想（例: PortfolioConstruction.md, StrategyModel.md）がプロジェクト内に存在する場合はそちらも参照してください。必要なら README を拡張してデプロイ手順や運用 Runbook を追記できます。