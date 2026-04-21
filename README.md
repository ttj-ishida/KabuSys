KabuSys
=======

日本株向けの自動売買システムのコアライブラリ群です。  
このリポジトリは、戦略の研究・ファクター計算、ポートフォリオ構築、注文発行（ExecutionEngine）、およびシステム監視（Monitoring）を含む実装を提供します。

主な特徴
--------
- ポートフォリオ構築
  - 候補選定（スコア／ランク）、等金額・スコア加重配分
  - ポジションサイズ計算（リスクベース、単元株丸め、aggregate cap）
  - セクター集中制限、レジーム乗数（bull/neutral/bear）
- リサーチ / ファクター計算
  - Momentum / Volatility / Value 等のファクターを DuckDB 上で計算
  - 将来リターンの計算、IC（Information Coefficient）や統計サマリ
- AI 補助
  - ニュースのセンチメント解析（OpenAI を使用、gpt-4o-mini を想定）
  - マクロニュースと ETF の MA を使った市場レジーム判定
- 実行系（Execution）
  - ExecutionEngine の起動スクリプト（paper_trading モードあり）
  - ブローカークライアントの抽象化（実ブローカ／モック切替）
  - OrderManager / RiskManager / Reconciler 等のコンポーネント群
- 監視（Monitoring）
  - SystemMonitor / TradeMonitor / RiskMonitor を束ねる MonitoringEngine
  - kill.flag による外部停止（KillSwitch）
  - 監視ログ永続化（SQLite、monitoring_db モジュール）
  - logging の統一セットアップ（コンソール + 日次ローテートファイル）
- ユーティリティ
  - 対話式 .env 作成ウィザード
  - 設定検証 CLI（警告/エラー出力）
  - Paper Trading 検証レポート生成スクリプト

前提・依存
-----------
- Python 3.10 以上（PEP 604 型表記などを使用しているため）
- 主な Python パッケージ（例）
  - duckdb
  - psutil
  - openai
  - PyYAML（validate_config の YAML 検証で推奨）
- SQLite（組み込み）／DuckDB（ローカルファイル DB）
- ネットワークアクセス（OpenAI を使う場合）

インストール（例）
-----------------
1. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   - pip install duckdb psutil openai PyYAML
   - （requirements.txt がある場合は pip install -r requirements.txt を使用）

環境変数 / 設定
----------------
- .env 自動読み込み
  - プロジェクトルート（.git または pyproject.toml を基準）にある .env / .env.local を自動で読み込みます。
  - OS 環境変数は保護され、.env.local の上書きは可能ですが OS の既存値は上書きされません。
  - 自動ロードを無効化する場合: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

主要な環境変数（抜粋）
- KABUSYS_ENV: 実行環境（development / paper_trading / live、デフォルト: development）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用リフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 SQLite（default: data/paper_trading.db）
- PAPER_FILL_MODE: paper_trading の約定モード（instant/partial/never/reject、default: instant）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag をクリアするか（0/1、本番では 0 推奨）
- MONITOR_POLL_INTERVAL: monitoring のポーリング間隔（秒、デフォルト 60）

セットアップ手順（推奨ワークフロー）
---------------------------------
1. リポジトリを取得
   - git clone ...

2. 仮想環境の作成と依存パッケージインストール（上記参照）

3. .env の作成（対話ウィザード推奨）
   - python -m kabusys.config_setup
     - 対話形式で必須値（トークン、パスワード等）を入力して .env を生成できます。

4. 設定の検証
   - python -m kabusys.validate_config
   - 問題があれば修正し、--strict をつけると警告もエラー扱いになります:
     - python -m kabusys.validate_config --strict

5. データディレクトリとログディレクトリの確認
   - デフォルトでは data/ と logs/ を使用します。必要に応じて環境変数で上書きしてください。

基本的な使い方
-------------
- 監視ループを起動（本番の監視プロセス）
  - python -m kabusys.run_monitoring
  - 補足:
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で上書きできます（例: MONITOR_POLL_INTERVAL=30）。
    - run_monitoring は常に本番用 sqlite_path を使用して monitoring DB を操作します（環境に関わらず）。
    - 停止は data/stop_requested.flag の作成でループを終了できます（ファイルが存在すると監視ループが終了）。

- 実行エンジンを起動（注文発行）
  - python -m kabusys.run_execution
  - 補足:
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient が使用され、ペーパートレード用 DB（data/paper_trading.db）へ記録され、本番 DB と分離されます。
    - 停止フラグ（data/stop_requested.flag）が立っていると起動せず終了します。
    - 実行中は data/execution.pid に PID を書きます（設定で変更可）。

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - オプション
    - --from YYYY-MM-DD: レポート開始日
    - --to YYYY-MM-DD: レポート終了日
    - --db PATH: SQLite ファイルパス（PAPER_TRADING_SQLITE_PATH 環境変数より優先）

- .env 対話ウィザード
  - python -m kabusys.config_setup

- 設定検証 CLI
  - python -m kabusys.validate_config
  - --strict を付けると警告も FAIL 扱い

ログ
----
- ログ出力は kabusys.utils.logging_setup.setup_logging を通して統一的に設定されます。
  - デフォルト: logs/<app_name>.log（TimedRotatingFileHandler、日次ローテート、30世代保持）
  - コンソール出力は stdout（stderr ではない）に流れます。
  - 例: run_execution は logs/execution.log、run_monitoring は logs/monitoring.log に出力します（app_name に依存）。

停止 / Kill Switch
-----------------
- KillSwitch（data/kill.flag）:
  - RiskMonitor 等が条件を満たすと kill.flag を書き込み、ExecutionEngine に停止シグナルを送ります。
  - KillSwitch は冪等で、既存の flag があれば再書き込みしません。
  - 起動時に自動で kill.flag をクリアする設定（KILL_FLAG_CLEAR_ON_START=1）が可能ですが、本番では推奨されません（安全のため 0 推奨）。
- 強制停止（監視側）
  - data/stop_requested.flag を作成すると run_monitoring/run_execution のループが検知して終了します。

ディレクトリ構成（主要ファイル）
-------------------------------
（リポジトリの src/kabusys 以下を要約）

- kabusys/
  - __init__.py (バージョン定義)
  - config.py (環境変数 / Settings クラス、自動 .env 読込)
  - config_setup.py (.env 対話ウィザード)
  - validate_config.py (設定検証 CLI)
  - run_execution.py (ExecutionEngine 起動スクリプト)
  - run_monitoring.py (Monitoring 起動スクリプト)
- kabusys/portfolio/
  - portfolio_builder.py (候補選定・重み計算)
  - position_sizing.py (発注株数計算・aggregate cap)
  - risk_adjustment.py (セクター上限・レジーム乗数)
- kabusys/research/
  - factor_research.py (momentum/volatility/value ファクター計算)
  - feature_exploration.py (将来リターン、IC、統計)
- kabusys/ai/
  - news_nlp.py (ニュース → LLM で銘柄別センチメント)
  - regime_detector.py (マクロ+MA を合成してレジーム判定)
- kabusys/monitoring/
  - monitoring_db.py (SQLite スキーマ初期化 & DB 操作ラッパ)
  - system_monitor.py, trade_monitor.py, risk_monitor.py, kill_switch.py, monitoring_engine.py, alert_manager.py (各種監視ロジック)
- kabusys/utils/
  - logging_setup.py (ログ初期化)
  - process_priority.py (プロセス優先度 / CPU affinity 設定)
- kabusys/tools/
  - paper_verification_report.py (ペーパートレード検証レポート)
- data/ (実行時に使用するデータ・フラグ・DB ファイル等)
- logs/ (デフォルトログ出力先)

設計上の留意点
--------------
- DuckDB をデータ分析用の永続 DB として利用し、prices_daily / raw_financials 等のテーブルを参照してファクター計算を行います。これにより計算ロジックは実行系と分離されています。
- 重要な日時処理（news window、regime scoring 等）はルックアヘッドバイアスを避けるよう設計されています（datetime.today()/date.today() を直接参照しないなど）。
- AI（OpenAI）呼び出し箇所はリトライ・バックオフやレスポンスバリデーションを実装しており、フェイルセーフとして API 失敗時は中立値で続行します。
- 本リポジトリの .env は絶対に Git にコミットしないでください（config_setup.py のヘッダにも注意書きあり）。

トラブルシュート / よくある質問
-------------------------------
- .env が読み込まれない
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 が設定されていないか確認してください。
  - プロジェクトルートが .git または pyproject.toml を含んでいるか確認してください。
- ログファイルが作れない（パーミッション等）
  - logs/ ディレクトリを手動で作成するか、LOG_DIR を指定して適切な書き込み権限を与えてください。
- OpenAI API にアクセスできない
  - 環境変数 OPENAI_API_KEY を設定するか、該当関数の api_key 引数で明示してください。
- validate_config で YAML の検証がスキップされる
  - PyYAML が未インストールの場合は YAML 検証がスキップされ、警告が出ます。PyYAML を入れると検証されます。

貢献・開発
----------
- 新しい機能を追加する場合はテストとドキュメントを追加してください。
- .env.example を参考にローカルで設定を行い、validate_config で検証してから実行してください。

ライセンス
---------
- 本リポジトリにライセンスファイルがある場合はそれに従ってください（ここでは特に指定していません）。

---
必要に応じて README に追記します。例えば、使用する Python バージョンや具体的な requirements.txt の中身、運用時の systemd / Supervisor 用の unit サンプル、テスト手順などが必要であれば指示してください。