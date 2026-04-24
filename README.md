# KabuSys

日本株向け自動売買システムのコードベース。株価データ集計・ファクター計算・ポートフォリオ構築・発注実行（本番 / ペーパートレード）・監視・AI 補助（ニュースセンチメント・レジーム判定）などを含みます。

## プロジェクト概要
- 目標：日本株の自動売買ワークフローを一貫して実装するライブラリ／実行スクリプト群。
- 主な機能：データ処理（DuckDB）、ファクター計算、ポートフォリオ構築、発注エンジン（kabuステーションまたはモック）、システム監視、アラート、AI を使ったニュース評価・レジーム判定、ペーパートレード検証レポート生成。
- 設計方針：DB 周りは DuckDB / SQLite を使用。設定は .env で管理。実行スクリプトはモジュールとして起動可能（python -m ...）。

## 主な機能一覧
- Execution
  - ExecutionEngine（発注の実行セッション、リスク制御、order_manager 等）
  - BrokerClientFactory により本番（kabuステーション）または Mock（ペーパートレード）を選択
  - Paper trading は本番 DB と分離して data/paper_trading.db を使用可能
- Monitoring
  - SystemMonitor（CPU/メモリ/ディスク/プロセス状態/データ鮮度）
  - TradeMonitor / RiskMonitor（滞留注文・約定異常、ドローダウン監視）
  - KillSwitch（危険検出時に data/kill.flag を書き込んで Execution を停止）
  - MonitoringEngine / run_monitoring 起動ループ
- Portfolio
  - 候補選定、等重・スコア重み、ポジションサイジング、セクター制限、レジーム乗数
- Research
  - ファクター計算（モメンタム、ボラティリティ、バリュー等）
  - 将来リターン、IC 計算、統計サマリー
- AI
  - ニュースの LLM によるセンチメント評価（OpenAI を利用）
  - レジーム判定（ETF MA とマクロニュースを組合せ）
- ツール
  - Paper Trading 検証レポート生成スクリプト（kabusys.tools.paper_verification_report）
  - 環境設定ウィザード（kabusys.config_setup）
  - 設定検証 CLI（kabusys.validate_config）

## セットアップ（ローカル開発用、概要）
1. リポジトリをクローン
   - git clone <repo_url>
   - cd <repo_root>

2. Python 仮想環境作成（例）
   - python -m venv .venv
   - source .venv/bin/activate  または .venv\Scripts\activate (Windows)

3. 依存パッケージをインストール
   - 要件ファイルがある場合: pip install -r requirements.txt
   - 最低限よく使うライブラリ（環境により変える）:
     - pip install duckdb psutil openai PyYAML
   - 開発用は追加パッケージが必要な場合あり（プロジェクトの requirements を参照ください）。

4. .env の作成（対話ウィザード推奨）
   - python -m kabusys.config_setup
   - ウィザードに従って J-Quants トークンや KABU_API_PASSWORD、KABUSYS_ENV 等を設定します。
   - 注意: .env ファイルは決して Git にコミットしないこと。

5. 設定検証（起動前チェック）
   - python -m kabusys.validate_config
   - --strict を付けると警告もエラー扱いになります。

## 主要な環境変数（抜粋）
- 必須
  - JQUANTS_REFRESH_TOKEN — J-Quants API 用
  - KABU_API_PASSWORD — kabuステーション API のパスワード
- 実行環境
  - KABUSYS_ENV — development / paper_trading / live（デフォルト: development）
    - paper_trading の場合、MockBrokerClient を使用し紙上の DB（PAPER_TRADING_SQLITE_PATH）に記録
- DB パス
  - DUCKDB_PATH — DuckDB ファイル（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH — 監視 DB（デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH — ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- ログ
  - LOG_LEVEL（DEBUG/INFO/...、デフォルト INFO）
  - LOG_DIR（デフォルト logs/）
- AI
  - OPENAI_API_KEY — OpenAI を使う機能を有効にする場合に必要
- その他
  - MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、デフォルト 60）
  - PAPER_FILL_MODE — ペーパートレードのフィル処理 ("instant","partial","never","reject")
  - KILL_FLAG_CLEAR_ON_START — 本番での自動 kill.flag クリア制御（0/1）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD — 1 にすると .env 自動読込を無効化

※ .env の自動ロード順序: OS 環境変数 > .env.local > .env。プロジェクトルートは .git または pyproject.toml を基準に検出されます。

## 使い方（よく使うコマンド例）
- 環境ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- 実行エンジン起動（ExecutionEngine）
  - python -m kabusys.run_execution
  - 挙動:
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使い PAPER_TRADING_SQLITE_PATH に記録
    - 停止制御は data/stop_requested.flag（存在すると起動を中止または停止）および Kill Switch（data/kill.flag）
    - 起動時にプロセス優先度を "high" に設定し、ログは logs/execution.log に出力されます

- 監視ループ起動（Monitoring）
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - 挙動:
    - 設定に関わらず monitoring は本番 sqlite_path を使用して監視ログを記録します（monitoring 用 DB の初期化を行います）
    - 停止フラグ: data/stop_requested.flag が存在するとループ終了
    - ログ: logs/monitoring.log（設定により LOG_DIR を変更可能）

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - または DB を指定: python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db
  - 簡易判定（稼働率・注文成功率・送信率・P95 レイテンシ等）を表示します

- AI 関連（Python API）
  - ニューススコアを計算して DB に書き込む:
    - from datetime import date
      import duckdb
      from kabusys.ai.news_nlp import score_news
      conn = duckdb.connect("data/kabusys.duckdb")
      score_news(conn, date(2026,4,20), api_key="sk-...")
  - レジーム判定:
    - from kabusys.ai.regime_detector import score_regime
      score_regime(conn, date(2026,4,20), api_key="sk-...")

## 停止・Kill フロー
- stop フラグ（run_execution / run_monitoring の両方で使用）
  - data/stop_requested.flag を作成すると run_execution/run_monitoring が検知して安全に停止します。
- Kill Switch（運用上の緊急停止）
  - KillSwitch はリスク監視で条件を満たすと data/kill.flag に理由を書き込みます。
  - ExecutionEngine 起動時に kill.flag が存在すると起動を中止します（本番運用の安全弁）。
  - 起動時に KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に kill.flag を自動クリアしますが、本番では 0 を推奨します。

## ディレクトリ構成（主要ファイル説明）
- src/kabusys/
  - __init__.py — パッケージ定義・バージョン
  - config.py — Settings クラス：環境変数 / .env の読み込み・検証ロジック
  - config_setup.py — .env 対話ウィザード
  - validate_config.py — 起動前設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — Monitoring のポーリングループ起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート生成
  - portfolio/
    - portfolio_builder.py — 候補選定・重み計算
    - risk_adjustment.py — セクター制限・レジーム乗数
    - position_sizing.py — 発注株数計算
  - research/
    - factor_research.py — ファクター（モメンタム／ボラ／バリュー等）
    - feature_exploration.py — 将来リターン / IC / 統計サマリー
  - ai/
    - news_nlp.py — ニュースを LLM で評価して ai_scores に書込
    - regime_detector.py — 市場レジーム判定（MA + マクロニュース）
  - monitoring/
    - monitoring_db.py — SQLite ベースの永続化層（テーブル初期化、読み書きユーティリティ）
    - system_monitor.py — システム/データ鮮度監視
    - trade_monitor.py — （滞留注文・約定異常等の監視）※詳細実装は該当ファイル参照
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - kill_switch.py — kill.flag 書込ユーティリティ
    - monitoring_engine.py — 各 Monitor を束ねる実行エンジン
  - execution/ (発注周りの実装群: Engine, OrderManager, BrokerFactory 等)
    - execution_engine.py, order_manager.py, order_repository.py, reconciler.py, risk_manager.py, broker_factory.py
  - utils/
    - logging_setup.py — 共通のログ設定
    - process_priority.py — プラットフォーム差分を吸収した優先度設定（psutil 使用）
  - data/ （実行時生成）
    - monitoring.db（デフォルト） / paper_trading.db（ペーパートレード用） / kill.flag / stop_requested.flag / execution.pid
  - config/ （プロジェクトルートに存在する想定）
    - system_config.yaml, data_config.yaml, strategy_config.yaml, risk_config.yaml, execution_config.yaml, monitoring_config.yaml
      - validate_config で存在チェックと YAML パース検証を行う（PyYAML がインストールされている場合）

## ログ
- デフォルトログディレクトリ: logs/
- run_execution は logs/execution.log、run_monitoring は logs/monitoring.log を生成
- setup_logging により StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション）を設定

## 運用上の注意
- KABUSYS_ENV=live の場合は本番動作になります。LINE 通知等の設定漏れがないか validate_config で必ず確認してください。
- .env に機密情報（APIキー等）を置く場合、絶対にリポジトリにコミットしないでください。
- OpenAI API を使う機能は API キー（OPENAI_API_KEY）が必須。API 呼び出しはリトライや失敗時フォールバックを実装していますが、API 使用には課金リスクがあります。
- データの整合性や DB マイグレーションには注意：monitoring_db.init_monitoring_db は冪等で簡単なマイグレーションを行いますが、重要な DB 操作はバックアップを推奨します。

---

この README はコードベースの主要な使い方・構成を簡潔にまとめたものです。さらに詳しい仕様（アルゴリズム設計や API の詳細）は該当モジュール内の docstring やプロジェクトの設計ドキュメント（例: PortfolioConstruction.md, StrategyModel.md）があればそちらを参照してください。必要であれば README を英語版や運用手順（systemd / supervisor 用 unit ファイル、Docker 化手順など）に拡張できます。