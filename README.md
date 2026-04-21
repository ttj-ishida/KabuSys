# KabuSys

日本株自動売買システム KabuSys のリポジトリ（抜粋）。  
この README はコードベースから生成した簡易ドキュメントです。実行スクリプト、設定、主要機能、ディレクトリ構成と使い方をまとめています。

---

目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 使い方（コマンド例）
- 主要環境変数 / 設定
- ディレクトリ構成

---

## プロジェクト概要

KabuSys は日本株向けの自動売買および研究用ライブラリ群です。主な役割は以下の通りです。

- シグナル生成・ポートフォリオ構築（portfolio）
- ポジションサイズ計算（position sizing）
- リスク調整（sector cap / regime multiplier）
- ExecutionEngine（注文発行・リスク管理・約定管理）
- Monitoring（システム状態・注文状態・リスクの定期監視）
- 研究用モジュール（ファクター算出、特徴量解析）
- AI連携（ニュースの NLP スコアリング、レジーム判定）
- CLI ツール（設定ウィザード、設定検証、紙トレ検証レポート 等）

設計上のポイント:
- SQLite（監視/発注ログ）と DuckDB（分析/研究）を併用
- .env ベースで設定を管理（自動ロード機能あり）
- Paper Trading 環境は本番 DB と分離（専用 SQLite）
- OpenAI を用いたニュース NLP 機能あり（APIキーが必要）

---

## 機能一覧

- 起動スクリプト
  - run_execution.py: ExecutionEngine を起動（KABUSYS_ENV により paper/live を切替）
  - run_monitoring.py: SystemMonitor のポーリングループを起動（デフォルト 60 秒間隔）
- 設定管理
  - config_setup.py: 対話式 .env 作成ウィザード
  - validate_config.py: .env と config/*.yaml の起動前検証 CLI
- モニタリング
  - SystemMonitor / TradeMonitor / RiskMonitor を束ねる MonitoringEngine
  - kill_switch による flag ファイルで ExecutionEngine の停止をトリガ
  - monitoring_db: 監視用 SQLite スキーマと読み書きユーティリティ
- Execution（発注周り）
  - BrokerClientFactory により本番 or Mock ブローカを切替
  - OrderRepository / OrderManager / RiskManager / ExecutionEngine の組立
- 研究・分析
  - research.factor_research: momentum / volatility / value 等のファクター算出（DuckDB）
  - research.feature_exploration: forward returns, IC, 統計サマリ等
- AI（OpenAI 連携）
  - ai.news_nlp: ニュース記事を LLM でセンチメント付与して ai_scores テーブルへ書込
  - ai.regime_detector: マクロ＋ETF MA200 乖離を使って市場レジーム判定
- ツール
  - tools.paper_verification_report: Paper Trading の性能検証レポート生成

---

## セットアップ手順（ローカル開発向け）

1. リポジトリをクローン
   - git clone <repo>

2. Python 仮想環境作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - pip install -r requirements.txt
   （注: 本リポジトリ抜粋では requirements.txt がない場合があります。psutil, duckdb, openai, PyYAML などが必要です）

4. 初期設定（.env の作成）
   - 対話式ウィザードを使う:
     - python -m kabusys.config_setup
   - もしくは .env を手動で作成（.env.example を参考にしてください）
   - 自動ロードを無効化したいとき:
     - 環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定

5. 設定検証
   - python -m kabusys.validate_config
   - 警告を厳密に扱う（--strict）: python -m kabusys.validate_config --strict

6. データディレクトリ作成
   - デフォルトで data/ および logs/ にファイルが作られます。権限等に注意してください。

---

## 使い方

以下は主要スクリプトの実行例です。すべて .env の設定に従います。

- ExecutionEngine を起動（foreground）
  - python -m kabusys.run_execution
  - ポイント:
    - 起動時にプロセス優先度を "high" に設定する試みを行います（失敗しても継続）。
    - KABUSYS_ENV=paper_trading の場合は MockBroker を使用し、paper_trading 用 DB（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）に記録します。
    - data/stop_requested.flag を作成すると起動を抑止・停止できます。PID ファイルは data/execution.pid（既定）に出力されます。

- Monitoring を起動
  - python -m kabusys.run_monitoring
  - ポイント:
    - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL（秒、デフォルト 60）
    - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path（SQLITE_PATH）を使用して監視 DB に記録します
    - run_monitoring は stop_requested.flag を監視し存在するとループを終了します

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db オプションで SQLite パスを指定可能（PAPER_TRADING_SQLITE_PATH 環境変数でも可）

- AI 機能（プログラムから呼び出す）
  - OpenAI API キーが必要: 環境変数 OPENAI_API_KEY を設定
  - 例（ニュース NLP）:
    - from kabusys.ai.news_nlp import score_news
    - score_news(conn=duckdb_conn, target_date=date(2026,4,1), api_key=None)
  - 例（レジーム判定）:
    - from kabusys.ai.regime_detector import score_regime
    - score_regime(conn=duckdb_conn, target_date=date(2026,4,1), api_key=None)

- 設定ウィザード / 検証
  - python -m kabusys.config_setup
  - python -m kabusys.validate_config [--strict]

ログ出力:
- デフォルト: console (stdout) と logs/<app_name>.log（日次ローテート、30日保持）
- LOG_DIR 環境変数でログ保存先を変更できます。
- setup_logging() により各スクリプトは統一的に設定されます。

停止 / Kill Switch:
- kill.flag（Settings.kill_flag_path：デフォルト data/kill.flag）を書くと ExecutionEngine に停止信号が送られます（Monitoring の KillSwitch がこれを生成します）。
- stop_requested.flag（data/stop_requested.flag）を使う起動スクリプトがいくつかあります（監視用/実行用の即時停止制御）。

---

## 主要環境変数 / 設定一覧（代表）

- KABUSYS_ENV
  - 値: development | paper_trading | live
  - デフォルト: development
  - 動作モードを切り替え（paper_trading は MockBroker）

- JQUANTS_REFRESH_TOKEN
  - J-Quants API リフレッシュトークン（必須）

- KABU_API_PASSWORD
  - kabuステーション API 用パスワード（必須）

- DUCKDB_PATH
  - DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）

- SQLITE_PATH
  - 監視 DB（本番）ファイルパス（デフォルト: data/monitoring.db）

- PAPER_TRADING_SQLITE_PATH
  - Paper Trading の SQLite（デフォルト: data/paper_trading.db）

- PAPER_FILL_MODE
  - Paper Trading の注文充足モード
  - 有効値: instant | partial | never | reject
  - デフォルト: instant

- LOG_LEVEL
  - DEBUG / INFO / WARNING / ERROR / CRITICAL
  - デフォルト: INFO

- LOG_DIR
  - ログファイル出力先ディレクトリ（setup_logging で使用）

- MONITOR_POLL_INTERVAL
  - run_monitoring のポーリング間隔（秒、デフォルト 60）
  - 0 以下や不正値はデフォルトにフォールバック

- OPENAI_API_KEY
  - OpenAI を使う機能の API キー（ai.news_nlp, ai.regime_detector）

- KILL_FLAG_CLEAR_ON_START
  - Start 時に kill.flag を自動でクリアするか（1: クリアする / 0: しない）
  - 本番では 0 を推奨

- KABUSYS_DISABLE_AUTO_ENV_LOAD
  - 1 を設定すると .env の自動ロードを無効化する（テスト時など）

---

## 注意点 / 運用上のヒント

- Monitoring は監視用 DB に対して常に「本番の sqlite_path」を使用します（KABUSYS_ENV に依存しません）。Paper トレードを完全分離したい場合は Execution 側のみ paper_sqlite_path を利用します。
- run_execution 起動時に stop_requested.flag が既に存在すると起動を行わず終了します。
- PID ファイルや flag ファイルは data/ 以下に生成されます。CI/CD や運用スクリプトでの掃除（削除）に注意してください。
- OpenAI 呼び出しはネットワークエラーやレート制限を考慮したリトライ実装が含まれていますが、API キーの漏洩やコスト管理に注意してください。
- DuckDB / SQLite のパスは .env で指定できます。ログや DB ファイルの配置先のディスク容量に注意してください。

---

## ディレクトリ構成（主要部分）

以下は src/kabusys 以下の主要ファイル・ディレクトリの抜粋です。

- kabusys/
  - __init__.py
  - config.py                  — 環境変数 / Settings 管理（.env 自動読み込み機能含む）
  - config_setup.py            — .env 対話式ウィザード
  - validate_config.py         — 設定検証 CLI
  - run_execution.py           — ExecutionEngine 起動スクリプト
  - run_monitoring.py          — SystemMonitor 起動スクリプト
  - tools/
    - paper_verification_report.py
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
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - monitoring_engine.py
    - kill_switch.py
    - alert_manager.py (コード抜粋外の可能性あり)
  - utils/
    - logging_setup.py
    - process_priority.py
  - execution/                  — Execution 関連（broker_factory, execution_engine, order_manager, risk_manager 等）
  - data/                       — 実行時に生成される data/ 以下の DB・flag・pid 等（リポジトリ外）

（注）本 README は該当コードベースの抜粋に基づき作成しています。実際のリポジトリにはさらに多くのモジュールやスクリプト、ドキュメント（PortfolioConstruction.md、StrategyModel.md 等）が存在する可能性があります。詳細はプロジェクトの完全なドキュメントを参照してください。

---

必要であれば、README に加えて以下を生成できます：
- サンプル .env テンプレート（.env.example）
- systemd / Supervisor 用の起動ユニット例
- 運用チェックリスト（ログローテーション、バックアップ、Kill Switch 運用指針）

要望があれば上記のいずれかを作成します。