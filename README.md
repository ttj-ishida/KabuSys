# KabuSys

日本株自動売買システムのコードベース README（日本語）

---

目次
- プロジェクト概要
- 主な機能
- セットアップ手順
- 使い方（代表的なモジュールのサンプル）
- ディレクトリ構成（主要ファイル一覧）
- 環境変数一覧（主要な設定）

---

## プロジェクト概要

KabuSys は日本株向けの自動売買システム用ライブラリ／アプリケーション群です。  
主に下記の責務を持つモジュール群で構成されています。

- ファクター計算・リサーチ（duckdb を使った過去価格・財務データ解析）
- ポートフォリオ構築（候補選定、配分、ポジションサイズ算出、セクター制限）
- 発注／Execution エンジン（ブローカー API 抽象化、注文管理、再同期間合）
- 監視・アラート（システム状態、注文滞留、ドローダウン検知、LINE 通知）
- AI 補助（ニュース記事の NLP センチメント評価、マクロレジーム判定）

設計方針として、DB への書き込みや外部 API 呼び出しは責務を限定して実装されており、テストしやすい純粋関数群と I/O 層を分離しています。

---

## 主な機能（抜粋）

- 環境変数／.env 自動読み込み（settings API）
- ファクター計算（Momentum / Volatility / Value 等）
- 将来リターン・IC（Information Coefficient）計算、統計サマリー
- ポートフォリオ構築：候補選定、等分配・スコア加重配分、リスクベースのポジションサイズ算出
- セクター集中制限・市場レジームに基づく投下資金乗数計算
- AI モジュール：
  - news_nlp: raw_news を OpenAI（gpt-4o-mini）でスコア化して ai_scores に保存
  - regime_detector: ETF(1321)の MA とマクロニュースを合成して market_regime を算出
- Execution 周り：
  - OrderManager / Reconciler / ExecutionEngine による堅牢な注文フロー
  - broker_api 抽象（Protocol 型）により複数バックエンド対応可能
- 監視：
  - MonitoringDB（SQLite）による永続ログ
  - System/Trade/Risk Monitor、KillSwitch、AlertManager（LINE Push）
  - Streamlit ベースの簡易ダッシュボード

---

## セットアップ手順

前提
- Python 3.10 以上を推奨（| 型ヒント等を使用）
- Git（レポジトリをクローンする場合）

1. レポジトリをクローン（例）
   git clone <repository-url>
   cd <repo-root>

2. 仮想環境を作成・有効化
   python -m venv .venv
   source .venv/bin/activate  # macOS/Linux
   .venv\Scripts\activate     # Windows

3. 依存パッケージをインストール（プロジェクトに requirements.txt がある場合はそれを使ってください）
   pip install duckdb openai requests psutil streamlit

   （上記はコード内で利用されている主なパッケージの例です。プロジェクト側の requirements.txt があればそちらを優先してください。）

4. データディレクトリの作成
   mkdir -p data

5. 監視 DB の初期化（MonitoringDB スキーマ作成）
   python - <<'PY'
   import sqlite3
   from kabusys.monitoring.monitoring_db import init_monitoring_db
   conn = sqlite3.connect("data/monitoring.db")
   init_monitoring_db(conn)
   conn.close()
   PY

6. 環境変数の設定
   - .env（プロジェクトルート）を作成すると自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
   - 必須/推奨環境変数は後述の「環境変数一覧」を参照してください。

---

## 使い方（代表的な例）

注意：以下は代表的な使い方例です。各コンポーネントは依存関係があるため、実際に動かすには DB やブローカークライアント等を準備してください。

- 設定（Settings）の参照
  from kabusys.config import settings
  print(settings.jquants_refresh_token)
  print(settings.duckdb_path)

- ポートフォリオ（候補選定・重み計算）
  from kabusys.portfolio import select_candidates, calc_score_weights, calc_equal_weights
  buy_signals = [{"code":"7203","signal_rank":1,"score":0.8}, {"code":"6758","signal_rank":2,"score":0.5}]
  candidates = select_candidates(buy_signals, max_positions=5)
  weights = calc_score_weights(candidates)  # スコア加重
  # weights = calc_equal_weights(candidates)  # 等金額配分

- ポジションサイズ計算（risk_based 等）
  from kabusys.portfolio import calc_position_sizes
  sizes = calc_position_sizes(
      weights=weights,
      candidates=candidates,
      portfolio_value=10_000_000,
      available_cash=1_000_000,
      current_positions={},
      open_prices={"7203":1000,"6758":800},
      allocation_method="score",
      lot_size=100,
  )

- リサーチ（duckdb 接続が必要）
  import duckdb
  from datetime import date
  from kabusys.research import calc_momentum, calc_volatility, calc_value
  conn = duckdb.connect(str(settings.duckdb_path))
  results = calc_momentum(conn, date(2026,3,20))
  # calc_volatility / calc_value も同様に呼べます

- AI ニューススコア（OpenAI API キー必要）
  from kabusys.ai import score_news
  import duckdb, sqlite3
  from datetime import date
  conn = duckdb.connect(str(settings.duckdb_path))
  # OPENAI_API_KEY を環境変数に設定するか、api_key 引数で渡す
  n = score_news(conn, date(2026,3,20), api_key=None)
  print(f"scored {n} symbols")

- レジーム判定（market_regime 書き込み）
  from kabusys.ai.regime_detector import score_regime
  conn = duckdb.connect(str(settings.duckdb_path))
  score_regime(conn, date(2026,3,20))

- Monitoring ダッシュボード（streamlit）
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

- ExecutionEngine（本番的な流れ）
  ExecutionEngine は多くの依存を持つため、実運用では BrokerAPIProtocol 実装、OrderRepository、RiskManager、OrderManager、DuckDB 接続などを組み合わせてインスタンス化して run_session() を呼びます。小規模な統合テストではモック実装を渡して動作確認できます。

---

## 主要ディレクトリ／ファイル構成

（プロジェクトの src/kabusys 以下、抜粋）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / Settings 管理（.env 自動読み込み）
  - portfolio/
    - __init__.py
    - portfolio_builder.py    — 候補選定、等配分/スコア配分
    - position_sizing.py      — 発注株数算出、aggregate cap
    - risk_adjustment.py      — セクターキャップ、レジーム乗数
  - research/
    - __init__.py
    - factor_research.py      — momentum/volatility/value の計算
    - feature_exploration.py  — forward returns, IC, summary
  - ai/
    - __init__.py
    - news_nlp.py             — ニュース NLP スコアリング（OpenAI）
    - regime_detector.py      — マクロ + MA200 による市場レジーム判定（OpenAI）
  - monitoring/
    - __init__.py
    - monitoring_db.py        — SQLite スキーマ + MonitoringDB クラス
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - monitoring_engine.py
    - alert_manager.py        — LINE push 通知
    - kill_switch.py
    - streamlit_dashboard.py
  - execution/
    - broker_api.py           — Broker API のデータモデル / Protocol / 例外
    - order_manager.py
    - reconciler.py
    - execution_engine.py
    - ... (order_repository, order_record 等は本コードベースで参照される想定)
  - その他（data パイプライン / stats 等）...

---

## 環境変数（主要なもの）

ここに列挙される環境変数は settings を通じて参照されます。プロジェクトルートに `.env`／`.env.local` を置くと自動読み込みされます（OS 環境変数が優先され、.env.local は上書き）。

- JQUANTS_REFRESH_TOKEN — （必須）J-Quants API リフレッシュトークン
- KABU_API_PASSWORD — （必須）kabuステーション API パスワード
- KABU_API_BASE_URL — kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- OPENAI_API_KEY — OpenAI API キー（news_nlp / regime_detector で使用）
- LINE_CHANNEL_ACCESS_TOKEN — LINE 通知用トークン（AlertManager）
- LINE_USER_ID — LINE 通知先ユーザー ID
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — Monitoring SQLite のパス（デフォルト: data/monitoring.db）
- PAPER_FILL_MODE — paper trading 用の fill_mode（instant/partial/never/reject）
- PAPER_TRADING_SQLITE_PATH — Paper Trading 用 SQLite ファイルパス
- PID_FILE_PATH — ExecutionEngine 用 PID ファイルパス（デフォルト: data/execution.pid）
- KILL_FLAG_PATH — kill.flag のパス（デフォルト: data/kill.flag）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするフラグ（"1" で有効）
- CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT — 監視閾値
- KABUSYS_ENV — "development" / "paper_trading" / "live"
- LOG_LEVEL — ログレベル ("DEBUG", "INFO", ...)

自動ロードを無効化したい場合:
- export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

例（.env の例）
JQUANTS_REFRESH_TOKEN=xxxxx
KABU_API_PASSWORD=secret
OPENAI_API_KEY=sk-...
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
KABUSYS_ENV=development
LOG_LEVEL=DEBUG

---

## 注意点 / 実運用上のヒント

- AI（OpenAI）を用いる処理は API コストおよびレイテンシが発生します。運用では API キー管理・リトライ方針を検討してください（コード中でもリトライ処理を実装）。
- ExecutionEngine / OrderManager はブローカー API 実装と結合する必要があります。テストではモックを使用して挙動を検証してください。
- DuckDB のスキーマ（prices_daily / raw_financials / raw_news 等）はリサーチ・AI モジュールが前提としているためデータ準備が必要です。
- MonitoringDB のスキーマは init_monitoring_db() で作成します。既存 DB へのマイグレーション処理のコードも含まれています（例: dashboard.peak_value カラムの追加）。

---

この README はコードベース（src/kabusys/*.py）からの主要点をまとめた概要です。より詳細な設計仕様（PortfolioConstruction.md, StrategyModel.md 等）や実行例はプロジェクト内のドキュメントを参照してください。必要であれば README にさらに「開発・テスト手順」や「API リファレンス」の追記も作成できます。