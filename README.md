# KabuSys

日本株向けの自動売買・リサーチ基盤コンポーネント群。  
本リポジトリは、発注エンジン（ExecutionEngine）・監視（Monitoring）・ポートフォリオ構築・ファクター計算・AI（ニュース NLP / レジーム判定）などのモジュールを含むライブラリ／実行スクリプト群です。

バージョン: 0.1.0

---

## 概要

KabuSys は以下を目的としたモジュール群を提供します。

- 日次・リアルタイムの発注実行（本番 / ペーパートレード）
- システム・注文・リスクの監視とアラート、Kill Switch（停止フラグ）
- ポートフォリオ構築（候補選定・重み付け・株数算出）
- DuckDB を用いたリサーチ（ファクター計算、特徴量解析）
- OpenAI を用いたニュースセンチメントスコアリングと市場レジーム判定
- ペーパートレード結果の検証レポート作成ツール

設計方針の例:
- 本番 DB とペーパートレード DB を分離
- ルックアヘッドバイアス防止（date.today()/datetime.today() を直接参照しない実装方針）
- フェイルセーフ（API 失敗時は安全側で継続）

---

## 主な機能一覧

- Execution
  - ExecutionEngine 起動スクリプト: `run_execution.py`
  - ブローカークライアント切替（本番 / Mock ペーパートレード）
  - リスク管理（ポジション上限・ドローダウン等）
- Monitoring
  - SystemMonitor / TradeMonitor / RiskMonitor を束ねる `MonitoringEngine`
  - SQLite に監視ログを永続化（`monitoring_db.py`）
  - KillSwitch（条件に応じて `data/kill.flag` を書き込み、Execution を停止）
  - `run_monitoring.py` によるポーリングループ起動（ポーリング間隔は環境変数で変更可能）
- Portfolio
  - 候補選定、等重・スコア重み、リスク調整（セクター上限、レジーム乗数）、ポジションサイズ算出
- Research
  - DuckDB を用いたファクター計算（モメンタム、バリュー、ボラティリティ）
  - 特徴量探索、IC 計算、前方リターン
- AI
  - ニュース NLP（OpenAI）による銘柄ごとのセンチメントスコア生成（`news_nlp.py`）
  - マクロニュースと ETF MA を合成した市場レジーム判定（`regime_detector.py`）
- ツール
  - ペーパートレード検証レポート生成 (`tools/paper_verification_report.py`)
  - 対話式 `.env` 生成ウィザード (`config_setup.py`)
  - 設定検証 CLI (`validate_config.py`)

---

## 要件（主要ライブラリ）

（プロジェクトに合わせて pip 等でインストールしてください）

- Python 3.9+
- duckdb
- psutil
- openai
- PyYAML（設定 YAML の検証に任意で使用）
- （実行環境により）sqlite3 は標準モジュール

例:
```
pip install duckdb psutil openai pyyaml
```

---

## セットアップ手順

1. リポジトリをクローン / 取得

2. 仮想環境を作成して依存をインストール
   ```
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt   # (ある場合)
   pip install duckdb psutil openai pyyaml
   ```

3. 環境変数（.env）の作成
   - 対話式ウィザードで初期 `.env` を作成できます:
     ```
     python -m kabusys.config_setup
     ```
   - あるいはルートに `.env` を置く（`.env.example` を参考に）。重要な環境変数:
     - JQUANTS_REFRESH_TOKEN (必須)
     - KABU_API_PASSWORD (必須)
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
     - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
     - SQLITE_PATH (デフォルト: data/monitoring.db)
     - PAPER_TRADING_SQLITE_PATH (ペーパートレード時の DB、デフォルト: data/paper_trading.db)
     - OPENAI_API_KEY (AI 機能を使う場合)
     - LOG_LEVEL (INFO 等)

   - サンプル（.env の一部）:
     ```
     JQUANTS_REFRESH_TOKEN=your_refresh_token_here
     KABU_API_PASSWORD=your_kabu_pwd_here
     KABUSYS_ENV=development
     DUCKDB_PATH=data/kabusys.duckdb
     SQLITE_PATH=data/monitoring.db
     PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
     LOG_LEVEL=INFO
     OPENAI_API_KEY=sk-...
     ```

4. 設定検証
   ```
   python -m kabusys.validate_config
   python -m kabusys.validate_config --strict   # 警告も失敗扱い
   ```

---

## 使い方（起動・主要コマンド）

- ExecutionEngine を起動（デフォルト環境に従う）
  ```
  python -m kabusys.run_execution
  ```
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し、ペーパートレード用 DB (PAPER_TRADING_SQLITE_PATH) に記録します。
  - 実行前に `data/kill.flag`（Kill Switch）や `data/stop_requested.flag` があると起動/実行に影響するため注意してください。
  - ExecutionEngine は `data/execution.pid` を PID file として扱います。

- Monitoring を起動（ポーリングループ）
  ```
  python -m kabusys.run_monitoring
  ```
  - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL` で上書き可能（秒単位、デフォルト 60）。
    例: `export MONITOR_POLL_INTERVAL=30`
  - Monitoring は環境にかかわらず本番 sqlite_path（Settings.sqlite_path）を使用して監視ログを書き込みます。

- ペーパートレード検証レポート（CLI）
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  - DB パスは `--db` または環境変数 `PAPER_TRADING_SQLITE_PATH` で指定可能。

- AI モジュールの呼び出し（プログラム内利用）
  - ニューススコアリング:
    ```
    from kabusys.ai.news_nlp import score_news
    # conn: duckdb connection (duckdb.connect(...))
    # target_date: datetime.date
    score_news(conn, target_date, api_key="sk-...")
    ```
  - レジーム判定:
    ```
    from kabusys.ai.regime_detector import score_regime
    score_regime(conn, target_date, api_key="sk-...")
    ```

- 設定ウィザード（.env 作成 / 更新）
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  ```

---

## 実運用に関する注意点

- KABUSYS_ENV のモード
  - development: ローカル開発・テスト（発注なし）
  - paper_trading: MockBroker を使ったペーパートレード（本番 DB と分離）
  - live: 実際に発注する本番モード（注意して使用）
- Kill Switch
  - `KillSwitch` は条件に応じて `data/kill.flag` を書き込みます。ExecutionEngine はこのファイルの存在を検出して停止します。
  - `KillSwitch.clear()` は `KILL_FLAG_CLEAR_ON_START=1` の場合に自動クリアを行う設定がありますが、本番環境では 0 を推奨します。
- 停止フラグ
  - `data/stop_requested.flag` は起動スクリプト（monitoring/execution いずれも）で監視され、存在するとループを終了します。
- ログ
  - デフォルトのログ出力先は `logs/`、ファイルは日次ローテーションで保持（30 日分）。
  - `LOG_DIR` 環境変数で上書き可。ログレベルは `LOG_LEVEL`（デフォルト: INFO）。
- DB
  - DuckDB: 分析・リサーチ用（デフォルト `data/kabusys.duckdb`）
  - SQLite: 監視ログ等（デフォルト `data/monitoring.db`）
  - ペーパートレード用 SQLite は分離（`PAPER_TRADING_SQLITE_PATH`）。

---

## 簡単なトラブルシュート

- `.env` が読み込まれない／環境変数が未設定
  - `KABUSYS_DISABLE_AUTO_ENV_LOAD` が設定されていないか確認
  - プロジェクトルートの検出は `.git` または `pyproject.toml` を基準に行われる
  - `python -m kabusys.config_setup` で対話的に作成するのが確実
- OpenAI API 関連
  - `OPENAI_API_KEY` を設定するか、関数呼び出し時に `api_key` を渡してください
  - API エラーはリトライロジックで安全にハンドリングされ、失敗時はフォールバック（例: macro_sentiment=0.0）します
- ログファイルが作成されない
  - `LOG_DIR` のディレクトリ作成に失敗していないか確認（`setup_logging` は失敗時にコンソール出力のみで継続）
- DuckDB / SQLite のスキーマエラー
  - `monitoring_db.init_monitoring_db` は冪等でテーブル作成および簡単なマイグレーション（列追加）を行います。起動時に自動で呼ばれます。

---

## ディレクトリ構成（主要ファイル）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / Settings
  - config_setup.py          — .env 対話ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor 起動スクリプト
  - tools/
    - paper_verification_report.py
  - ai/
    - news_nlp.py
    - regime_detector.py
    - __init__.py
  - monitoring/
    - monitoring_db.py
    - monitoring_engine.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - alert_manager.py
    - kill_switch.py
  - execution/                — (ExecutionEngine, order_manager, broker_factory, risk_manager, reconciler 等)
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py
  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py
  - utils/
    - logging_setup.py
    - process_priority.py
    - __init__.py
  - data/                     — 実行時に使用する DB / フラグファイル を格納（デフォルト）
    - monitoring.db
    - paper_trading.db
    - stop_requested.flag
    - kill.flag
    - execution.pid
  - logs/                     — デフォルトのログ出力先（起動時に作成されます）

（上記は主なファイルを抜粋しています。実際のリポジトリ全体を参照してください。）

---

必要であれば、README にサンプル .env のフルテンプレートや、各モジュールの API 使用例（関数シグネチャ、戻り値）を追記します。どの部分を詳しく追加しますか？