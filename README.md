# KabuSys

日本株向け自動売買システムの参考実装（モジュール群）。  
この README はコードベースの使用方法、セットアップ、主要機能、およびディレクトリ構成を日本語でまとめたものです。

---

## プロジェクト概要

KabuSys は次を目的としたモジュール群です。

- 株価データや財務データを用いたリサーチ／ファクター計算（research）
- ポートフォリオ構築・ポジションサイズ決定（portfolio）
- 発注（ExecutionEngine）と注文管理（execution）
- システム・取引の監視（monitoring）
- ニュース NLP によるセンチメント評価や市場レジーム判定（ai）
- 運用支援ツール（設定ウィザード・検証・レポート等）

設計方針の要点：
- 本番 DB とペーパートレード DB を分離（paper_trading モード）
- DuckDB を分析用 DB、SQLite を監視・履歴用 DB として使用
- 環境変数 / .env による設定管理（`kabusys.config`）
- フラグファイルによる停止（kill.flag / stop_requested.flag）や PID 管理

---

## 主な機能一覧

- Execution
  - ExecutionEngine（発注実行用エンジン、リスク管理・注文管理・reconciler 等を統合）
  - BrokerClientFactory により本番ブローカー／Mock ブローカーを切替（KABUSYS_ENV に依存）
- Monitoring
  - SystemMonitor: CPU/メモリ/ディスク、データ鮮度、Execution プロセスの監視
  - TradeMonitor / RiskMonitor: 注文滞留、異常約定、ドローダウン・ポジション上限監視
  - MonitoringEngine: 各 Monitor を束ねて定期実行、アラート・Kill Switch 評価
  - MonitoringDB: SQLite に監視ログ・trade_logs・risk_logs・dashboard を永続化
- Portfolio
  - 候補選定、等重・スコア重み、セクターキャップ、ポジションサイズ計算
- Research
  - ファクター計算（モメンタム・ボラティリティ・バリュー等）
  - 将来リターン計算、IC 計算、統計サマリ
- AI
  - news_nlp: OpenAI を使ったニュースセンチメント評価 → `ai_scores` に書き込み
  - regime_detector: ETF + マクロニュースで市場レジーム判定（`market_regime` 書込）
- ツール
  - 環境設定ウィザード: `kabusys.config_setup`（.env の対話作成）
  - 設定検証 CLI: `kabusys.validate_config`
  - Paper Trading 検証レポート: `kabusys.tools.paper_verification_report`

---

## 前提 / 必要なライブラリ

推奨環境：
- Python 3.10+
- 必要なパッケージの例:
  - duckdb
  - psutil
  - openai
  - PyYAML（設定 YAML 検証に使用、必須ではない）
- 仮想環境（venv / virtualenv）を推奨

インストール例（requirements.txt がある場合）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

手動インストール例（最小）:
```bash
pip install duckdb psutil openai PyYAML
```

---

## セットアップ手順

1. リポジトリをクローン／配置
2. 仮想環境を作成して依存をインストール（上記参照）
3. 環境変数設定（.env ファイル）
   - 推奨: 対話式ウィザードで .env を生成
     ```bash
     python -m kabusys.config_setup
     ```
   - 必須環境変数（少なくとも以下が必要）
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - よく使う設定例（.env）:
     ```
     KABUSYS_ENV=development
     JQUANTS_REFRESH_TOKEN=your_token_here
     KABU_API_PASSWORD=your_password_here
     DUCKDB_PATH=data/kabusys.duckdb
     SQLITE_PATH=data/monitoring.db
     LOG_LEVEL=INFO
     KILL_FLAG_CLEAR_ON_START=0
     ```
   - .env の自動読み込み:
     - プロジェクトルートに `.env` または `.env.local` がある場合、自動で読み込まれます（ただし環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると無効化可）。
4. 設定検証（任意）
   ```bash
   python -m kabusys.validate_config
   # 警告も FAIL 扱いにする場合:
   python -m kabusys.validate_config --strict
   ```
5. データディレクトリとログディレクトリの確認
   - デフォルト: `data/`（SQLite/flag/pid を置く）、`logs/`（ログ）
   - `LOG_DIR` 環境変数でログディレクトリを上書き可能

---

## 起動 / 使い方

以下は代表的な起動例です。いずれもパッケージを Python パスに含め、モジュールとして起動します（プロジェクトルートで実行することを想定）。

- ExecutionEngine（発注エンジン）起動
  - 注意: `KABUSYS_ENV=paper_trading` の場合、MockBrokerClient を用い、データは `data/paper_trading.db`（または環境変数 `PAPER_TRADING_SQLITE_PATH`）に分離されます。
  ```bash
  python -m kabusys.run_execution
  ```
  - 実行時の挙動:
    - プロセス優先度を "high" に設定（可能な限り）
    - SQLite / DuckDB に接続して Engine を初期化
    - `data/execution.pid` を使用（PID ファイル）
    - `data/stop_requested.flag` が存在する場合は起動しない
    - 停止は `stop_requested.flag` を作成するか、Engine の停止処理を呼ぶ

- Monitoring（監視ループ）起動
  ```bash
  python -m kabusys.run_monitoring
  ```
  - デフォルトは 60 秒間隔でポーリング（環境変数 `MONITOR_POLL_INTERVAL` で上書き可）
  - 監視は常に本番の `SQLITE_PATH` を使用（環境にかかわらず監視 DB は本番を参照）
  - `data/stop_requested.flag` を作成するとループが終了する

- 設定ウィザード
  ```bash
  python -m kabusys.config_setup
  ```

- 設定検証
  ```bash
  python -m kabusys.validate_config
  ```

- Paper Trading 検証レポート生成
  ```bash
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # デフォルト DB パスは data/paper_trading.db。別 DB を使う場合:
  python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db
  ```

- AI モジュール（ライブラリ関数として使用）
  - ニュース NLP（センチメント付与）:
    - 関数: `kabusys.ai.score_news(conn, target_date, api_key=None)`
    - DuckDB 接続（`duckdb.connect(...)`）と OpenAI API キーが必要
  - レジーム判定:
    - 関数: `kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)`

---

## 重要な環境変数（抜粋）

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV: development / paper_trading / live （デフォルト: development）
- DUCKDB_PATH（default: data/kabusys.duckdb）
- SQLITE_PATH（default: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、default: data/paper_trading.db）
- LOG_LEVEL（DEBUG/INFO/...）
- LOG_DIR（ログ保存先ディレクトリ）
- OPENAI_API_KEY（AI 機能使用時に必要）
- MONITOR_POLL_INTERVAL（監視ポーリング間隔秒、run_monitoring 用）
- PAPER_FILL_MODE（paper_trading の MockBroker の fill 動作: instant/partial/never/reject）
- KILL_FLAG_CLEAR_ON_START（起動時に kill.flag を自動クリアするか、0/1）

---

## 停止・Kill Switch の仕組み

- 停止フラグ（プロセス外からの停止指示）
  - `data/stop_requested.flag`：run_execution / run_monitoring がこれを検知して終了する
- Kill Switch（運用リスク検知による強制停止）
  - `KillSwitch` が `risk_monitor` の判定で条件を満たした場合、`data/kill.flag` を作成し、ExecutionEngine 側で検出して安全に停止させる
  - `KILL_FLAG_CLEAR_ON_START=1` を設定すると起動時に kill.flag を自動クリアしますが、本番では通常 `0` を推奨

---

## ディレクトリ構成（主要ファイル）

以下は主要なソース配置の抜粋（`src/kabusys/` 内）。ファイルはリポジトリの実際の配置に合わせてください。

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / .env 自動読み込み・Settings
  - config_setup.py          — .env 対話式ウィザード（CLI）
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — Monitoring 起動スクリプト
  - tools/
    - paper_verification_report.py
  - ai/
    - news_nlp.py
    - regime_detector.py
    - __init__.py
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
    - trade_monitor.py (存在: 実装ファイルは同階層にある想定)
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
  - utils/
    - logging_setup.py
    - process_priority.py
    - __init__.py
  - execution/
    - execution_engine.py (エンジン本体)
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
    - broker_factory.py
  - data/ (実行時に生成される想定)
    - monitoring.db (sqlite のデフォルト)
    - paper_trading.db (paper_trading 用 DB)
    - kill.flag / stop_requested.flag / execution.pid

（注）上記は主要モジュールのみ列挙。実際のリポジトリにはさらに補助モジュールやドキュメントが存在する場合があります。

---

## 運用・トラブルシュートのヒント

- DB マイグレーション
  - MonitoringDB は `init_monitoring_db()` で必要なテーブルを冪等に作成します。起動時に自動的に作成・最小マイグレーションを行います。
- ログがファイルに書き込まれない場合：
  - `LOG_DIR` のパーミッション確認、または `logging_setup.setup_logging` がディレクトリ作成に失敗している可能性あり。標準出力（stdout）は必ず出力されるよう設定されています。
- OpenAI API まわり
  - `OPENAI_API_KEY` が未設定だと AI 機能はエラーになります。API 呼び出しは再試行ロジックやフォールバック（失敗時はスキップや中立スコア）を持つ実装です。
- ペーパートレード時の DB 分離
  - `KABUSYS_ENV=paper_trading` を使うと発注は MockBroker に送り、履歴は `PAPER_TRADING_SQLITE_PATH` に記録されます。本番の SQLite を汚さないので検証が容易です。
- kill.flag の扱いに注意
  - 本番（KABUSYS_ENV=live）の場合は `KILL_FLAG_CLEAR_ON_START=0` を推奨。誤って自動クリアすると重要な停止フラグが消える恐れがあります。

---

## 参考コマンドまとめ

- 環境ウィザード（.env 生成）
  ```bash
  python -m kabusys.config_setup
  ```
- 設定検証
  ```bash
  python -m kabusys.validate_config
  ```
- Execution 起動
  ```bash
  python -m kabusys.run_execution
  ```
- Monitoring 起動
  ```bash
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  ```
- Paper Trading レポート
  ```bash
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```

---

必要に応じて README を補足します。運用上特に詳しく知りたい点（例: ExecutionEngine の構成、Broker API の実装や Mock の振る舞い、DB スキーマ詳細など）があれば教えてください。