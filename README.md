# KabuSys

日本株向け自動売買システムの参照実装ライブラリ & 起動スクリプト群。

このリポジトリは戦略（リサーチ/ファクター計算）、ポートフォリオ構築、発注エンジン（ExecutionEngine）、監視（Monitoring）、
AIベースのニューススコアリングなどを含むモジュール群を提供します。開発・ペーパートレード・本番の各実行モードを想定しています。

---

## 主な特徴（機能一覧）

- 環境設定管理
  - .env の自動読み込み / 対話式ウィザード（config_setup）
  - 起動前の設定検証 CLI（validate_config）
- 実行エンジン
  - ExecutionEngine: ブローカー抽象化、リスク管理、注文管理、リコンシリエーション等の組立て
  - 本番 / ペーパートレードモードの切替（KABUSYS_ENV）
  - ペーパートレードは MockBrokerClient を使用し DB を分離（data/paper_trading.db）
- 監視（Monitoring）
  - SystemMonitor / TradeMonitor / RiskMonitor を組み合わせた MonitoringEngine
  - 監視データは SQLite（デフォルト: data/monitoring.db）へ永続化
  - kill.flag による安全停止（KillSwitch）
  - 監視ループの起動スクリプト（run_monitoring）
- ポートフォリオ構築（純粋関数）
  - 候補選定、重み付け（等重・スコア加重）、ポジションサイズ計算、セクターキャップ、レジーム乗数
- リサーチ／ファクター計算
  - Momentum / Volatility / Value 等のファクターを DuckDB 経由で計算
  - 将来リターン・IC 計算・統計サマリ
- AI 補助（OpenAI）
  - ニュース記事のセンチメントを LLM で評価して ai_scores テーブルへ書き込み（news_nlp）
  - マクロニュースと ETF MA による市場レジーム判定（regime_detector）
- ツール
  - Paper Trading の検証レポート生成スクリプト（tools.paper_verification_report）
- ユーティリティ
  - ロギング設定（stdout + 日次ローテーションファイル）
  - プロセス優先度 / CPU affinity 設定ユーティリティ

---

## セットアップ手順（ローカル開発向け）

前提: Python 3.10+（typing | union 表記などが使用されています）

1. リポジトリをクローン
   - git clone <repo-url>

2. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   - 最低限必要な依存（例）:
     - duckdb
     - psutil
     - openai
     - PyYAML（config 検証に必要、任意）
   - 例:
     - pip install duckdb psutil openai PyYAML

   ※ requirements.txt がある場合はそれを使ってください:
     - pip install -r requirements.txt

4. 環境変数の初期化（推奨）
   - 対話式ウィザードで .env を作成:
     - python -m kabusys.config_setup
   - あるいは手動で .env を作成。最低で以下の必須環境変数を設定してください:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD

5. 設定の検証（任意）
   - python -m kabusys.validate_config
   - 警告もエラー扱いにする場合:
     - python -m kabusys.validate_config --strict

---

## 主な環境変数（抜粋）

（Settings クラスにより参照されるもの。括弧はデフォルト）

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV ("development" | "paper_trading" | "live") — デフォルト: development
  - paper_trading: MockBroker を使用し DB を分離
  - live: 本番
- DUCKDB_PATH (data/kabusys.duckdb)
- SQLITE_PATH (data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH (data/paper_trading.db)
- PAPER_FILL_MODE ("instant" | "partial" | "never" | "reject") — デフォルト: "instant"
- LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL) — デフォルト: INFO
- PID_FILE_PATH (data/execution.pid)
- KILL_FLAG_PATH (data/kill.flag)
- KILL_FLAG_CLEAR_ON_START (0|1) — デフォルト: 0
- MONITOR_POLL_INTERVAL (run_monitoring のポーリング間隔, 秒; デフォルト 60)
- OPENAI_API_KEY — AI モジュール使用時に必要

.env の自動読み込みはプロジェクトルート（.git または pyproject.toml を検出）を基準に行われます。自動読み込みを無効化する場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## 使い方（起動例）

- 監視ループを起動（ログは logs/monitoring.log）
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL で秒間隔を変更可能（例: MONITOR_POLL_INTERVAL=30）

- ExecutionEngine（発注エンジン）を起動
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合、paper_trading 用 DB（PAPER_TRADING_SQLITE_PATH）に記録します

- .env を対話式で生成/更新
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- Paper Trading 検証レポート出力
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB パス指定:
    - python -m kabusys.tools.paper_verification_report --db data/paper_trading.db

- AI スコアリング・レジーム判定（ライブラリ呼び出し）
  - kabusys.ai.score_news(conn, target_date, api_key=...)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=...)

---

## 停止 / Kill Switch

- 外部から ExecutionEngine を止めたい場合:
  - KillSwitch は data/kill.flag を書き込むことで停止シグナルを送ります（KillSwitch 実装により理由をファイルに書き込み）。
  - run_execution / run_monitoring は data/stop_requested.flag の存在をチェックしてループ終了または起動停止を行います。
  - 実行前に既存の kill.flag をクリアしたい場合は KILL_FLAG_CLEAR_ON_START=1 を設定できます（本番では 0 推奨）。

---

## ログ

- ログは stdout（StreamHandler）とファイル（日次ローテーション, logs/<app_name>.log）へ出力されます。
- デフォルトログディレクトリ: logs/
- ログレベルは環境変数 LOG_LEVEL または setup_logging の引数で制御可能
- ファイルハンドラ作成に失敗した場合でもコンソール出力は継続します

---

## データベース（永続化）

- DuckDB: 分析用（prices_daily, raw_financials 等の大規模時系列データ想定）
  - デフォルト: data/kabusys.duckdb
- SQLite: 監視・注文ログ等の永続化（MonitoringDB）
  - デフォルト: data/monitoring.db
- ペーパートレードモードの SQLite（Execution の記録等）
  - デフォルト: data/paper_trading.db

MonitoringDB は必要なスキーマを起動時に冪等作成（init_monitoring_db）します。マイグレーション処理（既存テーブルへの列追加）も含まれています。

---

## 主要モジュール（概観）

- kabusys.config — 環境変数 / Settings（デフォルト・検証ロジック）
- kabusys.config_setup — .env 対話式ウィザード
- kabusys.validate_config — 起動前検証 CLI
- kabusys.run_monitoring — SystemMonitor ポーリングループ起動スクリプト
- kabusys.run_execution — ExecutionEngine 起動スクリプト
- kabusys.monitoring — SystemMonitor / TradeMonitor / RiskMonitor / MonitoringEngine / KillSwitch / MonitoringDB
- kabusys.execution — 発注周り（BrokerFactory / Engine / OrderManager / RiskManager 等）※実装本体はこのコードベースに一部ある想定
- kabusys.portfolio — 銘柄選定、重み付け、ポジションサイズ、セクター制限等（純粋関数）
- kabusys.research — ファクター計算、特徴量解析ユーティリティ
- kabusys.ai — news_nlp（OpenAI を使ったニューススコアリング）, regime_detector
- kabusys.utils — logging_setup, process_priority（プロセス優先度 / CPU affinity）

---

## ディレクトリ構成

以下は主要ファイル・ディレクトリの抜粋（src/kabusys 配下）:

- kabusys/
  - __init__.py
  - config.py
  - config_setup.py
  - validate_config.py
  - run_monitoring.py
  - run_execution.py
  - utils/
    - __init__.py
    - logging_setup.py
    - process_priority.py
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - monitoring_engine.py
    - kill_switch.py
    - alert_manager.py (想定)
  - execution/
    - execution_engine.py (想定)
    - broker_factory.py (想定)
    - order_manager.py (想定)
    - order_repository.py (想定)
    - reconciler.py (想定)
    - risk_manager.py (想定)
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
  - data/  (実行時に作成されることが想定)
    - monitoring.db (デフォルト)
    - paper_trading.db (ペーパートレード時)
    - kill.flag / stop_requested.flag / execution.pid
  - tools/
    - __init__.py
    - paper_verification_report.py

（実装ファイルの一部は省略または外部に委譲されている箇所があります。実行前に依存モジュールの存在を確認してください。）

---

## 注意事項 / 運用メモ

- KABUSYS_ENV=live の場合は本番動作になります。LINE 通知トークンなどの設定漏れがあるとアラートが届きません。validate_config の live ガードを必ず確認してください。
- OpenAI を使う機能（news_nlp, regime_detector）は API キーが必要です。料金やレート制限に注意してください。API 呼び出しはリトライロジックを備えていますが、運用上の監視は必要です。
- 単体テスト・統合テストの仕組みはこの README に含まれていません。必要に応じて mokcking（OpenAI / ブローカー等）を行ってください。
- データベースやログファイルは .env 設定で変更できます。運用時はログディレクトリと DB パスのバックアップ・ローテーションを検討してください。

---

必要があれば、導入手順の詳細（systemd ユニット / Docker 化 / CI 用のセットアップ）や各モジュールの API リファレンス（関数仕様例）も作成します。どの情報が欲しいか教えてください。