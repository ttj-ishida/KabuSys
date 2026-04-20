README
=====

概要
----
KabuSys は日本株向けの自動売買・研究フレームワークです。銘柄選定、配分、ポジションサイジング、リスク監視、モニタリング、ペーパートレード検証、LLM を用いたニュース NLP / レジーム判定などの機能を備えています。主要コンポーネントは CLI スクリプト（実行エンジン・監視ループ等）とライブラリモジュール（portfolio、research、monitoring、ai、utils など）で構成されています。

主な機能
--------
- ExecutionEngine（発注・注文管理・リスク管理・リコンシリエーション）
  - 本番とペーパートレードを区別（KABUSYS_ENV=paper_trading 時は MockBrokerClient を使用）
  - paper_trading は専用 SQLite（data/paper_trading.db）に記録
- Monitoring（システム・注文・リスク監視）
  - system_status / trade_logs / risk_logs / dashboard 等を SQLite に永続化
  - Kill Switch によるフラグファイル停止機構（data/kill.flag）
- Portfolio construction
  - 候補選定、等重・スコア加重配分、ポジションサイズ計算、セクターキャップ、レジーム乗数
- Research
  - DuckDB を使ったファクター計算（モメンタム、ボラティリティ、バリュー等）
  - 将来リターン計算、IC（情報係数）計算、統計サマリー
- AI（OpenAI を利用）
  - ニュース記事のセンチメントスコアリング（ai_scores）
  - マクロセンチメントと ETF MA を合成した市場レジーム判定
- ユーティリティ
  - ロギング設定、プロセス優先度 / CPU affinity、.env ウィザード、設定検証、レポート生成ツール

セットアップ手順
----------------
1. リポジトリを取得
   - 例: git clone <repo-url>

2. Python 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存パッケージをインストール
   - requirements.txt がある場合: pip install -r requirements.txt
   - 最低限必要となる外部パッケージ（機能に応じて）:
     - duckdb
     - psutil
     - openai（AI 機能を使う場合）
     - PyYAML（config 検証で YAML をパースしたい場合）

4. 環境変数の初期化（.env）
   - 対話式ウィザードで .env を作成 / 更新:
     - python -m kabusys.config_setup
   - 必須環境変数（少なくとも以下は設定してください）:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - AI 機能を使う場合:
     - OPENAI_API_KEY を .env に設定
   - 環境読み込み:
     - デフォルトでプロジェクトルートの .env/.env.local が自動ロードされます。自動読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

5. 設定検証（起動前チェック）
   - python -m kabusys.validate_config
   - 警告もエラー扱いにする場合:
     - python -m kabusys.validate_config --strict

主要な環境変数（抜粋）
--------------------
- KABUSYS_ENV: 実行環境 ("development" / "paper_trading" / "live")（デフォルト: development）
- JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（AI 機能利用時）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 DB（デフォルト: data/paper_trading.db）
- LOG_LEVEL: ログレベル（"DEBUG","INFO","WARNING","ERROR"）
- LOG_DIR: ログ出力先ディレクトリ（デフォルト: logs/）
- MONITOR_POLL_INTERVAL: Monitoring ポーリング間隔（秒、デフォルト 60）
- KILL_FLAG_CLEAR_ON_START: 本番で kill.flag を自動クリアするか（"0" 推奨）

使い方
------
- 監視ループを起動（Monitoring）
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒単位で上書き可能（例: MONITOR_POLL_INTERVAL=30）
  - 監視プロセスは常に本番の sqlite_path を使用します（環境にかかわらず）

- 実行エンジンを起動（ExecutionEngine）
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使い、PAPER_TRADING_SQLITE_PATH に記録します
  - 実行中の PID は data/execution.pid（デフォルト）に保存されます
  - 停止方法:
    - run_execution と run_monitoring の両方はプロジェクトルートの data/stop_requested.flag を検知して安全に停止します
    - KillSwitch（監視から）により data/kill.flag が書き込まれると ExecutionEngine 側で停止指示を受けます

- 環境設定ウィザード
  - python -m kabusys.config_setup
  - .env を対話式に作成 / 更新します

- 設定検証
  - python -m kabusys.validate_config
  - オプション --strict で警告も失敗扱いにできます

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB パスは --db で指定可能。環境変数 PAPER_TRADING_SQLITE_PATH も参照します。

ログ・デバッグ
--------------
- ログ設定は kabusys.utils.logging_setup.setup_logging により統一的に行われます。
- デフォルトログディレクトリ: logs/
- ログファイル名はアプリ名プレフィックス（例: execution.log, monitoring.log）
- LOG_LEVEL または引数でログレベルを変更可能

停止・Kill スイッチ
------------------
- data/stop_requested.flag: 監視・実行スクリプトの外部停止用フラグ（スクリプトはこのファイルを検知して安全に終了します）
- data/kill.flag: KillSwitch が書き込むフラグ。主に監視から ExecutionEngine の停止を要求するために使用
- 実行 PID は data/execution.pid（デフォルト）に出力されます

ディレクトリ構成（主なファイル・概要）
------------------------------------
（src/kabusys 以下を想定）

- __init__.py
  - パッケージ定義・バージョン

- config.py
  - 環境変数ロード・Settings クラス。.env 自動ロード機能あり。
- config_setup.py
  - .env を対話的に作成するウィザード CLI
- validate_config.py
  - 起動前の設定検証 CLI

- run_monitoring.py
  - SystemMonitor を用いたポーリングループ起動スクリプト

- run_execution.py
  - ExecutionEngine 起動スクリプト（本番/ペーパー分離）

- monitoring/
  - monitoring_db.py : SQLite schema 初期化・永続化層
  - system_monitor.py : システム状態・データ鮮度監視
  - trade_monitor.py : （注文の滞留・約定異常などを検出するモジュール）
  - risk_monitor.py : ドローダウン・ポジション上限監視
  - kill_switch.py : フラグファイルによる停止判定
  - monitoring_engine.py : 各 Monitor を束ねるエンジン
  - alert_manager.py : 通知（LINE 等）管理（注: 実装の有無はリポジトリに依存）

- execution/
  - execution_engine.py : ExecutionEngine（セッション制御・注文フロー）
  - order_manager.py, order_repository.py, reconciler.py, risk_manager.py, broker_factory.py など

- portfolio/
  - portfolio_builder.py : 候補選定・重み計算
  - position_sizing.py : 株数決定・キャップ・スケーリング
  - risk_adjustment.py : セクター制限・レジーム乗数

- research/
  - factor_research.py : モメンタム・ボラ・バリューファクター計算（DuckDB）
  - feature_exploration.py : 将来リターン計算、IC、統計サマリ

- ai/
  - news_nlp.py : ニュースの LLM センチメント解析・ai_scores 書き込み
  - regime_detector.py : マクロ + ETF MA を使ったレジーム判定

- data/
  - (実行中に生成される SQLite / DuckDB ファイルや flag/pid ファイルを格納する想定ディレクトリ)
  - stop_requested.flag, kill.flag, execution.pid など

- tools/
  - paper_verification_report.py : ペーパートレード検証レポート生成スクリプト

注意事項・運用上のヒント
-----------------------
- 本番環境 (KABUSYS_ENV=live) では KILL_FLAG_CLEAR_ON_START を 0 に設定することを推奨します（誤って Kill Switch をクリアしないようにするため）。
- OpenAI を用いる機能は API キーが必須です。未設定だと例外を投げます（score_news / score_regime 等）。
- .env はセキュアな情報を含むため絶対にリポジトリにコミットしないでください（config_setup でも注意文が出ます）。
- DuckDB / SQLite のパスはデフォルトで data/ 以下に置かれます。ジョブユーザに書き込み権限があることを確認してください。
- Windows / POSIX でのプロセス優先度設定は kabusys.utils.process_priority が吸収しますが、権限不足で設定が失敗する場合があります（警告ログが出ます）。

ライセンス / 貢献
-----------------
- 本プロジェクトのライセンス情報・貢献ルールはリポジトリのトップレベルにある LICENSE / CONTRIBUTING を参照してください（存在しない場合はリポジトリ管理者へ問い合わせてください）。

付録 — よく使うコマンド例
-------------------------
- .env 作成:
  - python -m kabusys.config_setup

- 設定検証:
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- 監視起動:
  - MONITOR_POLL_INTERVAL=60 python -m kabusys.run_monitoring

- 実行エンジン起動:
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution

- ペーパートレード検証レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

以上。必要であれば README に含めたい追加情報（例: 実行フロー図、各テーブルスキーマ、CI 手順など）を指定してください。