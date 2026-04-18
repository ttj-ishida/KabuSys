KabuSys
=======

日本株向け自動売買フレームワーク（ライブラリ兼運用スクリプト群）。  
このリポジトリは取引実行エンジン、監視／アラート、ペーパートレード用ユーティリティ、ファクター計算／リサーチ、LLM を用いたニュース解析などのコンポーネントを含みます。

概要
----
KabuSys は以下の機能を持つモジュール群から構成される自動売買基盤です。

- 実行エンジン（ExecutionEngine）: ブローカークライアントを介した発注・注文管理・リスク管理
- 監視（Monitoring）: システム状態、注文ログ、リスク条件を定期ポーリングして記録・アラート
- ペーパートレード分離: KABUSYS_ENV=paper_trading 時は専用の SQLite に記録して本番 DB と分離
- 環境設定ユーティリティ: 対話式 .env 作成（config_setup）・設定検証（validate_config）
- リサーチ / ファクター計算: DuckDB を用いたファクター計算・特徴量探索
- AI モジュール: OpenAI（gpt-4o-mini 等）を用いたニュースセンチメント・レジーム判定
- ツール: Paper Trading の検証レポート生成スクリプト 等

主な機能一覧
--------------
- run_execution.py: ExecutionEngine を起動（プロセス優先度設定、DB 接続、BrokerFactory 経由でブローカー選択、デーモンスレッドで実行）
- run_monitoring.py: SystemMonitor のポーリングループを起動（MONITOR_POLL_INTERVAL で間隔指定可能）
- config_setup.py: 対話式に .env を作成・更新するウィザード
- validate_config.py: .env と config/*.yaml の簡易検証 CLI（--strict あり）
- monitoring: MonitoringDB（SQLite）/ SystemMonitor / TradeMonitor / RiskMonitor / KillSwitch / MonitoringEngine
- portfolio: 候補選定、重み計算、ポジションサイジング、セクター制限等の純粋関数群
- research: DuckDB 経由のファクター計算（momentum/volatility/value）・forward returns・IC 等
- ai: news_nlp（ニュースセンチメントを OpenAI で評価して ai_scores に保存）、regime_detector（市場レジーム判定）
- tools.paper_verification_report: ペーパートレード DB を解析して PASS/FAIL レポート作成

前提 / 必要要件
---------------
- Python 3.10 以上（Union 型注記等を使用）
- 必須ライブラリ（一部）:
  - duckdb
  - psutil
  - openai（AI 機能を使う場合）
- 開発 / 実行環境により追加パッケージ:
  - PyYAML（config/*.yaml の内容検証に使用。未インストール時は YAML 検証をスキップ）
- SQLite（組み込み）、標準ライブラリのモジュールを利用

インストール例（仮）
-------------------
仮に pip でインストールする場合の例:

  python -m venv .venv
  source .venv/bin/activate
  pip install --upgrade pip
  pip install duckdb psutil openai

（プロジェクトに requirements.txt がある場合は pip install -r requirements.txt を使用してください）

セットアップ手順
----------------
1. プロジェクトルートへ移動（README と同階層に data/ や logs/ が作成されます）。
2. 環境変数の準備:
   - 対話式ウィザードで .env を作成する:
       python -m kabusys.config_setup
   - もしくは .env.example を参考に .env を作成し必要な値を設定
3. 必須環境変数（例）:
   - JQUANTS_REFRESH_TOKEN（必須）
   - KABU_API_PASSWORD（必須）
   - KABUSYS_ENV（development / paper_trading / live、デフォルト: development）
   - OPENAI_API_KEY（AI 機能利用時）
   - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB を上書きする場合）
   - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH（監視 DB デフォルト: data/monitoring.db）
   - LOG_LEVEL（例: INFO）
4. 設定検証:
       python -m kabusys.validate_config
   - --strict を付けると警告も異常扱いになります
5. ディレクトリ作成:
   - data/ と logs/ は自動で作成される処理を含むモジュールがありますが、手動で用意しておくと権限問題を予防できます。

主な環境変数（重要なもの）
-------------------------
- KABUSYS_ENV: 実行環境（development / paper_trading / live）
  - paper_trading の場合、発注はモックブローカーに切り替え paper_trading 用 DB（PAPER_TRADING_SQLITE_PATH, デフォルト data/paper_trading.db）を使用
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）
- PAPER_FILL_MODE: paper_trading 時のモック約定挙動（instant / partial / never / reject）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（0=しない, 1=する）
- PID_FILE_PATH / KILL_FLAG_PATH: pid ファイル / kill flag のパス（Settings で参照）
- OPENAI_API_KEY: OpenAI API キー（ai モジュール使用時）
- LOG_LEVEL / LOG_DIR: ログ出力設定

基本的な使い方
--------------
- 実行エンジン（本番／ペーパー）を起動:
    python -m kabusys.run_execution
  - 起動直後に data/stop_requested.flag が存在する場合は起動せず終了します
  - ExecutionEngine は data/execution.pid を使用することがあります

- 監視プロセスを起動:
    python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（秒, デフォルト 60）
  - 監視は本番 sqlite_path を使用（KABUSYS_ENV に依らず）

- 設定ウィザード:
    python -m kabusys.config_setup

- 設定検証:
    python -m kabusys.validate_config
    python -m kabusys.validate_config --strict

- Paper Trading 検証レポート生成:
    python -m kabusys.tools.paper_verification_report
    python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - デフォルト DB: 環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db

- AI スコア付け / レジーム判定（ライブラリ関数として使用するか、別スクリプト経由で呼ぶ）:
  - kabusys.ai.score_news(conn, target_date, api_key=...)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=...)

停止・Kill Switch
-----------------
- KillSwitch は data/kill.flag を作成して ExecutionEngine に停止シグナルを送る仕組みです。  
- Kill 条件（例）: ドローダウン超過、ポジション上限超過 等。kill.flag が存在すると ExecutionEngine 側で停止される設計です。  
- run_monitoring / run_execution は project_root/data/stop_requested.flag の存在で停止や起動抑止のチェックを行います。

ログ
----
- ログはデフォルトで logs/ ディレクトリへ出力されます（TimedRotatingFileHandler により日次ローテート、30日保持）。  
- コンソール出力は stdout を使用します。LOG_DIR 環境変数や setup_logging の引数で変更可能。

ディレクトリ構成（主なファイル）
--------------------------------
以下はリポジトリ内の主なファイル・モジュール構成（抜粋）です。

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / Settings 定義（自動 .env ロード機能あり）
  - config_setup.py          — 対話式 .env ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py
    - regime_detector.py
  - monitoring/
    - monitoring_db.py
    - monitoring_engine.py
    - system_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - (trade_monitor.py, alert_manager.py 等はリポジトリに存在する想定)
  - utils/
    - logging_setup.py
    - process_priority.py

開発者向けメモ / API 利用
-----------------------
- DuckDB 接続を引数に取る関数群（research / ai / regime_detector）は、外部テーブル（prices_daily / raw_financials / raw_news 等）を参照します。ローカルで分析する場合は DuckDB に該当テーブルを用意してください。
- MonitoringDB は SQLite を永続化層として扱い、単一責務（読み書き）に集中した実装です。
- portfolio.*, position sizing 等は純粋関数群として設計されており、ユニットテストしやすくなっています。
- OpenAI を扱う部分はエラーハンドリング（429/5xx/タイムアウトのリトライ）やレスポンス検証を実装しています。API 呼び出し部はユニットテストでパッチ可能です。

よくある質問 / 注意点
--------------------
- .env は決して Git にコミットしないでください（config_setup.py のヘッダにも注意書きがあります）。
- KABUSYS_ENV=live にセットする前に必ず validate_config.py で検証を行い、LINE 通知設定等を確認してください。
- paper_trading モードは本番 DB と完全に分離するよう設計されています（PAPER_TRADING_SQLITE_PATH を使用）。

ライセンス・バージョン
---------------------
- パッケージバージョン: src/kabusys/__version__ = "0.1.0"
- ライセンス情報はリポジトリの LICENSE ファイルを参照してください（存在する場合）。

貢献 / 開発
-----------
- 新しい機能追加やバグ修正は Pull Request を通して行ってください。  
- 単体テスト・型チェック・静的解析を推奨します（pytest / mypy 等の導入を推奨）。

以上が本リポジトリの概要と基本的な使い方です。特定のモジュールや API の詳細ドキュメントが必要であれば、そのモジュール名を教えてください。さらに詳しい利用例や設定テンプレート（.env.example）も作成できます。