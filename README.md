README
======

概要
----
KabuSys は日本株向けの自動売買 / 研究用ツールキットです。このリポジトリには以下の主要機能を提供するモジュール群が含まれます。

- 実行エンジン（ExecutionEngine）: 発注管理、リスク管理、約定管理を行う実行コンポーネント
- 監視（Monitoring）: システム状態・データ鮮度・取引状況・リスクを定期監視し、Kill Switch を発動可能
- ポートフォリオ構築ユーティリティ: 候補選定・重み計算・サイズ計算・セクター制約などの純粋関数群
- リサーチ（Research）: DuckDB 上の株価データからファクター計算や特徴量探索を行う
- AI モジュール: ニュースを LLM（OpenAI）で解析してスコアや市場レジームを判定
- ユーティリティ: ロギング設定、プロセス優先度設定、設定ウィザード、設定検証ツール 等
- 運用ツール: Paper Trading 検証レポート生成スクリプト など

特徴一覧
--------
主な機能・特性:

- 設定管理:
  - .env ファイルを自動ロード（プロジェクトルート検出）／対話式ウィザードで .env を生成
  - validate_config で起動前に設定と config/*.yaml の妥当性チェック
- 実行環境分離:
  - KABUSYS_ENV による実行モード: development / paper_trading / live
  - paper_trading 時は MockBrokerClient を利用し、paper 用 SQLite DB（data/paper_trading.db）に記録
- 監視:
  - SystemMonitor / TradeMonitor / RiskMonitor を束ねて定期実行
  - Kill Switch（data/kill.flag）で安全に ExecutionEngine を停止
  - stop_requested.flag によるプロセス停止（run_monitoring/run_execution が参照）
- ロギング:
  - 統一的なログ設定（コンソール stdout + 日次ローテーションファイル logs/<app>.log）
- リサーチ & AI:
  - DuckDB を用いたファクター計算、将来リターン・IC 計算など
  - OpenAI（gpt-4o-mini 想定）を用いたニュースセンチメントと市場レジーム判定（失敗時はフェイルセーフ）

前提・依存パッケージ（代表）
--------------------------------
推奨 Python バージョン: 3.10+

主な外部依存:
- duckdb
- psutil
- openai
- PyYAML（config ファイル検証は任意・インストールされていない場合はスキップ）

pip でのインストール例:
  python -m venv .venv
  source .venv/bin/activate
  pip install duckdb psutil openai PyYAML

セットアップ手順（クイックスタート）
------------------------------
1. リポジトリをクローン
   git clone <repo>
   cd <repo>

2. 仮想環境の作成（任意）
   python -m venv .venv
   source .venv/bin/activate

3. 依存パッケージをインストール
   pip install duckdb psutil openai PyYAML

4. 環境変数設定（.env）を作成
   - 対話式ウィザードを推奨:
     python -m kabusys.config_setup
   - 生成後、設定を確認:
     python -m kabusys.validate_config
     # 警告もエラー扱いにする場合:
     python -m kabusys.validate_config --strict

   重要な環境変数の例（.env）:
     JQUANTS_REFRESH_TOKEN=your_token_here
     KABU_API_PASSWORD=your_password_here
     KABUSYS_ENV=development         # development | paper_trading | live
     DUCKDB_PATH=data/kabusys.duckdb
     SQLITE_PATH=data/monitoring.db
     LOG_LEVEL=INFO
     # Paper trading 用（任意）
     PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
     PAPER_FILL_MODE=instant

   自動ロードの無効化:
     KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると .env の自動読み込みをスキップします（テスト等で使用）。

5. ディレクトリの準備
   - data/ と logs/ は実行時に自動作成されますが、権限に注意してください。

使い方（主要コマンド）
---------------------

- 設定ウィザード（.env の作成/更新）
  python -m kabusys.config_setup

- 設定検証
  python -m kabusys.validate_config
  # 警告を FAIL 扱いにする:
  python -m kabusys.validate_config --strict

- 監視ループ起動（SystemMonitor を定期実行）
  python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を変更可能（デフォルト 60）
    例: export MONITOR_POLL_INTERVAL=30

  - このスクリプトは Monitoring 用に本番 sqlite_path を使用します（環境に関係なく）。

  - 停止:
    - プロジェクトルート/data/stop_requested.flag を作成するとループが検知して終了します。

- 実行エンジン起動（ExecutionEngine）
  python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合、MockBroker を使用して paper_trading_db（data/paper_trading.db）に記録します。
  - 起動前に data/stop_requested.flag が既に存在すると起動せず終了します。
  - 実行中に停止するには data/stop_requested.flag を作成するか、外部から Kill Switch（data/kill.flag）を置くことが可能（KillSwitch は ExecutionEngine 側で監視して停止処理を行う）。

- Paper Trading 検証レポート（運用後の評価）
  python -m kabusys.tools.paper_verification_report
  オプション:
    --from YYYY-MM-DD   レポート開始日
    --to   YYYY-MM-DD   レポート終了日
    --db PATH           SQLite DB パス（環境変数 PAPER_TRADING_SQLITE_PATH より優先）

- AI/リサーチ関連の呼び出し（ライブラリ的に使用）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - kabusys.research.calc_momentum(conn, date)
  - kabusys.research.calc_volatility(...), calc_value(...), calc_forward_returns(...), calc_ic(...)

運用上の注意
-------------
- Kill Switch / Stop Flag:
  - KillSwitch は Settings.kill_flag_path（デフォルト data/kill.flag）に理由を書き込むことで ExecutionEngine に停止を促します（冪等）。KillSwitch.clear() で削除できます。
  - run_monitoring/run_execution は project_root/data/stop_requested.flag を監視し、存在すると安全に終了します。
- ログ:
  - デフォルトで logs/<app>.log に日次ローテーションでログを出力します。ログディレクトリは LOG_DIR 環境変数で変更可能。
- Paper Trading:
  - paper_trading モードは本番 DB と完全分離されるよう設計されています。必ず PAPER_TRADING_SQLITE_PATH を確認してください。
- OpenAI API:
  - AI モジュールは OPENAI_API_KEY を必要とします。キー未設定時は該当処理は例外または 0.0 フォールバック（実装ごとに異なる）になります。呼び出し側で api_key を明示的に渡すことも可能です。
- .env の自動読み込み:
  - プロジェクトルート（.git または pyproject.toml）を基準に .env/.env.local を自動読み込みします。必要に応じて KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化できます。

ディレクトリ構成（主要ファイル）
------------------------------
以下はパッケージ内の主要モジュール一覧（src/kabusys/ 以下）。実際のプロジェクトはさらに細かいモジュールやファイルを含みます。

- src/kabusys/
  - __init__.py
  - config.py                 # 環境変数・設定管理
  - config_setup.py           # .env 対話式ウィザード
  - validate_config.py        # 設定検証 CLI
  - run_monitoring.py         # SystemMonitor ポーリングスクリプト
  - run_execution.py          # ExecutionEngine 起動スクリプト
  - utils/
    - logging_setup.py        # ログ設定ユーティリティ
    - process_priority.py     # プロセス優先度・CPU affinity 設定
  - monitoring/
    - monitoring_db.py        # SQLite 監視 DB ラッパ
    - system_monitor.py
    - trade_monitor.py        # （ここで紹介は割愛。取引監視ロジック）
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py        # （アラート送信ロジック）
  - execution/
    - execution_engine.py     # 実行エンジン（EngineConfig 等）
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
    - broker_factory.py
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
  - tools/
    - paper_verification_report.py

参考: 主要な環境変数一覧
-----------------------
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV (development | paper_trading | live) — デフォルト development
- DUCKDB_PATH — デフォルト data/kabusys.duckdb
- SQLITE_PATH — デフォルト data/monitoring.db
- PAPER_TRADING_SQLITE_PATH — デフォルト data/paper_trading.db
- LOG_LEVEL — デフォルト INFO
- OPENAI_API_KEY — AI モジュール用
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング秒数（整数）
- KILL_FLAG_CLEAR_ON_START — 本番での自動クリア防止に注意（0 推奨）

よくある運用フロー（例）
-----------------------
1. .env を作成（python -m kabusys.config_setup）
2. 設定検証（python -m kabusys.validate_config）
3. DuckDB / SQLite の初期データを配置（データパイプライン経由）
4. 実行エンジン起動（運用ノード）
   python -m kabusys.run_execution
5. 監視ノードで監視を起動
   python -m kabusys.run_monitoring
6. 異常発生時は monitoring が Kill Switch を書き込み → ExecutionEngine が安全停止

ライセンス・貢献
----------------
（ここにプロジェクト固有のライセンスや貢献指針を記載してください。）

付記（開発者向けメモ）
--------------------
- DuckDB のクエリやテーブルスキーマは各モジュール内の docstring / SQL を参照してください。
- モジュール設計は「副作用を極力避ける」「フェイルセーフ（AI 呼び出し失敗時は安全なフォールバック）」を重視しています。
- テスト時に .env 自動読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

以上。必要があれば README に含めたい追加の運用手順や環境変数の説明、サンプル .env テンプレートを作成します。