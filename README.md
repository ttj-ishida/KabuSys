README
=====

概要
----
KabuSys は日本株向けの自動売買システム（研究・ポートフォリオ構築・発注・監視・AI 補助）を念頭に設計された Python パッケージです。本リポジトリには以下の主要機能を持つモジュール群が含まれます：

- 発注エンジン（ExecutionEngine）とブローカークライアントの抽象化（paper/live 切替対応）
- 監視サブシステム（システム状態、注文ログ、リスク監視、Kill Switch）
- ポートフォリオ構築ユーティリティ（候補選定・重み付け・サイズ計算・リスク調整）
- 研究向けファクター計算・特徴量解析（DuckDB 経由）
- ニュース NLP / レジーム判定（OpenAI を利用したセンチメント評価）
- 各種 CLI ユーティリティ（.env ウィザード、設定検証、検証レポート生成）

主な特徴
--------
- 環境による振る舞い切替: KABUSYS_ENV により development / paper_trading / live を切替可能。paper_trading 時は MockBrokerClient を使い、発注データを本番 DB と分離して data/paper_trading.db に記録します。
- 安全保護: Kill Switch（data/kill.flag）や停止フラグ（data/stop_requested.flag）で外部からの停止制御が可能。監視が閾値超過時に自動でフラグを書き込めます。
- ロギング: 統一された logging 設定（コンソール + 日次ローテートファイル logs/<app>.log）を持ちます。
- DB: 監視用に SQLite（デフォルト data/monitoring.db）、分析用に DuckDB（デフォルト data/kabusys.duckdb）を使用。
- AI 機能: OpenAI（gpt-4o-mini 等）を用いたニュースセンチメント（ai_scores）、市場レジーム判定を実装。API キーが必要。
- 研究用ユーティリティ: DuckDB 接続を受け取り純粋関数でファクターや将来リターン、IC（情報係数）等を計算。
- テストしやすい設計: .env 自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。多くの API 呼び出しは差し替え可能に設計。

セットアップ手順
----------------

1. Python 環境を準備
   - 推奨: venv を使った仮想環境
     python -m venv .venv
     source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージをインストール
   - requirements.txt がある場合はそれを使ってください（本リポジトリに含まれていない場合、少なくとも以下が必要です）:
     pip install duckdb psutil openai
   - 監視/検証で YAML をパースする場合は PyYAML があると config/*.yaml の検証が可能:
     pip install pyyaml

3. プロジェクトルートにデフォルトフォルダを作成（自動で作られる場合あり）
   mkdir -p data logs

4. 環境変数の準備
   - .env を作成するか環境変数を設定します。初期作成には対話式ウィザードを使うと便利です（次節参照）。
   - 必須変数（例）
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - 主要な環境変数（一部）
     - KABUSYS_ENV: development | paper_trading | live (デフォルト: development)
     - DUCKDB_PATH: data/kabusys.duckdb
     - SQLITE_PATH: data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
     - LOG_LEVEL: DEBUG|INFO|...
     - OPENAI_API_KEY: OpenAI API キー（AI 機能使用時）
     - PAPER_FILL_MODE: instant|partial|never|reject（paper_trading の約定振る舞い）
     - MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、デフォルト 60）

使い方
------

1. .env の作成（対話式ウィザード）
   python -m kabusys.config_setup
   - ウィザードは .env を生成/更新します。終了後は python -m kabusys.validate_config で検証してください。

2. 設定検証
   python -m kabusys.validate_config
   - --strict オプションを付けると警告も失敗扱いになります。

3. ExecutionEngine（発注エンジン）の起動
   - 通常実行:
     python -m kabusys.run_execution
   - 動作:
     - 起動時にプロセス優先度を high に設定し、Settings() を読み込みます。
     - KABUSYS_ENV=paper_trading の場合は paper_trading 用 SQLite を使用（PAPER_TRADING_SQLITE_PATH）。
     - 停止は data/stop_requested.flag を作成することで外部から行えます。
     - 実行中は data/execution.pid に PID を書き込みます。

4. Monitoring（監視ループ）の起動
   python -m kabusys.run_monitoring
   - デフォルトのポーリング間隔は 60 秒。環境変数 MONITOR_POLL_INTERVAL で上書き可能（正の整数）。
   - 監視は常に Settings.sqlite_path（本番監視 DB）を用います（環境にかかわらず）。
   - stop はプロジェクトの data/stop_requested.flag を検出するとループを終了します。

5. Paper Trading 検証レポート生成
   python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
   - デフォルト DB: 環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db

6. AI 関連（ニューススコア / レジーム判定）
   - OPENAI_API_KEY が必要です。
   - プログラム経由で呼び出す例:
     from kabusys.ai import score_news
     score_news(duckdb_conn, target_date, api_key="...")

停止 / Kill Switch
- 外部停止フラグ:
  - data/stop_requested.flag — run_execution や run_monitoring が検出して安全終了します。
  - data/kill.flag — KillSwitch が書き込み、ExecutionEngine 停止のトリガーに使います（Monitoring が書き込み）。
- run_execution は起動時に KILL_FLAG_CLEAR_ON_START の設定により kill.flag を自動クリアするか制御します（本番では 0 を推奨）。

ログ
- ログファイルはデフォルト logs/<app_name>.log（例: logs/execution.log, logs/monitoring.log）に日次ローテートで保存されます。
- ログ設定は kabusys.utils.logging_setup.setup_logging を利用して統一管理されます。

注意点 / 運用メモ
- Monitoring は常に Settings.sqlite_path を使います（監視用 DB を本番 DB に設定するため）。
- Execution は paper_trading 環境であれば paper_sqlite_path（完全分離）を使用します。
- OpenAI 呼び出しはネットワークエラーやレート制限に対してリトライが組み込まれていますが、API キーや料金管理は運用者の責任です。
- Cron / systemd などでサービス化する際は logs/ と data/ のパーミッションに注意してください。
- 自動 .env 読み込みはプロジェクトルート（.git または pyproject.toml を基準）を探索して行われます。テストや CI で無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

ディレクトリ構成
----------------
以下は src/kabusys 以下を抜粋した主要ファイル構成です（省略あり）:

- src/
  - kabusys/
    - __init__.py
    - config.py                  # 環境変数/.env のロードと Settings クラス
    - config_setup.py            # .env 対話式ウィザード
    - validate_config.py         # 設定検証 CLI
    - run_execution.py           # ExecutionEngine 起動スクリプト
    - run_monitoring.py          # SystemMonitor ポーリング起動スクリプト
    - tools/
      - __init__.py
      - paper_verification_report.py  # Paper Trading 検証レポート
    - portfolio/
      - __init__.py
      - portfolio_builder.py     # 候補選定・重み計算
      - risk_adjustment.py       # セクター制限・レジーム乗数
      - position_sizing.py       # 発注株数計算
    - monitoring/
      - monitoring_db.py        # SQLite 維持・読み書き
      - system_monitor.py       # システム・データ鮮度監視
      - trade_monitor.py        # （省略: trade 関連監視）
      - risk_monitor.py         # ドローダウン・ポジション上限監視
      - kill_switch.py          # kill.flag 書込・評価
      - monitoring_engine.py    # モニターの束ね実行
      - alert_manager.py        # （省略: 通知管理、LINE など）
    - execution/
      - execution_engine.py     # ExecutionEngine（発注セッション管理）
      - order_manager.py
      - order_repository.py
      - reconciler.py
      - broker_factory.py
      - risk_manager.py
    - research/
      - __init__.py
      - factor_research.py      # Momentum/Value/Volatility など
      - feature_exploration.py  # IC / 統計
    - ai/
      - __init__.py
      - news_nlp.py             # ニュース NLP スコアリング（OpenAI 呼び出し）
      - regime_detector.py      # 市場レジーム判定（OpenAI）
    - utils/
      - __init__.py
      - logging_setup.py        # ログ初期化ユーティリティ
      - process_priority.py     # 優先度・CPU affinity 制御

サンプル .env（最小例）
----------------------
以下は .env の最小例（本番での保存や git 管理は厳禁）:

JQUANTS_REFRESH_TOKEN=your_jquants_token_here
KABU_API_PASSWORD=your_kabu_password_here
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
LOG_LEVEL=INFO
OPENAI_API_KEY=sk-...
PAPER_FILL_MODE=instant
PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
KILL_FLAG_CLEAR_ON_START=0

開発者向けヒント
----------------
- テスト時に .env の自動ロードを無効にする:
  export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
- logging の詳細や出力先を変えたい場合は kabusys.utils.logging_setup.setup_logging を直接呼んで設定できます。
- OpenAI 呼び出し部分はモジュール内の小関数（例: _call_openai_api）をモックしてテストできます。
- DuckDB を用いる研究モジュールは副作用を持たない関数群を多く提供しているため、単体で検証しやすく設計されています。

ライセンス / バージョン
----------------------
- パッケージバージョン: src/kabusys/__init__.py の __version__ を参照してください。

フィードバック / 変更履歴
-----------------------
コード・設計に関する質問や改善提案があれば Issue を立ててください。README に書かれていない実装上の詳細（例: execution の内部動作、各種設定の細かい意味）はソース内の docstring やコメントを参照してください。

以上。運用・デプロイの際は本 README の注意点（kill_flag, DB 分離, LOG 管理, OpenAI キー管理）を遵守してください。