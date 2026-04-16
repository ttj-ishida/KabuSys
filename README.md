README — KabuSys（日本株自動売買システム）
================================

概要
----
KabuSys は日本株の自動売買／研究／監視を目的とした Python ベースの小規模なシステムです。本コードベースには以下の主要機能が含まれます。

- ExecutionEngine：ブローカーと連携して注文を作成・管理（paper_trading モードあり）
- Monitoring：プロセス・システム状態・注文状況・リスクをポーリングしてログとアラートを出す
- Portfolio 構築ロジック：候補選定・重み付け・株数決定・セクター上限・レジーム調整
- Research：DuckDB を使ったファクター計算・特徴量解析
- AI：OpenAI API を使ったニュースのセンチメントスコアリングや市場レジーム判定
- Tools：Paper Trading の検証レポート生成、Streamlit ベースの監視ダッシュボードなど

主な設計方針：
- 実運用（live）とペーパートレーディング（paper_trading）を分離
- DuckDB を時系列/ファクターデータ用、SQLite を監視ログ/発注履歴用に利用
- 外部 API（OpenAI 等）呼び出しは明示的に API キーを渡すか環境変数で指定

機能一覧
--------
- 実行エンジン起動スクリプト
  - src/kabusys/run_execution.py
  - KABUSYS_ENV=paper_trading のときは MockBroker を使用し、data/paper_trading.db を使用
- 監視プロセス起動スクリプト
  - src/kabusys/run_monitoring.py
  - ポーリングで system / trade / risk をチェックし、SQLite に記録／LINE 通知／kill flag を制御
- 監視永続化層（MonitoringDB）
  - system_status, trade_logs, positions, risk_logs, dashboard を管理
- RiskMonitor / TradeMonitor / SystemMonitor / KillSwitch / AlertManager
  - ドローダウン検出、滞留注文検出、プロセス死活チェック、LINE 通知など
- Portfolio（純粋関数群）
  - 選定、等重・スコア重み、リスクベースのポジションサイズ算出、セクター制約、レジーム乗数
- Research（DuckDB ベース）
  - モメンタム / ボラティリティ / バリュー等のファクター計算、IC や forward returns、統計サマリ
- AI モジュール
  - news_nlp: raw_news から LLM によるセンチメントを算出して ai_scores に書き込み
  - regime_detector: ETF ma200 乖離 + マクロニュースセンチメントを合成して market_regime を判定
- ツール
  - paper_verification_report: ペーパートレード DB を解析して PASS/FAIL レポート出力
  - streamlit_dashboard: 監視 DB を可視化する Streamlit アプリ

セットアップ手順
----------------
1. リポジトリをクローン
   - git clone ... && cd <repo>

2. Python 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存ライブラリのインストール
   - 必須（代表例）: duckdb, psutil, openai, requests, streamlit
   - 例:
     - pip install duckdb psutil openai requests streamlit
   - （プロジェクトに requirements.txt があればそれを利用してください）

4. データディレクトリと初期ファイル
   - data ディレクトリを作成:
     - mkdir -p data
   - 実行・監視で使う SQLite / DuckDB のパスは Settings のデフォルトを参照します。
     - SQLite (監視): data/monitoring.db
     - Paper trading SQLite: data/paper_trading.db
     - DuckDB: data/kabusys.duckdb
   - これらは多くの初期化（monitoring テーブルの作成等）が起動時に自動で行われますが、
     prices_daily / raw_financials / raw_news 等の時系列データは別途準備してください（DuckDB）。

5. 環境変数 (.env)
   - .env または .env.local をプロジェクトルートに置くと自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。
   - 主要な環境変数（Settings から）:
     - JQUANTS_REFRESH_TOKEN — 必須（J-Quants API 用）
     - KABU_API_PASSWORD — 必須（kabuステーション API 用）
     - OPENAI_API_KEY — AI 機能を使う場合に必須
     - KABUSYS_ENV — development / paper_trading / live（デフォルト: development）
     - PAPER_FILL_MODE — paper_trading の注文約定挙動（instant|partial|never|reject）
     - PAPER_TRADING_SQLITE_PATH — paper_trading DB のパス（デフォルト data/paper_trading.db）
     - SQLITE_PATH — 監視 DB のパス（デフォルト data/monitoring.db）
     - DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — AlertManager の設定
     - MONITOR_POLL_INTERVAL — 監視ポーリング間隔（秒、run_monitoring 用、デフォルト 60）
   - .env のフォーマットは bash 形式（export KEY=VAL も可）。コメント行やクォートにも対応しています。

使い方（起動・コマンド例）
------------------------

- 監視プロセスの起動
  - 簡易:
    - python -m kabusys.run_monitoring
  - 挙動:
    - Settings.sqlite_path の SQLite に接続し init_monitoring_db を実行。
    - SystemMonitor / MonitoringDB を使いポーリングしてログ記録・アラート評価を行う。
    - MONITOR_POLL_INTERVAL で間隔を変更可（環境変数、秒単位）。デフォルト 60秒。
    - 停止は data/stop_requested.flag ファイルを作成するか Ctrl+C。

- 実行エンジン（ExecutionEngine）の起動
  - python -m kabusys.run_execution
  - 挙動:
    - Settings.env に応じて paper_trading モード／本番モードを切替。
    - paper_trading の場合は専用 SQLite（PAPER_TRADING_SQLITE_PATH）を使用して本番 DB と分離。
    - BrokerClientFactory でブローカークライアントを生成し、ExecutionEngine をスレッドで起動。
    - 停止は data/stop_requested.flag を作成することで検知されます。

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - オプション:
    - --db PATH — データベースパスを直接指定（環境変数 PAPER_TRADING_SQLITE_PATH より優先）

- Streamlit 監視ダッシュボード
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - read-only モードで SQLite を開いて dashboard / positions / trade_logs / system_status を表示

- AI 機能（プログラムから呼ぶ）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - OpenAI API キーを環境変数 OPENAI_API_KEY または引数で指定する必要があります。

運用上のファイル・フラグ
---------------------
- data/stop_requested.flag — run_monitoring / run_execution が監視している停止フラグ（存在するとループを抜ける）
- data/kill.flag — KillSwitch が書き込むフラグ（ExecutionEngine に停止シグナルを送る）
- data/execution.pid — ExecutionEngine の PID ファイル（SystemMonitor が生存確認に使用）
- DB ファイル:
  - data/monitoring.db（監視ログ）
  - data/paper_trading.db（paper_trading 用発注ログ）
  - data/kabusys.duckdb（価格・財務・ニュース等の分析データ）

ディレクトリ構成（主要ファイル）
------------------------------
- src/kabusys/
  - __init__.py
  - config.py — 環境変数／設定読み込み・Settings
  - run_monitoring.py — Monitoring ポーリングループ起動スクリプト
  - run_execution.py — ExecutionEngine 起動スクリプト
  - utils/
    - process_priority.py — プロセス優先度／CPU affinity ヘルパ
  - monitoring/
    - monitoring_db.py — SQLite テーブル定義・簡易 CRUD（init_monitoring_db, MonitoringDB）
    - system_monitor.py — CPU/メモリ/ディスク/データ鮮度/プロセス監視
    - trade_monitor.py — 注文滞留・約定異常価格チェック
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - kill_switch.py — kill.flag 書き込みと評価ロジック
    - alert_manager.py — LINE Push 通知実装
    - monitoring_engine.py — Monitor を束ねるループユーティリティ（テスト向け run_once/run）
    - streamlit_dashboard.py — Streamlit ダッシュボード実装
  - execution/
    - order_manager.py — 注文作成／状態遷移の外向き API
    - order_repository.py, order_record.py, reconciler.py, risk_manager.py, ...（発注周りの実装）
  - portfolio/
    - portfolio_builder.py — シグナル選定・重み付け
    - position_sizing.py — 株数決定・スケールダウン・単元丸め
    - risk_adjustment.py — セクター上限・レジーム乗数
  - research/
    - factor_research.py — momentum/volatility/value ファクター計算（DuckDB）
    - feature_exploration.py — forward returns / IC / 統計サマリ
  - ai/
    - news_nlp.py — raw_news を OpenAI に送り銘柄別センチメントを計算・書込
    - regime_detector.py — ma200 とマクロセンチメントの合成によるレジーム判定
  - tools/
    - paper_verification_report.py — paper_trading DB の検証レポート生成

開発・拡張ノート
----------------
- DuckDB テーブル（prices_daily, raw_financials, raw_news など）は外部データ投入が必要です。Research / AI 機能はそれらの前提データが揃っていることを期待します。
- init_monitoring_db() は監視用 SQLite のテーブル作成と簡易マイグレーションを行います。監視テーブルは起動時に自動で整備されます。
- OpenAI などの外部 API 呼び出しはリトライやフェイルセーフを含む実装になっていますが、API キー・利用料などの管理は運用者側で行ってください。
- process_priority・cpu_affinity は実行環境依存のため、権限や OS によって実行結果が異なります（警告ログが出ることがあります）。

トラブルシューティング（よくある質問）
-----------------------------------
- 「.env を置いたのに読み込まれない」
  - プロジェクトルートの特定は config._find_project_root() が .git または pyproject.toml を探索します。パッケージ配布後は自動ロードがスキップされる場合があります。その場合は環境変数を直接設定してください。
- 「AI モジュールが API キーを要求する」
  - OPENAI_API_KEY を環境変数に設定するか、関数呼び出し時に api_key 引数を渡してください。
- 「監視ループがすぐ停止する」
  - data/stop_requested.flag が存在すると起動直後に終了します。ファイルを削除して再起動してください。

ライセンス・貢献
----------------
- 本リポジトリのライセンスやコントリビューション方針はプロジェクトルートの LICENSE / CONTRIBUTING ファイルを参照してください（存在する場合）。

付記
----
この README はコードベースのファイル群（src/kabusys 以下）をもとに作成しています。実際のインストール／運用では依存関係の固定（requirements.txt/poetry）や環境ごとの設定 (.env.example) を用意することを推奨します。必要であれば README を英語版に翻訳したりセットアップスクリプトを追加することも可能です。