# KabuSys — 自動売買システム（README）

このリポジトリは日本株向けの自動売買・運用支援ツール群です。  
本READMEではプロジェクトの概要、主な機能、セットアップ手順、使い方、主要なディレクトリ構成を日本語でまとめます。

※ 本ドキュメントはソースコード（src/kabusys 以下）に基づいています。

---

目次
- プロジェクト概要
- 機能一覧
- 前提（推奨環境）
- セットアップ手順
- 使い方（主要コマンド・スクリプト）
- 環境変数と設定
- ファイル・ディレクトリ構成（主要ファイルの説明）
- 付録：トラブルシューティングのヒント

---

## プロジェクト概要

KabuSys は日本株の自動売買を支援するシステム群です。  
主な責務は以下のとおりです。

- データ更新・特徴量生成（DuckDB を想定）
- シグナル生成・ポートフォリオ構築（純粋関数群）
- Execution（発注エンジン）と監視（Monitoring）
- 起動時チェック・各種レポート生成（Pre-Market、Signal Queue、Execution Startup、Night Batch 等）
- Paper Trading（模擬発注）向けの検証ツール

設計上、レポート生成・ポートフォリオ構築・リスク調整などは「副作用なし（DBや外部APIを必要としない）関数」で実装されており、別途 DuckDB / SQLite / ブローカークライアントなどを組み合わせて動作します。

---

## 機能一覧

- Execution（発注）エンジン起動および管理（run_execution）
  - 本番 / ペーパートレードの切替（KABUSYS_ENV）
  - 起動時リコンシリエーション / Execution Startup Summary の生成
  - RiskManager による発注制限
- Monitoring（システム監視）ポーリングループ（run_monitoring）
  - CPU / メモリ / ディスクしきい値などの監視（Settings で閾値設定）
  - MONITOR_POLL_INTERVAL でポーリング間隔を調整可能
- レポート関連
  - Pre-Market Report（run_pre_market_report）
  - Signal Queue Confirmation（run_signal_queue_report）
  - Execution Startup Summary（operations/execution_startup_report）
  - Night Batch Report（operations/night_batch_report）
  - Paper Trading 検証レポート（tools/paper_verification_report）
- 環境設定ウィザード（config_setup）と設定検証（validate_config）
- ポートフォリオ構築ユーティリティ（portfolio パッケージ）
  - 候補選定、重み計算、ポジションサイジング、セクター制限、レジーム乗数
- ロギング、プロセス優先度設定ユーティリティ（utils）

---

## 前提（推奨環境）

- Python 3.10 以上（ソースに `X | None` などの構文を使用）
- 推奨パッケージ（最低限）:
  - duckdb
  - PyYAML (yaml)
  - psutil
- SQLite（Python 標準ライブラリに含まれます）
- Windows の Task Scheduler を利用するチェック（Pre-Market の task チェック）機能があるため、Windows 環境での実行を想定する箇所があります（Linux 環境でも動作しますが一部チェックがスキップされます）。

requirements.txt が提供されていない場合は、最低限以下をインストールしてください（例）:

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install duckdb pyyaml psutil
```

---

## セットアップ手順

1. リポジトリをクローン・チェックアウトする。

2. Python 仮想環境を作成して有効化する（任意だが推奨）。

3. 必要パッケージをインストールする（上記参照）。

4. 環境変数ファイルの準備
   - 対話式ウィザードで .env を作成する:
     ```bash
     python -m kabusys.config_setup
     ```
   - 手動で .env を作る場合は `.env.example` を参考にしてください（リポジトリにある場合）。重要な必須項目:
     - JQUANTS_REFRESH_TOKEN（必須）
     - JQUANTS_BULK_API_KEY（必須）
     - KABU_API_PASSWORD（必須）
     - KABUSYS_ENV（development / paper_trading / live）
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（Paper Trading 用: data/paper_trading.db）
   - 自動ロード:
     - config.py はプロジェクトルート（.git または pyproject.toml を基準）を探索して `.env` / `.env.local` を自動で読み込みます。
     - 自動読み込みを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

5. 設定検証:
   ```bash
   python -m kabusys.validate_config
   # 警告も失敗と見なす場合:
   python -m kabusys.validate_config --strict
   ```

6. データディレクトリ作成（必要に応じて）
   - デフォルトのパス: `data/`, `logs/`, `artifacts/` は起動時に作成されますが、権限や場所を事前確認してください。

---

## 使い方（主要コマンド）

以下のモジュールはパッケージのモジュール実行で起動できます（例: python -m kabusys.run_execution）。

- 実行エンジン（Execution）
  - 起動:
    ```bash
    python -m kabusys.run_execution
    ```
  - 環境切替:
    - ペーパートレード:
      ```bash
      export KABUSYS_ENV=paper_trading
      # Windows (PowerShell): $env:KABUSYS_ENV = "paper_trading"
      python -m kabusys.run_execution
      ```
    - Paper Trading は MockBrokerClient を使用し、データは `data/paper_trading.db`（または `PAPER_TRADING_SQLITE_PATH`）に記録されます（本番 DB と分離）。

- 監視ループ（Monitoring）
  - 起動:
    ```bash
    python -m kabusys.run_monitoring
    ```
  - ポーリング間隔の変更:
    - 環境変数 `MONITOR_POLL_INTERVAL`（秒）を設定できます（デフォルト 60 秒）。
    - 例: `MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring`

  - 停止フラグ:
    - 監視/実行プロセスはプロジェクトルートの `data/stop_requested.flag` を監視します。このファイルを作成すると安全に停止します。

- Pre-Market Report
  - 実行・保存:
    ```bash
    python -m kabusys.run_pre_market_report
    python -m kabusys.run_pre_market_report --save
    python -m kabusys.run_pre_market_report --json
    ```

- Signal Queue Confirmation View
  - 実行例:
    ```bash
    python -m kabusys.run_signal_queue_report
    python -m kabusys.run_signal_queue_report --date 2026-04-28
    python -m kabusys.run_signal_queue_report --save --json
    ```

- 設定ウィザード
  ```bash
  python -m kabusys.config_setup
  ```

- 設定検証
  ```bash
  python -m kabusys.validate_config
  ```

- Paper Trading 検証レポート（ツール）
  ```bash
  python -m kabusys.tools.paper_verification_report
  # 期間指定
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB 指定
  python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db
  ```
  - 環境変数 `PAPER_TRADING_SQLITE_PATH` で DB を指定可能。

- レポートの保存場所（デフォルト）
  - Pre-Market: artifacts/pre_market/{YYYY-MM-DD}/
  - Signal Queue: artifacts/signal_queue/{YYYY-MM-DD}/
  - Execution Startup: artifacts/execution_startup/{YYYY-MM-DD}/
  - Night Batch: artifacts/night_batch/{YYYY-MM-DD}/

---

## 環境変数と設定（主なもの）

- 必須（起動前に設定すること）
  - JQUANTS_REFRESH_TOKEN
  - JQUANTS_BULK_API_KEY
  - KABU_API_PASSWORD

- 主要な可変設定（デフォルト値）
  - KABUSYS_ENV: 実行環境（development / paper_trading / live）（デフォルト: development）
  - DUCKDB_PATH: data/kabusys.duckdb
  - SQLITE_PATH: data/monitoring.db
  - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
  - LOG_LEVEL: INFO（DEBUG/INFO/WARNING/ERROR/CRITICAL）
  - MONITOR_POLL_INTERVAL: 監視ポーリング秒数（デフォルト 60）
  - PAPER_FILL_MODE（paper_trading 用）:
    - 有効値: "instant" | "partial" | "never" | "reject"（デフォルト "instant"）
  - PID / Flag ファイル:
    - PID ファイル（実行エンジン）: data/execution.pid（Settings.pid_file_path）
    - Stop フラグ: data/stop_requested.flag
    - Kill フラグ: data/kill.flag（Settings.kill_flag_path）
    - KILL_FLAG_CLEAR_ON_START=1 にすると起動時に Kill Flag を自動クリア（注意: 本番では危険）

- .env の自動読み込み
  - プロジェクトルート検出 (.git または pyproject.toml があるディレクトリ) を基準に `.env` / `.env.local` をロードします。
  - OS 環境変数が優先され、`.env.local` は上書きモードで読み込まれます。
  - 自動読み込みを無効化する: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

---

## ログ・優先度・プロセス制御

- ロギング:
  - utils/logging_setup.py の `setup_logging(app_name="...")` を使って統一的ログを設定します。
  - デフォルトで stdout への出力と日次ローテーションのファイルハンドラ（logs/<app_name>.log）を設定します。
  - ログディレクトリ: `logs/`（環境変数 LOG_DIR で変更可）

- プロセス優先度:
  - 起動スクリプトは `set_process_priority("high")` を呼び出します（psutil を使用）。
  - プラットフォーム差分を吸収しますが、権限不足や未対応 OS では警告出力されスキップされます。

---

## ディレクトリ構成（主要ファイルの説明）

リポジトリの主要なディレクトリ / ファイル（src/kabusys を中心に抜粋）:

- src/kabusys/
  - __init__.py — パッケージ定義（バージョン等）
  - config.py — 環境変数 / Settings クラス、.env 自動ロードロジック
  - config_setup.py — .env 対話式ウィザード
  - validate_config.py — 起動前設定チェック CLI
  - run_execution.py — ExecutionEngine 起動スクリプト（本番 / paper 切替）
  - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト
  - run_pre_market_report.py — Pre-Market Report CLI
  - run_signal_queue_report.py — Signal Queue レポート CLI
  - operations/
    - pre_market_collector.py — Pre-Market のデータ収集（DB問い合わせ・ファイル・Task Schedulerチェック）
    - pre_market_report.py — Pre-Market レポート生成（純粋関数）
    - signal_queue_report.py — Signal Queue レポート生成（DuckDB 参照は collect_signals のみ）
    - execution_startup_report.py — Execution 起動時サマリ作成
    - night_batch_report.py — 夜間バッチ結果レポート
  - portfolio/
    - portfolio_builder.py — 候補選定・重み計算
    - position_sizing.py — 株数決定・資金配分
    - risk_adjustment.py — セクター上限・レジーム乗数
    - __init__.py — エクスポート
  - utils/
    - logging_setup.py — ログ設定ユーティリティ
    - process_priority.py — プロセス優先度 / CPU affinity ユーティリティ
  - research/
    - factor_research.py — ファクター計算（DuckDB を使用）
    - feature_exploration.py — 特徴量探索（研究用）
  - execution/ (発注関連のコンポーネント群。Broker / Engine / OrderManager 等）
  - monitoring/（監視 DB 初期化、SystemMonitor 実装など）
  - operations/（レポート・収集ロジック）
  - tools/
    - paper_verification_report.py — ペーパートレード検証用スクリプト

- config/
  - 各種 yaml 設定ファイル（例: risk_config.yaml, system_config.yaml など） — アプリケーション設定を格納

- data/
  - monitoring.db（デフォルト）や paper_trading.db、stop_requested.flag、kill.flag、*.pid などの実行時ファイル

- logs/
  - ログファイル（デフォルト出力先）

- artifacts/
  - 各種レポートの保存先（pre_market, signal_queue, execution_startup, night_batch 等）

---

## 付録：運用上の注意 / トラブルシューティング

- 本番環境（KABUSYS_ENV=live）では設定ミスが重大なトレード損失に繋がるため、validate_config で十分にチェックしてください（特に LINE 通知設定や Kill Switch の設定など）。
- stop/kill フラグ:
  - 自動的に停止させたい場合は `data/stop_requested.flag` を作成することで monitor / execution のループを止められます。
  - `data/kill.flag` は別途 Kill Switch 用（Settings.kill_flag_path）。本番で `KILL_FLAG_CLEAR_ON_START=1` を使うと危険です。
- Paper Trading：
  - paper_trading モードでは MockBroker を使い、発注は実行されず専用 SQLite（PAPER_TRADING_SQLITE_PATH）に記録されます。本番 DB と分離して検証できます。
- ログが出力されない / ファイルハンドラが作れない場合：
  - ディレクトリの権限やパスを確認してください。logging_setup は失敗時に stdout のみで継続する設計です。
- Windows の Task Scheduler チェックは `schtasks` コマンドを使用します。Linux 環境では該当チェックは失敗し False を返す（警告）ため、Pre-Market の判定に影響する可能性があります。

---

このREADMEはコードベースの主な使い方と設定をまとめたものです。  
さらに詳細な設計やアルゴリズム（ポートフォリオ構築の仕様や StrategyModel 等）はソース内のコメントや関連ドキュメント（もしあれば PortfolioConstruction.md, StrategyModel.md 等）を参照してください。必要であればさらに詳しい運用マニュアルやデプロイ手順を作成します。