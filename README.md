README — KabuSys
=================

概要
----
KabuSys は日本株向けの自動売買／研究プラットフォームです。  
戦略のファクター計算、ポートフォリオ構築、ポジションサイズ計算、実行エンジン（発注管理・リスク管理）、監視／アラート、AI を使ったニュース評価や市場レジーム判定などのコンポーネントを含みます。  
設計方針として「本番環境と検証環境（ペーパートレード）を分離」「ルックアヘッドバイアスを避ける」「外部 API 呼び出しは明示的に行う」などに配慮しています。

主な機能
----------
- 実行エンジン起動スクリプト（run_execution）
  - KABUSYS_ENV=paper_trading 時は MockBroker を利用し、paper_trading DB に記録
  - 実行中は PID ファイルを作成、停止用フラグによる安全停止
- 監視（Monitoring）
  - System / Trade / Risk 各モニタを周期的に実行する監視ループ（run_monitoring）
  - kill.flag による ExecutionEngine 停止（Kill Switch）
  - 監視ログの永続化（SQLite）
- ポートフォリオ構築
  - 候補選定、等重・スコア重み付け、セクター制約などの純粋関数群
  - ポジションサイズ計算（リスクベース、等配分、スコアベース）、単元株丸め、aggregate cap 調整
- 研究/リサーチ
  - ファクター計算（モメンタム、ボラティリティ、バリュー等） — DuckDB を使用
  - 将来リターン、IC（Information Coefficient）計算、統計サマリ
- AI モジュール
  - ニュースのセンチメント（OpenAI）を銘柄ごとにスコア化して ai_scores に保存
  - マクロニュース + ETF MA に基づく市場レジーム判定（LLM と組合せ）
  - API 呼び出しはリトライ・バリデーションを行い安全性を確保
- ユーティリティ
  - 環境設定ウィザード（.env 生成）
  - 設定検証 CLI（環境変数・config YAML の存在／簡易パース）
  - Paper Trading 検証レポート生成ツール（期間指定で稼働率・約定率・レイテンシ等を集計）
  - ログ設定ユーティリティ、プロセス優先度設定ユーティリティ

必要条件（概略）
----------------
- Python 3.10+ を推奨（typing / pattern に依存する記述があるため）
- 必須パッケージ（例）:
  - duckdb
  - psutil
  - openai
- オプション:
  - PyYAML（config のパースチェックを行う場合）
- SQLite（標準ライブラリで動作）
- ネットワーク接続（実行時に外部 API を使う場合）

セットアップ手順
----------------
1. リポジトリをクローン
   - git clone <repo-url>
2. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate   (Windows: .venv\Scripts\activate)
3. 必要パッケージをインストール（例）
   - pip install duckdb psutil openai
   - （開発用に）pip install PyYAML
   - ※ requirements.txt がある場合はそれを使ってください。
4. 環境変数（.env）を作成
   - 対話式ウィザードで作成:
     - python -m kabusys.config_setup
   - もしくは .env を手動で作成。主要キー（config_setup が生成するもの）:
     - JQUANTS_REFRESH_TOKEN (必須)
     - KABU_API_PASSWORD (必須)
     - KABUSYS_ENV (development | paper_trading | live) — default: development
     - DUCKDB_PATH (例: data/kabusys.duckdb)
     - SQLITE_PATH (例: data/monitoring.db)
     - PAPER_TRADING_SQLITE_PATH (paper_trading 用 DB、例: data/paper_trading.db)
     - OPENAI_API_KEY（AI 機能を使う場合）
     - LOG_LEVEL, KILL_FLAG_CLEAR_ON_START 等
5. 設定検証（推奨）
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗として扱います
6. データディレクトリ作成
   - data/ と logs/ は必要に応じて自動作成されますが、権限に注意してください。

使い方（主要コマンド）
--------------------
- 環境ウィザード（.env 作成／更新）
  - python -m kabusys.config_setup
- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict
- 実行エンジン起動（ExecutionEngine）
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合、専用の paper DB を使用して MockBroker で実行されます
  - 実行はデーモン/フォアグラウンドで可能。data/execution.pid を生成します。
  - 停止は data/stop_requested.flag（run_monitoring 側で使われる）や data/kill.flag（KillSwitch）を使う運用が想定されます
- 監視ループ起動（SystemMonitor）
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）
  - 監視は monitoring 用に本番 sqlite_path を常に使用します（設定に関係なく）
- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD
    - --to YYYY-MM-DD
    - --db PATH（PAPER_TRADING_SQLITE_PATH より優先して DB を指定）
- AI スコアリング（コード呼び出し）
  - ニューススコア化:
    - from kabusys.ai.news_nlp import score_news
    - score_news(duckdb_conn, target_date, api_key="...")
  - レジーム判定:
    - from kabusys.ai.regime_detector import score_regime
    - score_regime(duckdb_conn, target_date, api_key="...")

重要な環境変数（概要）
--------------------
（完全な一覧は kabusys.config.Settings / config_setup の定義を参照してください）
- JQUANTS_REFRESH_TOKEN (必須) — J-Quants API 用
- KABU_API_PASSWORD (必須) — kabuステーション API
- KABUSYS_ENV — execution の挙動を切り替え (development | paper_trading | live)
- DUCKDB_PATH — DuckDB ファイルパス（分析用）
- SQLITE_PATH — 監視 DB（monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード専用 SQLite（paper_trading.db）
- OPENAI_API_KEY — OpenAI API を使う機能のため
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒）
- KILL_FLAG_CLEAR_ON_START — Execution 起動時に kill.flag を自動消去するか（1=yes, 0=no）

運用メモ
--------
- Kill Switch:
  - RiskMonitor がしきい値を超えると KillSwitch が data/kill.flag を書き込みます。
  - ExecutionEngine は起動時および実行中に kill.flag を検知すると停止を受け入れます。
  - KILL_FLAG_CLEAR_ON_START=1 にすると Execution 起動時に自動クリアされます。live 環境では 0 を推奨します。
- 監視と実行の DB 分離:
  - run_monitoring は環境に関わらず settings.sqlite_path（本番監視 DB）を使用します。
  - run_execution は KABUSYS_ENV=paper_trading の場合、paper_sqlite_path を使用し本番 DB と分離します。
- ログ:
  - logs/<app_name>.log に日次ローテーションで保存されます（defaults: logs/）。
  - setup_logging() で stdout とログファイルの両方を設定します。
- プロセス優先度:
  - 起動スクリプトは最初に set_process_priority("high") を試みます。権限がない場合は警告ログが出ます。

コード構成（主要ファイル）
------------------------
以下は src/kabusys 配下の主要ファイル（抜粋）です。

- src/kabusys/
  - __init__.py
  - config.py                — 設定読み取り / Settings
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py       — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート
  - ai/
    - news_nlp.py            — ニュース NLP スコアリング
    - regime_detector.py     — 市場レジーム判定
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - monitoring/
    - monitoring_db.py
    - monitoring_engine.py
    - system_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - (trade_monitor.py は参照される箇所あり)
  - execution/
    - execution_engine.py    — 実行エンジン本体（参照実装）
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
    - broker_factory.py
  - utils/
    - logging_setup.py
    - process_priority.py

（上記に含まれない補助モジュールやスクリプトがプロジェクトに存在する場合があります）

ディレクトリツリー（例）
-----------------------
プロジェクトのトップレベル例:

- .env
- pyproject.toml / setup.cfg
- src/
  - kabusys/
    - __init__.py
    - config.py
    - config_setup.py
    - validate_config.py
    - run_execution.py
    - run_monitoring.py
    - portfolio/
    - research/
    - ai/
    - monitoring/
    - execution/
    - tools/
    - utils/
- config/
  - system_config.yaml
  - strategy_config.yaml
  - ...（テンプレートは scripts/generate_config.py などで生成）

追加情報 / トラブルシューティング
--------------------------------
- DuckDB / SQLite のファイルパスの親ディレクトリが存在しない場合、validate_config が警告を出します。起動時に自動作成されることもありますが、権限をチェックしてください。
- OpenAI を利用する機能は API キー必須です。AI 機能は失敗時に安全側のフォールバック（スコア 0.0 等）をする設計です。
- ログディレクトリの作成に失敗するとコンソール出力のみになります（setup_logging の仕様）。
- テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると .env 自動ロードを無効化できます。

貢献・開発
----------
- コードのビジネスロジックと I/O を分離する設計を心がけています。ユニットテストでは DB 接続や API 呼び出しをモックしてください（例: news_nlp の API 呼び出しは差し替え可能に実装済み）。
- 新しい設定項目追加時は config_setup.py、config.py、validate_config.py のそれぞれを更新してください。

以上。詳細は各モジュールの docstring / ソースコメントを参照してください。