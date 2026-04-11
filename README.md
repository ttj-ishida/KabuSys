# KabuSys

日本株向け自動売買システムの内部ライブラリ群と起動スクリプト群。シグナルに基づく発注エンジン、監視モジュール、ポートフォリオ構築ロジック、ファクター計算・リサーチ、LLM を使ったニュースセンチメント評価などを含みます。

このリポジトリはライブラリとしての再利用とデーモン的なプロセス起動（ExecutionEngine / MonitoringEngine）を想定しています。

---

## プロジェクト概要

主な目的は次のとおりです。

- シグナル駆動の発注エンジン（ExecutionEngine）
  - 発注ゲート（リスクチェック、レート制限、ドローダウン制御など）
  - ブローカー API 抽象化（実運用 / モックで分離）
  - 再起動時のリコンシリエーション（注文・ポジションの突合）
- 監視・アラート（MonitoringEngine）
  - プロセス監視、データ鮮度チェック、注文滞留・約定異常検知、ドローダウン監視
  - LINE へ通知、kill.flag による実行停止シグナル
  - Streamlit ベースの監視ダッシュボード
- ポートフォリオ構築（候補選定・重み計算・ポジションサイズ算出・セクター制限など）
- リサーチ（DuckDB を用いたファクター計算、将来リターン、IC・統計サマリ等）
- AI 補助（ニュース NLP による銘柄別センチメント、レジーム判定）

---

## 機能一覧

主要モジュールと機能（抜粋）:

- kabusys.execution
  - ExecutionEngine: シグナル読み取り・発注ループ、push ドレイン
  - OrderManager / OrderRepository: 注文管理、DB 永続化
  - Reconciler: 再起動時の注文・ポジション同期
  - RiskManager: ゲート（シグナル/エグゼキューション/ドローダウン等）
- kabusys.monitoring
  - MonitoringEngine: 各種モニタを束ねるポーリング実行
  - SystemMonitor: CPU/メモリ/Disk/プロセス存在・データ鮮度監視
  - TradeMonitor: 注文滞留・約定異常検知
  - RiskMonitor: ドローダウン・ポジション上限監視
  - KillSwitch: kill.flag を書き込むことで ExecutionEngine 停止
  - AlertManager: LINE へプッシュ通知（クールダウン管理）
  - monitoring_db: SQLite スキーマ定義とラッパー（MonitoringDB）
  - streamlit_dashboard: Streamlit による可視化
- kabusys.portfolio
  - portfolio_builder: 候補選定・重み計算（等配分／スコア加重）
  - position_sizing: 株数計算、lot 単位丸め、aggregate cap スケーリング
  - risk_adjustment: セクター上限適用、レジーム乗数
- kabusys.research
  - factor_research: Momentum / Volatility / Value 等のファクター計算（DuckDB）
  - feature_exploration: 将来リターン、IC、統計サマリ
- kabusys.ai
  - news_nlp.score_news: OpenAI を使ってニュースを銘柄別にスコア化し ai_scores に保存
  - regime_detector.score_regime: ETF MA とマクロニュースで市場レジーム判定
- kabusys.utils
  - process_priority: プロセス優先度・CPU affinity 設定ユーティリティ
- 設定読み込み
  - kabusys.config: .env 自動ロード、環境変数ラッパー（Settings）

---

## セットアップ手順

1. Python 環境準備（推奨: venv）
   - Python 3.10+ を想定（typing の union 表記など）
   - 仮想環境作成・有効化:
     - python -m venv .venv
     - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージをインストール
   - 主な依存例（requirements.txt が無い場合は手動で）:
     - duckdb
     - psutil
     - requests
     - openai
     - streamlit
   - 例:
     - pip install duckdb psutil requests openai streamlit

3. プロジェクトルートの .env
   - リポジトリルート（.git または pyproject.toml のあるディレクトリ）に `.env` / `.env.local` を置くと自動で読み込まれます（デフォルト挙動）。
   - 自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。
   - 必須っぽい環境変数例（用途に応じて設定）:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
     - OPENAI_API_KEY (AI 機能利用時)
     - KABUSYS_ENV (development / paper_trading / live)
     - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID (通知)
   - DB パス等のデフォルト:
     - DUCKDB_PATH: data/kabusys.duckdb
     - SQLITE_PATH: data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db

4. データディレクトリ作成
   - data/ 配下に DB や pid/flag を置くのがデフォルトです:
     - mkdir -p data

注意:
- process_priority の設定（高優先度）は psutil を通じて行われます。UNIX 系で負の nice を与える操作は権限が必要になる場合があります。

---

## 使い方

以下は典型的な起動例です。パッケージを import 可能な状態（PYTHONPATH に src を含める等）で実行してください。

1. ExecutionEngine を起動（本番 / paper_trading 切り替え）
   - 環境変数で切り替え:
     - export KABUSYS_ENV=paper_trading
       - paper_trading の場合、MockBrokerClient を利用し専用 SQLite（PAPER_TRADING_SQLITE_PATH）に記録します（本番 DB と分離）。
     - export KABUSYS_ENV=live
   - 起動コマンド（プロジェクトルート）:
     - PYTHONPATH=src python -m kabusys.run_execution
   - 注意:
     - 起動時にプロセス優先度を "high" に設定します（psutil 経由）。
     - PID ファイル (デフォルト: data/execution.pid) を使ってプロセス存在確認を行います。
     - kill.flag (デフォルト: data/kill.flag) があると起動直後に停止します。必要に応じて Settings.kill_flag_clear_on_start を使う設定があります。

2. MonitoringEngine を起動
   - デフォルトで本番 sqlite_path を使用（monitoring は環境にかかわらず本番 DB を参照します）。
   - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL`（秒）で上書き可能。デフォルト 60 秒。
   - 起動コマンド:
     - PYTHONPATH=src python -m kabusys.run_monitoring
   - 監視内容:
     - SystemMonitor（CPU/メモリ/Disk、プロセス存在、データ鮮度）
     - TradeMonitor（滞留注文、約定異常）
     - RiskMonitor（ドローダウン、ポジション上限）
     - KillSwitch（条件満たせば data/kill.flag を書き込み、必要なら AlertManager へ通知）

3. Streamlit ダッシュボード（監視 UI）
   - 起動コマンド:
     - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
   - read-only で SQLite を開くため、MonitoringEngine が先に DB を準備している必要があります。

4. AI 関連
   - ニューススコアリング:
     - kabusys.ai.score_news(conn, target_date, api_key=None)
     - API キーは引数もしくは環境変数 OPENAI_API_KEY を利用。
   - レジーム判定:
     - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)

5. 開発・リサーチ
   - DuckDB 接続を作り、kabusys.research の関数（calc_momentum / calc_volatility / calc_value / calc_forward_returns / calc_ic 等）を呼び出して解析できます。
   - 例（対話）:
     - PYTHONPATH=src python
     - >>> import duckdb, datetime
     - >>> conn = duckdb.connect("data/kabusys.duckdb")
     - >>> from kabusys.research import calc_momentum
     - >>> calc_momentum(conn, datetime.date(2026, 3, 20))

---

## 主要な環境変数（抜粋）

- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、デフォルト 60）
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 1 を設定すると .env 自動ロードを無効化
- JQUANTS_REFRESH_TOKEN: J-Quants API 用トークン（必須の場合あり）
- KABU_API_PASSWORD: kabuステーション API のパスワード
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト http://localhost:18080/kabusapi）
- OPENAI_API_KEY: OpenAI API キー（AI 機能利用時）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE 通知用
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（デフォルト data/paper_trading.db）
- PAPER_FILL_MODE: paper_trading の MockBroker 動作（instant | partial | never | reject）
- PID_FILE_PATH: 実行プロセスの PID ファイルパス（default data/execution.pid）
- KILL_FLAG_PATH: kill.flag のパス（default data/kill.flag）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動で消す（"1" で有効）
- LOG_LEVEL: ログレベル（DEBUG / INFO / ...）

---

## ディレクトリ構成

（主要ファイルのみ抜粋）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / .env 自動ロード、Settings
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリング起動スクリプト
  - utils/
    - process_priority.py    — プロセス優先度・CPU affinity ユーティリティ
  - execution/
    - execution_engine.py    — ExecutionEngine 実装
    - order_manager.py
    - order_repository.py
    - order_record.py
    - reconciler.py
    - broker_factory.py
    - broker_api.py
    - risk_manager.py
  - monitoring/
    - monitoring_engine.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py
    - monitoring_db.py
    - streamlit_dashboard.py
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
  - data/ (参照されるがリポジトリ内に含まれない可能性あり）
    - kabusys.duckdb (DuckDB file)
    - monitoring.db (SQLite)
    - paper_trading.db (paper trading 用 SQLite)

---

## 運用上の注意 / 実装上のポイント

- MonitoringEngine は MONITOR_POLL_INTERVAL で制御されます。MONITOR_POLL_INTERVAL が 1 未満や不正な場合はデフォルト 60 秒にフォールバックします。
- run_monitoring.py は KABUSYS_ENV の値にかかわらず、本番 sqlite_path（Settings.sqlite_path）を監視 DB に使用します。paper_trading は run_execution.py 側で分離されます。
- ExecutionEngine 起動時に PID ファイルを使用してプロセス存在チェックを行います。stale PID を検出すると削除し、ログ／risk_logs に記録します。
- AI 呼び出しは OpenAI の Chat Completions（gpt-4o-mini）を想定。ネットワーク・429・5xx にはリトライロジックが実装されていますが、API キー未設定時は例外が発生します。
- process_priority の設定は OS に依存します。権限不足で設定できない場合は警告ログが出ますが処理は継続します。
- DB スキーマは monitoring_db.init_monitoring_db により冪等に作成されます。既存スキーマとの互換性チェックや簡易マイグレーションも一部実装されています。

---

## 開発者向け補足

- パッケージを直接実行する際は PYTHONPATH=src を通すと便利です（開発時）。
- 単体関数群（ポートフォリオ関連、リサーチ関連）は副作用を持たない純粋関数として設計されており、ユニットテストが容易です。
- OpenAI 呼び出し部分はユニットテストでモック化しやすいように、内部 API 呼び出し関数を個別に定義してあります（テストで patch 可能）。

---

必要であれば、README に含めるコマンド例（systemd ユニット例、docker-compose、requirements.txt）や、.env.example のテンプレート、運用フロー（デプロイ手順・監視ルールなど）を追加で作成します。どの情報を優先して追加しますか？