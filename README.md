KabuSys
=======

日本株向け自動売買プラットフォームのコアライブラリ群および実行 / 監視スクリプトを含むリポジトリ。  
この README はコードベースの簡易ドキュメントです。実装はモジュール単位で設計され、実運用向けのフェイルセーフや冪等性（idempotence）に配慮されています。

プロジェクト概要
--------------
KabuSys は以下の主要機能を持つ自動売買システムのコア実装です。

- シグナルを受けてブローカーへ発注する ExecutionEngine（実稼働／ペーパートレード切替対応）
- 発注管理・再同期（Reconciler）、Order state machine（OrderManager）
- ポートフォリオ構築（候補選定・重み付け・ポジションサイジング、セクター制限 等）
- 研究用ファクター計算・特徴量解析（DuckDB を使ったローカル集計）
- ニュースの LLM（OpenAI）によるセンチメント集計／市場レジーム判定
- 監視（System / Trade / Risk モニタ）と通知（LINE Push）、kill flag による安全停止
- Streamlit ベースの監視ダッシュボード（読み取り専用）

主な機能一覧
-------------
- execution/
  - ExecutionEngine: シグナル処理ループ、push ドレイン、Gate チェック（複数のリスクゲート）
  - OrderManager / OrderRepository: 発注・状態遷移・永続化
  - Reconciler: 再起動時の自動復旧とポジション照合
  - RiskManager: レート制限・サーキットブレーカー等（Config に基づく）
- portfolio/
  - 銘柄選定（select_candidates）、重み計算（equal/score）、ポジションサイズ算出（risk_based 等）
  - セクター集中制限、レジームに応じた資金乗数
- research/
  - ファクター計算（momentum/value/volatility）、将来リターン、IC 計算、統計サマリ
- ai/
  - news_nlp.score_news: raw_news を集約して OpenAI に投げ、銘柄別 ai_score を ai_scores テーブルへ保存
  - regime_detector.score_regime: ETF(1321) MA とマクロニュースの LLM センチメントを合成してレジーム判定
- monitoring/
  - SystemMonitor / TradeMonitor / RiskMonitor：監視チェックと monitoring DB への記録
  - MonitoringEngine: 各 Monitor を束ねて定期実行、KillSwitch / AlertManager と連動
  - monitoring_db: SQLite ベースで監視ログのスキーマ初期化・読み書き
  - streamlit_dashboard.py: 監視 DB を読み取り専用で可視化
- utils/
  - process_priority: Windows / POSIX の差分を吸収してプロセス優先度や CPU affinity を設定

要件
----
- Python 3.10+（型アノテーションで | を使用）
- 主要外部ライブラリ:
  - duckdb
  - psutil
  - requests
  - openai
  - streamlit（ダッシュボード利用時）
- SQLite3 は標準ライブラリ（組み込み）
- ネットワークアクセス：LINE API / OpenAI / ブローカー API（本番時）

セットアップ手順
----------------
1. リポジトリをクローン
   - git clone <repo-url>
   - cd <repo>

2. 仮想環境を作成・有効化（例）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存パッケージをインストール
   - pip install --upgrade pip
   - pip install duckdb psutil requests openai streamlit

   （必要に応じて requirements.txt を用意している場合は pip install -r requirements.txt）

4. データディレクトリを作成
   - mkdir -p data

5. 環境変数を用意（.env）
   - プロジェクトルートに .env（または .env.local）を置くことで自動読み込みされます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
   - 必要な主要環境変数（一例）:
     - KABUSYS_ENV=development | paper_trading | live
     - JQUANTS_REFRESH_TOKEN=...
     - KABU_API_PASSWORD=...
     - OPENAI_API_KEY=...            （AI 機能を使う場合）
     - DUCKDB_PATH=data/kabusys.duckdb
     - SQLITE_PATH=data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
     - PAPER_FILL_MODE=instant | partial | never | reject
     - PID_FILE_PATH=data/execution.pid
     - KILL_FLAG_PATH=data/kill.flag
     - LINE_CHANNEL_ACCESS_TOKEN=...（通知を有効にする場合）
     - LINE_USER_ID=...              （通知を有効にする場合）
     - LOG_LEVEL=INFO

   例 (.env):
     KABUSYS_ENV=development
     OPENAI_API_KEY=sk-...
     DUCKDB_PATH=data/kabusys.duckdb
     SQLITE_PATH=data/monitoring.db
     PAPER_FILL_MODE=instant

6. DB 初期化
   - monitoring 用 SQLite は run_monitoring.py / run_execution.py が起動時に init_monitoring_db を呼ぶため、通常は手動初期化不要です。
   - DuckDB（prices_daily など）にデータを投入している前提で動作します（研究・AI 機能は DuckDB のテーブルを参照します）。

使い方
------
起動スクリプト（直接実行またはモジュール実行）:

- 監視ループを起動（System / Trade / Risk を定期チェック）
  - python src/kabusys/run_monitoring.py
  - モジュールとして: python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可（デフォルト 60）
    - 値が1未満または不正ならデフォルトにフォールバックします

- ExecutionEngine を起動（実売買 or ペーパートレード）
  - KABUSYS_ENV=paper_trading を設定すると paper_trading 用のデータベース（PAPER_TRADING_SQLITE_PATH）を使用し、MockBrokerClient モードになります
  - python src/kabusys/run_execution.py
  - モジュールとして: python -m kabusys.run_execution

- Streamlit ダッシュボード（監視表示）
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

- AI / レジーム関係（ライブラリ関数呼び出し）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - いずれも DuckDB の接続を渡して実行します。api_key が None の場合は環境変数 OPENAI_API_KEY を参照します。

実運用に関するポイント / 注意事項
----------------------------------
- kill.flag:
  - KillSwitch は data/kill.flag を書き込むことで ExecutionEngine に停止シグナルを送ります。ExecutionEngine は起動時に kill.flag を検出して安全に停止します。
  - settings.kill_flag_clear_on_start が True の場合、起動時に kill.flag をクリアするオプションがあります（設定で制御）。

- Paper trading:
  - KABUSYS_ENV=paper_trading の場合、発注周りは MockBrokerClient を使用し、本番 DB と分離された PAPER_TRADING_SQLITE_PATH を使用します（data/paper_trading.db がデフォルト）。

- プロセス優先度:
  - run_* スクリプトは起動時に set_process_priority("high") を試みます（psutil を使用）。権限不足や未対応 OS の場合はログに警告が出ます。

- OpenAI 呼び出し:
  - API 呼び出しはリトライとフォールバック（失敗時はスコアをスキップまたは 0.0 にフォールバック）を含む堅牢な実装になっていますが、API キー未設定時は例外になります。

- DB/データ鮮度:
  - SystemMonitor は DuckDB の prices_daily から最終日付を確認してデータ鮮度を判定します（_FRESHNESS_DAYS = 3）。
  - DuckDB のテーブル（prices_daily, raw_financials, raw_news, news_symbols 等）が前提です。research / ai 機能はこれらのテーブルに依存します。

- 権限・ポートフォリオ値:
  - RiskManager はブローカーの available cash を用いるため、ブローカークライアントが適切に現在残高を返すことが必要です。

ディレクトリ構成（主要ファイル）
------------------------------
（src/kabusys 以下を抜粋）

- kabusys/
  - __init__.py               — パッケージ定義（__version__ など）
  - config.py                 — 環境変数 / 設定読み込みロジック（.env 自動ロード含む）
  - run_monitoring.py         — SystemMonitor のポーリングループ起動スクリプト
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - utils/
    - process_priority.py     — プロセス優先度・CPU affinity ユーティリティ
  - portfolio/
    - portfolio_builder.py    — 候補選定・重み計算
    - position_sizing.py      — 株数決定・投下資金スケール調整
    - risk_adjustment.py      — セクター制限・レジーム乗数
  - research/
    - factor_research.py      — momentum/volatility/value ファクター計算
    - feature_exploration.py  — 将来リターン・IC・統計サマリ
  - ai/
    - news_nlp.py             — ニュース集約 → OpenAI でセンチメント取得 → ai_scores へ書込
    - regime_detector.py      — ETF MA + マクロニュースで市場レジーム判定
  - monitoring/
    - monitoring_db.py        — SQLite スキーマ初期化 + DB 操作用ラッパ
    - system_monitor.py       — CPU/メモリ/Disk/データ鮮度／プロセス監視
    - trade_monitor.py        — 滞留注文／約定異常監視
    - risk_monitor.py         — ドローダウン・ポジション上限監視
    - alert_manager.py        — LINE Push 通知ラッパ
    - kill_switch.py          — kill.flag 管理
    - monitoring_engine.py    — 各 Monitor を束ねるポーリングエンジン
    - streamlit_dashboard.py  — 監視ダッシュボード（Streamlit）
  - execution/
    - execution_engine.py     — 発注エンジン（シグナル読み込み / push ドレイン）
    - order_manager.py        — 発注の永続化と broker への送信フロー
    - reconciler.py           — 起動時の注文 / ポジション再同期
    - order_repository.py     — Orders DB の抽象化（SQLite）
    - order_record.py         — 注文状態遷移ロジック（純粋ロジック）
    - risk_manager.py         — 実行前ゲート（rate limit / circuit breaker 等）
    - broker_factory.py       — Broker クライアント生成（実際のブローカー or Mock）
    - broker_api.py           — ブローカー API プロトコル / 例外定義
  - monitoring/ (上記)
  - data/ (ディスク上のデフォルトパス)
    - kabusys.duckdb (DuckDB)
    - monitoring.db (SQLite)
    - paper_trading.db (ペーパートレード用 SQLite)

トラブルシューティング（簡易）
------------------------------
- psutil による優先度設定で AccessDenied が出る場合は権限不足（Windows の管理者権限、Linux の root 権限が必要なことがあります）。ログは警告に留まり処理は継続します。
- OpenAI API エラーやレート制限は内部でリトライ処理が入りますが、API キー未設定はエラーになります。
- monitoring_db のスキーママイグレーションは init_monitoring_db() が実行時に行います。既存 DB の列追加などは内部で安全に取り扱われます。

開発・テスト
-------------
- 各モジュールは純粋関数（副作用がない関数）と DB 操作層が分離されるよう設計されています。ユニットテストは関数単位で行えます（外部 API 呼び出しはモック可能）。
- news_nlp / regime_detector の API 呼び出しは _call_openai_api を patch してモック可能です。

最後に
------
この README はコードベースの主要点をまとめた簡易ドキュメントです。詳細な設計仕様（PortfolioConstruction.md, StrategyModel.md 等）や運用手順書が別途ある場合はそちらを参照してください。追加の説明やサンプル .env / 初期データロード手順が必要であればお知らせください。