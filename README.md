# KabuSys

日本株自動売買システムの一部（ライブラリ + 起動スクリプト群）。  
このリポジトリは、シグナル生成・ポートフォリオ構築・発注/実行エンジン・監視・AI補助（ニュース NLP / レジーム判定）などを含むモジュール群を提供します。

---

## プロジェクト概要

- システム全体の設計はモジュール化されており、以下の主要機能を持ちます:
  - 戦略（ファクター計算、特徴量解析）
  - ポートフォリオ構築（候補選定・重み付け・株数算出）
  - 発注/実行エンジン（ExecutionEngine, BrokerClientFactory 等）
  - 監視（SystemMonitor / TradeMonitor / RiskMonitor / KillSwitch）
  - 補助ツール（環境設定ウィザード、設定検証、Paper Trading レポート生成）
  - AI モジュール（ニュースセンチメント評価、レジーム判定） — OpenAI API を利用

- 設定は環境変数（`.env` ファイル）で管理。`.env` と `.env.local` は自動読み込みされます（ただし `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可）。

- DB:
  - DuckDB: 分析 / 研究用（デフォルト `data/kabusys.duckdb`）
  - SQLite: 監視・発注ログ（デフォルト `data/monitoring.db`）
  - Paper Trading では発注用 SQLite を分離（`data/paper_trading.db`）

---

## 機能一覧

- 起動スクリプト
  - `run_execution.py` — ExecutionEngine を起動（`KABUSYS_ENV=paper_trading` のときは MockBrokerClient を使用）
  - `run_monitoring.py` — SystemMonitor をポーリング起動（監視ログ収集・KillSwitch 判定など）

- 設定管理 / ユーティリティ
  - `config_setup.py` — 対話式で `.env` を生成/更新するウィザード
  - `validate_config.py` — .env および `config/*.yaml` の簡易検証 CLI

- 監視関連
  - `monitoring/monitoring_db.py` — 監視用 SQLite テーブルの初期化／読み書き
  - `monitoring/system_monitor.py` — システム指標（CPU/Memory/Disk/Data Freshness / Execution プロセス監視）
  - `monitoring/risk_monitor.py` — ドローダウン / ポジション上限監視
  - `monitoring/kill_switch.py` — 条件に応じて `data/kill.flag` を書き込み Execution を停止させる
  - `monitoring/monitoring_engine.py` — 各 Monitor を束ねるエンジン

- ポートフォリオ構築
  - `portfolio/portfolio_builder.py` — 候補選定・重み計算
  - `portfolio/position_sizing.py` — 株数／投資額算出（リスクベース等）
  - `portfolio/risk_adjustment.py` — セクター上限・レジーム乗数

- 研究・ファクター計算（DuckDB を参照）
  - `research/factor_research.py` — Momentum / Volatility / Value ファクター
  - `research/feature_exploration.py` — 将来リターン、IC、統計サマリ

- AI（OpenAI）
  - `ai/news_nlp.py` — ニュースを LLM で評価し `ai_scores` に保存
  - `ai/regime_detector.py` — マクロセンチメント + ETF MA 乖離で日次レジーム判定

- ツール
  - `tools/paper_verification_report.py` — Paper Trading の検証レポート生成

- ログ設定・プロセス優先度
  - `utils/logging_setup.py` — 統一的なロギング（stdout + 日次ローテートファイル）
  - `utils/process_priority.py` — Windows/Linux 両対応で優先度（nice / priority class）設定

---

## セットアップ手順

前提
- Python 3.10 以上（`|` 型合成等を使用）
- 基本的な OS ユーティリティ（sqlite3 は標準ライブラリ）

推奨パッケージ（最低限）
- duckdb
- psutil
- openai
- PyYAML（`validate_config` の YAML 検証用。なくても動作します）

例（venv を使用したセットアップ）
1. 仮想環境作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. 必要パッケージをインストール
   - pip install duckdb psutil openai pyyaml

3. `.env` の作成
   - 対話式で作る: python -m kabusys.config_setup
   - または `./.env.example` を参考に手動作成（リポジトリに example がある場合）

4. 設定検証（任意だが推奨）
   - python -m kabusys.validate_config
   - 厳格モード: python -m kabusys.validate_config --strict

注意:
- `.env` は機密情報（APIキー等）を含むため絶対に Git にコミットしないでください。
- `.env` の自動読み込みは `config.py` に実装されています。自動読み込みを無効にしたい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## 使い方

基本的な実行例（プロジェクトルートから実行）:

- 環境設定ウィザード（.env を生成/更新）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- ExecutionEngine を起動
  - python -m kabusys.run_execution
  - 挙動:
    - `KABUSYS_ENV=paper_trading` の場合は MockBrokerClient を使用し、Paper Trading 用 DB（デフォルト `data/paper_trading.db`）を使います。本番 DB とは完全分離されます。
    - 起動時に `data/stop_requested.flag` が存在すると起動せず終了します。
    - 実行中に `data/stop_requested.flag` を作成するとエンジンを停止します。
    - PID ファイルはデフォルト `data/execution.pid` に書かれます（設定で変更可能）。

- Monitoring を起動（SystemMonitor のポーリング）
  - python -m kabusys.run_monitoring
  - オプション:
    - ポーリング間隔を変更するには環境変数 `MONITOR_POLL_INTERVAL`（秒）を設定（デフォルト 60）。
  - 挙動:
    - Monitoring は `Settings.sqlite_path`（デフォルト `data/monitoring.db`）を使用し、環境（KABUSYS_ENV）に依らず本番 sqlite を参照します。
    - 停止は `data/stop_requested.flag` を作成することで行う。
    - KillSwitch の判定により `data/kill.flag` が書き込まれると ExecutionEngine に停止シグナルが送れます（Execution 側は `KILL_FLAG_PATH` を参照）。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - デフォルト DB: 環境変数 `PAPER_TRADING_SQLITE_PATH` または `data/paper_trading.db`

- AI 機能
  - `kabusys.ai.score_news(conn, target_date, api_key=None)` — OpenAI API キーが必要（引数 or `OPENAI_API_KEY`）。
  - `kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)` — 同様に OpenAI API キーが必要。
  - API 呼び出し回数に注意。失敗時はフェイルセーフで継続する設計（ゼロフォールバック等）。

ログ
- ログは stdout とファイル（`logs/<app_name>.log`）に出力されます。`LOG_DIR` / `LOG_LEVEL` で変更可能。
- `setup_logging(app_name="execution")` のように、各起動スクリプトはログを初期化します。

停止・Kill
- 強制的に ExecutionEngine を停止させたい場合は `data/kill.flag` を作成（`KillSwitch` が作成する挙動に準拠）。`Settings.kill_flag_path` でパスを変更可能。
- 実行停止のための共通フラグ（管理用）: `data/stop_requested.flag`（両起動スクリプトでチェックされます）。

---

## 主要環境変数（主なもの）

- 基本
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
  - LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL
  - LOG_DIR: ログ出力ディレクトリ（デフォルト: logs/）

- API キー / 外部サービス
  - JQUANTS_REFRESH_TOKEN（必須）
  - KABU_API_PASSWORD（必須）
  - OPENAI_API_KEY（AI 機能を使う場合必須）
  - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID（任意: アラート用）

- DB パス
  - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH（監視用、デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH（paper_trading 用 SQLite、デフォルト: data/paper_trading.db）

- Monitoring / Execution
  - MONITOR_POLL_INTERVAL（秒、デフォルト: 60）
  - PID_FILE_PATH（デフォルト: data/execution.pid）
  - KILL_FLAG_PATH（デフォルト: data/kill.flag）
  - KILL_FLAG_CLEAR_ON_START（"1" で起動時に kill.flag を自動クリア）

- Paper Trading 動作
  - PAPER_FILL_MODE: instant | partial | never | reject（デフォルト: instant）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD: 1 を設定すると .env 自動ロードを無効化

---

## ディレクトリ構成（抜粋）

- src/kabusys/
  - __init__.py
  - config.py — 環境変数 / 設定読み込みロジック
  - config_setup.py — .env ウィザード
  - validate_config.py — 設定検証 CLI
  - run_execution.py — Execution の起動スクリプト
  - run_monitoring.py — Monitoring の起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート
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
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - (TradeMonitor 等のモジュールが存在する想定)
  - utils/
    - logging_setup.py
    - process_priority.py

注意: 上記はリポジトリ内の主なファイル一覧です。実際の配布ではさらに `execution/`, `data/`, `strategy/` 等のサブパッケージが含まれる場合があります。

---

## 開発上の注意点 / 補足

- DB 初期化:
  - `monitoring_db.init_monitoring_db(conn)` は冪等でテーブル作成と必要なマイグレーション（例: `latency_ms`, `peak_value` カラム追加）を行います。`run_execution` / `run_monitoring` は起動時にこれを呼びます。

- Paper Trading と本番 DB の分離:
  - `run_execution` は `KABUSYS_ENV=paper_trading` の場合、`Settings.paper_sqlite_path`（デフォルト `data/paper_trading.db`）を使用します。これにより本番の監視 DB と発注ログが混ざることを防ぎます。

- ロギング:
  - `utils.logging_setup.setup_logging` は stdout と日次ロールのファイルハンドラを設定します。ログディレクトリ作成に失敗した場合はファイル出力をスキップして stdout のみで継続します。

- プロセス優先度:
  - 起動スクリプトは最初に `set_process_priority("high")` を呼びます。権限によっては失敗して警告がログ出力されます（処理継続）。

- AI（OpenAI）関連:
  - LLM 呼び出しは堅牢性を重視し、429 やネットワークエラー、5xx を指数バックオフでリトライする実装になっています。API キーは環境変数 `OPENAI_API_KEY` で指定するか、関数引数で渡します。
  - レスポンスのバリデーションを厳格に行い、部分失敗時も既存のスコアを保護するよう DB 書き込みを設計しています。

---

必要であれば、README にサンプルの `.env.example` 内容、詳細な起動オプション（ExecutionEngine の config や Broker の設定例）、および各モジュールの API 使用例（簡単なコードスニペット）を追加します。どの情報を優先して追加しますか？