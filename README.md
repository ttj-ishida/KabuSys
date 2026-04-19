# KabuSys

日本株向け自動売買システムの一部（ライブラリ + 起動スクリプト群）。  
このリポジトリは取引エンジン、監視、ポートフォリオ構築、リサーチ、AI を使ったニュース評価などの機能を含みます。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株の自動売買システム向けユーティリティとランタイムコンポーネント群です。主な目的は以下：

- 発注・約定管理を行う ExecutionEngine（本番 / ペーパートレードを切り替え可能）
- システム稼働状況や取引の監視とアラート（Kill Switch含む）
- ポートフォリオ構築（銘柄選定・重み計算・ポジションサイズ決定）
- リサーチ用ファクター計算（DuckDB を用いたオンチェーン計算）
- ニュースを LLM（OpenAI）で評価してスコア化する機能
- ペーパートレード検証レポート生成ツール

設計上の特徴として、DB は DuckDB（分析）と SQLite（監視・発注ログ）を用途に分け、環境（development / paper_trading / live）により挙動を切り替えます。

---

## 主な機能一覧

- 設定管理
  - .env 自動ロード（プロジェクトルート検出）
  - 対話式設定ウィザード（`config_setup`）
  - 設定検証 CLI（`validate_config`）
- 実行 / 監視
  - ExecutionEngine 起動スクリプト（`run_execution.py`）
    - `KABUSYS_ENV=paper_trading` 時は MockBrokerClient を使用し、`data/paper_trading.db` に記録
  - SystemMonitor / MonitoringEngine（`run_monitoring.py`）
    - モニタリングループ、Kill Switch判定、アラート連携
- データ永続化
  - 監視用 SQLite スキーマと読み書きラッパー（`monitoring_db.py`）
- ポートフォリオ
  - 候補選定、等配分 / スコア加重、ポジションサイズ決定、セクター上限・レジーム乗数
- リサーチ
  - ファクター計算（Momentum, Volatility, Value 等）
  - 将来リターン計算・IC (Information Coefficient)・統計サマリ
- AI
  - ニュースを LLM でセンチメント評価（`ai.news_nlp`）
  - マクロニュース + ETF MA によるレジーム判定（`ai.regime_detector`）
- ツール
  - Paper Trading 検証レポート生成（`tools.paper_verification_report`）

---

## 必要条件（推奨）

- Python 3.10+（typing に `X | Y` 形式を使用）
- 必要ライブラリ（最低限）
  - duckdb
  - psutil
  - openai（AI 機能を使う場合）
- 任意 / 推奨
  - PyYAML（`validate_config` が config/*.yaml を検査する場合）
- OS: Linux / macOS / Windows（process priority / cpu affinity は OS に依存する挙動あり）

インストール例（venv 推奨）:

```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai
# optional
pip install pyyaml
```

（requirements.txt がある場合は `pip install -r requirements.txt` を使用してください）

---

## 環境変数（主要）

- JQUANTS_REFRESH_TOKEN — 必須（J-Quants API）
- KABU_API_PASSWORD — 必須（kabuステーション API）
- KABUSYS_ENV — 実行環境: `development` / `paper_trading` / `live`（デフォルト: development）
- OPENAI_API_KEY — OpenAI を利用する場合に必要
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: `data/kabusys.duckdb`）
- SQLITE_PATH — SQLite（監視 DB）パス（デフォルト: `data/monitoring.db`）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード用 SQLite（デフォルト: `data/paper_trading.db`）
- LOG_LEVEL — ログレベル（`INFO` 等）
- LOG_DIR — ログ出力ディレクトリ（デフォルト: `logs/`）
- MONITOR_POLL_INTERVAL — 監視ポーリング間隔（秒、デフォルト 60）
- PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START など（詳しくは Settings）

初期設定はリポジトリルートの `.env` に記述します。自動読み込みはプロジェクトルート（.git または pyproject.toml を基準）で行われます。

---

## セットアップ手順

1. リポジトリをクローンし、Python 仮想環境を作る

   ```bash
   git clone <repo-url>
   cd <repo-root>
   python -m venv .venv
   source .venv/bin/activate
   pip install duckdb psutil openai
   pip install pyyaml  # optional for YAML validation
   ```

2. .env の作成（対話式ウィザード推奨）

   ```bash
   python -m kabusys.config_setup
   ```

   - 対話ウィザードに従って `JQUANTS_REFRESH_TOKEN` や `KABU_API_PASSWORD` を設定します。
   - ペーパートレード用 DB を使用する場合は `KABUSYS_ENV=paper_trading` を選択。

3. 設定検証

   ```bash
   python -m kabusys.validate_config
   # 厳格モード（警告も失敗扱い）
   python -m kabusys.validate_config --strict
   ```

4. DB の初期化は起動スクリプトが自動で行います（monitoring DB のテーブル作成等）。

5. ログディレクトリ / data ディレクトリを作成（多くの起動スクリプトで自動作成しますが、権限に注意）:

   ```bash
   mkdir -p logs data
   ```

---

## 使い方（起動 / 実行例）

- ExecutionEngine を起動（デフォルト: settings に従う）:

  ```bash
  python -m kabusys.run_execution
  ```

  - `KABUSYS_ENV=paper_trading` の場合は MockBroker を使用し、`data/paper_trading.db` に記録して本番 DB と分離します。
  - 起動時に `data/stop_requested.flag` が存在すると起動せずに終了します。
  - 実行中に停止させるには `data/stop_requested.flag` を作るか、`KillSwitch`（`data/kill.flag`）が発動するとエンジンに停止を指示します。

- Monitoring を起動（ポーリングループ）:

  ```bash
  # ポーリング間隔を環境変数で上書きしたい場合
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  ```

  - 環境変数 `MONITOR_POLL_INTERVAL`（秒）でポーリング間隔を変更可能。デフォルト 60 秒。
  - Monitoring は常に本番用の sqlite_path を参照して監視ログを保存します（環境に関わらず）。

- 設定ウィザード（.env 作成）:

  ```bash
  python -m kabusys.config_setup
  ```

- 設定検証:

  ```bash
  python -m kabusys.validate_config
  ```

- Paper Trading 検証レポート生成:

  ```bash
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB を明示する場合
  python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
  ```

---

## ファイル / フラグ関連（運用メモ）

- 停止フラグ
  - data/stop_requested.flag — 起動スクリプトが監視する「外部から停止要求」フラグ
  - data/kill.flag — KillSwitch による ExecutionEngine 停止シグナル（存在すると Engine を止める）
  - KillSwitch はリスク（ドローダウンやポジション上限）に基づいて `data/kill.flag` を書き込む
  - `KILL_FLAG_CLEAR_ON_START=1` を設定すると起動時に kill.flag を自動クリアする（本番での自動クリアは危険）

- PID ファイル
  - data/execution.pid（デフォルト） — ExecutionEngine の PID を格納

- ログ
  - デフォルトは `logs/<app_name>.log`（`run_execution` → logs/execution.log, `run_monitoring` → logs/monitoring.log 等）
  - 日次ローテーション（30 日保持）
  - `LOG_LEVEL` / `LOG_DIR` で調整可能

---

## 主要モジュールの説明（抜粋）

- kabusys.config
  - 環境変数読み込み・検証ロジック、Settings クラスで各種設定値をプロパティとして提供
  - .env 自動読み込み（`.git` / `pyproject.toml` を起点にプロジェクトルートを検出）

- kabusys.run_execution
  - ExecutionEngine の起動スクリプト。paper_trading 環境では MockBroker を使用し DB を分離

- kabusys.run_monitoring
  - SystemMonitor をポーリングする起動スクリプト。MONITOR_POLL_INTERVAL により間隔指定可能

- kabusys.monitoring.*
  - monitoring_db: SQLite のテーブル作成 / 永続化ラッパー
  - system_monitor: CPU/メモリ/Disk/プロセス/データ鮮度のチェック
  - risk_monitor: ドローダウン / ポジション制限のチェックとダッシュボード更新
  - kill_switch: しきい値超過時に kill.flag を書き込み Execution を停止させる
  - monitoring_engine: 各 Monitor を統合して実行およびアラート発行

- kabusys.portfolio.*
  - portfolio_builder: 候補選定、等重/スコア重み計算
  - position_sizing: 発注株数・リスクベースの算出・単元丸め
  - risk_adjustment: セクターキャップ適用、レジーム乗数算出

- kabusys.research.*
  - factor_research: Momentum / Volatility / Value 等のファクター計算（DuckDB 接続を受ける）
  - feature_exploration: 将来リターン計算、IC、統計サマリ

- kabusys.ai.*
  - news_nlp: raw_news をまとめて OpenAI に投げ、銘柄ごとのセンチメントを ai_scores に書き込む
  - regime_detector: ETF の MA とマクロニュース LLM スコアを合成して市場レジームを判定

---

## ディレクトリ構成（主要ファイル）

（src/kabusys をルートにした想定）

- src/
  - kabusys/
    - __init__.py
    - config.py
    - config_setup.py
    - validate_config.py
    - run_execution.py
    - run_monitoring.py
    - utils/
      - __init__.py
      - logging_setup.py
      - process_priority.py
    - monitoring/
      - monitoring_db.py
      - system_monitor.py
      - risk_monitor.py
      - kill_switch.py
      - monitoring_engine.py
      - (alert_manager.py, trade_monitor.py 等が想定される)
    - execution/  (ExecutionEngine 関連モジュール群)
      - (broker_factory.py, execution_engine.py, order_manager.py, order_repository.py, reconciler.py, risk_manager.py など)
    - portfolio/
      - portfolio_builder.py
      - position_sizing.py
      - risk_adjustment.py
      - __init__.py
    - research/
      - factor_research.py
      - feature_exploration.py
      - __init__.py
    - ai/
      - news_nlp.py
      - regime_detector.py
      - __init__.py
    - monitoring/
      - (上記)
    - tools/
      - __init__.py
      - paper_verification_report.py
    - data/ (実行時に使用する SQLite / flag / pid 等)
    - logs/ (ログ出力先)

---

## 運用上の注意 / ベストプラクティス

- 本番環境（KABUSYS_ENV=live）では kill.flag 自動クリアや無防備な設定を避ける（`KILL_FLAG_CLEAR_ON_START=0` 推奨）。
- OpenAI を使う機能（news_nlp / regime_detector）は API リクエストを行うため、API キーの管理とコストに注意する。
- process priority 設定は OS に依存し、権限不足で失敗することがある（警告に留まる）。
- ペーパートレード用データベースは本番 DB と分離されるように設定する（`PAPER_TRADING_SQLITE_PATH`）。
- ログと DB のバックアップ／ローテーション戦略を運用に組み込む。

---

## よく使うコマンド一覧

- 対話式 .env 作成
  - python -m kabusys.config_setup
- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict
- Execution 起動
  - python -m kabusys.run_execution
- Monitoring 起動
  - python -m kabusys.run_monitoring
- Paper Trading レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

---

README はプロジェクトの概要と運用に必要な手順をまとめたものです。追加の詳細（ExecutionEngine の内部や Broker 実装、alert_manager の設定など）は、該当モジュールのドキュメントやソース内の docstring を参照してください。必要であれば本 README に「インストール手順の自動化（Docker / systemd ユニット）」や「デプロイ手順」などのセクションを追記できます。どの追加情報が必要か教えてください。