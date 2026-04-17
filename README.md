KabuSys — 日本株自動売買システム
================================

このリポジトリは日本株自動売買システム「KabuSys」の主要モジュール群を含みます。
README ではプロジェクト概要、機能、セットアップ手順、基本的な使い方、主要ディレクトリ構成を日本語でまとめています。

プロジェクト概要
---------------
KabuSys は日本株の戦略・発注・監視・リスク管理・リサーチを含む自動売買フレームワークです。
主な設計方針：
- 本番 DB とペーパートレード DB を分離（KABUSYS_ENV による切替）
- DuckDB を使った分析（prices_daily / raw_financials など）
- SQLite を使った監視ログ（monitoring.db）とペーパートレード履歴（paper_trading.db）
- LLM（OpenAI）を使ったニュース NLP / 市場レジーム判定（オプション）
- Kill Switch（flag ファイル）による安全停止機構
- 実運用を想定したモジュール分割・冪等処理・フェイルセーフ設計

主な機能一覧
-------------
- 実行エンジン（ExecutionEngine 起動スクリプト run_execution.py）
  - 実際の発注（live）またはモック発注（paper_trading）をサポート
  - RiskManager / OrderManager / Reconciler 等を組み合わせてセッション運用
- 監視（Monitoring）
  - SystemMonitor: CPU/MEM/DISK・データ鮮度・プロセス生存監視
  - TradeMonitor: 滞留注文・約定価格異常の検出
  - RiskMonitor: ドローダウン・ポジション上限の監視と通知ログ
  - MonitoringEngine によるポーリングループ
  - KillSwitch による停止フラグ（data/kill.flag）操作
- ポートフォリオ構築
  - 候補選定、等金額/スコア加重の重み計算（portfolio_builder）
  - セクター上限適用・レジーム乗数（risk_adjustment）
  - ポジションサイズ計算（position_sizing）
- リサーチ
  - ファクター計算（momentum / volatility / value）
  - 将来リターン計算、IC（Information Coefficient）解析、統計サマリー
- AI（OpenAI）を使った拡張（任意）
  - news_nlp: ニュースを LLM でスコアリングして ai_scores テーブルへ書き込み
  - regime_detector: マクロニュース＋ETF MA で市場レジーム判定
- ツール
  - paper_verification_report: ペーパートレード DB を使った検証レポート作成
- 設定ユーティリティ
  - config_setup: 対話式 .env 作成ウィザード
  - validate_config: 環境・設定ファイルの事前検証 CLI

動作前提（推奨）
----------------
- Python 3.10 以上（typing の | 表記などを利用）
- 必要パッケージ（例）:
  - duckdb
  - psutil
  - openai (AI 機能を使う場合)
  - PyYAML（validate_config の YAML 検証を行う場合に必要）
- SQLite（標準ライブラリ）
- 環境変数は .env / .env.local / OS 環境変数から読み込み（自動ロード）

セットアップ手順
----------------

1. リポジトリをクローンして作業ディレクトリへ移動
   - 例: git clone ... && cd <project_root>

2. Python 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate（Windows: .venv\Scripts\activate）

3. 必要パッケージをインストール
   - pip install duckdb psutil openai
   - validate_config の YAML 検証を使う場合: pip install pyyaml

4. .env の準備
   - 対話式ウィザード:
     - python -m kabusys.config_setup
   - 手動で作成する場合、最低限以下を設定してください（例）:
     - JQUANTS_REFRESH_TOKEN=your_token_here
     - KABU_API_PASSWORD=your_kabu_password
     - KABUSYS_ENV=development  # development | paper_trading | live
     - DUCKDB_PATH=data/kabusys.duckdb
     - SQLITE_PATH=data/monitoring.db
     - LOG_LEVEL=INFO
     - OPENAI_API_KEY=sk-xxxx (AI 機能を使用する場合)
   - .env の自動ロード:
     - プロジェクトルートが .git または pyproject.toml を含む場合、起動時に自動で .env を読み込みます。
     - 自動ロードを無効にする: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

5. 設定検証（任意だが推奨）
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗（exit 1）として扱います:
     - python -m kabusys.validate_config --strict

基本的な使い方
--------------

- 実行エンジンを起動（実運用／ペーパー切替は KABUSYS_ENV で制御）
  - python -m kabusys.run_execution
  - ペーパートレード実行時、KABUSYS_ENV=paper_trading にすると MockBroker を使い、
    デフォルトで data/paper_trading.db に記録され、本番 DB と分離されます。

- 監視ループの起動
  - python -m kabusys.run_monitoring
  - ポーリング間隔を環境変数で上書き:
    - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
    - デフォルトは 60 秒
  - run_monitoring は常に本番 sqlite_path を使用して監視テーブルを操作します（環境に依存しない）。

- 停止・Kill 機能
  - 実行エンジンを停止させたい場合、data/kill.flag を作成すると KillSwitch により停止されます。
  - run_* スクリプトは data/stop_requested.flag を監視し、それが存在するとループを終了します。
  - kill.flag のクリアは Settings.kill_flag_clear_on_start による自動クリアの設定が可能（本番では 0 を推奨）。

- ペーパートレード検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db /path/to/paper_trading.db
    - 省略時は環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db を使用

- AI 機能（任意）
  - OPENAI_API_KEY を設定することで kabusys.ai.news_nlp.score_news や kabusys.ai.regime_detector.score_regime を利用できます。
  - LLM 呼び出しは失敗時にフェイルセーフ（スコア 0.0 等）で継続する実装です。

主要な環境変数（抜粋）
---------------------
- 必須
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- 任意 / デフォルトあり
  - KABUSYS_ENV (development | paper_trading | live) — default: development
  - DUCKDB_PATH — default: data/kabusys.duckdb
  - SQLITE_PATH — default: data/monitoring.db
  - PAPER_TRADING_SQLITE_PATH — default: data/paper_trading.db
  - LOG_LEVEL — default: INFO
  - MONITOR_POLL_INTERVAL — default: 60 (run_monitoring のポーリング間隔)
  - OPENAI_API_KEY — OpenAI を使う場合に必要
  - PAPER_FILL_MODE — paper_trade のモック約定挙動（instant|partial|never|reject）
  - KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか (0/1)
  - PID_FILE_PATH, KILL_FLAG_PATH — 各種ファイルパス（デフォルト: data/*）

ディレクトリ構成（主要ファイル）
------------------------------
以下はリポジトリ内の主要モジュール／ファイルです（抜粋）。

- src/kabusys/
  - __init__.py
  - config.py                 # 環境変数読み込み・Settings クラス
  - config_setup.py           # .env 対話式ウィザード
  - validate_config.py        # 設定検証 CLI
  - run_execution.py          # ExecutionEngine 起動スクリプト
  - run_monitoring.py         # SystemMonitor ポーリング起動スクリプト
  - utils/
    - process_priority.py     # プロセス優先度・CPU affinity ユーティリティ
  - monitoring/
    - monitoring_db.py        # SQLite 永続化層
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py        # （ファイル冒頭のみ、アラート送信ロジック）
  - execution/                 # 発注関連（OrderManager, ExecutionEngine 等）
    - order_manager.py
    - order_repository.py
    - execution_engine.py
    - broker_factory.py
    - reconciler.py
    - risk_manager.py
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

運用上の注意点
--------------
- 本番（KABUSYS_ENV=live）での起動前に必ず validate_config を実行して設定を確認してください。
- .env ファイルは機密情報を含むため Git にコミットしないでください（config_setup でも警告あり）。
- Kill Switch（data/kill.flag）の自動クリア設定は本番では無効（0）を推奨します。
- OpenAI API キーを使う際は API 使用量・レスポンスの信頼性に留意してください（LLM の応答を検証する仕組みがありますが、過信は禁物です）。
- psutil によるプロセス優先度変更や cpu_affinity 設定は OS と権限に依存します。失敗した場合はログに警告が出ますが処理は継続します。

開発／拡張のヒント
-------------------
- DuckDB 接続を引数で受ける設計のため、research モジュールはテストしやすくなっています。
- AI 呼び出し部分（_call_openai_api）や LLM レスポンス処理はテストでモック化しやすいよう分離されています。
- monitoring_db.init_monitoring_db は冪等でテーブル・カラムのマイグレーションを含むので、本番 DB を破壊しないよう注意して使用してください。

サンプルコマンドまとめ
--------------------
- .env の作成（ウィザード）
  - python -m kabusys.config_setup
- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict
- 実行エンジン起動
  - python -m kabusys.run_execution
- 監視起動
  - python -m kabusys.run_monitoring
- ペーパートレード検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- 個別モジュール実行（例: research）
  - Python REPL 上で import して関数を直接呼び出して検証可能

ライセンス・貢献
----------------
（該当する場合、ここにライセンス情報・コントリビュート方法を記載してください。README にない場合はプロジェクトルートの LICENSE を参照してください。）

---
この README はコードベースの公開ソースに基づき作成しています。追加の要望（例：より詳細な API ドキュメント、ER 図、実行フローチャートなど）があれば教えてください。