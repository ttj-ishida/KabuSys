# KabuSys

日本株自動売買システムの一部コンポーネント群。ポートフォリオ構築、発注エンジン（ExecutionEngine）、監視（Monitoring）、リサーチ（DuckDB ベースのファクター計算）、およびニュース NLP / レジーム判定などの補助ツールを含みます。

本 README はこのコードベースに含まれる主要な機能・セットアップ方法・実行例・ディレクトリ構成を簡潔にまとめたものです。

---

## プロジェクト概要

- DuckDB / SQLite を用いたデータ処理・永続化（分析用: DuckDB、監視/注文ログ: SQLite）
- 発注系（ExecutionEngine）は本番／ペーパートレードを切り替え可能
- 監視コンポーネント（SystemMonitor / TradeMonitor / RiskMonitor）による稼働・注文・リスク監視
- Kill Switch によるフラグファイルで ExecutionEngine 停止制御
- ニュースを LLM（OpenAI）でスコアリングする AI モジュール（news_nlp）とそれを用いた市場レジーム判定（regime_detector）
- ポートフォリオ構築（候補選定・重み付け・ポジションサイジング）、ファクター計算、特徴量解析の研究用モジュール
- 各種ユーティリティ（ログ設定、プロセス優先度設定、設定ウィザード、設定検証、レポート生成ツール）

---

## 主な機能一覧

- 環境設定管理
  - 対話式 `.env` ウィザード（kabusys.config_setup）
  - 起動前の設定検証（kabusys.validate_config）
- 実行エンジン（Execution）
  - ExecutionEngine 起動スクリプト（python -m kabusys.run_execution）
  - 本番 / ペーパートレード切替（KABUSYS_ENV）
  - Paper trading 時は専用 SQLite（data/paper_trading.db など）へ記録
- 監視（Monitoring）
  - System / Trade / Risk の監視とアラート発行
  - ポーリングループ起動スクリプト（python -m kabusys.run_monitoring）
  - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL` で上書き可能（デフォルト 60 秒）
  - 監視ログは SQLite（default: data/monitoring.db）
- AI / ニュース解析
  - raw_news を LLM でセンチメント化し ai_scores テーブルへ書き込み（kabusys.ai.score_news）
  - マクロニュース + ETF MA 乖離の合成による市場レジーム判定（kabusys.ai.regime_detector.score_regime）
- リサーチ / ファクター
  - Momentum / Volatility / Value 等のファクター計算（DuckDB）
  - 将来リターン計算、IC（情報係数）や統計サマリー
- ツール
  - Paper Trading 検証レポート生成スクリプト（kabusys.tools.paper_verification_report）
- ユーティリティ
  - ログ設定（stdout + 日次ローテートファイル）
  - プロセス優先度・CPU affinity 設定

---

## セットアップ手順（ローカル開発向け）

前提
- Python >= 3.10（構文で PEP 604 の union 型 (X | Y) を使用）
- Git, OS の適切な権限（psutil を使った優先度設定などで権限が必要となることがあります）

1. リポジトリをクローン
   - git clone <repo-url>

2. 仮想環境の作成と有効化
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存パッケージのインストール
   - もし requirements.txt がある場合:
     - pip install -r requirements.txt
   - 無い場合の主要パッケージ例:
     - pip install duckdb psutil openai pyyaml

   （開発では追加でテスト用パッケージ等を導入してください）

4. 環境変数の設定
   - 対話式ウィザードで `.env` を生成:
     - python -m kabusys.config_setup
   - 必須環境変数:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
     - （必要に応じて）OPENAI_API_KEY, LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID
   - 主要な環境変数:
     - KABUSYS_ENV: development | paper_trading | live
     - DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH
     - LOG_LEVEL, LOG_DIR
     - PAPER_FILL_MODE (instant|partial|never|reject)
     - MONITOR_POLL_INTERVAL（監視ループの秒数, default 60）

5. ディレクトリ作成（自動化される場合が多いが事前準備）
   - data/ （SQLite・PID・フラグファイル等）
   - logs/ （ログファイル）

6. 設定検証（起動前に実行推奨）
   - python -m kabusys.validate_config
   - 問題がある場合は指摘に従い .env や config/*.yaml を修正

---

## 使い方（主要コマンド例）

- 環境設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告もエラー扱いになります

- ExecutionEngine 起動
  - python -m kabusys.run_execution
  - 挙動:
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH（デフォルト: data/paper_trading.db）に記録します
    - 起動時に data/stop_requested.flag が存在すると起動を回避します
    - 実行中停止は data/stop_requested.flag をファイル生成することで指示可能（実装上の停止フラグ）

- Monitoring 起動
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒単位で指定可能（デフォルト 60）
  - 監視は Settings.sqlite_path（デフォルト data/monitoring.db）を使用（run_monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を参照します）

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db オプションで SQLite ファイルを指定可能（環境変数 PAPER_TRADING_SQLITE_PATH も利用可）

- プログラム内 API（モジュールの呼び出し例）
  - DuckDB 接続を作成して研究関数を呼び出す:
    - import duckdb
    - conn = duckdb.connect("data/kabusys.duckdb")
    - from kabusys.research import calc_momentum
    - calc_momentum(conn, target_date)
  - AI ニューススコアリング（プログラム的に呼ぶ場合）:
    - from kabusys.ai import score_news
    - score_news(conn, target_date, api_key="sk-...")
  - 市場レジーム判定:
    - from kabusys.ai.regime_detector import score_regime
    - score_regime(conn, target_date, api_key="sk-...")

---

## 重要な運用上の注意

- run_monitoring は実行環境 KABUSYS_ENV にかかわらず Settings.sqlite_path（監視 DB）を使用します。つまり監視データは常に指定の監視 DB に書き込まれます。
- run_execution は KABUSYS_ENV=paper_trading の場合に paper_sqlite_path（別 DB）を使用し、本番 DB とデータを分離します。
- Kill Switch / stop flag:
  - Kill Switch 書き込み: data/kill.flag を書き込むと ExecutionEngine 停止を指示できます（KillSwitch クラスを介して評価・書き込みされます）。
  - stop_requested.flag（data/stop_requested.flag）などのファイルが存在すると run_monitoring/run_execution のループが終了または起動回避します。
- OpenAI（LLM）を利用する機能は OPENAI_API_KEY が必要です。API のエラーやレート制限は実装内でリトライやフォールバック処理を行いますが、API キーやコストに注意してください。
- ログ:
  - ログは stdout と logs/<app_name>.log（日時ローテーション）に出力されます。LOG_DIR 環境変数で出力先を変更可能です。

---

## 推奨環境変数（抜粋）

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV (development | paper_trading | live)
- OPENAI_API_KEY (LLM 機能を使う場合)
- DUCKDB_PATH (default: data/kabusys.duckdb)
- SQLITE_PATH (default: data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH (default: data/paper_trading.db)
- MONITOR_POLL_INTERVAL (監視の秒間隔)
- PAPER_FILL_MODE (instant | partial | never | reject)
- LOG_LEVEL, LOG_DIR

---

## ディレクトリ構成（主要ファイル）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / Settings 管理（自動 .env ロード機能含む）
  - config_setup.py          — 対話式 .env ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — Monitoring ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py
  - utils/
    - logging_setup.py       — 共通ログ設定
    - process_priority.py    — プロセス優先度 / CPU affinity ヘルパ
  - monitoring/
    - monitoring_db.py       — 監視用 SQLite スキーマ & 永続化層
    - system_monitor.py
    - trade_monitor.py       — （省略時）取引監視（コードベースに存在）
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py       — （アラート送信ロジック、実装に依存）
  - execution/
    - execution_engine.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - broker_factory.py
    - risk_manager.py
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
  - monitoring/               （上記）
  - tools/                    （上記）
- config/
  - *.yaml                   — system_config.yaml 等（テンプレートや生成スクリプトあり）
- data/
  - monitoring.db            — デフォルト監視 DB（SQLite）
  - paper_trading.db         — Paper Trading 用 DB（KABUSYS_ENV により使用）
  - execution.pid
  - stop_requested.flag
  - kill.flag
- logs/
  - execution.log
  - monitoring.log
  - ...                     — 日次ローテーションされます

（注: 実際のリポジトリによってファイルの有無が異なる場合があります。上はコードベースからの抜粋です。）

---

## 開発者向けメモ / 拡張ポイント

- DuckDB のスキーマやテーブル（prices_daily / raw_financials / raw_news / ai_scores 等）を整備することで研究・AI モジュールが動作します。
- AI モジュールは OpenAI SDK（v1）を想定した呼び出しを行っています。テスト時は API 呼び出し部分をモックする設計になっています（_call_openai_api の差し替え等）。
- position_sizing や risk_adjustment は将来的に銘柄ごとの lot_size やコストモデルを導入する余地を残す設計です。
- ログや DB のパス、閾値などは config/*.yaml または環境変数で柔軟に変更できます。validate_config.py を活用して起動前チェックを行ってください。

---

この README はコードベース内のドキュメント文字列やヘッダーコメントを基に作成しています。より詳細な運用手順やアーキテクチャ設計、API ドキュメントを整備する場合は追加でドキュメントを作成してください。必要であれば、各モジュールごとの使い方サンプルやコンフィグ YAML 例も作成します。