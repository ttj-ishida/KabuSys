# KabuSys

KabuSys は日本株の自動売買システムのコアライブラリ群です。ファクター計算・ポートフォリオ構築・ポジションサイズ算出・発注エンジン・監視機能・AI ベースのニュース解析などを含むモジュール構成になっており、ローカル開発からペーパートレード、本番運用まで想定しています。

バージョン: 0.1.0

---

## 主な特徴

- ファクター計算（Momentum / Value / Volatility 等） — duckdb を用いて高速に集計
- ポートフォリオ構築（候補選定・重み計算・ポジションサイズ決定）
- ExecutionEngine（発注管理、リスク管理、リコンシリエーション）
- Paper Trading モード（本番 DB と完全分離して検証可能）
- 監視モジュール（SystemMonitor / TradeMonitor / RiskMonitor、Kill Switch）
- AI モジュール（ニュース NLP によるセンチメントスコア、レジーム判定）
- ログ設定ユーティリティ（コンソール + 日次ローテートファイル）
- 各種 CLI ツール（.env ウィザード、設定検証、Paper Trading 検証レポート生成）

---

## 依存関係（例）

以下は本リポジトリの主要依存パッケージです。プロジェクトに `requirements.txt` がない場合は、最低限下記をインストールしてください。

- Python 3.9+
- duckdb
- psutil
- openai
- PyYAML（任意: config YAML の検証に使用）
- （標準ライブラリ: sqlite3, logging, threading, datetime 等）

インストール例:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai PyYAML
```

---

## セットアップ手順

1. リポジトリをクローン／展開する。

2. 仮想環境を作成して依存関係をインストール（上記参照）。

3. 環境変数の作成:
   - 対話式ウィザードで `.env` を作成するのが推奨です。
   - 実行例:
     ```bash
     python -m kabusys.config_setup
     ```
   - ウィザードは `JQUANTS_REFRESH_TOKEN` / `KABU_API_PASSWORD` など必須項目を対話式で設定します。

4. 設定検証:
   - 作成した `.env` と `config/*.yaml` を検証します。
     ```bash
     python -m kabusys.validate_config
     # 警告を FAIL 扱いにする場合:
     python -m kabusys.validate_config --strict
     ```

5. データディレクトリとログディレクトリの準備:
   - デフォルトでは `data/` に SQLite / pid / flag、`logs/` にログが書き出されます。自動で作成されますが、権限等を確認してください。

---

## 主要な環境変数（抜粋）

（`.env` は絶対に Git に含めないでください）

- JQUANTS_REFRESH_TOKEN — J-Quants API（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト http://localhost:18080/kabusapi）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト `data/kabusys.duckdb`）
- SQLITE_PATH — 監視用 SQLite（デフォルト `data/monitoring.db`）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード用 SQLite（`KABUSYS_ENV=paper_trading`時に使用）
- KABUSYS_ENV — 実行環境（`development` / `paper_trading` / `live`、デフォルト `development`）
- LOG_LEVEL — ログレベル（`INFO` 等）
- KILL_FLAG_CLEAR_ON_START — Execution 起動時に kill.flag を自動クリアするか（開発用）
- OPENAI_API_KEY — OpenAI API キー（ai/news_nlp, ai/regime_detector で使用）

また、一部のランタイムオプションは実行時環境変数で制御できます。例:
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、デフォルト 60）

---

## 使い方（主要コマンド）

これらはプロジェクトルートで実行します（`.env` を用意した上で）。

- 実行エンジン（ExecutionEngine）を起動:
  - 通常:
    ```bash
    python -m kabusys.run_execution
    ```
  - `KABUSYS_ENV=paper_trading` の場合、MockBrokerClient を用い `data/paper_trading.db` へ記録して本番 DB と分離します。

- 監視ループを起動:
  ```bash
  python -m kabusys.run_monitoring
  ```
  - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を変更可能（秒）。
  - 停止は `data/stop_requested.flag` を作成すると監視ループが検知して停止します。

- 環境設定ウィザード（.env 作成）:
  ```bash
  python -m kabusys.config_setup
  ```

- 設定検証:
  ```bash
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- Paper Trading 検証レポート作成:
  ```bash
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  - `--db` で SQLite パスを明示的に指定可能。未指定時は `PAPER_TRADING_SQLITE_PATH` 環境変数または `data/paper_trading.db`。

- AI / Research 機能（一例、ライブラリ呼び出し）:
  - ニュース NLP を用いてスコアを生成:
    ```python
    from datetime import date
    import duckdb
    from kabusys.ai.news_nlp import score_news

    conn = duckdb.connect("data/kabusys.duckdb")
    score_news(conn, target_date=date(2026, 4, 11), api_key="YOUR_OPENAI_KEY")
    ```
  - レジーム判定:
    ```python
    from kabusys.ai.regime_detector import score_regime
    score_regime(conn, target_date=date(2026, 4, 11), api_key="YOUR_OPENAI_KEY")
    ```

---

## 監視・停止の仕組み（重要）

- Kill Switch:
  - リスク監視（drawdown 超過、ポジション上限等）で `data/kill.flag` を作成すると ExecutionEngine に停止シグナルを送ります。
  - `KillSwitch` はフラグが既に存在する場合は再書き込みしない（冪等）。

- 停止フラグ:
  - `data/stop_requested.flag` を作成すると `run_monitoring` / `run_execution` のループが検知して安全に終了します。

- Execution 起動時:
  - `KILL_FLAG_CLEAR_ON_START=1` を設定すると起動時に `kill.flag` を自動クリアしますが、本番では危険（推奨は `0`）。

---

## ロギング

- 共通ユーティリティ `kabusys.utils.logging_setup.setup_logging` を全起動スクリプトが利用します。
- 出力先:
  - コンソール（stdout）
  - 日次ローテーションファイル: `<LOG_DIR or logs>/<app_name>.log`（デフォルト `logs/`）
- ログレベルは `.env` の `LOG_LEVEL` または `setup_logging(level=...)` で制御可能。

---

## ディレクトリ構成（主要ファイル）

以下はソースツリーの主要部分（`src/kabusys`）の簡易ツリーです。

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / Settings
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor 起動スクリプト
  - tools/
    - paper_verification_report.py
  - utils/
    - logging_setup.py
    - process_priority.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - (その他: trade_monitor.py, alert_manager.py など)
  - ai/
    - news_nlp.py
    - regime_detector.py
    - __init__.py
  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py
  - execution/
    - (ExecutionEngine のコンポーネント群: broker_factory, execution_engine, order_manager, order_repository, risk_manager, reconciler, ...)
  - data/                    — 実行時に使う SQLite / pid / flag 等（プロジェクトルートの data/ を利用）
  - config/                  — yaml 設定テンプレート（system_config.yaml 等）

---

## 開発上の注意点

- Paper Trading と Live は DB を分離して扱う設計です。`KABUSYS_ENV=paper_trading` を使うことで本番データに影響を与えずに検証できます。
- .env を直接編集した場合は `python -m kabusys.validate_config` で検証することを推奨します。
- OpenAI を利用する機能（news_nlp, regime_detector）は API 失敗時にフェイルセーフ動作（0.0 やスキップ）を行うよう設計されていますが、APIキーとレート制限に注意してください。
- Logging / File I/O 関連は権限やディレクトリ存在に依存します。ログディレクトリや data ディレクトリに書き込み権限があるか事前に確認してください。
- psutil を使ったプロセス優先度設定はプラットフォーム依存です。権限不足で設定に失敗すると警告が出ますが、処理は継続します。

---

## よく使うコマンドまとめ

- ウィザードで .env 作成:
  ```bash
  python -m kabusys.config_setup
  ```
- 設定検証:
  ```bash
  python -m kabusys.validate_config
  ```
- 実行エンジン起動:
  ```bash
  python -m kabusys.run_execution
  ```
- 監視プロセス起動:
  ```bash
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  ```
- Paper Trading レポート:
  ```bash
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```

---

以上がプロジェクトの概要と基本的な使い方です。追加で README に含めたい具体的な実行例や設定サンプル（.env.example の内容など）があれば教えてください。必要に応じて追記します。