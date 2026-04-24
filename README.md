# KabuSys

日本株自動売買システム（KabuSys）のコードベース README（日本語）

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株向けの自動売買 / 研究 / 監視ユーティリティ群を収めたパッケージです。  
主な目的は以下です：

- 戦略の研究（ファクター計算、特徴量解析）
- ポートフォリオ構築（候補選定・重み付け・株数決定）
- 実行エンジン（ExecutionEngine）による発注管理（本番 / ペーパートレード対応）
- 監視（System / Trade / Risk）と Kill Switch による安全停止
- AI を使ったニュースセンチメント評価（OpenAI）
- ペーパートレード検証レポート生成ツール

設計方針として、DB（DuckDB/SQLite）を使った分析、LLM 呼び出しのフェイルセーフ化、設定ウィザード／検証 CLI の提供などを行っています。

---

## 機能一覧

- 設定管理
  - .env 自動読み込み（プロジェクトルートの .env/.env.local）
  - 対話式設定ウィザード: `python -m kabusys.config_setup`
  - 設定検証 CLI: `python -m kabusys.validate_config`
- 実行/監視
  - ExecutionEngine 起動スクリプト: `python -m kabusys.run_execution`
    - KABUSYS_ENV=paper_trading の場合は MockBroker を使用し DB を分離
  - Monitoring 起動スクリプト: `python -m kabusys.run_monitoring`
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更可能（デフォルト 60 秒）
- 監視コンポーネント
  - SystemMonitor, TradeMonitor, RiskMonitor, MonitoringEngine
  - KillSwitch（閾値・ポジション上限で kill.flag を生成）
  - 監視ログ・状態は SQLite（data/monitoring.db 等）へ永続化
- ポートフォリオ関連（純粋関数）
  - 候補選定、等重／スコア加重、ポジションサイズ計算、セクター上限、レジーム乗数
- 研究（Research）
  - Momentum / Volatility / Value ファクター計算（DuckDB 経由の SQL）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー
- AI
  - ニュース NLP（OpenAI を用いたセンチメント）: kabusys.ai.score_news
  - 市場レジーム判定（ma200 + マクロセンチメント）: kabusys.ai.regime_detector.score_regime
- ツール
  - Paper Trading 検証レポート生成: `python -m kabusys.tools.paper_verification_report`

---

## 前提条件 / 必要パッケージ

主に以下が必要になります（OS により追加の依存が必要な場合あり）:

- Python 3.9+
- duckdb
- psutil
- openai（AI 機能を使う場合）
- PyYAML（config YAML の検証を行う場合に任意）

例（最低限のインストール）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai pyyaml
```

（プロジェクトに requirements.txt があればそれを使ってください）

---

## セットアップ手順

1. リポジトリをクローン
   ```bash
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境作成・依存インストール（上記参照）

3. 対話式で .env を作成
   ```bash
   python -m kabusys.config_setup
   ```
   - J-Quants トークンや kabuAPI パスワード等の必須項目を入力します。
   - 生成される .env は絶対に Git にコミットしないでください。

4. 設定の検証
   ```bash
   python -m kabusys.validate_config
   # 警告を FAIL 扱いにする場合:
   python -m kabusys.validate_config --strict
   ```

5. データディレクトリの確認
   - デフォルトの DB / ファイルパス:
     - DuckDB: data/kabusys.duckdb
     - SQLite (監視): data/monitoring.db
     - ペーパートレード用 SQLite: data/paper_trading.db
     - ログ: logs/<app>.log（自動作成）
   - 必要に応じて .env で上書きしてください（例: DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH）。

---

## 主要な環境変数

必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

主要（任意／デフォルトあり）:
- KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
  - paper_trading の場合、Execution は専用 SQLite を使用します
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: SQLite 監視 DB（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト data/paper_trading.db）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- OPENAI_API_KEY: OpenAI を使う場合に必要
- MONITOR_POLL_INTERVAL: Monitoring のポーリング間隔（秒。デフォルト 60）

Kill Switch / プロセス制御:
- KILL_FLAG_PATH: kill.flag のパス（デフォルト data/kill.flag）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアする（1 = 有効。production 非推奨）

---

## 使い方（実行例）

基本的な起動方法はモジュール実行です。

- ExecutionEngine を起動（デフォルトでは .env の KABUSYS_ENV に従う）
  ```bash
  python -m kabusys.run_execution
  ```
  - KABUSYS_ENV=paper_trading の場合は MockBroker を使い、paper_sqlite_path を使って発注ログ等を分離します。
  - 起動時に data/stop_requested.flag が既に存在する場合は起動せず終了します。
  - 実行中に data/stop_requested.flag を作成するとエンジンを停止します。
  - 実行中は execution.pid（デフォルト data/execution.pid）に PID が書き込まれます。

- Monitoring（監視ループ）を起動
  ```bash
  # 環境変数でポーリング間隔を変更
  export MONITOR_POLL_INTERVAL=30
  python -m kabusys.run_monitoring
  ```
  - デフォルト 60 秒で SystemMonitor / TradeMonitor / RiskMonitor を順次実行します。
  - data/stop_requested.flag が存在すると監視ループは終了します。

- 設定ウィザード（.env 作成）
  ```bash
  python -m kabusys.config_setup
  ```

- 設定検証
  ```bash
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- Paper Trading 検証レポート（SQLite ファイルを指定可能）
  ```bash
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # --db オプションでパスを指定、または環境変数 PAPER_TRADING_SQLITE_PATH で指定
  ```

- AI 機能（ライブラリ関数として使用）
  - ニュースセンチメント（プログラム内から呼ぶ）
    ```py
    from datetime import date
    import duckdb
    from kabusys.ai import score_news

    conn = duckdb.connect('data/kabusys.duckdb')
    n_written = score_news(conn, target_date=date(2026, 4, 10), api_key='你的OPENAI_KEY')
    ```
  - レジーム判定（score_regime）も同様に呼び出せます。API キーが必要。

---

## 停止・Kill スイッチの挙動

- stop flag（強制停止用）
  - ファイル: data/stop_requested.flag
  - 存在すると run_execution / run_monitoring は起動検出またはループ内で停止します（スクリプト内部でチェック。手動で作成/削除してください）。

- kill flag（自動停止トリガ）
  - ファイル: data/kill.flag
  - KillSwitch が条件（ドローダウン閾値超過・ポジション上限超過等）を満たすと書き込まれます。ExecutionEngine は起動時にこの flag を参照し停止します（または監視が発見して通知します）。
  - 本番での誤動作を避けるため、KILL_FLAG_CLEAR_ON_START はデフォルト 0 を推奨します。

---

## ロギング

- ログ設定は共通ユーティリティで行われます（kabusys.utils.logging_setup.setup_logging）。
- 出力先:
  - コンソール (stdout)
  - 日次ローテートされるファイル: logs/<app_name>.log（デフォルト）
- ログレベルは環境変数 LOG_LEVEL または引数で制御可能（デフォルト INFO）。

---

## ディレクトリ構成（主要ファイル）

以下はこのリポジトリの主要なファイル・パッケージ（抜粋）です:

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数 / Settings 管理、自動 .env ロード
  - config_setup.py           — 対話式 .env ウィザード
  - validate_config.py        — 設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — Monitoring 起動スクリプト
  - tools/
    - paper_verification_report.py
  - ai/
    - news_nlp.py
    - regime_detector.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - monitoring/
    - monitoring_db.py
    - monitoring_engine.py
    - system_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - (TradeMonitor 等は別ファイルとして存在)
  - utils/
    - logging_setup.py
    - process_priority.py
  - execution/                 — Execution 用のサブパッケージ（Engine, BrokerFactory 等）
  - data/ (実行時に生成される想定)
    - monitoring.db (SQLite)
    - paper_trading.db (SQLite)
    - kabusys.duckdb (DuckDB)
    - execution.pid, stop_requested.flag, kill.flag

（リポジトリ全体の tree を出力する場合はローカルで `tree src/kabusys` 等を実行してください）

---

## 開発メモ / 注意点

- DB マイグレーションは簡易的にコード内で行っています（例: monitoring_db.init_monitoring_db にてカラム追加チェック）。
- AI 機能は OpenAI API に依存します。API 呼び出しはリトライ・フォールバック処理が組まれていますが、API キー未設定時は ValueError を出します。
- ファイルパスは .env による上書きが可能です。開発時は KABUSYS_ENV=development を使用してください（本番は live を慎重に設定）。
- 本番（live）では KILL_FLAG_CLEAR_ON_START=0 を推奨します（誤って Kill Switch を消すことを防止）。

---

必要があれば、README の英訳、デプロイ手順（systemd / supervisor 用の unit サンプル）、あるいは各モジュール（ExecutionEngine / TradeMonitor 等）の詳細ドキュメントを追加で作成します。どの情報を優先的に追加しますか？