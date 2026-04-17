# KabuSys

日本株自動売買システムのコアライブラリ群（戦略構築、発注実行、監視、リサーチ、AI 補助等）。  
この README はリポジトリ内の主要スクリプト／モジュールの使い方とセットアップ手順をまとめたものです。

---

## プロジェクト概要

KabuSys は以下の責務を持つモジュール群で構成された自動売買プラットフォームです。

- 発注エンジン（ExecutionEngine）: ブローカー API 経由で注文を作成・管理、リスク管理、再起動時のリコンシリエーション
- 監視（MonitoringEngine）: システム健常性・注文滞留・リスク指標を定期ポーリングしてログ/アラートを生成
- ポートフォリオ構築（portfolio）: 候補選定、重み計算、ポジションサイズ算出、セクター制限等
- リサーチ（research）: ファクター計算、将来リターン・IC 計算、特徴量探索
- AI 補助（ai）: ニュースの NLP スコアリング（OpenAI）や市場レジーム判定
- ツール（tools）: Paper Trading の検証レポート生成など
- DB 層: SQLite（monitoring）と DuckDB（時系列データ・ファクター計算）を併用

ライブラリは本番/ペーパートレードを明確に分離する設計がなされています（`KABUSYS_ENV` 設定）。

---

## 主な機能一覧

- ExecutionEngine 起動スクリプト（`run_execution.py`）
  - 実口座 / ペーパートレード切替（`KABUSYS_ENV` が `paper_trading` の場合は MockBroker）
  - 起動時の自動リコンシリエーション（`Reconciler`）
  - RiskManager によるリスク制御（ドローダウン、ポジション上限、レート制限等）
- MonitoringEngine（`run_monitoring.py` + 各 Monitor）
  - SystemMonitor: CPU/Mem/Disk、データ鮮度、実行プロセス監視
  - TradeMonitor: 滞留注文・約定異常価格検出
  - RiskMonitor: ドローダウン / ポジション上限監視
  - KillSwitch / AlertManager: 条件に従って停止フラグ書き込み・LINE 通知
  - Streamlit ダッシュボードで監視情報の可視化
- Portfolio モジュール
  - 候補選定、等配分・スコア加重、リスク調整、ポジションサイズ計算
- Research モジュール
  - Momentum / Volatility / Value 等のファクター計算、IC や統計サマリ
- AI モジュール
  - ニュースを LLM（OpenAI）でセンチメント評価し `ai_scores` に保存
  - 市場レジーム判定（ETF MA + マクロセンチメントの合成）
- Tools
  - Paper Trading 検証レポート生成スクリプト（`kabusys.tools.paper_verification_report`）

---

## 必要条件（依存ライブラリ）

- Python 3.9+
- 必須パッケージ（例）
  - duckdb
  - psutil
  - requests
  - openai
  - streamlit (ダッシュボード利用時)
- SQLite（標準で同梱）

（インストールは下記参照）

---

## セットアップ手順（ローカル開発向け）

1. リポジトリをクローンして作業ディレクトリに移動
   ```
   git clone <repo_url>
   cd <repo>
   ```

2. 仮想環境を作成して有効化
   (例: venv)
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

3. 依存パッケージをインストール
   必要なパッケージを requirements.txt にまとめている場合はそれを使ってください。
   例（個別インストールの最低セット）:
   ```
   pip install duckdb psutil requests openai streamlit
   ```

4. data ディレクトリ作成（PID / DB / フラグ等を置く）
   ```
   mkdir -p data
   ```

5. 環境変数の設定
   - 本番的に動かす場合は最低限必要な環境変数:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
     - OPENAI_API_KEY（AI 機能を使う場合）
   - .env ファイルをプロジェクトルートに置くと自動で読み込まれます（.env.local は上書き可能）。
   - 自動読み込みを無効にするには:
     ```
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```
   - 主要な環境変数（代表例）
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
     - SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
     - DUCKDB_PATH: DuckDB パス（デフォルト: data/kabusys.duckdb）
     - PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 SQLite（デフォルト: data/paper_trading.db）
     - PAPER_FILL_MODE: instant | partial | never | reject（ペーパートレードの約定モード）
     - MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、デフォルト 60）
     - PID_FILE_PATH / KILL_FLAG_PATH など

6. 初回の DB 初期化は各スクリプト実行時に自動で行われます（`init_monitoring_db` は冪等）。

---

## 使い方

以下は主要な起動／ユーティリティの実行例です。プロジェクトルートから実行してください。

- ExecutionEngine を起動（本番 / ペーパーは KABUSYS_ENV に依存）
  ```
  # 本番（デフォルト: development -> is_paper False）
  python -m kabusys.run_execution

  # Paper trading モードで起動
  export KABUSYS_ENV=paper_trading
  python -m kabusys.run_execution
  ```
  - ペーパートレードでは専用 DB（`PAPER_TRADING_SQLITE_PATH`）に記録され、本番 DB と分離されます。
  - 実行中は `data/execution.pid`（デフォルト）や stop フラグファイルを利用してプロセス制御します。

- Monitoring を起動（ポーリングループ）
  ```
  # ポーリング間隔を変更する例（秒）
  export MONITOR_POLL_INTERVAL=30
  python -m kabusys.run_monitoring
  ```
  - 監視はデフォルトで本番 sqlite_path を使います（KABUSYS_ENV にかかわらず）。
  - 停止はプロセスに SIGINT（Ctrl-C）を送るか data/stop_requested.flag を作成して行います。

- Streamlit ダッシュボード（監視 UI）
  ```
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  ```
  - read-only モードで SQLite を開きます。MonitoringEngine が動作中で DB にデータがあることが前提です。

- Paper Trading 検証レポート
  ```
  # デフォルト DB: data/paper_trading.db
  python -m kabusys.tools.paper_verification_report

  # 期間指定・DB 指定
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11 --db data/paper_trading.db
  ```

- AI 機能（プログラムから利用）
  - ニュース NLP スコア付け:
    - 関数: `kabusys.ai.score_news(conn, target_date, api_key=None)`
  - 市場レジーム判定:
    - 関数: `kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)`
  - どちらも `OPENAI_API_KEY` を設定するか、呼び出し時に `api_key` を渡してください。

---

## 停止・フラグ運用

- 実行プロセス停止（外部から）
  - `data/stop_requested.flag` を作成すると run_execution / run_monitoring のループが検知して安全に停止します。
- Kill Switch（自動停止）
  - リスク条件に該当すると `KillSwitch` が `data/kill.flag` を書き込む設計です。ExecutionEngine は起動時にこのフラグを検知すると起動を中止します。
  - `KillSwitch.clear()` を使うか手動で `data/kill.flag` を削除してから再起動してください。
- PID ファイル
  - 実行中は `data/execution.pid`（デフォルト）に PID が書かれます。SystemMonitor は stale PID を検出して削除します。

---

## 設定（Settings クラスの概要）

`kabusys.config.Settings` で環境変数から設定を一元管理します。重要なプロパティ:

- env / is_live / is_paper / is_dev — 実行環境
- sqlite_path / paper_sqlite_path — 各 SQLite DB のパス
- duckdb_path — DuckDB のパス
- pid_file_path / kill_flag_path — PID / Kill flag のパス
- paper_fill_mode — ペーパートレードの約定動作（instant / partial / never / reject）
- cpu_threshold_pct / memory_threshold_pct / disk_threshold_pct — 監視閾値
- log_level — ログレベル

自動 .env 読み込み:
- プロジェクトルートにある `.env` / `.env.local` を自動で読み込みます（OS 環境変数が優先）。
- 無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定。

---

## ディレクトリ構成

（主要ファイルのみ抜粋）

- src/kabusys/
  - __init__.py
  - config.py                        — 環境変数 / 設定管理
  - run_execution.py                 — ExecutionEngine 起動スクリプト
  - run_monitoring.py                — Monitoring 起動スクリプト
  - data/                             — (実行時に使用するローカルディレクトリ; README では data/)
  - execution/
    - execution_engine.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - broker_factory.py
    - broker_api.py
    - order_record.py
    - order_repository.py
  - monitoring/
    - monitoring_db.py               — SQLite テーブル初期化 + MonitoringDB
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py
    - monitoring_engine.py
    - streamlit_dashboard.py
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

（上記以外に utils, data, research の補助モジュール等）

---

## 開発者向けメモ（設計上のポイント）

- DB 初期化 (`init_monitoring_db`) は冪等化されており、既存 DB に対して安全に実行できます。マイグレーションも最小限のスキーマ追加で対応しています。
- `KABUSYS_ENV` の `paper_trading` モードでは発注処理は MockBrokerClient を使用し、データは `PAPER_TRADING_SQLITE_PATH` へ保存されます（本番 DB と分離）。
- AI 呼び出しは冪等・フォールバック重視：API エラー時は安全にフォールバックし、失敗でシステム停止を引き起こさない設計です。
- `utils.process_priority` はプラットフォーム差異（Windows / POSIX）を吸収してプロセス優先度を設定しますが、権限不足だと警告を出してスキップします。
- `MonitoringEngine` は単体実行（run_once）と常駐ループ（run）をサポートしており、ユニットテストが行いやすい構造になっています。

---

## よくある質問 / トラブルシュート

- DB が見つからない / 開けない:
  - パスの確認（`SQLITE_PATH` / `PAPER_TRADING_SQLITE_PATH`）。streamlit は read-only URI で開くためファイル存在が必要です。
- OpenAI 関連でエラーが出る:
  - `OPENAI_API_KEY` が設定されているか確認。環境変数、もしくは関数引数で API キーを渡してください。
- 自動 .env 読み込みを無効化したい:
  - `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定。

---

必要であれば、README に含める具体的な .env.example サンプルや、起動スクリプトの systemd / supervisor 用のサービス例も追加できます。どの情報を詳述したいか教えてください。