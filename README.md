# KabuSys

日本株自動売買システムのコードベース（README）。このドキュメントはローカル開発／デプロイ時に必要な概要、セットアップ、実行方法、ディレクトリ構成を日本語でまとめたものです。

> 注: 本 README はリポジトリ内の `src/kabusys` のコードから生成しています。実行環境や依存ライブラリは環境に合わせて調整してください。

---

目次
- プロジェクト概要
- 主な機能一覧
- 前提・依存ライブラリ
- セットアップ手順
- 使い方（起動コマンド・CLI）
- 主要な環境変数
- 実行時の停止／フラグ制御
- ディレクトリ構成（主要ファイルの説明）

---

## プロジェクト概要

KabuSys は日本株の自動売買／リサーチ／監視を目的とした Python ベースのシステムです。  
主な機能は以下の通り：

- データ加工・ファクター計算（DuckDB を利用）
- ポートフォリオ構築（候補選定、ウェイト計算、株数決定）
- ExecutionEngine（ブローカークライアントを介した発注・注文管理）
- 監視（System / Trade / Risk モニタ、Kill Switch）
- AI モジュール（ニュースの NLP スコアリング、レジーム判定を OpenAI API で実行）
- ペーパートレード専用モード（本番 DB と分離）

---

## 機能一覧（主要）

- data / DuckDB を使った時系列データ処理（prices_daily / raw_financials 等）
- research:
  - ファクター計算（モメンタム / ボラティリティ / バリュー）
  - 将来リターン計算、IC（情報係数）算出、統計サマリー
- portfolio:
  - 候補選定（スコア順）
  - 重み計算（等金額・スコア重み）
  - ポジションサイジング（risk_based／equal／score）
  - セクター上限やレジーム乗数の適用
- execution:
  - BrokerClientFactory により実ブローカーまたは MockBroker を選択（KABUSYS_ENV に依存）
  - OrderManager, RiskManager, Reconciler, ExecutionEngine（PID 管理・停止フラグの監視）
- monitoring:
  - SystemMonitor（CPU / メモリ / ディスク / データ鮮度 / 実行プロセス検出）
  - TradeMonitor（trade_logs の監視、滞留注文・価格異常検知）
  - RiskMonitor（ドローダウン・ポジション上限監視、dashboard 更新）
  - KillSwitch（条件により `data/kill.flag` を書き込み ExecutionEngine を停止）
  - MonitoringEngine（各 Monitor を定期実行）
- ai:
  - news_nlp：ニュースを OpenAI（gpt-4o-mini 等）でセンチメントし ai_scores に保存
  - regime_detector：ETF の MA 指標とマクロニュースの LLM スコアを合成してレジーム判定
- tools:
  - paper_verification_report：ペーパートレード DB から検証レポートを生成

---

## 前提・依存ライブラリ（概略）

推奨 Python バージョン: 3.10+

主要依存（抜粋）:
- duckdb
- psutil
- openai
- pyyaml（config 検証時に利用、無くても動作は可能）
- sqlite3（標準）
- logging（標準）

インストール例（仮）:
```bash
python -m pip install duckdb psutil openai pyyaml
```
リポジトリ側に requirements.txt がある場合はそれを利用してください。

---

## セットアップ手順

1. リポジトリをクローン／配置
2. Python 仮想環境を作成・有効化
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
   ```
3. 依存ライブラリをインストール
   ```bash
   pip install duckdb psutil openai pyyaml
   ```
4. 環境変数の作成
   - 対話式ウィザードで .env を作成:
     ```bash
     python -m kabusys.config_setup
     ```
   - もしくはプロジェクトルートに `.env` を作成し主要変数を設定します（下記「主要環境変数」参照）。
   - 自動 `.env` 読み込みを無効化するには:
     ```bash
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```
5. 設定検証（推奨）
   ```bash
   python -m kabusys.validate_config
   # 警告もエラー扱いにする場合
   python -m kabusys.validate_config --strict
   ```
6. 必要に応じて DuckDB / SQLite の DB ファイルを初期配置（コードは起動時にディレクトリ作成を行うことが多いです）。

---

## 使い方（起動・CLI）

- ExecutionEngine を起動（通常運用 / ペーパートレードは KABUSYS_ENV で切替）
  ```bash
  python -m kabusys.run_execution
  ```
  - KABUSYS_ENV=paper_trading を指定すると MockBrokerClient が用いられ、データは `data/paper_trading.db`（既定）へ記録されます。
  - 実行中の停止は `data/stop_requested.flag` を作成するか、Execution 側の kill.flag を書き込むことで行います。

- Monitoring を起動（監視ループ）
  ```bash
  # デフォルトのポーリング間隔は 60 秒。環境変数で上書き可。
  export MONITOR_POLL_INTERVAL=30  # 30秒間隔に変更
  python -m kabusys.run_monitoring
  ```

- 設定ウィザード（.env 作成・更新）
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
  # DB パスは --db で指定するか、環境変数 PAPER_TRADING_SQLITE_PATH を使用
  ```

- AI モジュール呼び出し（プログラム内 API）
  - ニュース NLP スコアリング:
    from kabusys.ai.news_nlp import score_news
    score_news(duckdb_conn, target_date, api_key="...")
  - レジーム判定:
    from kabusys.ai.regime_detector import score_regime
    score_regime(duckdb_conn, target_date, api_key="...")

  これらは OpenAI API キー（OPENAI_API_KEY 環境変数または引数）を必要とします。

---

## 主要な環境変数

（代表的なもののみ抜粋）

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants API 用リフレッシュトークン
- KABU_API_PASSWORD (必須) — kabuステーション API パスワード
- KABUSYS_ENV — 実行環境: development / paper_trading / live（デフォルト: development）
- OPENAI_API_KEY — OpenAI API キー（AI モジュールを利用する場合必須）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite 監視 DB（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード用 SQLite（paper_trading 時に使用）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...、デフォルト: INFO）
- MONITOR_POLL_INTERVAL — Monitoring のポーリング間隔（秒、デフォルト: 60）
- PAPER_FILL_MODE — Paper Trading 時の注文約定モード（instant/partial/never/reject）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリア (0/1)

.env の自動読み込み
- プロジェクトルートの `.env` / `.env.local` は自動で読み込まれます。無効化する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## 実行時の停止・フラグ制御

- data/stop_requested.flag
  - `run_monitoring.py` / `run_execution.py` がこのファイルの存在を検知すると優雅に終了します（起動前に既に存在する場合は ExecutionEngine を起動しません）。
- data/kill.flag
  - `KillSwitch` が条件を満たすとこのファイルを書き込み ExecutionEngine に停止シグナルを送ります。内部ルールは RiskMonitor 等が評価します。
- PID ファイル
  - ExecutionEngine は起動時に PID ファイルを扱います（デフォルト: data/execution.pid）。設定は Settings.pid_file_path で変更可能。

---

## ディレクトリ構成（主要ファイルと簡単な説明）

src/kabusys/
- __init__.py
  - パッケージ定義・バージョン情報
- config.py
  - .env / 環境変数の読み込みと Settings クラス
- config_setup.py
  - 対話式 .env 作成ウィザード
- validate_config.py
  - 起動前設定検証 CLI

起動スクリプト:
- run_execution.py
  - ExecutionEngine 起動スクリプト（KABUSYS_ENV により paper_trading モード選択）
- run_monitoring.py
  - SystemMonitor ポーリングループ起動スクリプト（MONITOR_POLL_INTERVAL で調整）

portfolio/
- portfolio_builder.py
  - 候補選定・重み計算（select_candidates, calc_equal_weights, calc_score_weights）
- position_sizing.py
  - 株数計算・上限・lot 単位処理
- risk_adjustment.py
  - セクター上限・レジーム乗数

research/
- factor_research.py
  - momentum / volatility / value 等のファクター計算（DuckDB を使用）
- feature_exploration.py
  - 将来リターン、IC、統計サマリ等

ai/
- news_nlp.py
  - ニュースの NLP スコアリング（OpenAI 使用）
- regime_detector.py
  - 市場レジーム判定（MA + LLM 合成）

monitoring/
- monitoring_db.py
  - SQLite ベースの監視用永続化層（テーブル定義・読み書き）
- system_monitor.py
  - システム状態・データ鮮度の監視
- trade_monitor.py
  - trade_logs を元に注文系の監視（ファイルは repository に含まれています）
- risk_monitor.py
  - ドローダウンやポジション数の監視
- kill_switch.py
  - 条件に応じて kill.flag を書き込む
- monitoring_engine.py
  - 各 Monitor を束ねるループ実行ロジック
- alert_manager.py
  - （通知送信ロジック、LINE など）※コードベースに依存

execution/
- execution_engine.py, order_manager.py, order_repository.py, reconciler.py, risk_manager.py, broker_factory.py
  - 注文運用ロジック・ブローカー抽象化・リスク制御

utils/
- logging_setup.py
  - 統一的なロギング設定（コンソール＋日次ローテーション）
- process_priority.py
  - プロセス優先度・CPU affinity 設定ユーティリティ

tools/
- paper_verification_report.py
  - ペーパートレードの検証レポート生成スクリプト

data/
- （実行時に生成されることが多い）
  - monitoring DB（例: data/monitoring.db）
  - paper_trading DB（例: data/paper_trading.db）
  - kill.flag / stop_requested.flag / execution.pid など

---

補足・運用上の注意
- KABUSYS_ENV が `live` の場合は本番と見なされ、十分な注意と監査のもとで設定してください（validate_config は live での警告を行います）。
- AI モジュールは OpenAI API を利用します。API コスト・レイテンシ・エラーに注意し、API_KEY は安全に管理してください。
- SQLite / DuckDB ファイルのバックアップと権限設定に注意してください。特にライブ環境では DB の取り扱いに注意。

---

この README はコードの現状に基づいて作成しています。リポジトリに新しいモジュールや CLI が追加された場合は適宜更新してください。必要であれば、README を拡張して運用手順（systemd / docker / supervisor 用の Unit ファイル例）やデプロイ手順も追加できます。