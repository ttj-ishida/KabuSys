# KabuSys

日本株向けの自動売買システムのコードベースドキュメント（README）。この README はリポジトリ内の主要なスクリプト・モジュールを元に作成しています。

---

## プロジェクト概要

KabuSys は日本株の自動売買（本番 / ペーパートレード）とそれに付随する監視・リサーチ・AI ツール群を含むパッケージです。主要機能は以下の通りです：

- 発注エンジン（ExecutionEngine） — ブローカークライアント経由で注文を実行／管理
- 監視（Monitoring） — システム稼働状況、注文・約定ログ、リスク（ドローダウン・ポジション数）を定期的に記録・通知
- ポートフォリオ構築（選定・重み算出・ポジションサイズ計算・セクター制限）
- リサーチ（ファクター計算・特徴量探索）
- AI 支援（ニュース NLP によるセンチメント評価、レジーム判定）
- 開発支援ツール（.env ウィザード、設定検証、ペーパートレード検証レポート生成）

設計上の特徴：
- 設定は .env（環境変数）ベース。config モジュールで安全に読み込み/検証。
- 本番とペーパートレードのデータは分離（paper_trading 用 DB を使用可能）。
- DuckDB を分析用に利用、SQLite を監視/ログ永続化用に利用。
- OpenAI（gpt-4o-mini 等）を用いたニュース解析・レジーム判定をサポート（任意）。

---

## 主な機能一覧

- run_execution.py
  - ExecutionEngine を起動。KABUSYS_ENV が `paper_trading` の場合は MockBrokerClient を使い、data/paper_trading.db に記録。
  - 起動時にプロセス優先度を "high" に設定し、PID ファイルを管理。
  - data/stop_requested.flag を検知すると安全に停止。

- run_monitoring.py
  - SystemMonitor のポーリングループを起動。ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL`（秒）で上書き可能（デフォルト 60 秒）。
  - 監視ログは常に本番用 SQLite（Settings.sqlite_path）を使用。

- monitoring モジュール
  - system_monitor, trade_monitor, risk_monitor, monitoring_engine, monitoring_db, kill_switch, alert_manager 等。
  - system_status / trade_logs / positions / risk_logs / dashboard テーブルを管理する init_monitoring_db。

- portfolio モジュール
  - 銘柄選定、重み計算、ポジションサイズ算出、セクター上限・レジーム乗数適用などの純粋関数群。

- research モジュール
  - ファクター計算（momentum / volatility / value）
  - 将来リターン・IC 計算・統計サマリー等

- ai モジュール
  - news_nlp.score_news: raw_news を LLM で評価し ai_scores に保存（OpenAI API 必須）
  - regime_detector.score_regime: マクロニュース + 1321（ETF）MA200 を組み合わせて市場レジーム判定

- utils
  - logging_setup: 統一ログ設定（stdout + 日次ローテートファイル）
  - process_priority: プロセス優先度 / CPU affinity 設定ユーティリティ
  - config: .env 自動読み込み（.env, .env.local）、Settings オブジェクト

- tools
  - paper_verification_report: ペーパートレード DB から検証レポートを生成（稼働率・約定率・レイテンシ等）

---

## セットアップ手順（クイックスタート）

前提：
- Python 3.9+（プロジェクトで要求される最小バージョンに合わせてください）
- git クローン済みのリポジトリルートを作業ディレクトリとすることを想定

1. 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. 依存パッケージのインストール（pip install で必要なライブラリを入れる）
   - 必要パッケージ（代表例）:
     - duckdb
     - psutil
     - openai
     - PyYAML（設定検証で YAML のパースを行う場合に任意）
   - 例:
     - pip install duckdb psutil openai PyYAML

   （requirements.txt がある場合はそれを使ってください）

3. .env の初期作成
   - ウィザードを使う（推奨）:
     - python -m kabusys.config_setup
   - 手動で作成する場合は .env.example を参照して .env を作成してください。
   - 自動読み込み:
     - config モジュールはプロジェクトルート検出に成功すれば `.env` と `.env.local` を自動読み込みします。
     - 自動読み込みを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

4. 設定検証（任意だが推奨）
   - python -m kabusys.validate_config
   - 警告をエラー扱いにする場合:
     - python -m kabusys.validate_config --strict

5. データディレクトリの作成（必要に応じて）
   - デフォルトでは `data/` に DB や PID / フラグファイルを置きます。ログは `logs/` に出力されます。
   - 例:
     - mkdir -p data logs

---

## 環境変数（主なもの）

（.env ウィザード / Settings クラスに基づく代表的な変数）

- JQUANTS_REFRESH_TOKEN: J-Quants API リフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabuステーション API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- KABUSYS_ENV: 実行環境（development / paper_trading / live）（デフォルト: development）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB の SQLite パス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: ペーパートレード時の約定モデル（instant | partial | never | reject、デフォルト: instant）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- OPENAI_API_KEY: OpenAI API キー（AI モジュール利用時に必須）
- LOG_DIR: ログ出力先ディレクトリ（デフォルト: logs）
- PID_FILE_PATH / KILL_FLAG_PATH 等（Settings でデフォルト指定あり）

モニタリング専用:
- MONITOR_POLL_INTERVAL: run_monitoring.py のポーリング間隔（秒、デフォルト 60）

停止系フラグ:
- data/stop_requested.flag: run_execution / run_monitoring が外部から停止を要求するために監視するフラグファイル（存在すると安全停止）
- data/kill.flag: KillSwitch が書き込むことで ExecutionEngine に停止要求を送る（Kill Switch：ドローダウンやポジション上限を監視して書き込む）

その他:
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると config の .env 自動読み込みを抑制可能（テスト時に便利）

---

## 使い方（主要コマンド例）

- 環境ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- ExecutionEngine 起動
  - python -m kabusys.run_execution
  - 注意:
    - 起動時に data/stop_requested.flag が存在すると起動を中止します。
    - ペーパートレードは KABUSYS_ENV=paper_trading を設定すると専用 DB（PAPER_TRADING_SQLITE_PATH）を使います。

- Monitoring 起動（SystemMonitor のポーリング）
  - python -m kabusys.run_monitoring
  - ポーリング間隔を変更したい場合:
    - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

- AI モジュール（ニューススコアリング / レジーム判定）
  - OpenAI API キーが必要（OPENAI_API_KEY 環境変数）
  - 例（スクリプト経由で呼ぶ想定）:
    - kabusys.ai.news_nlp.score_news(duckdb_conn, target_date, api_key=...)
    - kabusys.ai.regime_detector.score_regime(duckdb_conn, target_date, api_key=...)

- ログ
  - デフォルト出力先: stdout と logs/<app_name>.log（TimedRotatingFileHandler、日次ローテーション、30日保持）
  - app_name は run スクリプトで指定（例: setup_logging(app_name="execution") → logs/execution.log）

- 停止 / Kill Switch
  - 実行中の Engine を停止したい場合は `data/stop_requested.flag` を作成すると run スクリプトが検知して終了します（手動停止のための簡易フラグ）。
  - KillSwitch（監視側）が条件を満たすと `data/kill.flag` に理由を書き込み、ExecutionEngine がそれを検知して停止する仕組みです。ExecutionEngine 起動時に `KILL_FLAG_CLEAR_ON_START` 設定で自動クリアの挙動を制御できます（本番では無効推奨）。

---

## データファイル（デフォルトパス）

- DuckDB: data/kabusys.duckdb
- 監視 SQLite DB: data/monitoring.db
- ペーパートレード SQLite DB: data/paper_trading.db
- ログ: logs/<app_name>.log
- PID ファイル: data/execution.pid（ExecutionEngine が書き込む）
- 停止フラグ: data/stop_requested.flag（ランナーが監視）
- Kill フラグ: data/kill.flag（KillSwitch が作成）

---

## ディレクトリ構成

（リポジトリの src/kabusys 以下を抜粋）

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数 / Settings
  - config_setup.py           — .env ウィザード（対話式）
  - validate_config.py        — 設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — Monitoring ポーリング起動スクリプト
  - tools/
    - __init__.py
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
    - __init__.py
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - monitoring_engine.py
    - kill_switch.py
    - alert_manager.py (参照; 実装ファイルが存在する想定)
  - execution/
    - execution_engine.py
    - broker_factory.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
  - utils/
    - logging_setup.py
    - process_priority.py
    - __init__.py
  - research/（上記）
  - data/（リポジトリ外部データ・生成物）
  - config/（YAML 設定ファイル群: system_config.yaml 等）

※ 実際のリポジトリにより若干の差分がある場合があります。上記は提供コードから抽出した主なファイル構成です。

---

## 開発者向けメモ / 注意点

- 設定自動読込はプロジェクトルート（.git または pyproject.toml を基準）を検出して .env/.env.local を読み込みます。CWD に依存しない設計ですが、パッケージ展開後はプロジェクトルートの検出に注意してください。
- Settings クラスはプロパティで各種設定を提供します。未設定の必須変数は ValueError を発生させます。
- MonitoringDB の初期化は冪等（init_monitoring_db）。既存 DB に対する簡単なマイグレーション（カラム追加）も行われます。
- AI モジュールを利用する場合は OpenAI のレート制限・エラーハンドリングに注意。実装はエクスポネンシャルバックオフ等を入れていますが、API キーとコスト管理は利用者責任です。
- logs ディレクトリの作成に失敗した場合はファイルハンドラが作成されず stdout のみで出力されます。権限等に注意してください。
- ペーパートレードは本番 DB と分離されます（PAPER_TRADING_SQLITE_PATH）。本番 DB を誤って上書きしないよう .env の設定を慎重に行ってください。

---

この README はコードベースの主要な使い方と設定を簡潔にまとめたものです。追加で必要な例や詳細（API 仕様、Strategy / Engine の内部仕様など）があれば教えてください。README を拡張してサンプル .env、運用手順 (systemd / supervisor のユニットファイル例) やデバッグ方法（ログ確認・PID/フラグファイル操作）等も追記できます。