README
=====

概要
----
KabuSys は日本株の自動売買・リサーチ用ライブラリ兼実行基盤です。本リポジトリには以下の主要機能が実装されています。

- 実行エンジン起動スクリプト（run_execution）
- 監視（Monitoring）コンポーネント（run_monitoring / MonitoringEngine）
- ポートフォリオ構築（候補選定・重み付け・ポジションサイズ計算）
- リサーチ（ファクター計算・特徴量探索）
- AI を使ったニュース NLP / レジーム判定（OpenAI 経由）
- Paper Trading 用の検証レポート等のユーティリティ

この README はコードベースにある主要モジュールを参照して、導入・起動方法やディレクトリ構成をまとめたものです。

主な機能
--------
- run_execution: 実際の ExecutionEngine を起動するスクリプト。KABUSYS_ENV=paper_trading の場合は MockBroker を使用して data/paper_trading.db に記録（本番 DB と分離）。
- run_monitoring: SystemMonitor のポーリングループを起動。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更可能（デフォルト 60 秒）。監視データは sqlite（monitoring.db）へ保存。
- monitoring モジュール群: SystemMonitor / TradeMonitor / RiskMonitor / KillSwitch / MonitoringEngine / MonitoringDB による監視・アラート・Kill Switch ロジック。
- portfolio モジュール: 候補選定（select_candidates）、配分計算（等金額・スコア重み）、ポジションサイズ計算（risk_based 等）、セクター上限の適用、レジーム乗数。
- research モジュール: ファクター計算（momentum/value/volatility）、将来リターン、IC 計算、統計サマリ。
- ai モジュール: news_nlp（ニュース記事を LLM でセンチメント評価して ai_scores に保存）、regime_detector（ETF／マクロ情報を LLM と合成して日次レジーム判定）。
- utils: ログ設定（TimedRotatingFileHandler を含む標準化されたロギング）、プロセス優先度 / CPU affinity 設定ユーティリティ。
- 設定支援ツール: config_setup（対話的 .env 作成ウィザード）、validate_config（起動前チェック）。
- tools: paper_verification_report（Paper Trading 検証レポート生成）

セットアップ手順
---------------
前提
- Python 3.10 以上（コード内で型ヒントに | を使用しているため）
- SQLite (標準で Python に同梱)
- 任意の DuckDB バイナリは Python パッケージ duckdb で使用

1. リポジトリをクローン
   git clone <repo_url>
   cd <repo_root>

2. 仮想環境を作成して有効化（任意だが推奨）
   python -m venv .venv
   source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージのインストール
   pip install duckdb psutil openai
   - PyYAML は validate_config の YAML 検証を有効化する場合に必要:
     pip install pyyaml
   - 他、運用環境に応じて追加の依存（例えば broker client ライブラリ等）が必要になる場合があります。

4. 環境変数設定（.env）
   - 対話形式で作成する:
     python -m kabusys.config_setup
     -> .env を生成します（.env は決して Git にコミットしないこと）

   - 手動で作る場合は .env.example を参考にして .env を作成してください。

5. 設定検証（任意）
   python -m kabusys.validate_config
   --strict を付けると警告も失敗扱いになります:
   python -m kabusys.validate_config --strict

主要な環境変数（抜粋）
--------------------
- JQUANTS_REFRESH_TOKEN (必須): J-Quants API 用リフレッシュトークン
- KABU_API_PASSWORD (必須): kabuステーション API パスワード
- KABUSYS_ENV (デフォルト: development): 実行環境。development / paper_trading / live
- PAPER_TRADING_SQLITE_PATH (デフォルト: data/paper_trading.db): Paper Trading 用 SQLite
- SQLITE_PATH (デフォルト: data/monitoring.db): 監視 DB
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb): DuckDB ファイル
- LOG_LEVEL (デフォルト: INFO): ログレベル
- OPENAI_API_KEY: OpenAI API を利用する AI 機能で必須
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒）
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1: 自動 .env ロードを無効化（テスト時等）

使い方
------
起動スクリプト

- 監視ループを起動（SystemMonitor）
  python -m kabusys.run_monitoring

  オプション / 挙動:
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を変更可能。0 以下や不正値はデフォルト 60 秒にフォールバックします。
  - run_monitoring はプロセス優先度を "high" に設定します（実行権限が必要な場合があります）。
  - 本スクリプトは KABUSYS_ENV に関わらず本番 sqlite_path を使用して監視データを記録します。
  - 停止方法: プロジェクトルート/data/stop_requested.flag を作成するとループは検知して終了します（通常はオペレーショナルな停止フラグ）。

- 実行エンジンを起動（ExecutionEngine）
  python -m kabusys.run_execution

  挙動:
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、Paper Trading 専用 DB (PAPER_TRADING_SQLITE_PATH, デフォルト data/paper_trading.db) に記録され、本番 DB と完全に分離されます。
  - run_execution もプロセス優先度を "high" に設定します。
  - 起動時に data/stop_requested.flag が既に存在する場合は起動せずに終了します（安全措置）。
  - 実行中は data/execution.pid に PID を書きます。停止は stop_requested.flag を作るか、Kill Switch が data/kill.flag を書き込むことで Engine に停止シグナルを与えます。

- Kill Switch
  monitoring.kill_switch モジュールはリスク条件（ドローダウンやポジション上限）を満たすと data/kill.flag を書き込みます。ExecutionEngine はこのフラグを参照して安全停止を行います。

AI 機能
- AI 機能（kabusys.ai.news_nlp, kabusys.ai.regime_detector）は OpenAI API を使用します。
- OPENAI_API_KEY を環境変数に設定するか、関数呼び出し時に api_key を渡してください。
- API 呼び出しはリトライやフェイルセーフの処理が入っていますが、API キー未設定時は例外になります。

ツール
- Paper Trading 検証レポート
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  --db オプションで DB パスを指定できます。デフォルトは env または data/paper_trading.db。

ログ
---
- ログ設定は kabusys.utils.logging_setup.setup_logging で統一的に行われます。
- デフォルトは logs/ ディレクトリ配下にアプリ別ログ（例: logs/execution.log, logs/monitoring.log）を日次ローテーション（30日分保持）で出力します。
- LOG_DIR 環境変数でログ保存先を変更できます。
- 既にハンドラが設定されている場合は再設定時にクリアして二重出力を防止します。

停止 / フラグ管理
----------------
- stop_requested.flag: run_monitoring / run_execution が監視する「停止要求」フラグ（存在するとプロセスを停止）。場所: <project_root>/data/stop_requested.flag
- kill.flag: KillSwitch が書き込むフラグ（ExecutionEngine に停止を促す目的）。存在すると ExecutionEngine 側で停止動作が行われます。
- execution.pid: run_execution が書き出す PID ファイル（場所は Settings.pid_file_path で指定可能）

ディレクトリ構成（抜粋）
---------------------
以下は主要ファイルを抜粋した構成例（src/kabusys 以下）:

- src/kabusys/
  - __init__.py
  - config.py                # 設定管理（.env 自動ロード / Settings クラス）
  - config_setup.py          # .env 作成ウィザード（対話式）
  - validate_config.py       # 起動前の設定検証 CLI
  - run_monitoring.py        # SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py         # ExecutionEngine 起動スクリプト
  - tools/
    - paper_verification_report.py
  - ai/
    - news_nlp.py
    - regime_detector.py
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py        # (trade_monitor 実装あり)
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py        # (アラート送信ロジック)
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py
  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py
  - utils/
    - logging_setup.py
    - process_priority.py
    - __init__.py
  - execution/                # Execution に関する実装（order_manager など）
  - data/                     # デフォルト DB / フラグファイル置き場（git 管理除外推奨）

注意事項 / 運用上のヒント
-----------------------
- .env は決してリポジトリにコミットしないでください（API キーやパスワード等が含まれます）。
- KABUSYS_ENV を "live" にする前に必ず validate_config を実行して全設定を確認してください。validate_config は本番向けの追加警告を出します。
- AI 機能を有効にする場合は OpenAI の利用料金に注意してください。テスト時はモック（関数をモンキーパッチ）して呼び出しを回避できます。
- run_monitoring / run_execution は起動時にプロセス優先度を "high" に設定します。必要に応じて権限や OS の設定を確認してください。
- Paper Trading と Live の DB は分離されています（paper_trading は PAPER_TRADING_SQLITE_PATH を使用）。

追加情報 / 開発者向け
---------------------
- 開発時に .env 自動読み込みを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- validate_config は PyYAML がインストールされている場合に config/*.yaml のパース検証も行います（未インストール時は警告）。
- DuckDB の接続は各モジュールに直接渡して SQL を発行する設計です。Data pipeline / prices_daily / raw_financials テーブルに依存しています。

問い合わせ / コントリビュート
----------------------------
バグ、改善提案、機能追加の PR は歓迎します。コードベースのスタイルに合わせてテストとドキュメントを付けてください。

以上がこのコードベースの概要・セットアップ・使い方となります。必要であれば .env のサンプルや起動時のトラブルシュート（ログ確認方法、PermissionError 対処など）を追記します。どの情報を詳しく追加しますか？