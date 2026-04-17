KabuSys — README
=================

概要
----
KabuSys は日本株向けの自動売買／研究／監視を目的とした軽量なコードベースです。本リポジトリには次のような機能群が含まれます。

- 注文発行・状態管理（ExecutionEngine、OrderManager、Reconciler）
- 監視（SystemMonitor / TradeMonitor / RiskMonitor / MonitoringEngine）
- ポートフォリオ構築（候補選定、重み計算、ポジションサイジング、セクター制限）
- 研究用ファクター計算・特徴量解析（ファクター計算、IC 計算、将来リターン）
- AI 帰属のニュースセンチメント（OpenAI を利用したニュースNLP / レジーム判定）
- Paper Trading 用検証レポート生成スクリプト
- Streamlit ベースの監視ダッシュボード

主な設計方針
- DB は SQLite / DuckDB を利用（監視ログは SQLite、分析は DuckDB）
- Paper Trading は本番 DB と完全分離（デフォルト: data/paper_trading.db）
- 環境変数・.env による設定管理（自動ロード機能あり）
- LLM 呼び出しは失敗耐性（リトライ・フォールバック）を考慮

機能一覧
-------
主要な機能（抜粋）：

- 実行系
  - ExecutionEngine 起動スクリプト (src/kabusys/run_execution.py)
  - ブローカー選択工場（実ブローカー / MockBroker）
  - OrderManager / OrderRepository による注文管理
  - Reconciler による再起動後の自動照合・復旧

- 監視系
  - SystemMonitor: CPU / メモリ / ディスク / プロセス監視・データ鮮度チェック
  - TradeMonitor: 滞留注文・約定異常価格検出
  - RiskMonitor: ドローダウン・ポジション上限監視
  - KillSwitch / AlertManager: 条件に応じた停止フラグ書き込み・LINE 通知
  - MonitoringEngine / run_monitoring.py: ポーリングループで各モニタを実行
  - streamlit_dashboard.py: Web ダッシュボード（Streamlit）

- ポートフォリオ／リスク
  - 候補選定、等金額／スコア重み、リスクベースの枚数算出
  - セクター集中制限、レジーム乗数

- 研究（Research）
  - ファクター計算（Momentum/Value/Volatility）
  - 将来リターン、IC（Spearman）計算、統計サマリー

- AI（OpenAI）
  - news_nlp: ニュースを LLM でスコアリングし ai_scores に保存
  - regime_detector: ma200 とマクロニュースの LLM スコアを合成してレジーム判定

- ツール
  - paper_verification_report: Paper Trading DB から検証レポートを生成

セットアップ手順
---------------
前提
- Python 3.10 以上（型ヒントで | 演算子等を使用）
- 任意の仮想環境（venv, virtualenv, poetry 等）を推奨

1. ソースを配置
   - ソースは src/kabusys 以下にある想定です。パッケージを実行するにはプロジェクトルートを PYTHONPATH に含めるか、editable install を行ってください。
     例:
       - export PYTHONPATH=$(pwd)/src
       - または pip install -e .（setup がある場合）

2. 必要なパッケージをインストール
   - 最低限のパッケージ例:
     pip install duckdb psutil requests openai streamlit
   - 他にもプロジェクトで使用するパッケージがあれば requirements.txt を参照してください（本リポジトリに無い場合は上記の主要パッケージを入れてください）。

3. 環境変数（.env）
   - プロジェクトルートの .env/.env.local を自動ロードします（OS 環境変数が優先）。自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。
   - 主要な環境変数（主なもののみ列挙）:
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
     - JQUANTS_REFRESH_TOKEN: J-Quants API 用トークン（必須）
     - KABU_API_PASSWORD: kabuステーション API パスワード（必須）
     - OPENAI_API_KEY: OpenAI API キー（AI 機能使用時）
     - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: LINE 通知用（任意）
     - SQLITE_PATH: 監視用 SQLite DB（デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH: Paper Trading DB（デフォルト: data/paper_trading.db）
     - DUCKDB_PATH: DuckDB ファイル（デフォルト: data/kabusys.duckdb）
     - PAPER_FILL_MODE: paper_trading 時の約定モード（instant|partial|never|reject、デフォルト: instant）
     - MONITOR_POLL_INTERVAL: 監視ループの間隔（秒、デフォルト: 60）
     - PID_FILE_PATH / KILL_FLAG_PATH / その他閾値等（Settings クラス参照）

4. データディレクトリ
   - スクリプトは data/ 配下のファイル（.db, .pid, stop_requested.flag, kill.flag）を参照/作成します。必要に応じて作成してください。多くの操作は自動作成しますが、権限やパスに注意してください。

使い方
-----
実行方法の例（プロジェクトルートで実行することを想定）

- 監視ループ（Monitoring）
  - デフォルトでは本番 sqlite_path を使用して監視テーブルを初期化し、ポーリングを開始します。
  - 実行:
    KABUSYS_ENV=development python -m kabusys.run_monitoring
  - ポーリング間隔を環境変数で上書き:
    MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - 停止: プロジェクトルート/data/stop_requested.flag を作成すると監視ループが終了します（run_monitoring/run_execution 両方で参照）。

- 実行エンジン（ExecutionEngine）
  - live / paper_trading を切り替えて実行します。paper_trading の場合は MockBrokerClient を用い、DB は paper_trading 用を使用します。
  - 実行:
    KABUSYS_ENV=live python -m kabusys.run_execution
    KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  - 停止: data/stop_requested.flag を作成すると起動中エンジンに停止信号が送られます。
  - KillSwitch（条件が満たされると data/kill.flag を作成）により ExecutionEngine に停止指示を送る設計です。

- Streamlit ダッシュボード
  - 監視 DB を read-only で参照するダッシュボード。
  - 実行:
    streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

- Paper Trading 検証レポート
  - Paper Trading DB（デフォルト data/paper_trading.db）から指標を計算して出力します。
  - 実行例:
    python -m kabusys.tools.paper_verification_report
    python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
    python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db

- AI 関連
  - ニュースセンチメント / レジーム判定は OpenAI API キーが必要です（OPENAI_API_KEY）。
  - 関数はライブラリ API としても呼べます（kabusys.ai.score_news, kabusys.ai.regime_detector.score_regime）。

停止フラグと挙動
- data/stop_requested.flag
  - run_monitoring.py と run_execution.py が監視しているフラグファイル。存在するとそれぞれのループを終了します（手動停止用）。
- data/kill.flag
  - KillSwitch が条件を満たした際に作成され、ExecutionEngine に停止を促すために使用されます（理由メッセージをファイルに書く）。

設定（Settings）について
- src/kabusys/config.py に Settings クラスがあり、すべての主要設定はここから取得します。主なプロパティ:
  - env / is_live / is_paper / is_dev
  - sqlite_path / paper_sqlite_path / duckdb_path
  - pid_file_path / kill_flag_path / kill_flag_clear_on_start
  - CPU/MEM/DISK 監視閾値
  - PAPER_FILL_MODE（instant|partial|never|reject）

ディレクトリ構成
----------------
以下は主要なソースファイルのツリー（抜粋）です。実際には src/kabusys 以下にモジュールが配置されています。

- src/
  - kabusys/
    - __init__.py
    - config.py
    - run_monitoring.py
    - run_execution.py
    - tools/
      - __init__.py
      - paper_verification_report.py
    - utils/
      - __init__.py
      - process_priority.py
    - monitoring/
      - __init__.py
      - monitoring_db.py
      - monitoring_engine.py
      - system_monitor.py
      - trade_monitor.py
      - risk_monitor.py
      - kill_switch.py
      - alert_manager.py
      - streamlit_dashboard.py
    - execution/
      - (order_manager.py, reconciler.py, order_repository.py, execution_engine.py 等)
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
      - __init__.py
      - news_nlp.py
      - regime_detector.py
    - data/  （実行時に使用されるディレクトリ、DB/フラグ/PID を格納）

注意事項・運用上のポイント
-----------------------
- .env の自動読み込みはプロジェクトルートの検出（.git または pyproject.toml）を起点に行います。テストなど自動ロードを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- Paper Trading では本番 DB と完全分離する設計です。KABUSYS_ENV=paper_trading を適切に利用してください。
- LLM（OpenAI）連携は API の失敗や制限を考慮してリトライやフォールバック（0.0 等）を行う実装になっていますが、API キーやクォータの管理には注意してください。
- process priority / CPU affinity の設定はプラットフォーム差分（Windows / POSIX）を吸収しますが、権限の都合で設定できないケースがあるため失敗時は warning を出して続行します。
- DB マイグレーションは init_monitoring_db が一部を自動で行います（カラム追加等）。ただし複雑なスキーマ変更は手動での対応が必要になる場合があります。

貢献・拡張
----------
- 研究用ファクターやポートフォリオ構築ロジックは純粋関数群で実装されているため、単体テストや差し替えが容易です。
- ブローカーインターフェースを追加するには execution/broker_api / broker_factory を拡張してください。
- LINE 通知や他の通知チャネル（Slack 等）を追加する場合は alert_manager を拡張してください。

ライセンス・作者
----------------
本リポジトリのライセンス情報・作者情報は別途プロジェクトルートの LICENSE / pyproject.toml 等を参照してください。

以上が本コードベースの概要と基本的な使い方です。README に記載がない実行フローや詳細な API 仕様についてはソース内の docstring を参照してください。必要なら README に追加したい項目（環境変数の完全一覧、実行例スクリプト、依存関係ファイルなど）を教えてください。