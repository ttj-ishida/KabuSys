# KabuSys

日本株自動売買システムのコアライブラリ（リサーチ、ポートフォリオ構築、監視、実行エンジン、AI ニュース評価など）。  
この README ではプロジェクト概要、機能、セットアップ手順、主要な使い方例、ディレクトリ構成を日本語でまとめます。

---

## プロジェクト概要

KabuSys は日本株を対象とした自動売買システムのコアコンポーネント群です。DuckDB / SQLite をデータ層として利用し、以下の主要機能を提供します。

- 定量ファクター計算（モメンタム・ボラティリティ・バリュー等）
- ポートフォリオ構築（候補選定、重み計算、株数決定、セクター制限）
- ニュースを用いた LLM ベース（OpenAI）によるセンチメント評価と市況レジーム判定
- 注文管理（OrderManager, Reconciler）とブローカー API 抽象化
- 監視機能（システム状態・注文滞留・ドローダウン検出）および LINE 通知
- Streamlit ベースの監視ダッシュボード

設計方針として、DB 参照は限定的（research は DuckDB のみ、監視は SQLite のみ）かつテストしやすい純粋関数／軽量クラスを多用しています。API キーや設定は環境変数／.env から読み込む仕組みを備えています。

---

## 主な機能一覧

- research/
  - calc_momentum / calc_volatility / calc_value：DuckDB の prices_daily / raw_financials テーブルからファクター計算
  - calc_forward_returns / calc_ic / factor_summary：特徴量探索・IC 計算
- portfolio/
  - select_candidates / calc_equal_weights / calc_score_weights：候補選定と重み計算
  - calc_position_sizes：株数計算（リスクベース / 等分配 / スコア加重）
  - apply_sector_cap / calc_regime_multiplier：セクター上限・レジーム乗数
- ai/
  - score_news：raw_news を集約して OpenAI（gpt-4o-mini）で銘柄別センチメント評価 → ai_scores に保存
  - score_regime：ETF（1321）MA とマクロニュース LLM を合成して market_regime に書き込み
- execution/
  - ExecutionEngine：シグナル読み込み → Gate 検査 → 発注ループ（push ドレイン含む）
  - OrderManager / Reconciler：DB 永続化を含む注文状態管理と起動時自動復旧
  - broker_api：ブローカー抽象（OrderRequest, OrderStatus, Position 等）
- monitoring/
  - MonitoringDB：SQLite テーブル定義・読み書きユーティリティ
  - SystemMonitor / TradeMonitor / RiskMonitor：定期チェックとアラート生成
  - AlertManager：LINE push による通知（クールダウン管理）
  - streamlit_dashboard.py：監視ダッシュボード（Streamlit）
- 設定管理
  - kabusys.config: .env / 環境変数の読み込みと Settings オブジェクト

---

## セットアップ手順

※以下は一般的なセットアップ例です。環境や要件に合わせて調整してください。

1. Python を用意
   - 推奨: Python 3.10 以降

2. 仮想環境の作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   - 最低限必要なライブラリ（例）:
     - duckdb
     - openai
     - requests
     - psutil
     - streamlit (ダッシュボード使用時)
   - インストール例:
     - pip install duckdb openai requests psutil streamlit

   （プロジェクトに requirements.txt / pyproject.toml がある場合はそちらを参照してください）

4. 環境変数 / .env の設定
   - プロジェクトルート（.git または pyproject.toml のあるディレクトリ）が存在する場合、kabusys.config は自動で `.env` と `.env.local` を読み込みます（優先度: OS 環境変数 > .env.local > .env）。自動読み込みを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
   - 主要な環境変数（よく使うもの）:
     - JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須な機能がある場合）
     - KABU_API_PASSWORD: kabu ステーション API パスワード（必須）
     - KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
     - OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合）
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE 通知用（任意）
     - DUCKDB_PATH: DuckDB ファイル（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH: 監視 DB（デフォルト: data/monitoring.db）
     - PAPER_FILL_MODE: Paper Trading の fill モード（instant|partial|never|reject）
     - PAPER_TRADING_SQLITE_PATH: Paper trading 用 SQLite（デフォルト: data/paper_trading.db）
     - PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT など（監視関連）
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
     - LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）
   - シンプルな .env 例:
     ```
     JQUANTS_REFRESH_TOKEN=xxxxx
     KABU_API_PASSWORD=your_kabu_password
     OPENAI_API_KEY=sk-xxxx
     DUCKDB_PATH=data/kabusys.duckdb
     SQLITE_PATH=data/monitoring.db
     LINE_CHANNEL_ACCESS_TOKEN=
     LINE_USER_ID=
     KABUSYS_ENV=development
     LOG_LEVEL=DEBUG
     ```

5. 監視 DB の初期化（SQLite）
   - Python から実行:
     ```
     python -c "import sqlite3; from kabusys.monitoring.monitoring_db import init_monitoring_db; conn=sqlite3.connect('data/monitoring.db'); init_monitoring_db(conn); conn.close()"
     ```
   - これにより監視用のテーブル（system_status, trade_logs, positions, risk_logs, dashboard 等）が作成されます。

---

## 使い方（主要な例）

以下はライブラリの代表的な使い方例です。各機能はモジュール単位でインポートして利用します。

- 環境設定の取得
  ```python
  from kabusys.config import settings
  print(settings.jquants_refresh_token)  # 必須環境変数がなければ ValueError
  print(settings.duckdb_path)            # Path オブジェクト
  ```

- Streamlit 監視ダッシュボード起動
  ```
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  ```
  - 引数 `--db` で SQLite DB パスを指定（既定: data/monitoring.db）。監視デーモンが書き込んだ監視情報を read-only で表示します。

- AI ニューススコアリング（例）
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai import score_news

  conn = duckdb.connect('data/kabusys.duckdb')
  # target_date に対する前日15:00～当日08:30 JST の記事を対象にスコアを計算して ai_scores テーブルに書き込む
  count = score_news(conn, date(2026, 3, 20), api_key=None)  # api_key None -> OPENAI_API_KEY を参照
  print(f"scored {count} codes")
  ```

- 市場レジーム判定（例）
  ```python
  from kabusys.ai.regime_detector import score_regime
  import duckdb
  from datetime import date

  conn = duckdb.connect('data/kabusys.duckdb')
  score_regime(conn, date(2026, 3, 20))  # market_regime テーブルに結果を書き込む
  ```

- ファクター計算（research）
  ```python
  from kabusys.research import calc_momentum, calc_volatility, calc_value
  import duckdb
  from datetime import date

  conn = duckdb.connect('data/kabusys.duckdb')
  target = date(2026, 3, 20)
  mom = calc_momentum(conn, target)
  vol = calc_volatility(conn, target)
  val = calc_value(conn, target)
  ```

- ポートフォリオ（候補選定・重み・株数決定）
  ```python
  from kabusys.portfolio import select_candidates, calc_score_weights, calc_position_sizes

  buy_signals = [{"code":"1234","signal_rank":1,"score":0.8}, ...]
  candidates = select_candidates(buy_signals, max_positions=10)
  weights = calc_score_weights(candidates)
  sizes = calc_position_sizes(
      weights=weights,
      candidates=candidates,
      portfolio_value=10_000_000,
      available_cash=7_000_000,
      current_positions={},
      open_prices={"1234": 1500.0},
      allocation_method="score",
  )
  ```

- 監視 DB 直接利用
  ```python
  import sqlite3
  from kabusys.monitoring.monitoring_db import MonitoringDB, init_monitoring_db

  conn = sqlite3.connect("data/monitoring.db")
  init_monitoring_db(conn)  # 初期化（冪等）
  db = MonitoringDB(conn)
  db.log_system_status(cpu_percent=10.5, memory_percent=30.0, disk_percent=40.0, process_ok=True)
  ```

- 実運用の ExecutionEngine / OrderManager 等は外部ブローカー実装や OrderRepository（SQLite）などの依存があるため、単体で完結する簡単な呼び出し例はここでは割愛します。コードを参照して各依存を実装してください。

---

## 設定の自動読み込み

- kabusys.config はプロジェクトルート（このファイルの親階層で .git または pyproject.toml が見つかる場所）を探索し、`.env` / `.env.local` を自動読み込みします。優先度は:
  1. OS 環境変数
  2. .env.local
  3. .env
- 自動読み込みを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。
- Settings プロパティは必須値のチェック（_require）や値の検証（PAPER_FILL_MODE, KABUSYS_ENV, LOG_LEVEL など）を行います。値が不正な場合は ValueError が発生します。

---

## ディレクトリ構成（抜粋）

以下は本リポジトリの主要なファイル／モジュール構成（src 以下）です。実際のツリーはさらに多くのファイルを含む可能性があります。

- src/kabusys/
  - __init__.py
  - config.py
  - ai/
    - __init__.py
    - news_nlp.py
    - regime_detector.py
  - portfolio/
    - __init__.py
    - portfolio_builder.py
    - risk_adjustment.py
    - position_sizing.py
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - monitoring/
    - __init__.py
    - monitoring_db.py
    - monitoring_engine.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - alert_manager.py
    - kill_switch.py
    - streamlit_dashboard.py
  - execution/
    - broker_api.py
    - execution_engine.py
    - order_manager.py
    - reconciler.py
    - (その他 OrderRepository / order_record 等)
  - (data/, strategy/ 等のサブパッケージが存在する可能性あり)

---

## 注意事項・運用上のポイント

- AI（OpenAI）機能は API キーが必須です。API 呼び出しで失敗した場合はフェイルセーフの挙動（0.0 フォールバック、処理継続など）を多く実装していますが、運用では API レートやコストに注意してください。
- ExecutionEngine / OrderManager は「実際の発注」を行うため、ブローカー API 実装（BrokerAPIProtocol を満たすクラス）が必要です。テスト時はモック実装を使ってください。
- kill flag（KABUSYS の kill.switch 機能）はファイルベースです（デフォルト: data/kill.flag）。起動時に存在する場合の挙動は Settings.kill_flag_clear_on_start に依存します。
- DB 書き込み（特に ai_scores / market_regime 等）はトランザクションで冪等性を保つ実装になっていますが、DB バージョンや接続の違いで挙動が変わる可能性があります（DuckDB / SQLite）。運用前に検証してください。

---

## 参考 / 開発者向け

- 各モジュールは単体でテストしやすい設計（純粋関数、DB 接続注入、OpenAI 呼び出しのラッパー化）になっています。ユニットテスト時は外部呼び出し（OpenAI / ブローカー API / psutil）をモックしてください。
- .env のパースは kabusys.config の内部実装に依存します。特殊なエスケープやコメントルールがあるため複雑な .env を使う場合は注意してください。

---

この README は主要な使い方に焦点を当てています。詳細な実装・API（OrderRepository のスキーマや BrokerAPIProtocol の詳細等）は各モジュールの docstring を参照してください。必要であれば README を拡張して「デプロイ手順」「ブローカー実装例」「ローカルでの end-to-end 実行例」などを追加できます。