# KabuSys

日本株向けの自動売買・リサーチ基盤ライブラリ群。ポートフォリオ構築、ポジションサイジング、ファクター計算、ニュースのLLMによるセンチメント評価、市場レジーム判定、監視（アラート・ダッシュボード）、発注エンジン（ExecutionEngine）などをモジュール化して提供します。

主な設計方針
- DuckDB / SQLite を用いたオンプレミスデータ操作（外部サービスへの依存を最小化）
- モジュールは純粋関数または読み書き層に分離（テスト容易性）
- ルックアヘッドバイアス防止（time.now / date.today を直接参照しない設計箇所あり）
- OpenAI（LLM）呼び出しは失敗時にフォールバックし安全に継続するフェイルセーフ設計

---

## 機能一覧

- 環境変数/設定読み込み（.env/.env.local 自動ロード、プロジェクトルート検出）
- ポートフォリオ構築
  - 候補選定、等ウェイト／スコア加重ウェイト、リスクに応じたポジションサイズ決定
  - セクター集中抑制、レジーム乗数
- リサーチ（DuckDB ベース）
  - Momentum / Volatility / Value ファクター計算
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー
- AI（OpenAI）
  - ニュース記事の銘柄別センチメント算出（ai_scores へ書き込み）
  - マクロニュースとETF MA を用いた市場レジーム判定（market_regime へ書き込み）
- 監視
  - MonitoringDB（SQLite）によるシステム/トレード/リスクログ永続化
  - RiskMonitor / TradeMonitor / SystemMonitor、LINE Push を用いたアラート
  - Streamlit ダッシュボード（読み取り専用接続で可視化）
  - kill.flag による実行停止シグナル
- 発注/実行
  - ExecutionEngine（シグナル取得→Gate チェック→発注→WebSocketドレイン）
  - OrderManager / OrderRepository / Reconciler による再同期・クラッシュ後復旧
  - Broker API 抽象化（Protocol）でブローカ実装差し替え可能

---

## 要件

- Python 3.10+
- 主要依存（例）:
  - duckdb
  - openai
  - requests
  - psutil
  - streamlit (ダッシュボード利用時)
- SQLite は標準ライブラリで利用可能

推奨: 仮想環境（venv / virtualenv / poetry 等）を使用してください。

---

## セットアップ手順

1. リポジトリをクローン / プロジェクトルートへ移動
2. Python 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate (Unix) / .venv\Scripts\activate (Windows)
3. 依存パッケージのインストール（例）
   - pip install duckdb openai requests psutil streamlit
4. 環境変数設定
   - プロジェクトルートに `.env` を作成するか、OS 環境変数を設定します。
   - 自動ロードはデフォルトで有効。自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定。

例: `.env`（最低限の例）
    JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
    KABU_API_PASSWORD=your_kabu_api_password
    OPENAI_API_KEY=sk-...
    # 任意
    LINE_CHANNEL_ACCESS_TOKEN=...
    LINE_USER_ID=...
    DUCKDB_PATH=data/kabusys.duckdb
    SQLITE_PATH=data/monitoring.db
    KABUSYS_ENV=development
    LOG_LEVEL=INFO
    PAPER_FILL_MODE=instant

.env.local があれば .env の上書きとして読み込まれます（OS 環境変数は保護されます）。

設定バリデーション
- KABUSYS_ENV: development | paper_trading | live
- LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL
- PAPER_FILL_MODE: instant | partial | never | reject

---

## 使い方（代表例）

注意: 多くの関数は DuckDB または sqlite3 の接続を引数に取ります。事前にデータテーブル（prices_daily / raw_financials / raw_news / news_symbols / ai_scores / market_regime 等）を準備してください。

- 設定を参照する
    from kabusys.config import settings
    token = settings.jquants_refresh_token

- MonitoringDB 初期化（SQLite）
    import sqlite3
    from kabusys.monitoring.monitoring_db import init_monitoring_db
    conn = sqlite3.connect("data/monitoring.db")
    init_monitoring_db(conn)

- Streamlit ダッシュボード起動
    streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

- ファクター / リサーチ API（DuckDB 接続）
    import duckdb
    from datetime import date
    from kabusys.research import calc_momentum, calc_volatility, calc_value

    conn = duckdb.connect("data/kabusys.duckdb")
    target = date(2026, 3, 20)
    mom = calc_momentum(conn, target)
    vol = calc_volatility(conn, target)
    val = calc_value(conn, target)

- ニューススコア（LLM を使用、OPENAI_API_KEY 必須）
    import duckdb
    from datetime import date
    from kabusys.ai.news_nlp import score_news

    conn = duckdb.connect("data/kabusys.duckdb")
    count = score_news(conn, date(2026, 3, 20))  # ai_scores テーブルへ書き込み

- 市場レジーム判定（LLM を使用、OPENAI_API_KEY 必須）
    from kabusys.ai.regime_detector import score_regime
    score_regime(conn, date(2026, 3, 20))

- ExecutionEngine の実行（概念）
  ExecutionEngine は Broker 実装、OrderRepository、RiskManager、OrderManager、DuckDB 接続、EngineConfig 等の組み合わせで起動します。簡略例（実際の Broker 実装や OrderRepository の構築が必要）:
    from kabusys.execution.execution_engine import ExecutionEngine, EngineConfig
    engine = ExecutionEngine(broker, repo, risk_manager, order_manager, duckdb_conn, EngineConfig(target_date=...))
    engine.run_session()

- Kill Flag
  - kill.flag のパスは settings.kill_flag_path（デフォルト data/kill.flag）で管理。
  - KillSwitch は kill.flag を書き込むと ExecutionEngine の起動中ループを停止します。
  - ExecutionEngine 起動時に KILL_FLAG_CLEAR_ON_START=1 が設定されている場合は既存の kill.flag をクリアして起動します（デフォルトは拒否）。

---

## 環境変数・主要設定一覧

必須
- JQUANTS_REFRESH_TOKEN — J-Quants API（リサーチ用等）
- KABU_API_PASSWORD — kabuステーション API のパスワード
- OPENAI_API_KEY — OpenAI を使う機能（news_nlp, regime_detector 等）で必須

任意 / デフォルト有り
- KABUSYS_ENV (development|paper_trading|live) — 動作モード（default: development）
- LOG_LEVEL — ログレベル（default: INFO）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID — LINE 通知
- DUCKDB_PATH (default: data/kabusys.duckdb)
- SQLITE_PATH (default: data/monitoring.db)
- PAPER_FILL_MODE (instant|partial|never|reject) — Paper Trading の模擬約定モード（default: instant）
- PAPER_TRADING_SQLITE_PATH (default: data/paper_trading.db)
- PID_FILE_PATH (default: data/execution.pid)
- KILL_FLAG_PATH (default: data/kill.flag)
- KILL_FLAG_CLEAR_ON_START (0|1) — 起動時に kill.flag を自動クリアするか（default: 0）
- CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT — 監視閾値
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 — .env 自動ロードを無効化

設定は `.env` → `.env.local` の順に読み込まれ、OS 環境変数は上書き保護されます。

---

## 実装上の注意点 / 補足

- DuckDB / SQLite テーブルスキーマは実行前に適切に準備してください（research / ai / monitoring で参照するテーブル）。
- OpenAI 呼び出しはリトライ・バックオフ・レスポンス検証を行いますが、APIキーの管理は慎重に行ってください。
- ExecutionEngine は PID ファイルを書き、kill.flag を検出すると安全停止します。起動時の kill.flag の扱いは設定で制御できます。
- Reconciler により再起動時の注文状態同期（OrderSent の自動復旧）を行います。Broker 側の実装に依存します。
- 競合状態や DB ツールのバージョン差異（DuckDB の binder 等）により executemany で空配列が許容されない点を回避する対応があるため、そのままの形で互換性を保つ実装があります。

---

## ディレクトリ構成

（プロジェクトルートの `src/kabusys` 配下を抜粋）

- src/kabusys/
  - __init__.py
  - config.py                          — 環境変数 / .env 自動ロード / Settings
  - ai/
    - __init__.py
    - news_nlp.py                       — ニュースの LLM センチメント → ai_scores
    - regime_detector.py                — マクロ + MA によるレジーム判定
  - research/
    - __init__.py
    - factor_research.py                — Momentum / Volatility / Value 等
    - feature_exploration.py            — forward returns / IC / summary
  - portfolio/
    - __init__.py
    - portfolio_builder.py              — 候補選定・ウェイト計算
    - risk_adjustment.py                — セクター上限・レジーム乗数
    - position_sizing.py                — 株数計算・aggregate cap
  - monitoring/
    - __init__.py
    - monitoring_db.py                  — MonitoringDB（SQLite）
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - alert_manager.py
    - kill_switch.py
    - monitoring_engine.py
    - streamlit_dashboard.py
  - execution/
    - broker_api.py                      — Broker API データモデル・Protocol・例外
    - order_manager.py
    - order_repository.py (利用箇所あり)
    - order_record.py (利用箇所あり)
    - reconciler.py
    - execution_engine.py
    - risk_manager.py (利用箇所あり)
  - monitoring (db code as above)
  - その他（data pipeline / stats 等の補助モジュールが存在する想定）

---

## 貢献 / テスト

- 各モジュールは純粋関数に区分されているためユニットテストが書きやすい設計です。DuckDB を利用する関数は一時 DB 接続を作ってテストデータを流し込み検証してください。
- OpenAI 呼び出し箇所は内部呼び出し関数（_call_openai_api 等）を patch/mock して単体テスト可能です。
- .env 自動ロードをテスト時に無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

README は以上です。具体的に「ExecutionEngine の起動サンプル」「DuckDB スキーマ」などの追加情報が必要でしたら、使用ケースに合わせて追記します。