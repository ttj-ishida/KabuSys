# KabuSys

日本株向け自動売買 / 研究プラットフォーム（軽量版）

---

## プロジェクト概要

KabuSys は日本株の自動売買・バックテスト・リサーチを支援する Python 製モジュール群です。本リポジトリには以下の主要機能が実装されています。

- ExecutionEngine（発注エンジン）: 実口座 / ペーパートレードでの発注管理
- Monitoring（監視）: システム指標・注文ログの定期監視と Kill Switch
- Portfolio / Position sizing: 銘柄選定と株数決定ロジック（純粋関数）
- Research: ファクター計算・特徴量解析ユーティリティ（DuckDB を使用）
- AI モジュール: ニュース NLP によるセンチメント評価・市場レジーム判定（OpenAI）
- ユーティリティ: 環境設定ウィザード、設定検証、ログ設定など

設計方針の要点:
- 環境変数による設定管理（.env をサポート）
- DuckDB / SQLite をデータ層に使用（ローカルファイル）
- 本番・ペーパートレードの DB 分離設計
- OpenAI API 呼び出しは冗長性を考慮したリトライ実装

---

## 機能一覧

- run_execution.py: ExecutionEngine を起動（本番 / paper_trading 切替対応）
- run_monitoring.py: SystemMonitor のポーリングループを起動
- config_setup.py: 対話式 .env 生成ウィザード
- validate_config.py: .env / config/*.yaml の設定チェック CLI
- tools/paper_verification_report.py: ペーパートレード検証レポート生成
- portfolio/*: 候補選定、重み計算、リスク調整、ポジションサイズ決定
- research/*: ファクター計算（Momentum/Volatility/Value）、IC 計算など
- ai/*: ニュース NLP（score_news）、市場レジーム判定（score_regime）
- monitoring/*: DB 永続化層、System/Trade/Risk Monitor、Kill Switch、MonitoringEngine
- utils/*: ログ設定、プロセス優先度・CPU affinity 設定など

---

## 前提条件（推奨）

- Python 3.10+
- 必須パッケージ（代表例）:
  - duckdb
  - psutil
  - openai (AI 機能を使う場合)
  - pyyaml (config YAML 検証を行う場合)
- SQLite（Python 標準の sqlite3 を使用）
- ネットワーク接続（kabu API / OpenAI を使う場合）

（実際の依存関係はプロジェクトの requirements ファイルを参照してください）

---

## セットアップ手順

1. リポジトリをクローンして Python 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  （Windows は .venv\Scripts\activate）

2. 必要なパッケージをインストール（例）
   - pip install duckdb psutil openai pyyaml

3. 環境変数の初期作成（推奨: 対話ウィザード）
   - python -m kabusys.config_setup
     - 画面入力で .env を作成します（.env は絶対に Git にコミットしないでください）。

4. 設定検証
   - python -m kabusys.validate_config
   - 本番前は --strict を付けて警告も FAIL にする:
     - python -m kabusys.validate_config --strict

5. データディレクトリの準備（.env のデフォルトを使用する場合）
   - mkdir -p data logs

---

## 環境変数（主なもの・デフォルト）

（.env で設定可能。多くは config_setup.py の出力を参考にしてください）

- KABUSYS_ENV
  - 実行環境: development / paper_trading / live
  - デフォルト: development
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL
  - デフォルト: http://localhost:18080/kabusapi
- OPENAI_API_KEY
  - AI 機能利用時に必要
- DUCKDB_PATH
  - デフォルト: data/kabusys.duckdb
- SQLITE_PATH
  - 監視 DB（production 用）デフォルト: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH
  - ペーパートレード専用 DB（paper_trading 時使用）デフォルト: data/paper_trading.db
- LOG_LEVEL
  - デフォルト: INFO
- LOG_DIR
  - デフォルト: logs/
- KILL_FLAG_CLEAR_ON_START
  - 起動時に Kill Switch を自動クリアするか（0/1、本番は 0 推奨）
- PAPER_FILL_MODE
  - ペーパートレードの約定モード: instant / partial / never / reject
  - デフォルト: instant
- MONITOR_POLL_INTERVAL
  - run_monitoring のポーリング間隔（秒）。デフォルト: 60
  - 無効値（<=0）はデフォルトにフォールバック

---

## 使い方

基本的にはパッケージのモジュールとして起動します。

- 環境設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- ExecutionEngine 起動
  - python -m kabusys.run_execution
  - 注意:
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使い、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）へ記録します。
    - 起動時に data/stop_requested.flag が存在する場合は起動せずに終了します。
    - 実行中は data/execution.pid が作成されます。
    - 手動停止は Ctrl+C または monitoring の Kill Switch により data/kill.flag が書き込まれると停止処理が行われます。

- Monitoring 起動
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更可能（秒）。例:
    - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - 監視は本番 sqlite_path（Settings.sqlite_path）を使用します（KABUSYS_ENV に依存せず）。
  - 停止は Ctrl+C またはプロジェクトルート/data/stop_requested.flag の作成でループが終了します。

- Paper Trading 検証レポート（ツール）
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定: --db PATH（環境変数 PAPER_TRADING_SQLITE_PATH でも指定可能）

- AI 機能
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - OpenAI API キーは OPENAI_API_KEY 環境変数か関数引数で渡してください。
  - モデルは gpt-4o-mini を想定（実装内定義）。API 呼び出しはリトライ/フォールバック処理あり。

---

## 停止 / Kill Switch / フラグファイル

- 停止要求用フラグ（run_monitoring / run_execution が参照）
  - data/stop_requested.flag
    - 存在すると起動ループを検知して安全に終了します（手動停止用）。
- Kill Switch（ExecutionEngine 停止シグナル）
  - data/kill.flag
    - 監視コンポーネント（KillSwitch）が条件を満たすとこのファイルを書き込み、ExecutionEngine は停止します。
  - 設定により起動時に自動クリアされることがある（KILL_FLAG_CLEAR_ON_START=1）。

---

## ログ

- ログ出力は kabusys.utils.logging_setup.setup_logging を経由して設定されます。
- デフォルトはコンソール（stdout）と日次ローテートファイル（logs/<app_name>.log）です。
- ログディレクトリは LOG_DIR 環境変数または `logs/` を使用します。

---

## 主要ディレクトリ構成

リポジトリの主要モジュールと役割（抜粋）

- src/kabusys/
  - __init__.py
  - run_execution.py               — ExecutionEngine 起動スクリプト
  - run_monitoring.py              — Monitoring 起動スクリプト
  - config.py                      — Settings クラス（環境変数読み込み）
  - config_setup.py                — .env 対話式ウィザード
  - validate_config.py             — 設定検証 CLI
  - utils/
    - logging_setup.py             — ログ設定ユーティリティ
    - process_priority.py          — プロセス優先度 / CPU affinity
  - monitoring/
    - monitoring_db.py             — SQLite 監視用 DB 層
    - system_monitor.py            — システム・データ鮮度監視
    - trade_monitor.py             — 注文ログ監視（省略ファイル参照）
    - risk_monitor.py              — ドローダウン・ポジション上限監視
    - kill_switch.py               — Kill Switch 実装
    - monitoring_engine.py         — 複数モニタの統合ループ
    - alert_manager.py             — アラート送信（LINE など）※実装参照
  - execution/
    - execution_engine.py          — 発注エンジン本体（EngineConfig 等）
    - broker_factory.py            — ブローカークライアント生成（実ブローカ / Mock）
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
  - portfolio/
    - portfolio_builder.py         — 候補選定、重み計算
    - position_sizing.py           — 株数決定、aggregate cap
    - risk_adjustment.py           — セクターキャップ、レジーム乗数
  - research/
    - factor_research.py           — Momentum / Volatility / Value 計算（DuckDB）
    - feature_exploration.py       — 将来リターン、IC、統計サマリー
  - ai/
    - news_nlp.py                  — ニュース NLP（OpenAI）による ai_score 生成
    - regime_detector.py           — 市場レジーム判定（MA + マクロセンチメント）
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート生成

プロジェクトルートには `data/`（DB / PID / flag）と `logs/` ディレクトリを配置する想定です。

---

## 注意事項 / ベストプラクティス

- .env は絶対に Git にコミットしないでください（機密情報を含む）。
- 本番（KABUSYS_ENV=live）では KILL_FLAG_CLEAR_ON_START=0 を推奨します。
- AI モジュールは外部 API を使用するため、API レート・コスト・レスポンスの不確実性に注意してください。実行はテスト環境で十分検証してから行ってください。
- DuckDB / SQLite ファイルはファイルロックやバックアップに注意して運用してください。
- プロセス優先度設定（set_process_priority）は OS 権限に依存します。権限がない場合は警告が出て設定はスキップされます。

---

## 参考コマンドまとめ

- .env 作成:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict
- 実行（Monitoring）:
  - MONITOR_POLL_INTERVAL=60 python -m kabusys.run_monitoring
- 実行（Execution Engine）:
  - python -m kabusys.run_execution
- ペーパートレード検証レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

---

必要であれば、README に入れる具体的な .env サンプルや実行例（systemd unit / Dockerfile / docker-compose）も作成します。どの内容が必要か教えてください。