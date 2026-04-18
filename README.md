# KabuSys

日本株自動売買システム（軽量フレームワーク）  
この README はリポジトリ内の主要スクリプト・モジュールに基づき、導入・運用手順、機能一覧、ディレクトリ構成を日本語でまとめたものです。

注意: 本リポジトリは発注ロジック・AI 統合・監視機能などを含みます。本番（実際の発注）で使用する場合は設定・権限・運用ルールを十分に確認してください。

---
## プロジェクト概要
KabuSys は日本株の自動売買に必要な以下の要素を提供します:
- 戦略・ポートフォリオ構築（銘柄選定、配分、リスク調整、株数決定）
- ExecutionEngine（発注管理、オーダーマネージャ、リスク管理）
- Monitoring（システム稼働・データ鮮度・注文状況・リスク監視）
- AI モジュール（ニュース NLP によるセンチメント、レジーム判定）
- 開発用ユーティリティ（設定ウィザード、設定検証、ペーパートレード検証レポート）
- データ分析（DuckDB ベースでファクター計算やリサーチ）

主要な設計方針:
- 環境変数による設定（.env / .env.local 自動読み込み）
- paper_trading（ペーパートレード）と live（本番）を切り替え可能
- ロギング・プロセス優先度設定・Kill Switch による安全停止

---
## 主な機能一覧
- Settings 管理（env 値取得・妥当性チェック）
- config_setup: 対話式 .env 作成ウィザード（python -m kabusys.config_setup）
- validate_config: 起動前の設定検証 CLI（python -m kabusys.validate_config）
- Execution 起動スクリプト（python -m kabusys.run_execution）
  - paper_trading モードで MockBroker を利用し、本番 DB と分離
  - 停止フラグ（data/stop_requested.flag）/ PID 管理（data/execution.pid）
- Monitoring 起動スクリプト（python -m kabusys.run_monitoring）
  - SystemMonitor / TradeMonitor / RiskMonitor をポーリング
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）
- MonitoringDB: SQLite に監視ログ・トレードログ・ポジション・リスクログ・ダッシュボードを永続化
- KillSwitch: 条件（ドローダウン超過等）で data/kill.flag を書いて Execution を停止
- AI:
  - news_nlp.score_news: OpenAI を使ったニュースセンチメント -> ai_scores へ書き込み
  - regime_detector.score_regime: MA と LLM による市場レジーム判定
  - OpenAI キーが必要（OPENAI_API_KEY または引数で指定）
- tools:
  - paper_verification_report: ペーパートレード DB を解析して PASS/FAIL の検証レポートを生成
- portfolio モジュール:
  - 候補選定、重み計算、セクター制限、ポジションサイズ算出（丸め・上限・スケーリング）

---
## セットアップ手順（開発/運用の最小手順）
前提: Python 3.10+ 想定、必要なパッケージはプロジェクトの requirements に沿ってインストールしてください（DuckDB, psutil, openai, PyYAML など）。

1. リポジトリをチェックアウト
2. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 依存関係をインストール
   - pip install -r requirements.txt  （requirements.txt がない場合は主に duckdb, psutil, openai, pyyaml を入れる）
4. .env 作成（推奨: ウィザード）
   - python -m kabusys.config_setup
   - ウィザードは .env を生成します（.env は絶対に Git にコミットしないでください）
   - 自動ロード: .env / .env.local は Settings モジュールがプロジェクトルートを特定できた場合に起動時自動読み込みされます。自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。
5. 設定検証
   - python -m kabusys.validate_config
   - 警告を FAIL 扱いにする: python -m kabusys.validate_config --strict
6. データディレクトリ作成（必要に応じて）
   - デフォルト DB パス: data/kabusys.duckdb, data/monitoring.db, data/paper_trading.db
   - ログディレクトリ: logs/（デフォルト）
7. OpenAI を使う場合
   - OPENAI_API_KEY を .env に設定（ニュース NLP / レジーム判定で必要）
8. 起動前の注意
   - 本番モード KABUSYS_ENV=live の場合は設定を慎重に確認してください（LINE 通知設定、KILL_FLAG_CLEAR_ON_START 等）
   - Kill Switch 動作や PID ファイルの配置（data/execution.pid, data/kill.flag, data/stop_requested.flag）に注意

---
## 使い方（主要コマンド例）
- 設定ウィザード（.env 生成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 厳格モード（警告をエラー扱い）:
    - python -m kabusys.validate_config --strict

- ExecutionEngine 起動
  - python -m kabusys.run_execution
  - 振る舞い:
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、paper_trading 用 DB（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）に記録します。
    - 起動時に data/stop_requested.flag が存在する場合は起動を中止します。
    - 実行中に stop フラグが生成されるとエンジンを停止します。

- Monitoring 起動（独立プロセスで定期監視）
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を変更できます（デフォルト 60）
  - 監視は常に本番 sqlite_path（Settings.sqlite_path）を使用します（環境に依らず）

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - デフォルト DB: data/paper_trading.db（環境変数 PAPER_TRADING_SQLITE_PATH または --db で指定可能）

- AI 機能（コードから呼ぶ）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - OpenAI API キーは OPENAI_API_KEY 環境変数または関数引数で指定

運用時のフラグ / ファイル:
- data/stop_requested.flag — run_* スクリプトでループ停止の検出に使用
- data/kill.flag — KillSwitch が書き込み、ExecutionEngine に停止を促す（外部で書くことで即時停止）
- data/execution.pid — ExecutionEngine が PID を書き込む

ログ:
- デフォルトで stdout とファイル出力（logs/<app_name>.log、日次ローテーション）
- ログレベルは LOG_LEVEL 環境変数で指定（デフォルト INFO）

---
## 設定 (主な環境変数)
必須（少なくとも validate_config によりチェックされる）:
- JQUANTS_REFRESH_TOKEN — J-Quants API 用リフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API パスワード

主な任意/重要:
- KABUSYS_ENV — 実行環境: development | paper_trading | live（デフォルト development）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — paper_trading 用 SQLite（デフォルト data/paper_trading.db）
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- OPENAI_API_KEY — OpenAI API キー（AI 機能を使う場合必須）
- PAPER_FILL_MODE — ペーパートレードでの約定モード（instant | partial | never | reject）
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（0/1、本番では 0 推奨）

Settings クラスは上記をプロパティとして提供します（kabusys.config.Settings）。

---
## ディレクトリ構成（主要ファイル）
以下は src/kabusys 以下の主要構造と要点です（省略あり）。実際のリポジトリルートはプロジェクトの .git または pyproject.toml を基準に自動検出されます。

- src/
  - kabusys/
    - __init__.py  (パッケージ定義、__version__)
    - config.py  (環境変数／.env の自動読み込み、Settings)
    - config_setup.py  (対話式 .env ウィザード)
    - validate_config.py  (設定検証 CLI)
    - run_execution.py  (ExecutionEngine 起動スクリプト)
    - run_monitoring.py (Monitoring ポーリング起動スクリプト)

    - execution/  (発注エンジン関連)
      - broker_factory.py
      - execution_engine.py
      - order_manager.py
      - order_repository.py
      - reconciler.py
      - risk_manager.py

    - monitoring/
      - monitoring_db.py  (SQLite スキーマ・永続化層)
      - system_monitor.py
      - trade_monitor.py
      - risk_monitor.py
      - kill_switch.py
      - alert_manager.py
      - monitoring_engine.py

    - portfolio/
      - portfolio_builder.py
      - position_sizing.py
      - risk_adjustment.py
      - __init__.py

    - ai/
      - news_nlp.py
      - regime_detector.py
      - __init__.py

    - research/
      - factor_research.py
      - feature_exploration.py
      - __init__.py

    - tools/
      - paper_verification_report.py

    - data/  （実行時に作成される想定のディレクトリ）
      - monitoring.db (デフォルト)
      - paper_trading.db (ペーパートレード用 DB)
      - kabusys.duckdb (デフォルト)
      - kill.flag / stop_requested.flag / execution.pid

    - utils/
      - logging_setup.py  (共通ロギング設定)
      - process_priority.py (プロセス優先度設定)
      - __init__.py

---
## 運用上の注意と安全策
- KABUSYS_ENV=live は本番モードです。validate_config での警告を必ず確認してください（LINE 通知設定など）。
- Kill Switch（data/kill.flag）や stop フラグにより外部から安全に停止できます。KILL_FLAG_CLEAR_ON_START は本番では 0 を推奨します。
- run_execution/run_monitoring はプロセス優先度を high に設定しようとします（psutil を利用）。権限次第で失敗する場合がありますが、警告で継続します。
- OpenAI API を使う機能は API コスト・レイテンシ・応答妥当性に注意してください。失敗時はフェイルセーフ（スコア=0 など）にフォールバックする設計です。
- DB マイグレーション: monitoring_db.init_monitoring_db は既存テーブルへマイグレーション（カラム追加）を試みますが、完全なマイグレーション戦略が必要な場合は事前バックアップを推奨します。

---
## 参考 / 追加情報
- ログ設定: kabusys.utils.logging_setup.setup_logging(app_name="execution") を各起動ポイントが呼び出します。ログは stdout と logs/<app_name>.log に日次ローテーションで出力されます。
- ポートフォリオ構築・リスク調整のアルゴリズムはドキュメント（PortfolioConstruction.md, StrategyModel.md の想定）に対応した純粋関数群として設計されています（DB 参照なし、テスト容易）。
- DuckDB を使ったファクター計算・リサーチは kabusys.research.* で提供されます。DuckDB 接続を渡して実行する想定です。

---
README の内容はコードベースの概要を短くまとめたものです。詳細は各モジュールの docstring・ソースを参照してください。必要であれば、運用手順書（systemd / supervisor のユニット、監視アラートの具体的設定、DB バックアップ方法）を別途作成します — その場合は要件を教えてください。