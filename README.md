KabuSys — 日本株自動売買システム
================================

概要
----
KabuSys は日本株の自動売買・研究・監視を目的とした Python パッケージです。  
本リポジトリには以下の主要機能を備えています。

- ExecutionEngine（注文発行／リスク管理／約定処理）
- Monitoring（システム稼働・注文状態・リスク監視、Kill Switch）
- Portfolio construction（銘柄選定・配分・ポジションサイズ）
- Research（ファクター／特徴量解析、IC 計算）
- AI モジュール（ニュース NLP によるセンチメント集約、レジーム判定）
- ユーティリティ（設定ウィザード、設定検証、紙トレード検証レポート）

主な特徴
--------
- 環境ごとの分離（development / paper_trading / live）
  - paper_trading 環境では MockBrokerClient を使用し、paper_trading 用の SQLite DB に記録します。
- Monitoring と Execution のプロセス優先度調整（高優先度で起動）
- DuckDB を利用した分析・研究向け高速クエリ
- OpenAI を使ったニュースセンチメント分析（gpt-4o-mini を想定）
- .env ベースの設定管理（対話式ウィザードと検証 CLI あり）
- ログはコンソール（stdout）と日次ローテートファイルへ出力（logs/*.log）

セットアップ
------------
1. リポジトリをクローンして仮想環境を作成・有効化します。
   (例)
   - python >= 3.9 を想定
   - python -m venv .venv
   - source .venv/bin/activate

2. 必要なパッケージをインストールします（pip の例）。
   必須ライブラリ（少なくとも以下は必要）:
   - duckdb
   - psutil
   - openai
   - （任意）PyYAML（config/*.yaml の内容検証用）

   例:
   - pip install duckdb psutil openai PyYAML

3. 環境変数の準備
   - 対話式ウィザードで .env を作成できます:
     python -m kabusys.config_setup
   - または .env を手動で作成してください（.env.example を参考に）。最低限の必須項目:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - 重要な環境変数（抜粋）:
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
     - OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合）
     - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（デフォルト: data/paper_trading.db）
     - LOG_LEVEL / LOG_DIR
     - PAPER_FILL_MODE: instant | partial | never | reject（paper_trading の約定挙動）
     - MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、デフォルト 60）

4. ディレクトリ作成（自動で作られる場合あり）:
   - data/
   - logs/

使い方（主要コマンド）
--------------------

- 環境設定ウィザード（.env の作成/更新）
  - python -m kabusys.config_setup

- 設定検証 CLI
  - python -m kabusys.validate_config
  - 厳格モード（警告も失敗扱い）: python -m kabusys.validate_config --strict

- ExecutionEngine（実トレード／ペーパートレード実行）
  - python -m kabusys.run_execution
  - 動作概要:
    - Settings を読み、KABUSYS_ENV が paper_trading の場合は専用の paper_trading DB を使用し MockBrokerClient を使います。
    - 起動時に data/stop_requested.flag が存在する場合は起動しません。
    - 実行中は data/stop_requested.flag により停止を受け付けます。
    - Monitoring の KillSwitch（data/kill.flag）により停止させる仕組みがあります（Monitoring 側が書き込み）。

- Monitoring（システム監視ループ）
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒単位で上書き可（デフォルト 60 秒）。
  - Monitoring は KABUSYS_ENV に関わらず本番 sqlite_path（Settings.sqlite_path）を使用してログを保存します。
  - 監視処理は system_monitor, trade_monitor, risk_monitor を呼び、必要に応じて KillSwitch を作動させ data/kill.flag を書きます。
  - 停止: data/stop_requested.flag を作成するとループが終了します。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - デフォルト DB: data/paper_trading.db（環境変数 PAPER_TRADING_SQLITE_PATH で上書き可）
  - 出力: 稼働率・注文成功率・送信率・レイテンシ等のサマリと PASS/FAIL 判定

ログと監視ファイルについて
--------------------------
- ログ:
  - デフォルトログディレクトリ: logs/
  - 各アプリケーション名（例: execution, monitoring）で <app_name>.log を日次ローテート（30 日保存）
  - ログレベルは LOG_LEVEL 環境変数または setup_logging の引数で制御

- PID / フラグファイル:
  - data/execution.pid: ExecutionEngine の PID（設定ファイルで上書き可）
  - data/kill.flag: Monitoring が書き込む Kill Switch（存在すると ExecutionEngine に停止シグナルとなる）
  - data/stop_requested.flag: 開発・運用停止用フラグ。run_execution/run_monitoring のループが検出して安全に終了する
  - これらファイルは Settings でパスを変更できます

重要な挙動（環境による違い）
--------------------------
- KABUSYS_ENV の値:
  - development: 開発用。発注等は行わない想定（実装での取り扱いに依存）
  - paper_trading: MockBrokerClient を使い、paper_trading 用 DB（data/paper_trading.db）に記録。PAPER_FILL_MODE が発注約定挙動を制御
  - live: 本番モード（実際に発注が行われるため注意が必要）
- PAPER_FILL_MODE:
  - instant / partial / never / reject（paper_trading モードの約定シミュレーション振る舞い）
- Monitoring は常に Settings.sqlite_path（production path）を使用する設計です（監視ログを本番 DB に付与する想定）

主要モジュール説明
------------------
- kabusys.config
  - .env の自動読み込み、Settings クラスによる環境変数アクセスラッパ
  - 必須 env のチェックは validate_config で行う

- kabusys.utils
  - logging_setup: 統一的ログ設定
  - process_priority: プロセス優先度／CPU affinity 設定ユーティリティ

- kabusys.execution
  - ExecutionEngine、OrderManager、RiskManager、Reconciler、BrokerClientFactory など（起動スクリプト: run_execution）

- kabusys.monitoring
  - monitoring_db: 監視用 SQLite テーブル定義と CRUD
  - system_monitor / trade_monitor / risk_monitor: 各種監視ロジック
  - monitoring_engine: 監視ループの統合
  - kill_switch: リスク条件に基づく kill.flag 書き込み

- kabusys.portfolio
  - portfolio_builder, position_sizing, risk_adjustment: 銘柄選定・重み付け・ポジションサイズ計算

- kabusys.research
  - factor_research: モメンタム・バリュー・ボラティリティ等のファクター計算（DuckDB 経由）
  - feature_exploration: 将来リターン計算、IC、統計サマリ

- kabusys.ai
  - news_nlp: raw_news を LLM でセンチメント解析して ai_scores へ書き込む
  - regime_detector: マクロセンチメントと MA200 を合成して市場レジーム判定を行い market_regime テーブルへ保存

設定検証と初期化ワークフロー（推奨）
---------------------------------
1. python -m kabusys.config_setup で .env を生成／更新
2. python -m kabusys.validate_config で必須設定やパスを確認（--strict を推奨）
3. DB（data/）や logs/ ディレクトリを作成（多くの場合自動作成されます）
4. python -m kabusys.run_monitoring を先に起動して監視を開始
5. python -m kabusys.run_execution を起動（paper_trading の場合は DB が分離されます）

安全運用メモ
------------
- 本番運用前に validate_config で警告・エラーがないことを確認してください
- KABUSYS_ENV=live の場合は LINE の通知設定等を確実に設定してください（validate_config に警告あり）
- Kill Switch（data/kill.flag）や stop_requested.flag の挙動を理解しておくこと
- ログを定期的にローテーション／アーカイブしてください（logs/ 配下）

簡易ディレクトリ構成
--------------------
（主要ファイルのみ抜粋）

- src/
  - kabusys/
    - __init__.py
    - config.py
    - config_setup.py
    - validate_config.py
    - run_execution.py
    - run_monitoring.py
    - execution/  (ExecutionEngine, order_manager, broker_factory, etc.)
    - monitoring/
      - monitoring_db.py
      - monitoring_engine.py
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
      - news_nlp.py
      - regime_detector.py
    - tools/
      - paper_verification_report.py
    - utils/
      - logging_setup.py
      - process_priority.py

バージョン
---------
パッケージバージョンは kabusys.__version__ = "0.1.0"

ライセンス・貢献
----------------
（この README には含まれていません。プロジェクトルートに LICENSE があればそちらを参照してください）

付録: よく使うコマンド例
-----------------------
- .env を作る（ウィザード）:
  python -m kabusys.config_setup

- 設定検証:
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict

- 監視を開始:
  python -m kabusys.run_monitoring &
  # 停止: touch data/stop_requested.flag

- エンジンを起動（paper_trading か live に応じて動作）:
  python -m kabusys.run_execution &
  # 停止（Monitoring 経由の Kill Switch）:
  # monitoring が条件のとき data/kill.flag を書き込む
  # 手動で停止要求:
  touch data/stop_requested.flag

- Paper Trading レポート:
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

以上。設定や運用方針に応じて .env や systemd / supervisor のユニットファイルを作成して安全にデプロイしてください。必要なら、systemd ユニット／dockerfile のサンプルも作成可能です。