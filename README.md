# KabuSys

日本株向けの自動売買フレームワーク（モジュール群）の README。  
本ドキュメントはリポジトリ内の主要スクリプト・モジュールの概要、セットアップ、起動方法、ディレクトリ構成を日本語でまとめたものです。

注意: 実際の取引や API キーを扱うため、本プロジェクトを本番で使う場合は十分なテスト・レビューを行ってください。

---

## プロジェクト概要

KabuSys は日本株の自動売買（Execution）・監視（Monitoring）・リサーチ（Research）・AI ベースのニュース分析（AI）などを含むモジュール群です。  
主な設計方針：

- DuckDB / SQLite を使ったデータ処理・永続化
- Execution と Monitoring は明確に分離（paper_trading 環境時は本番 DB と分離）
- OpenAI（gpt-4o-mini）を用いたニュースセンチメントや市場レジーム判定機能（API キー必要）
- フェイルセーフ設計（API 失敗時はフォールバックやスキップで継続）

バージョン: __version__ = 0.1.0

---

## 機能一覧

- Execution
  - ExecutionEngine 起動スクリプト（run_execution.py）
  - OrderManager / OrderRepository による発注管理
  - Reconciler による起動時の自動復旧（ブローカー照合）
  - RiskManager によるリスク制御（上限比率・レート制限等）
  - paper_trading 環境における MockBroker と専用 SQLite（data/paper_trading.db）

- Monitoring
  - SystemMonitor: CPU/メモリ/ディスク、プロセス生存、データ鮮度監視
  - TradeMonitor: 滞留注文、約定異常価格の検出
  - RiskMonitor: ドローダウン・ポジション数監視、ダッシュボード更新とリスクログ
  - KillSwitch: 条件に応じて data/kill.flag を書いて ExecutionEngine 停止シグナルを発行
  - AlertManager: LINE push による通知（トークン未設定時はログのみ）
  - streamlit ベースの監視ダッシュボード

- Research / Portfolio
  - ファクター計算（momentum / volatility / value）
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリ
  - ポートフォリオ候補選定、重み計算、ポジションサイズ計算（単元株取り扱い、スケール調整）
  - セクターキャップ・レジーム乗数

- AI
  - ニュースセンチメント（OpenAI）を銘柄ごとに評価して ai_scores に保存
  - 市場レジーム判定（MA200 乖離 + マクロニュースセンチメント）

- ユーティリティ
  - Settings（環境変数読み込み・検証・デフォルト）
  - process_priority: プラットフォーム差異を吸収してプロセス優先度 / CPU affinity 設定
  - 各種ツールスクリプト（paper_trading 検証レポート生成等）

---

## セットアップ手順（開発環境向け）

1. リポジトリをクローンし、プロジェクトルートに移動します。
   - 本リポジトリは src/ 配下にパッケージがある想定です。Python の import が通るようにするには以下のいずれかを行ってください：
     - pip install -e . （setup.py/pyproject が存在する場合）
     - PYTHONPATH を設定： export PYTHONPATH=$(pwd)/src
     - または実行時に python -m で実行（下記参照）

2. Python 環境（推奨: 3.10+）を用意し、依存パッケージをインストールします（例）:
   - duckdb
   - psutil
   - openai
   - requests
   - streamlit
   - 例: pip install duckdb psutil openai requests streamlit

   （実際の requirements.txt があれば pip install -r requirements.txt を使用してください）

3. 環境変数の設定
   - プロジェクトルートの .env / .env.local を用意すると、config.Settings が自動的にロードします（OS 環境変数が優先）。
   - 自動ロードを無効化する場合: KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定
   - 主要な環境変数（例）:
     - JQUANTS_REFRESH_TOKEN — 必須（J-Quants API）
     - KABU_API_PASSWORD — 必須（kabuステーション API）
     - OPENAI_API_KEY — ニュース NLP / regime 用（AI 機能）
     - KABUSYS_ENV — development | paper_trading | live（デフォルト: development）
     - PAPER_FILL_MODE — paper_trading の約定振る舞い（instant|partial|never|reject）
     - PAPER_TRADING_SQLITE_PATH — paper_trading 用 SQLite（デフォルト: data/paper_trading.db）
     - DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
     - PID_FILE_PATH, KILL_FLAG_PATH, LOG_LEVEL, LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID

4. データディレクトリの作成
   - data/ ディレクトリを作成しておくと便利です（デフォルト DB ファイルは data/ 以下に作られます）。
     - mkdir -p data

---

## 使い方（主要スクリプト・例）

実行はプロジェクトルートから行うことを想定しています。PYTHONPATH に src を含めるか、パッケージとしてインストールしてから実行してください。

1. Monitoring ポーリングを起動（常駐）
   - デフォルトのポーリング間隔は 60 秒。環境変数で変更可能: MONITOR_POLL_INTERVAL
   - 実行例:
     - python -m kabusys.run_monitoring
   - 挙動:
     - process 優先度を "high" に設定（可能なら）
     - Settings から sqlite_path（監視 DB）/ duckdb_path を読み接続
     - monitoring DB のテーブルを init（init_monitoring_db）
     - SystemMonitor.check_once() をループで実行して system_status / risk_logs / dashboard 等を更新
   - 環境変数例:
     - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

2. ExecutionEngine を起動（発注エンジン）
   - 実行例:
     - python -m kabusys.run_execution
   - KABUSYS_ENV が paper_trading の場合、MockBrokerClient を使用し paper_trading 専用 DB（PAPER_TRADING_SQLITE_PATH）に記録します（本番 DB と分離）。
   - 起動時に Reconciler による照合や RiskManager の初期化が行われ、ExecutionEngine.run_session() が呼ばれます。

3. Streamlit 監視ダッシュボード
   - 起動例:
     - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
   - 読み取り専用で monitoring DB を表示。MonitoringEngine が書き込むデータを可視化します。

4. Paper Trading 検証レポート生成ツール
   - 実行例:
     - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
     - または DB を明示:
       python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
   - レポートは標準出力に出力され、稼働率 / 注文成功率 / 送信率 / レイテンシ (P95) などの指標を表示・PASS/FAIL 判定します。

5. AI 機能（ニューススコア・レジーム判定）
   - OpenAI API キーが必要（OPENAI_API_KEY 環境変数または関数引数）
   - モジュール API（プログラムから呼ぶ例）:
     - from kabusys.ai.news_nlp import score_news
       score_news(conn, target_date, api_key=None)
     - from kabusys.ai.regime_detector import score_regime
       score_regime(conn, target_date, api_key=None)
   - 両機能とも DB（DuckDB）を読み書きします。失敗時はフォールバック動作（スコア=0 やスキップ）があります。

---

## 設定の振る舞い（Settings）

- 環境変数は自動で .env/.env.local から読み込まれます（OS 環境変数 > .env.local > .env）。
- 自動読み込みを無効化するには: KABUSYS_DISABLE_AUTO_ENV_LOAD=1
- Settings はいくつかの値をバリデーションします（KABUSYS_ENV, PAPER_FILL_MODE, LOG_LEVEL 等）。未設定の必須キーは ValueError を投げます。
- デフォルトパス:
  - DUCKDB_PATH: data/kabusys.duckdb
  - SQLITE_PATH: data/monitoring.db
  - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
  - PID_FILE_PATH: data/execution.pid
  - KILL_FLAG_PATH: data/kill.flag

---

## 監視 DB（Monitoring DB）スキーマ概略

init_monitoring_db により作成される主要テーブル（冪等で作成）:

- system_status: cpu_percent, memory_percent, disk_percent, process_ok, recorded_at
- trade_logs: 発注イベントログ（event_type, client_order_id, code, side, qty, price, filled_qty, state, latency_ms）
- positions: 保有ポジションテーブル（code, qty, avg_price, current_price, updated_at）
- risk_logs: リスクイベント（event_type, metric_name, metric_value, threshold, detail）
- dashboard: 集計（id=1 固定） — portfolio_value, cash, drawdown_pct, open_order_count, position_count, peak_value

MonitoringDB クラスが読み書き API を提供します（log_system_status / log_trade_event / upsert_position / log_risk_event / upsert_dashboard / get_dashboard）。

---

## 実行時の注意点

- run_monitoring / run_execution は起動直後に set_process_priority("high") を試みます。プラットフォームや権限により失敗する場合は警告が出ますが処理は継続します。
- Monitoring は KABUSYS_ENV に依らずデフォルトの sqlite_path（本番パス）を使用します。Execution は paper_trading 時は別 DB を使用します。
- KillSwitch は条件を満たすと data/kill.flag を書き込みます。ExecutionEngine 起動時に kill.flag が残っていると影響があるため、Settings.kill_flag_clear_on_start を使うか起動前に手動で削除してください。
- OpenAI を使う機能は API 利用制限やエラーを想定しており、429/ネットワーク断/タイムアウト/5xx に対しては指数バックオフでリトライします。その他はスキップして継続します。
- DuckDB への書き込みは executemany の空リストに注意（古い DuckDB バージョンではエラー） — コード内でガードがされています。

---

## ディレクトリ構成（主要ファイル）

以下は src/kabusys 以下の主要モジュールのツリー（抜粋）:

- src/
  - kabusys/
    - __init__.py
    - config.py                       # Settings / .env 自動ロード
    - run_monitoring.py               # Monitoring ポーリング起動
    - run_execution.py                # ExecutionEngine 起動
    - tools/
      - __init__.py
      - paper_verification_report.py  # paper_trading 検証レポート（CLI）
    - monitoring/
      - __init__.py
      - monitoring_db.py              # MonitoringDB（SQLite スキーマ + API）
      - system_monitor.py
      - trade_monitor.py
      - risk_monitor.py
      - kill_switch.py
      - alert_manager.py
      - monitoring_engine.py
      - streamlit_dashboard.py
    - execution/
      - order_manager.py
      - order_repository.py           # （OrderRepository 実装あり）
      - reconciler.py
      - execution_engine.py           # Engine 実装本体（起動は run_execution）
      - broker_factory.py
      - broker_api.py
      - order_record.py
      - order_repository.py
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
    - ai/
      - __init__.py
      - news_nlp.py
      - regime_detector.py
    - utils/
      - __init__.py
      - process_priority.py
    - data/ (参照されるが実体は別)
      - pipeline.py (get_last_price_date などを参照)
      - stats.py (zscore_normalize 等)

（リポジトリ全体を参照し、足りないモジュールや DB スキーマは実際のプロジェクトに合わせて補完してください）

---

## よくある操作例

- 監視 DB の初期化（run_monitoring 実行時に自動で init されます）
- paper_trading レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- Streamlit ダッシュボード:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
- Monitoring の短周期テスト（環境変数）:
  - MONITOR_POLL_INTERVAL=10 python -m kabusys.run_monitoring

---

## 最後に / 開発者向けメモ

- .env.example を用意して主要な環境変数をドキュメント化すると運用が容易になります。
- DuckDB / SQLite のバージョン互換性に注意してください（executemany の仕様差分など）。
- OpenAI API 呼び出し部分はテストのために _call_openai_api を patch して差し替え可能に設計されています。
- セキュリティ: API キーやパスワードは .env に平文で置かれる場合があるため、アクセス権限や Vault の利用を検討してください。

---

README に不足している情報（依存関係の exact list、実行時のログ設定、Engine の追加オプション等）があれば、該当箇所の補足を作成します。必要な情報やフォーマット指定があれば教えてください。