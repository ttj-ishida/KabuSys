README.md

概要
---
KabuSys は日本株の自動売買システム向けに設計された Python パッケージです。本リポジトリには以下の機能群が含まれます:
- 注文発行・注文状態管理（ExecutionEngine、OrderManager 等）
- 監視・アラート（SystemMonitor、TradeMonitor、RiskMonitor、KillSwitch、AlertManager）
- ポートフォリオ構築・ポジションサイズ計算（portfolio パッケージ）
- 研究用ファクター計算・特徴量解析（research パッケージ）
- ニュース NLP / レジーム判定（AI モジュール、OpenAI 経由）
- 検証ツール（paper trading レポート生成、Streamlit ダッシュボード等）

主な機能
---
- 実行エンジン起動スクリプト（run_execution.py）
  - 本番 / Paper Trading を切替可能（KABUSYS_ENV）
  - Paper Trading 時は MockBrokerClient を利用し、本番 DB と分離して data/paper_trading.db に記録
- 監視ループ（run_monitoring.py / MonitoringEngine）
  - システムリソース、データ鮮度、注文滞留、約定異常価格、ドローダウン等を定期チェック
  - LINE による通知（AlertManager）
  - KillSwitch による停止指令出力（data/kill.flag）
- AI 補助機能
  - ニュースを LLM（OpenAI）でスコア化し ai_scores に保存（news_nlp.score_news）
  - マクロニュース + ETF MA を合成して市場レジームを判定（regime_detector.score_regime）
- 研究用ファクター計算（research.calc_momentum, calc_volatility, calc_value 等）
- Paper Trading 検証レポート生成ツール（tools/paper_verification_report.py）
- 監視ダッシュボード（Streamlit ベース）

動作環境・依存
---
推奨:
- Python 3.10+
主要依存（抜粋）:
- duckdb
- psutil
- requests
- streamlit（ダッシュボード使用時）
- openai（AI モジュール使用時）

インストール例:
- requirements.txt がある場合:
  pip install -r requirements.txt
- ない場合（最低限）:
  pip install duckdb psutil requests streamlit openai

セットアップ手順
---
1. リポジトリをクローン／展開
2. Python 仮想環境を作成・有効化
   python -m venv .venv
   source .venv/bin/activate（Windows の場合は .venv\Scripts\activate）
3. 依存パッケージをインストール
   pip install duckdb psutil requests streamlit openai
   または pip install -r requirements.txt
4. 環境変数設定
   - プロジェクトルートに .env または .env.local を置くと自動的に読み込まれます（既存 OS 環境変数は保護されます）。
   - 自動読み込みを無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。
5. 必須環境変数（例）
   - JQUANTS_REFRESH_TOKEN: J-Quants API 用トークン
   - KABU_API_PASSWORD: kabuステーション API パスワード
   - OPENAI_API_KEY: OpenAI を使う場合に必要
   （詳細は下記 環境変数一覧 を参照）

環境変数（主なもの）
---
- KABUSYS_ENV: 起動環境。allowed: development / paper_trading / live（デフォルト: development）
- OPENAI_API_KEY: OpenAI API キー（AI モジュール用）
- JQUANTS_REFRESH_TOKEN: J-Quants API
- KABU_API_PASSWORD: kabuステーション API
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: AlertManager（LINE通知）用
- SQLITE_PATH: 監視 DB パス（デフォルト: data/monitoring.db）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- PAPER_TRADING_SQLITE_PATH: Paper Trading の SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: paper_trading 時の約定挙動（instant|partial|never|reject、デフォルト: instant）
- PID_FILE_PATH: ExecutionEngine の PID ファイルパス（デフォルト: data/execution.pid）
- KILL_FLAG_PATH: KillSwitch が書き込むフラグファイル（デフォルト: data/kill.flag）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動削除する場合は "1"
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト: 60）
- CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT: 監視のしきい値

簡単な .env サンプル
---
KABUSYS_ENV=development
OPENAI_API_KEY=sk-xxxx...
JQUANTS_REFRESH_TOKEN=xxxx
KABU_API_PASSWORD=xxxx
LINE_CHANNEL_ACCESS_TOKEN=
LINE_USER_ID=
SQLITE_PATH=data/monitoring.db
DUCKDB_PATH=data/kabusys.duckdb
PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
MONITOR_POLL_INTERVAL=60

使い方
---

起動・実行
- 監視ループ（Monitoring）
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒で指定できます（デフォルト 60）。
  - 実行:
    python -m kabusys.run_monitoring
  - 動作:
    - process priority を high に設定（psutil により OS に依存して設定されます）
    - SQLite / DuckDB に接続し init_monitoring_db() を呼び出してテーブルを保証
    - 監視ループを実行し system/trade/risk などをチェックしてログ保存・アラート発行

- 実行エンジン（ExecutionEngine）
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、Paper Trading 用 DB（PAPER_TRADING_SQLITE_PATH）に記録します
  - 実行:
    python -m kabusys.run_execution
  - 実行中の停止:
    - プロジェクトルート/data/stop_requested.flag を作成すると run_execution は検知して安全に停止します
    - KillSwitch (data/kill.flag) が書かれると ExecutionEngine 側で停止指示を受け取る運用

- Paper Trading 検証レポート
  - 対象 DB は PAPER_TRADING_SQLITE_PATH またはオプション --db
  - 実行例:
    python -m kabusys.tools.paper_verification_report
    python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
    python -m kabusys.tools.paper_verification_report --db data/paper_trading.db

- Streamlit ダッシュボード（監視 UI）
  - 実行例:
    streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - 監視 DB を読み取り専用で開き、ダッシュボード表示を行います（MonitoringEngine が稼働中であることが前提）

- AI モジュール（ニュース NLP / レジーム判定）
  - news_nlp.score_news(conn, target_date, api_key=None)
    - DuckDB 接続を与えて指定日分のニュースをスコア化し ai_scores に書き込み
    - api_key 引数または OPENAI_API_KEY 環境変数が必要
  - regime_detector.score_regime(conn, target_date, api_key=None)
    - DuckDB から ETF 1321 の MA とマクロニュースからレジームを判定して market_regime テーブルに保存

停止・制御
- stop_requested.flag: run_monitoring / run_execution は project_root/data/stop_requested.flag を存在チェックし、存在すればループを終了します
- kill.flag: KillSwitch が書き込むファイルで、ExecutionEngine に対する強制停止トリガーとして用いられます（path は Settings.kill_flag_path で制御可能）
- PID ファイル: ExecutionEngine は data/execution.pid を PID ファイルとして扱います（SystemMonitor が stale PID を検出するロジックあり）

注意事項 / 運用メモ
---
- Settings は .env / .env.local / OS 環境変数をロードします（優先順位は OS環境 > .env.local > .env）。プロジェクトルート自動検出は .git または pyproject.toml を基準に行います。
- monitoring は環境にかかわらず本番 sqlite_path を使用します（run_monitoring のドキュメント参照）。
- Paper Trading は本番 DB と完全に分離するため PAPER_TRADING_SQLITE_PATH を必ず確認してください。
- OpenAI API 呼び出しはレートリミットや一時エラーに対してエクスポネンシャルバックオフでリトライする実装が含まれますが、API キーとコストに注意してください。
- process priority / CPU affinity の設定は OS 権限に依存し、失敗した場合はログに警告が出ます。

ディレクトリ構成
---
src/kabusys/
- __init__.py
- config.py                — 環境変数 / 設定管理
- run_monitoring.py        — SystemMonitor ポーリングループ起動スクリプト
- run_execution.py         — ExecutionEngine 起動スクリプト
- data/                    — 実行時生成ファイル (例: monitoring.db, paper_trading.db, execution.pid, kill.flag) ※リポジトリに含まれない
- tools/
  - __init__.py
  - paper_verification_report.py
- ai/
  - __init__.py
  - news_nlp.py
  - regime_detector.py
- monitoring/
  - __init__.py
  - monitoring_db.py
  - system_monitor.py
  - trade_monitor.py
  - risk_monitor.py
  - notify/ (AlertManager は monitoring/alert_manager.py)
  - monitoring_engine.py
  - kill_switch.py
  - streamlit_dashboard.py
- execution/
  - order_manager.py
  - reconciler.py
  - (その他 broker, engine, order_repository 等の実装が想定される)
- portfolio/
  - portfolio_builder.py
  - risk_adjustment.py
  - position_sizing.py
- research/
  - __init__.py
  - factor_research.py
  - feature_exploration.py
- utils/
  - __init__.py
  - process_priority.py

（上記は本リポジトリの主要ファイル・モジュールを抜粋した構成です）

開発・テスト
---
- .env の自動ロードは便利ですが、ユニットテストや CI では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自動ロードを無効にできます。
- AI モジュールの外部 API 呼び出しはテストでパッチ（モック）しやすいよう設計されています（内部呼び出し関数を差し替え可能）。

貢献・ライセンス
---
- 本 README ではライセンス情報は含めていません。リポジトリに LICENSE ファイルがあればそれに従ってください。

補足
---
- ここに記載したコマンドやファイルパスは、ソース内のデフォルト値に基づいています。運用環境では .env で適切に上書きしてください。
- 何か特定の機能（例: Broker 実装、ExecutionEngine の詳細な起動オプション、テスト例など）についてドキュメントが必要であれば、どの箇所を深掘りするか教えてください。