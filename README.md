# KabuSys

日本株向け自動売買フレームワークの一部実装リポジトリ（ミニマム実装）。  
この README はリポジトリ内の主要コンポーネント（監視・実行エンジン、ポートフォリオ構築、リサーチ、AI ニュース解析など）についての概要、セットアップ、使い方、ディレクトリ構成をまとめたものです。

---

## プロジェクト概要

KabuSys は日本株の自動売買を支援するライブラリ群・ランタイムコンポーネント群です。本コードベースには以下の主要機能を含みます。

- ExecutionEngine 起動スクリプトと注文管理（Execution）
- 監視（Monitoring）：システム状態、注文滞留、リスク（ドローダウン・ポジション上限）監視、アラート
- Portfolio Construction：候補選定・重み計算・ポジションサイズ算出・セクター制約
- Research：ファクター計算、将来リターン・IC 計算、統計サマリ
- AI：ニュースを LLM（OpenAI）でスコアリングする機能、レジーム判定
- ツール：Paper Trading 検証レポート生成、Streamlit ダッシュボード等

設計上の特徴:
- DuckDB / SQLite を使って履歴データ・メタデータを管理
- Paper Trading と Live（本番）を分離（専用 SQLite を利用）
- OpenAI API を用いたニュース NLP（gpt-4o-mini を想定）
- プロセス優先度（High）設定、停止フラグファイルによる安全停止

---

## 機能一覧

- 実行（Execution）
  - ExecutionEngine の起動/停止（run_execution.py）
  - ブローカークライアントのファクトリ（Mock / 実ブローカー切替）
  - 注文管理（OrderManager）、リコンシリエーション（Reconciler）

- 監視（Monitoring）
  - SystemMonitor：CPU/メモリ/ディスク、データ鮮度、Execution プロセス存在確認
  - TradeMonitor：滞留注文、約定価格の異常検知
  - RiskMonitor：ドローダウン・ポジション上限検知
  - KillSwitch：重大リスクで実行エンジン停止のためのフラグファイル書込み
  - AlertManager：LINE への通知（クールダウン管理）
  - Streamlit ベースの監視ダッシュボード

- ポートフォリオ構築
  - 候補選定（score 降順 + tie-break）
  - 均等 / スコア加重配分
  - リスクベースのポジションサイズ計算（単元丸め・aggregate cap）
  - セクターキャップ適用、レジーム乗数

- リサーチ
  - Momentum / Volatility / Value ファクター計算（DuckDB 上の prices_daily / raw_financials を参照）
  - Forward returns, IC（Spearman）, 統計サマリ

- AI
  - news_nlp.score_news(): raw_news を集約して OpenAI で銘柄ごとセンチメントを算出し ai_scores に保存
  - regime_detector.score_regime(): MA200 とマクロニュースセンチメントを合成して日次レジーム判定（market_regime へ保存）

- ツール
  - Paper Trading 検証レポート出力（kabusys.tools.paper_verification_report）
  - Streamlit ダッシュボード（監視用）

---

## 必要要件（例）

- Python 3.10+
- 必要なパッケージ（抜粋）
  - duckdb
  - psutil
  - requests
  - openai
  - streamlit
- SQLite（組み込み）
- ネットワーク接続（LINE API / OpenAI を使用する場合）

※ requirements.txt は本リポジトリに含めていない場合があります。プロジェクトで利用しているライブラリを上記を参考にインストールしてください。

---

## セットアップ手順（ローカル開発向け）

1. リポジトリをクローン / 作業ディレクトリへ移動

2. 仮想環境を作成・有効化（例）
   - python -m venv .venv
   - source .venv/bin/activate  (macOS/Linux)
   - .venv\Scripts\activate     (Windows)

3. 必要パッケージをインストール
   - pip install duckdb psutil requests openai streamlit

   （プロジェクトで requirements.txt がある場合は pip install -r requirements.txt）

4. データディレクトリ作成
   - mkdir -p data

5. 環境変数設定
   - プロジェクトルートに .env を置く（自動読み込み機能あり）。例: .env
     - KABUSYS_ENV=development|paper_trading|live
     - JQUANTS_REFRESH_TOKEN=...
     - KABU_API_PASSWORD=...
     - OPENAI_API_KEY=...
     - LINE_CHANNEL_ACCESS_TOKEN=...
     - LINE_USER_ID=...
     - PAPER_FILL_MODE=instant|partial|never|reject
     - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
     - DUCKDB_PATH=data/kabusys.duckdb
     - SQLITE_PATH=data/monitoring.db
     - MONITOR_POLL_INTERVAL=60
     - LOG_LEVEL=INFO
     - など（詳細は下の「環境変数」を参照）

6. DB 初期化
   - run_monitoring.py / run_execution.py は起動時に monitoring DB スキーマを作成します（init_monitoring_db を呼び出すため、手動で初期化する必要は基本的にありません）。

---

## 環境変数（主なもの）

- KABUSYS_ENV: development / paper_trading / live（default: development）
- JQUANTS_REFRESH_TOKEN: J-Quants API（必須）
- KABU_API_PASSWORD: kabuステーション API のパスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: AlertManager の LINE 通知に使用
- PAPER_FILL_MODE: paper_trading 時のモック約定動作（instant|partial|never|reject）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（default: data/paper_trading.db）
- DUCKDB_PATH: DuckDB ファイルパス（default: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（default: data/monitoring.db）
- MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、default: 60）
- PID_FILE_PATH: ExecutionEngine の PID ファイルパス（default: data/execution.pid）
- KILL_FLAG_PATH: KillSwitch の flag ファイルパス（default: data/kill.flag）
- CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT: 監視の閾値
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 1 を設定すると .env 自動ロードを無効化

Settings クラス（kabusys.config.Settings）で多くの設定をラップしています。設定値が必須の場合は起動時に ValueError が投げられます。

---

## 使い方（実行例）

1. 監視ループ（Monitoring）
   - 役割: SystemMonitor を使ってシステム状態を定期記録し、トリガーがあれば KillSwitch / Alert を起動します。
   - 実行:
     - python -m kabusys.run_monitoring
     - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を変更可能（例: export MONITOR_POLL_INTERVAL=30）

   - 実行時のポイント:
     - run_monitoring は Settings に依存し、監視の DB は Settings.sqlite_path（デフォルト data/monitoring.db）を使用します。
     - 起動時にプロセス優先度を High に設定しようとします（psutil が必要）。

2. 実行エンジン（ExecutionEngine）
   - 役割: ブローカーへ発注、注文管理、リスク管理、リコンシリエーションを行うメインエンジン。
   - 実行:
     - python -m kabusys.run_execution
   - 特記事項:
     - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使い Paper Trading 用の専用 SQLite（PAPER_TRADING_SQLITE_PATH = data/paper_trading.db など）に記録します（本番 DB と分離）。
     - 実行中は PID ファイル（data/execution.pid）を作成します。停止は stop flag（data/stop_requested.flag）や kill.flag によって制御されます。

3. Streamlit 監視ダッシュボード
   - 起動方法:
     - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
   - read-only で SQLite を開きダッシュボードを表示します（Monitoring が書き込んでいる DB を参照）。

4. Paper Trading 検証レポート
   - 実行:
     - python -m kabusys.tools.paper_verification_report
     - 期間指定: python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
     - DB パス指定: --db /path/to/paper_trading.db（環境変数 PAPER_TRADING_SQLITE_PATH でも指定可）
   - 出力: 標準出力に稼働率・注文成功率・レイテンシ等の集計と PASS/FAIL 判定を表示します。

5. AI 機能（ニュース NLP / レジーム判定）
   - news_nlp.score_news(conn, target_date, api_key=None)
     - 引数: DuckDB 接続（DuckDBPyConnection）、target_date（date）、api_key（OpenAI API key, None なら OPENAI_API_KEY 環境変数を使用）
     - 処理: raw_news を銘柄ごとに集約し、OpenAI にバッチ送信して ai_scores テーブルに結果を書き込む
   - regime_detector.score_regime(conn, target_date, api_key=None)
     - ETF 1321 の MA200 乖離とマクロニュースの LLM スコアを組み合わせ market_regime テーブルへ書き込み

---

## 停止・制御ファイル

- data/stop_requested.flag
  - run_monitoring.py / run_execution.py はこのファイルの存在を検知して安全にループを終了します（外部から停止させたい場合に利用）。

- data/kill.flag
  - KillSwitch が危険閾値を満たした際に書き込むファイル。ExecutionEngine の停止トリガーとして利用されます。Settings.kill_flag_clear_on_start を参照して起動時に自動クリアする挙動を制御できます。

- PID ファイル: data/execution.pid
  - ExecutionEngine 起動時に PID を保存。SystemMonitor は PID 存在とプロセス実存性をチェックして stale PID を検出・削除します。

---

## 開発時の注意点・設計ノート

- 設計はルックアヘッドバイアス防止を考慮しており、AI / リサーチ系関数は内部で datetime.today() を直接参照しない実装になっています（target_date を明示的に渡す）。
- Monitoring の DB スキーマ変更は init_monitoring_db() でマイグレーション的処理を行います（冪等）。
- OpenAI API への呼び出しは頑健化（429・タイムアウト・5xx に対する指数バックオフ）されていますが、API キーの設定漏れは ValueError を投げます。
- Paper Trading と Live は DB を完全に分離する設計になっています（settings.is_paper により切替）。
- PID / ファイルの操作や psutil によるプロセス制御は権限に左右されるため、実行時のユーザー権限に注意してください。

---

## 主要ディレクトリ構成

（ソースは src/kabusys 配下）

- src/kabusys/
  - __init__.py
  - config.py                        — 環境変数 / Settings 管理
  - run_monitoring.py                — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py                 — ExecutionEngine 起動スクリプト

  - execution/
    - broker_api.py (想定)
    - broker_factory.py
    - execution_engine.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
    - order_record.py
    - order_repository.py
    - ...（注文・ブローカー関連）

  - monitoring/
    - monitoring_db.py                — SQLite 永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py
    - monitoring_engine.py
    - streamlit_dashboard.py

  - portfolio/
    - portfolio_builder.py
    - risk_adjustment.py
    - position_sizing.py
    - __init__.py

  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py

  - ai/
    - news_nlp.py
    - regime_detector.py
    - __init__.py

  - tools/
    - paper_verification_report.py
    - __init__.py

  - utils/
    - process_priority.py
    - __init__.py

- data/                               — デフォルトの DB / PID / flag ファイル置き場（実行時に作成）
  - monitoring.db (SQLite)
  - paper_trading.db (SQLite, paper_trading 用)
  - kabusys.duckdb (DuckDB)
  - execution.pid
  - kill.flag / stop_requested.flag

---

## よくある操作例（まとめ）

- 監視を起動（デフォルト 60 秒間隔）
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- 実行エンジンを起動（paper_trading モード）
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution

- Streamlit ダッシュボード起動
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

- Paper Trading レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

- AI ニューススコア（Python REPL / スクリプト内）
  - import duckdb, datetime
  - conn = duckdb.connect("data/kabusys.duckdb")
  - from kabusys.ai.news_nlp import score_news
  - score_news(conn, datetime.date(2026, 4, 10), api_key="sk-...")

---

## トラブルシューティング

- psutil による優先度設定失敗や CPU affinity 設定失敗は権限不足でワーニングになります（処理は続行します）。
- OpenAI キーが未設定だと AI 機能は ValueError を投げます。テスト時は該当機能をモックしてください。
- DuckDB / SQLite ファイルがロックされている場合、別プロセスが DB を占有しているか確認してください（Streamlit や別のプロセスの接続）。
- stop_requested.flag / kill.flag を用いた強制停止はファイルの存在確認に依存するため、ファイルの削除や作成に対する権限に注意してください。

---

この README はコードベースの主要な利用方法と設計意図を簡潔にまとめたものです。各モジュールは docstring とログ出力により詳細な動作説明を含んでいるため、実際に動かしながら該当モジュールの docstring を参照してください。必要であれば README に追記・改善を行います。