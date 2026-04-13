KabuSys — 日本株自動売買システム
================================

このリポジトリは日本株向けの自動売買プラットフォーム「KabuSys」の一部実装です。
売買（Execution）、ポートフォリオ構築（Portfolio）、リサーチ（Research）、AI（ニュース NLP / レジーム判定）、
および運用監視（Monitoring）機能を含みます。設計は本番安全性（クラッシュ耐性・フェイルセーフ）や
ルックアヘッドバイアス対策を重視しています。

主な機能
--------

- 実行エンジン（Execution）
  - OrderManager / OrderRepository による注文の作成・送信・状態同期
  - BrokerClientFactory による実運用 / Paper Trading（モック）の切替
  - Reconciler による起動時の自動リコンシリエーション（注文・ポジション同期）
  - RiskManager による発注時リスク制御（ポジション比率・利用率・サーキットブレーカー等）

- ポートフォリオ構築（Portfolio）
  - シグナルに基づく候補選定（select_candidates）
  - 等金額 / スコア重み付け（calc_equal_weights, calc_score_weights）
  - ポジションサイズ計算（calc_position_sizes）
  - セクターキャップ適用・レジーム乗数（apply_sector_cap, calc_regime_multiplier）

- リサーチ（Research）
  - Momentum / Volatility / Value ファクター計算（DuckDB 上の prices_daily / raw_financials を参照）
  - 将来リターン計算、IC（Information Coefficient）や統計サマリ機能

- AI（ニュース NLP / レジーム判定）
  - OpenAI（gpt-4o-mini）を用いたニュースのセンチメントスコア付与（ai.news_nlp.score_news）
  - マクロニュース + ETF（1321）MA 乖離を合成した市場レジーム判定（ai.regime_detector.score_regime）
  - API 呼び出しに対するリトライ、JSON バリデーション、フェイルセーフ動作を実装

- 監視（Monitoring）
  - SystemMonitor / TradeMonitor / RiskMonitor によるポーリング監視
  - MonitoringDB（SQLite）に監視ログを永続化
  - AlertManager による LINE Push 通知（構成済みなら）
  - KillSwitch（data/kill.flag）で ExecutionEngine を安全に停止できる仕組み
  - Streamlit ダッシュボードで監視データを可視化
  - paper_trading 用の検証レポート生成ツール（kabusys.tools.paper_verification_report）

セットアップ手順
----------------

前提
- Python 3.10+（typing 機能や新しい型注釈が使われています）
- DuckDB, sqlite3 が動作する環境
- ネットワークアクセス（OpenAI / LINE を使う場合）

1. リポジトリをクローンして作業ディレクトリへ
   - この README はソースが src/kabusys 以下にある前提です。

2. 依存パッケージをインストール
   - requirements.txt があれば:
     pip install -r requirements.txt
   - 最低限必要となるパッケージ（例）:
     pip install duckdb psutil openai requests streamlit

3. 環境変数を設定
   - ルートに .env を置くと自動で読み込まれます（OS 環境変数 > .env.local > .env の優先順）。
   - 自動ロードを無効にする場合:
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

   主要な環境変数（抜粋）
   - JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須な機能がある場合）
   - KABU_API_PASSWORD: kabuステーション API パスワード（必須）
   - OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合）
   - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE 通知用
   - KABUSYS_ENV: 起動環境 — "development" | "paper_trading" | "live"（デフォルト: development）
   - SQLITE_PATH: 監視 DB（デフォルト: data/monitoring.db）
   - DUCKDB_PATH: DuckDB ファイル（デフォルト: data/kabusys.duckdb）
   - PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
   - PAPER_FILL_MODE: paper_trading の約定挙動 ("instant" | "partial" | "never" | "reject")
   - PID_FILE_PATH: ExecutionEngine の PID ファイル（デフォルト: data/execution.pid）
   - KILL_FLAG_PATH: KillSwitch のフラグファイル（デフォルト: data/kill.flag）
   - MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、デフォルト: 60）

4. データディレクトリ作成（必要に応じて）
   mkdir -p data

使い方（実行例）
----------------

- 監視ループを起動（SystemMonitor 単体スクリプト）
  - モジュール実行:
    python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で上書きできます（1秒以上）。無効値は 60 秒にフォールバックします。
  - 監視は Settings の sqlite_path（監視用 DB）を常に使用します（KABUSYS_ENV に依らない）。

- 実行エンジンを起動（ExecutionEngine）
  - 本番/ペーパーを切り替えるには環境変数 KABUSYS_ENV を設定:
    # Paper Trading
    export KABUSYS_ENV=paper_trading
    python -m kabusys.run_execution

    # Live
    export KABUSYS_ENV=live
    python -m kabusys.run_execution

  - paper_trading の場合、Broker は MockBrokerClient を使い、orders は PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に分離されます。
  - プロセス開始時に PID ファイル（Settings.pid_file_path）を書き、終了時にクリーンアップします（kill flag 管理と連携）。

- Streamlit ダッシュボード（監視）
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

- Paper Trading 検証レポート生成
  python -m kabusys.tools.paper_verification_report
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  オプション --db で別の DB パスを指定可能。

- AI バッチ処理（例：ニューススコア付与 / レジーム判定）
  - news_nlp.score_news(conn, target_date, api_key=None) — DuckDB 接続と target_date を与えて呼ぶ
  - regime_detector.score_regime(conn, target_date, api_key=None)
  - これらは OpenAI API キー（引数または環境変数 OPENAI_API_KEY）を要求します。API 呼び出し失敗時は安全側のフォールバックを行う設計です。

運用上の注意
------------

- 監視（Monitoring）は常に本番の sqlite_path を参照します。Paper Trading と分離して運用したい場合は Execution 側の PAPER_TRADING_SQLITE_PATH を利用してください。
- KillSwitch は data/kill.flag を書き込み、ExecutionEngine の停止トリガーとして利用します。起動時に KILL_FLAG_CLEAR_ON_START=1 を設定すると自動でクリアします。
- プロセス優先度は set_process_priority("high") により開始時に試みて設定されます。権限不足等で失敗しても警告ログとなり続行します。
- Streamlit ダッシュボードは DB を読み取り専用で開きます（URI に ?mode=ro を付与）。

ディレクトリ構成（抜粋）
------------------------

以下はソース内の主要ファイル/パッケージ（src/kabusys 以下）の抜粋ツリーです:

- src/kabusys/
  - __init__.py
  - config.py                    — 環境変数 / .env ロードと Settings クラス
  - run_monitoring.py            — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py             — ExecutionEngine 起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py — Paper Trading 検証レポート生成
  - portfolio/
    - __init__.py
    - portfolio_builder.py        — 候補選定・重み計算
    - position_sizing.py         — 株数決定・単元丸め・スケールダウン
    - risk_adjustment.py         — セクターキャップ・レジーム乗数
  - research/
    - __init__.py
    - factor_research.py         — Momentum / Volatility / Value
    - feature_exploration.py     — 将来リターン / IC / 統計
  - ai/
    - __init__.py
    - news_nlp.py                — ニュース NLP（OpenAI 呼び出し、ai_scores 書込）
    - regime_detector.py         — 市場レジーム判定（MA + マクロ）
  - monitoring/
    - __init__.py
    - monitoring_db.py           — SQLite スキーマ + MonitoringDB クラス
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py
    - monitoring_engine.py
    - streamlit_dashboard.py
  - execution/
    - reconciler.py
    - order_manager.py
    - (そのほか Execution 関連モジュールが存在)
  - utils/
    - __init__.py
    - process_priority.py        — psutil ベースの優先度 / affinity ユーティリティ

よくある質問 / トラブルシューティング
------------------------------------

- .env が読み込まれない
  - KABUSYS_DISABLE_AUTO_ENV_LOAD が設定されていないか確認してください。
  - プロジェクトルート検出は __file__ を起点に .git または pyproject.toml を探します。パッケージ配布後や配置方法によっては自動検出に失敗することがあります。その場合は環境変数を直接 export してください。

- OpenAI 呼び出しが頻繁に失敗する
  - rate limit であれば retry/backoff ロジックが働きます。API キーが正しいか、モデル名（デフォルト gpt-4o-mini）が利用可能か確認してください。
  - テストでは _call_openai_api をモックして挙動を検証できます。

- SQLite / DuckDB のファイルパス
  - デフォルトは data/monitoring.db（SQLite） と data/kabusys.duckdb（DuckDB）です。環境変数 SQLITE_PATH / DUCKDB_PATH で変更できます。

貢献・拡張
---------

- 既存モジュールは「純粋関数」設計の部分（portfolio/*）と I/O を含む部分（ai/*, monitoring/*, execution/*）で分離されています。ユニットテストは純粋関数群から書き始めると容易です。
- 将来的な拡張案:
  - 銘柄ごとの lot_size をマスタデータから取得する（position_sizing の TODO）
  - AI パイプラインの並列化（現在はバッチ単位で逐次）
  - Streamlit ダッシュボードの追加ウィジェット（チャート・時系列）

ライセンス・注意
----------------

- 本 README はソースのコードコメント・設計方針に基づく概要ドキュメントです。実際に運用する際は適切なテスト、リスク管理と法令遵守を行ってください。
- 実際のブローカー接続や金銭を扱う運用では、十分な監査・セーフガード（注文・資金管理・監視アラート）を実装した上で行ってください。

質問や追加ドキュメントの要望があれば教えてください。README の補強（例: 環境変数サンプル .env.example、運用フロー図、CI テスト例）も作成可能です。