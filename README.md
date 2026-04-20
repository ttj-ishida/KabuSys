# KabuSys

日本株自動売買システム（KabuSys）のリポジトリ向け README（日本語）

この README はリポジトリ内のソースコードに基づき、セットアップ方法・起動方法・主要機能・ディレクトリ構成をまとめたものです。

※ 本ドキュメントはコードベースからの推定に基づき作成しています。実運用時は必ず設定ファイル（.env / config/*.yaml）や運用ポリシーを確認してください。

---

## プロジェクト概要

KabuSys は日本株の自動売買を目的としたシステムで、以下の主要機能を備えています。

- 注文管理・発注エンジン（ExecutionEngine）  
  - 実口座（live）とペーパートレード（paper_trading）で挙動を分離（ペーパートレードは専用 SQLite を使用）
- 監視（Monitoring）  
  - システム稼働状況、データ鮮度、注文の滞留・異常、リスク（ドローダウン・ポジション上限）をポーリング監視
  - Kill Switch（条件成立時にフラグを書き ExecutionEngine を停止）
- ポートフォリオ構築（候補選定・重み付け・ポジションサイズ計算・セクター制限 等）
- リサーチ / ファクター計算（DuckDB ベースでのファクター計算、IC計算など）
- AI モジュール（ニュースの NLP スコアリング / 市場レジーム判定（OpenAI））
- ツール（Paper Trading の検証レポート生成など）
- ログ管理ユーティリティ・プロセス優先度管理などのユーティリティ群

---

## 機能一覧（抜粋）

- config_setup: 対話式に .env を作成・更新するウィザード
- validate_config: .env と config/*.yaml の事前検証ツール
- run_execution: ExecutionEngine を起動（KABUSYS_ENV により本番 or ペーパー切替）
- run_monitoring: SystemMonitor のポーリングループを起動（MONITOR_POLL_INTERVAL により間隔を設定可能）
- monitoring: system_status / trade_logs / risk_logs / positions / dashboard テーブルによる監視ログ永続化（SQLite）
- portfolio: 候補選定／重み計算／ポジションサイズ計算／リスク調整（純粋関数）
- research: ファクター計算（momentum, value, volatility 等）と特徴量探索ユーティリティ
- ai.news_nlp: raw_news を LLM（OpenAI）でスコアリングし ai_scores に書き込む
- ai.regime_detector: ma200 とマクロニュースの LLM 評価を合成して市場レジーム判定
- tools.paper_verification_report: ペーパートレード DB を基に検証レポートを出力

---

## 前提（依存ライブラリ）

主な依存（コード参照に基づく、バージョンは適宜指定してください）:

- Python 3.9+
- duckdb
- psutil
- openai
- sqlite3（標準）
- PyYAML（config YAML の検証に利用、任意）

パッケージは requirements.txt 等を用意している場合はそちらを参照してください。

---

## 環境変数（主要項目）

コード内で参照される主要な環境変数とデフォルト値（重要なもののみ抜粋）:

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
- OPENAI_API_KEY (AI 機能利用時に必要)
- KABUSYS_ENV: execution モード（development / paper_trading / live。デフォルト: development）
- DUCKDB_PATH: DuckDB ファイル（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL: ログレベル（デフォルト: INFO）
- LOG_DIR: ログ保存先ディレクトリ（デフォルト: logs）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（0/1。デフォルト: 0）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト: 60）
- PAPER_FILL_MODE: ペーパートレードの約定モード（instant | partial | never | reject）

.env の自動読み込み:
- プロジェクトルートにある `.env` / `.env.local` は自動で読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。

---

## セットアップ手順（クイックスタート）

1. リポジトリをクローンして作業ディレクトリへ移動
   - git clone ... && cd <repo>

2. Python 仮想環境作成・有効化、依存ライブラリをインストール
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
   - pip install -r requirements.txt  （requirements.txt が無ければ個別に duckdb, psutil, openai, pyyaml 等を pip install）

3. .env を作成
   - 対話式ウィザードを使う（推奨）:
     - python -m kabusys.config_setup
   - または手動で .env を作成（注意: .env は絶対に Git にコミットしない）

   最低限設定する必須項目:
   - JQUANTS_REFRESH_TOKEN=
   - KABU_API_PASSWORD=
   - （必要時）OPENAI_API_KEY=
   - KABUSYS_ENV=development など

4. 設定検証（起動前チェック）
   - python -m kabusys.validate_config
   - 問題があれば出力に従って修正。--strict を付けると警告も失敗扱いになります:
     - python -m kabusys.validate_config --strict

5. データ・ログディレクトリ等の作成は通常自動で行われますが、手動で作る場合:
   - mkdir -p data logs

---

## 実行方法（代表的なコマンド）

- ExecutionEngine を起動（本番/ペーパーは KABUSYS_ENV で切替）:
  - python -m kabusys.run_execution

  特記事項:
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用して data/paper_trading.db に記録します（本番 DB と分離）。
  - 起動前に data/stop_requested.flag が存在すると起動を行わず終了します。
  - 実行中に停止させたい場合は data/stop_requested.flag を作成してください（監視側や手動で設定する運用が想定されています）。

- Monitoring（SystemMonitor ポーリング）を起動:
  - python -m kabusys.run_monitoring
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL（秒）で上書き可能（デフォルト 60 秒）:
    - export MONITOR_POLL_INTERVAL=30

  特記事項:
  - 監視プロセスは Settings.sqlite_path を使って監視ログを記録します（監視は環境に依存せず本番 sqlite_path を使用する設計）。
  - 監視は data/stop_requested.flag を検知して終了します。

- Paper Trading 検証レポート出力:
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
  - 環境変数 PAPER_TRADING_SQLITE_PATH でも DB を指定可能（コマンドライン優先）

- AI モジュールの実行（例: ニューススコアリング）
  - モジュールはプログラムから呼び出して使用する想定です。OpenAI API キーが必要です（環境変数 OPENAI_API_KEY）。
  - 例（Python スクリプト内）:
    - from kabusys.ai.news_nlp import score_news
    - score_news(conn, target_date, api_key=None)  # api_key 指定がない場合は env OPENAI_API_KEY を参照

---

## 停止・Kill Switch について

- 停止フラグ:
  - data/stop_requested.flag — run_monitoring / run_execution がポーリングで検知する停止フラグ。存在すると起動しない／実行中は停止処理を行います（スクリプト内で参照）。
- Kill Switch:
  - data/kill.flag — KillSwitch が書き込むことで ExecutionEngine に停止シグナルを送る仕組み。理由の文字列がファイルに書き込まれます。
  - Settings.kill_flag_clear_on_start=1 を設定すると起動時に自動クリアされますが、本番では 0 を推奨します。

---

## ログ

- 共通ログ設定ユーティリティ: kabusys.utils.logging_setup.setup_logging
  - stdout（StreamHandler）と日次ローテートされたファイルログ（TimedRotatingFileHandler）を root ロガーに設定します。
  - デフォルトログディレクトリ: logs/
  - ログファイル名: <app_name>.log（例: execution.log, monitoring.log）
  - LOG_LEVEL / LOG_DIR 環境変数で上書き可能

---

## 主要設定ファイル / データベース

- .env: 環境変数定義（必須項目あり）
- config/*.yaml: 各種構成ファイル（存在しない場合は警告、validate_config で検証）
- data/kabusys.duckdb（デフォルト: data/kabusys.duckdb）: 分析用 DuckDB
- data/monitoring.db（デフォルト）: 監視ログ用 SQLite
- data/paper_trading.db（ペーパートレード用 SQLite、KABUSYS_ENV=paper_trading 時に使用）

---

## ディレクトリ構成（抜粋）

リポジトリの主要なソース構成（src/kabusys 以下）:

- kabusys/
  - __init__.py
  - config.py                — 環境変数 / 設定の管理
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor 起動スクリプト
  - utils/
    - logging_setup.py       — ログ設定ユーティリティ
    - process_priority.py    — プロセス優先度 / CPU affinity ユーティリティ
  - monitoring/
    - monitoring_db.py       — Monitoring DB（SQLite）初期化 & ラッパー
    - system_monitor.py      — システム・データ鮮度監視
    - trade_monitor.py       — 注文監視（滞留・約定異常等） ※実装ファイルあり
    - risk_monitor.py        — ドローダウン・ポジション上限監視
    - kill_switch.py         — Kill Switch 書き込みロジック
    - monitoring_engine.py   — 各 Monitor を束ねるエンジン
    - alert_manager.py       — アラート送信（LINE 等） ※実装ファイルあり
  - execution/
    - execution_engine.py    — ExecutionEngine 本体（ファイル存在）
    - broker_factory.py      — ブローカークライアント生成（Mock 対応）
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
    - news_nlp.py            — ニュース NLP スコアリング（OpenAI 利用）
    - regime_detector.py     — 市場レジーム判定（ma200 + LLM）
  - tools/
    - paper_verification_report.py

（上記は提供されたコードファイルを反映した抜粋です。詳細はソースツリーを参照してください）

---

## 開発・運用時の注意点 / トラブルシューティング

- .env の自動読み込み:
  - プロジェクトルート（.git または pyproject.toml を検出）を基に .env を自動読み込みします。自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- config/*.yaml の検証:
  - validate_config は PyYAML がインストールされていないと YAML 検証をスキップします（警告）。
- DuckDB / SQLite:
  - DuckDB は分析用（prices_daily / raw_financials 等）。Monitoring は SQLite（軽量永続化）を使用します。
- OpenAI API:
  - AI 機能を使用するには OPENAI_API_KEY が必要です。API のレート制限やエラーはリトライ（指数バックオフ）で耐性を持たせていますが、費用とレート制限に注意してください。
- 権限関連:
  - プロセス優先度変更（psutil による nice / Windows priority）や CPU affinity は権限が必要な場合があります。失敗時は警告を出してスキップします。
- 停止フラグ / PID:
  - data/execution.pid などの PID ファイル・停止フラグは運用スクリプトや自動化（systemd / cron / コンテナの停止ハンドリング）で扱えるよう設計されています。
- ログディレクトリ作成に失敗する場合:
  - ログは stdout にも出力されるため、ログディレクトリの作成に失敗してもコンソールログで状況把握できます。

---

## よくある運用ワークフロー（例）

1. 開発環境での初期化
   - python -m kabusys.config_setup
   - python -m kabusys.validate_config

2. ペーパートレードでの動作確認
   - export KABUSYS_ENV=paper_trading
   - python -m kabusys.run_execution
   - 別ターミナルで python -m kabusys.run_monitoring

3. 検証レポート作成
   - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-10

4. 本番移行前チェック
   - .env の本番用値（KABUSYS_ENV=live）をセット
   - OPENAI_API_KEY 等の確認
   - python -m kabusys.validate_config --strict

---

必要であれば README に追加したい情報（例: サンプル .env、systemd ユニットファイル例、CI/CD の設定、詳細な API 使用例など）を教えてください。必要に応じて追記します。