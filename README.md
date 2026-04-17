# KabuSys

日本株自動売買システムのコンポーネント群（ライブラリ + 実行スクリプト群）。

このリポジトリはトレーディングエンジン、監視（Monitoring）、ポートフォリオ構築、リサーチ、AI（ニュース NLP / レジーム検出）などのモジュールを含みます。設計上、実動作での発注・口座操作はブローカークライアントを通じて行い、Paper Trading（模擬取引）モードでは本番 DB と完全に分離して動作します。

## 主な機能一覧

- Execution（発注エンジン）
  - ブローカー抽象化（実ブローカー / モック）
  - OrderManager（状態遷移・発注管理）
  - Reconciler（再起動時の自動同期）
  - リスク管理（RiskManager 等 — 一部省略ファイルあり）

- Monitoring（監視）
  - SystemMonitor: CPU / メモリ / ディスク / プロセス状態 / データ鮮度監視
  - TradeMonitor: 注文滞留・約定異常検知
  - RiskMonitor: ドローダウン・ポジション数監視
  - KillSwitch / AlertManager: 条件に応じた停止フラグ生成および LINE 通知
  - MonitoringEngine: 各監視を束ねたポーリングループ
  - ストリームリットダッシュボード（streamlit で可視化）

- Portfolio（ポートフォリオ構築）
  - 銘柄選定、重み付け（等配分・スコア加重）
  - セクター上限適用、レジーム乗数
  - 株数決定（リスクベース、上限、単元丸め、aggregate cap）

- Research（リサーチ）
  - ファクター計算（モメンタム・バリュー・ボラティリティ等）
  - 将来リターン計算、IC（情報係数）計算、統計サマリー

- AI（ニュース NLP / レジーム判定）
  - OpenAI（gpt-4o-mini）を用いたニュースセンチメント -> ai_scores テーブル書込
  - マクロニュース＋ETF MA200 を合成した市場レジーム判定（market_regime テーブルへ書込）
  - API呼び出しは冪等性やリトライを考慮した実装

- ユーティリティ
  - 環境変数 / .env の自動読み込み（Settings）
  - プロセス優先度 / CPU affinity 設定ユーティリティ
  - 各種 DB マイグレーション（monitoring DB の初期化・カラム追加）

---

## セットアップ手順

前提:
- Python 3.10+（typing の構文に依存）
- (推奨) 仮想環境を作る: python -m venv .venv && source .venv/bin/activate

1. 依存パッケージをインストール（例）
   - duckdb, psutil, openai, requests, streamlit
   - 例:
     pip install duckdb psutil openai requests streamlit

2. プロジェクトルートに data ディレクトリを作成（DB 等の出力先）
   mkdir -p data

3. 環境変数設定
   - 簡単にはルートに `.env` ファイルを置くと自動で読み込まれます（.env.local が存在すれば優先上書き）。
   - 自動ロードを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト等で有用）。

必須と思われる主な環境変数（例）:
- JQUANTS_REFRESH_TOKEN=...
- KABU_API_PASSWORD=...
- OPENAI_API_KEY=...（AI 機能を使う場合）
- KABUSYS_ENV=development | paper_trading | live

パス・オプション:
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (監視用デフォルト: data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH (paper_trading 用デフォルト: data/paper_trading.db)
- PID_FILE_PATH (デフォルト: data/execution.pid)
- KILL_FLAG_PATH (デフォルト: data/kill.flag)

PAPER_FILL_MODE（paper_trading の約定モード）:
- instant | partial | never | reject (デフォルト: instant)

例 .env (最小)
JQUANTS_REFRESH_TOKEN=your_jquants_token
KABU_API_PASSWORD=your_kabu_password
OPENAI_API_KEY=your_openai_key
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
PAPER_TRADING_SQLITE_PATH=data/paper_trading.db

---

## 使い方

以下は主要なスクリプト／起動方法の例です。

注意: パッケージ内部のスクリプトはモジュールとして実行できます（python -m kabusys.run_monitoring など）。

1. 監視プロセス起動（Monitoring）
   - 環境変数: MONITOR_POLL_INTERVAL でポーリング間隔を秒単位で上書き可能（デフォルト 60 秒。1 秒未満や不正値はデフォルトにフォールバック）。
   - 実行:
     python -m kabusys.run_monitoring
   - 停止:
     - ループは Ctrl+C（KeyboardInterrupt）で停止できます。
     - 外部から停止させるにはリポジトリルートの data/stop_requested.flag ファイルを作成してください（ループは検知して終了します）。

2. ExecutionEngine（発注エンジン）起動
   - 本番 / Paper Trading 切替:
     - 本番: KABUSYS_ENV=live（デフォルトは development）
     - Paper Trading: KABUSYS_ENV=paper_trading（この場合、MockBrokerClient を使用し PAPER_TRADING_SQLITE_PATH に記録）
   - 実行:
     python -m kabusys.run_execution
   - 停止:
     - data/stop_requested.flag を作成するとエンジンは安全に停止を開始します。
     - KillSwitch（監視側）が閾値を超えた場合は data/kill.flag が書かれ、エンジン停止トリガーとなる設計です。
   - PID 管理:
     - Engine は pid ファイル（デフォルト data/execution.pid）を参照してプロセス生存チェックを行います。

3. ストリームリットダッシュボード
   - 起動:
     streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
   - 監視 DB が read-only で開かれるため、MonitoringEngine を先に動かしてデータを書き込ませてください。

4. Paper Trading 検証レポート
   - ツール: kabusys.tools.paper_verification_report
   - 実行例:
     python -m kabusys.tools.paper_verification_report
     python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
   - デフォルト DB: data/paper_trading.db（--db で上書き可能）
   - レポートは稼働率・注文成功率・送信率・レイテンシ等を算出し PASS/FAIL 判定を行います。

5. AI 機能（プログラムから利用）
   - ニューススコアリング:
     from kabusys.ai.news_nlp import score_news
     score_news(duckdb_conn, target_date, api_key="...")  # api_key を渡すか環境変数 OPENAI_API_KEY を利用
   - レジーム判定:
     from kabusys.ai.regime_detector import score_regime
     score_regime(duckdb_conn, target_date, api_key="...")

---

## 重要な動作上の注意点・設計方針

- Monitoring は KABUSYS_ENV の値に関係なく監視用の sqlite_path（デフォルト data/monitoring.db）を使用します。Execution は paper_trading 時に専用 DB に切替えます（本番 DB と完全分離）。
- .env 自動ロード:
  - プロジェクトルートは .git または pyproject.toml を基準に自動検出します。見つからない場合は自動ロードをスキップします。
  - OS 環境変数が優先され、.env は上書きされません。.env.local は OS 環境変数を保護しつつ上書きされる仕組みです。
- プロセス優先度:
  - 起動時に set_process_priority("high") を呼び出します（psutil に依存）。権限やプラットフォームによって失敗する場合は警告にとどまり処理は継続します。
- OpenAI 呼び出し:
  - レスポンスの JSON モードを使う想定で実装されていますが、API の形が変わると影響を受けます。API 呼び出し部はテスト時にモック可能です。
  - API キーがない状態では例外を投げる箇所があります。AI 機能を使う場合は OPENAI_API_KEY の設定が必要です。
- Kill / Stop フラグ:
  - data/stop_requested.flag: run_monitoring / run_execution のループを止めるためのファイル（外部運用オペレーション用）。
  - data/kill.flag: KillSwitch が書き込むファイルで ExecutionEngine に停止を促します。
  - KillSwitch は冪等（既存ファイルがあれば再書き込みしない）です。

---

## ディレクトリ構成（抜粋）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / .env 読み込みと Settings クラス
  - run_monitoring.py        — SystemMonitor ポーリング起動スクリプト
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - utils/
    - process_priority.py    — プロセス優先度 / CPU affinity ユーティリティ
  - monitoring/
    - monitoring_db.py       — SQLite のスキーマ初期化・永続化 API（MonitoringDB）
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py
    - monitoring_engine.py
    - streamlit_dashboard.py
  - execution/
    - order_manager.py
    - reconciler.py
    - order_repository.py    (省略ファイルあり)
    - execution_engine.py    (省略ファイルあり)
    - broker_factory.py      (省略ファイルあり)
    - ...                    (OrderRecord, broker API 定義等)
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
  - tools/
    - paper_verification_report.py

- data/
  - monitoring.db (SQLite)
  - paper_trading.db (Paper Trading 用 SQLite)
  - kabusys.duckdb (DuckDB)
  - stop_requested.flag
  - kill.flag
  - execution.pid

注: 一部ファイルはこの README に含まれていない補助モジュール（order_repository や broker 実装など）に依存します。実運用前に全モジュールが揃っていることを確認してください。

---

## 開発 / デバッグのヒント

- DB（DuckDB / SQLite）の確認:
  - DuckDB はローカルファイルに格納されます（DUCKDB_PATH）。リサーチや AI 処理は DuckDB 上の prices_daily / raw_financials / raw_news 等のテーブルを参照します。
- テスト時:
  - 環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` をセットすると .env 自動ロードを無効化できます。
  - OpenAI 呼び出しはモック（unittest.mock.patch）で差し替え可能に実装されています。
- 権限系のエラー:
  - psutil による優先度設定や cpu_affinity は管理者権限が必要なケースがあります。権限不足時は警告を出してスキップします。

---

この README はコードベースの主要点をまとめたものです。各モジュールの詳細な使い方やパラメータは該当ソース（src/kabusys 以下の各 .py）を参照してください。README に関して補足してほしい点（例: サービス unit ファイル、Docker 化、CI 設定など）があればお知らせください。