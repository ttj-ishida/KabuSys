# KabuSys

日本株自動売買システムのライブラリ / 起動スクリプト群です。本リポジトリは取引実行、監視、ポートフォリオ構築、リサーチ、AI（ニュースNLU）などのコンポーネントを含みます。

---

## プロジェクト概要

KabuSys は日本株向けの自動売買システムを構成するモジュール群です。主な責務は次の通りです。

- ExecutionEngine：発注・注文管理・リスク管理を行う実行エンジン（本番 / ペーパートレード対応）
- Monitoring：システムの稼働監視、取引ログ監視、リスク監視、Kill Switch（停止フラグ）管理
- Portfolio：候補選定、重み計算、ポジションサイズ計算、セクター/レジーム制約
- Research：ファクター計算、特徴量探索、将来リターン・IC 計算
- AI：ニュースのセンチメント評価（OpenAI を利用）や市場レジーム判定
- Utils：ロギング設定、プロセス優先度設定等のユーティリティ
- CLI ツール：.env ウィザード、設定検証、ペーパートレード検証レポート生成など

設計上、データ永続化には DuckDB（分析用）と SQLite（監視／注文履歴）を使用します。Paper Trading（`KABUSYS_ENV=paper_trading`）は本番DBと分離され、`data/paper_trading.db` を用います。

---

## 機能一覧（主な機能）

- 実行（Execution）
  - Broker クライアント抽象化（本番 / Mock）
  - OrderManager / Reconciler / RiskManager による発注・状態管理
  - ExecutionEngine によるセッション実行、PID 管理、stop フラグ連携
- 監視（Monitoring）
  - SystemMonitor：CPU/メモリ/ディスク/データ鮮度/プロセス監視
  - TradeMonitor：滞留注文・約定異常検出（ソース参照）
  - RiskMonitor：ドローダウン・ポジション上限の監視とダッシュボード更新
  - KillSwitch：条件で kill.flag を書き込む（ExecutionEngine に停止信号）
  - MonitoringEngine：各種モニタを束ねてポーリング、アラート送出
- ポートフォリオ構築（Portfolio）
  - 候補選定、等金額・スコア重み、リスクベースサイズ決定、セクター制限、レジーム乗数
- リサーチ（Research）
  - Momentum / Volatility / Value ファクター計算（DuckDB 利用）
  - 将来リターン計算、IC（Spearman）算出、ファクター統計
- AI（ニュース NLP / レジーム検出）
  - OpenAI を用いたニュースセンチメント評価（`ai_scores` テーブル更新）
  - マクロ記事 + ETF MA200 による市場レジーム判定
- ツール
  - .env 設定ウィザード（対話式）：`python -m kabusys.config_setup`
  - 設定検証 CLI：`python -m kabusys.validate_config`
  - ペーパートレード検証レポート：`python -m kabusys.tools.paper_verification_report`

---

## 要件

- Python 3.10+
- 推奨パッケージ（最低限）:
  - duckdb
  - psutil
  - openai (AI 機能を使う場合)
  - pyyaml（設定ファイル YAML の検証を行う場合）
- 任意（ロギング / ファイル出力）: 権限に注意してディレクトリ作成を行ってください。

（実際の requirements.txt がある場合はそちらを使用してください）

インストール例（仮）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai pyyaml
```

---

## セットアップ手順

1. リポジトリをクローン
   ```bash
   git clone <repo-url>
   cd <repo-root>
   ```

2. 仮想環境を作り依存をインストール（上記参照）

3. 初期環境変数ファイルの作成（対話式ウィザード）
   ```bash
   python -m kabusys.config_setup
   ```
   - これによりプロジェクトルートに `.env` が生成されます。
   - `.env` は Git にコミットしないでください（秘密情報が含まれるため）。

4. 設定検証
   ```bash
   python -m kabusys.validate_config
   ```
   - `--strict` を付けると警告もエラー扱い（exit code 1）になります。

5. 必要に応じて DuckDB / SQLite のパス、ログディレクトリ等を .env で調整。
   - デフォルト:
     - DUCKDB_PATH: data/kabusys.duckdb
     - SQLITE_PATH: data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
     - LOG_DIR: logs/
     - LOG_LEVEL: INFO

6. DB 初期化
   - 監視用 SQLite テーブルは監視起動時（または実行起動時）に自動作成されます（冪等）。
   - DuckDB のテーブルはデータインポート / 別スクリプトで準備してください。

---

## 主要な環境変数（要点）

- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABUSYS_ENV（`development` | `paper_trading` | `live`; デフォルト: `development`）
  - `paper_trading` の場合は MockBroker を使用し、paper 用 SQLite（PAPER_TRADING_SQLITE_PATH）が使用されます。
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE（`instant` | `partial` | `never` | `reject`、デフォルト `instant`）
- OPENAI_API_KEY（AI 機能を利用する場合必須）
- LOG_LEVEL（デフォルト: INFO）
- LOG_DIR（デフォルト: logs/）
- PID_FILE_PATH（デフォルト: data/execution.pid）
- KILL_FLAG_PATH（デフォルト: data/kill.flag）
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 — 自動 .env ロードを無効化

自動 .env 読込はプロジェクトルート（.git または pyproject.toml が見つかる場所）から `.env`、`.env.local` の順で行われます。既存の OS 環境変数は保護されます。

---

## 使い方（実行例）

- ExecutionEngine（起動）
  ```bash
  # 本番/開発: .env で KABUSYS_ENV を指定
  python -m kabusys.run_execution
  ```
  - `KABUSYS_ENV=paper_trading` の場合は MockBroker を使い、`data/paper_trading.db` に記録されます。
  - 起動時に `data/stop_requested.flag` が存在すると起動せず終了します。
  - 実行中に `data/stop_requested.flag` を作ると安全に停止します（スレッド停止処理あり）。
  - 実行時に PID ファイル（デフォルト `data/execution.pid`）が管理されます。

- Monitoring（起動）
  ```bash
  # ポーリングループを開始
  python -m kabusys.run_monitoring
  ```
  - デフォルトのポーリング間隔は 60 秒。環境変数 MONITOR_POLL_INTERVAL で上書き可能（正の整数のみ、無効値はデフォルトにフォールバック）。
  - 監視は常に本番 sqlite_path を使用（環境にかかわらず）。
  - `data/stop_requested.flag` を作成するとループを終了します。

- 設定検証
  ```bash
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- .env ウィザード
  ```bash
  python -m kabusys.config_setup
  ```

- ペーパートレード検証レポート
  ```bash
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```

- AI 機能（プログラム的呼び出し）
  - ニューススコア付け:
    - kabusys.ai.news_nlp.score_news(duckdb_conn, target_date, api_key=None)
  - レジーム判定:
    - kabusys.ai.regime_detector.score_regime(duckdb_conn, target_date, api_key=None)

注意: AI 機能を CLI から直接呼ぶエントリポイントは提供されていません（モジュール関数を呼び出す設計）。OpenAI API キーは引数または環境変数 `OPENAI_API_KEY` を指定してください。

---

## 停止 / Kill Switch / フラグファイル

- stop_requested.flag（data/stop_requested.flag）
  - run_execution.py / run_monitoring.py はこのファイルの有無を確認し、存在すれば安全に終了します（外部から停止したい場合に使用）。
- kill.flag（デフォルト: data/kill.flag。Settings.kill_flag_path で上書き可能）
  - KillSwitch により重大なリスク（例: ドローダウン閾値超過、ポジション上限超過）が検出されたときに書き込まれます。
  - ExecutionEngine は起動時に kill.flag の有無を確認し、存在する場合は起動を中止する（設定に応じて）。
  - `KILL_FLAG_CLEAR_ON_START=1` を設定すると起動時に kill.flag が自動クリアされます（本番では推奨しません）。

---

## ロギング

- 共通のロギング設定ユーティリティ: `kabusys.utils.logging_setup.setup_logging`
  - コンソール（stdout）出力 + 日次ローテートファイル出力（TimedRotatingFileHandler）を root ロガーに設定します。
  - デフォルトログディレクトリ: `logs/`（`LOG_DIR` 環境変数で変更可）
  - デフォルトログレベル: `INFO`（`LOG_LEVEL` 環境変数または引数で変更可）

---

## ディレクトリ構成（抜粋）

以下は主要ファイル / モジュールの一覧（`src/kabusys/` 以下）:

- kabusys/
  - __init__.py
  - config.py              — 環境設定読み込み・Settings クラス、自動 .env ロード
  - config_setup.py        — .env 対話式ウィザード
  - validate_config.py     — 設定検証 CLI
  - run_execution.py       — ExecutionEngine 起動スクリプト
  - run_monitoring.py      — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート生成
  - utils/
    - logging_setup.py     — ログ初期化ユーティリティ
    - process_priority.py  — プロセス優先度設定 / CPU affinity
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py          — ニュースを OpenAI でスコアリング
    - regime_detector.py   — 市場レジーム判定
  - monitoring/
    - monitoring_db.py     — SQLite 用永続化層（テーブル作成 / CRUD ヘルパー）
    - system_monitor.py
    - trade_monitor.py     — （ソース参照）
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
  - execution/              — Execution 関連（BrokerFactory, Engine, OrderManager 等）
  - data/                   — （データファイル群: sqlite/duckdb/logs など）

（実際のファイル一覧はリポジトリの内容を参照してください）

---

## 開発上の注意・設計上のポイント

- Paper Trading と Live はデータベースを分離しているため、ペーパートレード実行で本番データが汚れることはありません（ただし .env 設定は慎重に）。
- AI 機能（news_nlp / regime_detector）は OpenAI API を利用します。API 呼び出しはリトライやフォールバックを組み込んでおり、失敗時は安全側の既定値で継続します（例: macro_sentiment=0.0）。
- Monitoring は設定に基づく Kill Switch を提供し、重大なリスク発生時に手動の介入なしで Execution を停止する仕組みがあります。ただし本番運用時は Kill Switch の設定（しきい値・自動クリア設定）を十分に確認してください。
- .env の自動ロードはプロジェクトルートを基準に行われます（CWD に依存しない）。必要に応じて `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化できます。
- ロギングファイルの作成に失敗した場合はコンソール出力のみで動作します。

---

## トラブルシューティング

- 「環境変数がない / プレースホルダ値」：`python -m kabusys.validate_config` で確認。`.env` を `config_setup` で更新してください。
- OpenAI 連携エラー：環境変数 `OPENAI_API_KEY` が設定済みか確認。API レート制限等はログにリトライ記録が残ります。
- DB / ログディレクトリ作成失敗：実行ユーザーにディレクトリ作成権限があるか確認してください。
- ポーリング間隔を変更したい：`MONITOR_POLL_INTERVAL` 環境変数を正の整数（秒）で設定（無効値は 60 秒にフォールバック）。

---

## ライセンス / バージョン情報

- パッケージバージョンは `kabusys/__init__.py` 内の `__version__` を参照してください（例: "0.1.0"）。

---

README の改善点や追加で記載したい使用例（CI / デプロイスクリプト、cron での監視起動等）があれば教えてください。必要であればサンプル .env.example を作成します。