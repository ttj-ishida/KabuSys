# KabuSys

日本株向け自動売買 / 研究プラットフォームの一部実装。  
ポートフォリオ構築、ポジションサイズ決定、監視・リスク管理、ペーパートレード検証、OpenAI を用いたニュース NLP / レジーム検出などのユーティリティ群を含みます。

---

## プロジェクト概要
KabuSys は日本株自動売買システムのコンポーネント群です。本リポジトリには以下の主要機能が含まれます。

- ExecutionEngine（発注実行）および Paper Trading（ペーパートレード）サポート
- Monitoring（システム稼働、注文・リスク監視、Kill Switch）
- Portfolio Construction（候補選定・重み付け・ポジションサイズ計算）
- Research（ファクター計算、将来リターン、IC 計算など）
- AI モジュール（OpenAI を用いたニュースのセンチメント評価、レジーム判定）
- ツール（設定ウィザード、設定検証、ペーパートレード検証レポート生成）

設計方針の一部：
- DB（DuckDB / SQLite）を使ったデータ処理と永続化
- 実行環境（KABUSYS_ENV）に応じて paper_trading を分離
- OpenAI 呼び出しはフェイルセーフでリトライ・フォールバック処理あり

---

## 主な機能一覧
- 設定ウィザード: python -m kabusys.config_setup
- 設定検証: python -m kabusys.validate_config
- 実行エンジン起動: python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、data/paper_trading.db に記録
- 監視ループ起動: python -m kabusys.run_monitoring
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で変更可能（デフォルト 60秒）
- ペーパートレード検証レポート: python -m kabusys.tools.paper_verification_report
- ポートフォリオ構築ユーティリティ（select_candidates, calc_equal_weights, calc_score_weights）
- ポジションサイズ計算（risk_based / equal / score）
- セクターキャップ / レジーム倍率適用
- AI: ニュースセンチメントスコアリング（kabusys.ai.news_nlp.score_news）、市場レジーム判定（kabusys.ai.regime_detector.score_regime）
- 監視用 DB ラッパー（MonitoringDB）と各種 Monitor（SystemMonitor, TradeMonitor, RiskMonitor）および MonitoringEngine
- ロギングセットアップユーティリティ（kabusys.utils.logging_setup）

---

## セットアップ手順（開発用/簡易）
1. 必要な Python バージョン
   - Python 3.10 以上（| 型注釈などを使用）

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  または .venv\Scripts\activate

3. 必要パッケージのインストール（例）
   - pip install duckdb psutil openai pyyaml
   - 補足:
     - duckdb: データ分析用
     - psutil: プロセス/システム情報取得
     - openai: OpenAI API 呼び出し
     - pyyaml: validate_config が config/*.yaml を検証する場合に必要（任意）

4. .env の作成
   - 対話式ウィザード:
     - python -m kabusys.config_setup
   - またはプロジェクトルートに手動で .env を配置
   - 重要な環境変数（最低限）
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
     - （必要に応じて）OPENAI_API_KEY

5. 設定検証
   - python -m kabusys.validate_config
   - --strict をつけると警告もエラー扱い（exit 1）

6. データディレクトリの準備（自動作成されることが多い）
   - デフォルト DB パス: data/kabusys.duckdb, data/monitoring.db, data/paper_trading.db
   - ログディレクトリ: logs/（kabusys.utils.logging_setup が作成）

---

## 主要環境変数（主なもの）
- KABUSYS_ENV: 実行環境。development / paper_trading / live（デフォルト: development）
- JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（AI 機能使用時）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 SQLite（デフォルト data/paper_trading.db）
- PAPER_FILL_MODE: paper_trading の注文約定挙動（instant|partial|never|reject）（デフォルト instant）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- LOG_DIR: ログ出力ディレクトリ（デフォルト logs/）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（1=クリア、0=クリアしない）

---

## 使い方（コマンド例）
- 環境設定ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 厳格モード（警告も失敗扱い）:
    - python -m kabusys.validate_config --strict

- 実行エンジン起動
  - python -m kabusys.run_execution
  - 備考:
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用 DB に分離して動作
    - 起動時に data/stop_requested.flag が存在すると起動しない
    - 実行中は data/execution.pid に PID を書き込みます

- 監視ループ起動
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング周期を秒指定可能（例: MONITOR_POLL_INTERVAL=30）
  - 監視は本番 sqlite_path（settings.sqlite_path）を利用（環境にかかわらず監視 DB は本番パスを使う実装）

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

- AI 機能の利用例（Python スクリプト内から）
  - OpenAI API キー準備（環境変数 OPENAI_API_KEY を設定）
  - 例（ニューススコアリング）:
    - from kabusys.ai.news_nlp import score_news
    - import duckdb, datetime
    - conn = duckdb.connect("data/kabusys.duckdb")
    - score_news(conn, target_date=datetime.date(2026,4,10))
  - 例（レジーム判定）:
    - from kabusys.ai.regime_detector import score_regime
    - score_regime(conn, target_date=datetime.date(2026,4,10))

---

## Kill / Stop フラグ
- data/kill.flag
  - KillSwitch（監視）によって書き込まれるフラグ。ExecutionEngine は Settings.kill_flag_path（デフォルト data/kill.flag）を参照して停止判断を行います。
  - 実行時に KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時にクリアされます（本番では 0 推奨）。

- data/stop_requested.flag
  - run_monitoring / run_execution はこのフラグファイルの存在をチェックしてループを終了またはエンジン停止を行います（外部からの停止要求に利用）。

---

## ロギング
- 共通設定関数: kabusys.utils.logging_setup.setup_logging(app_name="…")
  - stdout（StreamHandler）と日次ローテートファイル（logs/<app_name>.log）を設定
  - デフォルト保持日数 30 日
  - 環境変数 LOG_DIR / LOG_LEVEL で挙動を制御

---

## ディレクトリ構成（主なファイル）
以下は src/kabusys をルートとした主要なファイル・ディレクトリの例です。

- src/kabusys/
  - __init__.py
  - config.py                     — 環境変数 / 設定管理
  - config_setup.py               — .env 対話式ウィザード
  - validate_config.py            — 設定検証 CLI
  - run_execution.py              — ExecutionEngine 起動スクリプト
  - run_monitoring.py             — Monitoring ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート生成
  - ai/
    - news_nlp.py                 — ニュース NLP（OpenAI）によるスコアリング
    - regime_detector.py          — マーケットレジーム判定（OpenAI + MA）
  - monitoring/
    - monitoring_db.py            — 監視用 SQLite 永続化層
    - monitoring_engine.py
    - system_monitor.py
    - trade_monitor.py            — （存在する前提。注文監視ロジック）
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py            — （アラート送信ロジック、存在する場合）
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - utils/
    - logging_setup.py
    - process_priority.py
  - execution/                    — ExecutionEngine 周りの実装（BrokerFactory など）
  - data/                         — デフォルトで使用されるデータ/DB/flag の配置（プロジェクトルート）

（上記は主要モジュールの抜粋です。詳細はソースツリーを参照してください。）

---

## 実運用上の注意
- KABUSYS_ENV=live の場合は設定ミスにより実際に発注が行われるため、validate_config で警告・設定を慎重に確認してください。
- OpenAI を利用する機能は API 利用料が発生します。API キーの取り扱いに注意してください。
- ペーパートレード用データベースは本番 DB と明示的に分離されます（PAPER_TRADING_SQLITE_PATH）。
- ログや DB のパス、Kill Switch の挙動等は .env で管理できます。.env は決してリポジトリにコミットしないでください。

---

## 貢献 / 拡張案（例）
- execution/order_manager 周りの Broker 実装差し替え（実ブローカー接続やモック）
- trade_monitor の詳細実装（滞留注文検出、価格異常検出ロジック）
- alert_manager: LINE / Slack / メールなど通知チャネルの追加
- portfolio の lot_size を銘柄ごとに対応する（マスタ参照）
- AI 呼び出しのバッチ最適化・コスト制御（トークン上限対応）

---

README はここまでです。より具体的な使い方（各モジュールの引数や戻り値、DB スキーマの詳細）が必要であれば、そのセクションを追加してドキュメント化します。どの部分を掘り下げますか？