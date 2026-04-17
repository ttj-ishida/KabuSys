# KabuSys

日本株向けの自動売買システム（ライブラリ/実行スクリプト群）のミニマム実装。  
このリポジトリには、実行エンジン起動スクリプト、監視（Monitoring）周り、ポートフォリオ構築、ファクター計算、AI（ニュース NLP / レジーム判定）連携、各種ユーティリティが含まれます。

以下はプロジェクトを始めるための README（日本語）です。

---

## プロジェクト概要

KabuSys は以下の機能群を備えた自動売買フレームワークの一部です：

- ExecutionEngine を起動して発注／注文管理を行う（実口座 / ペーパートレード両対応）
- 監視サービス（System / Trade / Risk Monitor）による稼働監視、Kill Switch による安全停止
- ポートフォリオ構築（候補選定、重み付け、ポジションサイズ算出）
- リサーチ用ファクター計算（モメンタム、ボラティリティ、バリュー等）
- AI モジュール（OpenAI を用いたニュースセンチメント評価、レジーム判定）
- 運用用ツール（.env ウィザード、設定検証、Paper Trading 検証レポート生成）

設計方針として、外部 API（ブローカー等）へのアクセスをテスト／本番で切り替えられる設計、データ永続化は主に DuckDB / SQLite を利用します。

---

## 主な機能一覧

- 実行関連
  - run_execution.py: ExecutionEngine の起動（KABUSYS_ENV により paper_trading を分離）
- 監視関連
  - run_monitoring.py: SystemMonitor のポーリング起動スクリプト
  - MonitoringEngine / SystemMonitor / TradeMonitor / RiskMonitor / AlertManager
  - kill_switch による flag ファイル書き込みで ExecutionEngine を停止可能
- 環境設定・検証
  - config_setup.py: 対話式で .env を生成・更新するウィザード
  - validate_config.py: .env や config/*.yaml の事前検証ツール
- 分析・リサーチ
  - research.factor_research: モメンタム / ボラティリティ / バリュー算出
  - research.feature_exploration: 将来リターン計算、IC（Information Coefficient）等
- ポートフォリオ構築
  - portfolio.portfolio_builder, position_sizing, risk_adjustment
- AI（OpenAI）
  - ai.news_nlp: ニュースから銘柄別センチメントを計算して ai_scores に格納
  - ai.regime_detector: ETF の MA 等と LLM によるマクロセンチメントを組み合わせて市場レジーム判定
- ツール
  - tools.paper_verification_report: Paper Trading の検証レポート出力（期間指定可）
- ユーティリティ
  - utils.process_priority: プロセス優先度 / CPU affinity 設定ユーティリティ
  - monitoring/monitoring_db.py: SQLite ベースの監視ログ永続化層

---

## セットアップ手順

前提: Python 3.9+ を想定（実装の型ヒント等に依存）。プロジェクトルートは `.git` または `pyproject.toml` を基に自動検出されます。

1. リポジトリをクローンしてワークディレクトリへ移動
   - git clone ... ; cd <repo>

2. 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   - pip install --upgrade pip
   - pip install psutil duckdb requests openai
   - （オプション）PyYAML があれば validate_config の YAML 検証が有効化されます: pip install pyyaml

   注意: requirements.txt が無い場合は上記パッケージを個別にインストールしてください。

4. 初期環境変数 (.env) の作成
   - 対話式ウィザードを使う（推奨）:
     - python -m kabusys.config_setup
   - 生成後、必須環境変数（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD など）を設定してください。

5. 設定検証
   - python -m kabusys.validate_config
   - 警告も厳格に扱う場合は `--strict` を付与します。

6. 必要なディレクトリの作成
   - デフォルトでは data/ 以下に DB ファイルや PID/flag ファイルが作られます。自動作成されることもありますが、権限等の問題があれば手動で作成してください。

---

## 主要環境変数（抜粋）

- KABUSYS_ENV: 実行環境（development | paper_trading | live） デフォルト: development
- JQUANTS_REFRESH_TOKEN: J-Quants API リフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: SQLite（監視）ファイルパス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用の SQLite（デフォルト: data/paper_trading.db）
- OPENAI_API_KEY: OpenAI 使用時に必要（AI モジュールを使う場合）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: AlertManager（LINE）用トークン / 送信先
- LOG_LEVEL: ログレベル（DEBUG/INFO/…）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）
- PAPER_FILL_MODE: paper_trading 時の MockBroker の fill モード（instant|partial|never|reject）
- KILL_FLAG_PATH: kill.flag のパス（デフォルト: data/kill.flag）
- PID_FILE_PATH: execution PID のパス（デフォルト: data/execution.pid）
- KILL_FLAG_CLEAR_ON_START: 1 にすると ExecutionEngine 起動時に kill.flag を自動クリア（本番では 0 推奨）

環境変数は .env / .env.local を通じて設定できます（config_setup.py を推奨）。

---

## 使い方（主要スクリプト / コマンド）

- 対話式で .env を作る：
  - python -m kabusys.config_setup

- 設定を検証する：
  - python -m kabusys.validate_config
  - 厳格モード: python -m kabusys.validate_config --strict

- ExecutionEngine を起動する（発注エンジン）：
  - python -m kabusys.run_execution
  - 補足:
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使い data/paper_trading.db に記録して本番 DB と分離します。
    - 起動時に data/stop_requested.flag が存在すると起動せずに終了します。
    - 停止は data/stop_requested.flag を作成するか、ExecutionEngine 側で受ける kill.flag により安全停止されます。
    - PID ファイルを書き出します（デフォルト: data/execution.pid）。

- Monitoring を起動する（SystemMonitor のポーリング）：
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可能（デフォルト 60）。
  - Monitoring は KABUSYS_ENV に関係なく本番 sqlite_path を使用します（監視は常に本番 DB を監視する想定）。

- Paper Trading 検証レポート（CLI）：
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db オプションで SQLite ファイルを指定可能（環境変数 PAPER_TRADING_SQLITE_PATH を優先）。

- AI モジュール（プログラムから呼ぶ）
  - ニュース NLP（銘柄別スコア算出）:
    - from kabusys.ai.news_nlp import score_news
    - score_news(duckdb_conn, target_date, api_key="...")  # api_key を省略すると OPENAI_API_KEY を参照
  - レジーム判定:
    - from kabusys.ai.regime_detector import score_regime
    - score_regime(duckdb_conn, target_date, api_key="...")

- 注意点（運用）
  - process_priority: 起動スクリプトは最初にプロセス優先度を "high" に設定しようとします。環境によっては権限が必要で、失敗時は警告が出ます。
  - OpenAI を使う機能は API キーが必須です（OPENAI_API_KEY）。

---

## データと永続化

- DuckDB: 分析用（prices_daily / raw_financials / raw_news / ai_scores / market_regime 等）
  - デフォルトファイル: data/kabusys.duckdb
- SQLite: 監視用・Paper Trading 用など。監視 DB は monitoring_db.init_monitoring_db() で必要なテーブルを冪等に初期化します。
  - 監視 DB のデフォルトファイル: data/monitoring.db
  - Paper Trading DB のデフォルトファイル: data/paper_trading.db

監視用 SQLite (monitoring_db) は次のテーブルを作成します（概略）:
- system_status (cpu/memory/disk/process_ok etc.)
- trade_logs (発注イベントのログ、latency_ms 等)
- positions (保有ポジション)
- risk_logs (リスクイベント)
- dashboard (集計情報, peak_value 等)

---

## ディレクトリ構成

（リポジトリの src/kabusys 配下の主要ファイル・モジュール）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / Settings 管理、自動 .env ロードロジック
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリング起動スクリプト
  - utils/
    - process_priority.py    — プロセス優先度 / CPU affinity ユーティリティ
  - monitoring/
    - monitoring_db.py       — SQLite 永続化層
    - monitoring_engine.py   — 各 Monitor を束ねるエンジン
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - alert_manager.py
    - kill_switch.py
  - execution/                — 実行系（OrderRepository, ExecutionEngine, BrokerFactory 等）※一部参照あり
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py             — ニュース NLP（OpenAI）
    - regime_detector.py      — レジーム判定（OpenAI）
  - tools/
    - paper_verification_report.py
  - data/                     — 実行時に生成される (data/kabusys.duckdb, data/monitoring.db, data/paper_trading.db, flags, pid など)

（注）実際のリポジトリで他に `data/`, `config/` などが存在する可能性があります。config/*.yaml は validate_config.py で参照されます。

---

## 運用上の注意 / トラブルシュート

- .env は絶対にリポジトリへコミットしないでください（config_setup でも注意喚起があります）。
- データベースファイルや data/ ディレクトリの権限に注意（プロセスが書き込めること）。
- psutil による優先度設定や cpu_affinity 設定は環境によって失敗する可能性があります（警告ログが出ますが、処理自体は継続されます）。
- OpenAI API 呼び出しはレートリミットやネットワークエラーが発生し得ます。モジュール内ではリトライロジックやフェイルセーフ（失敗時はスコア 0 など）を備えていますが、API キーや使用量は運用側で管理してください。
- Paper Trading は本番データベースと完全に分離されます。`KABUSYS_ENV=paper_trading` を利用してください。
- kill.flag / stop_requested.flag により外部から安全に停止できます。`KILL_FLAG_CLEAR_ON_START` を本番で `1` にするのは危険です（本番では `0` 推奨）。

---

## 開発者向けメモ

- 監視ループのポーリング間隔は MONITOR_POLL_INTERVAL（秒）で上書き可能。
- Monitoring は KABUSYS_ENV に依存せず本番 sqlite_path に接続して監視を行います（監視は本番 DB を参照する前提）。
- paper_verification_report は paper_trading DB の trade_logs / risk_logs / system_status 等を参照して検証レポートを出力します。期間指定（--from / --to）や --db による DB 指定が可能です。
- DuckDB 接続を渡して関数を直接呼ぶ設計（テストが容易）。AI 呼び出しは内部で OpenAI クライアントを生成するため、テスト時には _call_openai_api を patch して差し替えることを想定しています。

---

必要であれば README にサンプル .env のテンプレートや、より詳細な運用手順（systemd / Supervisor 用のサービス定義、ログローテーション、バックアップ手順など）を追加します。どの情報を重点的に追加したいか教えてください。