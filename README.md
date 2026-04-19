README
=====

概要
----
KabuSys は日本株自動売買システムのコードベースです。  
ポートフォリオ構築・ポジションサイズ計算、リサーチ（ファクター計算 / 特徴量解析）、AI ベースのニュース NLP、実行エンジン（発注）および監視（モニタリング）を含むモジュール群で構成されています。  
本リポジトリは主に次の用途を想定しています：戦略研究、ペーパートレード検証、本番運用支援。

主な特徴
--------
- ポートフォリオ構築
  - シグナル選定、等配分・スコア加重の重み計算
  - リスク調整（セクター上限、レジーム乗数）
  - ポジションサイズ計算（単元株丸め、aggregate cap）
- リサーチ
  - Momentum / Volatility / Value 等のファクター計算（DuckDB を利用）
  - 将来リターン計算、IC（Information Coefficient）や統計サマリー
- AI 支援
  - ニュースのセンチメント解析（OpenAI API を利用）
  - マクロニュース + ETF MA を使った市場レジーム判定
- 実行エンジン（Execution）
  - 本番 / ペーパートレード切替対応（ペーパー時は MockBrokerClient を使用）
  - 注文・リスク管理・再コンシリエーション等（Engine モジュール）
- 監視（Monitoring）
  - システム状態（CPU/メモリ/ディスク）、データ鮮度、注文ログ、リスク監視
  - Kill Switch（flag ファイル）による安全停止
  - 監視ループ・アラート管理・監視 DB（SQLite）
- 運用ユーティリティ
  - .env 対話式ウィザード（config_setup）
  - 設定検証 CLI（validate_config）
  - ペーパートレード検証レポート生成ツール

セットアップ手順
--------------
1. リポジトリをクローン
   - git clone ... && cd <project_root>

2. Python 仮想環境を作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - 必要なパッケージ（例）:
     - duckdb
     - psutil
     - openai
     - PyYAML（config の YAML 検証を行う場合）
   - 例:
     - pip install duckdb psutil openai PyYAML

   ※ requirements.txt はこのコードスニペットに含まれていません。プロジェクトの配布物に合わせて適宜インストールしてください。

4. データ・ログ用ディレクトリを準備（起動時に自動作成されることが多いですが事前作成しておくと安心です）
   - mkdir -p data logs

5. 環境変数設定
   - 対話型ウィザードで .env を生成:
     - python -m kabusys.config_setup
   - ウィザード実行後、設定を検証:
     - python -m kabusys.validate_config
   - 主要な環境変数（主なもの）:
     - JQUANTS_REFRESH_TOKEN (必須)
     - KABU_API_PASSWORD (必須)
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
     - DUCKDB_PATH — デフォルト: data/kabusys.duckdb
     - SQLITE_PATH — デフォルト: data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH — ペーパートレード用 DB（paper_trading モード）
     - LOG_LEVEL — デフォルト: INFO
     - OPENAI_API_KEY — AI 機能を使う場合に必要
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — 本番アラート用（任意）
     - MONITOR_POLL_INTERVAL — 監視ループのポーリング間隔（秒、デフォルト 60）
     - PAPER_FILL_MODE — ペーパートレードの約定挙動（instant/partial/never/reject）

6. （任意）Kill Flag のクリア設定
   - 本番では KILL_FLAG_CLEAR_ON_START=0 を推奨（誤って Kill Switch を無効化しないため）
   - 設定は .env で行う（config_setup がサポート）

使い方
------
- 実行エンジン（ExecutionEngine）起動
  - 通常起動（デフォルト DB を使用）
    - python -m kabusys.run_execution
  - ペーパートレードで起動
    - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
    - ペーパー時は MockBrokerClient を使い、デフォルトで data/paper_trading.db に記録されます。

  注意:
   - 起動時に data/stop_requested.flag が存在すると起動を中止します。
   - 実行中はデーモンスレッドで engine.run_session() が動作し、stop flag や外部シグナルで安全に停止できます。
   - Execution 起動時にプロセス優先度を高に設定します（psutil による）。

- 監視プロセス起動
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を変更できます（デフォルト 60）。
  - 監視は本番 sqlite_path を常に使用します（KABUSYS_ENV に依存せず）。

- 設定ウィザード（.env 生成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - --strict オプションを指定すると警告も失敗（exit code 1）扱いになります。

- ペーパートレード検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - python -m kabusys.tools.paper_verification_report --db path/to/db.sqlite
  - 指標：稼働率、注文成功率、送信率、P95 レイテンシ等を集計して PASS/FAIL 判定を出力します。

運用上のポイント / フラグ類
-------------------------
- Kill Switch
  - KillSwitch は Settings.kill_flag_path（デフォルト data/kill.flag）へ書き込み、ExecutionEngine に停止シグナルを送ります。
  - KillSwitch は冪等に動作し、既にファイルがあれば再書き込みしません。
  - 実行開始時に KILL_FLAG_CLEAR_ON_START=1 を設定すると kill.flag を自動クリアする挙動を許す設定があるため、本番では 0 を推奨します。

- Stop フラグ
  - run_monitoring / run_execution はプロジェクトルートの data/stop_requested.flag を監視し、存在するとループを終了します（安全なシャットダウン）。

- ログ
  - logs/<app_name>.log に日次ローテーションで出力されます（デフォルト保存 30 日）。
  - setup_logging 関数で統一的に設定されます。stdout にも出力されます（cron/Task Scheduler に向くよう stdout を使用）。

- DB の分離
  - 監視ログ（monitoring）は settings.sqlite_path（デフォルト data/monitoring.db）を使用。
  - ペーパートレードは paper_sqlite_path（デフォルト data/paper_trading.db）を使用して本番 DB と分離します。
  - DuckDB（分析用）は settings.duckdb_path（デフォルト data/kabusys.duckdb）。

主要モジュール一覧（抜粋）
------------------------
- run_monitoring.py — SystemMonitor ポーリングループ起動
- run_execution.py — ExecutionEngine 起動スクリプト
- config.py — 環境変数 / 設定取得ラッパー（Settings）
- config_setup.py — .env 対話式ウィザード
- validate_config.py — 起動前の設定検証 CLI
- monitoring/
  - monitoring_db.py — SQLite 永続化層（system_status / trade_logs / positions / risk_logs / dashboard）
  - system_monitor.py, trade_monitor.py, risk_monitor.py, monitoring_engine.py, kill_switch.py, alert_manager.py
- execution/ (エンジン関連; 一部はスニペットに含まれていません)
  - execution_engine.py, order_manager.py, order_repository.py, reconciler.py, risk_manager.py, broker_factory.py
- portfolio/
  - portfolio_builder.py, position_sizing.py, risk_adjustment.py
- research/
  - factor_research.py, feature_exploration.py
- ai/
  - news_nlp.py, regime_detector.py
- tools/
  - paper_verification_report.py
- utils/
  - logging_setup.py, process_priority.py

ディレクトリ構成（主要ファイル）
------------------------------
プロジェクトルート（省略可能なファイルを除く）
- src/
  - kabusys/
    - __init__.py
    - run_monitoring.py
    - run_execution.py
    - config.py
    - config_setup.py
    - validate_config.py
    - tools/
      - __init__.py
      - paper_verification_report.py
    - portfolio/
      - portfolio_builder.py
      - position_sizing.py
      - risk_adjustment.py
      - __init__.py
    - research/
      - factor_research.py
      - feature_exploration.py
      - __init__.py
    - ai/
      - news_nlp.py
      - regime_detector.py
      - __init__.py
    - monitoring/
      - monitoring_db.py
      - system_monitor.py
      - trade_monitor.py
      - risk_monitor.py
      - kill_switch.py
      - monitoring_engine.py
      - alert_manager.py
    - utils/
      - logging_setup.py
      - process_priority.py
      - __init__.py
    - execution/
      - execution_engine.py
      - order_manager.py
      - order_repository.py
      - reconciler.py
      - risk_manager.py
      - broker_factory.py
    - data/ (実行時に作成される想定)
      - monitoring.db (既定)
      - paper_trading.db (ペーパートレード時)
      - kill.flag, stop_requested.flag, execution.pid
- logs/

補足（設計上の注意）
-------------------
- DuckDB を分析基盤に使用しています。research モジュールは DuckDB 接続を受け取り SQL を主体に計算します（外部 API に依存しません）。
- AI 機能は OpenAI API（gpt-4o-mini を想定）を使用します。API キーの管理は環境変数 OPENAI_API_KEY を推奨します。
- 設定ファイル .env は絶対に Git にコミットしないでください（config_setup のヘッダにも記載あり）。
- 本番運用時は KABUSYS_ENV=live に設定し、LINE通知等のアラート設定を必ず確認してください（validate_config の live チェック参照）。

問い合わせ / 開発メモ
--------------------
- 開発中の仕様変更に注意してください（特に DB スキーマや設定キー）。config_setup / validate_config を使って起動前に検証することを推奨します。
- ロギング・Kill Switch・stop flag の挙動は運用上重要です。運用ドキュメントに従って慎重に扱ってください。

以上。必要であれば README に含めるサンプル .env、運用手順（サービス化 / systemd / supervisor のサンプル）や各モジュールの詳細ドキュメントを追加します。どの情報を優先して追記しますか？