# KabuSys

日本株自動売買システム（モジュール群）  
このリポジトリは、シグナル生成・ポートフォリオ構築、発注実行、監視、AIベースのニュースセンチメントなどを備えた自動売買基盤の一部実装です。

Version: 0.1.0

---

## 概要

KabuSys は日本株の自動売買に必要なコンポーネント群を提供します。主なサブシステムは次の通りです。

- ExecutionEngine: 発注ロジック・ブローカー連携・リスク制御
- MonitoringEngine: システム稼働状況・注文状態・リスク監視、Kill Switch
- Research / Portfolio: ファクター計算、候補選定、ポジションサイズ計算
- AI モジュール: ニュース NLP によるセンチメント算出、レジーム判定
- ユーティリティ: 設定管理・ログ設定・プロセス優先度設定 等
- ツール: ペーパートレード検証レポート生成等

本 README はローカル実行や運用・検証のための基本的な手順を記載しています。

---

## 機能一覧

- 環境設定ウィザード（`kabusys.config_setup`）: .env を対話形式で生成・更新
- 設定検証 CLI（`kabusys.validate_config`）: .env と config/*.yaml の事前チェック
- ExecutionEngine 起動スクリプト（`kabusys.run_execution`）:
  - `KABUSYS_ENV=paper_trading` の場合は MockBroker を使い DB を分離（paper_trading 用 SQLite）
  - プロセス優先度調整、PID/停止フラグ管理、スレッドでのエンジン実行
- MonitoringEngine 起動スクリプト（`kabusys.run_monitoring`）:
  - 定期ポーリングで System/Trade/Risk をチェック、Kill Switch を発動
  - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）
- 監視用永続化（SQLite）: system_status / trade_logs / positions / risk_logs / dashboard
- Portfolio モジュール: 候補選定・重み付け・ポジションサイズ計算・セクター上限適用
- Research: momentum/volatility/value 等のファクター計算（DuckDB ベース）
- AI モジュール:
  - `kabusys.ai.news_nlp.score_news`: OpenAI を使ったニュースごとのセンチメント算出・ai_scores への書き込み
  - `kabusys.ai.regime_detector.score_regime`: ma200 とマクロニュースを組み合わせた市場レジーム判定
- ツール: ペーパートレード検証レポート出力（`kabusys.tools.paper_verification_report`）

---

## 必要要件（主な依存パッケージ）

最低限インストールしておくもの（例）:

- Python 3.10+
- duckdb
- psutil
- openai
- PyYAML（config の検証で必要・任意）

インストール例（venv 推奨）:

```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai PyYAML
```

（プロジェクトに requirements.txt があればそれを利用してください）

---

## セットアップ手順

1. リポジトリをクローンしてワークディレクトリへ移動

2. 仮想環境を作成し依存関係をインストール

3. .env を作成
   - 対話式ウィザードで作る:
     ```bash
     python -m kabusys.config_setup
     ```
   - もしくは `.env` を手動で作成し、以下の必須環境変数を設定してください:
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
   - 重要なサンプル設定:
     - KABUSYS_ENV: development | paper_trading | live
     - DUCKDB_PATH: data/kabusys.duckdb
     - SQLITE_PATH: data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db（paper_trading 用）
     - OPENAI_API_KEY: OpenAI API を利用する場合に必要

4. 設定検証（起動前に実行推奨）
   ```bash
   python -m kabusys.validate_config
   # 警告も失敗扱いにする場合:
   python -m kabusys.validate_config --strict
   ```

5. データディレクトリ / ログディレクトリの確認
   - デフォルト DB 等は `data/` 配下に保存されます。必要に応じてディレクトリ作成やパスを .env で変更してください。
   - ログはデフォルトで `logs/` に日次ローテーションで出力されます。

---

## 環境変数（主要なもの）

- KABUSYS_ENV: 実行環境（development | paper_trading | live）
- JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト http://localhost:18080/kabusapi）
- OPENAI_API_KEY: OpenAI API キー（AI モジュール使用時）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 SQLite（paper_trading 時に使用）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）
- LOG_DIR: ログ保存先（デフォルト logs/）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、デフォルト 60）
- PAPER_FILL_MODE: ペーパートレードのフィルモード（instant | partial | never | reject）
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1: 自動 .env ロードを無効化（テスト用）

---

## 実行方法（主要コマンド）

- ExecutionEngine の起動（本番またはペーパートレード）
  ```bash
  # 環境変数で切り替え例:
  export KABUSYS_ENV=paper_trading
  python -m kabusys.run_execution
  ```
  - ペーパートレードでは `PAPER_TRADING_SQLITE_PATH`（デフォルト: data/paper_trading.db）へ記録され、本番 DB と分離されます。
  - 起動時に `data/stop_requested.flag` が存在すると起動せず終了します。
  - 実行中は `data/execution.pid` が作成されます。

- MonitoringEngine の起動
  ```bash
  # ポーリング間隔を上書きする例（秒）
  export MONITOR_POLL_INTERVAL=30
  python -m kabusys.run_monitoring
  ```
  - 監視ループは `MONITOR_POLL_INTERVAL`（デフォルト 60 秒）で動作します。
  - 監視は常に production 用 sqlite_path（Settings.sqlite_path）を使用します（環境に依らない）。

- 設定ウィザード
  ```bash
  python -m kabusys.config_setup
  ```

- 設定検証
  ```bash
  python -m kabusys.validate_config
  ```

- ペーパートレード検証レポート（ツール）
  ```bash
  # デフォルト DB: data/paper_trading.db
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # 別 DB を指定する場合
  python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db
  ```

- AI モジュールを直接呼ぶ（Python REPL 等）
  ```python
  from kabusys.ai.news_nlp import score_news
  import duckdb
  conn = duckdb.connect('data/kabusys.duckdb')
  # score_news(conn, date(2026, 4, 15)) のように使用（OPENAI_API_KEY が必要）
  ```

---

## ログ / DB の配置

- デフォルトログディレクトリ: logs/
  - ファイル名はアプリ名毎に分かれる（例: logs/execution.log, logs/monitoring.log）
  - 日次ローテーション・30日分保持

- デフォルトデータディレクトリ: data/
  - DuckDB: data/kabusys.duckdb
  - 監視 SQLite: data/monitoring.db
  - ペーパートレード SQLite: data/paper_trading.db
  - フラグファイル:
    - data/kill.flag: Kill Switch により ExecutionEngine を停止させるためのファイル
    - data/stop_requested.flag: 実行中スクリプトにループ停止を要求するためのフラグ
  - PID:
    - data/execution.pid: ExecutionEngine の PID（存在時は実行中の目安）

---

## 運用上の注意

- Kill Switch:
  - RiskMonitor 等が条件を満たすと `KillSwitch` が `data/kill.flag` に理由を書き込みます。ExecutionEngine は起動時や稼働中にこのフラグを確認して安全な停止を行います。
  - `KILL_FLAG_CLEAR_ON_START=1` を本番で設定すると起動時に自動で kill.flag をクリアしてしまい危険なので注意（デフォルト 0 推奨）。

- ペーパートレード分離:
  - `KABUSYS_ENV=paper_trading` にすると execution は `PAPER_TRADING_SQLITE_PATH` に記録します。本番データベースとは完全に分離されます。

- プロセス優先度:
  - 起動スクリプトは最初に process priority を "high" に設定しようとしますが、環境によって設定できない場合は警告が出ます。

- DuckDB / SQLite の互換性:
  - AI モジュールや Research モジュールは DuckDB に対する SQL を実行します。DuckDB のバージョンによる制約（executemany の空リスト問題など）に注意していますが、運用時は推奨バージョンを合わせてください。

- ログディレクトリ作成に失敗した場合、ファイル出力ハンドラは無効化され標準出力のみになります。権限等を確認してください。

---

## ディレクトリ構成（抜粋）

リポジトリ内の主要ファイル/ディレクトリを示します（実際のファイル構成は若干異なる場合があります）。

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数・設定管理
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor 起動スクリプト
  - tools/
    - paper_verification_report.py
  - utils/
    - logging_setup.py
    - process_priority.py
  - monitoring/
    - monitoring_db.py
    - monitoring_engine.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py
  - execution/
    - execution_engine.py
    - order_manager.py
    - order_repository.py
    - broker_factory.py
    - reconciler.py
    - risk_manager.py
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
  - data/                    — 実行時に使用するデータ・DB（規約）
  - logs/                    — ログ出力先（デフォルト）

---

## 参考コマンド例

- バックグラウンドで実行（簡易例）
  ```bash
  nohup python -m kabusys.run_monitoring > /var/log/kabusys_monitor.out 2>&1 &
  nohup python -m kabusys.run_execution > /var/log/kabusys_exec.out 2>&1 &
  ```

- 停止（フラグファイルを置く）
  ```bash
  # 実行中のエンジンに即時停止を要求
  mkdir -p data
  echo "stop requested" > data/stop_requested.flag
  # ExecutionEngine はこのファイルを検知して安全停止します
  ```

- Kill Switch を手動でクリア
  ```bash
  rm -f data/kill.flag
  ```

---

## 開発・拡張ポイント（メモ）

- position_sizing / portfolio のロジックは純粋関数として設計されているためユニットテストが書きやすいです。
- AI モジュールは外部 API（OpenAI）に依存するため、ユニットテストでは _call_openai_api をモックする設計になっています。
- DuckDB を利用した Research 周りは大規模データ分析向けに SQL を中心に構築されています。

---

README は以上です。不明点や README の追記・修正したい箇所があれば具体的に教えてください（例: 運用手順の拡充、サンプル .env の追加、システム図の追加など）。