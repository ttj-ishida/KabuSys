README
======

概要
----
KabuSys は日本株向けの自動売買システム（プロトタイプ）です。本リポジトリはトレード実行エンジン、監視/アラート、ポートフォリオ構築、リサーチ（ファクター計算）、および AI ベースのニュースセンチメント／レジーム判定機能を含みます。設計方針としては「本番 DB とペーパートレードの分離」「ルックアヘッドバイアスの排除」「フェイルセーフ（API 失敗時は継続）」を重視しています。

主な特徴
--------
- ExecutionEngine：注文送信・注文管理・リスク管理の実行エンジン（KABU API または MockBroker を利用）
- Monitoring：システム稼働・データ鮮度・注文/リスクの常時監視、Kill Switch による停止信号発行
- Portfolio construction：候補選定、重み付け、株数決定（等金額・スコア重み・リスクベース）
- Research：DuckDB を用いたファクター計算（モメンタム、ボラティリティ、バリュー等）と特徴量解析
- AI モジュール：OpenAI（gpt-4o-mini 想定）を使ったニュースセンチメント（銘柄別）と市場レジーム判定
- ユーティリティ：ログ設定、プロセス優先度／CPU affinity、環境 (.env) ウィザード、設定検証、ペーパートレード検証レポート生成

必要な依存パッケージ（例）
-------------------------
主に以下が必要になります（バージョンは適宜調整してください）:
- Python 3.10+
- duckdb
- psutil
- openai
- PyYAML（config ファイルの検証で任意）
その他、標準ライブラリを使用します。

セットアップ手順
--------------
1. リポジトリをクローンして Python 仮想環境を作成
   - python -m venv .venv
   - source .venv/bin/activate (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   - pip install duckdb psutil openai PyYAML
   （プロジェクトで requirements.txt があれば pip install -r requirements.txt を使用）

3. 初期設定 (.env) の作成
   - 対話式ウィザード:
     - python -m kabusys.config_setup
     - ウィザードは .env を生成／更新します。J-Quants トークンや kabu API パスワードなど必須項目が含まれます。
   - 手動で .env を作る場合は .env.example を参考にしてください（リポジトリに例ファイルがない場合は config_setup の項目を参照）。

4. 設定の検証
   - python -m kabusys.validate_config
   - 警告も失敗扱いにする場合: python -m kabusys.validate_config --strict

環境変数の主な項目
------------------
- JQUANTS_REFRESH_TOKEN （必須）: J-Quants API 用トークン
- KABU_API_PASSWORD （必須）: kabuステーション API パスワード
- KABUSYS_ENV: 実行環境（development | paper_trading | live）。デフォルト: development
- OPENAI_API_KEY: OpenAI API キー（AI モジュールで使用）
- DUCKDB_PATH: DuckDB のファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（SQLite）パス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード時の SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: ペーパートレードの約定動作（instant | partial | never | reject）
- LOG_LEVEL / LOG_DIR: ログ出力設定
- MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、run_monitoring で有効）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（本番では 0 推奨）

デフォルトのデータ / ログパス
------------------------------
- SQLite（監視）: data/monitoring.db
- SQLite（ペーパートレード）: data/paper_trading.db
- DuckDB: data/kabusys.duckdb
- ログ: logs/<app_name>.log
- Kill / stop フラグ:
  - data/kill.flag (KillSwitch により ExecutionEngine 停止トリガー)
  - data/stop_requested.flag (run_execution / run_monitoring の終了トリガー)
- pid ファイル: data/execution.pid

使い方（主要コマンド）
--------------------

- 環境設定ウィザード
  - python -m kabusys.config_setup
    - .env を対話的に作成・更新します。

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- 実行エンジン（ExecutionEngine）の起動
  - python -m kabusys.run_execution
  - 補足:
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、ペーパートレード用 DB（data/paper_trading.db）へ記録します（本番 DB と完全分離）。
    - 起動前に data/stop_requested.flag が存在すると起動しません。
    - 停止は data/stop_requested.flag を作成するか、KillSwitch が data/kill.flag を作成するとエンジンを停止します。

- 監視プロセスの起動
  - python -m kabusys.run_monitoring
  - 補足:
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可能。デフォルト 60 秒。
    - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用して監視ログを残します。
    - run_monitoring は data/stop_requested.flag を検知するとループを終了します。

- ペーパートレード検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db PATH （環境変数 PAPER_TRADING_SQLITE_PATH の代替）

- AI スコアリング / レジーム判定（ライブラリ関数）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - OpenAI API キーは引数または環境変数 OPENAI_API_KEY で指定

停止方法 / Kill Switch
---------------------
- 実行エンジンの強制停止シグナル:
  - KillSwitch は条件（ドローダウン超過やポジション上限超過など）により data/kill.flag に理由を記載して停止を要求します。
  - 監視スクリプト（MonitoringEngine）は Kill Switch 発動時に必要に応じてアラートを送信します。
- 手動停止:
  - data/stop_requested.flag を作成すると run_execution/run_monitoring のメインループは検知して安全に終了します。
  - run_execution は実行中に stop_requested.flag を検知すると engine.stop() を呼んで終了処理します。

ディレクトリ構成（主要ファイル）
-------------------------------
概略:
- src/kabusys/
  - __init__.py
  - config.py                       — 環境変数 / 設定読み込みロジック
  - config_setup.py                 — .env 対話式ウィザード
  - validate_config.py              — 設定検証 CLI
  - run_execution.py                — ExecutionEngine 起動スクリプト
  - run_monitoring.py               — SystemMonitor 起動スクリプト
  - tools/
    - paper_verification_report.py   — ペーパートレード検証レポート生成
  - ai/
    - news_nlp.py                    — ニュース NLP（銘柄別センチメント）
    - regime_detector.py             — 市場レジーム判定
  - portfolio/
    - portfolio_builder.py           — 候補選定・重み計算
    - position_sizing.py             — 株数計算・資金配分
    - risk_adjustment.py             — セクター制限・レジーム乗数
  - research/
    - factor_research.py             — ファクター計算（momentum/vol/val）
    - feature_exploration.py         — IC/将来リターン計算・統計
  - monitoring/
    - monitoring_db.py               — SQLite 監視 DB 層
    - system_monitor.py              — システム状態・データ鮮度チェック
    - trade_monitor.py               — 注文関連監視（ログ参照）
    - risk_monitor.py                — ドローダウン・ポジション上限監視
    - kill_switch.py                 — kill.flag 書き込みロジック
    - alert_manager.py               — （アラート送信のラッパー）※実装参照
    - monitoring_engine.py           — 各 Monitor の統合ポーリング
  - execution/
    - execution_engine.py            — 実行エンジンのコア（run_session など）
    - broker_factory.py              — ブローカークライアント作成
    - order_manager.py / order_repository.py / reconciler.py / risk_manager.py
  - monitoring/monitoring_db.py      — 監視ログ DB の初期化・操作
  - utils/
    - logging_setup.py               — ログ設定ユーティリティ
    - process_priority.py            — プロセス優先度 / CPU affinity 設定

開発メモ / テスト向け情報
-----------------------
- OpenAI 呼び出しは各モジュールでラップしているため、ユニットテストでは該当関数を mock.patch して API 呼び出しを差し替えられます（例: kabusys.ai.news_nlp._call_openai_api）。
- DuckDB / SQLite を使ったロジックは DB 接続を引数で受けるため、テスト用に一時 DB ファイルや in-memory 接続を与えて検証可能です。
- Settings は .env 自動ロードを行いますが、テスト時に自動ロードを無効化する環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を使えます。

補足
----
- 本リポジトリはミニマムな設計ドキュメントと合わせて、実運用を意識した堅牢性（ログ・マイグレーション・フェイルセーフ）を取り入れた構成になっています。
- 本番運用前には KABUSYS_ENV=live の設定・LINE 通知等の確認、kill_flag の扱い（KILL_FLAG_CLEAR_ON_START）を必ず確認してください。

問題／問い合わせ
----------------
不具合や質問がある場合は、実行ログ（logs/<app_name>.log）と .env の（秘密情報をマスクした）設定内容を添えて報告してください。