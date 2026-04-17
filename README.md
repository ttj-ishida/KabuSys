KabuSys — 日本株自動売買システム（README）
================================

概要
----
KabuSys は日本株の自動売買・リサーチ・監視を目的とした Python ベースのシステムです。本リポジトリは以下の主要機能を備えます。

- 発注・注文管理・リコンシリエーション（ExecutionEngine）
- システム・注文・リスク監視およびアラート（Monitoring）
- ポートフォリオ構築ユーティリティ（選定・重み・ポジションサイズ）
- ファクター計算・特徴量探索（Research）
- ニュース NLP による銘柄センチメント（AI モジュール）
- Paper Trading 用検証レポート生成ツール
- Streamlit を使った監視ダッシュボード

主な設計思想は「現実的な運用を想定した堅牢性」と「テストしやすい純粋関数・明確な境界」です。

主な機能一覧
-------------
- Execution
  - Broker クライアント抽象化（実運用 / Paper Trading の分離）
  - OrderManager（状態遷移・重複検知）
  - Reconciler（起動時の自動復旧：Order / Position 照合）
  - RiskManager（注文前リスクチェック）
- Monitoring
  - SystemMonitor: CPU/Mem/Disk/プロセス生存・データ鮮度確認
  - TradeMonitor: 注文滞留・約定異常チェック
  - RiskMonitor: ドローダウン・ポジション数監視とアラート記録
  - KillSwitch: 条件に応じた停止フラグ書き込み（data/kill.flag）
  - AlertManager: LINE Push 通知（クールダウン管理）
  - SQLite ベースの監視 DB（スキーマ生成・簡易マイグレーション実装）
  - Streamlit ダッシュボード表示スクリプト
- Portfolio
  - 候補選定、等重・スコア重み、リスク調整（セクター制限・レジーム乗数）
  - ポジションサイズ計算（単元株丸め・aggregate cap）
- Research
  - モメンタム / バリュー / ボラティリティ等のファクター計算（DuckDB）
  - 将来リターン・IC・統計サマリー
- AI
  - news_nlp: OpenAI を使ったニュースセンチメント（銘柄別スコア）
  - regime_detector: ma200 とマクロニュースを合成した市場レジーム判定
- Tools
  - Paper Trading 検証レポート出力（sqlite から集計）
  - ユーティリティ（プロセス優先度設定など）

動作要件
--------
- Python 3.10+
- 主要ライブラリ（例、requirements に記載する想定）
  - duckdb
  - psutil
  - requests
  - openai
  - streamlit
  - （SQLite は標準ライブラリ）
- OS: Linux / macOS / Windows（プロセス優先度や cpu_affinity は OS に依存する挙動あり）

セットアップ手順
----------------
1. リポジトリをクローンしてワークディレクトリへ移動
   - git clone ... && cd <repo>

2. 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - pip install duckdb psutil requests openai streamlit
   - （プロダクション用に requirements.txt を作成して管理してください）

4. 環境変数の設定
   - プロジェクトルートに .env または .env.local を置くと自動ロードされます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると無効化）。
   - 代表的な環境変数（.env 例）:
     - KABUSYS_ENV=development | paper_trading | live
     - JQUANTS_REFRESH_TOKEN=...
     - KABU_API_PASSWORD=...
     - OPENAI_API_KEY=...
     - LINE_CHANNEL_ACCESS_TOKEN=...
     - LINE_USER_ID=...
     - DUCKDB_PATH=data/kabusys.duckdb
     - SQLITE_PATH=data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
     - PAPER_FILL_MODE=instant    # instant|partial|never|reject
     - LOG_LEVEL=INFO
     - MONITOR_POLL_INTERVAL=60   # run_monitoring のポーリング秒（0以下は無効）
   - 注意: KABUSYS_ENV が paper_trading の場合、Execution は MockBroker を使い paper トランザクションは data/paper_trading.db に保存されます（本番DBと完全に分離）。

5. データディレクトリを作成
   - mkdir -p data

使い方（主な起動・ツール）
------------------------

- 監視ループ（SystemMonitor をポーリングして monitoring DB を更新）
  - 実行:
    - python -m kabusys.run_monitoring
  - 補足:
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可能。デフォルト 60 秒。
    - run_monitoring は Settings.getenv（KABUSYS_ENV を含む）に関係なく本番 sqlite_path を使用し init_monitoring_db を実行します。
    - 停止は data/stop_requested.flag を作成することで検知して終了します。

- ExecutionEngine（発注エンジン）
  - 実行:
    - python -m kabusys.run_execution
  - 補足:
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を利用し PAPER_TRADING_SQLITE_PATH (デフォルト data/paper_trading.db) に記録します。
    - 起動時に data/stop_requested.flag が存在すると起動せず終了します。
    - 実行中も data/stop_requested.flag を作成すると安全に停止します。
    - PID ファイル: data/execution.pid（Settings.pid_file_path に基づく）

- Streamlit ダッシュボード（監視データ表示）
  - 実行:
    - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - 説明:
    - read-only 接続で monitoring DB を開き、Overview / Positions / Orders / System タブを表示します。

- Paper Trading 検証レポート
  - 実行:
    - python -m kabusys.tools.paper_verification_report
    - オプション: --from YYYY-MM-DD --to YYYY-MM-DD --db PATH
  - 説明:
    - PAPER_TRADING_SQLITE_PATH（または --db）を参照して注文・監視ログを集計し PASS/FAIL 判定を出力します。

- AI / Regime スコアリング（プログラム内 API）
  - news_nlp.score_news(conn, target_date, api_key=None)
  - ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - 注意:
    - OpenAI API キーは引数で渡すか環境変数 OPENAI_API_KEY を設定してください。
    - 失敗時はフェイルセーフ（部分的にスコア取得し書き込み）を行う設計です。

- プロセス優先度設定ユーティリティ
  - kabusys.utils.process_priority.set_process_priority("high"|"normal"|"low")
  - run_monitoring / run_execution の起動時に最初に呼び出しています（psutil が必要）。

設定とファイル（フラグ / PID）
-----------------------------
- data/stop_requested.flag
  - 管理者が作ることで run_* スクリプトがループを脱して停止するためのフラグ。
- data/execution.pid
  - ExecutionEngine が起動時に書き込む PID ファイル。SystemMonitor はこの PID を参照してプロセス生存チェックを行う。
- data/kill.flag
  - KillSwitch が書き込むファイル。リスク条件を満たすと Execution の停止を指示するために作成されます（Execution 側は kill.flag を見てシャットダウンします）。
- DB マイグレーション: monitoring_db.init_monitoring_db() は必要なテーブルを作成し、既存 DB に不足カラムがあれば簡易マイグレーション（ALTER TABLE ADD COLUMN）を行います。

ディレクトリ構成（主要ファイル）
-----------------------------
（src/kabusys 以下の主な構成を抜粋）

- src/kabusys/
  - __init__.py
  - config.py                      — 環境変数 / Settings 管理（.env 自動ロード）
  - run_monitoring.py              — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py               — ExecutionEngine 起動スクリプト
  - utils/
    - process_priority.py          — プロセス優先度 / CPU affinity ユーティリティ
  - monitoring/
    - __init__.py
    - monitoring_db.py             — SQLite 永続化層（init / MonitoringDB）
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
    - (broker_factory, execution_engine, order_repository, order_record, risk_manager 等)
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py
  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py
  - ai/
    - news_nlp.py
    - regime_detector.py
    - __init__.py
  - data/                           — 実行時に使用する SQLite / DuckDB / フラグファイル等（リポジトリ外 or .gitignored にするべき）
  - tools/
    - paper_verification_report.py
    - __init__.py

開発メモ / 注意点
-----------------
- KABUSYS_ENV の値は "development", "paper_trading", "live" のいずれかのみ有効です。paper_trading は本番 DB と完全に分離されるよう設計されています。
- Settings は .env / .env.local を自動的に読み込みますが、OS 環境変数が優先されます。自動ロードを無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB はリサーチ・ファクター計算向けの列指向 DB として利用します（prices_daily / raw_financials 等のテーブルを前提）。
- OpenAI を用いる機能は外部 API に依存するため、実行時に API キーを必ず設定してください。失敗時は多くの箇所でフォールバック（スコア 0.0 など）しますが、完全な結果は得られません。
- ローカルでの Paper Trading 検証時は PAPER_TRADING_SQLITE_PATH を適切に分離してください（デフォルト: data/paper_trading.db）。

ライセンス / 貢献
-----------------
- この README はコードベースに基づいたドキュメントです。実装の拡張やバグ修正は PR を通して行ってください。実際のライセンスはプロジェクトの LICENSE を参照してください（このサンプルではライセンスファイルは含まれていません）。

補足や例が必要であれば、どのコンポーネント（例: Execution の起動フロー、monitoring のアラート設定、AI スコアリングのユースケースなど）について詳しく知りたいか教えてください。