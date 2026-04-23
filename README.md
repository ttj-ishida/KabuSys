# KabuSys

日本株自動売買システムのコンポーネント群（ライブラリ＋起動スクリプト／ツール群）

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株の自動売買・リサーチ・監視を目的としたコードベースです。  
主な機能は以下のとおりです。

- ExecutionEngine（発注エンジン）とペーパートレード分離運用
- 監視コンポーネント（System / Trade / Risk）と Kill Switch（フラグファイルによる停止）
- ポートフォリオ構築（候補選定・重み付け・ポジションサイズ算出）
- リサーチモジュール（ファクター計算・将来リターン・IC 計算など）
- ニュースの NLP ベースセンチメント評価（OpenAI を利用）
- 各種 CLI ユーティリティ（.env ウィザード・設定検証・レポート生成）
- ログ設定・プロセス優先度設定など運用ユーティリティ

設計方針として、DB（SQLite / DuckDB）を使った永続化と、実運用向けの冪等性・フェイルセーフ処理が盛り込まれています。

---

## 主な機能一覧

- 起動スクリプト
  - run_execution.py : ExecutionEngine の起動（KABUSYS_ENV に応じて本番 or paper_trading）
  - run_monitoring.py : SystemMonitor のポーリング起動（MONITOR_POLL_INTERVAL で間隔を調整可能）
- 設定管理
  - config_setup.py : .env を対話式に作成・更新するウィザード
  - validate_config.py : 環境変数 / config/*.yaml の事前検証ツール（--strict オプションあり）
- 監視
  - monitoring_engine.py : 各 Monitor を束ねるエンジン（ポーリング / アラート / Kill Switch）
  - system_monitor.py / trade_monitor.py / risk_monitor.py : それぞれの監視ロジック
  - monitoring_db.py : 監視用 SQLite スキーマと永続化 API
  - kill_switch.py : フラグファイルによる ExecutionEngine 停止の実装
- 発注・リスク管理（execution 以下に実装）
  - BrokerClientFactory（環境に応じてモック or 実クライアント）
  - ExecutionEngine / OrderManager / RiskManager / Reconciler 等
- ポートフォリオ構築（純粋関数）
  - portfolio_builder, position_sizing, risk_adjustment
- リサーチ（duckdb を用いたファクター計算等）
  - factor_research.py, feature_exploration.py（IC, forward returns 等）
- AI（OpenAI）連携
  - news_nlp.py : ニュース記事から銘柄ごとのセンチメントを生成して ai_scores に保存
  - regime_detector.py : マクロ＋ETF MA200 を組合せた市場レジーム推定
- ツール
  - tools/paper_verification_report.py : ペーパートレードの検証レポート生成

---

## セットアップ手順（開発 / 実行前準備）

1. Python バージョン
   - Python 3.10+ を推奨（型注釈や | を使った union を使用）

2. 依存ライブラリ（最低限）
   - duckdb
   - psutil
   - openai （AI 機能を使う場合）
   - PyYAML（validate_config の YAML 検証を行う場合）
   - 例（venv 作成後）:
     - pip install duckdb psutil openai PyYAML

   ※ requirements.txt がある場合はそれを利用してください。

3. プロジェクトルートで .env を作成
   - 対話式ウィザード:
     - python -m kabusys.config_setup
   - もしくは .env.example を参考に作成してください。
   - 必須環境変数:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - よく使う環境変数（デフォルトは括弧内）:
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
     - DUCKDB_PATH (data/kabusys.duckdb)
     - SQLITE_PATH (data/monitoring.db)
     - PAPER_TRADING_SQLITE_PATH (data/paper_trading.db)
     - LOG_LEVEL (INFO)
     - OPENAI_API_KEY （AI を使う場合）
     - PAPER_FILL_MODE ("instant" | "partial" | "never" | "reject")

4. 設定検証（推奨）
   - python -m kabusys.validate_config
   - --strict を付けると警告も FAIL 扱いで exit code 1

5. ディレクトリ作成
   - 実行ログやフラグファイル用ディレクトリが必要（通常自動作成されますが手動で確認してもよい）
     - data/
     - logs/

6. DB 初期化
   - 起動スクリプト（run_execution / run_monitoring）が内部で必要なテーブル作成（init_monitoring_db）を行います。

---

## 使い方（起動例 / CLI）

- ExecutionEngine 起動（本番 or paper_trading を .env の KABUSYS_ENV で切替）
  - デフォルト（.env で KABUSYS_ENV を設定）:
    - python -m kabusys.run_execution
  - 注意: KABUSYS_ENV=paper_trading のときは MockBrokerClient を利用し、paper_trading 用 DB（PAPER_TRADING_SQLITE_PATH）に記録されます。

- Monitoring 起動（ポーリング監視）
  - ポーリング間隔を環境変数で上書き:
    - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - run_monitoring は MONITOR_POLL_INTERVAL を秒で読み取り、デフォルトは 60 秒。
  - 監視は Settings.env にかかわらず本番 sqlite_path（SQLITE_PATH）を使用して監視ログを保存します。

- .env 作成ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - オプション --db で SQLite ファイルを指定可能（環境変数 PAPER_TRADING_SQLITE_PATH でも可）

- AI 関連（ライブラリ関数）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - これらは DuckDB 接続（duckdb.connect(...).cursor()）を引数に受け取ります。OPENAI_API_KEY を環境変数で指定していれば api_key を省略できます。

- Kill Switch / 停止フラグ
  - ExecutionEngine は data/kill.flag（Settings.kill_flag_path）や data/stop_requested.flag（実行スクリプトで使用）により外部から停止できます。
  - KillSwitch はリスク条件に応じて data/kill.flag を書き込みます。

---

## 環境変数（主要）

- JQUANTS_REFRESH_TOKEN : J-Quants API トークン（必須）
- KABU_API_PASSWORD : kabuステーション API パスワード（必須）
- KABUSYS_ENV : 実行環境（development / paper_trading / live）デフォルト: development
- DUCKDB_PATH : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH : 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH : ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL : ログレベル（DEBUG/INFO/...）デフォルト: INFO
- OPENAI_API_KEY : OpenAI API キー（AI 機能を使う場合）
- MONITOR_POLL_INTERVAL : run_monitoring のポーリング間隔（秒、デフォルト 60）
- PAPER_FILL_MODE : ペーパートレードの約定モード（instant/partial/never/reject）

---

## 運用に関する注意点

- run_monitoring は monitoring 用の SQLite を使用してログを保存します（Settings に従う）。Monitoring は KABUSYS_ENV にかかわらず sqlite_path を参照します。
- run_execution は KABUSYS_ENV=paper_trading の場合、paper_sqlite_path を使用して本番 DB と完全分離します。
- process priority の設定は psutil を利用します。権限不足などで設定に失敗する場合は警告ログが出てスキップされます。
- OpenAI の呼び出し部分はリトライやバックオフを実装しているものの、API キーや料金、レートリミットに注意してください。
- .env は機密情報を含むため、絶対にリポジトリへコミットしないでください。

---

## ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py
- config.py                   — 環境変数 / Settings
- config_setup.py             — .env ウィザード
- validate_config.py          — 設定検証 CLI
- run_execution.py            — ExecutionEngine 起動スクリプト
- run_monitoring.py           — SystemMonitor 起動スクリプト

- execution/                   — 発注エンジン周り（BrokerFactory, Engine 等）
- monitoring/
  - monitoring_db.py           — SQLite スキーマ + DB API
  - monitoring_engine.py       — 各 Monitor を束ねる
  - system_monitor.py
  - trade_monitor.py
  - risk_monitor.py
  - kill_switch.py
  - alert_manager.py
- portfolio/
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py
- research/
  - factor_research.py
  - feature_exploration.py
- ai/
  - news_nlp.py                — ニュース NLP スコアリング（OpenAI）
  - regime_detector.py         — 市場レジーム判定
- tools/
  - paper_verification_report.py
- utils/
  - logging_setup.py
  - process_priority.py

その他:
- data/  （デフォルトの DB / pid / フラグを置く想定）
- logs/  （ログファイル保存先）

（実際のファイル構成はプロジェクトルートでご確認ください）

---

## 開発者向けメモ

- DuckDB 接続を渡して計算する設計になっているため、リサーチ関数は副作用が少なくテストが容易です。
- monitoring_db.init_monitoring_db はテーブル作成＋マイグレーション（列追加）を冪等に行います。
- AI 周りのテストは API 呼び出しをラップした関数を patch/mock することで外部依存を切り離して行えます（コード中に示された _call_openai_api をモックするパターンなど）。

---

必要であれば README にさらに「起動時の systemd / supervisor の設定例」や「Dockerfile」「requirements.txt」のテンプレート等を追記できます。どの情報を優先して追加しますか？