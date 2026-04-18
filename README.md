# KabuSys

日本株向け自動売買システムの一部（ライブラリ / 起動スクリプト / ユーティリティ群）。

このリポジトリは取引エンジン（ExecutionEngine）、監視（Monitoring）、ポートフォリオ構築・リスク管理、ファクター計算、LLM を使ったニュース/NLP モジュールなどを含みます。各コンポーネントはモジュール化されており、.env による設定で動作を切り替えられます。

注意: 本 README はソースコードをベースにした説明です。実運用前に必ず設定の検証・テストを行ってください。

主な特徴
- ExecutionEngine 起動スクリプト（本番 / ペーパートレードを環境で切替）
- 監視プロセス（SystemMonitor / TradeMonitor / RiskMonitor を束ねた MonitoringEngine）
- 環境設定ウィザード（.env の対話的作成）
- 設定検証 CLI（.env と config/*.yaml のチェック）
- Paper Trading 検証レポート生成ツール
- ポートフォリオ構築、ポジションサイズ計算、セクター制約、レジーム判定（LLM 統合）
- DuckDB / SQLite を使ったデータ参照・永続化
- ログの統一設定（コンソール + 日次ローテーションファイル）

必須 / 主要機能一覧
- 設定関連
  - config_setup: .env を対話的に作成・更新
  - validate_config: 設定（環境変数・YAML）検証 CLI
- 実行 / 監視
  - run_execution: ExecutionEngine を起動（KABUSYS_ENV により paper_trading でモックブローカー）
  - run_monitoring: SystemMonitor のポーリングループ起動（MONITOR_POLL_INTERVAL で間隔変更可）
  - kill.flag / stop_requested.flag による外部停止制御
- 解析 / 研究
  - research: ファクター計算（momentum/value/volatility）、IC 計算等
  - ai: ニュース NLP（OpenAI）によるセンチメント集計、レジーム検出
- ユーティリティ
  - tools.paper_verification_report: Paper Trading の検証レポート生成

前提（推奨）
- Python 3.10+
- 必要パッケージ（例）
  - duckdb
  - psutil
  - openai
  - PyYAML（config YAML 検証を行う場合）
インストール例（仮の requirements がない場合の例）:
  pip install duckdb psutil openai PyYAML

セットアップ手順

1. リポジトリをクローン / 展開
   - 任意のディレクトリにコードを配置します。プロジェクトルートは .git または pyproject.toml を基準に自動検出されます。

2. Python 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - pip install duckdb psutil openai PyYAML

4. .env を作成する
   - 対話的ウィザードを使用（推奨）:
     python -m kabusys.config_setup
   - または手動でプロジェクトルートに `.env` を作成（.env.example を参考に）:
     例（最低限の必須項目）:
     ```
     JQUANTS_REFRESH_TOKEN=your_jquants_token_here
     KABU_API_PASSWORD=your_kabu_password_here
     KABUSYS_ENV=development
     DUCKDB_PATH=data/kabusys.duckdb
     SQLITE_PATH=data/monitoring.db
     LOG_LEVEL=INFO
     KILL_FLAG_CLEAR_ON_START=0
     ```
   - 注意: `JQUANTS_REFRESH_TOKEN`, `KABU_API_PASSWORD` は必須です。`.env` は Git にコミットしないでください。

5. 設定の検証
   - python -m kabusys.validate_config
   - 警告もエラー扱いにする場合:
     python -m kabusys.validate_config --strict

使い方（主要コマンド）

- ExecutionEngine を起動（本番 / ペーパー切替は KABUSYS_ENV）
  - デフォルト（KABUSYS_ENV による）:
    python -m kabusys.run_execution
  - メモ:
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用して paper_trading 用 DB（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）に記録します。
    - ExecutionEngine は data/execution.pid（デフォルト）に PID ファイルを書きます。
    - data/stop_requested.flag が存在すると起動しない / 既存スレッドを停止します。

- Monitoring を起動（SystemMonitor のポーリングループ）
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）
  - 監視プロセスは MonitoringDB（SQLite）へ永続化します
  - 監視は KABUSYS_ENV の値に関わらず本番 sqlite_path を参照します（監視ログは本番 DB を使う想定）

- 設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告も失敗扱いで exit(1)

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB パス指定:
    python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
  - 環境変数 PAPER_TRADING_SQLITE_PATH でも DB を指定可能

- ai モジュール（プログラム内で呼び出し）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
    - raw_news / news_symbols / ai_scores に基づき OpenAI でスコアリングして ai_scores に書き込む
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
    - ETF 1321 の MA200 とマクロニュースからレジームを判定し market_regime に書き込む

重要な環境変数（抜粋）
- 必須
  - JQUANTS_REFRESH_TOKEN — J-Quants API 用リフレッシュトークン（必須）
  - KABU_API_PASSWORD — kabuステーション API パスワード（必須）
- 選択 / 主要
  - KABUSYS_ENV — 実行環境: development / paper_trading / live（デフォルト: development）
  - DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH — paper_trading 用 SQLite（デフォルト: data/paper_trading.db）
  - LOG_LEVEL — ログレベル（DEBUG/INFO/...、デフォルト INFO）
  - LOG_DIR — ログファイル保存先（デフォルト logs/）
  - OPENAI_API_KEY — OpenAI API キー（ai モジュールで使用）
  - MONITOR_POLL_INTERVAL — run_monitoring のポーリング秒数（デフォルト 60）
  - KILL_FLAG_PATH — kill.flag のパス（デフォルト data/kill.flag）
  - PID_FILE_PATH — Execution PID ファイルパス（デフォルト data/execution.pid）
  - KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（0/1、default 0）

運用上の注意
- run_monitoring は監視ログに関して「常に本番 sqlite_path を使用する」実装のため、環境変数にかかわらず監視ログは production DB を参照する点に注意してください。
- run_execution は KABUSYS_ENV=paper_trading のとき paper 用 DB を使い、本番 DB と分離されます。
- 停止方法:
  - プロセス内のポーリングループは data/stop_requested.flag の存在を検知して終了します（run_monitoring / run_execution の挙動）。
  - KillSwitch（kill.flag）を書き込むと ExecutionEngine に停止シグナルを送ります（監視 > kill 評価ロジックにより書き込まれます）。
- ログ:
  - logs/<app_name>.log に日次ローテーションで出力されます（デフォルト logs/、30 日保持）。
  - コンソールは stdout に出力されます。

ディレクトリ構成（主要ファイル）
- config/
  - system_config.yaml, data_config.yaml, strategy_config.yaml, risk_config.yaml, execution_config.yaml, monitoring_config.yaml
- data/
  - monitoring.db (デフォルト SQLite)
  - paper_trading.db (paper_trading 用, デフォルト)
  - execution.pid, kill.flag, stop_requested.flag などの制御ファイル
- logs/
  - execution.log, monitoring.log, ...（デフォルト）
- src/kabusys/
  - __init__.py
  - config.py — 環境変数読み込み・Settings
  - config_setup.py — .env ウィザード
  - validate_config.py — 設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor ポーリング起動スクリプト
  - utils/
    - logging_setup.py — ログ設定ユーティリティ
    - process_priority.py — プロセス優先度設定
  - monitoring/
    - monitoring_db.py — SQLite 永続化層
    - system_monitor.py, trade_monitor.py, risk_monitor.py, monitoring_engine.py, kill_switch.py, alert_manager.py (監視関連)
  - execution/ (ExecutionEngine 関連モジュール)
  - portfolio/ (選定・配分・リスク調整・ポジションサイズ)
  - research/ (factor_research, feature_exploration)
  - ai/
    - news_nlp.py — ニュースセンチメントスコアリング（OpenAI）
    - regime_detector.py — 市場レジーム判定（MA200 + マクロニュース）
  - tools/
    - paper_verification_report.py — Paper Trading レポート生成

簡易ツリー例
src/
  kabusys/
    __init__.py
    config.py
    config_setup.py
    validate_config.py
    run_execution.py
    run_monitoring.py
    utils/
      logging_setup.py
      process_priority.py
    monitoring/
      monitoring_db.py
      system_monitor.py
      risk_monitor.py
      kill_switch.py
      monitoring_engine.py
    ai/
      news_nlp.py
      regime_detector.py
    portfolio/
      portfolio_builder.py
      position_sizing.py
      risk_adjustment.py
    research/
      factor_research.py
      feature_exploration.py
    tools/
      paper_verification_report.py

よくある運用フロー（例）
1. .env を作成（python -m kabusys.config_setup）
2. 設定検証（python -m kabusys.validate_config）
3. 監視プロセス起動（本番環境では常駐）
   - python -m kabusys.run_monitoring
4. 実行エンジン起動（マーケット営業日に起動）
   - python -m kabusys.run_execution
5. Paper Trading の検証や AI スコアリングは順次ジョブとして実行

トラブルシューティング / 開発メモ
- config/*.yaml の構造検証には PyYAML が必要です。インストールしていない場合、validate_config は YAML 検証をスキップして警告を出します。
- ログディレクトリ作成に失敗するとファイルハンドラは無効化され、コンソールのみ出力になります（警告が stderr に出ます）。
- psutil の権限によりプロセス優先度設定や CPU affinity の設定が失敗することがあります（権限不足は警告でスキップされます）。

ライセンス / バージョン
- パッケージバージョンは src/kabusys/__init__.py の __version__ を参照してください（例: 0.1.0）。

この README はコードベースの短い導入ドキュメントです。各モジュールの詳細や API（関数引数・戻り値など）は、ソースコード内の docstring を参照してください。追加でサンプル設定や運用手順（systemd / supervisor 用 unit、Dockerfile 等）が必要であればお知らせください。