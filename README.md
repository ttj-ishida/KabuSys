KabuSys — 日本株自動売買システム
================================

このリポジトリは日本株向けの自動売買・研究・監視ユーティリティ群をまとめた軽量フレームワークです。  
主要機能は取引エンジン（ExecutionEngine）、監視（Monitoring）、ポートフォリオ構築、ファクター計算、LLM を用いたニュース NLP / レジーム判定、ペーパートレード検証レポート生成などです。

目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 使い方
- 環境変数（主要）
- 停止 / Kill Switch
- ディレクトリ構成

プロジェクト概要
----------------
KabuSys は次のようなコンポーネントを含む自動売買プラットフォームのコアライブラリです。

- ExecutionEngine（発注ロジック、リスク管理、OrderManager 等）
- Monitoring（システム状態・注文状況・リスク監視、Kill Switch）
- Portfolio（候補選定・重み付け・ポジションサイズ算出・セクター調整）
- Research（ファクター計算、将来リターン・IC 計算、統計サマリ）
- AI（ニュースのセンチメント評価、マクロレジーム判定。OpenAI を利用）
- Tools（ペーパートレード検証レポート等）
- ユーティリティ（ログ設定、プロセス優先度設定、設定ロード）

設計上の注意点
- .env（環境変数）を使って設定を行います。config_setup.py による対話型ウィザードと validate_config による起動前検証を備えています。
- Monitoring の監視ログは SQLite（Settings.sqlite_path）へ永続化されます。Monitoring は環境設定（KABUSYS_ENV）に関わらず production 用 sqlite_path を参照します。
- KABUSYS_ENV=paper_trading の場合は MockBrokerClient を用い、paper_tradingDB（data/paper_trading.db）に記録して本番 DB と分離します。

機能一覧
--------
- 環境設定ウィザード: python -m kabusys.config_setup
- 設定検証: python -m kabusys.validate_config
- ExecutionEngine 起動: python -m kabusys.run_execution
  - paper_trading モードで MockBroker を使用
  - 停止フラグ（data/stop_requested.flag）を検知して停止
  - PID ファイル: data/execution.pid（Settings.pid_file_path）
- Monitoring 起動: python -m kabusys.run_monitoring
  - 定期ポーリングで System/Trade/Risk をチェック、監視ログを書き込み
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔変更（秒、デフォルト 60）
  - 停止フラグ（data/stop_requested.flag）でループ終了
  - Kill Switch（リスク閾値超時に data/kill.flag を書き込み、Execution を停止）
- Portfolio 機能
  - 候補選定、等金額／スコア加重、リスクベース配分、単元株丸め、セクターキャップ、レジーム乗数
- Research（DuckDB を用いたファクター計算）
  - momentum / volatility / value 等のファクター
  - forward returns、IC（Spearman）計算、ファクター統計
- AI（OpenAI 使用）
  - news_nlp: ニュースを集約して LLM で銘柄ごとのセンチメントスコアを ai_scores に保存
  - regime_detector: ETF 1321 の MA200 とマクロニュースの LLM センチメントを組み合わせ市場レジーム判定
- Tools
  - Paper Trading 検証レポート生成（python -m kabusys.tools.paper_verification_report）

セットアップ手順
----------------
1. リポジトリをクローンし、Python 仮想環境を作る
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. 必要パッケージをインストール
   - 最小（必須）:
     pip install duckdb psutil openai
   - 設定検証で YAML を検証したい場合:
     pip install pyyaml
   - （開発用）テスト等:
     pip install pytest

   実運用では requirements.txt を用意している場合はそれを使ってください（本リポジトリには明示的な requirements.txt がないため上記を参考にしてください）。

3. .env を作成
   - 対話的に作成する: python -m kabusys.config_setup
   - もしくは .env.template/.env.example を参考に手動作成

4. データディレクトリ
   - デフォルトの SQLite / DuckDB / PID / フラグファイルは data/ と logs/ に書き込まれます。必要に応じてディレクトリを作成してください（setup_logging が自動で作成することもあります）。

使い方
------
基本的なコマンド（モジュールとして実行）:

- 環境設定ウィザード
  - python -m kabusys.config_setup

- 設定検証（起動前チェック）
  - python -m kabusys.validate_config
  - --strict を付けると警告も失敗扱い（exit code 1）

- ExecutionEngine の起動
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading を指定すると paper_trading 用の MockBroker と paper DB（PAPER_TRADING_SQLITE_PATH）を使用
  - 起動時、data/stop_requested.flag が存在すると起動しません
  - 実行中は data/stop_requested.flag を作成すると安全に停止を試みます
  - PID ファイルは Settings.pid_file_path（デフォルト data/execution.pid）へ出力

- Monitoring の起動
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を調整。デフォルト 60 秒
  - 監視スクリプトは MonitoringDB を初期化（init_monitoring_db）し、system_status/trade_logs/risk_logs 等を作成します
  - data/stop_requested.flag が存在するとループを終了します

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db で SQLite ファイルを指定可能（PAPER_TRADING_SQLITE_PATH 環境変数でも可）

主要な環境変数（概要とデフォルト）
--------------------------------
主な設定は .env または環境変数で行います。Settings クラス（kabusys.config）内で取得・検証されています。主要項目:

- JQUANTS_REFRESH_TOKEN （必須）
- KABU_API_PASSWORD （必須）
- KABU_API_BASE_URL （デフォルト: http://localhost:18080/kabusapi）
- OPENAI_API_KEY （AI 機能を使う場合は必須）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID （アラート通知）
- DUCKDB_PATH （デフォルト: data/kabusys.duckdb）
- SQLITE_PATH （デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH （デフォルト: data/paper_trading.db）
- KABUSYS_ENV （development / paper_trading / live、デフォルト: development）
- LOG_LEVEL （DEBUG/INFO/...、デフォルト INFO）
- MONITOR_POLL_INTERVAL （run_monitoring 用、秒、デフォルト 60）
- PAPER_FILL_MODE （paper_trading 時のモック約定モード: instant/partial/never/reject）

停止 / Kill / フラグファイル
----------------------------
- 起動・停止の制御はファイルフラグで行われる設計です。
  - data/stop_requested.flag : run_execution / run_monitoring がこのファイル存在を検出すると安全シャットダウンします。
  - data/kill.flag : Monitoring の KillSwitch が書き込むと ExecutionEngine 側で外部制御により停止を促します（本番用の強力な停止トリガー）。
- KillSwitch の評価条件はリスク（ドローダウンやポジション上限）に基づきます。KillSwitch は冪等に flag ファイルを書きます（既に存在する場合は書き換えません）。
- ExecutionEngine 起動時に KILL_FLAG_CLEAR_ON_START=1 が設定されていると kill.flag を自動でクリアします（本番では 0 を推奨）。

ロギング
-------
- 共通のログ設定ユーティリティ: kabusys.utils.logging_setup.setup_logging(app_name="...")  
  - stdout に StreamHandler、ファイルに日次ローテーション（logs/<app_name>.log）を設定します。
  - デフォルトで logs/ ディレクトリにファイル保存（LOG_DIR で上書き可）。

DB 初期化
--------
- monitoring 用 SQLite スキーマは kabusys.monitoring.monitoring_db.init_monitoring_db() にて作成・マイグレーションされます。起動スクリプトは自動的にこれを呼びます。

安全上の注意
------------
- KABUSYS_ENV=live（本番）では十分に設定を確認してください。validate_config は live の場合に追加の警告を出します。
- .env は絶対に Git へコミットしないでください（config_setup が注意書きを出します）。
- OpenAI API キーや証券 API の認証情報は安全に保管してください。
- 実際の発注ロジックはブローカークライアント実装に依存します。実運用ではリスク管理設定（RiskConfig 等）を慎重に設定してください。

ディレクトリ構成（主要ファイル）
-----------------------------
以下は src/kabusys 以下の代表的なファイル・モジュール構成です（抜粋）。

- kabusys/
  - __init__.py
  - config.py                  — 環境変数/設定読み込み
  - config_setup.py            — .env 対話ウィザード
  - validate_config.py         — 起動前チェック CLI
  - run_execution.py           — ExecutionEngine 起動スクリプト
  - run_monitoring.py          — Monitoring ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py
  - ai/
    - news_nlp.py              — ニュース NLP（OpenAI）
    - regime_detector.py       — レジーム判定（MA200 + LLM）
  - monitoring/
    - monitoring_db.py         — monitoring 用 SQLite 抽象
    - monitoring_engine.py
    - system_monitor.py
    - trade_monitor.py         (存在：監視ロジック群)
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py         (存在: アラート送信ラッパ)
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

（上記はリファレンス的な抜粋です。詳細は各モジュールの docstring を参照してください。）

追加情報 / 開発
----------------
- テストや CI を追加する場合、DuckDB のテスト用 DB やモッククライアントを使って外部 API 呼び出しを切り離してください（AI モジュールは API 呼び出しラッパーをモックしやすく設計されています）。
- 依存ライブラリのバージョン管理（requirements.txt / pyproject.toml）を別途用意すると再現性が向上します。

問い合わせ
----------
不明点やバグ報告はリポジトリの issue へお願いします。README にない操作や設定項目を使う場合は各モジュールの docstring を参照してください（各ファイルの先頭に使い方・設計方針が記載されています）。

以上。安全に運用してください。