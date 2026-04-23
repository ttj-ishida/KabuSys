# KabuSys

日本株自動売買システムのコアライブラリ群（README 日本語版）

---

## プロジェクト概要

KabuSys は日本株の自動売買／リサーチ用ユーティリティ群をまとめた Python パッケージです。  
主な機能は以下の通りです：

- 実運用向けの ExecutionEngine（発注処理）
- 監視コンポーネント（System / Trade / Risk のポーリングと Kill Switch）
- ポートフォリオ構築（候補選定・重み付け・ポジションサイズ決定）
- リサーチ（ファクター計算・特徴量探索）
- AI 補助（ニュース NLP によるセンチメント評価、レジーム判定）
- ペーパートレード検証レポート生成ツール

設計方針として、DB（DuckDB/SQLite）を用いたデータ永続化、外部 API（kabuステーション/J-Quants/OpenAI など）との疎結合、フェイルセーフ（API失敗時のフォールバック）を重視しています。

---

## 主な機能一覧

- Execution
  - ExecutionEngine（実際の発注実行、paper_trading モード対応）
  - ブローカークライアントの抽象化（BrokerClientFactory）
  - 注文管理・リスク管理・照合（OrderManager / RiskManager / Reconciler）
- Monitoring
  - SystemMonitor（CPU/メモリ/ディスク/プロセス生存 / データ鮮度）
  - TradeMonitor（注文滞留・約定異常など）
  - RiskMonitor（ドローダウン、ポジション上限監視）
  - KillSwitch（フラグファイル経由で Execution を停止）
  - MonitoringEngine（複数モニタを束ねてポーリング、アラート送出）
- Portfolio
  - 銘柄選定・重み計算（等金額・スコア加重）
  - セクターキャップ適用、レジーム乗数
  - ポジションサイズ計算（単元株丸め、各種上限対応）
- Research
  - ファクター計算（Momentum / Volatility / Value）
  - 将来リターン / IC / 統計サマリ
- AI
  - news_nlp: OpenAI を用いたニュースセンチメント集約＆書込（ai_scores）
  - regime_detector: 指標 + LLM による市場レジーム判定（market_regime）
- Tools
  - ペーパートレード検証レポート生成スクリプト（paper_verification_report）
- 設定管理
  - .env ウィザード（config_setup.py）
  - 設定検証 CLI（validate_config.py）
- ロギング・プロセス優先度ユーティリティ
  - 統一ロギング設定（logs/日次ローテート）
  - プラットフォーム差分を吸収するプロセス優先度設定

---

## 必要環境 / 依存

- Python 3.10 以上（型ヒントに | 合成注釈を使用）
- 標準ライブラリ: sqlite3, logging, threading, datetime, pathlib, etc.
- 外部パッケージ（最低限）:
  - duckdb
  - psutil
  - openai (AI 機能を使う場合)
  - PyYAML（config YAML 検証を行う場合）
- OS: Linux / macOS / Windows（プロセス優先度設定は OS に依存した処理を行います）

インストール例:
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai pyyaml
```

※ requirements.txt は同梱されていないため、プロジェクトに合わせて依存を追加してください。

---

## セットアップ手順

1. リポジトリをクローン
   - git clone … && cd <repo>

2. 仮想環境を作成・有効化し、依存をインストール
   - 例: python -m venv .venv && source .venv/bin/activate
   - pip install duckdb psutil openai pyyaml

3. .env を生成（対話式ウィザード）
   - python -m kabusys.config_setup
   - ウィザードに従い、必須項目（JQUANTS_REFRESH_TOKEN / KABU_API_PASSWORD 等）を入力してください。

4. 設定検証
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いになります（exit code 1）。

5. data/logs ディレクトリ
   - 多くの処理は自動で data/ や logs/ を作成しますが、必要に応じて手動作成してください。
   - デフォルト DB パス:
     - DuckDB: data/kabusys.duckdb
     - SQLite (monitoring): data/monitoring.db
     - Paper トレード SQLite: data/paper_trading.db

6. 環境変数（重要）
   - 必須:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - 推奨・オプション:
     - KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
     - OPENAI_API_KEY: AI 機能を使う場合に必須
     - PAPER_FILL_MODE: instant | partial | never | reject（paper_trading の注文約定挙動）
     - DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH
     - LOG_LEVEL, LOG_DIR
     - KILL_FLAG_CLEAR_ON_START (0/1)
   - 監視のポーリング間隔:
     - MONITOR_POLL_INTERVAL（秒、デフォルト 60）。0 以下や不正値は無視してデフォルトにフォールバックされます。

---

## 使い方（起動方法）

主要なエントリポイントはモジュールとして起動できます。

- ExecutionEngine を起動（実運用 / ペーパートレード）
  - python -m kabusys.run_execution
  - 動作:
    - KABUSYS_ENV=paper_trading のときは MockBrokerClient を使い、paper_trading 専用 DB（data/paper_trading.db）へ記録します。
    - execution.pid（デフォルト data/execution.pid）を生成してプロセス監視等に使います。
    - data/stop_requested.flag を配置すると起動済みエンジンへ停止要求を送れます。

- Monitoring を起動
  - python -m kabusys.run_monitoring
  - 動作:
    - SystemMonitor / TradeMonitor / RiskMonitor 等をポーリングして監視ログを SQLite に記録します。
    - MONITOR_POLL_INTERVAL で間隔を変更できます（秒、デフォルト 60）。
    - Monitoring は環境にかかわらず本番 sqlite_path を使用します（監視は本番 DB を見る想定）。

- ペーパートレード検証レポート
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - デフォルト DB: 環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db

- 設定ウィザード / 検証
  - python -m kabusys.config_setup
  - python -m kabusys.validate_config [--strict]

- AI 機能（プログラムから呼出）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - これらは DuckDB 接続を受け取り、結果を DB に書き込みます。API キーは引数または OPENAI_API_KEY 環境変数を利用します。

注意点:
- Kill Switch は data/kill.flag を書くことで ExecutionEngine に停止命令を出します。KillSwitch.clear() で削除可能。KILL_FLAG_CLEAR_ON_START による自動クリアは注意して設定してください（本番では 0 推奨）。
- Monitoring は監視用の SQLite DB（SQLITE_PATH）を直接操作します。設定によってはファイルの位置を確認してください。

---

## 主要環境変数（抜粋）

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
- OPENAI_API_KEY (AI 機能を使う場合に必須)
- DUCKDB_PATH — デフォルト: data/kabusys.duckdb
- SQLITE_PATH — デフォルト: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH — デフォルト: data/paper_trading.db
- PAPER_FILL_MODE — paper_trading 用（instant | partial | never | reject） デフォルト: instant
- LOG_LEVEL — デフォルト: INFO
- LOG_DIR — デフォルト: logs/
- MONITOR_POLL_INTERVAL — 監視ポーリング間隔（秒）デフォルト: 60
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（0/1、デフォルト: 0）

サンプル .env（最低限の必須のみ）
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
KABU_API_PASSWORD=your_kabu_api_password
KABUSYS_ENV=development
OPENAI_API_KEY=sk-...
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
LOG_LEVEL=INFO
```

---

## ロギング / PID / フラグファイル

- ログ:
  - デフォルト: logs/<app_name>.log（TimedRotatingFileHandler、日次ローテート、30日保持）
  - コンソール出力は標準出力 (stdout)
  - setup_logging() を各起動スクリプトが呼び出します

- PID / stop フラグ:
  - data/execution.pid — ExecutionEngine の PID（デフォルト）
  - data/stop_requested.flag — run_execution / run_monitoring などで使用される停止フラグパス（存在すると停止）
  - data/kill.flag — KillSwitch が書き込む停止（強制）フラグ

---

## ディレクトリ構成

（ソースツリーの主なファイルを抜粋）

- src/
  - kabusys/
    - __init__.py
    - config.py
    - config_setup.py
    - validate_config.py
    - run_execution.py
    - run_monitoring.py
    - utils/
      - __init__.py
      - logging_setup.py
      - process_priority.py
    - execution/            (発注エンジン関連: BrokerFactory, ExecutionEngine, OrderManager, RiskManager, Reconciler, OrderRepository 等)
      - ...
    - monitoring/
      - monitoring_db.py
      - system_monitor.py
      - trade_monitor.py
      - risk_monitor.py
      - monitoring_engine.py
      - kill_switch.py
      - alert_manager.py
      - ...
    - portfolio/
      - portfolio_builder.py
      - position_sizing.py
      - risk_adjustment.py
      - __init__.py
    - research/
      - factor_research.py
      - feature_exploration.py
      - __init__.py
    - ai/
      - news_nlp.py
      - regime_detector.py
      - __init__.py
    - monitoring/ (監視関連、DB スキーマ等)
    - tools/
      - __init__.py
      - paper_verification_report.py
    - data/ (実行時に作成される想定: DB ファイルや flag/pid を配置)

その他: config/*.yaml 想定（system_config.yaml 等。validate_config で存在チェック／パースを行います）

---

## 開発者向けノート / 実装上の重要ポイント

- Settings（config.py）はプロジェクトルート（.git または pyproject.toml を探索）を基準に .env を自動読み込みします。テスト時には KABUSYS_DISABLE_AUTO_ENV_LOAD をセットして自動ロードを無効にできます。
- Monitoring の init_monitoring_db は既存 DB に対するマイグレーション（列追加）を含み、冪等で実行可能です。
- paper_trading モードは本番 DB と完全分離する設計（PAPER_TRADING_SQLITE_PATH を使用）。
- AI 呼び出し（news_nlp / regime_detector）は OpenAI SDK（chat completions）を使用。API 失敗時はフェイルセーフで処理を継続し、DB にフォールバック値を書き込みます。
- Process priority / CPU affinity の設定は psutil を使い、OS による差分を吸収しています（アクセス権限不足時は警告でスキップ）。

---

## よくある質問（FAQ）

Q: 監視（Monitoring）と Execution は別プロセスで動かすべきですか？  
A: はい。監視は ExecutionEngine を監視・必要に応じて停止する役割があるため、別プロセス（別コンテナ）で常時動作させるのが想定です。

Q: 本番環境での Kill Switch の取り扱いは？  
A: KILL_FLAG_CLEAR_ON_START を 0 にしておき、kill.flag の自動消去を無効にすることを推奨します。validate_config は live 環境での注意点を警告します。

Q: OpenAI API のキーはどこに設定する？  
A: .env の OPENAI_API_KEY、または score_news / score_regime の api_key 引数で渡せます。

---

## 付録：よく使うコマンド一覧

- 環境設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- 実行エンジン起動
  - python -m kabusys.run_execution

- 監視起動
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- ペーパートレード検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - python -m kabusys.tools.paper_verification_report --db data/paper_trading.db

---

この README はコードベースの主要点をまとめたものです。実運用前に必ず python -m kabusys.validate_config で設定チェックを行い、テスト環境（paper_trading / development）で動作確認を実施してください。