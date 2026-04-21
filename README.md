# KabuSys — 日本株自動売買システム

このリポジトリは、日本株向けの自動売買システム「KabuSys」のコードベースです。  
本 README ではプロジェクト概要、主要機能、セットアップ手順、基本的な使い方、およびディレクトリ構成を日本語でまとめます。

---

## プロジェクト概要

KabuSys は以下の主要機能を組み合わせて自動売買ワークフローを実現します：

- 戦略（ファクター計算、特徴量解析）に基づく銘柄選定と配分（portfolio モジュール）
- 注文発行・管理・再整合（execution モジュール）
- システム稼働・注文・リスク監視（monitoring モジュール）
- ニュースの NLP によるセンチメント（AI モジュール）や市場レジーム判定
- Paper Trading（シミュレーション）モードに対応（本番 DB と分離）
- 運用支援ツール（.env ウィザード、設定検証、検証レポート等）

設計方針として、DB（DuckDB/SQLite）を使った分析・ログ保存、OpenAI（任意）の利用、プラットフォーム差分を吸収するユーティリティ群を提供します。

---

## 主な機能一覧

- portfolio
  - 銘柄候補の選定（select_candidates）
  - 等金額／スコア重み配分（calc_equal_weights, calc_score_weights）
  - ポジションサイジング（calc_position_sizes）
  - セクター上限やレジーム乗数（apply_sector_cap, calc_regime_multiplier）

- research
  - モメンタム・ボラティリティ・バリュー等のファクター計算（DuckDB を利用）
  - 将来リターン計算・IC（Information Coefficient）等の解析

- execution
  - ブローカークライアント抽象化（本番 or Mock）
  - ExecutionEngine（発注セッションの起動 / 停止）
  - RiskManager / OrderManager / Reconciler（発注・再整合・リスク管理）

- monitoring
  - SystemMonitor / TradeMonitor / RiskMonitor を束ねる MonitoringEngine
  - SQLite に監視ログを書き込む monitoring_db（system_status, trade_logs, risk_logs, positions, dashboard）
  - KillSwitch（条件に応じて data/kill.flag を書いて ExecutionEngine を停止）

- ai
  - news_nlp: OpenAI を用いたニュースの銘柄別センチメント算出（ai_scores 保存）
  - regime_detector: ETF + マクロニュースを使った市場レジーム判定

- tools
  - paper_verification_report: ペーパートレード DB からレポートを生成（稼働率、注文成功率、レイテンシ等）

- utils
  - logging_setup: 統一ロギング（コンソール + 日次ローテートファイル）
  - process_priority: プロセス優先度 / CPU affinity の簡便 API
  - config: .env 読み込みロジックと Settings クラス
  - config_setup: 対話式 .env 生成ウィザード
  - validate_config: 起動前の設定検証 CLI

---

## セットアップ手順（ローカル開発向け）

1. Python 環境（推奨: 3.10+）を用意し、仮想環境を作成・有効化します。
   - 例:
     - python -m venv .venv
     - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要依存パッケージをインストールします（最低限の例）。
   - 例:
     - pip install duckdb psutil openai
     - 監証用に PyYAML を使う (任意): pip install pyyaml

   ※ requirements.txt がない場合は実行時の ImportError を参照して追加してください。

3. プロジェクトルートに .env を用意します。
   - 対話的に作成する:
     - python -m kabusys.config_setup
   - 既存の .env を手動で用意する場合は .env.example を参考に設定します（リポジトリに例があれば）。

4. 設定を検証します:
   - python -m kabusys.validate_config
   - 警告も失敗にしたい場合:
     - python -m kabusys.validate_config --strict

5. DB ファイル（data/…）は起動時に自動作成されることが多いですが、DuckDB 用ファイルや paper_trading 用 SQLite が明示的に必要な場合は .env のパスを確認してください。

---

## 必須 / 代表的な環境変数

必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

重要（デフォルトあり）:
- KABUSYS_ENV: development | paper_trading | live（default: development）
  - paper_trading の場合は MockBroker を使用し、paper_trading 専用 DB に記録されます
- DUCKDB_PATH: DuckDB ファイルパス（default: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（default: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（default: data/paper_trading.db）
- LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL（default: INFO）
- OPENAI_API_KEY: OpenAI API を利用する場合に必須（news_nlp / regime_detector）

その他:
- PAPER_FILL_MODE: instant | partial | never | reject（paper_trading のフィルモード）
- PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START
- LOG_DIR: ログの保存先ディレクトリ
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）

.env の自動読み込み:
- デフォルトでプロジェクトルートの .env / .env.local を読み込みます。自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## 使い方（主要スクリプト）

- 環境設定ウィザード（.env 作成 / 更新）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告もエラー扱いになります

- 実行エンジン起動（ExecutionEngine）
  - python -m kabusys.run_execution
  - 挙動:
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、paper_trading 専用 DB に記録します（本番 DB と完全分離）。
    - 起動前に data/stop_requested.flag があると起動せず終了します。
    - 実行中に data/stop_requested.flag を作成するとエンジン停止を試みます。
    - 実行中は data/execution.pid に PID を書きます（設定により変更可）。

- 監視ループ起動（SystemMonitor）
  - python -m kabusys.run_monitoring
  - 挙動:
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で上書き可能（デフォルト 60 秒）
    - monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path（SQLITE_PATH）を使用して監視ログを保存します
    - data/stop_requested.flag が作成されると監視ループが終了します

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report --from YYYY-MM-DD --to YYYY-MM-DD
  - オプション --db で DB パスを指定可能（環境変数 PAPER_TRADING_SQLITE_PATH より優先）

- AI（ニュース NLP / レジーム判定）
  - 実行には OPENAI_API_KEY が必要です（引数で渡す API キーも可）。
  - news_nlp (kabusys.ai.score_news) は DuckDB 接続を受け取り、raw_news / news_symbols / ai_scores を操作します。
  - regime_detector.score_regime を利用して市場レジーム判定を行い、market_regime テーブルへ書き込みます。

- ログ設定
  - 全起動スクリプトは共通の setup_logging を呼び出します。
  - デフォルトで stdout 出力 + logs/<app_name>.log 日次ローテーション（30 日分保管）

---

## 運用上の注意

- Kill Switch
  - RiskMonitor が条件を満たすと KillSwitch が data/kill.flag を書き、ExecutionEngine に停止シグナルを送ります。
  - 本番で KILL_FLAG_CLEAR_ON_START=1 は危険（自動クリアされるため）なので注意。

- Paper Trading
  - paper_trading モードでは paper_trading 専用 DB（PAPER_TRADING_SQLITE_PATH）に完全に分離して記録します。実発注は行いません（MockBrokerClient）。

- DB マイグレーション
  - monitoring_db.init_monitoring_db は冪等的にテーブルを作成し、既存 DB に対する簡易マイグレーション（カラム追加）を行います。

- OpenAI 利用
  - API の失敗時はフェイルセーフでスコアにフォールバックする設計（例: macro_sentiment=0.0 など）。ただし、キー未設定時はエラーになります。

---

## ディレクトリ構成（主要ファイル）

（src/kabusys 配下を抜粋）

- src/kabusys/
  - __init__.py
  - config.py ....................... 環境変数/Settings 管理（.env 自動読み込み含む）
  - config_setup.py ................ .env 対話式ウィザード
  - validate_config.py ............. 起動前の設定検証 CLI
  - run_execution.py ............... ExecutionEngine 起動スクリプト
  - run_monitoring.py .............. SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py ... ペーパートレード検証レポート生成
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
    - __init__.py
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py         (実装あり）
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py (実装あり）
  - utils/
    - logging_setup.py
    - process_priority.py
  - execution/ (発注関連コンポーネント)
    - execution_engine.py
    - broker_factory.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
  - research/、portfolio/、ai/：戦略・解析・AI 関連の実装群

- data/  （運用時にログや DB、フラグファイルを配置する想定）
  - monitoring.db （デフォルト SQLITE_PATH）
  - paper_trading.db （PAPER_TRADING_SQLITE_PATH）
  - stop_requested.flag, kill.flag, execution.pid などのフラグ/制御ファイル

- logs/  （デフォルトのログ出力先）

---

## 例：よく使うコマンドまとめ

- .env 作成（ウィザード）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- ペーパートレード検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - または DB を指定: --db path/to/paper_trading.db

- 実行（paper_trading）
  - export KABUSYS_ENV=paper_trading
  - python -m kabusys.run_execution

- 監視ループ起動（ポーリング間隔を 30 秒にする例）
  - export MONITOR_POLL_INTERVAL=30
  - python -m kabusys.run_monitoring

- 停止
  - 監視/実行ループは data/stop_requested.flag の作成で停止させる仕組み（運用ツール等でフラグファイルを作成してください）。
  - リスクキルスイッチは data/kill.flag に理由を書き込みます。

---

## 開発者向け補足

- テストや CI では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を使って .env の自動読み込みを無効にできます。
- validate_config は PyYAML がインストールされていれば config/*.yaml の構文検査も行います（未インストール時はスキップして警告）。
- logging_setup は既存ハンドラをクリアしてから再設定するため、テスト時にロガーの構成を安定させやすくなっています。
- AI 関連の外部呼び出しはリトライ・バックオフや部分失敗時のフェイルセーフを組み込んでありますが、運用時は API 使用量やコストに注意してください。

---

もし README に追加したい具体的な項目（例: CI 設定、デプロイ例、API ドキュメント、ユニットテストの実行方法、requirements.txt）や、プロジェクトルートに含めるべきサンプル .env のテンプレートがあれば教えてください。必要に応じて追記します。