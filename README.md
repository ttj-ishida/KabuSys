# KabuSys

日本株向け自動売買システムのリポジトリ（ライブラリ + 起動スクリプト群）。

この README はソースコード（src/kabusys 以下）をもとに、プロジェクト概要・機能・セットアップ・使い方・ディレクトリ構成を説明します。

---

## プロジェクト概要

KabuSys は日本株の自動売買・研究・監視機能を備えたシステムです。主な設計方針は次の通りです。

- 実行ロジック（ExecutionEngine）と監視（Monitoring）を分離し、kill/stop フラグによる安全停止をサポート
- DuckDB を分析・研究用データベースとして利用、SQLite を監視・取引ログ保存用に利用
- Paper Trading（ペーパートレード）モードを用意し、本番 DB と完全分離
- ニュースの NLP 評価やレジーム判定に OpenAI（gpt-4o-mini 等）を利用するモジュールを組込
- 設定は .env ファイル／環境変数で管理。対話式ウィザードと検証 CLI を提供

バージョン: 0.1.0（src/kabusys/__init__.py）

---

## 主な機能一覧

- 実行エンジン（Execution）
  - 実際の注文送信ロジック（ブローカークライアントを注入）
  - Paper Trading モードをサポート（モックブローカー、専用 SQLite）
  - リスク管理、注文管理、リコンサイル機能（Engine 側の構成）
- 監視（Monitoring）
  - SystemMonitor：CPU/メモリ/ディスク/プロセスの監視、データ鮮度チェック
  - TradeMonitor：注文滞留や約定異常の検知（該当箇所はモジュール内）
  - RiskMonitor：ドローダウン・ポジション数上限の監視
  - KillSwitch：監視結果に応じて kill.flag を書き込み停止シグナルを送出
  - MonitoringEngine：各 Monitor を束ねるポーリングループ
- 永続化
  - monitoring_db：system_status / trade_logs / positions / risk_logs / dashboard テーブルとマイグレーション
- ポートフォリオ構築（純粋関数群）
  - 候補選定、等金額/スコア加重、ポジションサイズ決定、セクターキャップ、レジーム乗数
- 研究（Research）
  - ファクター計算（モメンタム/バリュー/ボラティリティ）
  - 将来リターン・IC 計算・統計サマリー
- AI
  - news_nlp: raw_news を集約して OpenAI でセンチメント評価 → ai_scores に書き込み
  - regime_detector: ma200 とマクロニュースセンチメントを合成して市場レジームを判定
- ユーティリティ
  - .env 対話式ウィザード（config_setup）
  - 設定検証 CLI（validate_config）
  - Paper Trading 検証レポート生成スクリプト（tools/paper_verification_report）
  - ログ設定ユーティリティ、プロセス優先度設定など

---

## 前提 / 必要ライブラリ (例)

以下はソースで参照される外部ライブラリの例です。実際の requirements はプロジェクト側で用意してください。

- Python 3.9+（typing の list[str] 等を使用）
- duckdb
- psutil
- openai
- PyYAML（config 検証時に YAML 構成ファイル検証を行う場合に必要）
- （sqlite3 は標準ライブラリ）

---

## セットアップ手順（ローカル開発向け）

1. リポジトリをクローン
   - git clone ...; cd <repo>

2. 仮想環境を作成・有効化（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   - pip install duckdb psutil openai PyYAML
   - （プロジェクトに requirements.txt がある場合は pip install -r requirements.txt）

4. .env の作成（対話式ウィザード）
   - python -m kabusys.config_setup
   - ウィザードは J-Quants トークンや kabu API パスワード等の必須項目を案内します

   自動読み込みについて:
   - デフォルトでプロジェクトルートの .env と .env.local を自動読み込みします
   - 自動読み込みを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定

5. 設定検証
   - python -m kabusys.validate_config
   - 警告もエラー扱いにしたい場合は --strict を付与

6. ディレクトリ（data / logs 等）が必要なら作成
   - data ディレクトリは PID / flag / SQLite の配置に使用
   - logs ディレクトリはログ出力に使用（setup_logging が自動作成を試みます）

---

## 主要な環境変数（重要なもの）

- JQUANTS_REFRESH_TOKEN — J-Quants API 用（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）
- KABUSYS_ENV — 実行環境: development | paper_trading | live（デフォルト: development）
  - paper_trading 時は Execution は MockBroker を使用し、専用 paper_trading DB を使う
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード専用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE — paper_trading 時の約定挙動（instant/partial/never/reject）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...）
- OPENAI_API_KEY — OpenAI API キー（news_nlp / regime_detector 用）
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、デフォルト 60）
- KILL_FLAG_CLEAR_ON_START — Execution 起動時に kill.flag を自動クリアするか（0/1）

---

## 使い方（起動と主要コマンド）

CLI はパッケージモジュールとして起動します。プロジェクトルートで以下を実行します。

- 環境設定ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 厳密モード（警告を FAIL とする）: python -m kabusys.validate_config --strict

- 監視ループを起動（監視プロセス）
  - python -m kabusys.run_monitoring
  - 説明:
    - デフォルトで MONITOR_POLL_INTERVAL=60 秒
    - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で上書き可能
    - 監視は Settings.sqlite_path を使用（KABUSYS_ENV に依らず本番 sqlite_path を参照）
    - 停止: プロジェクト root/data/stop_requested.flag を作成するとループが終了します

- 実行エンジンを起動（ExecutionEngine）
  - python -m kabusys.run_execution
  - 説明:
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使い、data/paper_trading.db（または PAPER_TRADING_SQLITE_PATH）へ記録
    - KABUSYS_ENV により本番／ペーパートレードが切り替わる
    - 起動時に data/stop_requested.flag が存在する場合は起動せず終了
    - 停止は同じく data/stop_requested.flag を作成することで通知されます
    - 実行中は pid ファイル（data/execution.pid 等）を書きます

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定: --from YYYY-MM-DD --to YYYY-MM-DD
  - DB 指定: --db PATH（PAPER_TRADING_SQLITE_PATH 環境変数でも指定可）

- プログラム API（研究・AI 等をスクリプトから利用）
  - 例: ニューススコアリング（プログラム的呼び出し）
    - from kabusys.ai.news_nlp import score_news
    - score_news(duckdb_conn, target_date, api_key="...")

  - 例: レジーム判定
    - from kabusys.ai.regime_detector import score_regime
    - score_regime(duckdb_conn, target_date, api_key="...")

---

## 停止 / Kill Switch の運用

- 停止フラグ（監視ループ / 実行エンジンの外部停止）
  - data/stop_requested.flag を配置すると run_monitoring/run_execution のループが終了します（監視スクリプトはこのフラグを監視）。
- Kill Switch（自動停止判断）
  - KillSwitch は監視結果（ドローダウンやポジション上限等）に基づき data/kill.flag を書き込みます
  - Execution 起動時に KILL_FLAG_CLEAR_ON_START=1 を設定すると自動クリアする挙動があり危険です（本番では 0 推奨）
  - KillSwitch が書いた理由は kill.flag の内容に保存されます

---

## ロギング

- 共通のログセットアップ関数: kabusys.utils.logging_setup.setup_logging(app_name="...") を各起動スクリプトが使用
- 出力:
  - コンソール（stdout）
  - 日次ローテートファイル logs/<app_name>.log（デフォルト logs ディレクトリに 30 日分保持）
- ログ出力先は環境変数 LOG_DIR または引数で上書き可能

---

## ディレクトリ構成（抜粋）

以下は src/kabusys 以下の主なファイル・モジュール構成（主要ファイルのみ抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                    — 環境変数 / Settings
  - config_setup.py              — .env 対話式ウィザード
  - validate_config.py           — 設定検証 CLI
  - run_monitoring.py            — Monitoring ポーリング起動スクリプト
  - run_execution.py             — ExecutionEngine 起動スクリプト
  - utils/
    - logging_setup.py
    - process_priority.py
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py
  - execution/                    — Execution 系（Engine, OrderManager, BrokerFactory 等）
    - execution_engine.py
    - order_manager.py
    - order_repository.py
    - broker_factory.py
    - risk_manager.py
    - reconciler.py
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
  - tools/
    - paper_verification_report.py
  - data/                         — 実行時に使用するファイル群（例: monitoring.db, paper_trading.db, kill.flag, stop_requested.flag, execution.pid）
  - logs/                         — ログファイル（デフォルト）

---

## 開発上の注意点・設計メモ

- SQLite の monitoring DB と Paper Trading DB は分離されています（paper_trading は settings.is_paper を参照）。
- DuckDB は分析・研究用に想定。AI モジュールや research モジュールは DuckDB 接続を受け取って SQL を実行します。
- OpenAI 連携:
  - API キーは OPENAI_API_KEY または関数引数で渡す必要があります。
  - ニューススコアリング / レジーム判定はネットワークエラーを考慮したリトライロジックを内包していますが、API 呼び出し失敗時はフェイルセーフで続行します。
- 自動的に .env を読み込む機能があり、テスト時には KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化できます。
- ログディレクトリ作成やプロセス優先度設定は権限不足で失敗することがありますが、フェイルオープンで処理は継続します（警告ログが出ます）。

---

## よく使うコマンドまとめ

- .env 作成ウィザード
  - python -m kabusys.config_setup
- 設定検証
  - python -m kabusys.validate_config
- 監視ループ起動
  - python -m kabusys.run_monitoring
- 実行エンジン起動
  - python -m kabusys.run_execution
- Paper Trading レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

---

必要であれば、この README にサンプル .env（テンプレート）、より詳細な起動例（systemd / supervisor 用 Unit ファイル例）、および各モジュールの詳細 API ドキュメントを追加できます。どの情報を追加したいか教えてください。