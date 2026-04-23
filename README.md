README.md（日本語）
=================

概要
----
KabuSys は日本株向けの自動売買システム向けライブラリ／ランタイム群です。本リポジトリには以下を含みます。
- ExecutionEngine（約定・発注・リスク管理）
- Monitoring（システム状態・注文状態・リスク監視、Kill Switch）
- Portfolio構築・ポジションサイズ計算等の純粋関数群（バックテスト／生成ロジック）
- Research（ファクター計算、特徴量探索）
- AI連携（OpenAI を用いたニュースセンチメント・レジーム判定）
- 運用支援ツール（.env 設定ウィザード、設定検証、Paper Trading 検証レポート等）

主な機能
--------
- Execution
  - 本番（live）／ペーパートレード（paper_trading）切替対応
  - ブローカー抽象化（実ブローカー / MockBroker 切替）
  - リスク管理（最大ポジション率、資金利用率、回路遮断等）
- Monitoring
  - CPU／メモリ／ディスク／プロセス稼働監視の定期ポーリング
  - 注文ログ、ポジション、リスクログの永続化（SQLite）
  - Kill Switch（条件に応じて data/kill.flag を書き込み ExecutionEngine を安全に停止）
  - アラート送信（LINE トークン設定で通知可能）
- Research / Portfolio
  - DuckDB を使ったファクター計算（Momentum / Volatility / Value 等）
  - ポートフォリオ候補選定、重み付け、ポジションサイズ決定、セクター制限、レジーム乗数
- AI (OpenAI)
  - ニュースを LLM でスコア化（news_nlp）
  - マクロニュースと ETF MA を用いた市場レジーム判定（regime_detector）
- 運用ツール
  - .env 対話式ウィザード（config_setup）
  - 設定検証 CLI（validate_config）
  - Paper Trading 向け検証レポート生成（tools.paper_verification_report）

前提・依存
----------
- Python 3.10+
- 必須ライブラリ（少なくとも実行に必要なもの）
  - duckdb
  - psutil
  - openai
- 開発時に便利なライブラリ
  - PyYAML（config/*.yaml の検証に使用。未インストールでも動作はするが検証がスキップされます）

インストール例
---------------
（仮に仮想環境を作成済みとする）

1) 依存ライブラリをインストール（requirements.txt がある場合はそれを利用）
   - 例:
     pip install duckdb psutil openai pyyaml

2) （任意）プロジェクトルートに logs/ と data/ を作る（ログや DB のデフォルト保存先）
   mkdir -p logs data

セットアップ手順
--------------
1. .env の作成（対話式ウィザード）
   - 実行:
     python -m kabusys.config_setup
   - これにより .env（デフォルト）を作成／更新できます。J-Quants や kabu API の鍵などを入力してください。

2. 設定検証
   - 実行:
     python -m kabusys.validate_config
   - 問題があれば警告／エラーが出力されます。--strict を付けると警告も失敗扱いになります。

3. DB 初期化
   - 実行スクリプト（run_monitoring / run_execution）が内部で必要テーブルを作成します。事前に手動作成は不要です。

環境変数（重要）
----------------
- 必須（少なくとも実行前に設定が必要）
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- 実行環境切替
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
    - paper_trading のときは MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に記録
- DB パス
  - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB）
- ロギング
  - LOG_LEVEL（例: INFO / DEBUG）
  - LOG_DIR（デフォルト: logs/）
- OpenAI
  - OPENAI_API_KEY（AI 機能を使う場合に必須）
- Monitoring 周期
  - MONITOR_POLL_INTERVAL（秒、デフォルト: 60）
- Paper Trading
  - PAPER_FILL_MODE（instant | partial | never | reject、デフォルト: instant）
- Kill Switch 動作
  - KILL_FLAG_CLEAR_ON_START=1 にすると起動時に data/kill.flag を自動クリア（本番では 0 推奨）
- 自動 .env ロードの無効化
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1

使い方（主要コマンド）
--------------------

- 環境ウィザード（.env 作成）
  python -m kabusys.config_setup

- 設定検証
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict

- ExecutionEngine 起動（本番または paper_trading）
  python -m kabusys.run_execution
  - 補足:
    - KABUSYS_ENV=paper_trading を設定すると MockBrokerClient を使い、data/paper_trading.db に記録されます。
    - 起動中の停止: data/stop_requested.flag を作成すると実行スレッドが検知して停止します。
    - ExecutionEngine の pid ファイルはデフォルト data/execution.pid に作成されます。

- Monitoring 起動（ポーリングループ）
  python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可能（デフォルト 60）。
  - 停止: プロジェクトルート/data/stop_requested.flag を作るとループを終了します。
  - Monitoring は環境（KABUSYS_ENV）に関わらず本番 sqlite_path を使用して監視テーブルを保存します。

- Paper Trading 検証レポート（コマンドライン）
  python -m kabusys.tools.paper_verification_report --from YYYY-MM-DD --to YYYY-MM-DD
  - デフォルト DB: data/paper_trading.db（PAPER_TRADING_SQLITE_PATH または --db で指定可）

- AI 機能（プログラム内部 API）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - いずれも OPENAI_API_KEY を環境変数か引数で与える必要があります。

停止／Kill フロー
-----------------
- run_execution / ExecutionEngine 側停止リクエスト:
  - monitoring 側や管理オペレータが data/kill.flag を書く（KillSwitch を通じて作成）と ExecutionEngine 側で停止をトリガーできます。
  - run_* スクリプトを強制終了したい場合は data/stop_requested.flag を作成してください（両起動スクリプトでポーリングループを終了するために使用）。

ロギング
-------
- 標準的に stdout にログを出力し、logs/<app_name>.log に日次ローテーションで保存します（30 日保持）。
- app_name は run_monitoring/run_execution の起動時にそれぞれ "monitoring" / "execution" が使われます。
- ログレベルは LOG_LEVEL 環境変数、または setup_logging の引数で制御できます。

ディレクトリ構成（主要ファイル）
-----------------------------
（src/kabusys 以下の概観）

- kabusys/
  - __init__.py
  - config.py                     — 環境変数 / 設定読み込みロジック（.env 自動ロード含む）
  - config_setup.py               — .env 対話式ウィザード
  - validate_config.py            — 設定検証 CLI
  - run_execution.py              — ExecutionEngine 起動スクリプト
  - run_monitoring.py             — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート CLI
  - ai/
    - news_nlp.py                  — ニュースセンチメント（OpenAI 呼び出し、スコア書き込み）
    - regime_detector.py           — レジーム判定（MA + マクロセンチメント）
  - monitoring/
    - monitoring_db.py             — SQLite モデル（テーブル作成・CRUD）
    - system_monitor.py            — システム状態・データ鮮度監視
    - trade_monitor.py             — 注文関連監視（ファイル内にあり）
    - risk_monitor.py              — ドローダウン・ポジション上限監視
    - kill_switch.py               — kill.flag 管理
    - monitoring_engine.py         — 複数監視の統合エンジン
    - alert_manager.py             — （未掲示だが存在想定）アラート送信用抽象
  - execution/
    - execution_engine.py          — 実行エンジン（セッション管理等）
    - broker_factory.py            — ブローカークライアント生成
    - order_manager.py             — 注文管理
    - order_repository.py          — 永続化レイヤ（SQLite）
    - reconciler.py                — 照合ロジック
    - risk_manager.py              — 発注前リスクチェック
  - portfolio/
    - portfolio_builder.py         — 候補選定・重み計算
    - position_sizing.py           — 株数計算・スケール調整
    - risk_adjustment.py           — セクター上限・レジーム乗数
  - research/
    - factor_research.py           — ファクター計算（DuckDB）
    - feature_exploration.py       — 将来リターン・IC・統計
  - utils/
    - logging_setup.py             — ログ初期化ユーティリティ
    - process_priority.py          — プロセス優先度 / CPU affinity 設定
  - data/ (ランタイムで生成されることを想定）
    - monitoring.db / paper_trading.db / kill.flag / stop_requested.flag / execution.pid
  - config/ (テンプレート: system_config.yaml 等)

開発上の注意点 / 運用上の注意
----------------------------
- KABUSYS_ENV=live のときは十分な注意が必要です（validate_config は注意喚起を出します）。
- .env は機密情報を含むため絶対にバージョン管理にコミットしないでください。
- OpenAI を利用する機能は API コストとレイテンシを伴います。API キーは安全に管理してください。
- paper_trading モードは本番 DB と分離されます。実際の発注を行う前に paper_trading で十分検証してください。
- プロセス優先度設定（set_process_priority）は OS 権限に依存します。権限不足時は警告が出ますが処理は続行します。

サンプル運用フロー
-----------------
1. .env を作成（python -m kabusys.config_setup）
2. 設定検証（python -m kabusys.validate_config）
3. データ用ディレクトリ作成（mkdir -p data logs）
4. 必要な DuckDB / SQLite の初期テーブルは起動スクリプトで自動生成されるため、まずは
   - 監視を開始: python -m kabusys.run_monitoring
   - 別ターミナルでエンジンを起動: python -m kabusys.run_execution
5. 停止する場合はプロジェクトルートの data/stop_requested.flag を作成（touch data/stop_requested.flag）

ライセンス・その他
------------------
- 本 README はコードから読み取れる仕様を基に作成しています。実際のライセンス情報や CONTRIBUTING、要件ファイル (requirements.txt) はリポジトリのルートにあるファイルを参照してください。

問題報告 / 貢献
----------------
- バグ・改善提案は issue を立ててください。開発に貢献する場合は PR をお願いします。

以上。必要であれば、README に含めるサンプル .env テンプレートや system_config.yaml の雛形を生成して追記します。希望があれば教えてください。