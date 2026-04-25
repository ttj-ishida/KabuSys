KabuSys — 日本株自動売買システム
=============================

本ドキュメントはリポジトリ内のコードベース（src/kabusys 以下）を対象とした README です。プロジェクト概要、主要機能、セットアップ手順、実行方法、ディレクトリ構成を日本語でまとめています。

プロジェクト概要
---------------
KabuSys は日本株向けの自動売買システムのコア実装群です。下記の主要な責務を含みます。

- 発注エンジン（ExecutionEngine）とブローカークライアントの抽象化（paper/live 切り替え対応）
- 監視コンポーネント（System / Trade / Risk）と Kill Switch による自動停止
- ポートフォリオ構築（候補選定、重み付け、ポジションサイズ計算、セクター制限）
- リサーチ（ファクター計算、特徴量探索、IC 計算）
- ニュース NLP を使ったセンチメント評価（OpenAI API を利用）
- 運用ユーティリティ（設定ウィザード・設定検証・ログ設定・プロセス優先度設定 等）

主な機能一覧
-------------
- 実行スクリプト
  - run_execution.py: ExecutionEngine の起動（KABUSYS_ENV により paper_trading を分離）
  - run_monitoring.py: SystemMonitor をポーリングして監視ログを取得
- 設定まわり
  - config_setup.py: .env を対話式で生成 / 更新するウィザード
  - validate_config.py: .env や config/*.yaml の起動前チェック
  - config.py: 環境変数からの設定取得と Settings クラス
- 監視
  - monitoring/monitoring_db.py: SQLite による監視ログ永続化
  - monitoring/system_monitor.py, trade_monitor.py, risk_monitor.py 等: 各種チェック実装
  - monitoring/monitoring_engine.py: 各 Monitor を束ねる実行ループ
  - monitoring/kill_switch.py: Kill Switch（データ駆動で Execution を停止）
- 発注・リスク管理（execution 以下、コード省略）
- ポートフォリオ構築（portfolio パッケージ）
  - 候補選定、等金額／スコア重み、リスク補正（セクターキャップ・レジーム乗数）、ポジションサイズ算出
- リサーチ（research パッケージ）
  - ファクター計算（Momentum / Volatility / Value）
  - 将来リターン計算、IC（スピアマンランク相関）、統計サマリ
- AI
  - ai/news_nlp.py: raw_news を集約し OpenAI でセンチメントを算出して ai_scores に書き込み
  - ai/regime_detector.py: ETF MA とマクロニュースセンチメントを合成して日次レジーム判定
- ツール
  - tools/paper_verification_report.py: ペーパートレード DB の検証レポート生成

必須・推奨依存パッケージ
---------------------
（環境によりバージョン指定を行ってください）
- Python 3.10+
- duckdb
- psutil
- openai（AI 機能を利用する場合）
- PyYAML（設定検証で YAML 構文チェックを行う場合に必要、任意）
- sqlite3（標準ライブラリ）

セットアップ手順
----------------

1. リポジトリをクローン、またはパッケージを配置
2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 依存パッケージをインストール
   - pip install duckdb psutil openai pyyaml
     （必要なものだけインストールして構いません。AI/検証機能はオプション）
4. .env の用意
   - 対話式ウィザードを使う:
     - python -m kabusys.config_setup
   - または手動で .env を作成（プロジェクトルートに配置）
   - 主要な環境変数例:
     - JQUANTS_REFRESH_TOKEN=your_token
     - KABU_API_PASSWORD=your_password
     - KABUSYS_ENV=development|paper_trading|live
     - DUCKDB_PATH=data/kabusys.duckdb
     - SQLITE_PATH=data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
     - OPENAI_API_KEY=sk-xxxx   (AI 機能を使う場合)
     - LOG_LEVEL=INFO
     - KILL_FLAG_CLEAR_ON_START=0
   - 自動 env ロード:
     - config.py はプロジェクトルート（.git または pyproject.toml のある階層）を探索して .env/.env.local を自動ロードします。
     - 自動ロードを無効化する場合: KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を環境に設定

5. DB/ディレクトリの準備
   - デフォルトでは data/ 以下のファイルを参照します。必要に応じてディレクトリ作成:
     - mkdir -p data logs

設定の検証
---------
- validate_config.py を使って起動前にチェックできます:
  - python -m kabusys.validate_config
  - 警告を FAIL 扱いにするには --strict を指定: python -m kabusys.validate_config --strict

使い方（実行例）
----------------

1. ExecutionEngine を起動（本番／ペーパートレード切り替え）
   - python -m kabusys.run_execution
   - 挙動:
     - Settings により KABUSYS_ENV が paper_trading の場合は paper_trading DB（PAPER_TRADING_SQLITE_PATH）と MockBrokerClient を使います。本番（live）は本番 DB を使用します。
     - 起動前に data/stop_requested.flag が存在すると起動をスキップします。
     - プロセス優先度を "high" に設定します（可能な場合）。
     - 実行中、data/execution.pid に PID を書き出します（Engine 側の pid_file 設定に依存）。
     - 停止は Kill Switch による kill.flag（Settings.kill_flag_path、デフォルト data/kill.flag）や管理側で stop_requested.flag を作るなどで行います。

2. 監視ループを起動
   - python -m kabusys.run_monitoring
   - 挙動:
     - SystemMonitor のポーリングループを起動します。デフォルトの間隔は 60 秒（環境変数 MONITOR_POLL_INTERVAL で上書き可能）。
     - 監視 DB（SQLite）は環境にかかわらず settings.sqlite_path（デフォルト data/monitoring.db）を使用して永続化します。
     - 停止は data/stop_requested.flag を作成することで検出します。

3. Paper Trading の検証レポート生成
   - python -m kabusys.tools.paper_verification_report
   - オプション:
     - --from YYYY-MM-DD --to YYYY-MM-DD --db PATH
   - 簡単なパス解決: --db > 環境変数 PAPER_TRADING_SQLITE_PATH > デフォルト data/paper_trading.db

4. AI 関連（ニュース NLP / レジーム判定）
   - OpenAI API キーが必要（OPENAI_API_KEY または引数で渡す）
   - ニュースセンチメント計算:
     - kabusys.ai.score_news を呼び出すか、適切なエントリポイント（スクリプト／タスク）から実行
   - レジーム判定:
     - kabusys.ai.regime_detector.score_regime を呼び出す（DB と API キーが必要）

停止・Kill Switch
-----------------
- 手動停止（run_* スクリプト共通）
  - プロジェクトルート/data/stop_requested.flag を作成すると、run_monitoring.py / run_execution.py（起動時とループ中）が検出して停止または起動抑制します。
- 自動停止（システムによる Kill Switch）
  - monitoring の評価ロジック（RiskMonitor 等）が条件を満たすと KillSwitch が data/kill.flag（Settings.kill_flag_path）を書き込み、ExecutionEngine 側で検出して安全停止する設計です。
  - KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に自動クリアされますが、本番では 0 を推奨します。

ログ
----
- ログは kabusys.utils.logging_setup.setup_logging を通して統一的に設定されます。
  - デフォルト出力先: stdout と logs/<app_name>.log（日次ローテート、30 日保持）
  - 環境変数 LOG_DIR でログディレクトリを変更可能
  - LOG_LEVEL でログレベルを制御

重要な環境変数（主要）
--------------------
- KABUSYS_ENV: development | paper_trading | live
- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト data/paper_trading.db）
- OPENAI_API_KEY: OpenAI を使う場合に必要
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）
- PAPER_FILL_MODE: ペーパートレードの約定動作（instant | partial | never | reject）
- LOG_LEVEL: "DEBUG","INFO","WARNING","ERROR","CRITICAL"
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（1/0）

ディレクトリ構成（抜粋）
-----------------------
src/kabusys/
- __init__.py
- config.py                — 環境変数 / Settings
- config_setup.py          — .env 対話式ウィザード
- validate_config.py       — 設定検証 CLI
- run_execution.py         — ExecutionEngine 起動スクリプト
- run_monitoring.py        — SystemMonitor 起動スクリプト
- execution/               — 発注エンジン・注文管理・ブローカー抽象
- monitoring/              — 監視ロジック、DB 永続化、Kill Switch、Alert 管理
  - monitoring_db.py
  - system_monitor.py
  - risk_monitor.py
  - kill_switch.py
  - monitoring_engine.py
- portfolio/               — 候補選定・重み付け・ポジションサイズ等
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py
- research/                — ファクター / 特徴量探索
  - factor_research.py
  - feature_exploration.py
- ai/                      — OpenAI 経由のニュース NLP / レジーム判定
  - news_nlp.py
  - regime_detector.py
- tools/                   — 補助ツール（paper_verification_report 等）
  - paper_verification_report.py
- utils/                   — ロギング設定・プロセス優先度などユーティリティ
  - logging_setup.py
  - process_priority.py

開発メモ・注意点
----------------
- 設定ファイル（.env）は絶対に Git にコミットしないでください（config_setup でもその旨の注記あり）。
- .env の自動ロードはプロジェクトルート探索（.git / pyproject.toml）に依存します。パッケージ配布後の動作にも配慮した実装です。
- AI 関連は外部 API（OpenAI）を使用するため API キーと通信環境が必要です。API 呼び出しはリトライ・フェイルセーフを備えていますが、費用・レート制限に注意してください。
- run_execution / run_monitoring は stop_requested.flag を使ったシンプルなプロセスマネジメントを採用しています。運用時は systemd / supervisor / コンテナ管理を併用することを推奨します。
- SQLite / DuckDB のパスやログディレクトリは環境変数で変更可能です。運用アセット（バックアップ、アクセス制御等）を考慮してください。

ライセンス・バージョン
---------------------
パッケージバージョンは src/kabusys/__init__.py の __version__ を参照してください（現状 0.1.0）。

付録：よく使うコマンド
----------------------
- .env ウィザード:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config
- ExecutionEngine 起動:
  - python -m kabusys.run_execution
- Monitoring 起動:
  - python -m kabusys.run_monitoring
- Paper Trading レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

---
必要であれば、各モジュール（monitoring/system_monitor, ai/news_nlp, execution 部分など）の詳細な利用例・API 仕様や、Docker / systemd 用の起動ユニット例も作成できます。どの箇所のドキュメントが欲しいか教えてください。