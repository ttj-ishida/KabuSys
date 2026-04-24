# KabuSys

日本株向け自動売買システムのコードベース README（日本語）

---

## プロジェクト概要

KabuSys は日本株の自動売買／研究／モニタリングを行うためのモジュール群です。  
主な役割は以下の通りです。

- データ集計・研究（DuckDB ベース）
- シグナル生成・ポートフォリオ構築（純関数群）
- ExecutionEngine による発注処理（kabuステーション / Mock ブローカー）
- 監視（System / Trade / Risk）と Kill Switch（停止フラグによる安全停止）
- Paper Trading の検証レポート生成
- ニュース NLP（OpenAI）を用いた銘柄センチメント算出、レジーム判定

この README はコードベースに含まれる主要機能・セットアップ・使い方・ディレクトリ構成をまとめたものです。

---

## 機能一覧

- 設定管理
  - .env 読み込み（自動ロード）、Settings クラスによる環境変数アクセス
  - 対話式設定ウィザード（`kabusys.config_setup`）
  - 起動前検証 CLI（`kabusys.validate_config`）

- 実行・監視（起動スクリプト）
  - ExecutionEngine 起動スクリプト（`run_execution.py`）
    - `KABUSYS_ENV=paper_trading` の場合は MockBrokerClient を使用し、paper_trading 用 DB に記録
  - Monitoring（`run_monitoring.py`）
    - SystemMonitor のポーリングループ（MONITOR_POLL_INTERVAL による間隔指定可）

- 監視コンポーネント
  - SystemMonitor: CPU/メモリ/ディスク、プロセス PID、データ鮮度を監視
  - TradeMonitor: 発注／約定ログの監視（滞留注文・異常約定など）
  - RiskMonitor: ドローダウン・ポジション上限の検出とリスクログ記録
  - KillSwitch: 条件に応じて `data/kill.flag` を書き込み、ExecutionEngine に停止シグナルを送る
  - MonitoringEngine: 上記を束ねてポーリング、アラート通知呼び出し

- ポートフォリオ構築（純関数群）
  - 候補選定・重み計算（等配分・スコア加重）
  - セクター上限の適用
  - ポジションサイズ算出（リスクベース、等配分、スコア配分）

- 研究（Research）
  - ファクター計算（Momentum / Volatility / Value）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー

- AI（OpenAI）
  - ニュース NLP（news_nlp）：銘柄ごとのセンチメントを LLM で算出して ai_scores に格納
  - レジーム判定（regime_detector）：ETF の MA とマクロニュースのセンチメントを合成して市場レジーム判定

- ユーティリティ
  - ログ設定ユーティリティ（console + 日次ローテートファイル）
  - プロセス優先度/CPU affinity 設定ユーティリティ

- ツール
  - Paper Trading 検証レポート生成スクリプト（`tools.paper_verification_report`）

---

## 要件（推奨）

- Python 3.10+
- 推奨パッケージ（主要な依存）
  - duckdb
  - psutil
  - openai
  - PyYAML（config 検証時のみ任意）
- 実行環境により追加パッケージが必要になることがあります（requirements.txt がある場合はそれを利用してください）。

インストール例（最低限）:
```
pip install duckdb psutil openai PyYAML
```

---

## セットアップ手順

1. リポジトリをクローン／取得

2. Python 仮想環境を作成・有効化（任意）
   ```
   python -m venv .venv
   source .venv/bin/activate  # POSIX
   .venv\Scripts\activate     # Windows
   ```

3. 依存パッケージをインストール
   ```
   pip install duckdb psutil openai PyYAML
   ```

4. .env の作成（対話ウィザード）
   ```
   python -m kabusys.config_setup
   ```
   - ウィザードは J-Quants トークン、kabu API パスワード、DB パス等を対話的に作成します。
   - 生成された .env は絶対に Git にコミットしないでください。

5. 設定検証（起動前チェック）
   ```
   python -m kabusys.validate_config
   ```
   - `--strict` を付けると警告も失敗扱いになります。

6. データディレクトリの準備（.env でデフォルト path を使用する場合）
   - デフォルトでは `data/`、`logs/` ディレクトリが使われます。必要に応じて作成されます。

---

## 主要な環境変数（抜粋）

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants API 用（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）

運用関連:
- KABUSYS_ENV — 実行環境（development / paper_trading / live）、デフォルト: development
- LOG_LEVEL — ログレベル（DEBUG/INFO/...）, デフォルト: INFO
- LOG_DIR — ログ保存ディレクトリ（デフォルト: logs/）

DB 関連:
- DUCKDB_PATH — DuckDB ファイル（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）

AI（OpenAI）:
- OPENAI_API_KEY — OpenAI API キー（news_nlp / regime_detector などで使用）

その他:
- MONITOR_POLL_INTERVAL — Monitoring のポーリング間隔（秒、デフォルト: 60）
- PAPER_FILL_MODE — Paper Trading の約定モード（instant / partial / never / reject）
- KILL_FLAG_CLEAR_ON_START — Execution 起動時に kill.flag を自動クリアするか（"1" で有効、デフォルト "0" 推奨）

---

## 使い方（コマンド）

- 対話式 .env 作成
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- ExecutionEngine の起動
  ```
  python -m kabusys.run_execution
  ```
  - KABUSYS_ENV=paper_trading の場合は MockBroker を用い、paper_trading DB に記録します。
  - 起動時に `data/stop_requested.flag` が存在すると起動を中止します。
  - Execution は起動時に優先度を "high" に設定し、PID ファイル（デフォルト: data/execution.pid）を利用します。

- Monitoring（ポーリングループ）の起動
  ```
  python -m kabusys.run_monitoring
  ```
  - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL`（秒）で上書き可（デフォルト 60 秒）。
  - 監視は本番 sqlite_path（Settings.sqlite_path）を使用してログを永続化します。
  - 停止は `data/stop_requested.flag` を作成するか KeyboardInterrupt（Ctrl+C）。

- Paper Trading 検証レポート生成
  ```
  python -m kabusys.tools.paper_verification_report
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  - `--db` オプションまたは環境変数 `PAPER_TRADING_SQLITE_PATH` で DB パスを指定できます。

- AI 系モジュールの呼び出し（プログラムから）
  - news_nlp.score_news(conn, target_date, api_key=None)
  - regime_detector.score_regime(conn, target_date, api_key=None)
  - これらは DuckDB 接続オブジェクトと日付を受け取り、OpenAI API キー（引数または環境変数）を使用します。

---

## 停止・Kill Switch

- ExecutionEngine と Monitoring の両スクリプトはプロジェクトルート下の `data/stop_requested.flag` を監視し、存在すれば安全に終了します。
- Kill Switch（リスク条件により Execution を停止する）は `data/kill.flag` を書き込みます。Execution 側は Settings.kill_flag_path（デフォルト: data/kill.flag）を参照して動作する設計です。
- 実行前に `KILL_FLAG_CLEAR_ON_START=1` を設定すると起動時に自動で kill.flag をクリアしますが、本番では推奨されません。

---

## ログ・DB の場所（デフォルト）

- ログディレクトリ: logs/
  - ファイル名はアプリ名（例: execution.log, monitoring.log）で日次ローテートされます。
- DuckDB: data/kabusys.duckdb（環境変数 DUCKDB_PATH で変更可）
- 監視（SQLite）: data/monitoring.db（環境変数 SQLITE_PATH で変更可）
- Paper Trading DB: data/paper_trading.db（PAPER_TRADING_SQLITE_PATH）

ログ設定は `kabusys.utils.logging_setup.setup_logging` で統一的に行われます。

---

## 重要な設計・実装ノート

- 設定自動ロードはプロジェクトルート（.git または pyproject.toml が存在するディレクトリ）を起点に `.env` / `.env.local` を読み込みます。自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- Monitoring の初期化は `monitoring_db.init_monitoring_db()` によりテーブル作成・マイグレーションを行います（冪等）。
- ExecutionEngine は paper_trading と live を明確に分離し、paper_trading は別 SQLite を使用します。
- AI 呼び出し（OpenAI）はリトライやレスポンス検証を行い、失敗時は安全なフォールバック（例: スコア 0.0）を採用します。
- process priority の設定や CPU affinity は os/権限に依存し、失敗時はログ警告を出してスキップします。

---

## ディレクトリ構成（抜粋）

以下はリポジトリ内の主要ファイル／モジュールの一覧（提供されたコードベースに基づく抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                   — 環境変数・Settings
  - config_setup.py             — .env 対話ウィザード
  - validate_config.py          — 設定検証 CLI
  - run_execution.py            — ExecutionEngine 起動スクリプト
  - run_monitoring.py           — Monitoring 起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py
  - ai/
    - __init__.py
    - news_nlp.py               — ニュース NLP / OpenAI 呼び出し
    - regime_detector.py        — レジーム判定（MA + マクロ NLP）
  - monitoring/
    - monitoring_db.py          — SQLite 永続化層
    - monitoring_engine.py
    - system_monitor.py
    - trade_monitor.py          — （存在: 参照あり。実装は省略）
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py          — （存在: 参照あり。実装は省略）
  - execution/
    - execution_engine.py       — 実行エンジン（参照）
    - broker_factory.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
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

（実際のリポジトリではさらに data/、config/、scripts/ 等のディレクトリが存在する可能性があります）

---

## 参考コマンドまとめ

- .env を作る: python -m kabusys.config_setup
- 設定検証: python -m kabusys.validate_config [--strict]
- 実行エンジン起動: python -m kabusys.run_execution
- 監視起動: python -m kabusys.run_monitoring
- Paper 検証レポート: python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]

---

必要であれば README にサンプル .env テンプレート（.env.example）や systemd 用のユニットファイル例、Dockerfile や docker-compose のサンプルを追記できます。どの情報を追加したいか教えてください。