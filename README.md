# KabuSys

日本株向け自動売買システムの参照実装ライブラリ / 実行スクリプト群です。  
このリポジトリは戦略・ポートフォリオ構築、発注実行、監視、リサーチ、AI を用いたニュース評価などのコンポーネントを含みます。

バージョン: 0.1.0

---

## 概要

KabuSys は次を目的としたモジュール群を提供します。

- 株式アルゴリズムの研究・ファクター計算（DuckDB を使用）
- ポートフォリオ構築（候補選定・重み計算・ポジションサイズ算出）
- ExecutionEngine による発注管理（実稼働 / ペーパートレードの分離）
- 監視コンポーネント（プロセス、生存率、注文ログ、リスク監視）
- ニュースを LLM で評価する AI モジュール（OpenAI）
- コマンドライン用ユーティリティ（設定ウィザード・設定検証・検証レポート生成 等）

設計上のポイント:

- .env を利用した環境変数管理（自動読み込み機能あり）
- paper_trading 環境では本番 DB と分離（data/paper_trading.db）
- ロギングは共通ユーティリティで統一（stdout + 日次ローテート）
- フェイルセーフを重視（API失敗時のフォールバック、部分書き込みで既存データ保護 等）

---

## 主な機能一覧

- config
  - 環境変数の読み込み・検証（Settings クラス）
  - 設定ウィザード（対話式で .env 作成）
  - 起動前チェック（validate_config）
- execution
  - ExecutionEngine（発注、OrderManager、RiskManager、Reconciler 等）
  - Broker クライアントの抽象化（paper_trading 時は Mock）
- monitoring
  - SystemMonitor / TradeMonitor / RiskMonitor / KillSwitch
  - MonitoringDB（SQLite）によるログ永続化
  - 監視ループ起動スクリプト
- portfolio
  - 候補選定・重み付け・リスク調整・株数決定（純粋関数でテスト容易）
- research
  - ファクター計算（Momentum / Volatility / Value 等）
  - 特徴量探索・IC 計算・統計サマリー
- ai
  - ニュース NLP（OpenAI）を使った銘柄ごとのセンチメント評価
  - レジーム判定（MA200 + マクロニュースの LLM 評価）
- tools
  - Paper Trading 検証レポート生成スクリプト

---

## セットアップ手順

1. Python 環境を用意
   - 推奨: Python 3.10+（コードは型注釈等を使用）
   - 仮想環境を作成・有効化
     - python -m venv .venv
     - source .venv/bin/activate (Linux/Mac) / .venv\Scripts\activate (Windows)

2. 依存パッケージのインストール（代表例）
   - pip install duckdb psutil openai PyYAML
   - （requirements.txt がある場合）
     - pip install -r requirements.txt

3. プロジェクトルートに移動（パッケージはプロジェクトルートを基準に .env を自動読み込みします）
   - レポジトリのルート（pyproject.toml または .git がある階層）

4. 環境変数の準備
   - 対話式ウィザードで .env を作る:
     - python -m kabusys.config_setup
   - または .env を手動作成（最低必須）
     - JQUANTS_REFRESH_TOKEN=your_token
     - KABU_API_PASSWORD=your_password
     - KABUSYS_ENV=development|paper_trading|live
     - （必要に応じて）OPENAI_API_KEY=sk-...
   - 自動ロードを無効にする場合:
     - KABUSYS_DISABLE_AUTO_ENV_LOAD=1

5. データディレクトリ作成（必要に応じて）
   - data/（デフォルトの DB / フラグファイル保存場所）
   - logs/（ロギング出力先 — setup_logging が自動作成を試みます）

注意:
- paper_trading 環境では SQLite は data/paper_trading.db を使用して本番 DB と分離されます。
- 監視は常に settings.sqlite_path（デフォルト data/monitoring.db）を利用します（monitoring は環境に依存しない）。

---

## 環境変数（主なもの）

- 必須
  - JQUANTS_REFRESH_TOKEN — J-Quants API 用
  - KABU_API_PASSWORD — kabuステーション API パスワード
- 選択 / デフォルト
  - KABUSYS_ENV — 実行環境（development / paper_trading / live）デフォルト: development
  - DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH — ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
  - LOG_LEVEL — ログレベル（DEBUG/INFO/...、デフォルト: INFO）
  - OPENAI_API_KEY — OpenAI を使う機能で必要
  - PAPER_FILL_MODE — ペーパートレード時の約定挙動（instant/partial/never/reject）
  - KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag をクリアするか（1/0、デフォルト: 0）
  - MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、デフォルト: 60）

---

## 使い方（主要スクリプト）

一般にパッケージとして実行します。プロジェクトルートで実行してください。

- 環境ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 厳格モード（警告も失敗扱い）:
    - python -m kabusys.validate_config --strict

- 監視ループ起動（SystemMonitor を定期実行）
  - MONITOR_POLL_INTERVAL 環境変数で秒間隔を指定可能（例: 30秒）
    - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - 停止: プロジェクトルートの data/stop_requested.flag ファイルを作成すると監視ループが終了します。
  - 監視は settings.sqlite_path（デフォルト data/monitoring.db）を使用します。

- ExecutionEngine 起動（発注エンジン）
  - KABUSYS_ENV=paper_trading を設定すると MockBrokerClient を使用し、DB は data/paper_trading.db に記録されます（本番 DB と分離）。
    - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  - 実行中に停止するには data/stop_requested.flag を作成します。
  - 実行時は data/execution.pid に PID が書かれます。

- Paper Trading 検証レポート（CSV などではなく標準出力）
  - python -m kabusys.tools.paper_verification_report
  - 期間を指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
  - 環境変数 PAPER_TRADING_SQLITE_PATH でも DB を指定できます。

- AI 関連（ニューススコア / レジーム検出）
  - OpenAI API キーが必要（OPENAI_API_KEY 環境変数または関数引数で渡す）
  - kabusys.ai.score_news / kabusys.ai.regime_detector.score_regime 等を呼び出すことで DuckDB 内のテーブルに書き込みます。

ログ:
- ログは stdout と logs/<app_name>.log に出力されます（ログディレクトリは LOG_DIR 環境変数で上書き可）。

Kill Switch / Stop Flag:
- Kill Switch は監視モジュールが条件を満たしたときに data/kill.flag を書き込み、ExecutionEngine に停止シグナルを送ります。
- 手動停止等には data/stop_requested.flag を使用します（run_* スクリプトはこのファイルの存在を監視します）。

---

## ディレクトリ構成（概要）

以下は src/kabusys 配下の主要構成です（省略あり）。実際のリポジトリはさらに詳細なファイルを含みます。

- src/
  - kabusys/
    - __init__.py
    - config.py                — 環境変数・設定管理（Settings）
    - config_setup.py          — .env 対話式ウィザード
    - validate_config.py       — 設定検証 CLI
    - run_monitoring.py        — SystemMonitor ポーリング起動スクリプト
    - run_execution.py         — ExecutionEngine 起動スクリプト
    - data/                    — データ処理 / pipeline（DuckDB 連携の想定）
    - execution/
      - execution_engine.py
      - order_manager.py
      - order_repository.py
      - reconciler.py
      - broker_factory.py
      - risk_manager.py
    - monitoring/
      - monitoring_db.py
      - system_monitor.py
      - trade_monitor.py
      - risk_monitor.py
      - kill_switch.py
      - monitoring_engine.py
      - alert_manager.py
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
    - utils/
      - logging_setup.py
      - process_priority.py

※ 実際のリポジトリではさらに細分化されたモジュール・ユーティリティが含まれます。

---

## 開発・運用上の注意

- .env は機密情報を含むため Git 管理しないでください（config_setup も README 内に警告を出力します）。
- 本番（KABUSYS_ENV=live）では LINE 通知等の設定を必ず確認してください（validate_config の live ガード）。
- OpenAI を使う処理は API 呼び出しが失敗してもフェイルセーフで進むよう実装されていますが、API コストやレート制限には注意してください。
- monitoring は常に production 用 sqlite_path を参照するため、監視ログの共有に注意してください。
- プロセス優先度設定は psutil 経由で行います。権限がないと設定に失敗しますが、警告ログに留まるようになっています。

---

## 追加情報 / トラブルシュート

- SQLite / DuckDB のテーブルがない場合、各モジュールは必要テーブルの作成（マイグレーション）を行うよう設計されています（例: init_monitoring_db）。
- YAML ベースの config/*.yaml が必要な場合は PyYAML が必要です。validate_config は PyYAML が無い場合は YAML 内容チェックをスキップします。
- ログディレクトリ作成に失敗した場合、ファイル出力は無効化され stdout のみになります。

---

この README はコードベース（src/kabusys）をもとにした概要ドキュメントです。詳細な設計仕様（PortfolioConstruction.md, StrategyModel.md 等）は別途参照してください。質問や補足が必要であれば教えてください。