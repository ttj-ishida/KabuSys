KabuSys — 日本株自動売買システム
================================

本リポジトリは日本株の自動売買・研究・監視を目的としたモジュール群です。
主要コンポーネントは実行エンジン（ExecutionEngine）、監視（Monitoring）、
ポートフォリオ構築・サイズ決定、ファクター計算、LLM を利用したニュース NLP などを含みます。

この README ではプロジェクト概要、主な機能、セットアップ手順、使い方、ディレクトリ構成を日本語で説明します。

プロジェクト概要
----------------
- 自動売買のコアロジック（ExecutionEngine 等）と、監視・リスク管理（Monitoring）、
  研究用モジュール（ファクター計算・特徴量解析）、および AI を用いたニュースセンチメント評価を提供します。
- SQLite / DuckDB をデータ永続化に使用。paper_trading（ペーパートレード）モードでは本番 DB と分離された専用 DB を使用します。
- OpenAI（gpt-4o-mini 等）を用いたニュース解析・レジーム判定機能を備えています（APIキーが必要）。

主な機能一覧
-------------
- 起動スクリプト
  - run_execution.py: ExecutionEngine を起動（KABUSYS_ENV による paper/live 切替）
  - run_monitoring.py: SystemMonitor をポーリングして監視データを記録
- 設定・検証
  - config_setup.py: .env を対話式に作成/更新するウィザード
  - validate_config.py: .env と config/*.yaml の起動前チェック
  - config.py: 環境変数の解決ロジック（自動 .env ロード、Settings クラス）
- 監視（monitoring）
  - system_monitor.py, trade_monitor.py（一覧はコード参照）: システム状態・注文挙動の監視
  - risk_monitor.py: ドローダウン・ポジション上限などリスク監視
  - kill_switch.py: 条件に応じて data/kill.flag を書き込み ExecutionEngine を停止
  - monitoring_db.py: SQLite によるテーブル定義・永続化ロジック
  - monitoring_engine.py: 各 Monitor を束ねるポーリングエンジン
- 実行（execution）
  - ExecutionEngine 周り（ブローカーファクトリ、OrderManager, RiskManager, Reconciler 等）
  - paper_trading では MockBrokerClient を使用し data/paper_trading.db に記録（本番 DB 分離）
- ポートフォリオ（portfolio）
  - 候補選定、重み計算（等金額/スコア加重）、単元丸め、セクターキャップ、レジーム乗数など
- 研究（research）
  - calc_momentum / calc_volatility / calc_value：DuckDB を用いたファクター計算
  - feature_exploration：将来リターン計算、IC（Information Coefficient）等
- AI（ai）
  - news_nlp.py：raw_news を集約して OpenAI に投げ、銘柄ごとのセンチメントを ai_scores に保存
  - regime_detector.py：ETF の MA 乖離とマクロニュースでレジーム判定
- ユーティリティ
  - logging_setup.py：stdout + 日次ローテーションログ設定
  - process_priority.py：プロセス優先度 / CPU affinity 設定ユーティリティ
- ツール
  - tools/paper_verification_report.py：Paper Trading の検証レポート生成

セットアップ手順
----------------

1. リポジトリをクローン
   - 例: git clone <repo-url>

2. Python 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 必要なパッケージをインストール
   - requirements.txt がある場合はそれを使う想定です。主要依存例:
     - duckdb
     - psutil
     - openai
     - PyYAML（config YAML 検証で任意）
   - 例:
     - pip install duckdb psutil openai PyYAML

4. .env の準備（対話式ウィザード推奨）
   - python -m kabusys.config_setup
   - ウィザードは J-Quants トークンや kabu API パスワード、DB パス、KABUSYS_ENV 等を作成します。
   - 生成された .env は絶対に Git にコミットしないでください。

5. 設定検証
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗として扱います。

6. データディレクトリ・DB
   - デフォルトの DB パス:
     - DuckDB: data/kabusys.duckdb
     - SQLite (monitoring): data/monitoring.db
     - Paper trading DB: data/paper_trading.db（KABUSYS_ENV=paper_trading 時に使用）
   - 必要に応じて .env の DUCKDB_PATH / SQLITE_PATH / PAPER_TRADING_SQLITE_PATH を設定してください。

重要な環境変数（抜粋）
--------------------
- 必須
  - JQUANTS_REFRESH_TOKEN: J-Quants API のリフレッシュトークン
  - KABU_API_PASSWORD: kabuステーション API のパスワード
- 実行環境
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- DB / ログ
  - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
  - SQLITE_PATH (デフォルト: data/monitoring.db)
  - PAPER_TRADING_SQLITE_PATH (デフォルト: data/paper_trading.db)
  - LOG_LEVEL (デフォルト: INFO)
  - LOG_DIR (デフォルト: logs/)
- AI
  - OPENAI_API_KEY: OpenAI API キー（ai.news_nlp, ai.regime_detector で使用）
- 監視
  - MONITOR_POLL_INTERVAL: run_monitoring のポーリング秒数（デフォルト: 60）
  - PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START 等（Settings 参照）
- テスト用
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1: 自動 .env ロードを無効化

使い方（実行例）
----------------

1. 実行エンジン（Engine）を起動
   - python -m kabusys.run_execution
   - 説明:
     - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、paper_trading 用 DB に記録します。
     - 起動前に data/stop_requested.flag が存在すると起動をスキップします。
     - 実行中に data/stop_requested.flag が作成されるとエンジン停止をトリガーします。

2. 監視ループを起動
   - python -m kabusys.run_monitoring
   - 説明:
     - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書きできます（デフォルト 60 秒）。
     - 監視は本番 sqlite_path を使用（環境にかかわらず同じ監視 DB を参照）します。
     - data/stop_requested.flag を検知するとループを終了します。

3. Paper Trading 検証レポートの生成
   - python -m kabusys.tools.paper_verification_report
   - 期間指定例:
     - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
   - --db オプションで SQLite パスを指定できます（環境変数 PAPER_TRADING_SQLITE_PATH も可）。

4. 設定検証（再掲）
   - python -m kabusys.validate_config
   - 起動前に必ず実行して環境変数や config/*.yaml の不足をチェックしてください。

ファイル / フラグの意味（運用ノート）
-----------------------------------
- data/stop_requested.flag
  - 実行スクリプト（run_monitoring / run_execution）はこのファイルを検知して安全に停止します。
- data/kill.flag
  - KillSwitch（リスク異常時）により作成され、ExecutionEngine に停止シグナルを送るために使用されます。
- data/execution.pid
  - ExecutionEngine の PID ファイルパス（Settings.pid_file_path による設定）。

ログ
----
- ログは stdout にも出力され、ファイルは logs/<app_name>.log に日次ローテーションで保存されます。
- logging_setup.setup_logging() が各起動スクリプトで使用されます。
- ログレベルは環境変数 LOG_LEVEL または setup_logging の引数で制御します。

ディレクトリ構成
----------------
（主要なファイル・モジュールを抜粋したツリー）
- src/
  - kabusys/
    - __init__.py
    - config.py
    - config_setup.py
    - validate_config.py
    - run_execution.py
    - run_monitoring.py
    - tools/
      - __init__.py
      - paper_verification_report.py
    - utils/
      - __init__.py
      - logging_setup.py
      - process_priority.py
    - monitoring/
      - monitoring_db.py
      - system_monitor.py
      - trade_monitor.py
      - risk_monitor.py
      - kill_switch.py
      - monitoring_engine.py
      - alert_manager.py
    - execution/   (ExecutionEngine, OrderManager, BrokerFactory, RiskManager 等)
      - execution_engine.py
      - order_manager.py
      - order_repository.py
      - broker_factory.py
      - reconciler.py
      - risk_manager.py
    - portfolio/
      - __init__.py
      - portfolio_builder.py
      - position_sizing.py
      - risk_adjustment.py
    - research/
      - __init__.py
      - factor_research.py
      - feature_exploration.py
    - ai/
      - __init__.py
      - news_nlp.py
      - regime_detector.py
    - data/ (期待される実行時データディレクトリ: DB や flagファイル)
    - config/ (YAML 設定ファイル群: system_config.yaml 等)

補足・運用上の注意
-----------------
- Paper Trading と本番 DB は分離する設計です。KABUSYS_ENV=paper_trading を使って運用してください。
- OpenAI の利用には API キー（OPENAI_API_KEY）が必要です。課金・レート制限に注意してください。
- process_priority.set_process_priority() が起動時に呼ばれます。実行環境によっては権限不足で警告が出ますが、継続します。
- .env の自動読み込みはデフォルトで有効です。テストや特殊用途で自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB / SQLite の接続は明示的に close されますが、バックアップや永続化の運用方針は運用者で定めてください。

開発・テスト
-------------
- 単体関数群（portfolio、research など）は副作用を持たない純粋関数として設計されているため、ユニットテストが書きやすいです。
- news_nlp や regime_detector の外部 API 呼び出しはラップ関数をモックしてテスト可能です（コード内にモック指定のコメントあり）。
- validate_config.py は起動前に設定不備を自動検出するため CI に組み込むことを推奨します。

ライセンス・貢献
----------------
- （ここにライセンスや貢献ガイドラインを追記してください）

問題・問い合わせ
-----------------
- 実装上の疑問点やバグは Issue を立ててください。README に書かれていない詳細な実装仕様はソース内の docstring を参照してください。

以上。まずは .env を作成（python -m kabusys.config_setup）→ 設定検証（python -m kabusys.validate_config）→ 監視・実行スクリプトを起動（python -m kabusys.run_monitoring / python -m kabusys.run_execution）で運用開始できます。