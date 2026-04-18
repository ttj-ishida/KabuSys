# KabuSys

KabuSys は日本株向けの自動売買／リサーチ／モニタリングを目的とした小規模なシステム群です。  
本リポジトリには、実行エンジン（ExecutionEngine）、監視（Monitoring）、ポートフォリオ構築、リサーチ用ユーティリティ、AI を利用したニューススコアリングなどのモジュールが含まれます。

バージョン: 0.1.0

---

## 概要

- 自動売買ロジック（発注・オーダー管理・リスク管理）を実行する `run_execution`。
- システム安定性・データ鮮度・取引ログなどを定期的に記録・監視する `run_monitoring`。
- Paper Trading（模擬発注）を本番 DB と分離して実行可能。
- DuckDB を用いたリサーチ（ファクター計算・特徴量解析）モジュール。
- OpenAI（gpt-4o-mini 想定）を使ったニュース NLP による銘柄スコアリングと、市場レジーム判定。
- 設定ウィザード（`.env` 生成）と起動前チェック（設定検証 CLI）。
- 監視結果を SQLite（監視 DB）に永続化し、kill.switch（`data/kill.flag`）などで ExecutionEngine 停止を制御。

---

## 主な機能一覧

- 設定管理
  - .env 自動読み込み（プロジェクトルートにある `.env` / `.env.local`）
  - 対話式設定ウィザード (`kabusys.config_setup`)
  - 設定検証 CLI (`kabusys.validate_config`)
- 実行系
  - ExecutionEngine 起動スクリプト（`run_execution.py`）
  - Paper Trading 用の分離 DB（`data/paper_trading.db` デフォルト）
  - ブローカークライアント抽象化（BrokerClientFactory）
  - オーダー管理、リスク管理、リコンシリエーション
- 監視系
  - SystemMonitor / TradeMonitor / RiskMonitor を束ねる MonitoringEngine
  - monitoring DB（SQLite）による `system_status`, `trade_logs`, `positions`, `risk_logs`, `dashboard` の永続化
  - Kill Switch（閾値超過で `data/kill.flag` 書き込み）
  - run_monitoring のポーリングループ（環境変数で間隔上書き可能）
- ポートフォリオ構築
  - 候補選定、等分配・スコア重み配分、ポジションサイズ計算、セクターキャップ、レジーム乗数
- リサーチ
  - DuckDB を用いたファクター計算（モメンタム・バリュー・ボラティリティ等）
  - 将来リターン、IC（Information Coefficient）計算、統計サマリ
- AI（OpenAI）連携
  - ニュースのセンチメントを LLM でスコアリングして `ai_scores` へ保存（`kabusys.ai.news_nlp`）
  - マクロ記事＋ETF MA200 を合成して市場レジームを判定し `market_regime` に永続化（`kabusys.ai.regime_detector`）
- ツール
  - Paper Trading の検証レポート生成ツール（`kabusys.tools.paper_verification_report`）

---

## 前提・依存（推奨）

- Python 3.9+
- 必要パッケージ（例）
  - duckdb
  - psutil
  - openai
  - PyYAML（設定検証で YAML の中身検証を有効にする場合）
- 標準ライブラリ: sqlite3, logging, threading, datetime, pathlib 等

推奨インストール例:
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai PyYAML
# または requirements.txt があれば:
# pip install -r requirements.txt
```

---

## セットアップ手順

1. リポジトリをクローンし、仮想環境を作成して依存をインストールする（上記を参照）。

2. .env の準備
   - 対話式ウィザードで `.env` を作成する:
     ```
     python -m kabusys.config_setup
     ```
   - もしくはプロジェクトルートに `.env` を手動で配置する。
   - 必須の環境変数:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - 重要な環境変数（例）:
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
     - DUCKDB_PATH: data/kabusys.duckdb（分析用）
     - SQLITE_PATH: data/monitoring.db（監視用）
     - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db（paper_trading 用）
     - OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合）
     - LOG_LEVEL: DEBUG/INFO/…
     - KILL_FLAG_CLEAR_ON_START: 0/1（本番では 0 推奨）

3. 設定検証（起動前に推奨）
   ```
   python -m kabusys.validate_config
   # 警告も失敗扱いにする場合:
   python -m kabusys.validate_config --strict
   ```

4. データディレクトリ作成（必要に応じて）
   ```
   mkdir -p data logs
   ```

---

## 使い方（起動例）

- 監視ループ起動:
  ```
  python -m kabusys.run_monitoring
  ```
  - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL`（秒）で上書き可能（デフォルト 60 秒）。
  - 監視は常に本番の sqlite_path（Settings.sqlite_path）を使用します。
  - 停止はプロジェクトルートの `data/stop_requested.flag` を作成するか、Ctrl+C。

- 実行エンジン起動:
  ```
  python -m kabusys.run_execution
  ```
  - KABUSYS_ENV により挙動が変わります:
    - `paper_trading`: MockBrokerClient を使い `data/paper_trading.db` を使用（本番 DB と完全分離）
    - `live`: 本番ブローカーを利用
  - ExecutionEngine は `data/execution.pid`（デフォルト）に PID を書きます。
  - 停止シグナルは `data/stop_requested.flag` を作成することで検出されます。

- Paper Trading 検証レポート:
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  - DB は `--db PATH` または環境変数 `PAPER_TRADING_SQLITE_PATH` で指定。

- AI スコア計算（ライブラリ関数）
  - `kabusys.ai.score_news(conn, target_date, api_key=None)` — DuckDB 接続を渡してニューススコアリングを実行。
  - `kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)` — 市場レジーム判定を行い `market_regime` テーブルに書き込む。

注意:
- OpenAI API を利用する場合、`OPENAI_API_KEY` が必要。
- AI 呼び出しは失敗耐性（リトライ・フォールバック）を実装していますが、API 料金やレート制限に注意してください。

---

## フラグ・停止・PID

- 停止フラグ（ExecutionEngine 停止）
  - data/kill.flag — Kill Switch によって書き込まれる（Execution を完全に止めるために使用）
  - data/stop_requested.flag — run_execution / run_monitoring の外部停止指示に使用（起動ループはこれを参照）
- PID ファイル
  - data/execution.pid — ExecutionEngine が起動時に書き込む PID（デフォルト、Settings.pid_file_path）

---

## 重要な環境変数（抜粋）

- KABUSYS_ENV: execution モード（development / paper_trading / live）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（AI 機能使用時）
- DUCKDB_PATH / SQLITE_PATH / PAPER_TRADING_SQLITE_PATH: 各 DB パス
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒）
- PAPER_FILL_MODE: paper_trading の MockBroker の fill モード（instant|partial|never|reject）
- LOG_LEVEL: ログ出力レベル（INFO など）

---

## ロギング

- ロギングは `kabusys.utils.logging_setup.setup_logging()` で統一的に設定します。
- デフォルトは `logs/<app_name>.log`（日次ローテーション、30 世代保持）。
- 標準出力は stdout に出力されます（cron / systemd からの一貫した取り扱いのため）。

---

## ディレクトリ構成

以下は主なファイル/ディレクトリ（抜粋）です:

- src/kabusys/
  - __init__.py
  - config.py                    — 環境変数/設定管理
  - config_setup.py              — .env 対話式生成ウィザード
  - validate_config.py           — 設定検証 CLI
  - run_monitoring.py            — SystemMonitor ポーリング起動スクリプト
  - run_execution.py             — ExecutionEngine 起動スクリプト
  - tools/
    - paper_verification_report.py
  - utils/
    - logging_setup.py
    - process_priority.py
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py            — （コード例に含まれていると想定）
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py            — （実装があれば）
  - execution/
    - execution_engine.py        — 発注エンジン（主要ロジック）
    - broker_factory.py
    - order_manager.py
    - order_repository.py
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
  - data/                         — （実行時に DB / フラグファイルを配置）
  - logs/                         — ログ出力先（実行時に作成）

（実際のファイル一覧はリポジトリ内を確認してください）

---

## 運用上の注意・ベストプラクティス

- 本番で `KABUSYS_ENV=live` を設定する際は `.env` の内容を十分に確認してください。`validate_config` は `--strict` で警告も FAIL 扱いにできます。
- Kill Switch（`data/kill.flag`）や `KILL_FLAG_CLEAR_ON_START` 設定は本番運用で特に慎重に取り扱ってください。`KILL_FLAG_CLEAR_ON_START=1` は本番では危険です（自動的に危険な状態をクリアしてしまうため）。
- Paper Trading と本番 DB は分離されていますが、ファイルパスの指定ミスには注意してください（`PAPER_TRADING_SQLITE_PATH` / `SQLITE_PATH`）。
- OpenAI 連携は API キー管理・コストに注意し、レート制限や失敗時のフォールバックを想定して運用してください。
- ログディレクトリに関するパーミッションやディスク容量管理を行い、ログローテーションや古いログの削除方針を定めてください。

---

## 開発者向けメモ

- DuckDB 接続を渡す設計により、analysis（リサーチ）機能は本番 DB に直接アクセスしつつ、SQL と Python を組み合わせた処理を行います。
- モジュール設計は副作用を最小化する方針（例: Settings は環境変数をラップ、DB 初期化は冪等）。
- テストを容易にするため、AI 呼び出しや外部依存は内部で差し替え（patch）しやすい設計になっています。

---

もし README に追加したい具体的な例（.env.example、実行時ログのサンプル、systemd ユニットファイルの例など）があれば教えてください。必要に応じて追記します。