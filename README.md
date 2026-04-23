# KabuSys

日本株自動売買システムの Python コードベース用 README（日本語）。

この README はリポジトリ内の主要モジュールを元に、導入・実行・設定方法やディレクトリ構成をまとめたものです。

重要: このプロジェクトでは .env に機密情報（API トークン・パスワード等）を保存します。.env は絶対にリポジトリにコミットしないでください。

---

## プロジェクト概要

KabuSys は日本株の自動売買システムを構成するモジュール群です。主な役割は以下です。

- 戦略（ファクター計算、特徴量解析、ポートフォリオ構築、ポジションサイズ計算）
- 注文発行・リスク管理・約定管理を行う Execution エンジン
- システム稼働監視・トレード監視・リスク監視と Kill Switch（停止フラグ）
- Paper Trading 用の検証ツール（レポート生成）
- ニュース NLP / マクロレジーム判定（OpenAI API を利用したスコアリング）
- ロギング・設定管理・ユーティリティ

設計上の注意点：
- .env（または環境変数）から設定を読み込む仕組み
- paper_trading（ペーパートレード）時は本番 DB と分離（専用 SQLite）
- 監視は別プロセスとして動作し、kill.flag による ExecutionEngine 停止シグナルを発行

---

## 主な機能一覧

- 設定ウィザード（.env 生成）: kabusys.config_setup
- 設定検証 CLI: kabusys.validate_config
- ExecutionEngine 起動スクリプト: kabusys.run_execution
  - KABUSYS_ENV=paper_trading 時は MockBroker を利用し専用 DB を使用
- Monitoring 起動スクリプト（ポーリングループ）: kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL によるポーリング間隔上書き（デフォルト 60 秒）
  - 監視 DB の初期化（init_monitoring_db）
- MonitoringEngine: System / Trade / Risk 各モニタの統合とアラート評価
- Kill Switch: 指定条件で data/kill.flag を書き込み Execution を止める
- Paper Trading 検証レポート: kabusys.tools.paper_verification_report
- ニュース NLP（OpenAI 使用）: kabusys.ai.news_nlp（ai_scores 生成）
- 市場レジーム判定（OpenAI 使用）: kabusys.ai.regime_detector
- ポートフォリオ構築・リスク調整・ポジションサイズ計算: kabusys.portfolio
- ファクター計算・研究ユーティリティ: kabusys.research
- ログ設定 / プロセス優先度設定 / 環境読み込みユーティリティ: kabusys.utils

---

## セットアップ手順（開発マシン想定）

1. リポジトリをクローン：
   - git clone <repo-url>

2. Python 仮想環境を作成・有効化（例）:
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール（主な依存）:
   - duckdb
   - psutil
   - openai
   - PyYAML（validate_config の YAML 検証に optional）
   実際の requirements.txt がある場合はそれを使用してください。
   例:
   - pip install duckdb psutil openai pyyaml

4. 初期 .env を作成:
   - 対話式ウィザードを使う: python -m kabusys.config_setup
     → .env がプロジェクトルートに作成されます（既存 .env を読み込んで更新可）
   - 手動で作る場合は .env.example を参照してください（リポジトリに例が無い場合は下記「推奨環境変数」を参照）。

5. 設定検証:
   - python -m kabusys.validate_config
   - 警告を失敗扱いにする: python -m kabusys.validate_config --strict

6. データディレクトリ等の準備:
   - デフォルトでは `data/`、`logs/` が使用されます。実行時に自動作成されますが、権限等を確認してください。

注意:
- 自動で .env を読み込む挙動は Settings モジュールで実装されています。自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- .env.local が存在する場合は .env より優先して上書きロードされます（ただし OS 環境変数は保護されます）。

---

## 主要環境変数（抜粋・必須／任意）

必須（起動前に設定）:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

一般的設定:
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）
- LOG_DIR: ログ出力先ディレクトリ（デフォルト: logs）
- OPENAI_API_KEY: OpenAI API を使う機能で必要
- PAPER_FILL_MODE: ペーパートレードの約定モード（instant|partial|never|reject, デフォルト: instant）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（0/1, デフォルト: 0）

監視系:
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング秒数（デフォルト: 60）

その他:
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE 通知連携（任意）

.env の自動読み込み順:
- OS 環境変数 > .env.local > .env

---

## 使い方（実行例）

- 環境変数を設定 (.env に保存済みを前提)。

1) 設定ウィザード（対話式）
   - python -m kabusys.config_setup

2) 設定検証
   - python -m kabusys.validate_config
   - 厳格モード: python -m kabusys.validate_config --strict

3) ExecutionEngine 起動（本番 / ペーパー）
   - 本番: KABUSYS_ENV=live python -m kabusys.run_execution
   - ペーパートレード: KABUSYS_ENV=paper_trading python -m kabusys.run_execution
     - ペーパートレード時は MockBrokerClient を使用し PAPER_TRADING_SQLITE_PATH に記録します。
   - 実行中は data/execution.pid（デフォルト）に PID を出力します。
   - 停止を指示するには data/stop_requested.flag（stop フラグ）を作成してください（監視プロセスも同様の stop フラグを監視します）。

4) Monitoring 起動（常駐ポーリング）
   - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
   - MONITOR_POLL_INTERVAL を与えない場合は 60 秒がデフォルト。
   - 監視は Settings.sqlite_path（monitoring.db）にログを記録します（monitoring は環境にかかわらず本番 sqlite_path を使用する設計）。

5) Paper Trading 検証レポート生成
   - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
   - DB を明示する場合:
     python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

6) AI 系処理（プログラム的利用）
   - ニューススコアリング: kabusys.ai.score_news(conn, target_date, api_key=None)
   - レジーム判定: kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
   - これらを使うには OPENAI_API_KEY が必要です（引数で渡すことも可）。

ログ:
- setup_logging により stdout と logs/<app_name>.log（日次ローテーション）が出力されます。

Kill / Stop:
- KillSwitch は監視基準（ドローダウン・ポジション上限等）に到達した場合に data/kill.flag を書き込みます。ExecutionEngine は起動時に kill.flag をチェックし、`KILL_FLAG_CLEAR_ON_START` の設定次第では起動時に自動クリアされる可能性があります（本番では 0 を推奨）。

---

## ディレクトリ構成（抜粋）

以下は主要ファイル・モジュールの一覧（リポジトリ内 src/kabusys を想定）。

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / Settings 管理（.env 自動読み込み含む）
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリング起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py  — Paper Trading 検証レポート生成
  - ai/
    - __init__.py
    - news_nlp.py             — ニュース NLP スコアリング（OpenAI）
    - regime_detector.py      — 市場レジーム判定（OpenAI）
  - portfolio/
    - __init__.py
    - portfolio_builder.py    — 候補選定・重み計算
    - risk_adjustment.py      — セクターキャップ・レジーム乗数
    - position_sizing.py      — 株数決定・資金配分ロジック
  - research/
    - __init__.py
    - factor_research.py      — モメンタム / バリュー / ボラティリティ
    - feature_exploration.py  — 将来リターン・IC・統計サマリ
  - monitoring/
    - monitoring_db.py        — SQLite テーブル初期化・読み書きラッパ
    - system_monitor.py       — システム稼働・データ鮮度監視
    - trade_monitor.py        — （トレード監視モジュール）
    - risk_monitor.py         — ドローダウン / ポジション上限監視
    - kill_switch.py          — Kill Switch 実装（kill.flag）
    - monitoring_engine.py    — 各 Monitor の統合/ポーリング
    - alert_manager.py        — （アラート送信の統合）※実装参照
  - execution/                — Execution 関連コンポーネント（Engine, BrokerFactory 等）
  - utils/
    - logging_setup.py       — ログ設定ユーティリティ
    - process_priority.py    — プロセス優先度 / CPU affinity 設定
    - __init__.py
  - data/ (外部データ処理関連モジュール参照)
  - strategy/ (戦略本体モジュール、設計ドキュメント参照)

注: 上の一覧は主要ファイルを抜粋したものです。その他の補助モジュールや未表示の実装ファイルが存在する場合があります。

---

## 注意点・運用メモ

- 監視（monitoring）は設計上、KABUSYS_ENV にかかわらず Settings.sqlite_path（本番監視 DB）を使用します。ペーパートレード用 DB は run_execution が担当して分離します。
- run_execution は起動時に data/stop_requested.flag（または data/kill.flag の存在等）を確認し、既に停止フラグがある場合は起動しません。
- OpenAI を利用する機能は API 呼び出しの失敗に対してリトライ・フォールバックの実装がなされていますが、API キーや利用ポリシーには注意してください。
- ログディレクトリ作成に失敗した場合はファイル出力を行わず stdout のみで動作します。ログディレクトリの権限を事前に確認してください。
- .env の自動読み込みはプロジェクトルート（.git または pyproject.toml を基準）を検索して行われます。CWD に依存しない設計ですが、プロジェクトルートが見つからない場合は自動ロードをスキップします。

---

## サンプル .env（最小例）

以下は .env に最低限設定すべき項目の例（機密値は適切に設定してください）:

JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here
KABU_API_PASSWORD=your_kabu_api_password_here
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
LOG_LEVEL=INFO
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxx

---

この README はコードベース内の docstring、関数名、起動スクリプトに基づいて作成しています。実行前に必ず `python -m kabusys.validate_config` で設定を確認してください。必要であれば、さらに運用手順 (systemd / supervisor / docker compose など) を追加してください。