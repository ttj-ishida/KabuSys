# KabuSys

KabuSys は日本株自動売買システムのリポジトリです。本リポジトリは取引エンジン（Execution）、監視（Monitoring）、ポートフォリオ構築、リサーチ（ファクター計算）および AI を使ったニュース NLP / レジーム判定機能などのコンポーネント群で構成されています。

以下は本コードベースの概要・セットアップ・使い方・ディレクトリ構成の説明です。

---

## プロジェクト概要

主な目的：
- シグナルに基づいた発注（ExecutionEngine / OrderManager）
- 実行中のシステム監視（SystemMonitor / TradeMonitor / RiskMonitor）
- 監視イベントの永続化（SQLite）
- ポートフォリオ構築（候補選定・重み付け・株数決定）
- DuckDB を使ったリサーチ（ファクター計算、将来リターン、IC 等）
- OpenAI を利用したニュースセンチメントやマクロセンチメント評価（AI）
- Paper trading（本番 DB と分離された動作）をサポート

設計上の特徴：
- DuckDB（時系列・ファクターデータ）と SQLite（監視ログ・発注ログ）を併用
- Paper trading モード時は本番の発注 API にアクセスせず MockBrokerClient を使用し、専用の SQLite（デフォルト: data/paper_trading.db）へ記録
- 監視（Monitoring）は環境に関係なく本番の sqlite_path を使用して稼働ログを取得（運用監視を一元化）
- .env ファイルの自動読み込み（プロジェクトルートを探索）を実装。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能

---

## 主な機能一覧

- Execution（発注）関連
  - OrderManager: 発注フロー／状態管理
  - Reconciler: 再起動後の注文・ポジション突合
  - RiskManager: 発注前チェック（rate limit / position limits 等） ※設定部分は Execution 側に実装

- Monitoring（監視）
  - SystemMonitor: CPU / メモリ / ディスク / Execution プロセス生存 / データ鮮度監視
  - TradeMonitor: 滞留注文・約定価格異常検出
  - RiskMonitor: ドローダウン、ポジション数上限監視（ダッシュボード更新、アラートの永続化）
  - KillSwitch: しきい値到達時に data/kill.flag を書き込み Execution を停止させる仕組み
  - AlertManager: LINE Messaging API を使った通知（クールダウンあり）
  - streamlit による監視ダッシュボード（read-only の SQLite を表示）

- Portfolio（配分）
  - 候補選定、等重・スコア加重配分、リスク調整（セクターキャップ、レジーム乗数）、単元丸め・ポジションサイズ計算

- Research（リサーチ）
  - ファクター計算（Momentum / Volatility / Value 等）
  - 特徴量探索（将来リターン計算、IC、統計サマリー）

- AI（OpenAI）
  - news_nlp: ニュース記事をまとめて LLM に投げ、銘柄ごとのセンチメント（ai_scores）を取得・書き込み
  - regime_detector: ETF(1321) の MA200 乖離とマクロニュースの LLM センチメントを合成して日次レジームを判定・保存

- ツール
  - paper_verification_report: Paper Trading DB を解析して稼働率・注文成功率・レイテンシ等の検証レポートを出力

---

## セットアップ手順（開発用）

1. リポジトリをクローン
   - 例: git clone <repo-url>

2. Python 仮想環境作成 & 有効化
   - python3 -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要な依存パッケージをインストール
   - 本リポジトリでは以下の主要依存があります（バージョンはプロジェクト要件に合わせて調整してください）:
     - duckdb
     - psutil
     - openai
     - requests
     - streamlit
   - 例:
     - pip install duckdb psutil openai requests streamlit

   （requirements.txt が用意されていれば pip install -r requirements.txt を使用してください）

4. データディレクトリの作成（任意）
   - mkdir -p data

5. 環境変数設定
   - .env または環境変数で各種設定を行います。自動でプロジェクトルートの `.env` / `.env.local` を読み込みます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。
   - 主な環境変数（一部とデフォルト値）:
     - KABUSYS_ENV: development | paper_trading | live  (デフォルト: development)
     - OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合必須）
     - JQUANTS_REFRESH_TOKEN: J-Quants API 用トークン（必須）
     - KABU_API_PASSWORD: kabuステーション API 用パスワード（必須）
     - DUCKDB_PATH: data/kabusys.duckdb（デフォルト）
     - SQLITE_PATH: data/monitoring.db（監視用の本番 DB、デフォルト）
     - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db（paper_trading 用 DB）
     - PAPER_FILL_MODE: instant | partial | never | reject（paper trading の埋め方、デフォルト: instant）
     - PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START 等（監視・停止制御）
     - LOG_LEVEL: DEBUG/INFO/...

6. 初期 DB 作成
   - 監視用 DB スキーマは起動時に自動作成されます（init_monitoring_db）。特に手動操作は不要です。

---

## 使い方（主要スクリプト / コマンド）

注意: パッケージをインストール済み、または PYTHONPATH に src が含まれている前提です。簡単に実行するにはプロジェクトルートで `python -m kabusys.<module>` を使ってください。

1. 監視プロセス（Monitoring）
   - 起動:
     - python -m kabusys.run_monitoring
     - デフォルトのポーリング間隔は 60 秒。環境変数 MONITOR_POLL_INTERVAL で上書き可能（秒単位、1 以上）。
   - 停止:
     - data/stop_requested.flag を作成すると run_monitoring のループが終了します。

   補足:
   - run_monitoring は常に Settings.sqlite_path（本番 monitoring.db）を使用してログを記録します（KABUSYS_ENV に依存しない）。
   - process priority を "high" に設定します（set_process_priority）。

2. 発注エンジン（Execution）
   - 起動:
     - python -m kabusys.run_execution
   - 挙動:
     - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH（デフォルト: data/paper_trading.db）へ全発注ログを記録して本番 DB と分離します。
     - Stop: data/stop_requested.flag を検知するとエンジンを停止します。
     - 実行中、PID ファイル (data/execution.pid デフォルト) を書きます。SystemMonitor はこの PID を参照してプロセス生存を確認します。

3. 監視ダッシュボード（Streamlit）
   - 起動:
     - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
   - 説明:
     - read-only モードで SQLite を開き、Dashboard、Positions、Orders、System 情報を表示します。

4. Paper Trading 検証レポート
   - 実行:
     - python -m kabusys.tools.paper_verification_report
     - オプション:
       - --from YYYY-MM-DD --to YYYY-MM-DD
       - --db PATH（PAPER_TRADING_SQLITE_PATH より優先）
   - 出力:
     - 稼働率、注文成功率、送信率、レイテンシ（平均・最大・P95）を標準出力に表示し PASS/FAIL 判定を行います。

5. AI 関連
   - ニューススコア作成:
     - kabusys.ai.score_news(conn, target_date, api_key=...)
       - 実行は DuckDB 接続を渡して行います。OpenAI API キーが必要（引数または OPENAI_API_KEY 環境変数）。
   - レジーム判定:
     - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=...)
       - DuckDB 上の prices_daily/raw_news を参照して market_regime テーブルに結果を書き込みます。

---

## 重要な挙動 / 設定メモ

- .env 自動読み込み
  - プロジェクトルート（.git または pyproject.toml を検出）を基に `.env` と `.env.local` を自動読み込みします。
  - OS 環境変数は保護され、`.env.local` の override は OS 環境変数を上書きしません（protected）。
  - 無効化: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

- 環境（KABUSYS_ENV）
  - 有効値: development | paper_trading | live
  - run_execution は paper_trading の場合に paper_db を使用し、MockBrokerClient を利用します。
  - 監視（Monitoring）は env に関係なく settings.sqlite_path（本番の監視 DB）を使用します。

- 停止 / キルフラグ
  - data/stop_requested.flag: run_monitoring / run_execution の起動ループがこれを検知して安全に終了します。
  - data/kill.flag: KillSwitch が書き込み、ExecutionEngine に停止シグナルとして使われます。KillSwitch.evaluate() が条件を満たすと生成されます。
  - PID ファイル: data/execution.pid（Monitoring はこれを読んで実プロセスの存否を確認）

- Paper trading の fill モード
  - PAPER_FILL_MODE（instant|partial|never|reject）：MockBroker の約定挙動を制御

- MONITOR_POLL_INTERVAL
  - run_monitoring のポーリング間隔（秒）。環境変数で上書き（デフォルト 60）。1 未満の値は無視されデフォルトにフォールバックされます。

---

## 監視 DB（SQLite）スキーマ（init_monitoring_db による作成）

起動時に以下のテーブルとインデックスを作成（冪等）します。既存 DB に対してはマイグレーション処理（カラム追加）も行います。

- system_status
  - recorded_at, cpu_percent, memory_percent, disk_percent, process_ok
  - idx_system_status_recorded_at

- trade_logs
  - logged_at, event_type, client_order_id, code, side, qty, price, filled_qty, state, latency_ms
  - idx_trade_logs_logged_at, idx_trade_logs_client_order_id

- positions
  - code (PK), qty, avg_price, current_price, updated_at
  - idx_positions_updated_at

- risk_logs
  - logged_at, event_type, metric_name, metric_value, threshold, detail
  - 各種インデックスあり

- dashboard
  - 単一行（id=1）で集計を記録: updated_at, portfolio_value, cash, drawdown_pct, open_order_count, position_count, peak_value

---

## 主要ディレクトリ構成

（src/kabusys 配下の主要ファイルを抜粋）

- src/kabusys/
  - __init__.py
  - config.py                     — 環境変数 / Settings 管理
  - run_monitoring.py             — SystemMonitor ポーリング起動スクリプト
  - run_execution.py              — ExecutionEngine 起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート用 CLI
  - monitoring/
    - __init__.py
    - monitoring_db.py             — SQLite 永続化層（init + MonitoringDB）
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py
    - monitoring_engine.py
    - streamlit_dashboard.py
  - execution/
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - execution_engine.py (省略ファイルがある前提)
    - broker_factory.py, broker_api.py, order_record.py, ...（発注関連）
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py
  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py
  - ai/
    - news_nlp.py
    - regime_detector.py
    - __init__.py
  - utils/
    - process_priority.py
    - __init__.py
  - data/ (実行時に利用する DB / フラグ類)
    - monitoring.db (デフォルト SQLITE_PATH)
    - paper_trading.db (paper trading 用)
    - kabusys.duckdb (DuckDB path)
    - stop_requested.flag, kill.flag, execution.pid など（ランタイム制御）

---

## 開発・運用上の注意

- AI 機能を使う (news_nlp / regime_detector) 場合は OpenAI の API キー（OPENAI_API_KEY）が必要です。API 呼び出しは失敗時のフォールバックを持ちますが、結果の信頼性は API に依存します。
- run_monitoring は本番の監視 DB を参照するため、Paper trading 環境でも監視ログは production path に記録されます（設計上の意図）。
- process priority / CPU affinity の設定はプラットフォームに依存し、権限不足や未対応 OS の場合は警告が出てスキップされます。
- DuckDB / SQLite のファイルパスは Settings で簡単に切り替え可能です。CI やローカルテストでは別のデータファイルを指定してください。
- .env の自動ロードはプロジェクトルートを検出して行います。テストや特殊な起動方法では KABUSYS_DISABLE_AUTO_ENV_LOAD を使って制御できます。

---

README に書いた内容はコードの注釈や docstring をベースにまとめています。実運用に移す場合はセキュリティ（API キーの管理）、モニタリングのアラート設定、Broker クライアントの実装・検証、バックアップ・リカバリ方針などを必ず整備してください。

必要であれば、README に追記する実例の .env.example、docker-compose 構成、systemd ユニットファイルや unit テンプレート、CI/CD の手順なども作成できます。どの情報が欲しいか教えてください。