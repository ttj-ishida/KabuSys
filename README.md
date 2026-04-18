# KabuSys

日本株自動売買システムのコアライブラリ群と起動スクリプト群です。  
このリポジトリは発注エンジン、監視エンジン、ポートフォリオ構築、ファクター計算、ニュースNLP（OpenAI）などのモジュールで構成されています。

バージョン: 0.1.0

---

## 概要

KabuSys は以下の責務を持つコンポーネント群を提供します。

- ExecutionEngine: ブローカークライアントを通じた発注処理・オーダー管理・リスク管理
- Monitoring: システム資源、発注ログ、リスク指標の定期監視とアラート / Kill Switch
- Portfolio construction: 候補選定・重み付け・ポジションサイズ計算・セクター制限などの純粋関数
- Research: DuckDB 上のファクター算出・将来リターン・IC 等の解析用ユーティリティ
- AI: OpenAI を利用したニュースセンチメント評価や市場レジーム判定
- Tools: ペーパートレード検証レポート生成スクリプト 等

設計方針の一部:
- 本番用の設定は環境変数 / `.env` で管理
- Paper Trading（模擬発注）は本番 DB と分離（`data/paper_trading.db`）
- DuckDB は分析用途、SQLite は監視・履歴用途として利用
- OpenAI を利用する機能は API キーが必須（失敗時はフェイルセーフ）

---

## 主な機能一覧

- 起動スクリプト
  - run_execution: ExecutionEngine を起動（`KABUSYS_ENV=paper_trading` で MockBroker を使用）
  - run_monitoring: SystemMonitor のポーリングループ起動（MONITOR_POLL_INTERVAL で間隔変更可能）
- 設定
  - config_setup: 対話式に `.env` を作成・更新
  - validate_config: `.env` と `config/*.yaml` の事前検証ツール
- 監視
  - system_monitor / trade_monitor / risk_monitor / monitoring_engine / kill_switch
  - monitoring_db: SQLite テーブルの作成・マイグレーション・読み書き
- ポートフォリオ
  - 候補選定、等配分 / スコア加重配分、ポジションサイズ計算、セクター制限、レジーム乗数
- 解析（research）
  - ファクター算出（momentum / value / volatility 等）
  - 将来リターン・IC・統計サマリ
- AI
  - news_nlp: OpenAI でニュースを銘柄ごとにスコアリングし ai_scores に保存
  - regime_detector: MA とマクロニュースセンチメントを合成して日次レジーム判定
- ツール
  - paper_verification_report: ペーパートレード DB の検証レポート生成

---

## セットアップ手順

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo-root>
   ```

2. Python 仮想環境を作成・有効化
   ```
   python -m venv .venv
   source .venv/bin/activate   # Unix/macOS
   .venv\Scripts\activate      # Windows
   ```

3. 依存パッケージをインストール  
   （requirements.txt がある場合はそれを使用してください。なければ少なくとも以下をインストール）
   ```
   pip install duckdb psutil openai PyYAML
   ```
   - duckdb: 分析テーブル操作
   - psutil: プロセス優先度・CPU/メモリ取得等
   - openai: ニュースNLP / レジーム判定で使用
   - PyYAML: `validate_config` の YAML 検証に任意で必要

4. 設定ファイル（.env）を作成  
   対話式ウィザードで作成できます:
   ```
   python -m kabusys.config_setup
   ```
   または手動で `.env` を作成してください。必須環境変数:
   - JQUANTS_REFRESH_TOKEN
   - KABU_API_PASSWORD

   推奨 / 主要変数:
   - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
   - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH（デフォルト: data/monitoring.db）
   - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト: data/paper_trading.db）
   - LOG_LEVEL（DEBUG/INFO/...）
   - OPENAI_API_KEY（AI 機能を使う場合）

5. 設定検証（任意だが推奨）
   ```
   python -m kabusys.validate_config
   # 警告も FAIL にしたい場合
   python -m kabusys.validate_config --strict
   ```

6. データディレクトリの確認（必要に応じて作成）
   - data/: デフォルトで SQLite DB、PID / flag ファイル等を置く
   - logs/: ログファイル（`kabusys.utils.logging_setup` により自動作成を試みます）

---

## 使い方（主要コマンド）

- ExecutionEngine を起動
  ```
  python -m kabusys.run_execution
  ```
  - `KABUSYS_ENV=paper_trading` のときは MockBrokerClient を使用し、Paper Trading 用 DB（`PAPER_TRADING_SQLITE_PATH`）に記録します。
  - 起動時に `data/stop_requested.flag` が存在すると起動しません。
  - 実行中は `data/execution.pid` に PID を書きます。停止要求は `data/stop_requested.flag` の作成で行います。

- Monitoring を起動（ポーリング）
  ```
  python -m kabusys.run_monitoring
  ```
  - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔（秒）を上書き（デフォルト 60 秒）。
  - 監視は常に本番 sqlite_path（`SQLITE_PATH`）を使用します（環境に依らず）。
  - 停止は `data/stop_requested.flag` を作成するか Ctrl+C。

- .env 作成ウィザード
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  ```

- Paper Trading 検証レポート（ツール）
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  - `--db` で DB パスを明示、なければ環境変数 `PAPER_TRADING_SQLITE_PATH`、それもなければ `data/paper_trading.db`。

---

## 環境変数（要点）

必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

主要（デフォルト値は省略）:
- KABUSYS_ENV: development | paper_trading | live
- DUCKDB_PATH: data/kabusys.duckdb
- SQLITE_PATH: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
- LOG_LEVEL: INFO
- OPENAI_API_KEY: OpenAI を利用する場合必須
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング秒数（整数）

その他:
- PID / flag 関連は Settings により `data/execution.pid`, `data/kill.flag` 等が参照されます。

---

## 動作上の注意点

- run_monitoring は監視用 DB（MonitoringDB）を常に本番の sqlite_path に対して初期化します。paper_trading として分離したい用途は各スクリプトの設定を確認してください。
- プロセス優先度を上げる処理（set_process_priority）は OS と権限に依存します。権限不足時は警告が出てスキップされます。
- OpenAI を使う機能は API 呼び出しの失敗／タイムアウトに対してリトライやフォールバックを組み込んでいますが、API キー未設定時は例外を投げます。
- `data/kill.flag` は KillSwitch によって作成され、ExecutionEngine の停止トリガになります。`KILL_FLAG_CLEAR_ON_START=1` を設定すると起動時に自動クリアしますが、本番では 0 を推奨します。
- ログはデフォルト `logs/<app_name>.log` に日次ローテーションで保存されます。ログディレクトリ作成に失敗した場合はコンソールのみの出力になります。

---

## ディレクトリ構成（主要ファイル）

src/kabusys/
- __init__.py
- config.py                — 環境変数 / Settings 管理
- config_setup.py          — .env 対話ウィザード
- validate_config.py       — 設定検証 CLI
- run_execution.py         — ExecutionEngine 起動スクリプト
- run_monitoring.py        — SystemMonitor ポーリング起動スクリプト

modules/
- execution/               — ExecutionEngine 関連（broker_factory, execution_engine, order_manager, order_repository, reconciler, risk_manager 等）※詳細は実装ファイル群
- monitoring/
  - monitoring_db.py       — SQLite テーブル初期化 / MonitoringDB
  - system_monitor.py
  - trade_monitor.py
  - risk_monitor.py
  - kill_switch.py
  - monitoring_engine.py
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
- tools/
  - paper_verification_report.py

utils/
- logging_setup.py         — 統一ログ設定（コンソール + 日次ファイルローテーション）
- process_priority.py      — プロセス優先度 / CPU affinity 設定ユーティリティ

その他:
- data/                    — デフォルト DB / PID / flag ファイル置き場（実行時に生成）
- logs/                    — ログ出力（デフォルト）

---

## 開発・運用メモ

- DB スキーマのマイグレーションは monitoring_db.init_monitoring_db 内で一部対応（列追加等）しています。
- research / ai モジュールは DuckDB の prices_daily / raw_financials / raw_news 等のテーブルを前提としています。テーブルが存在しない場合は該当機能がエラーになる場合があります（validate_config は YAML の存在確認に留まります）。
- コンポーネントはできるだけ副作用を避ける設計（純粋関数、外部アクセスの明確化）を意識しています。テスト時は外部 API 呼び出し箇所を patch して検証してください。
- ローカル開発では `KABUSYS_ENV=development` を使用し、発注が行われない状態で動作確認を行ってください。

---

もし README に追記してほしい点（例：具体的な ExecutionEngine の起動例、API の仕様、`config/*.yaml` のサンプル、依存パッケージの完全な requirements.txt など）があれば教えてください。必要に応じて追記・サンプルを作成します。