README
======

概要
----
KabuSys は日本株向けの自動売買・リサーチ・監視フレームワークです。  
本リポジトリには、実行エンジン（ExecutionEngine）、監視コンポーネント（Monitoring）、ポートフォリオ構築、ファクター計算やリサーチツール、AI を使ったニュース解析・レジーム判定、ならびに運用補助スクリプトが含まれます。

主な設計方針:
- DuckDB を用いた時系列ファクター計算（prices_daily / raw_financials 等）
- SQLite を監視ログ / 注文ログの永続化に使用
- Paper Trading 環境は本番 DB と完全に分離
- OpenAI（gpt-4o-mini）を用いたニュース NLP / マクロ判定をオプションで実行
- ルックアヘッドバイアスを避ける設計（date/time を直接参照しない等）

機能一覧
--------
- 実行エンジン起動（run_execution.py）
  - 本番 / paper_trading を切り替え可能（KABUSYS_ENV）
  - BrokerClientFactory により実ブローカー／MockBroker を切替
  - リスク管理（RiskManager）、注文管理（OrderManager）、リコンシリエーション（Reconciler）等を統合
- 監視プロセス（run_monitoring.py）
  - CPU / メモリ / ディスク / 実行プロセスの生存チェック
  - データ鮮度チェック（DuckDB の最終価格日）
  - 監視ログの永続化（SQLite）
  - stop flag による安全停止
- 監視エンジン（MonitoringEngine）
  - SystemMonitor / TradeMonitor / RiskMonitor を束ね、アラート発行・KillSwitch 判定を実行
- モニタリング永続層（MonitoringDB）
  - system_status / trade_logs / positions / risk_logs / dashboard 等のテーブル管理
  - マイグレーション処理付き（列追加等）
- Trade モニタ（TradeMonitor）
  - 滞留注文（stale orders）や約定異常価格の検出
- リスクモニタ（RiskMonitor）
  - ドローダウン・ポジション上限の監視、risk_logs への記録
- KillSwitch
  - kill.flag を書き込むことで ExecutionEngine 停止を促す仕組み
- アラート（AlertManager）
  - LINE Messaging API を使った一方向プッシュ通知（クールダウン管理）
- Streamlit ダッシュボード（streamlit_dashboard.py）
  - 監視 DB を読み取りダッシュボードを表示
- Paper Trading 検証レポート（tools/paper_verification_report.py）
  - Paper Trading 用 SQLite から稼働率・注文成功率・レイテンシ等のレポート生成
- ポートフォリオ構築ユーティリティ（portfolio/*）
  - 候補選定、重み計算、セクター上限適用、ポジションサイズ計算（単元丸め含む）
- リサーチ（research/*）
  - momentum / volatility / value ファクター計算、将来リターン、IC 計算、ファクター統計要約
- AI モジュール（ai/*）
  - news_nlp: ニュースを LLM でセンチメント化し ai_scores に書き込み
  - regime_detector: MA200 とマクロセンチメントを合成し市場レジームを判定・書き込み

セットアップ手順
---------------
前提:
- Python 3.10 以上を推奨（| 型注釈・将来のtyping機能の利用のため）
- SQLite は標準ライブラリに含まれます
- 必要な外部パッケージ（最低）:
  - duckdb
  - psutil
  - requests
  - streamlit (ダッシュボード利用時)
  - openai (AI 機能利用時)

推奨手順:
1. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   - pip install duckdb psutil requests streamlit openai

   （プロジェクトに requirements.txt があれば pip install -r requirements.txt）

3. 環境変数（.env）を用意
   - プロジェクトルートに .env または .env.local を作成できます。
   - 自動ロードは既定で有効（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。

主要な環境変数（Settings参照）:
- JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- OPENAI_API_KEY: OpenAI API キー（AI 機能利用時）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE 通知用
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 時の SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: Paper Trading の約定挙動（instant|partial|never|reject、デフォルト instant）
- PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START: プロセス管理・停止フラグ関連
- CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT: 監視閾値
- KABUSYS_ENV: 起動環境 (development | paper_trading | live)、デフォルト development
- LOG_LEVEL: ログレベル (DEBUG|INFO|WARNING|ERROR|CRITICAL)
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）

使い方
------
プロジェクトルートから次のコマンドで主要コンポーネントを実行できます。

1) 監視プロセスの起動
- デフォルトのポーリング間隔 60 秒（環境変数 MONITOR_POLL_INTERVAL で上書き可）
- python -m kabusys.run_monitoring
- 停止は data/stop_requested.flag を作成するか Ctrl+C（KeyboardInterrupt）

注: run_monitoring は監視ログに対して Settings.env に関係なく sqlite_path（本番）を使用します。

2) 実行エンジン（ExecutionEngine）の起動
- KABUSYS_ENV=paper_trading とすると MockBroker を利用し、Paper Trading 用 DB（PAPER_TRADING_SQLITE_PATH）に記録します
- python -m kabusys.run_execution
- 起動時に data/stop_requested.flag が存在する場合は起動を中止します
- 実行中は data/execution.pid に PID を書き込み、停止は stop flag を作ることで安全停止させます

3) Streamlit 監視ダッシュボード
- streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
- 既定は data/monitoring.db（読み取り専用で開きます）

4) Paper Trading 検証レポート生成
- python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- --db オプションで DB パス指定可（環境変数 PAPER_TRADING_SQLITE_PATH でも指定可能）

5) プログラム的な利用（ライブラリ）
- ai.score_news(conn, target_date, api_key=None)
- ai.regime_detector.score_regime(conn, target_date, api_key=None)
- research.calc_momentum(conn, date), research.calc_volatility(...), research.calc_value(...)
- portfolio.select_candidates / calc_equal_weights / calc_score_weights / calc_position_sizes など

停止・フラグ関連
- data/stop_requested.flag: run_monitoring / run_execution のポーリングループを終了させる外部フラグ
- data/kill.flag: KillSwitch が書き込むと ExecutionEngine に停止シグナルを送る（Engine 側で監視）
- PID ファイル: data/execution.pid に ExecutionEngine の PID が記録される

ディレクトリ構成
----------------
（抜粋、主要ファイルのみ記載）
- src/kabusys/
  - __init__.py
  - config.py                     — 環境変数 / 設定管理
  - run_monitoring.py             — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py              — ExecutionEngine 起動スクリプト
  - data/ …                       — 実行時生成されるデータファイル（DB・flag等）
  - ai/
    - __init__.py
    - news_nlp.py                  — ニュース NLP / ai_scores 書き込み
    - regime_detector.py           — レジーム判定（MA200 + マクロセンチメント）
  - monitoring/
    - __init__.py
    - monitoring_db.py             — SQLite テーブル初期化・ラッパー
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - monitoring_engine.py
    - alert_manager.py
    - kill_switch.py
    - streamlit_dashboard.py
  - execution/
    - order_manager.py
    - reconciler.py
    - ... (BrokerClientFactory, ExecutionEngine 等の実装が想定される)
  - portfolio/
    - portfolio_builder.py
    - risk_adjustment.py
    - position_sizing.py
    - __init__.py
  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py
  - tools/
    - __init__.py
    - paper_verification_report.py
  - utils/
    - process_priority.py           — プロセス優先度 / CPU affinity ユーティリティ
    - __init__.py

注意事項 / 運用上のポイント
--------------------------
- .env の自動読み込み
  - プロジェクトルート（.git または pyproject.toml が存在する場所）にある .env / .env.local が自動で読み込まれます
  - OS 環境変数は保護され、.env.local は .env の上書きとして読み込まれます
  - 自動読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください

- Paper Trading と本番データの分離
  - KABUSYS_ENV=paper_trading の場合、run_execution は PAPER_TRADING_SQLITE_PATH に DB を書き、実ブローカー呼び出しは MockBroker に切替えます（本番 DB と完全分離）

- モニタリング DB のマイグレーション
  - monitoring_db.init_monitoring_db は冪等でテーブル作成を行い、既存 DB に対する簡単な列追加マイグレーションも含まれます

- OpenAI 利用
  - AI 機能（news_nlp / regime_detector）を利用するには OPENAI_API_KEY が必要です
  - API 呼び出しはリトライ・エクスポネンシャルバックオフの実装が含まれていますが、API コストやレート制限に注意してください

- プロセス優先度
  - 実行スクリプトは起動時に set_process_priority("high") を呼びます。psutil による操作なので権限不足時は警告が出ます

最小限の開発ワークフロー例
--------------------------
1. 仮想環境作成 & パッケージ導入
2. .env を準備（必須項目を設定）
3. DuckDB に prices_daily / raw_financials / raw_news 等のデータを投入
4. 監視を起動: python -m kabusys.run_monitoring
5. 実行エンジン起動（別プロセス）: python -m kabusys.run_execution
6. Streamlit でダッシュボード確認
7. Paper Trading 検証レポートを生成して挙動を評価

免責・今後の拡張
----------------
- この README はコード内のドキュメント文字列に基づき自動的に要点をまとめたものです。実運用前に設定値や依存関係、ブローカー実装の安全性を必ず確認してください。  
- 将来的に拡張すると想定される点:
  - 銘柄別単元サイズ対応（lot_size を銘柄マスタで管理）
  - より細かな手数料 / スリッページモデル
  - 高度な監視アラート（複数チャネル対応）

お問い合わせ
------------
実装や設計に関する質問があれば、コードの該当モジュール（monitoring/*, execution/*, ai/*, research/*）を参照してください。各モジュール内に詳細な docstring が記載されています。