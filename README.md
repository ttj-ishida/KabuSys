# KabuSys

日本株自動売買システムのコアライブラリ群と起動スクリプト群です。  
このリポジトリは、戦略の研究（factor / feature）、ポートフォリオ構築、発注実行（本番/ペーパートレード）およびシステム監視・アラートに必要なコンポーネントを含みます。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は以下の主要な機能を持つモジュール群で構成されています。

- データ処理 / 研究:
  - DuckDB を用いたファクター計算（モメンタム、ボラティリティ、バリューなど）
  - 将来リターン計算、IC（Information Coefficient）や統計サマリー
- ポートフォリオ構築:
  - 候補選定、重み計算、リスク調整（セクターキャップ、レジーム乗数）
  - ポジションサイズ計算（リスクベース、等分配など）、単元株丸め、集計キャップ処理
- 発注実行:
  - ExecutionEngine の起動スクリプト（本番 / ペーパートレード切替）
  - ブローカークライアントのファクトリ、注文管理、リスク管理、照合（reconciler）
- 監視・アラート:
  - SystemMonitor / TradeMonitor / RiskMonitor を束ねる MonitoringEngine
  - SQLite を用いた監視ログ永続化（monitoring_db）
  - Kill Switch（条件に応じて data/kill.flag を書き込んで ExecutionEngine を停止）
- AI 支援:
  - ニュースセンチメント（OpenAI）を使った銘柄ごとのスコア付け
  - マクロニュース＋ETF MA による市場レジーム判定
- 補助ユーティリティ:
  - ログセットアップ、プロセス優先度設定、環境設定ウィザード・検証 CLI、レポート作成スクリプト

---

## 主な機能一覧

- config_setup.py: 対話式 .env 作成ウィザード
- validate_config.py: 環境変数・設定ファイル検証 CLI
- run_execution.py: ExecutionEngine （発注ロジック）起動スクリプト
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、data/paper_trading.db に記録（本番 DB と完全分離）
- run_monitoring.py: SystemMonitor をポーリングする監視用プロセス起動スクリプト
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）
- tools/paper_verification_report.py: ペーパートレード検証レポート生成スクリプト
- research.*: DuckDB を利用したファクター計算・分析ユーティリティ
- portfolio.*: 候補選定、重み付け、ポジションサイズ計算、リスク調整
- ai.news_nlp / ai.regime_detector: OpenAI を用いたニュース NLP 処理とレジーム判定
- monitoring.*: 監視データベースの読み書き、各種モニタ、KillSwitch、監視エンジン

---

## セットアップ手順

前提:
- Python 3.9+（コードは型アノテーション等を用いています）
- ネットワーク接続（OpenAI を利用する場合）

1. リポジトリをチェックアウト
   - 例: git clone <repo-url>

2. 仮想環境の作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 必要パッケージをインストール
   - pip install duckdb psutil openai
   - 任意 / 推奨:
     - PyYAML（config/*.yaml の構文チェックを行いたい場合）: pip install pyyaml
   - （requirements.txt が無い場合は上記パッケージを手動でインストールしてください）

4. .env の作成
   - 対話式ウィザード: python -m kabusys.config_setup
   - もしくは .env.example を参考に .env を作成してルートに配置

5. 設定の検証
   - python -m kabusys.validate_config
   - 警告も厳格に扱う場合: python -m kabusys.validate_config --strict

6. DB ファイル（初回は自動でテーブル作成されます）
   - デフォルト:
     - SQLite (monitoring) : data/monitoring.db
     - DuckDB (分析)       : data/kabusys.duckdb
     - Paper trading DB    : data/paper_trading.db（KABUSYS_ENV=paper_trading 使用時）

---

## 主要な環境変数

（よく使うものを抜粋）

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants API 用リフレッシュトークン
- KABU_API_PASSWORD (必須) — kabuステーション API パスワード
- KABU_API_BASE_URL — kabuステーション API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- OPENAI_API_KEY — OpenAI API キー（ai モジュール使用時）
- KABUSYS_ENV — 実行環境: development | paper_trading | live（デフォルト: development）
  - paper_trading 時は run_execution が paper DB を使います
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite 監視 DB（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード DB（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE — MockBroker の約定挙動（instant / partial / never / reject）
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- LOG_DIR — ログ出力ディレクトリ（デフォルト: logs/）
- PID_FILE_PATH — ExecutionEngine の PID ファイルパス（デフォルト: data/execution.pid）
- KILL_FLAG_PATH — Kill Switch 用フラグファイル（デフォルト: data/kill.flag）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（0/1）

モニタ関連：
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、デフォルト 60）

注意:
- run_monitoring は Monitoring を実行する際、KABUSYS_ENV に関わらず本番 sqlite_path（SQLITE_PATH）を使用します。
- run_execution は KABUSYS_ENV=paper_trading の場合に PAPER_TRADING_SQLITE_PATH を使用し本番 DB と分離します。

---

## 利用方法（起動例）

- 環境変数をセット（例: Bash）
  - export KABUSYS_ENV=development
  - export OPENAI_API_KEY=sk-...

- 設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config

- ExecutionEngine を起動（発注エンジン）
  - python -m kabusys.run_execution
  - 注意: 起動前に data/kill.flag があると起動しません

- Monitoring を常駐起動（SystemMonitor のポーリング）
  - python -m kabusys.run_monitoring
  - ポーリング間隔を環境変数で変更:
    - export MONITOR_POLL_INTERVAL=30

- ペーパートレード検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 例: python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB パスを指定する場合:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

- プログラム内 API を使う（ライブラリ利用）
  - 例: ファクター計算
    - from kabusys.research import calc_momentum
    - result = calc_momentum(duckdb_conn, date(2026, 4, 1))

---

## Kill Switch / 停止フロー

- KillSwitch は data/kill.flag を書き込むことで ExecutionEngine に停止を要求します。
- ExecutionEngine / run_execution は data/stop_requested.flag（および data/execution.pid）を監視して終了処理を行います。
- kill.flag の自動クリアは KILL_FLAG_CLEAR_ON_START を 1 に設定すると有効になりますが、本番では推奨されません。

---

## ログ

- 共通ログ設定: kabusys.utils.logging_setup.setup_logging(app_name=...)
  - コンソール (stdout) とファイル (logs/<app_name>.log、日次ローテーション) を設定
  - LOG_LEVEL / LOG_DIR 環境変数で制御

---

## ディレクトリ構成

（主要ファイルのみ抜粋）

- src/
  - kabusys/
    - __init__.py
    - config.py                — 環境変数読み込み・Settings
    - config_setup.py          — .env 対話ウィザード
    - validate_config.py       — 設定検証 CLI
    - run_execution.py         — ExecutionEngine 起動スクリプト
    - run_monitoring.py        — SystemMonitor ポーリング起動スクリプト
    - tools/
      - paper_verification_report.py
    - ai/
      - news_nlp.py
      - regime_detector.py
    - research/
      - factor_research.py
      - feature_exploration.py
    - portfolio/
      - portfolio_builder.py
      - position_sizing.py
      - risk_adjustment.py
    - monitoring/
      - monitoring_db.py
      - system_monitor.py
      - trade_monitor.py
      - risk_monitor.py
      - monitoring_engine.py
      - kill_switch.py
      - alert_manager.py (参照)
    - utils/
      - logging_setup.py
      - process_priority.py
    - execution/                 — ExecutionEngine 周りのモジュール群（broker, order_manager 等）
    - data/                      — データ関連（pipeline / stats 等）
    - other support modules...

- data/                         — デフォルト DB / フラグファイル置き場（例: data/monitoring.db, data/kill.flag）
- logs/                         — ログ出力先（デフォルト）

---

## 追加メモ / FAQ

- DB 初期化:
  - monitoring 用のテーブルは起動スクリプト内で init_monitoring_db() が呼ばれ冪等に作成されます。手動初期化は不要です。
- Paper trading の分離:
  - KABUSYS_ENV=paper_trading のとき、run_execution は PAPER_TRADING_SQLITE_PATH を使い本番 SQLite と分離します。
- OpenAI 利用時:
  - API 失敗（429/5xx/タイムアウト等）に対して内部でリトライ・フォールバックする実装がありますが、API キーは必須です（ai モジュールを使う場合）。
- 依存関係:
  - 実行に必須のライブラリ: duckdb, psutil, openai
  - 設定ファイル（YAML）の構文チェックに PyYAML を利用します（任意）

---

この README はコードベースの主要点を要約したものです。詳しい実装やパラメータの調整は各モジュールの docstring / ソースコードをご確認ください。必要であれば README にサンプル .env やデプロイ手順（systemd / Docker / Supervisor 用の設定例）を追加します。追加して欲しいセクションがあれば教えてください。