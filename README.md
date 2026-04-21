KabuSys
=======

日本株自動売買システムの軽量実装（ライブラリ＋起動スクリプト群）。  
このリポジトリは、シグナル生成 / ポートフォリオ構築 / 発注実行（実口座・ペーパートレード両対応） / 監視 / AI を組み合わせた構成になっています。

主な特徴
-------
- ポートフォリオ構築（候補選定・重み付け・ポジションサイズ算出）
- リスク調整（セクター上限、レジーム乗数）
- 発注エンジン（ExecutionEngine、ペーパートレード時は MockBrokerClient を利用し DB を分離）
- 監視（System / Trade / Risk モニタ、Kill Switch による安全停止）
- AI モジュール（ニュース NLP によるセンチメントスコア、レジーム判定）
- 研究用モジュール（ファクター計算、特徴量探索、IC 計算）
- 各種ユーティリティ（ログ設定、プロセス優先度設定、.env ウィザード、設定検証）
- DuckDB / SQLite によるデータ管理（分析用 DuckDB、監視・ペーパー用 SQLite）

要件
----
- Python 3.10+
- 必須パッケージ（例）
  - duckdb
  - psutil
  - openai
  - （オプション）PyYAML（config/*.yaml の検証で使用）
- これらはプロジェクトに requirements.txt がない場合は手動でインストールしてください:
  pip install duckdb psutil openai pyyaml

設定（.env）
-----------
環境変数またはルートの .env / .env.local で設定します。自動ロード機能が有効（KABUSYS_DISABLE_AUTO_ENV_LOAD 未設定）なら起動時に .env を読み込みます。

必須（最低限）
- JQUANTS_REFRESH_TOKEN=...
- KABU_API_PASSWORD=...

重要な設定例（主なもの）
- KABUSYS_ENV=development|paper_trading|live
  - paper_trading の場合、発注は MockBrokerClient を使い data/paper_trading.db に記録します。
- DUCKDB_PATH=data/kabusys.duckdb
- SQLITE_PATH=data/monitoring.db
- PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
- OPENAI_API_KEY=...（AI モジュールを使う場合）
- LOG_LEVEL=INFO

.env を対話式に作成する
- python -m kabusys.config_setup
  - ウィザードで .env を作成または更新します。
  - 生成後は必ず設定検証を行ってください（下記）。

設定検証
- python -m kabusys.validate_config
  - 必須環境変数や config/*.yaml の存在と簡易検証を行います。
  - --strict を付けると警告も失敗扱い（exit code=1）。

起動 / 実行方法
------------

1) 実行エンジン（Execution）
- 目的: 発注ロジックを実行するメインプロセス
- コマンド:
  - python -m kabusys.run_execution
- 挙動:
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使い、データは PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に記録され、本番 DB と分離されます。
  - 起動時に data/stop_requested.flag が既に存在すると起動せず終了します（安全措置）。
  - PID ファイル: data/execution.pid （Settings.pid_file_path で変更可）
  - プロセス優先度を "high" に設定しようとします（psutil が必要、権限によっては失敗してスキップされます）。

2) 監視ループ（Monitoring）
- 目的: システム・注文・リスク監視を定期的に実行してログ/アラート/kill switch を管理
- コマンド:
  - python -m kabusys.run_monitoring
- 挙動:
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL（秒）で上書き可能（デフォルト 60 秒）。1 秒未満や 0 は無効でデフォルトにフォールバックします。
  - Monitoring は KABUSYS_ENV に関わらず Settings.sqlite_path（デフォルト data/monitoring.db）を使用します（監視 DB は本番用を想定）。
  - data/stop_requested.flag を監視して存在すればループを終了します。

3) Paper Trading 検証レポート
- 目的: ペーパートレード履歴を集計して PASS/FAIL 判定のレポートを作成
- コマンド:
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
- DB 指定:
  - --db オプション、または環境変数 PAPER_TRADING_SQLITE_PATH、省略時は data/paper_trading.db

4) AI / 研究関数
- AI:
  - kabusys.ai.score_news(conn, target_date, api_key=None) — raw_news を OpenAI に送信して ai_scores を更新
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None) — レジーム判定と market_regime への書き込み
  - どちらも OPENAI_API_KEY（または api_key 引数）が必要
- 研究:
  - kabusys.research.calc_momentum / calc_volatility / calc_value
  - kabusys.research.calc_forward_returns / calc_ic / factor_summary
  - これらは DuckDB 接続を受け取り、prices_daily / raw_financials 等のテーブルを参照します

停止 / Kill Switch / 制御ファイル
-------------------------------
- data/kill.flag
  - KillSwitch（監視側）が条件を満たしたときに書き込むファイル。ExecutionEngine はこのフラグで停止されます。
  - KillSwitch が書き込む理由テキストがファイルに保存されます。
- data/stop_requested.flag
  - run_monitoring.py / run_execution.py のループ停止制御に使われるフラグ。存在すると監視やエンジンの起動を停止または終了します。
- KILL_FLAG_CLEAR_ON_START=1（.env）を設定すると起動時に kill.flag を自動で削除できます（本番では 0 を推奨）。

ロギング
-------
- 共通ロギングは kabusys.utils.logging_setup.setup_logging を通じて設定されます。
- 出力:
  - コンソール(stdout)
  - 日次ローテーションファイル: logs/<app_name>.log（デフォルト、30 日保持）
- LOG_DIR 環境変数または setup_logging の引数で変更可能

主要な環境変数一覧（抜粋）
--------------------------
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV (development|paper_trading|live) — デフォルト development
- LOG_LEVEL (DEBUG|INFO|...)
- DUCKDB_PATH (default: data/kabusys.duckdb)
- SQLITE_PATH (default: data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH (default: data/paper_trading.db)
- OPENAI_API_KEY (AI モジュール使用時に必要)
- MONITOR_POLL_INTERVAL (監視のポーリング間隔（秒）)
- KILL_FLAG_CLEAR_ON_START (0|1)

ディレクトリ構成（主要ファイル）
------------------------------
（src/kabusys 以下を抜粋）

- kabusys/
  - __init__.py
  - config.py                — 環境変数読み込み・Settings
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — Monitoring ポーリングループ起動スクリプト
  - tools/
    - paper_verification_report.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - execution/               — 発注エンジン周りの実装（OrderManager 等はここ）
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - risk_monitor.py
    - trade_monitor.py (参照)
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py (参照)
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py
    - regime_detector.py
  - utils/
    - logging_setup.py
    - process_priority.py

注意事項 / 運用メモ
------------------
- Python バージョンは 3.10 以上を推奨（型アノテーションで | を使用）。
- psutil を使ってプロセス優先度や CPU affinity を設定します。権限によっては設定に失敗することがあります（ログに警告）。
- Monitoring は監視 DB として sqlite を使用します。監視処理は環境に依らず sqlite_path を参照するため、設定ファイルでの DB パス管理に注意してください。
- AI モジュールは外部 API（OpenAI）に依存します。API 呼び出しはリトライ/フェイルセーフ実装されていますが、APIキーや料金に注意してください。
- .env を決してリポジトリにコミットしないでください（config_setup でも同旨の注意書きがあります）。
- データディレクトリ（data/）やログディレクトリ（logs/）の権限を事前に確認してください。

よく使うコマンドまとめ
---------------------
- .env 対話式作成: python -m kabusys.config_setup
- 設定検証:          python -m kabusys.validate_config [--strict]
- 実行エンジン起動:  python -m kabusys.run_execution
- 監視ループ起動:    python -m kabusys.run_monitoring
- ペーパーレポート:  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- AI スコアリング（例）:
    - Python REPL で duckdb 接続を作成し kabusys.ai.score_news を呼び出す（OPENAI_API_KEY 必要）

サポート / 拡張ポイント
-----------------------
- strategy / execution の実装はモジュール化されており、ブローカープラグインやポートフォリオ戦略の差し替えが可能です。
- DuckDB のスキーマ（prices_daily / raw_financials / raw_news 等）を投入すれば研究モジュールで分析・ファクター検証ができます。
- 将来的に銘柄別 lot_size や手数料モデルの拡張余地あり（position_sizing.py に TODO コメントあり）。

ライセンス
---------
（ここにプロジェクトのライセンス情報を記載してください）

以上。必要であればセットアップ手順の詳細（例: 仮想環境作成、依存パッケージのインストール、初期データ投入手順）や各モジュールの API 使用例を追記します。どの部分を詳しく記載しますか？