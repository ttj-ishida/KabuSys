# KabuSys

日本株向け自動売買 / 研究基盤のコアライブラリ群です。  
本リポジトリは注文エンジン、監視、ポートフォリオ構築、研究用ファクター計算、AI（ニュースNLP / レジーム判定）などの主要コンポーネントを含みます。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株自動売買システムの基盤モジュール群です。主な目的は次のとおりです：

- 注文実行エンジン（ExecutionEngine）とそれに関連するブローカー抽象化（paper/live の分離）
- システム・注文・リスク監視、および Kill Switch による安全停止
- ポートフォリオ構築（銘柄選定、重み計算、ポジションサイズ計算、セクターキャップ等）
- 研究用モジュール（ファクター計算・特徴量探索）
- AI を使ったニュースセンチメント解析および市場レジーム判定
- ユーティリティ（ログ設定、プロセス優先度設定、設定ウィザード・検証等）
- ペーパートレード向け検証レポート生成ツール

設計方針として、可能な限り副作用を抑え、DB（SQLite / DuckDB）を明確に分離し、LLM 利用箇所はフェイルセーフ（失敗時はスキップまたは中立値）にしています。

---

## 主な機能一覧

- run_execution.py
  - ExecutionEngine の起動スクリプト。KABUSYS_ENV によって paper_trading（MockBroker）と live を切り替え。
  - paper_trading 時は専用 SQLite（デフォルト: data/paper_trading.db）に分離して記録。
- run_monitoring.py
  - SystemMonitor のポーリングループを実行し system_status 等を記録。
  - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き（デフォルト: 60 秒）。
- config_setup.py
  - 対話式ウィザードで .env を初期作成 / 更新するユーティリティ。
- validate_config.py
  - .env や config/*.yaml の設定を起動前に検証する CLI。
- tools/paper_verification_report.py
  - ペーパートレード結果の集計・パス/フェイル判定レポート生成。
- ai/news_nlp.py
  - OpenAI（gpt-4o-mini）を用いたニュース記事の銘柄別センチメントスコアリング（ai_scores への書き込み）。
- ai/regime_detector.py
  - ETF（1321）の MA 乖離 + マクロニュースセンチメントを合成して日次レジーム（bull/neutral/bear）を判定し DB に永続化。
- portfolio/*
  - 銘柄選定、重み計算、ポジションサイズ計算、セクター制約・レジーム乗数などの純粋関数実装。
- monitoring/*
  - MonitoringDB（SQLite）を用いたログ永続化、各種 Monitor（System / Trade / Risk）、KillSwitch、Alert 管理、監視エンジン。

---

## セットアップ手順

以下は開発/実行用の基本手順です。

1. Python 環境を用意
   - Python 3.10+ を推奨
   - 仮想環境例:
     - python -m venv .venv
     - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   - 必須（最低限）:
     - duckdb
     - psutil
     - openai
   - 追加（便利）:
     - PyYAML（validate_config の YAML 検証に必要）
   - 例:
     - pip install duckdb psutil openai PyYAML

   ※ リポジトリに requirements.txt がない場合は上記を個別に入れてください。

3. .env を作成
   - 対話式ウィザード:
     - python -m kabusys.config_setup
   - もしくは .env.example を参考に手動作成
   - 自動ロード: Settings モジュールはプロジェクトルートの `.env` / `.env.local` を自動でロードします（`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能）。

4. 設定検証（任意だが推奨）
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いになります。

5. 必要ディレクトリの確認
   - デフォルト DB/ログパスは `data/` と `logs/`。`logs/` は起動時に自動作成されますが、`data/` を作成しておくと安全です。
     - mkdir -p data logs

6. OpenAI API を使う機能を利用する場合:
   - 環境変数 `OPENAI_API_KEY` を設定するか、関数呼び出し時に api_key 引数を渡してください。

---

## 環境変数（主なもの）

（一部デフォルト値を併記）

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL (default: http://localhost:18080/kabusapi)
- LINE_CHANNEL_ACCESS_TOKEN (任意)
- LINE_USER_ID (任意)
- DUCKDB_PATH (default: data/kabusys.duckdb)
- SQLITE_PATH (default: data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH (default: data/paper_trading.db)
- PAPER_FILL_MODE (default: instant) — 有効値: instant | partial | never | reject
- KABUSYS_ENV (default: development) — 有効値: development | paper_trading | live
- LOG_LEVEL (default: INFO)
- KILL_FLAG_CLEAR_ON_START (default: 0) — 1 にすると起動時に kill.flag を自動クリア
- PID_FILE_PATH (default: data/execution.pid)
- KILL_FLAG_PATH (default: data/kill.flag)
- MONITOR_POLL_INTERVAL (run_monitoring 用、デフォルト 60 秒)
- OPENAI_API_KEY (AI 機能用)

注意: Settings モジュールでは自動的に .env をロードします（プロジェクトルートが検出できる場合）。

---

## 使い方（コマンド例）

- 設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 厳密モード: python -m kabusys.validate_config --strict

- ExecutionEngine 起動（本番 / ペーパー）
  - デフォルト（KABUSYS_ENV で切替）:
    - python -m kabusys.run_execution
  - ペーパートレードに切り替える場合:
    - export KABUSYS_ENV=paper_trading
    - python -m kabusys.run_execution
  - 停止は `data/stop_requested.flag` を作成すると安全に停止できます（停止フラグの検出により停止処理が走ります）。
  - Execution により使用される DB:
    - paper_trading では PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）
    - それ以外では SQLITE_PATH（デフォルト data/monitoring.db）

- Monitoring 起動
  - python -m kabusys.run_monitoring
  - ポーリング間隔を変更する:
    - export MONITOR_POLL_INTERVAL=30
    - python -m kabusys.run_monitoring
  - 監視プロセスも `data/stop_requested.flag` によって安全にループを抜けます。

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB パスを指定:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

- AI 機能（Python API から呼ぶ）
  - ニューススコアリング:
    - from kabusys.ai.news_nlp import score_news
    - score_news(conn, target_date, api_key=None)  # api_key が None の場合は OPENAI_API_KEY を参照
  - レジーム判定:
    - from kabusys.ai.regime_detector import score_regime
    - score_regime(conn, target_date, api_key=None)

---

## Kill Switch / 停止フラグ

- Kill Switch:
  - monitoring.kill_switch.KillSwitch が条件に応じて `data/kill.flag` を書き込み、ExecutionEngine に停止シグナルを送ります。
  - 本番での誤動作を避けるため、`KILL_FLAG_CLEAR_ON_START=0`（デフォルト）を推奨します。

- 手動停止フラグ:
  - `data/stop_requested.flag` を作成すると run_execution / run_monitoring のループが検出して安全停止します。

---

## ロギング

- 共通ユーティリティ: kabusys.utils.logging_setup.setup_logging(app_name="execution" など)
  - stdout（StreamHandler）と日次ローテートされるファイルログ（logs/<app_name>.log）を設定します。
  - ログ出力ディレクトリは環境変数 `LOG_DIR` で上書き可能（デフォルト logs/）。
  - ログレベルは `LOG_LEVEL` 環境変数または setup_logging の引数で指定できます。

---

## ディレクトリ構成（主要ファイル）

src/kabusys/
- __init__.py
- config.py              — 環境変数読み込み・Settings 定義
- config_setup.py        — .env 対話式ウィザード
- validate_config.py     — 設定検証 CLI
- run_execution.py       — ExecutionEngine 起動スクリプト
- run_monitoring.py      — SystemMonitor 起動スクリプト

subpackages:
- ai/
  - __init__.py
  - news_nlp.py          — ニュース NLP スコアリング
  - regime_detector.py   — 市場レジーム判定
- monitoring/
  - monitoring_db.py     — SQLite 永続化層
  - system_monitor.py
  - trade_monitor.py     — （trade 関連の監視ロジック）
  - risk_monitor.py
  - kill_switch.py
  - monitoring_engine.py
  - alert_manager.py     — （通知管理）
- execution/
  - broker_factory.py
  - execution_engine.py
  - order_manager.py
  - order_repository.py
  - reconciler.py
  - risk_manager.py
- portfolio/
  - __init__.py
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py
- research/
  - __init__.py
  - factor_research.py
  - feature_exploration.py
- tools/
  - __init__.py
  - paper_verification_report.py
- utils/
  - __init__.py
  - logging_setup.py
  - process_priority.py
- data/ (実行時に使用するローカルディレクトリ)
  - monitoring.db (デフォルト for monitoring)
  - paper_trading.db (paper_trading 用)
  - stop_requested.flag, execution.pid, kill.flag など

（上記は主要ファイルの抜粋です。詳しくはソースツリーを参照してください）

---

## 実行上の注意 / ベストプラクティス

- 本番（KABUSYS_ENV=live）では .env の内容・ LINE 通知設定・ Kill Switch の挙動を慎重に確認してください。validate_config の `--strict` モードで事前チェックすることを推奨します。
- OpenAI API を使う機能は API コストとレート制限に注意してください。news_nlp と regime_detector はリトライやフォールバックを組み込んでいますが、運用ルールを設けてください。
- ペーパートレード時は DB が本番と分離されるよう `KABUSYS_ENV=paper_trading` を設定してください。
- ログや DB ファイルはバックアップ/ローテーション方針を検討してください（logs/ は日次ローテーションで 30 日保持）。
- プロセス優先度設定（set_process_priority）は psutil の権限に依存するため、権限不足や未対応 OS の場合は警告となりスキップされます。

---

## 開発向け補足

- 多くのモジュールは純粋関数（副作用なし）で設計されており、ユニットテストが容易です（例: portfolio/*.py, research/*.py）。
- DB 操作は monitoring_db.py のように薄いラッパーで分離されています。Integration テスト時は一時 SQLite ファイルを用いるのが安全です。
- OpenAI 呼び出し部分は個別関数化してあり、テスト時はモック（unittest.mock.patch）で置き換え可能です。

---

もし README に追加したい情報（例: requirements.txt、CI 設定、デプロイ手順、API 仕様の詳細など）があれば教えてください。必要に応じて追加・拡張します。