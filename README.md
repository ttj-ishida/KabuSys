# KabuSys

日本株自動売買システムの小規模フレームワーク（ライブラリ + 起動スクリプト群）。  
このリポジトリは、取引エンジン（ExecutionEngine）、監視（Monitoring）、ポートフォリオ構築、リサーチ、AI を使ったニューススコアリングなどの主要コンポーネントを含みます。

バージョン: 0.1.0

---

## 概要

KabuSys は次のような役割を持つモジュール群を提供します。

- Execution: 発注ロジック（本番 / ペーパートレード切り替え）
- Monitoring: システム・注文・リスク監視と Kill Switch（フラグファイルによる停止）
- Portfolio: 候補選定、重み計算、ポジションサイズ決定、リスク調整
- Research: ファクター計算・特徴量探索（DuckDB を用いた分析）
- AI: OpenAI を用いたニュース NLP（銘柄ごとのセンチメント算出）／レジーム判定
- Utils: ロギング設定、プロセス優先度設定など
- Tools: ペーパートレード検証レポート等の CLI ユーティリティ

設計方針の一部：
- DuckDB / SQLite をデータ層として使用（分析用に DuckDB、監視/履歴に SQLite）
- 本番 DB とペーパートレード DB を分離
- 可能な限り副作用を抑え、純粋関数スタイルのモジュールを用意
- .env を用いた環境設定、自動読み込み（必要に応じて無効化可能）

---

## 主な機能一覧

- ExecutionEngine の起動スクリプト（run_execution.py）
  - KABUSYS_ENV による本番 / paper_trading 切替
  - Paper Trading 時は MockBrokerClient を使用し専用 DB に記録
- Monitoring（run_monitoring.py）
  - SystemMonitor / TradeMonitor / RiskMonitor をポーリング
  - Kill Switch（data/kill.flag）を評価して ExecutionEngine を停止可能
  - ポーリング間隔の環境変数上書き（MONITOR_POLL_INTERVAL）
- 設定ウィザード（config_setup.py）
  - 対話式で .env を生成・更新
- 設定検証 CLI（validate_config.py）
  - 必須 env のチェック、config/*.yaml のパースチェック（PyYAML があれば）
- Paper Trading 検証レポート（tools/paper_verification_report.py）
  - 稼働率、注文成功率、レイテンシなどの集計と基準判定
- AI モジュール
  - news_nlp: OpenAI を用いた銘柄別ニュースセンチメント算出（ai_scores へ書き込み）
  - regime_detector: ETF とマクロニュースを組み合わせた市場レジーム判定
- Portfolio モジュール
  - 候補選定・重み計算・ポジションサイズ算出・セクター制限・レジーム乗数
- ユーティリティ
  - ログ設定（stdout + 日次ローテートログ）
  - プロセス優先度 / CPU affinity 設定

---

## 必要環境・依存パッケージ

- Python 3.10+
- 必須（機能により必要）:
  - duckdb
  - psutil
  - openai (AI 機能を使う場合)
- 推奨／任意:
  - PyYAML（config/*.yaml の検証を行う場合）
- 標準ライブラリ:
  - sqlite3, logging, threading, datetime, pathlib など

サンプルインストールコマンド（venv 推奨）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install duckdb psutil openai
# 任意で
pip install PyYAML
```

（requirements.txt がない場合は上記を参照してインストールしてください）

---

## セットアップ手順

1. リポジトリをクローン
   ```bash
   git clone <repo-url>
   cd <repo-root>
   ```

2. Python 仮想環境を作成して依存をインストール（上記参照）

3. .env の作成
   - 対話式ウィザードを使う（推奨）
     ```bash
     python -m kabusys.config_setup
     ```
   - 手動で .env を作成する場合は `.env.example` を参考に必要な環境変数を設定してください。

4. 設定検証
   ```bash
   python -m kabusys.validate_config
   # 警告も FAIL としたい場合:
   python -m kabusys.validate_config --strict
   ```

5. データ / ログ ディレクトリの確認
   - デフォルトのログディレクトリ: `logs/`
   - デフォルトの DB / PID / flag: `data/`
   - 必要に応じて .env の `DUCKDB_PATH` / `SQLITE_PATH` / `PAPER_TRADING_SQLITE_PATH` / `PID_FILE_PATH` / `KILL_FLAG_PATH` を上書き

---

## 主要な環境変数（抜粋）

必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

よく使う／挙動に影響するもの:
- KABUSYS_ENV: development | paper_trading | live
- DUCKDB_PATH: DuckDB ファイル（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL: ログレベル
- OPENAI_API_KEY: OpenAI API を使う場合
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒。デフォルト 60）
- KILL_FLAG_CLEAR_ON_START: 本番環境で起動時に kill.flag を自動クリアするか（"0" or "1"）

自動 .env 読み込み:
- 起動時にプロジェクトルート（.git または pyproject.toml）から `.env` と `.env.local` を自動読み込みします。自動読み込みを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## 使い方（コマンド例）

- ExecutionEngine を起動（バックグラウンドでの実行や supervisord/systemd 等を推奨）
  ```bash
  # 通常起動（KABUSYS_ENV に基づき paper/live/dev が切替）
  python -m kabusys.run_execution
  ```

  - ペーパートレードで起動したい場合:
    ```bash
    export KABUSYS_ENV=paper_trading
    python -m kabusys.run_execution
    ```
    ペーパートレード時は `PAPER_TRADING_SQLITE_PATH`（デフォルト: data/paper_trading.db）に記録され、本番 DB とは分離されます。

- Monitoring を起動（ポーリング監視）
  ```bash
  # ポーリング間隔を環境変数で上書き（秒）
  export MONITOR_POLL_INTERVAL=30
  python -m kabusys.run_monitoring
  ```

  - 監視プロセスは ExecutionEngine 停止の検知・Kill Switch の評価・アラート通知などを行います。Monitoring は常に本番 `SQLITE_PATH`（監視 DB）を使用します（環境にかかわらず）。

- .env ウィザード（対話式）
  ```bash
  python -m kabusys.config_setup
  ```

- 設定検証
  ```bash
  python -m kabusys.validate_config
  ```

- ペーパートレード検証レポート出力
  ```bash
  # デフォルト DB を使用
  python -m kabusys.tools.paper_verification_report

  # 期間と DB を指定
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11 --db data/paper_trading.db
  ```

---

## Kill / Stop フラグ

- ExecutionEngine と Monitoring スクリプトはいくつかのフラグファイルを参照します:
  - data/stop_requested.flag: run_execution/run_monitoring の停止（これがあると起動しない / ループ終了）
  - data/kill.flag: Kill Switch による ExecutionEngine 停止シグナル（Monitoring が判定して書き込む）
  - data/execution.pid: ExecutionEngine の PID 保存先（既定値・設定可能）

- Kill Switch は RiskMonitor の判定（ドローダウン超過・ポジション上限超過）を受け、`data/kill.flag` を書き込みます。ExecutionEngine 側はこのフラグを検知して整然と停止します。

- 起動時に `KILL_FLAG_CLEAR_ON_START=1` を設定すると起動時に kill.flag を自動で削除しますが、本番環境では推奨されません。

---

## ライブラリ API の使い方（簡易）

- Portfolio:
  ```python
  from kabusys.portfolio import select_candidates, calc_equal_weights, calc_position_sizes

  candidates = select_candidates(buy_signals, max_positions=10)
  weights = calc_equal_weights(candidates)
  shares = calc_position_sizes(weights, candidates, portfolio_value=10000000, available_cash=2000000, ...)
  ```

- Research（DuckDB 接続を渡す）:
  ```python
  import duckdb
  from kabusys.research import calc_momentum

  conn = duckdb.connect("data/kabusys.duckdb")
  results = calc_momentum(conn, target_date=date(2026, 4, 10))
  ```

- AI（ニューススコア付与）:
  ```python
  from kabusys.ai.news_nlp import score_news
  import duckdb

  conn = duckdb.connect("data/kabusys.duckdb")
  score_news(conn, target_date=date(2026,4,10), api_key="sk-...")
  ```

---

## ロギング

- ログはデフォルトで `logs/` 配下にアプリ名ごとのファイル（例: logs/execution.log, logs/monitoring.log）へ日次ローテーションで出力されます。標準出力にも同様のログが流れます。ログディレクトリは環境変数 `LOG_DIR` または `setup_logging` の引数で変更可能です。
- ログレベルは `LOG_LEVEL` 環境変数で制御します（デフォルト: INFO）。

---

## ディレクトリ構成

主要なファイル／ディレクトリ（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数読み込みと Settings
  - config_setup.py           — .env ウィザード（対話式）
  - validate_config.py        — 設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — Monitoring 起動スクリプト
  - tools/
    - paper_verification_report.py
  - execution/                — Execution 関連（Engine, BrokerFactory, OrderManager など）
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - monitoring_engine.py
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
  - utils/
    - logging_setup.py
    - process_priority.py
  - data/ (実行時に使用されるディレクトリ)
    - monitoring.db (デフォルト)
    - paper_trading.db (ペーパートレード時)
    - kill.flag, stop_requested.flag, execution.pid など

（プロジェクトルートに README / pyproject.toml / .git など）

---

## 注意事項 / 運用メモ

- 本番稼働時は必ず KABUSYS_ENV=live を確認し、LINE 通知等の設定（LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID）を整備してください。
- kill.flag の自動クリアは本番で危険です（KILL_FLAG_CLEAR_ON_START は通常 0 推奨）。
- OpenAI を利用する機能は API コストが発生します。API キー管理とレート制限に注意してください。
- DuckDB / SQLite のファイルはバックアップ・スナップショット運用を検討してください。
- ログディレクトリや data ディレクトリのパーミッションに注意してください（サービスユーザが書き込めること）。

---

必要であれば、README に追加すべき具体的な運用手順（systemd ユニットの例、Dockerfile、CI/CD 設定など）を追記します。どの情報を優先して追加しますか？