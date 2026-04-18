KabuSys
=======

日本株向け自動売買システム（KabuSys）の軽量ドキュメントです。  
このリポジトリは戦略リサーチ、ポートフォリオ構築、発注エンジン（ExecutionEngine）、監視（Monitoring）、
およびニュース AI スコアリング等のユーティリティ群を含みます。

概要
----
KabuSys は以下の機能を持つモジュール群で構成されています（設計方針は "フェイルセーフ" と "ルックアヘッドバイアス回避" を重視）:

- 取引（ExecutionEngine）: ブローカークライアント経由で注文を管理・送信。paper_trading モードでは MockBrokerClient を使用して本番 DB と分離。
- 監視（Monitoring）: システム稼働状況、データ鮮度、注文ログ、リスク指標の監視。Kill Switch による発注停止シグナル出力。
- ポートフォリオ構築: 候補選定、重み計算、ポジションサイズ計算、セクター制限などの純関数ユーティリティ。
- 研究（Research）: ファクター計算（モメンタム、ボラティリティ、バリュー）、将来リターン、IC 計算、統計サマリ。
- AI（ニュース NLP / レジーム判定）: OpenAI を利用したニュースセンチメント集約と市場レジーム判定（gpt-4o-mini を想定）。
- ツール: Paper Trading の検証レポート生成など。

主な特徴
--------
- .env ベースの設定管理（config_setup による対話ウィザード、validate_config による検証）
- DuckDB（分析用） と SQLite（監視・発注ログ）を併用
- 発注処理と監視は別プロセス設計（pid / flag ファイルで連携）
- Paper Trading 用の専用 DB を用意し、本番 DB と完全分離可能
- OpenAI API（任意）を使ったニュース解析・レジーム判定（API キーは環境変数で指定）
- ログはコンソール + 日次ローテート（logs/*.log）

前提 / 依存
------------
主な Python パッケージ（例）:
- Python 3.8+
- duckdb
- psutil
- openai（AI 機能を使う場合）
- PyYAML（config 検証時に YAML の内容を検証したい場合）
（プロジェクトには requirements.txt は含まれていませんので、上記を適宜 pip インストールしてください）

セットアップ手順
----------------

1. リポジトリをクローン:
   git clone <repo-url>
   cd <repo-root>

2. 仮想環境を作成・有効化（任意）:
   python -m venv .venv
   source .venv/bin/activate  # macOS/Linux
   .venv\Scripts\activate     # Windows

3. 必要パッケージをインストール（例）:
   pip install duckdb psutil openai pyyaml

4. .env の初期作成（対話ウィザード）:
   python -m kabusys.config_setup

   ウィザードで入力するとプロジェクトルートに .env ファイルが作成されます。
   もしくは .env.example を参考に手動作成してください（.env は絶対に Git にコミットしないでください）。

5. 設定検証:
   python -m kabusys.validate_config
   --strict を付けると警告も失敗扱いになります:
   python -m kabusys.validate_config --strict

環境変数（主なもの）
--------------------
主な環境変数とデフォルト値・説明（.env に設定）:

- JQUANTS_REFRESH_TOKEN (必須): J-Quants API 用リフレッシュトークン
- KABU_API_PASSWORD (必須): kabuステーション API パスワード
- KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
- KABUSYS_ENV (default: development) : development | paper_trading | live
  - paper_trading の場合、Execution は paper_trading DB を使用（本番と分離）
- DUCKDB_PATH (default: data/kabusys.duckdb)
- SQLITE_PATH (default: data/monitoring.db) — 監視 DB（monitoring は環境にかかわらず本番 sqlite_path を使用）
- PAPER_TRADING_SQLITE_PATH (default: data/paper_trading.db) — paper_trading 用 DB
- LOG_LEVEL (default: INFO)
- LOG_DIR (default: logs/)
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID : 本番アラート用（任意）
- KILL_FLAG_CLEAR_ON_START (default: 0) : 起動時に kill.flag を自動クリアするか（本番では 0 推奨）
- OPENAI_API_KEY : OpenAI 利用時に必須（ai.score_news / regime_detector 等）
- PAPER_FILL_MODE (default: instant) : paper_trading 用 MockBrokerClient の fill 動作
  有効値: instant | partial | never | reject
- MONITOR_POLL_INTERVAL (default: 60) : run_monitoring のポーリング間隔（秒）。1 以上の整数を指定。

起動・使い方
------------

基本的にモジュールは python -m で実行できます。

1. ExecutionEngine の起動
   - paper_trading で起動する例（.env で KABUSYS_ENV=paper_trading を設定）:
     python -m kabusys.run_execution

   - 動作
     - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用して PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に記録します。
     - 起動時に data/stop_requested.flag が既に存在する場合は起動せず終了します。
     - 実行中に data/stop_requested.flag が作成されるとエンジンは graceful stop を行います。
     - PID ファイル: data/execution.pid（Settings.pid_file_path で変更可能）

2. Monitoring の起動
   python -m kabusys.run_monitoring

   - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で上書きできます（デフォルト 60 秒）。
   - 監視は本番 sqlite_path を常に参照します（Settings.sqlite_path）。
   - 監視ループ停止: data/stop_requested.flag を作成すると監視ループが終了します。
   - 監視は system_status / trade_logs / risk_logs / dashboard 等を管理・書き込みします。

3. Paper Trading 検証レポート生成（ツール）
   python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
   オプション --db で DB パスを直接指定可能:
   python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

4. AI 機能
   - ニュース NLP（ai.score_news）やレジーム判定（ai.regime_detector）を使う場合は OPENAI_API_KEY を設定してください。
   - API 呼び出しは外部ネットワークに依存するため、失敗時はフォールバックやスキップを行う設計になっています。

停止・Kill Switch
-----------------
- Execution と Monitoring の停止：プロセスに SIGINT（Ctrl+C） を送るか、プロジェクトルートの data/stop_requested.flag ファイルを作成してください（run_execution / run_monitoring が検知して終了します）。
- Kill Switch（監視 -> 発注停止）:
  - RiskMonitor 等が条件を満たすと data/kill.flag を書き込み、ExecutionEngine は起動時にこの kill.flag を読み検出します。
  - kill.flag は Settings.kill_flag_clear_on_start が 1 でなければ自動でクリアされません（本番は自動クリア無効推奨）。

ロギング
-------
- setup_logging により root ロガーを設定します。
- コンソール（stdout）と日次ローテーションファイル（logs/<app_name>.log）に出力されます。
- ログディレクトリは LOG_DIR 環境変数または既定の logs/ を使用します。

主要コマンドまとめ
------------------
- .env 作成（対話）: python -m kabusys.config_setup
- 設定検証: python -m kabusys.validate_config [--strict]
- Execution 起動: python -m kabusys.run_execution
- Monitoring 起動: python -m kabusys.run_monitoring
- Paper Trading レポート: python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]

ディレクトリ構成（抜粋）
-----------------------
以下は src/kabusys 配下の主要ファイル・モジュールのツリー（抜粋）です:

- src/kabusys/
  - __init__.py
  - config.py                # 環境変数 / Settings 管理（自動 .env ロード含む）
  - config_setup.py          # .env 対話ウィザード
  - validate_config.py       # 設定検証 CLI
  - run_execution.py         # ExecutionEngine 起動スクリプト
  - run_monitoring.py        # Monitoring 起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py  # Paper Trading 検証レポート
  - ai/
    - __init__.py
    - news_nlp.py            # ニュース NLP（OpenAI）スコアリング
    - regime_detector.py     # 市場レジーム判定（MA + マクロ NLP）
  - monitoring/
    - monitoring_db.py      # SQLite 用永続化層
    - monitoring_engine.py
    - system_monitor.py
    - trade_monitor.py      # （実装ファイルは同ディレクトリに存在）
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py      # （アラート送信実装）
  - execution/
    - execution_engine.py
    - order_manager.py
    - order_repository.py
    - broker_factory.py
    - reconciler.py
    - risk_manager.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - data/                   # デフォルトの DB / flag / pid 保存先（実行時に自動作成されます）
  - utils/
    - logging_setup.py
    - process_priority.py

（実際のリポジトリには上記以外にもサブモジュールがあります。詳しくはソースを参照してください）

注意事項 / 運用上のヒント
-----------------------
- .env は絶対にリポジトリにコミットしないでください（API キー・パスワードが含まれます）。
- 本番環境（KABUSYS_ENV=live）での KILL_FLAG_CLEAR_ON_START=1 は危険です。Kill Switch は手動での安全停止手段として扱ってください。
- monitoring は「監視」目的で本番 sqlite_path を常に使用します。paper_trading の場合も監視 DB は本番 DB を参照する仕様に注意してください（run_monitoring ドキュメント参照）。
- OpenAI 等の外部 API は失敗する前提でコードが設計されていますが、API キー制限やレートに注意してください。
- ローカルで複数プロセスを起動する際は pid / flag ファイル（data/）を適切に管理してください。

貢献 / 開発
------------
- 機能追加・修正は Pull Request を送ってください。
- 設定項目を増やす際は config_setup.py と config.py の両方を更新してください。
- 大きな DB スキーマ変更は monitoring_db.init_monitoring_db のマイグレーションロジックを拡張してください。

お問い合わせ
------------
実装上の疑問や設計に関する質問があれば、リポジトリの issue を作成してください。