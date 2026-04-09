# KabuSys

バージョン: 0.1.0

KabuSys は日本株自動売買の研究・実行・監視を目的とした軽量ライブラリ／フレームワークです。DuckDB を用いたリサーチ・ファクター計算、LLM（OpenAI）を使ったニュースセンチメント評価、kabuステーション等のブローカー API を想定した発注エンジン、そして監視用の SQLite ベースの永続層 / ダッシュボードを提供します。

目標:
- 研究フェーズと実行フェーズを分離し、安全に自動売買を行うためのツール群を提供
- DB 参照は明確に限定し、副作用を最小化したモジュール設計
- LLM を組み込んだ補助機能（ニュース NLP / レジーム判定）を提供（OpenAI API 必須）

---

## 主な機能一覧

- 設定管理
  - .env / .env.local の自動読み込み（プロジェクトルート判定）
  - Settings クラスで環境変数を型付きで取得

- ポートフォリオ構築（純粋関数）
  - 銘柄選定（スコア順ソート）
  - 等金額配分 / スコア加重配分
  - セクター上限適用、レジーム乗数計算
  - 株数決定（リスクベース／等分配／スコア分配）、単元丸め、aggregate cap

- リサーチ／ファクター計算
  - Momentum / Volatility / Value 等のファクター計算（DuckDB 接続を受け取る）
  - 将来リターン、IC（Spearman）、ファクター統計サマリ

- AI（LLM）機能
  - ニュース記事の銘柄別センチメントスコア化（OpenAI）
  - マクロニュースを用いた市場レジーム判定（bull/neutral/bear）
  - API 呼び出しはリトライ/フェイルセーフ実装

- 実行（Execution）
  - OrderManager / ExecutionEngine: 注文状態管理、送信、Reconciler による再同期
  - Broker API 用 Protocol / データモデル（OrderRequest 等）
  - リスクゲート（Gate1/2/3）を経た発注フロー、kill.flag による安全停止

- 監視（Monitoring）
  - SQLite での監視ログ永続化（MonitoringDB）
  - SystemMonitor / TradeMonitor / RiskMonitor / KillSwitch / AlertManager
  - streamlit ダッシュボード（監視表示）

---

## セットアップ手順

前提:
- Python 3.10+ を想定（型注釈で | や数型を使用）
- Git が使える環境

1. リポジトリをクローン:
   git clone <repo_url>
   cd <repo_root>

2. 仮想環境の作成（推奨）:
   python -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate

3. 必要パッケージのインストール:
   pip install duckdb openai requests psutil streamlit

   （プロジェクトで requirements.txt を用意している場合は pip install -r requirements.txt）

4. 環境変数設定 (.env)
   - プロジェクトルート（.git または pyproject.toml のあるディレクトリ）を自動検出し、.env / .env.local を読み込みます。
   - 自動読み込みを無効化する場合:
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

   主要な環境変数（例）:
   - JQUANTS_REFRESH_TOKEN (必須: J-Quants API 用トークン)
   - KABU_API_PASSWORD (必須: kabuステーション API パスワード)
   - OPENAI_API_KEY (LLM 機能使用時に必須)
   - KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
   - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID (監視通知)
   - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
   - SQLITE_PATH (デフォルト: data/monitoring.db)
   - PAPER_FILL_MODE / PAPER_TRADING_SQLITE_PATH（ペーパートレード設定）
   - PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START / LOG_LEVEL / KABUSYS_ENV など

5. 監視 DB 初期化（SQLite）:
   Python スクリプトで init_monitoring_db を呼ぶ例:

   python -c "import sqlite3; from kabusys.monitoring.monitoring_db import init_monitoring_db; conn=sqlite3.connect('data/monitoring.db'); init_monitoring_db(conn); conn.close()"

6. DuckDB の準備:
   prices_daily / raw_financials / raw_news 等のテーブルを用意してください。これは運用データに依存します。

---

## 使い方（よく使う API / 実行例）

以下はライブラリ内の主要な関数・クラスの簡単な利用例です。

- Settings（環境変数取得）
  from kabusys.config import settings
  token = settings.jquants_refresh_token
  duckdb_path = settings.duckdb_path

- ポートフォリオ構築（候補選定→重み→ポジションサイズ）
  from kabusys.portfolio import select_candidates, calc_score_weights, calc_position_sizes

  candidates = select_candidates(buy_signals, max_positions=10)
  weights = calc_score_weights(candidates)
  sizes = calc_position_sizes(weights, candidates, portfolio_value=10_000_000, available_cash=1_000_000, current_positions={}, open_prices=price_map)

- ファクター計算（DuckDB 接続が必要）
  import duckdb
  from datetime import date
  from kabusys.research import calc_momentum, calc_volatility, calc_value

  conn = duckdb.connect(settings.duckdb_path)
  res_mom = calc_momentum(conn, date(2026, 3, 20))
  res_vol = calc_volatility(conn, date(2026, 3, 20))
  res_val = calc_value(conn, date(2026, 3, 20))

- ニュース NLP スコアリング（OpenAI 必須）
  from kabusys.ai import score_news
  import duckdb
  from datetime import date

  conn = duckdb.connect(settings.duckdb_path)
  count = score_news(conn, date(2026, 3, 20), api_key="sk-...")

- レジーム判定
  from kabusys.ai.regime_detector import score_regime
  count = score_regime(conn, date(2026, 3, 20), api_key=None)  # 環境変数 OPENAI_API_KEY を利用

- 監視（MonitoringEngine をテスト実行）
  from kabusys.monitoring import SystemMonitor, TradeMonitor, RiskMonitor, MonitoringEngine, AlertManager, KillSwitch
  import sqlite3, duckdb
  from pathlib import Path

  mon_conn = sqlite3.connect("data/monitoring.db")
  duck_conn = duckdb.connect(settings.duckdb_path)
  monitor_db = MonitoringDB(mon_conn)
  system_monitor = SystemMonitor(mon_conn, duck_conn)
  # TradeMonitor は OrderRepository が必要（省略）
  risk_monitor = RiskMonitor(mon_conn)
  kill_switch = KillSwitch(Path(settings.kill_flag_path))
  alert_manager = AlertManager(settings.line_channel_access_token, settings.line_user_id)
  engine = MonitoringEngine(system_monitor, trade_monitor, risk_monitor, interval_sec=60, kill_switch=kill_switch, alert_manager=alert_manager)
  engine.run_once()

- streamlit ダッシュボード表示
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

- ExecutionEngine（本番的利用）
  ExecutionEngine は BrokerAPIProtocol 実装（kabu station client 等）、OrderRepository、RiskManager、OrderManager、DuckDB 接続など多数の依存を組み合わせて使います。実運用ではこれらを具体的な実装でインスタンス化し、EngineConfig を与えて run_session() を呼びます。コードベース内の ExecutionEngine 実装を参照してください。

---

## ディレクトリ構成（主要ファイル・説明）

src/kabusys/
- __init__.py
  - パッケージエントリ（バージョン・公開 API）

- config.py
  - .env 自動読み込み、Settings クラス（環境変数管理）

- portfolio/
  - portfolio_builder.py: 候補選定、等配分・スコア配分
  - position_sizing.py: 株数計算、aggregate cap・単元丸め
  - risk_adjustment.py: セクターキャップ、レジーム乗数
  - __init__.py: 主要関数を再エクスポート

- research/
  - factor_research.py: モメンタム、ボラティリティ、バリュー計算（DuckDB ベース）
  - feature_exploration.py: 将来リターン、IC、ファクター統計
  - __init__.py: 研究ユーティリティ公開（zscore_normalize は data.stats から）

- ai/
  - news_nlp.py: raw_news を LLM に送り銘柄別センチメントを ai_scores に書込む
  - regime_detector.py: ETF MA とマクロニュースで市場レジーム判定
  - __init__.py: ai public API（score_news など）

- monitoring/
  - monitoring_db.py: SQLite スキーマ作成、MonitoringDB クラス（CRUD）
  - system_monitor.py: CPU/メモリ/ディスク・データ鮮度・PID チェック
  - trade_monitor.py: 注文滞留・約定異常チェック
  - risk_monitor.py: ドローダウン・ポジション上限監視
  - kill_switch.py: kill.flag 制御
  - alert_manager.py: LINE Push 通知ラッパー（クールダウン管理）
  - monitoring_engine.py: 各 Monitor を束ねるポーリングエンジン
  - streamlit_dashboard.py: streamlit での可視化

- execution/
  - broker_api.py: Broker API のデータモデル・Protocol・例外
  - order_manager.py: OrderState Machine の外向き API（create/send/sync/cancel）
  - reconciler.py: 起動時リコンシリエーション（注文・ポジション照合）
  - execution_engine.py: Signal-pull 型の発注エンジン（WebSocket push 受信含む）
  - その他（order_record.py, order_repository.py, risk_manager.py などはコードベースに含まれる想定）

- その他
  - data パッケージ (prices pipeline / stats): DuckDB 関連ユーティリティ（ソースに応じて）
  - monitoring DB / paper trading DB のデフォルトパスは data/ 配下

---

## 注意事項 / 運用上のポイント

- .env 自動読み込み:
  - プロジェクトルートは __file__ の親ディレクトリから .git または pyproject.toml を探索して決定します。配布後・異なる作業ディレクトリでも動作するよう設計されています。
  - 読み込み順序: OS 環境変数 > .env.local > .env
  - テスト等で自動ロードを無効にする場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

- 安全設計:
  - LLM 呼び出しは 429 / ネットワーク断 / タイムアウト / 5xx を想定したリトライを実装。致命的な失敗時はフェイルセーフ（無視または 0 にフォールバック）します。
  - ExecutionEngine は kill.flag に依存した安全停止、起動時の reconciler による自動復旧、PID ファイル管理を備えます。
  - MonitoringDB のマイグレーションは冪等（存在チェックあり）です。

- テスト:
  - LLM やネットワークを使う部分は _call_openai_api 等をモックしてテスト可能なように分離されています。

---

## 参考 / 開発上のヒント

- DuckDB を使ったリサーチ関数は外部副作用を持たない純粋関数群なので、データを用意すれば対話的に試せます。
- 実際のブローカー実装は BrokerAPIProtocol を満たすクラスを作成して注入してください（テスト用にスタブ実装を作るのが簡単です）。
- LINE 連携は AlertManager 経由。トークン未設定時はログ出力のみで安全に動作します。

---

この README はコードベースの主要部分をまとめた導入ドキュメントです。具体的な実行エントリポイントや CLI、追加のユーティリティはプロジェクト内の該当ファイルを参照してください。必要であれば、起動スクリプト例や運用フロー（デプロイ手順、cron/サービス設定、バックアップ方針）についても追記します。どの情報がさらに必要か教えてください。