KabuSys — 日本株自動売買システム
=================================

概要
----
KabuSys は日本株向けの自動売買システムのコードベースです。本リポジトリには以下の主要機能が含まれます。

- 実行エンジン（ExecutionEngine）による発注／注文管理（paper_trading モードでの分離された DB をサポート）
- 監視（Monitoring）：システム稼働状況、注文ログ、リスク監視、Kill Switch（フラグファイル）など
- ポートフォリオ構築ユーティリティ（候補選定、重み計算、数量算出、セクター制限など）
- リサーチ/ファクター計算（DuckDB を用いたファクター計算・特徴量解析）
- AI 関連モジュール（ニュース NLP によるセンチメント評価、レジーム判定）
- 各種 CLI ツール（環境設定ウィザード、設定検証、ペーパートレード検証レポート等）

主要な思想
- 本番/ペーパーの DB 分離（paper_trading 時は data/paper_trading.db を使用）
- .env による設定管理（config_setup による対話生成 / validate_config による検証）
- DuckDB を解析用 DB として利用、SQLite を監視／注文履歴用に利用
- OpenAI を使った NLP 機能はキーが必要。API エラー時はフォールバックする安全設計

機能一覧
--------
- 環境設定ウィザード: python -m kabusys.config_setup
- 設定検証 CLI: python -m kabusys.validate_config
- 実行エンジン起動: python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は MockBroker を利用し、paper_trading DB に記録
- 監視プロセス起動: python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を調整可能（デフォルト 60 秒）
- Paper Trading 検証レポート: python -m kabusys.tools.paper_verification_report
- AI モジュール:
  - kabusys.ai.news_nlp.score_news — ニュース記事を OpenAI でスコアリングし ai_scores に保存
  - kabusys.ai.regime_detector.score_regime — ETF とマクロニュースからレジーム判定
- ポートフォリオ構築関数（純粋関数群）
  - select_candidates, calc_equal_weights, calc_score_weights
  - calc_position_sizes（リスクベース／等分配等）
  - apply_sector_cap, calc_regime_multiplier

セットアップ手順
----------------
1. Python 環境を用意
   - Python 3.8+ 推奨
   - 仮想環境作成（例）
     - python -m venv .venv
     - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   - 最低限の依存:
     - duckdb
     - psutil
     - openai (AI 機能を使う場合)
     - PyYAML（validate_config で YAML の内容検証を行いたい場合）
   - 例:
     - pip install duckdb psutil openai PyYAML

   （requirements.txt がある場合は pip install -r requirements.txt を使用）

3. .env を作成
   - 対話式ウィザードを使う（推奨）:
     - python -m kabusys.config_setup
   - ウィザードで生成される .env はプロジェクトルートに保存される（.env を絶対に Git にコミットしないこと）

4. 設定検証
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱い（exit code 1）になる

5. ディレクトリ / DB 初期化
   - ログディレクトリ（デフォルト logs/）や data/ ディレクトリは自動作成されることが多いですが、権限を確認してください。

使い方（実行例）
----------------

- 環境設定ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 厳格モード: python -m kabusys.validate_config --strict

- 実行エンジン（Execution Engine）起動
  - python -m kabusys.run_execution
  - paper_trading モード（.env で KABUSYS_ENV=paper_trading）にすると data/paper_trading.db を使い、外部ブローカー呼び出しはモック化される
  - 実行中に停止させるには data/stop_requested.flag を作成する（run_execution はこのフラグを監視して停止）
  - または監視側から KillSwitch により data/kill.flag を書き込むと ExecutionEngine に停止シグナルが送られる

- 監視プロセス起動
  - python -m kabusys.run_monitoring
  - ポーリング間隔を変更するには環境変数 MONITOR_POLL_INTERVAL を秒数で設定（例: export MONITOR_POLL_INTERVAL=30）
  - 監視は常に本番 sqlite_path（Settings.sqlite_path）を使用するので、監視 DB の指定は .env で SQLTIE_PATH を設定
  - 監視プロセスも data/stop_requested.flag を検知してループを終了する

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db PATH を指定するか環境変数 PAPER_TRADING_SQLITE_PATH を設定

設定（主要環境変数）
-------------------
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- DUCKDB_PATH: 分析用 DB（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL
- LOG_DIR: ログ出力先ディレクトリ（デフォルト logs/）
- OPENAI_API_KEY: OpenAI API を使う機能で利用
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒）
- PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START: 監視・停止フラグ制御関連

重要なファイル／フラグ
--------------------
- data/stop_requested.flag: run_execution / run_monitoring が監視している停止フラグ（存在すると起動済プロセスを安全に停止）
- data/kill.flag: KillSwitch が書き込むファイル。ExecutionEngine に対する強制停止トリガ（本番では注意して使用）
- data/execution.pid: 実行エンジンの PID ファイル（run_execution が使用）
- logs/: 各アプリケーション（execution, monitoring など）のログファイル

ディレクトリ構成（抜粋）
----------------------
（src/kabusys 以下を示します）

- kabusys/
  - __init__.py
  - config.py                — 環境変数 / 設定読み込みユーティリティ
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリング起動スクリプト
  - ai/
    - __init__.py
    - news_nlp.py            — ニュース NLP（OpenAI 呼び出し）
    - regime_detector.py     — 市場レジーム判定
  - monitoring/
    - __init__.py
    - monitoring_db.py       — SQLite スキーマ定義 / 永続層
    - system_monitor.py      — システム監視（CPU/MEM/DISK/データ鮮度）
    - trade_monitor.py       — 注文ログ監視（存在ファイル参照）
    - risk_monitor.py        — ドローダウン / ポジション上限監視
    - kill_switch.py         — Kill Switch（フラグファイル書込）
    - monitoring_engine.py   — 各モニタをまとめるエンジン
    - alert_manager.py       — （アラート送信ロジック、別ファイル）
  - execution/
    - (ExecutionEngine 関連モジュール群: broker_factory, execution_engine, order_manager, order_repository, reconciler, risk_manager, ...)
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py
  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py
  - utils/
    - logging_setup.py       — ロギング設定（Stream + TimedRotatingFileHandler）
    - process_priority.py    — プロセス優先度 / CPU affinity 設定
    - __init__.py
  - tools/
    - paper_verification_report.py — Paper Trading の検証レポート生成
    - __init__.py

運用上の注意
-----------
- 本番環境（KABUSYS_ENV=live）では .env の設定を慎重に管理してください。validate_config は live の時に追加警告を出します。
- .env は絶対に Git にコミットしないでください。
- OpenAI キーを設定している場合、API 使用量に注意してください（コスト発生）。
- run_monitoring は常に monitoring の sqlite_path（Settings.sqlite_path）を使用します。監視用 DB の分離が必要なら .env で SQLITE_PATH を調整してください。
- paper_trading は実際のブローカーに発注しませんが、動作確認用のログや DB を生成します（data/paper_trading.db）。

開発者向けヒント
-----------------
- ロギングの初期化は各スクリプトで setup_logging(app_name=...) を呼んで行います。ログファイルは logs/<app_name>.log に日次ローテーションで保存されます。
- プロセス優先度は utils.process_priority.set_process_priority("high") を用いて起動時に上げる設計です（psutil の権限に依存）。
- DuckDB 接続は分析処理（research, ai）で再利用できます。テーブル名（prices_daily, raw_financials, raw_news, ai_scores 等）を参照してください。
- エラーや例外は各モジュールで捕捉してロギングするようになっており、監視ループは例外から回復する設計です。

FAQ（よくある質問）
------------------
Q: run_monitoring のポーリング間隔はどう変えますか？
A: 環境変数 MONITOR_POLL_INTERVAL に秒数を設定してください（例: export MONITOR_POLL_INTERVAL=30）。不正値や 0 以下はデフォルト 60 秒にフォールバックします。

Q: ペーパートレード用 DB の場所を変えたい
A: .env の PAPER_TRADING_SQLITE_PATH を設定するか、コマンドラインでツールに --db オプションを指定します（paper_verification_report 等）。

Q: Kill Switch はどのように動くの？
A: RiskMonitor の判定で DRAWDOWN_ALERT や POSITION_LIMIT_ALERT がトリガーとなると KillSwitch が data/kill.flag に理由を書き込みます。ExecutionEngine はこのフラグを検知して停止します（冪等で再書き込みしません）。

さらに知りたいこと・貢献
-----------------------
- 各モジュールの内部実装（ExecutionEngine、OrderManager、BrokerClient 等）はそれぞれのファイルを参照してください。
- 機能追加やバグ修正のプルリクエストは歓迎します。テストの追加、requirements.txt の整備、CI の導入などがあると助かります。

以上で README の概要です。必要であれば、実行例スニペットや .env のサンプル、よくあるエラー対処法（DB 権限、OpenAI 接続エラー等）を追加で作成します。どの情報を補足しますか？