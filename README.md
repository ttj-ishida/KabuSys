KabuSys — 日本株自動売買システム（README）
======================================

概要
----
KabuSys は日本株の自動売買・研究・監視を行うための小規模なコードベースです。本リポジトリには以下の主要機能を含みます:

- 注文発行・状態管理を行う ExecutionEngine（実運用 / Paper Trading 切替対応）
- システム・注文・リスク監視（ログ保存、kill flag 発報、LINE 通知）
- ポートフォリオ構築（候補選定・重み付け・株数計算・セクター制限 等）
- 研究用モジュール（ファクター計算、将来リターン、IC 計算、統計サマリ）
- AI を使ったニュースセンチメント評価（OpenAI）とレジーム判定
- Paper Trading 検証レポート生成ツール
- Streamlit ベースの監視ダッシュボード

主な特徴
--------
- 本番／paper_trading（モックブローカー + 別 DB）を環境変数で切替可能
- DuckDB（時系列データ分析）と SQLite（監視・発注ログ）を併用
- OpenAI（gpt-4o-mini）を用いたニュース NLP／マクロセンチメント（オプション）
- 監視ループはファイルベースの停止フラグ（data/stop_requested.flag）で安全停止
- LINE Push を用いたアラート（AlertManager）と kill.flag による Execution 停止

前提・依存
----------
- Python 3.10 以上（PEP 604 の型記法 (X | Y) を使用）
- 必要な主なライブラリ:
  - duckdb
  - psutil
  - requests
  - openai（AI 機能を使う場合）
  - streamlit（ダッシュボードを使う場合）
- 事前に環境変数を設定するか .env / .env.local を作成（自動ロード機能あり。無効化可）

セットアップ手順
----------------
1. リポジトリをクローンしてプロジェクトルートへ移動します。
2. 仮想環境を作成・有効化（推奨）。
   - python -m venv .venv
   - Unix/macOS: source .venv/bin/activate
   - Windows PowerShell: .venv\Scripts\Activate.ps1
3. 必要パッケージをインストール（例）:
   - pip install duckdb psutil requests openai streamlit
   - ※ 実際はプロジェクト用 requirements.txt があればそれを使ってください。
4. 開発用にパッケージを editable インストールすると python -m で実行しやすい:
   - pip install -e .
   （上記ができない場合は PYTHONPATH=src を指定して python -m を実行してください）
5. 環境変数の設定:
   - .env もしくは .env.local をプロジェクトルートに置くと自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化）。
   - 必須: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD
   - OpenAI を使う場合: OPENAI_API_KEY を設定
   - 主要な環境変数（代表例）は下記を参照してください。

重要な環境変数（代表）
--------------------
- KABUSYS_ENV: 起動環境。development / paper_trading / live（デフォルト: development）
  - paper_trading の場合、MockBroker を使い DB を data/paper_trading.db に書きます
- JQUANTS_REFRESH_TOKEN: J-Quants API 用トークン（必須）
- KABU_API_PASSWORD: kabu ステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（ai 機能を使う場合必須）
- PAPER_FILL_MODE: paper_trading の約定モード（instant|partial|never|reject、デフォルト instant）
- PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite パス（デフォルト data/paper_trading.db）
- DUCKDB_PATH: DuckDB ファイル（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
- PID_FILE_PATH: ExecutionEngine の PID ファイル（デフォルト data/execution.pid）
- KILL_FLAG_PATH: kill.flag のパス（デフォルト data/kill.flag）
- MONITOR_POLL_INTERVAL: 監視ループ間隔（秒、デフォルト 60）
- LOG_LEVEL: ログレベル（DEBUG/INFO/…、デフォルト INFO）

使い方（起動例）
----------------

前提: プロジェクトルートで実行、または pip install -e . 後に実行することを想定します。
PYTHONPATH=src を使う例も記載します。

- ExecutionEngine（発注エンジン）起動
  - プロダクション的実行: python -m kabusys.run_execution
  - 開発・未インストール時: PYTHONPATH=src python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading を指定すると MockBroker を使い data/paper_trading.db に記録されます。
  - 起動時、data/stop_requested.flag が既に存在すると起動せず終了します。
  - 実行中は data/execution.pid に PID が書かれ、停止フラグで安全停止します。

- Monitoring（システム監視）起動
  - python -m kabusys.run_monitoring
  - 起動時にプロセス優先度を「high」に試みて設定します。
  - MONITOR_POLL_INTERVAL=30 などでポーリング間隔を上書き可能。
  - 監視は常に本番の sqlite_path を使って監視ログ（system_status / trade_logs / risk_logs / positions / dashboard）を永続化します。
  - 監視ループの停止はプロジェクトルート/data/stop_requested.flag を作成することで行えます。

- Streamlit 監視ダッシュボード
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - データベースを読み取り専用で開いてダッシュボード表示を行います。

- Paper Trading 検証レポート（ツール）
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db オプションで DB パスを指定可能（環境変数 PAPER_TRADING_SQLITE_PATH も優先度あり）

- AI 関連
  - ニュース NLP スコアリング: kabusys.ai.score_news(conn, target_date, api_key=None)
  - レジーム判定: kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - これらは OpenAI API キーが必要です。API 呼び出しはリトライやフェイルセーフを備えています。

監視・停止関連
---------------
- stop_requested.flag（data/stop_requested.flag）
  - run_monitoring.py / run_execution.py のループ停止に使用。
- kill.flag（設定パスは Settings.kill_flag_path、デフォルト data/kill.flag）
  - KillSwitch が書き込み、ExecutionEngine に停止シグナルを送る用途に使います（Execution 側で検出して停止）。

設定読み込み
-----------
- .env / .env.local がプロジェクトルートにある場合、自動で読み込まれます（OS 環境変数が優先）。
- 自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- .env のパースでは export KEY=val、引用符、行内コメント等に対応しています。

ディレクトリ構成（抜粋）
----------------------
以下は src/kabusys 配下の主要ファイルと役割の一覧です（抜粋）。

- src/kabusys/
  - __init__.py                — パッケージ初期化、バージョン定義
  - config.py                  — 環境変数／設定管理（Settings クラス）
  - run_execution.py           — ExecutionEngine 起動スクリプト
  - run_monitoring.py          — SystemMonitor 起動スクリプト

- src/kabusys/execution/
  - order_manager.py
  - order_repository.py
  - execution_engine.py
  - reconciler.py
  - broker_factory.py
  - ...                       — 発注／リコンシリエーション関連

- src/kabusys/monitoring/
  - monitoring_db.py           — SQLite テーブル作成・永続化 API
  - system_monitor.py
  - trade_monitor.py
  - risk_monitor.py
  - kill_switch.py
  - alert_manager.py
  - monitoring_engine.py
  - streamlit_dashboard.py

- src/kabusys/portfolio/
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py

- src/kabusys/research/
  - factor_research.py
  - feature_exploration.py

- src/kabusys/ai/
  - news_nlp.py                — ニュース NLP スコアリング（OpenAI）
  - regime_detector.py         — レジーム判定（MA + マクロセンチメント）

- src/kabusys/tools/
  - paper_verification_report.py — Paper Trading 検証レポート出力ツール

データファイル（デフォルト）
---------------------------
- data/monitoring.db          — 監視ログ SQLite（Settings.sqlite_path のデフォルト）
- data/paper_trading.db       — Paper Trading 用 SQLite（paper_trading 環境時）
- data/kabusys.duckdb         — DuckDB（時系列・調査データ）
- data/execution.pid          — ExecutionEngine の PID（Settings.pid_file_path）
- data/kill.flag              — KillSwitch が書き込む停止フラグ（Settings.kill_flag_path）
- data/stop_requested.flag    — 手動で作って run_* ループを停止させるためのフラグ

運用上の注意
------------
- Paper Trading モードは本番 DB と完全分離されるので挙動確認に利用してください。
- OpenAI 呼び出しは API 利用料が発生します。api_key を安全に管理してください。
- process priority / CPU affinity の設定は OS に依存し、権限不足時は警告を出してスキップされます。
- monitoring_db.init_monitoring_db() は冪等でマイグレーション処理（列追加）も行いますが、運用環境でのバックアップは推奨します。
- kill.flag の書き込みは冪等です。存在すると ExecutionEngine に対する停止要求になります。

よくあるコマンドまとめ
--------------------
- 開発環境でモジュールをそのまま実行する
  - PYTHONPATH=src python -m kabusys.run_execution
  - PYTHONPATH=src python -m kabusys.run_monitoring

- インストールして実行する
  - pip install -e .
  - python -m kabusys.run_execution
  - python -m kabusys.run_monitoring

- Paper Trading レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

- Streamlit ダッシュボード
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

サポート・拡張ポイント
--------------------
- broker adapter を追加して別ブローカーとの接続を実装できます（execution/broker_factory.py を参照）。
- position sizing の lot_size を銘柄別に拡張する、手数料推定ロジックを強化する等が想定されます。
- AI モジュールは API 呼び出しの抽象化やキャッシュ化で運用コストを抑えられます。

ライセンス
----------
（ここにライセンス情報を記載してください。例: MIT / Proprietary）

最後に
------
この README はリポジトリ内のソースコード（主要モジュール）をもとに作成しています。実際の導入・運用前には環境変数や DB パスの確認、バックアップ、テスト環境での十分な検証を行ってください。必要があれば README をプロジェクトに合わせて追記・修正してください。