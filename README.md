# KabuSys

日本株向け自動売買 / リサーチ基盤のモジュール群です。  
このリポジトリには、実行エンジン、監視・アラート、ポートフォリオ構築、リサーチ、AI（ニュースNLP / レジーム判定）等のコンポーネントが含まれます。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は以下の機能を持つコンポーネント群から構成されたシステムです。

- ExecutionEngine — 注文発行・リスク管理・再整合の実行エンジン（本番 / ペーパートレード対応）
- Monitoring — システム状態、注文状態、リスク監視と Kill Switch（停止フラグ）管理
- Portfolio construction — 候補選定、重み計算、ポジションサイズ算出、セクター制約・レジーム調整
- Research — ファクター計算（モメンタム／バリュー／ボラティリティ等）、特徴量探索、IC計算
- AI — ニュースセンチメント（OpenAI）を用いたスコアリング、マクロニュースを使った市場レジーム判定
- Tools — ペーパートレード検証レポート生成などユーティリティ

設計方針の要点:
- データ永続化には DuckDB と SQLite（監視ログ）を使用
- 環境分離: KABUSYS_ENV により development / paper_trading / live を切替
- 本番用プロセスは PID/flag ファイルで制御（data/*.pid, data/stop_requested.flag, data/kill.flag）
- OpenAI を利用する機能は API キーを要求。失敗時はフェイルセーフで継続する実装

---

## 主な機能一覧

- 実行エンジン起動: python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は MockBroker を使い data/paper_trading.db に記録
  - プロセス優先度を高く設定、PID ファイル生成、stop フラグ検知で停止
- 監視ループ起動: python -m kabusys.run_monitoring
  - SystemMonitor を定期実行して system_status 等を記録、kill.flag の作成/評価は KillSwitch 等で実施
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）
- 設定ウィザード: python -m kabusys.config_setup
  - .env の対話的生成・更新
- 設定検証: python -m kabusys.validate_config [--strict]
  - .env および config/*.yaml（存在すれば）をチェック
- Paper Trading 検証レポート: python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
- AI:
  - kabusys.ai.score_news(target_date) — raw_news を元に OpenAI で銘柄ごとのセンチメントを ai_scores テーブルへ書込
  - kabusys.ai.regime_detector.score_regime(target_date) — マクロニュース + ETF MA を元に market_regime を判定・書込
- ポートフォリオ関連:
  - 候補選定、等配分 / スコア配分、リスクベースのポジションサイズ計算（lot 100 丸め等）
- Monitoring DB API（MonitoringDB）: system_status, trade_logs, positions, risk_logs, dashboard の作成・操作ユーティリティ

---

## セットアップ手順

前提:
- Python 3.9+（パッケージが依存する機能に応じて適宜）
- システムパッケージ: libpq 等は不要（DuckDB/SQLite を使用）
- 推奨: 仮想環境（venv / pipenv / poetry 等）

1. リポジトリを取得し、仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要な Python パッケージをインストール
   - 主要依存（例）:
     - duckdb
     - psutil
     - openai
     - PyYAML（config YAML 検証用、任意）
   - 例:
     - pip install duckdb psutil openai PyYAML
   - （プロジェクトに requirements.txt がある場合はそれを使ってください）

3. .env を準備
   - 対話形式で作成:
     - python -m kabusys.config_setup
   - あるいは .env を手動作成（以下は主要な環境変数とデフォルト）
     - JQUANTS_REFRESH_TOKEN (必須)
     - KABU_API_PASSWORD (必須)
     - KABU_API_BASE_URL (default: http://localhost:18080/kabusapi)
     - DUCKDB_PATH (default: data/kabusys.duckdb)
     - SQLITE_PATH (default: data/monitoring.db)
     - KABUSYS_ENV (development | paper_trading | live) (default: development)
     - LOG_LEVEL (DEBUG|INFO|WARNING|ERROR) (default: INFO)
     - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID (任意)
     - KILL_FLAG_CLEAR_ON_START (0|1) (default: 0)
     - PAPER_FILL_MODE (instant|partial|never|reject) (paper_trading 用)
     - PAPER_TRADING_SQLITE_PATH (paper_trading 用 DB パス, default: data/paper_trading.db)
     - OPENAI_API_KEY （AI 機能を使う場合必須）
   - 自動読み込み:
     - kabusys.config はプロジェクトルートの .env と .env.local を自動で読み込みます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると無効化）

4. データディレクトリの作成（必要に応じて）
   - mkdir -p data logs

5. 設定検証
   - python -m kabusys.validate_config
   - 警告も厳格に扱う場合:
     - python -m kabusys.validate_config --strict

---

## 使い方（主要スクリプト）

- 実行エンジン（ExecutionEngine）を起動
  - python -m kabusys.run_execution
  - 挙動:
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し PAPER_TRADING_SQLITE_PATH に記録（本番 DB と分離）
    - data/stop_requested.flag が存在すると起動しない、または実行中に検知すると停止
    - PID ファイル: data/execution.pid（Settings.pid_file_path で変更可能）

- 監視ループを起動
  - python -m kabusys.run_monitoring
  - オプション:
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒単位で指定（デフォルト 60）
  - 挙動:
    - SystemMonitor.check_once() を定期実行して system_status を記録
    - kill.flag を管理する KillSwitch（条件達成時に data/kill.flag に理由を書き込む）
    - 停止: data/stop_requested.flag を作成すると監視プロセス・実行エンジンが停止する設計

- 設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config [--strict]

- ペーパートレード検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - デフォルト DB: 環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db

- AI 関連（ライブラリ利用）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
    - conn: duckdb connection（DuckDBPyConnection）
    - target_date: date オブジェクト
    - api_key 指定が無ければ環境変数 OPENAI_API_KEY を参照
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)

ログ出力:
- デフォルトでは logs/<app_name>.log に日次ローテーションで保存（30日保持）および stdout にも出力  
  - ログディレクトリは環境変数 LOG_DIR または引数で変更可能

停止・Kill の取り扱い:
- data/stop_requested.flag: run_execution / run_monitoring が存在をチェックし停止
- data/kill.flag: KillSwitch が条件に応じて書き込む（ExecutionEngine は起動時に KILL_FLAG_CLEAR_ON_START に応じて自動クリア可能）
- PID ファイル: data/execution.pid（設定で変更可）

---

## 環境変数（主要一覧）

必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

主要（省略時はデフォルト）:
- KABUSYS_ENV (development | paper_trading | live) — 実行環境
- DUCKDB_PATH (data/kabusys.duckdb)
- SQLITE_PATH (data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH (data/paper_trading.db)
- LOG_LEVEL (INFO)
- LOG_DIR (logs/)
- OPENAI_API_KEY（AI 機能利用時）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID（本番アラート用、任意）
- MONITOR_POLL_INTERVAL（監視ポーリング秒数、デフォルト 60）
- PAPER_FILL_MODE（paper_trading の fill 挙動: instant|partial|never|reject）
- PID_FILE_PATH（デフォルト data/execution.pid）
- KILL_FLAG_PATH（デフォルト data/kill.flag）
- KILL_FLAG_CLEAR_ON_START（"1" で起動時に kill.flag を自動クリア）

詳しい説明は kabusys.config.Settings と config_setup.py の _ITEMS を参照してください。

---

## ディレクトリ構成（抜粋）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / .env 自動読み込みと Settings
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 起動前設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — Monitoring ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート生成
  - utils/
    - logging_setup.py       — 統一ログ設定ユーティリティ
    - process_priority.py    — プロセス優先度 / CPU affinity 設定ユーティリティ
  - monitoring/
    - monitoring_db.py       — SQLite 用監視 DB 層（テーブル作成/読み書き）
    - system_monitor.py      — CPU/メモリ/ディスク/データ鮮度監視
    - trade_monitor.py       — （注文に関する監視。ファイル内の実装参照）
    - risk_monitor.py        — ドローダウン・保有数監視
    - kill_switch.py         — kill.flag 書き込みロジック
    - monitoring_engine.py   — 各 Monitor を束ねるポーリングエンジン
    - alert_manager.py       — （アラート送信）※実装ファイル参照
  - execution/
    - execution_engine.py    — 実行エンジン本体（EngineConfig 等）
    - broker_factory.py      — ブローカークライアント生成
    - order_manager.py       — 注文管理
    - order_repository.py    — 注文永続化
    - reconciler.py          — 注文状態再整合ロジック
    - risk_manager.py        — リスク管理ロジック
  - portfolio/
    - portfolio_builder.py   — 候補選定・重み付け
    - position_sizing.py     — 株数計算・丸め・キャップ調整
    - risk_adjustment.py     — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py     — momentum/value/volatility 等のファクター計算（DuckDB）
    - feature_exploration.py — 将来リターン・IC・統計サマリー
  - ai/
    - news_nlp.py            — ニュース NLP を用いた銘柄スコアリング（OpenAI）
    - regime_detector.py     — マクロ + ETF MA を使ったレジーム判定
  - data/                    — 実行時に使用するデータ・フラグ（data/*.db, *.pid, *.flag）
  - logs/                    — ログファイル（出力先）

---

## 運用上の注意点

- 本番（KABUSYS_ENV=live）では Kill Switch / LINE 通知などの設定を必ず確認してください。validate_config の WARN を重視して設定を整えてください。
- .env は Git 管理に含めないでください（config_setup.py のヘッダにも注意書きあり）。
- OpenAI を使う機能は API 利用料がかかります。API キーの管理と利用制限に注意してください。
- DuckDB / SQLite のファイルはバックアップやアクセス権に注意（複数プロセスが同一ファイルへ競合アクセスする場合の設計に注意）。
- プロセス優先度設定はアクセス権により失敗することがあります（ログで WARN を確認）。

---

必要であれば README にコマンド例、.env.example のテンプレート、systemd / supervisor 用ユニット例、テストの実行方法などを追加します。どの情報を優先して追記しましょうか？