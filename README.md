README
=====

概要
----
KabuSys は日本株の自動売買・リサーチ・監視を想定した小規模なフレームワークです。本コードベースは以下の主要機能を含みます。

- 注文実行エンジン（ExecutionEngine）の起動 / ペーパートレード切替
- 監視プロセス（System / Trade / Risk のポーリング）と Kill Switch
- ポートフォリオ構築（銘柄選定・配分・ポジション算出）
- リサーチ（ファクター計算・特徴量探索）
- ニュース NLP（OpenAI を用いたニュースセンチメント評価）
- Paper Trading 検証レポート生成ツール
- 環境設定ウィザード / 設定検証 CLI
- ログ設定・プロセス優先度ユーティリティ

特徴
----
主な機能一覧（抜粋）：

- Execution
  - KABUSYS_ENV に応じて本番 / paper_trading を切り替え
  - paper_trading は専用 SQLite（data/paper_trading.db など）に記録し本番 DB と分離
  - プロセス優先度を高く設定（psutil 利用）。PID / stop フラグ管理あり
- Monitoring
  - System / Trade / Risk 各モニタを統合して定期ポーリング
  - system_status / trade_logs / risk_logs / positions / dashboard の永続化（SQLite）
  - Kill Switch（drawdown やポジション上限で data/kill.flag を書込）
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）
- Portfolio
  - 候補選定、等重・スコア重み、リスクベース位置サイズ計算、セクター制限、レジーム乗数
- Research
  - DuckDB を使ったファクター計算（momentum/value/volatility 等）
  - 将来リターン・IC・統計サマリー等
- AI
  - OpenAI を利用したニュースセンチメント（gpt-4o-mini 想定）
  - 市場レジーム判定（ETF MA + マクロセンチメントの合成）
- ツール
  - paper_verification_report: ペーパートレード DB を解析して PASS/FAIL レポートを出力
- 開発支援
  - .env を対話式に作成するウィザード（kabusys.config_setup）
  - 起動前に設定を検証する CLI（kabusys.validate_config）

セットアップ手順
----------------
1. リポジトリをクローン
   - git clone <repo-url>
   - cd <repo>

2. Python 仮想環境（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   - 最低限の依存（例）:
     - pip install duckdb psutil openai
   - 追加（設定検証で YAML をパースする場合など）:
     - pip install PyYAML
   - （プロジェクトに requirements.txt があればそれを使用してください）
     - pip install -r requirements.txt

4. ディレクトリ準備（任意）
   - data/ と logs/ は自動作成されることが多いですが、手動で準備しても良いです。
     - mkdir -p data logs

5. 環境変数の設定（.env）
   - 対話式ウィザードで作成するのが簡単です:
     - python -m kabusys.config_setup
   - もしくは .env に直接以下の主要項目を設定してください（例・必須 / デフォルト）:
     - JQUANTS_REFRESH_TOKEN (必須)
     - KABU_API_PASSWORD (必須)
     - KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
     - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
     - SQLITE_PATH (デフォルト: data/monitoring.db)
     - PAPER_TRADING_SQLITE_PATH (デフォルト: data/paper_trading.db)
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
     - LOG_LEVEL (DEBUG|INFO|WARNING|ERROR) — デフォルト: INFO
     - OPENAI_API_KEY（news_nlp / regime_detector を使う場合に必要）
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（本番通知用、任意）

6. 設定検証（推奨）
   - python -m kabusys.validate_config
   - --strict をつけると警告も失敗扱いになります:
     - python -m kabusys.validate_config --strict

使い方
------
主要な実行スクリプトはモジュールとして Python -m で呼び出します。

- ExecutionEngine 起動
  - python -m kabusys.run_execution
  - 動作:
    - Settings に基づき DB を接続（paper_trading の場合は paper_sqlite_path を使用）
    - BrokerClientFactory 経由でブローカークライアントを取得（KABUSYS_ENV による差し替え）
    - ExecutionEngine をスレッドで起動。data/stop_requested.flag を監視してシャットダウン
  - 注意:
    - 実行前に data/kill.flag のクリア設定 (KILL_FLAG_CLEAR_ON_START) を確認してください（本番では 0 推奨）
    - 実行中は data/execution.pid に PID を出す（設定により）

- Monitoring 起動
  - python -m kabusys.run_monitoring
  - 動作:
    - process priority を high に設定
    - monitoring 用の SQLite（Settings.sqlite_path）と DuckDB を接続
    - SystemMonitor.check_once をポーリング（MONITOR_POLL_INTERVAL 秒、デフォルト 60）
    - data/stop_requested.flag を検知するとループを終了
  - 環境変数:
    - MONITOR_POLL_INTERVAL=30 などで間隔を上書き可能

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - 例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
    - 指定がない場合は PAPER_TRADING_SQLITE_PATH 環境変数 または data/paper_trading.db を参照

- 環境設定ウィザード
  - python -m kabusys.config_setup
  - 対話式で .env を作成 / 更新します。完了後に validate_config を実行することを推奨。

- 設定検証
  - python -m kabusys.validate_config
  - 設定漏れやファイルパスの問題、YAML の解析エラーなどを事前検出します。

- AI 関連（プログラム API）
  - OpenAI API キーが必要（環境変数 OPENAI_API_KEY または関数引数で指定）
  - 主要 API:
    - kabusys.ai.score_news(conn, target_date, api_key=None) — news_nlp のバッチスコアリング
    - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - 注意:
    - OpenAI 呼び出しはリトライ / フォールバック実装あり（429/タイムアウト等）
    - API 使用時は利用料金に注意してください

運用上のポイント・挙動
--------------------
- プロセス優先度:
  - run_execution / run_monitoring は開始時に set_process_priority("high") を呼び出します（psutil 必須）。失敗した場合は警告ログを出します。
- DB:
  - monitoring 用 SQLite は Settings.sqlite_path（デフォルト data/monitoring.db）
  - paper_trading の場合は paper_sqlite_path（デフォルト data/paper_trading.db）を使用して本番 DB と分離します
  - DuckDB は分析用に使用（Settings.duckdb_path）
- Kill / Stop:
  - data/kill.flag: Kill Switch による停止シグナル。KillSwitch が書き込む
  - data/stop_requested.flag: run_execution / run_monitoring が優雅に停止するためのローカル制御フラグ（本リポジトリ内スクリプトで参照）
  - data/execution.pid: ExecutionEngine の PID（起動時に作成）
- ロギング:
  - kabusys.utils.logging_setup.setup_logging で stdout と日次ローテーションファイル（logs/<app_name>.log）を設定
  - 環境変数 LOG_DIR / LOG_LEVEL で挙動を変更可能
- マイグレーション:
  - init_monitoring_db は冪等でテーブルを作成し、既存 DB に対する軽微なマイグレーション（列追加）も行います

ディレクトリ構成（主要ファイル・モジュール）
---------------------------------------
- src/kabusys/
  - __init__.py
  - config.py               — 環境変数 / Settings の定義・自動 .env ロード
  - config_setup.py         — .env 対話式ウィザード
  - validate_config.py      — 起動前設定検証 CLI
  - run_execution.py        — ExecutionEngine 起動スクリプト
  - run_monitoring.py       — Monitoring ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート
  - utils/
    - logging_setup.py       — 統一的なログ設定ユーティリティ
    - process_priority.py    — プロセス優先度 / CPU affinity ユーティリティ
  - monitoring/
    - monitoring_db.py      — monitoring 用 SQLite CRUD ヘルパ
    - system_monitor.py     — システム状態・データ鮮度監視
    - trade_monitor.py      — （trade 監視、存在）
    - risk_monitor.py       — ドローダウン・ポジション監視
    - monitoring_engine.py  — 各 Monitor を束ねるエンジン
    - kill_switch.py        — kill.flag 操作ユーティリティ
    - alert_manager.py      — （通知管理、存在）
  - execution/
    - execution_engine.py   — ExecutionEngine 本体（存在）
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
    - broker_factory.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py           — ニュースセンチメント（OpenAI）
    - regime_detector.py    — 市場レジーム判定（MA + マクロセンチメント）
  - data/ (ランタイム)
    - *.db, kill.flag, stop_requested.flag, execution.pid などが配置される想定
  - logs/ (ランタイム)
    - <app_name>.log 日次ローテート

よくある質問（FAQ）
------------------
Q. MONITOR_POLL_INTERVAL はどのように設定しますか？
A. 環境変数で上書きできます。例: MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

Q. Paper Trading と本番 DB を分離していますか？
A. はい。KABUSYS_ENV=paper_trading のときは paper_sqlite_path（デフォルト data/paper_trading.db）を使用します。

Q. OpenAI を使う際の注意点は？
A. OPENAI_API_KEY を環境変数か関数引数で渡してください。API の呼び出しはコストが発生します。失敗時はフォールバック処理が行われますが、想定外の結果を避けるため運用監視を推奨します。

Q. ログファイルの場所は？
A. デフォルトは logs/<app_name>.log。環境変数 LOG_DIR で変更可能です。

貢献・デバッグ
--------------
- ログを参照して問題を確認してください（logs/ 以下）
- 設定の検証:
  - python -m kabusys.validate_config
- .env を再生成したいとき:
  - python -m kabusys.config_setup

ライセンス・その他
------------------
- 本リポジトリのライセンス表記はプロジェクトルートの LICENSE を参照してください（なければプロジェクト所有者に確認してください）。

補足
----
- 本 README はソースコード内の実装（docstring/コメント）に基づき作成しています。実際の実装や運用手順はプロジェクトの運用ドキュメントや maintainers の指示を優先してください。