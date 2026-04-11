KabuSys
=======

KabuSys は日本株の自動売買 / リサーチ / 監視を行うための軽量なフレームワークです。
本リポジトリは以下の主要コンポーネントを含みます:

- ExecutionEngine: シグナルに基づく発注エンジン（本番 / ペーパートレード対応）
- Reconciler / OrderManager: 起動時リコンシリエーション、注文状態管理
- Portfolio モジュール: 候補選定・ウェイト計算・ポジションサイジング
- Research モジュール: ファクター計算・IC/統計分析
- AI モジュール: ニュースのセンチメント解析（OpenAI）と市場レジーム判定
- Monitoring: システム／注文／リスク監視、LINE 通知、Streamlit ダッシュボード

以下に概要、機能、セットアップ、使い方、ディレクトリ構成をまとめます。

プロジェクト概要
---------------
KabuSys は、株式のシグナル→発注→モニタリングのワークフローを想定したモジュール群です。
設計方針の一部:

- 発注ロジックと DB 層を分離（SQLite / DuckDB を利用）
- 本番とペーパートレードを明確に分離（環境変数 KABUSYS_ENV）
- 再起動後の自動復旧（Reconciler）
- LLM を使ったニュースセンチメント / レジーム判定（OpenAI）
- 軽量な監視（system/trade/risk）と通知（LINE）、Streamlit ダッシュボード

主な機能一覧
-------------
- Execution
  - Signal ベースの発注ループ（ExecutionEngine）
  - OrderManager: 発注 → 永続化 → ブローカー呼び出しの安全なフロー
  - Reconciler: OrderSent 等の未確定注文をブローカーと照合して復旧
  - RiskManager: Gate 機構、レート制限、サーキットブレーカーなど（設定可能）

- Portfolio
  - 候補選定（スコア降順）
  - 等配分 / スコア加重配分
  - ポジションサイズ計算（リスクベース、単元株丸め）
  - セクター上限・レジーム乗数の適用

- Research
  - Momentum/Volatility/Value 等ファクター計算（DuckDB 上の prices_daily / raw_financials を参照）
  - 将来リターン計算、IC（Spearman）計算、統計サマリー

- AI（OpenAI 連携）
  - ニュース記事をまとめて LLM に投げ、銘柄ごとのセンチメントを ai_scores に保存（news_nlp）
  - マクロ記事 + ETF MA を用いた日次レジーム判定（regime_detector）
  - OpenAI の失敗はフェイルセーフ（多くのケースで 0.0 やスキップして継続）

- Monitoring
  - SystemMonitor / TradeMonitor / RiskMonitor：DB（SQLite）へログ＆閾値監視
  - KillSwitch：閾値超過で flag ファイルを書き、ExecutionEngine 停止をトリガー
  - AlertManager：LINE push による通知（クールダウン管理）
  - Streamlit ダッシュボード（読み取り専用で監視 DB を表示）

セットアップ手順
----------------

1. リポジトリをクローン
   - git clone <repo-url>

2. Python 仮想環境を作成
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 必要パッケージをインストール（例）
   - pip install --upgrade pip
   - pip install duckdb psutil requests openai streamlit

   （プロジェクト側で requirements.txt があればそれを使用してください）

4. 設定（環境変数 / .env）
   - プロジェクトルートに .env や .env.local を置くと自動読み込みされます（デフォルト）。
   - 自動ロードを無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

   主な環境変数:
   - KABUSYS_ENV: development | paper_trading | live （デフォルト: development）
     - paper_trading の場合、専用の PAPER_TRADING_SQLITE_PATH を使い、MockBroker を利用する想定
   - JQUANTS_REFRESH_TOKEN: 必須（Settings.jquants_refresh_token で _require）
   - KABU_API_PASSWORD: 必須（kabuステーション API 用）
   - OPENAI_API_KEY: OpenAI を使う機能（news_nlp / regime_detector）を有効にする場合に必須
   - DUCKDB_PATH: DuckDB ファイルのパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH: 監視 DB（デフォルト: data/monitoring.db）
   - PAPER_TRADING_SQLITE_PATH: ペーパートレード用監視 DB（デフォルト: data/paper_trading.db）
   - PAPER_FILL_MODE: instant | partial | never | reject（ペーパートレードの約定動作）
   - PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START 等（監視周り）
   - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID（AlertManager 用）
   - LOG_LEVEL（DEBUG/INFO/...）
   - MONITOR_POLL_INTERVAL: run_monitoring のポーリング秒（デフォルト 60）

5. データディレクトリを作成
   - mkdir -p data

6. DB 初期化
   - 監視 DB は run_monitoring.run / run_execution が起動時に init_monitoring_db を呼ぶため
     明示的な初期化は不要。但しデータ投入や DuckDB のスキーマ準備（prices_daily / raw_financials 等）は別途必要です。

使い方
------

※ 実行前に PYTHONPATH に src を含めるか、パッケージとしてインストールしてください。
例: PYTHONPATH=src python -m kabusys.run_monitoring

1. Monitoring を起動（常駐ポーリング）
   - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒で上書き可能（デフォルト 60 秒）。
   - 起動:
     - PYTHONPATH=src python -m kabusys.run_monitoring
     - または package インストール後: python -m kabusys.run_monitoring

   - 監視は常に本番用の sqlite_path を使用（Settings の設計による）。
   - run_monitoring はプロセス優先度を high に設定しようとします（psutil 経由。権限により警告が出ることがあります）。

2. Execution を起動（当日の取引セッション）
   - paper_trading で起動する例:
     - export KABUSYS_ENV=paper_trading
     - PYTHONPATH=src python -m kabusys.run_execution
   - live 環境では実際の BrokerClientFactory が生成するブローカーへ接続します（設定要）。
   - run_execution は Settings を参照して paper_trading 時は別 sqlite（PAPER_TRADING_SQLITE_PATH）を使います。
   - 起動時に Reconciler による同期や各種初期化が行われます。

3. Streamlit ダッシュボード（監視）
   - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
   - ダッシュボードは監視 DB を読み取り専用で開きます（データがないとその旨表示）。

4. AI 機能
   - news_nlp.score_news(conn, target_date, api_key=None)
     - OPENAI_API_KEY を設定するか、api_key を渡してください。
     - news_nlp は raw_news / news_symbols / ai_scores を参照・更新します。
   - regime_detector.score_regime(conn, target_date, api_key=None)
     - ETF（1321）とマクロニュースを使ったレジーム判定を行い market_regime テーブルへ書き込みます。

注意点 / 運用メモ
- kill.flag（Settings.kill_flag_path）を書き込むと ExecutionEngine 側で次回チェック時に停止します。
  KillSwitch は冪等に書き込みを行います。Execution 起動時に KILL_FLAG_CLEAR_ON_START=1 を
  設定すると起動時にクリアできます（Settings.kill_flag_clear_on_start）。
- psutil を使った優先度設定 / CPU affinity は権限によって失敗する可能性があります（警告を出してスキップ）。
- OpenAI の呼び出しはコストが発生します。API キーの設定と運用コストに注意してください。
- DuckDB 側のテーブル（prices_daily, raw_financials 等）は本プロジェクト外で作成 / 更新する前提です。

主要ファイル・ディレクトリ構成
-----------------------------

以下は src/kabusys 以下の主要ファイルと簡単な説明です（抜粋）:

- src/kabusys/
  - __init__.py              — パッケージ定義（__version__ 等）
  - config.py                — 環境変数 / Settings（.env 自動ロード、必須キー検査）
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py       — SystemMonitor ポーリングループ起動スクリプト

- src/kabusys/execution/
  - execution_engine.py      — ExecutionEngine（発注ループ、push drain 等）
  - order_manager.py         — OrderManager（発注ワークフロー）
  - order_repository.py      — SQLite ベースの注文永続化（not shown in excerpt）
  - reconciler.py            — 起動時の自動リコンシリエーション
  - risk_manager.py          — 発注リスク評価（Gate 等、not shown in excerpt）
  - broker_factory.py        — Broker クライアント生成（Mock / 実ブローカー）
  - broker_api.py            — Broker API 抽象プロトコル / 型定義

- src/kabusys/monitoring/
  - monitoring_db.py         — 監視用 SQLite スキーマ + MonitoringDB ラッパー
  - system_monitor.py        — CPU/メモリ/ディスク/データ鮮度/プロセス監視
  - trade_monitor.py         — 注文滞留・約定異常の検出
  - risk_monitor.py          — ドローダウン / ポジション上限監視
  - kill_switch.py           — kill.flag の書き込み・評価
  - alert_manager.py         — LINE 通知クライアント
  - monitoring_engine.py     — 各 Monitor を束ねるポーリングエンジン
  - streamlit_dashboard.py   — Streamlit による監視ダッシュボード

- src/kabusys/portfolio/
  - portfolio_builder.py     — 候補選定・スコアソート
  - position_sizing.py       — 株数算出・aggregate cap など
  - risk_adjustment.py       — セクターキャップ・レジーム乗数

- src/kabusys/research/
  - factor_research.py       — Momentum / Volatility / Value の計算（DuckDB）
  - feature_exploration.py   — 将来リターン、IC、統計サマリー

- src/kabusys/ai/
  - news_nlp.py              — ニュースの LLM センチメントスコア取得・ai_scores 書き込み
  - regime_detector.py       — ETF MA + マクロセンチメントで市場レジーム判定

- src/kabusys/utils/
  - process_priority.py      — プロセス優先度 / CPU affinity 設定用ユーティリティ

例: 実行コマンドまとめ
---------------------
- Monitoring 起動（デフォルト間隔 60s）:
  - PYTHONPATH=src python -m kabusys.run_monitoring
  - 間隔を変更: MONITOR_POLL_INTERVAL=30 PYTHONPATH=src python -m kabusys.run_monitoring

- Execution 起動（paper_trading 例）:
  - export KABUSYS_ENV=paper_trading
  - PYTHONPATH=src python -m kabusys.run_execution

- Streamlit ダッシュボード:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

ライセンス / 貢献
----------------
（ここにライセンス情報や貢献方法を追記してください）

最後に
-----
この README はコードベースの主要機能と運用手順のサマリです。実際の導入時は .env の作成・DuckDB のデータ投入・Broker の実装確認・OpenAI キーの管理などを丁寧に行ってください。必要であれば各モジュールの詳細ドキュメント（関数単位の docstring を参照）を参照してください。