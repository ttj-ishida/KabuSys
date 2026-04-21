README
=====

概要
----
KabuSys は日本株向けの自動売買 / リサーチ / モニタリング基盤のミニマル実装です。本リポジトリは以下の主要機能を含みます。

- 発注エンジン（ExecutionEngine） — ブローカークライアント経由で発注を実行。paper_trading モードでの完全分離をサポート。
- 監視（Monitoring） — システム状態・注文状態・リスク（ドローダウン・ポジション上限等）を定期ポーリングしてログ・アラート・Kill Switch を管理。
- ポートフォリオ構築ユーティリティ — 候補選定、重み付け、ポジションサイジング、セクターキャップ等の純粋関数群。
- リサーチ（Research） — DuckDB 上の市場データを用いたファクター計算・統計解析。
- AI モジュール（OpenAI） — ニュースの NLP スコアリング、マクロセンチメントに基づくレジーム判定（OpenAI API 使用、任意）。
- 運用ユーティリティ — .env ウィザード、設定検証、Paper Trading 検証レポートなど。

主な設計方針
- 実行スクリプトと監視はプロセス優先度設定・ログ統一化済み。
- Paper Trading（KABUSYS_ENV=paper_trading）は発注データを専用 SQLite に分離。
- DuckDB を分析用 DB、SQLite を監視・発注履歴 DB として併用。
- OpenAI 呼び出しはリトライやレスポンス検証を行い、API エラーでも安全に継続する設計。

機能一覧
---------
- run_execution: ExecutionEngine を起動（実環境 / paper_trading 切替）。
- run_monitoring: SystemMonitor のポーリングループ起動（MONITOR_POLL_INTERVAL で間隔指定可）。
- config_setup: 対話式 .env 生成ウィザード。
- validate_config: .env と config/*.yaml の起動前検証 CLI。
- tools.paper_verification_report: Paper Trading の検証レポート生成（稼働率・成功率・レイテンシ等）。
- portfolio: 候補選定 / 重み計算 / ポジションサイジング / リスク調整の純粋関数群。
- research: ファクター計算（モメンタム・ボラティリティ・バリュー）・IC 計算等。
- ai: news_nlp（ニュースのセンチメントスコア取得） / regime_detector（市場レジーム判定）。
- monitoring: DB スキーマ作成・ログ永続化、System/Trade/Risk モニタ、KillSwitch、MonitoringEngine。
- utils: ロギングセットアップ、プロセス優先度 / CPU affinity ユーティリティ。

セットアップ手順
----------------

1. Python 環境
   - Python 3.9+ を推奨（コードは型注釈に 3.9+ の機能を使っています）。
   - 仮想環境を作成して有効化してください。
     - 例: python -m venv .venv && source .venv/bin/activate

2. 依存ライブラリのインストール（例）
   - 必要な主要パッケージ:
     - duckdb
     - psutil
     - openai (AI 機能を使う場合)
     - PyYAML（config YAML の詳細検証を行う場合）
   - 例:
     - pip install duckdb psutil openai PyYAML
   - ※ requirements.txt が無い場合は上記を手動インストールしてください。

3. プロジェクトルートの準備
   - data/ と logs/ ディレクトリを作成（logging_setup が自動作成を試みますが、手動で作ると権限問題を避けられます）。
     - mkdir -p data logs

4. 環境変数の設定
   - 必須:
     - JQUANTS_REFRESH_TOKEN — J-Quants API のリフレッシュトークン
     - KABU_API_PASSWORD — kabuステーション API パスワード
   - 推奨 / 任意:
     - KABUSYS_ENV — 実行環境 (development | paper_trading | live)。デフォルトは development。
     - DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
     - SQLITE_PATH — 監視 SQLite（デフォルト data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH — paper_trading 用 SQLite（デフォルト data/paper_trading.db）
     - OPENAI_API_KEY — OpenAI API キー（ai モジュール使用時）
     - LOG_LEVEL — ログレベル（DEBUG/INFO/…）
     - MONITOR_POLL_INTERVAL — 監視ポーリング間隔（秒、run_monitoring 用）
   - .env の自動生成:
     - python -m kabusys.config_setup を実行して .env を作成できます（対話式）。

5. 設定検証（起動前チェック）
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱い（exit code 1）になります。

使い方
------

主要スクリプトの起動例（プロジェクトルートで実行）:

- ExecutionEngine を起動（実行 / ペーパートレードは KABUSYS_ENV に依存）
  - python -m kabusys.run_execution
  - Paper Trading モード:
    - export KABUSYS_ENV=paper_trading
    - python -m kabusys.run_execution
    - paper_trading の場合は PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に発注ログ等を保存します（本番 DB と分離）。

- Monitoring を起動
  - python -m kabusys.run_monitoring
  - ポーリング間隔を変更する:
    - export MONITOR_POLL_INTERVAL=30  # 30秒に変更
  - 監視は Settings.sqlite_path（SQLITE_PATH）の DB を使用します（監視は常に本番 sqlite_path を参照します）。

- .env ウィザード（対話式）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db で別の DB を指定できます（環境変数 PAPER_TRADING_SQLITE_PATH より優先）。

- AI モジュール（プログラム内 API 呼び出し）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - OpenAI を使う場合は OPENAI_API_KEY を環境変数で設定するか api_key を渡してください。

停止 / Kill Switch
- run_monitoring / run_execution の停止方法:
  - グレースフル停止: data/stop_requested.flag を作成すると run_monitoring と run_execution は次のポーリングで検知して終了します。
    - touch data/stop_requested.flag
  - Kill Switch（監視が検知すると data/kill.flag を書き込み、Execution を停止させる）:
    - Kill 条件は RiskMonitor などが生成し、KillSwitch が data/kill.flag を作成します。
    - 手動クリア: rm data/kill.flag
  - Execution の PID ファイル:
    - 実行中は data/execution.pid に PID を書き込みます（run_execution 側の挙動）。

ログ
----
- ログは標準出力に出力され、デフォルトで logs/<app_name>.log に日次ローテーションで保存されます（logs ディレクトリに書き込み権限が必要）。
- ログレベルは環境変数 LOG_LEVEL または setup_logging の引数で制御できます。

ディレクトリ構成
----------------

（src/kabusys 以下の主要ファイルと役割）

- kabusys/
  - __init__.py
  - config.py
    - 環境変数の読み込み・Settings クラス。自動で .env（.env.local）をプロジェクトルートから読み込む仕組み。
  - config_setup.py
    - .env 対話式ウィザード。python -m kabusys.config_setup で起動。
  - validate_config.py
    - 起動前の設定検証 CLI。
  - run_execution.py
    - ExecutionEngine 起動スクリプト（KABUSYS_ENV=paper_trading の扱いあり）。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト。MONITOR_POLL_INTERVAL 環境変数で間隔を制御。
  - utils/
    - logging_setup.py — 共通ロギング設定（Stream + 日次ローテートファイル）。
    - process_priority.py — プロセス優先度 / CPU affinity 設定（Windows / POSIX を吸収）。
  - monitoring/
    - monitoring_db.py — SQLite スキーマ初期化 / 永続化ラッパー（MonitoringDB）。
    - system_monitor.py — システム状態・データ鮮度チェック。
    - trade_monitor.py — （注文滞留・約定異常等の検知ロジック）。
    - risk_monitor.py — ドローダウン / ポジション上限監視。
    - kill_switch.py — data/kill.flag による Execution 停止シグナル管理。
    - monitoring_engine.py — 各 Monitor を束ねるポーリング Engine。
    - alert_manager.py — （LINE などの通知マネージャ、アラート送信を一元化する想定のモジュール）。
  - execution/
    - execution_engine.py — ExecutionEngine 本体（発注セッションの主要ロジック）。
    - broker_factory.py — ブローカークライアント生成（実ブローカー or Mock）。
    - order_manager.py, order_repository.py, reconciler.py, risk_manager.py — 発注 / 注文永続化 / リスク制御等。
  - portfolio/
    - portfolio_builder.py, position_sizing.py, risk_adjustment.py — 候補選定・重量配分・ポジション決定・リスク調整。
  - research/
    - factor_research.py — モメンタム / ボラティリティ / バリュー等の計算（DuckDB を利用）。
    - feature_exploration.py — 将来リターン計算・IC・統計サマリ。
  - ai/
    - news_nlp.py — ニュースを OpenAI に送り銘柄別スコアを生成して ai_scores に保存。
    - regime_detector.py — ETF の ma200 とマクロ記事の LLM センチメントを合成して市場レジーム判定。
  - tools/
    - paper_verification_report.py — Paper Trading の検証レポート生成 CLI。

注意点 / 運用上のポイント
------------------------
- Paper Trading は本番データベースと完全に分離されるよう設計されています（settings.is_paper による分岐）。
- 監視（monitoring）は環境にかかわらず Settings.sqlite_path（本番の monitoring DB）を使用します。監視ログは通常の監視 DB に残ります。
- OpenAI を用いる機能は API キーを必要とし、API のエラー時はフェイルセーフ（0 にフォールバック、部分失敗時も既存データを保護）するよう設計されています。
- DB 初期化: init_monitoring_db() により必要なテーブルとマイグレーション（カラム追加）を冪等に作成します。
- ログ保存先のディレクトリ権限に注意してください。ファイルハンドラ作成に失敗するとコンソールログのみになります。

よくある操作例（まとめ）
-----------------------
- .env を作成（対話式）
  - python -m kabusys.config_setup
- 設定検証
  - python -m kabusys.validate_config
- Execution 起動（開発モード）
  - export KABUSYS_ENV=development
  - python -m kabusys.run_execution
- Monitoring 起動（ポーリング間隔 60 秒）
  - python -m kabusys.run_monitoring
- 停止（即時ではなく次回ポーリングで安全停止）
  - touch data/stop_requested.flag
- Kill Switch を手動で書く（運用上は監視が書くが手動も可能）
  - echo "reason" > data/kill.flag
  - 実行中の Execution は kill.flag を検知すると停止します。

ライセンス / 貢献
-----------------
- 本リポジトリのライセンス情報や貢献手順はプロジェクトルートの LICENSE / CONTRIBUTING を参照してください（存在しない場合は事前にプロジェクトオーナーに確認してください）。

補足
----
- 実運用前に必ず validate_config でチェックし、KABUSYS_ENV=live の場合は特に LINE 通知設定・Kill Switch の設定値を確認してください。
- 本 README はコードベースのソースから抜粋した設計意図・使い方を記載しています。実際の挙動や追加の設定ファイル（config/*.yaml）が存在する場合はそちらも参照してください。

必要であれば、README に含めるサンプル .env の雛形や systemd / supervisor 用のサービス定義テンプレート、さらに詳細なコマンド例（Docker/Compose での起動例など）も作成します。希望があれば教えてください。