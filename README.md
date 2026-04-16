KabuSys — README
===============

概要
----
KabuSys は日本株向けの自動売買システムのコードベースです。  
本リポジトリは以下の主要機能を提供します：

- 注文発行・管理の ExecutionEngine（本番・Paper Trading 切替）
- モニタリング（システム・注文・リスク監視）、アラート送信（LINE）
- ポートフォリオ構築（候補選定・重み付け・ポジションサイズ算出）
- リサーチ／ファクター計算（DuckDB を使った各種ファクター）
- AI を用いたニュースセンチメント（OpenAI API 連携）
- Paper Trading 検証レポートや Streamlit ダッシュボード等の運用ツール

設計方針のポイント：
- DuckDB / SQLite をデータ層に利用（分析・監視ログを分離）
- 本番と Paper Trading の DB は分離（Paper は data/paper_trading.db が既定）
- AI 呼び出しは API キー依存（失敗時はフォールバックや安全な挙動）
- .env ファイル自動読み込み機能あり（必要なら無効化可能）

主な機能一覧
----------------
- Execution
  - 実際のブローカー／Mock ブローカーを切り替えて注文を送信・管理
  - 再起動後のリコンシリエーション（Reconciler）で状態を復元
  - RiskManager による発注制限、OrderManager の state machine
- Monitoring
  - SystemMonitor：CPU/メモリ/ディスク/プロセス生存確認、データ鮮度チェック
  - TradeMonitor：滞留注文・約定異常価格検出
  - RiskMonitor：ドローダウン・ポジション上限検出とリスクログ記録
  - AlertManager：LINE へプッシュ通知（クールダウン管理）
  - KillSwitch：条件により data/kill.flag を書き込み ExecutionEngine を停止
  - Streamlit ダッシュボード（read-only 接続）
- Portfolio
  - 候補選定（score/rank）、等配分・スコア重み配分、リスク調整（セクター上限）
  - ポジションサイズ計算（単元丸め、aggregate cap、コストバッファ）
- Research
  - Momentum / Volatility / Value ファクター計算（DuckDB）
  - 将来リターン・IC 計算・要約統計
- AI
  - news_nlp: ニュースを LLM でセンチメントスコア化して ai_scores テーブルへ保存
  - regime_detector: ma200 とマクロニュースの LLM センチメントを合成して市場レジーム判定
- Tools
  - paper_verification_report: Paper Trading データから検証レポートを生成
  - streamlit_dashboard: 監視データ可視化

前提 / 依存パッケージ
--------------------
開発環境の例（pip でインストールしてください）:
- Python 3.10+
- duckdb
- psutil
- requests
- openai
- streamlit (ダッシュボード利用時)
- その他標準ライブラリ（sqlite3 等は組み込み）

requirements.txt は本リポジトリに含まれていないため、上記パッケージを仮想環境にインストールしてください。

セットアップ手順
----------------
1. リポジトリをクローン・チェックアウト
   - git clone ... && cd <repo>

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   - pip install duckdb psutil requests openai streamlit

4. 環境変数（.env）設定
   - プロジェクトルートに .env を置くことで自動読み込みされます（config.py の既定動作）。
   - 自動読み込みを無効化する場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
   - 主要な環境変数（代表例）:
     - KABUSYS_ENV: development / paper_trading / live（既定: development）
     - JQUANTS_REFRESH_TOKEN: （必須）
     - KABU_API_PASSWORD: kabu ステーション API パスワード（必須）
     - OPENAI_API_KEY: OpenAI API キー（AI モジュール利用時）
     - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: LINE Push 用
     - PAPER_FILL_MODE: instant | partial | never | reject（Paper Trading）
     - PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（既定: data/paper_trading.db）
     - SQLITE_PATH: 監視用 SQLite（既定: data/monitoring.db）
     - DUCKDB_PATH: DuckDB ファイルパス（既定: data/kabusys.duckdb）
     - PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START 等

5. data ディレクトリ
   - 実行中に PID / flag / sqlite 等のファイルが生成されます。必要に応じて data/ を作成してください（多くの処理は自動で mkdir を行います）。

使い方（実行例）
----------------

- Monitoring ループ起動
  - 簡単に監視ループを起動する:
    - python -m kabusys.run_monitoring
  - ポーリング間隔の上書き:
    - export MONITOR_POLL_INTERVAL=30
  - 備考: monitor は KABUSYS_ENV にかかわらず sqlite_path（本番監視 DB）を使用します。
  - 停止: プロセスを停止するか、プロジェクトルート/data/stop_requested.flag を作成します（本スクリプトは起動時に stop flag を参照）。

- ExecutionEngine（注文エンジン）起動
  - python -m kabusys.run_execution
  - Paper Trading モード:
    - export KABUSYS_ENV=paper_trading
    - この場合、MockBrokerClient を使い data/paper_trading.db（または PAPER_TRADING_SQLITE_PATH）に記録します（本番 DB と分離）。
  - 起動フロー:
    - PID ファイルを書き込み、内部で Reconciler を呼ぶなどして安全にセッションを開始します。
  - 停止:
    - data/stop_requested.flag を作成する、または KillSwitch により data/kill.flag が書き込まれると停止処理が走ります。

- Paper Trading 検証レポート
  - 単発レポート生成:
    - python -m kabusys.tools.paper_verification_report
    - 期間指定:
      - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
    - DB 指定:
      - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
  - 主要な閾値（ソース内定義）
    - 稼働率 >= 99.0%
    - 注文成功率（Filled/Created） >= 90.0%
    - 送信率（Sent/Created） >= 95.0%
    - P95 レイテンシ <= 200 ms

- Streamlit ダッシュボード（監視）
  - 起動:
    - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - ダッシュボードは監視 DB に対して読み取り専用で開きます（URI に ?mode=ro を付与）。

- AI（ニューススコアリング / レジーム判定）
  - OpenAI API キーが必要（OPENAI_API_KEY）。呼び出し例:
    - Python から kabusys.ai.score_news / kabusys.ai.regime_detector.score_regime を呼ぶ
  - 動作上の注意:
    - レートリミットや 5xx を考慮したリトライ実装あり
    - 失敗時はフェイルセーフ（例: macro_sentiment = 0.0）で継続

運用・管理
-----------
- Kill / Stop フラグ
  - ExecutionEngine を停止させるための flag ファイル:
    - data/kill.flag — KillSwitch が書き込む（永続停止理由を含む）
    - data/stop_requested.flag — run_execution/run_monitoring の外部停止トリガ（存在チェックでループを抜ける）
  - KillSwitch は RiskMonitor の判定により kill.flag を作成します。

- PID とプロセス優先度
  - 起動スクリプトは psutil を用いてプロセス優先度を "high" に設定します（権限が必要な場合あり）。
  - 無効な OS ではスキップされます。

- DB マイグレーション
  - monitoring_db.init_monitoring_db() は冪等にテーブル・インデックスを作成し、必要に応じて軽微なスキーマ追加（列追加）を行います。

ディレクトリ構成（主要ファイル）
--------------------------------
- src/kabusys/
  - __init__.py
  - config.py — 環境変数 / .env 読み込みロジック
  - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py — ExecutionEngine 起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート
  - execution/
    - execution_engine.py, order_manager.py, order_repository.py, reconciler.py, risk_manager.py, broker_factory.py, …（注文周り）
  - monitoring/
    - monitoring_db.py — SQLite 用永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
    - system_monitor.py, trade_monitor.py, risk_monitor.py, monitoring_engine.py
    - kill_switch.py, alert_manager.py, streamlit_dashboard.py
  - portfolio/
    - portfolio_builder.py, position_sizing.py, risk_adjustment.py
  - research/
    - factor_research.py, feature_exploration.py
  - ai/
    - news_nlp.py, regime_detector.py
  - data/  (実行時に生成されることが多い)
    - monitoring.db (SQLITE_PATH の既定)
    - paper_trading.db (PAPER_TRADING_SQLITE_PATH の既定)
    - kabusys.duckdb (DUCKDB_PATH の既定)
    - execution.pid, stop_requested.flag, kill.flag, …

開発・デバッグのヒント
---------------------
- ログ:
  - 起動スクリプトは logging.basicConfig(level=logging.INFO) を設定しています。必要なら LOG_LEVEL 環境変数で設定を行ってください（Settings.log_level を参照）。
- .env のパース:
  - config._parse_env_line はシェル風の export やクォート、インラインコメントにかなり忠実に対応します。
- テスト:
  - AI 呼び出し部分（_openai_api など）はユニットテストで差し替え（モック）しやすい設計です。
- 注意:
  - MONITOR（run_monitoring）は監視用 DB（sqlite_path）を使用します。Paper Trading の監視も本設定に依存するため意図しない上書きを避けるため .env を確認してください。

ライセンス / 貢献
-----------------
- この README はコードベースからの自動生成ドキュメントです。実運用前に .env の内容や DB パス、API キーの管理方針を必ず確認してください。  
- 貢献は Pull Request を通じて受け付けてください（詳細はリポジトリの CONTRIBUTING.md に従ってください／存在する場合）。

付録：よく使うコマンド例
-----------------------
- 監視開始（デフォルト 60 秒間隔）:
  - MONITOR_POLL_INTERVAL 環境変数で上書き可能
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- ExecutionEngine（Paper）起動:
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
- Paper レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- Streamlit ダッシュボード:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

ご不明点や補足してほしい内容があれば教えてください。README の補完（例: .env.example、requirements.txt、起動用 systemd ユニット例など）も作成できます。