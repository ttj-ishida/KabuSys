# KabuSys

短い説明:
KabuSys は日本株向けの自動売買・リサーチ・監視用ライブラリ群です。戦略のファクター計算、ポートフォリオ構築、発注エンジン、監視ダッシュボード、LLM（OpenAI）を使ったニュースセンチメント評価などのコンポーネントを含みます。各モジュールは純粋関数または明確に分離された I/O 層で構成されており、テストしやすく設計されています。

---

## 主な機能一覧

- 環境変数 / .env の自動読み込みと設定管理（kabusys.config）
  - 自動読み込みはプロジェクトルート（.git または pyproject.toml）を探索して .env / .env.local を読み込みます
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能
- ポートフォリオ構築（kabusys.portfolio）
  - 候補選択 (select_candidates)
  - 等重・スコア加重の重み算出 (calc_equal_weights / calc_score_weights)
  - 位置サイズ計算（リスクベース、上限・単元丸め、コストバッファ等）(calc_position_sizes)
  - セクター上限適用、レジーム乗数 (apply_sector_cap / calc_regime_multiplier)
- リサーチ（kabusys.research）
  - モメンタム / ボラティリティ / バリュー等のファクター計算（DuckDB 接続を受け取る純粋関数）
  - 将来リターン計算、IC（情報係数）算出、ファクター統計サマリ
  - z-score 正規化ユーティリティ参照
- AI（kabusys.ai）
  - ニュース記事の LLM センチメントスコアリング（OpenAI を使用）(news_nlp.score_news)
  - 市場レジーム判定（ETF ma200 とマクロニュースの LLM 結果を合成）(regime_detector.score_regime)
  - API 呼び出しに対するリトライ/バリデーション、結果は DuckDB に保存
- 発注 / 実行（kabusys.execution）
  - ブローカー API 抽象（Protocol）・データモデル・例外定義
  - OrderManager（DB と Broker の調停、2  相永続化パターン、再送・同期）
  - ExecutionEngine（シグナル処理 / push drain / kill-switch 実装）
  - 起動時の再整合（Reconciler）
- 監視（kabusys.monitoring）
  - SQLite を使った永続化層（MonitoringDB）
  - システム監視（CPU/Memory/Disk・データ鮮度）
  - 注文監視（滞留注文・約定異常）
  - リスク監視（ドローダウン・ポジション上限）
  - LINE へのアラート送信（AlertManager）
  - Streamlit ベースの監視ダッシュボード

---

## セットアップ手順（開発 / ローカル実行向け）

前提:
- Python 3.10+ を推奨（typing の | 記法や型ヒントを利用）
- git 等の基本ツール

1. リポジトリをクローン
   - git clone <リポジトリ URL>

2. 仮想環境を作成・有効化（例）
   - python -m venv .venv
   - source .venv/bin/activate  (Linux / macOS)
   - .venv\Scripts\activate     (Windows PowerShell)

3. 必要パッケージをインストール
   - 代表的な依存パッケージ:
     - duckdb
     - openai
     - psutil
     - requests
     - streamlit
   - pip でインストールする例:
     - pip install duckdb openai psutil requests streamlit

   （プロジェクトに requirements.txt がある場合はそれを使用してください）

4. 環境変数設定
   - プロジェクトルートに `.env` / `.env.local` を配置すると自動的に読み込まれます（.env.local は .env を上書き）
   - 自動読み込みを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定
   - 主要な環境変数（必要に応じて設定）:
     - JQUANTS_REFRESH_TOKEN — J-Quants 用トークン（必須な箇所で使用）
     - KABU_API_PASSWORD — Kabu API パスワード（必須）
     - KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
     - OPENAI_API_KEY — OpenAI API キー（AI モジュールで必須）
     - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID — LINE 通知用（任意）
     - DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
     - SQLITE_PATH — 監視 DB（デフォルト data/monitoring.db）
     - PAPER_FILL_MODE — paper trading の模擬約定モード（instant/partial/never/reject）
     - PAPER_TRADING_SQLITE_PATH, PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT, KABUSYS_ENV, LOG_LEVEL
   - .env の書式は shell 互換形式（コメント、export プレフィックス、クォートを扱います）。詳細は kabusys.config の実装を参照。

5. データベース（監視 DB）初期化（SQLite）
   - 監視 DB を初期化するには MonitoringDB の init_monitoring_db を使う:
     - Python スクリプト例:
       from pathlib import Path
       import sqlite3
       from kabusys.monitoring.monitoring_db import init_monitoring_db
       Path("data").mkdir(exist_ok=True)
       conn = sqlite3.connect("data/monitoring.db")
       init_monitoring_db(conn)
       conn.close()

6. DuckDB / データ投入
   - research や戦略実行は prices_daily / raw_financials / raw_news 等のテーブルを想定します。DuckDB に適切なテーブルを作成・データを投入してください。

---

## 使い方（主なユースケースの例）

- settings（環境設定）を使う
  - 例:
    from kabusys.config import settings
    token = settings.jquants_refresh_token
    duckdb_path = settings.duckdb_path

- ファクター計算（DuckDB 接続を渡す）
  - 例:
    import duckdb
    from datetime import date
    from kabusys.research import calc_momentum, calc_volatility, calc_value
    conn = duckdb.connect("data/kabusys.duckdb")
    res = calc_momentum(conn, date(2026, 3, 20))

- ニュース NLP スコアリング（OpenAI を使用）
  - 例:
    import duckdb
    from datetime import date
    from kabusys.ai.news_nlp import score_news
    conn = duckdb.connect("data/kabusys.duckdb")
    n_written = score_news(conn, date(2026, 3, 20), api_key="sk-...")

  - 注意: OPENAI_API_KEY を環境変数で設定しておけば api_key を省略できます。API 呼び出しはリトライ・バリデーションを行います。

- レジーム判定
  - 例:
    from kabusys.ai.regime_detector import score_regime
    score_regime(conn, date(2026, 3, 20))

- 監視ダッシュボード（Streamlit）
  - 起動コマンド例:
    streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

- 監視 DB API（MonitoringDB）
  - 例: MonitoringDB を使ってシステムステータスをログする
    from kabusys.monitoring.monitoring_db import MonitoringDB, init_monitoring_db
    import sqlite3
    conn = sqlite3.connect("data/monitoring.db")
    init_monitoring_db(conn)
    db = MonitoringDB(conn)
    db.log_system_status(cpu_percent=1.0, memory_percent=2.0, disk_percent=3.0, process_ok=True)

- ExecutionEngine（概要）
  - ExecutionEngine は BrokerAPIProtocol 実装、OrderRepository、RiskManager、OrderManager、DuckDB 接続、EngineConfig を受け取りセッションを実行します。実稼働では kill.flag チェック・PID 書き込み・WebSocket ドレイン等を行います。
  - テストでは run_session の代わりに _process_signals / _drain_push_queue を直接呼ぶことで単体テストを行えます。

---

## 自動 .env ロードの挙動

- プロジェクトルート（.git または pyproject.toml を含むディレクトリ）を、kabusys.config が __file__ を起点に探索して検出します。
- 見つかった場合、.env を先に読み込み（既存環境変数を上書きしない）、その後 .env.local を上書きモードで読み込みます。
- OS の既存環境変数は保護されます（上書きされません）。
- 自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト用途など）。

---

## ディレクトリ構成（主要ファイル）

src/kabusys/
- __init__.py
- config.py
- __version__ = "0.1.0"

サブパッケージ:
- ai/
  - news_nlp.py        — ニュースの LLM センチメント処理
  - regime_detector.py — 市場レジーム判定
  - __init__.py
- research/
  - factor_research.py     — momentum / volatility / value 等
  - feature_exploration.py — 将来リターン / IC / summary
  - __init__.py
- portfolio/
  - portfolio_builder.py  — 候補選定・重み算出
  - position_sizing.py    — 注文株数算出（リスク/単元丸め）
  - risk_adjustment.py    — セクター上限・レジーム乗数
  - __init__.py
- execution/
  - broker_api.py         — Broker API の型定義 / 例外 / データモデル
  - order_manager.py      — OrderState マネージャ
  - execution_engine.py   — メイン発注エンジン（セッション実行）
  - reconciler.py         — 起動時の同期ロジック
  - その他（order_record, order_repository 等は省略ファイル群として想定）
- monitoring/
  - monitoring_db.py      — SQLite スキーマ + MonitoringDB
  - system_monitor.py
  - trade_monitor.py
  - risk_monitor.py
  - kill_switch.py
  - alert_manager.py
  - monitoring_engine.py
  - streamlit_dashboard.py
  - __init__.py
- portfolio, research, ai, monitoring はそれぞれテスト可能な純粋関数／クラスで構成

その他:
- data/ — デフォルトの DB 保存先（DuckDB / monitoring.sqlite 等）
- .env.example （プロジェクトルートに用意することを推奨）

---

## 開発にあたっての注意点 / ベストプラクティス

- DuckDB や SQLite へのアクセスは接続オブジェクトを呼び出し側で作り渡す設計です。テスト時は in-memory DB を用いると良いです。
- LLM / ブローカー API 呼び出しは外部との I/O なのでテストではモックしてください（モジュール内で _call_openai_api 関数を patch する仕組みあり）。
- kill.flag / PID ファイルの扱いに注意してください（起動時に残存している場合は起動拒否または自動クリアの挙動があります）。
- 環境変数は .env / .env.local にまとめて管理し、自動ロード挙動を理解しておくと便利です。

---

もし README に追加したい内容（例: 実行例スクリプト、CI 設定、詳しい .env.example、テスト手順、依存バージョン指定など）があれば教えてください。必要に応じて補足のサンプルやテンプレートを作成します。