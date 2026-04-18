# KabuSys

日本株向け自動売買システムのコアライブラリ群と起動スクリプト群です。  
このリポジトリは、注文実行エンジン（ExecutionEngine）、監視（Monitoring）、ポートフォリオ構築、ファクター/リサーチ、AI を用いたニュース解析・レジーム判定、ユーティリティ群などを含みます。

バージョン: 0.1.0

---

目次
- プロジェクト概要
- 主な機能一覧
- 前提条件 / インストール
- 環境設定 (.env)
- セットアップ手順
- 使い方（主なコマンド）
- 重要な環境変数
- 動作の仕組み（概略）
- ディレクトリ構成

---

## プロジェクト概要

KabuSys は日本株の自動売買を想定したモジュール化されたシステムです。  
以下の責務がモジュール別に分離されています。

- Execution: ブローカークライアント、注文管理、リスク管理、発注エンジン
- Monitoring: システム状態・注文状態・リスク監視、Kill Switch（停止指令）
- Portfolio: 候補選定、重み計算、ポジションサイズ決定、セクター制約
- Research: ファクター計算（Momentum/Value/Volatility 等）、特徴量探索
- AI: ニュース NLP（OpenAI）を用いた銘柄スコアリング、レジーム判定
- Tools: ペーパートレード検証レポート生成 等
- Utils: ロギング設定、プロセス優先度設定、設定ロードなど
- Config: .env 自動ロード・設定検証・対話式セットアップ

設計方針としては、DB（SQLite / DuckDB）を使用したデータ永続化、LLM 呼び出しは安全に行う（リトライ/バリデーション）、本番/ペーパーの分離などが組み込まれています。

---

## 主な機能一覧

- ExecutionEngine（本番 / ペーパートレード両対応）
  - ブローカー抽象化（本番 / モック切替）
  - OrderManager / RiskManager / Reconciler 統合
- Monitoring
  - SystemMonitor（CPU/メモリ/Disk、データ鮮度、PID チェック）
  - TradeMonitor（滞留注文・約定異常等検出）
  - RiskMonitor（ドローダウン・ポジション上限監視）
  - KillSwitch（条件に応じた停止フラグ書き込み）
  - MonitoringEngine（監視ループ、アラート発行）
- Portfolio（純粋関数群）
  - 候補選定、等重/スコア加重、リスクベース sizing
  - セクター上限適用、レジーム乗数
- Research
  - ファクター計算（momentum/value/volatility）
  - 将来リターン計算、IC 計算、統計サマリー
- AI
  - news_nlp: OpenAI を用いた銘柄別センチメントスコア生成（ai_scores へ書込）
  - regime_detector: MA200 とマクロニュースで市場レジーム判定
- Tools
  - Paper Trading 検証レポート生成スクリプト
- Utils / 管理
  - ログ設定（stdout + 日次ローテーション）
  - プロセス優先度 / CPU affinity 設定
  - .env 対話式ウィザード、設定検証 CLI
  - Monitoring 用 SQLite 初期化・マイグレーション

---

## 前提条件 / インストール

推奨 Python バージョン: 3.10+

必要（想定）パッケージ例:
- duckdb
- psutil
- openai
- PyYAML（config 検証時の YAML パースに必要）
- （標準ライブラリの sqlite3 は組み込み）

インストール例（仮に requirements.txt を用意する場合）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install -U pip
# 個別インストール例
pip install duckdb psutil openai PyYAML
# あるいは requirements.txt があれば:
# pip install -r requirements.txt
```

ログディレクトリは既定で `logs/`。DB は既定で `data/` 配下に作成されます（自動生成されますが権限に注意）。

---

## 環境設定 (.env)

自動ロード:
- 起動時、プロジェクトルート（.git または pyproject.toml があるディレクトリ）を探索し `.env` / `.env.local` を読み込みます。
- OS 環境変数が優先され、`.env.local` は `.env` を上書きします。
- 自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

対話式ウィザード（.env の初期作成 / 更新）:
```bash
python -m kabusys.config_setup
```

設定検証:
```bash
python -m kabusys.validate_config
# 警告も失敗扱いにする場合:
python -m kabusys.validate_config --strict
```

必須環境変数（例）
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

主要な環境変数（抜粋）
- KABUSYS_ENV: development | paper_trading | live（既定: development）
- DUCKDB_PATH: DuckDB ファイルパス（既定: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（既定: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 DB（既定: data/paper_trading.db）
- OPENAI_API_KEY: OpenAI 使用時に必要（AI モジュール）
- LOG_LEVEL, LOG_DIR 等

PAPER_FILL_MODE（ペーパートレード時の約定動作）:
- instant | partial | never | reject（既定: instant）

監視関連:
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、既定 60）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（0/1）

---

## セットアップ手順（簡易）

1. リポジトリをクローンして、仮想環境を作成・有効化
2. 必要パッケージをインストール（duckdb, psutil, openai, PyYAML 等）
3. .env を作成（対話式ウィザード推奨）
   - `python -m kabusys.config_setup`
4. 設定検証:
   - `python -m kabusys.validate_config`
5. DB 初期化は起動スクリプトが行います（monitoring 用テーブルの作成等）。必要に応じて data/ ディレクトリの権限を確認。

---

## 使い方（主なコマンド）

- 実行エンジン（ExecutionEngine）起動:
  - 本番 / ペーパーの差は KABUSYS_ENV で切替
  ```bash
  python -m kabusys.run_execution
  ```

  - 起動フロー:
    1. ロギング初期化
    2. プロセス優先度を high に設定
    3. SQLite / DuckDB 接続（ペーパートレードなら専用 SQLite を使用）
    4. BrokerClient を生成し ExecutionEngine を起動（デーモンスレッド）
    5. 停止フラグ（data/stop_requested.flag）を監視して終了

- 監視ループ起動:
  ```bash
  python -m kabusys.run_monitoring
  ```
  - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔（秒）を上書きできます（既定 60）。
  - Monitoring は常に本番の sqlite_path（monitoring DB）を使用します。

- 設定ウィザード:
  ```bash
  python -m kabusys.config_setup
  ```

- 設定検証:
  ```bash
  python -m kabusys.validate_config
  ```

- Paper Trading 検証レポート:
  ```bash
  # デフォルトDBを使用
  python -m kabusys.tools.paper_verification_report

  # 期間指定
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

  # 別DB指定
  python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
  ```

- AI / レジーム判定（コードから呼び出す）
  - news_nlp.score_news(conn, target_date, api_key)
  - regime_detector.score_regime(conn, target_date, api_key)
  - OPENAI_API_KEY または api_key 引数を指定してください。

- テスト的に MonitoringEngine を 1 回だけ回す（ユニットテストやデバッグ用にモック注入可）
  - MonitoringEngine.run_once() を用いる

---

## 重要な稼働フラグ / ファイル

- data/kill.flag — KillSwitch が書き込む停止フラグ（ExecutionEngine に停止指令）
- data/stop_requested.flag — 実行スクリプト側が監視する停止要求フラグ（run_monitoring/run_execution）
- data/execution.pid — Execution の PID ファイル（run_execution にて使用）
- data/*.db, data/kabusys.duckdb — DB ファイルの既定パス

Kill Switch と停止挙動は冪等性を重視して設計されています（既存フラグは上書きしない等）。

---

## 動作の仕組み（概略）

- ExecutionEngine は注文処理・注文履歴管理・リスクチェックを行い、trade_logs / positions / dashboard 等を更新します。
- Monitoring 系は SystemMonitor / TradeMonitor / RiskMonitor を定期的に呼び、MonitoringDB（SQLite）にログを書き、必要に応じて KillSwitch を発動して停止指令を書き込みます。
- AI モジュールは DuckDB 上の raw_news 等を読み取り、OpenAI へプロンプト送信後に ai_scores 等へ書き込みます（JSON バリデーション・リトライ実装あり）。
- Research モジュールは DuckDB 接続を受け取り、価格テーブル等からファクターを計算して返す（副作用なしの純粋関数群）。

---

## ディレクトリ構成（抜粋）

（リポジトリルート / src/kabusys 以下）

- kabusys/
  - __init__.py
  - config.py                      — 環境変数 / Settings
  - config_setup.py                — .env 対話式ウィザード
  - validate_config.py             — 設定検証 CLI
  - run_execution.py               — ExecutionEngine 起動スクリプト
  - run_monitoring.py              — Monitoring 起動スクリプト
  - tools/
    - paper_verification_report.py  — ペーパートレード検証レポート
  - execution/
    - broker_factory.py
    - execution_engine.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - monitoring_engine.py
    - kill_switch.py
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
  - utils/
    - logging_setup.py
    - process_priority.py
  - data/                            — 実行時生成される想定（DB・pid・flag 等）

---

## 開発時の注意 / 補足

- Python 型ヒントで 3.10 の構文（|）を使用しているため、Python 3.10 以上を推奨します。
- OpenAI を利用するモジュールは API キー（OPENAI_API_KEY）を必要とします。呼び出しはリトライ・バリデーションを行いますが、API 利用料に注意してください。
- config/ 設定 YAML の検証には PyYAML が必要です。未インストール時は検証がスキップされます。
- ログは stdout にも出力され、かつ logs/<app>.log に日次ローテートで保存されます（logs ディレクトリに書き込めることを確認してください）。
- データベースに関するファイルパスは Settings で環境変数から上書きできます（例: SQLITE_PATH, DUCKDB_PATH, PAPER_TRADING_SQLITE_PATH）。

---

もし README に追加したい点（例: サンプル .env、実際の broker 実装の説明、CI / デプロイ手順、単体テストの実行方法など）があれば教えてください。必要に応じて追記・整備します。