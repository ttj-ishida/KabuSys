# KabuSys

日本株向け自動売買システムのコアライブラリ群と起動スクリプト群です。本リポジトリはトレード実行エンジン、監視/アラート、ポートフォリオ構築、ファクター計算、AI（ニュースNLP／レジーム判定）等のモジュールを含みます。

---

## 概要

- モジュール構成は Python パッケージ `kabusys` 配下に分割されています。
- 実行用エントリポイント：
  - ExecutionEngine 起動: `run_execution.py`
  - Monitoring（監視）起動: `run_monitoring.py`
- 設定は環境変数（`.env` / `.env.local`）で管理。対話式ウィザードや検証ツールを提供します。
- Paper trading（ペーパートレード）用に本番 DB と分離された専用 SQLite を使用可能。
- OpenAI を使ったニュースセンチメントやレジーム判定機能を備えています（APIキー必須）。

---

## 主な機能一覧

- Execution（発注）系
  - ExecutionEngine、OrderManager、RiskManager、Reconciler 等（依存注入でブローカークライアントを切替え可能）
  - KABUSYS_ENV=`paper_trading` 時は MockBrokerClient を使用し、`data/paper_trading.db` に記録

- Monitoring（監視）
  - SystemMonitor: CPU / メモリ / ディスク / データ鮮度 / 実行プロセス監視
  - TradeMonitor: 発注ログの滞留や約定異常検出（実装はモジュール内）
  - RiskMonitor: ドローダウン・ポジション上限などのリスク監視
  - KillSwitch: 条件に応じて `data/kill.flag` を書き込み ExecutionEngine に停止信号を送信
  - MonitoringEngine: 上記を束ねて定期ポーリング・アラート発行

- Portfolio（ポートフォリオ構築）
  - 候補選定、等配分／スコア重み配分、単元丸め、セクター上限適用、レジーム乗数等

- Research（調査/特徴量）
  - ファクター計算（Momentum / Volatility / Value）
  - 将来リターン計算、IC（スピアマン）計算、統計サマリ

- AI（OpenAI連携）
  - ニュースを LLM でスコアリング（`ai.news_nlp.score_news`）
  - マクロニュース＋ETF MA を使ったレジーム判定（`ai.regime_detector.score_regime`）
  - リトライ・バッチ処理・出力バリデーション等の実装

- ツール
  - 設定ウィザード: `.env` を対話的に作成 (`config_setup.py`)
  - 設定検証 CLI: `.env` / `config/*.yaml` を起動前にチェック (`validate_config.py`)
  - Paper Trading 検証レポート生成ツール (`tools.paper_verification_report`)

---

## 必要条件 / 事前準備

- 推奨 Python: 3.10+
  - （コードで型注釈の union 演算子 `|` を使用しているため）
- 主な依存パッケージ:
  - duckdb
  - psutil
  - openai (AI 機能を使う場合)
  - PyYAML（`validate_config.py` で YAML 検証を行う場合に推奨）
- インストール例（仮に requirements を手動で用意する場合）:
  - pip install duckdb psutil openai PyYAML

※プロジェクトに `pyproject.toml` や `requirements.txt` があればそちらを使用してください。

---

## セットアップ手順

1. リポジトリをクローンし、仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate（Windows: .venv\Scripts\activate）

2. 必要パッケージをインストール
   - pip install duckdb psutil openai PyYAML

3. .env を作成（対話式ウィザード推奨）
   - python -m kabusys.config_setup
     - 各項目を入力して `.env` を生成します。
   - もしくは `.env` を手動作成。必須環境変数:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD

4. 設定を検証
   - python -m kabusys.validate_config
   - 厳密モード（警告も失敗扱い）:
     - python -m kabusys.validate_config --strict

5. データディレクトリ作成（必要に応じて）
   - デフォルトの DB / ログ出力先は `data/` と `logs/`。
   - 例: mkdir -p data logs

---

## 環境変数（主なもの）

- KABUSYS_ENV: 実行環境（development / paper_trading / live） デフォルト: development
- JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH: DuckDB ファイル（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: paper_trading の約定モード（instant / partial / never / reject） デフォルト: instant
- LOG_LEVEL: ログレベル（DEBUG/INFO/…） デフォルト: INFO
- LOG_DIR: ログ保存ディレクトリ（デフォルト: logs/）
- OPENAI_API_KEY: OpenAI API キー（AI 機能を使用する場合に必須）
- MONITOR_POLL_INTERVAL: Monitoring のポーリング間隔（秒、デフォルト: 60）
- KILL_FLAG_PATH: kill.flag のパス（デフォルト: data/kill.flag）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag をクリアするか（0/1、デフォルト: 0）
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 自動 .env 読み込みを無効化（1 に設定すると自動ロードをスキップ）

注意: 自動 .env 読み込みはプロジェクトルートに `.env` / `.env.local` がある場合に行われます。OS 環境変数は上書きされません（`.env.local` は上書きモード）。

---

## 使い方（起動・実行例）

- 設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - ※ --strict オプションで警告もエラー扱い

- ExecutionEngine（発注エンジン）起動
  - 実行例:
    - python -m kabusys.run_execution
  - 補足:
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使い、`PAPER_TRADING_SQLITE_PATH`（デフォルト: `data/paper_trading.db`）に記録します。
    - 起動時に `data/stop_requested.flag` がある場合は起動をキャンセルします。
    - 実行中に `data/stop_requested.flag` を作成すると Engine を停止します。
    - ExecutionEngine は `data/execution.pid`（デフォルト）へ PID を管理します。

- Monitoring（監視）起動
  - 実行例:
    - python -m kabusys.run_monitoring
  - 補足:
    - デフォルトで MONITOR_POLL_INTERVAL=60 秒。環境変数で上書き可。
    - Monitoring は Settings.env に関係なく本番の `SQLITE_PATH`（監視 DB）を使用します（監視ログを一元化するため）。
    - 監視は system / trade / risk を順次チェックし、KillSwitch の判定やアラート通知を行います。
    - `data/stop_requested.flag` を監視しており、存在を検知すると監視ループを終了します。

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - デフォルト DB: `data/paper_trading.db`。`--db` オプションまたは環境変数 `PAPER_TRADING_SQLITE_PATH` で指定可。

- AI 機能（ニューススコア・レジーム判定）
  - OpenAI API キー (`OPENAI_API_KEY`) の設定が必要。
  - ニューススコア: `kabusys.ai.news_nlp.score_news(conn, target_date, api_key=None)`
  - レジーム判定: `kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)`

---

## ログ

- ログは標準出力（stdout）とファイル（`<LOG_DIR>/<app_name>.log`）に出力されます。
- デフォルトのログディレクトリ: `logs/`
- 日次ローテーション・30日分保持（TimedRotatingFileHandler）
- ログ設定は `kabusys.utils.logging_setup.setup_logging` で統一的に行われます。

---

## 停止 / Kill Switch

- 実行制御ファイル:
  - data/stop_requested.flag — スクリプト（monitoring, execution）が起動ループ／スレッドを終了するための汎用停止フラグ
  - data/kill.flag — KillSwitch が書き込む停止フラグ（ExecutionEngine に対する「安全装置」）
- `KILL_FLAG_CLEAR_ON_START=1` を設定すると起動時に kill.flag を自動でクリアします（注意: 本番環境では推奨しません）。

---

## ディレクトリ構成 (主要ファイルのみ抜粋)

- src/kabusys/
  - __init__.py
  - config.py — 環境変数 / Settings 管理（自動 .env ロード含む）
  - config_setup.py — 対話式 .env ウィザード
  - validate_config.py — 設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — Monitoring 起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート
  - execution/ — 実行エンジン関連（Engine, OrderManager, BrokerFactory など）
  - monitoring/
    - monitoring_db.py — SQLite テーブル初期化・永続化レイヤ
    - system_monitor.py, trade_monitor.py, risk_monitor.py, kill_switch.py, monitoring_engine.py, alert_manager.py
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
  - data/ (実行時に使用するファイル群・例)
    - monitoring.db (デフォルト SQLITE_PATH)
    - paper_trading.db (PAPER_TRADING_SQLITE_PATH)
    - kabusys.duckdb (DUCKDB_PATH)
    - kill.flag, stop_requested.flag, execution.pid

---

## 開発メモ / 注意点

- .env ファイルは絶対にリポジトリにコミットしないでください（`config_setup.py` のヘッダにも注意書きがあります）。
- Monitoring は監視 DB に対して常に「本番」sqlite を使用する設計です（環境にかかわらず）。Paper Trading のエンジンは paper_db を使用し分離されます。
- OpenAI を用いるモジュールは API 呼び出し時にリトライ／バックオフやレスポンスの厳密なバリデーションを行いますが、API キーの管理と利用に注意してください（コスト・レート制限）。
- `psutil` を用いた優先度設定 / CPU affinity は権限不足で失敗することがあります（警告ログを出して継続します）。
- DuckDB/SQLite に対する executemany の空リストバインドの扱いなど、互換性考慮がコード内にあります。DuckDB のバージョン差に注意してください。

---

## よく使うコマンドまとめ

- 対話式 .env 作成:
  - python -m kabusys.config_setup

- 設定検証:
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- Execution 起動:
  - python -m kabusys.run_execution

- Monitoring 起動:
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- Paper Trading 検証レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

---

必要であれば README にサンプル `.env`、systemd / supervisor の起動スクリプト例や Dockerfile 例、さらに各モジュール（ExecutionEngine の使い方やブローカープラグインの追加方法）を追記します。どの追加情報が必要か教えてください。