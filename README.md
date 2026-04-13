README
======

概要
----
KabuSys は日本株の自動売買・研究・監視を目的とした Python パッケージです。本リポジトリには注文実行エンジン、監視コンポーネント、ポートフォリオ構築、ファクター計算、ニュース NLP（OpenAI を利用）などの主要ロジックが含まれます。ローカルの DuckDB / SQLite をデータ層として利用し、paper_trading（モックブローカー）モードをサポートします。

主な特徴
--------
- 実行エンジン（ExecutionEngine）: ブローカークライアントを介した注文発行、リスク管理、リコンシリエーション
- 監視（Monitoring）: システム・注文・リスク監視、LINE 通知、kill flag による安全停止
- ポートフォリオ構築: 候補選定・重み算出・ポジションサイズ決定・セクター制約
- 研究モジュール: ファクター計算（Momentum/Value/Volatility）、特徴量探索、IC 計算
- ニュース NLP / レジーム判定: OpenAI を用いたニュースセンチメント評価と市場レジーム決定
- Paper Trading 検証ツール: 運用ログからレポートを生成するスクリプト
- Streamlit ダッシュボード: 監視 DB を可視化する UI

要件
----
- Python 3.9+
- 主な依存ライブラリ（例）:
  - duckdb
  - psutil
  - requests
  - openai
  - streamlit (ダッシュボード利用時)
- SQLite（組み込み）
- ネットワーク（LINE / OpenAI API を使う場合）

セットアップ
----------
1. リポジトリを取得:
   - git clone ...
2. 仮想環境を作成して有効化:
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 開発パッケージをインストール:
   - pip install -U pip
   - pip install duckdb psutil requests openai streamlit
   - （パッケージ管理に requirements.txt / pyproject.toml がある場合はそれに従ってください）
4. データディレクトリを作成:
   - mkdir -p data
5. 環境変数 / .env:
   - プロジェクトルートに .env/.env.local を置くと自動で読み込まれます（.git または pyproject.toml を基準にルートを探索）。
   - 自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。
   - 主要な環境変数（抜粋）:
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
     - OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector）
     - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD
     - SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
     - DUCKDB_PATH（DuckDB、デフォルト: data/kabusys.duckdb）
     - PAPER_TRADING_SQLITE_PATH（paper トレード時の DB、デフォルト: data/paper_trading.db）
     - PAPER_FILL_MODE（paper_trading の約定動作: instant|partial|never|reject、デフォルト: instant）
     - PID_FILE_PATH（ExecutionEngine の PID ファイル、デフォルト: data/execution.pid）
     - KILL_FLAG_PATH（停止フラグファイル、デフォルト: data/kill.flag）
     - LOG_LEVEL（INFO 等）
   - 簡易 .env 例:
     JQUANTS_REFRESH_TOKEN=...
     KABU_API_PASSWORD=...
     OPENAI_API_KEY=...
     KABUSYS_ENV=paper_trading

使い方
------

実行エンジン（Execution）
- 目的: 注文の実行・リスク管理・リコンシリエーションを行う主要実行プロセス
- 起動:
  - python -m kabusys.run_execution
  - 実行時、KABUSYS_ENV が paper_trading の場合はモックブローカーが利用され、data/paper_trading.db に記録されます（本番 DB と分離）。
- 動作:
  - プロセス優先度を "high" に設定（psutil を使用、権限不足時は警告）。
  - SQLite / DuckDB に接続し、関連テーブルが無ければ初期化します。
  - ExecutionEngine.run_session() によりセッションを開始します。

監視ループ（Monitoring）
- 目的: System / Trade / Risk の定期チェック、アラート送信、kill flag 評価
- 起動:
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可能。デフォルト 60 秒。
- 備考:
  - Monitoring は KABUSYS_ENV に関わらず本番の sqlite_path を使用します（監視は本番 DB を対象に行いたいため）。
  - kill.flag（Settings.kill_flag_path）を書き込むと ExecutionEngine に停止シグナルを送ります。flag のクリアは KillSwitch.clear() を使用（Execution 起動時に自動で消す設定あり）。

Streamlit ダッシュボード
- 起動:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
- 機能:
  - ポートフォリオ概要、保有ポジション、発注ログ、最新システムステータス、リスクログを表示します。

Paper Trading 検証レポート
- 目的: paper_trading DB から運用品質（稼働率・注文成功率・レイテンシ等）を判定する
- 実行:
  - python -m kabusys.tools.paper_verification_report
  - 引数:
    --from YYYY-MM-DD --to YYYY-MM-DD --db PATH
  - デフォルト DB: data/paper_trading.db（PAPER_TRADING_SQLITE_PATH で上書き可）

AI（ニュース NLP / レジーム判定）
- OpenAI API を利用する機能:
  - kabusys.ai.news_nlp.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
- 要件:
  - OPENAI_API_KEY を環境変数で設定するか、関数に api_key を渡してください。
  - API 呼び出しはリトライ・バックオフ等のフェイルセーフ実装あり。失敗時はスコアをフォールバックし継続します。

データベース初期化
- monitoring 用 SQLite は init_monitoring_db() でテーブル / インデックスを冪等に作成します（run_monitoring/run_execution 内で自動呼び出し）。
- DuckDB は prices_daily / raw_financials 等のテーブルを期待します（データ投入は別途パイプライン）。

運用上の注意
- プロセス優先度（high）や CPU affinity 設定は権限が必要です。権限不足の際は警告が出ますが処理は続行します。
- OpenAI / LINE 通知は外部サービスに依存するため、API キーやネットワークの可用性を確認してください。
- kill.flag が存在すると ExecutionEngine による処理停止がトリガーされます。手動で消す場合は data/kill.flag を削除してください。

ディレクトリ構成（抜粋）
--------------------
src/kabusys/
- __init__.py — パッケージ定義
- config.py — 環境変数 / 設定読み込みロジック（.env 自動ロード、Settings クラス）
- run_monitoring.py — SystemMonitor ポーリングループの起動スクリプト
- run_execution.py — ExecutionEngine 起動スクリプト

サブパッケージ:
- ai/
  - news_nlp.py — ニュースセンチメントの OpenAI スコアリング
  - regime_detector.py — 市場レジーム判定（MA200 + マクロセンチメント）
- monitoring/
  - monitoring_db.py — SQLite ベースの永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
  - system_monitor.py — システム状態・データ鮮度チェック
  - trade_monitor.py — 注文滞留・約定異常チェック
  - risk_monitor.py — ドローダウン・ポジション上限監視
  - kill_switch.py — kill.flag による停止シグナル
  - alert_manager.py — LINE 通知
  - monitoring_engine.py — 各モニタの束ね
  - streamlit_dashboard.py — Streamlit UI
- execution/
  - reconciler.py — 起動時リコンシリエーション
  - order_manager.py — 注文作成/送信等の高レベル API
  - ...（broker, order_repository, order_record 等が存在）
- portfolio/
  - portfolio_builder.py — 候補選定・重み計算
  - position_sizing.py — 株数決定・キャップ適用
  - risk_adjustment.py — セクターキャップ・レジーム乗数
- research/
  - factor_research.py — Momentum/Volatility/Value 等のファクター
  - feature_exploration.py — 将来リターン・IC・統計サマリー
- tools/
  - paper_verification_report.py — Paper Trading 検証レポート生成 CLI
- utils/
  - process_priority.py — プロセス優先度・CPU affinity ヘルパ

補足（トラブルシュート）
-----------------------
- .env 読み込みが効いていない場合:
  - プロジェクトルートの判定に .git または pyproject.toml を利用します。これらがない場合は自動ロードがスキップされます。
  - 強制的に無効化している場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を確認してください。
- OpenAI 未設定エラー:
  - news_nlp.score_news / regime_detector.score_regime は API キーが必須で、未設定時は ValueError を送出します。
- MONITOR_POLL_INTERVAL:
  - run_monitoring のポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で秒数を指定できます。1 未満や無効な値はデフォルト 60 秒にフォールバックします。

以上。開発・運用に際して不明点があればソース内の docstring（各モジュール冒頭）を参照してください。README に未記載の実行フロー・内部仕様は各モジュールで詳細に説明されています。