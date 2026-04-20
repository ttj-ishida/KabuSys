# KabuSys

日本株自動売買システムの Python パッケージ（ドキュメント）。  
この README はリポジトリ内の主要モジュール群をもとに、導入・起動方法や主要機能を日本語でまとめたものです。

---
目次
- プロジェクト概要
- 機能一覧
- 前提・依存関係
- セットアップ手順
- 環境変数（主なもの）
- 使い方（主要スクリプト）
- ツール・ユーティリティ
- ディレクトリ構成

---

## プロジェクト概要
KabuSys は日本株向けの自動売買・リサーチ基盤です。  
主なコンポーネントは以下です。

- ExecutionEngine（発注・注文管理・リスク管理）
- Monitoring（システム監視・アラート・Kill Switch）
- Portfolio construction（候補選定・配分・サイズ計算・リスク調整）
- Research（ファクター計算・特徴量解析）
- AI モジュール（ニュース NLP によるセンチメント評価、レジーム判定）
- 各種 CLI ツール（環境ウィザード、設定検証、ペーパートレード検証レポート 等）

設計方針の一部：外部 API 呼び出しを受ける箇所（kabu API / OpenAI 等）は明示的で、Paper Trading 用に本番 DB とは分離した挙動が用意されています。

---

## 機能一覧
- Execution
  - 発注ロジックの実行（ExecutionEngine, OrderManager, RiskManager, Reconciler 等）
  - Paper Trading モードでは MockBrokerClient を利用し、発注データは別ファイルに保存
- Monitoring
  - システム資源（CPU/メモリ/ディスク）や Execution プロセスの監視
  - トレードログ・リスクログ・ダッシュボード永続化（SQLite）
  - Kill Switch（閾値超過時に停止フラグを作成）
- Portfolio construction
  - 候補選定（score / rank）
  - 等配分・スコア加重・リスクベースの株数決定
  - セクター集中制限、レジーム乗数
- Research
  - Momentum / Volatility / Value 等のファクター計算（DuckDB を利用）
  - 将来リターン計算、IC（Information Coefficient）等の解析
- AI
  - ニュース記事を LLM（OpenAI）で評価し銘柄別スコアを生成して保存
  - マクロニュースと ETF MA 乖離を用いた市場レジーム判定
- ツール
  - .env 初期ウィザード（config_setup）
  - 設定検証 CLI（validate_config）
  - Paper Trading 検証レポート生成（tools.paper_verification_report）

---

## 前提・依存関係
最低限インストールが必要なライブラリ（例）：
- Python 3.9+（型注記などを踏まえた目安）
- duckdb
- psutil
- openai（AI 機能を使用する場合）
- PyYAML（config 検証で YAML ファイルの中身検証を行う場合、任意）

インストール例（仮想環境推奨）:
- pip install duckdb psutil openai pyyaml

（このリポジトリに requirements.txt がある場合はそちらを使用してください）

---

## セットアップ手順

1. リポジトリをクローンして移動
   - git clone ... && cd repo

2. 仮想環境の作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存ライブラリのインストール
   - pip install duckdb psutil openai pyyaml

4. .env の作成（ウィザード推奨）
   - python -m kabusys.config_setup
     - 対話形式で .env を作成します（デフォルト: プロジェクトルート/.env）
   - もしくは .env.example を参考に手動作成

5. 設定検証（任意だが推奨）
   - python -m kabusys.validate_config
   - 警告も FAIL 扱いにしたい場合:
     - python -m kabusys.validate_config --strict

6. 必要な DB／ディレクトリ
   - デフォルトのパス:
     - DuckDB: data/kabusys.duckdb
     - SQLite (monitoring): data/monitoring.db
     - Paper Trading SQLite: data/paper_trading.db
   - ログ出力先: logs/（default）
   - これらは .env または環境変数で上書きできます（下記参照）

---

## 主な環境変数（抜粋）
（config.py, validate_config.py を参照）

必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

運用に関連する主な設定:
- KABUSYS_ENV: execution モード
  - development / paper_trading / live
  - paper_trading の場合、Execution は MockBroker を使い paper_trading.db に記録
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視 SQLite（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト data/paper_trading.db）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- LOG_DIR: ログ保存ディレクトリ（デフォルト logs/）
- OPENAI_API_KEY: OpenAI を使う機能で必要
- PAPER_FILL_MODE: ペーパートレードでの約定挙動（instant|partial|never|reject）
- MONITOR_POLL_INTERVAL: monitoring ポーリング間隔（秒、デフォルト 60）
- PID_FILE_PATH / KILL_FLAG_PATH: Execution 停止管理用パス

注意:
- 自動ロード順は OS 環境 > .env.local > .env
- KILL_FLAG_CLEAR_ON_START=1 に注意（本番では 0 推奨）

---

## 使い方（主要スクリプト）

各スクリプトはモジュールとして実行できます（python -m ...）。

1. 環境設定ウィザード
   - python -m kabusys.config_setup
   - .env の生成・更新に使います。

2. 設定検証
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いになります。

3. Monitoring（監視ループ）
   - python -m kabusys.run_monitoring
   - 概要:
     - プロセス優先度を "high" に設定（可能な場合）
     - SQLite と DuckDB に接続（monitoring は常に本番 sqlite_path を使用）
     - SystemMonitor を起動しポーリングループを実行（デフォルト 60 秒）
     - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能
   - 停止:
     - プロジェクトルート/data/stop_requested.flag が存在するとループを終了します

4. Execution（発注エンジン）
   - python -m kabusys.run_execution
   - 概要:
     - プロセス優先度を "high" に設定
     - KABUSYS_ENV=paper_trading の場合は paper_sqlite_path を使用し MockBrokerClient を利用
     - 実行時に data/stop_requested.flag が既にあると起動せず終了
     - 実行中は thread で ExecutionEngine.run_session を回し、stop flag を検知したら engine.stop() を呼ぶ
   - PID, kill flag:
     - PID ファイル: data/execution.pid（デフォルト）
     - Kill Switch は data/kill.flag に書き込まれ、ExecutionEngine 側で読んで停止を判断します

5. Paper Trading 検証レポート
   - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
   - デフォルト DB パス: 環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db
   - レポートでは稼働率、注文成功率、送信率、レイテンシ等を集計して PASS/FAIL を判定します

6. AI モジュール（ライブラリ呼び出し）
   - kabusys.ai.score_news(conn, target_date, api_key=None)
     - DuckDB 接続と日付を渡してニューススコアを ai_scores テーブルへ書き込む
     - OpenAI API キーが必要（引数か OPENAI_API_KEY）
   - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
     - 市場レジームを判定して market_regime テーブルへ書き込み

---

## ログ・監視ファイル
- ログ: logs/<app_name>.log（TimedRotatingFileHandler、日次ローテート、30 日保持）
- stop flag: data/stop_requested.flag （run_* スクリプトの外部停止用）
- kill flag: data/kill.flag （Monitoring → KillSwitch が書き込むと Execution は停止を受ける）
- PID ファイル: data/execution.pid（ExecutionEngine 起動時に使用）

---

## 開発者向けメモ（ポイント）
- Settings クラス（kabusys.config.Settings）で環境変数を一元管理
- .env 自動読み込みはデフォルトで有効（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）
- MonitoringDB（monitoring/monitoring_db.py）は SQLite に対する永続化レイヤーを提供
- DuckDB はリサーチ／AI 部分で集計に使用（prices_daily, raw_financials, raw_news 等）
- AI 呼び出しはリトライやレスポンス検証を入れて堅牢化している
- Paper Trading 用の DB は本番 DB とは分離（Settings.is_paper 判定により切替）

---

## ディレクトリ構成（抜粋）
以下は src/kabusys 以下の主要ファイル構成（代表的なもののみ抜粋）:

- src/kabusys/
  - __init__.py
  - config.py
  - config_setup.py
  - validate_config.py
  - run_monitoring.py
  - run_execution.py
  - tools/
    - __init__.py
    - paper_verification_report.py
  - ai/
    - __init__.py
    - news_nlp.py
    - regime_detector.py
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - monitoring_engine.py
    - kill_switch.py
    - alert_manager.py
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
  - monitoring/
    - ...（上記）
  - utils/
    - __init__.py
    - logging_setup.py
    - process_priority.py
  - data/ (実行時に生成されるディレクトリ / DB / flag 等)

（その他、data/、config/ 等の補助ファイルがプロジェクトルートに存在）

---

## よくある操作例

- .env を作成して検証する
  - python -m kabusys.config_setup
  - python -m kabusys.validate_config

- 監視プロセスを起動（デーモン管理下で実行）
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- Execution を Paper Trading で起動
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution

- Paper Trading レポートを生成
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

- AI スコア付与（スクリプト等から呼び出し）
  - from kabusys.ai import score_news
  - score_news(duckdb_conn, date(2026, 4, 10), api_key="sk-...")

---

README の内容はコードコメント・モジュールの実装に依存しています。実運用前には必ず validate_config による検証、および staging/paper_trading モードでの十分なテストを行ってください。必要であればさらに詳細な運用手順・アーキテクチャ図・API 利用制限に関するドキュメントを追加することを推奨します。