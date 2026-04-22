KabuSys — README
=================

概要
----
KabuSys は日本株向けの自動売買 / 調査基盤ライブラリです。  
戦略用ファクター計算、ポートフォリオ構築、ポジションサイズ計算、監視（Monitoring）、Execution エンジン（発注処理の起動スクリプト）、およびニュース NLP / レジーム判定などの機能を含むモジュール群で構成されています。  
主にローカル実行・ペーパートレード・本番（live）を想定した設計になっています。

主な特徴
--------
- ポートフォリオ構築：
  - 候補選定、等配分・スコア加重配分、スコアベースのウェイト計算
  - ポジションサイズ計算（リスクベース、等配分、スコア配分）
  - セクター上限・レジーム乗数の適用
- ファクター / リサーチ：
  - Momentum / Volatility / Value 等のファクター計算（DuckDB を利用）
  - 将来リターン、IC（Information Coefficient）、特徴量サマリなど
- AI 支援：
  - ニュースを OpenAI（gpt-4o-mini）でスコアリングして ai_scores に書き込むロジック
  - マクロニュース + ETF MA による市場レジーム判定
  - API レート制御 / 再試行 / レスポンス検証の実装
- 実行・監視：
  - ExecutionEngine 起動スクリプト（run_execution.py）と監視用ループ（run_monitoring.py）
  - SQLite（監視ログ） + DuckDB（分析データ）を使用
  - リスク監視（ドローダウン、ポジション数上限）と Kill Switch
- 運用支援：
  - .env 対話式ウィザード（config_setup.py）
  - 設定検証ツール（validate_config.py）
  - ペーパートレード検証レポート生成ツール

要件（推奨）
------------
最低限必要な外部パッケージ（抜粋）：
- Python 3.8+
- duckdb
- psutil
- openai
- PyYAML（config ファイル検証時に利用。必須ではない）

インストール例（例示）
- 仮想環境作成・有効化
  - python -m venv .venv && source .venv/bin/activate  (Windows は .venv\Scripts\activate)
- パッケージインストール（例）
  - pip install duckdb psutil openai pyyaml

セットアップ手順
---------------
1. リポジトリの配置
   - ソースコードは src/kabusys 以下に配置されています。プロジェクトルートには .env や data/ ディレクトリを置きます。

2. .env の作成
   - 対話式ウィザードを使う（推奨）:
     - python -m kabusys.config_setup
     - ウィザードは .env を生成します。Sensitive 情報（API キー等）は入力時にマスクされます。
   - 直接作成する場合は .env.example を参考にしてください（リポジトリにある想定）。

3. 設定検証
   - python -m kabusys.validate_config
   - --strict を付けると警告もエラー扱いになります。

4. データディレクトリと DB の確認
   - デフォルトの DB/ファイルパス:
     - DuckDB: data/kabusys.duckdb
     - Monitoring SQLite: data/monitoring.db
     - Paper trading SQLite: data/paper_trading.db
     - PID / フラグ: data/execution.pid, data/kill.flag, data/stop_requested.flag
   - 必要に応じて .env で DUCKDB_PATH / SQLITE_PATH / PAPER_TRADING_SQLITE_PATH を上書きしてください。

主な環境変数（抜粋）
-------------------
- JQUANTS_REFRESH_TOKEN — J-Quants API のリフレッシュトークン（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）
- KABUSYS_ENV — 実行環境: development | paper_trading | live（デフォルト: development）
- OPENAI_API_KEY — OpenAI API キー（ai モジュール利用時）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視 DB パス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード用 SQLite（paper_trading 環境時）
- PAPER_FILL_MODE — paper_trading の約定モード（instant|partial|never|reject）
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか (0/1)
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、デフォルト 60）

起動 / 使用方法
---------------

1) 設定の検証
- python -m kabusys.validate_config
  - 環境変数や config/*.yaml（存在する場合）の妥当性をチェックします。

2) .env 対話式作成
- python -m kabusys.config_setup

3) Execution エンジン起動（発注エンジン）
- 実行（通常）:
  - python -m kabusys.run_execution
- 挙動:
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient（ペーパートレード）を利用し、Paper DB（PAPER_TRADING_SQLITE_PATH）に記録します。
  - 起動時に data/stop_requested.flag が存在する場合は起動せず終了します。
  - 実行中は data/execution.pid を利用（PID 書き込み）。
  - 停止は data/stop_requested.flag を作成するか、Kill Switch（data/kill.flag）で行います。

4) 監視ループ起動（Monitoring）
- python -m kabusys.run_monitoring
- オプション:
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒単位で指定（デフォルト 60）。
- 挙動:
  - SystemMonitor / TradeMonitor / RiskMonitor を定期実行して SQLite にログします。
  - 監視は Settings で指定した sqlite_path（監視 DB）を常に使用します（環境に依らず本番 DB パスを使用する点に注意）。

5) Paper Trading 検証レポート
- python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - PAPER_TRADING_SQLITE_PATH 環境変数で DB を指定可能。
  - 出力は標準出力にレポートを印字します。

6) AI モジュール（プログラムから呼び出す例）
- ニュースセンチメントを付与（プログラム呼び出し）例:
  - from kabusys.ai.news_nlp import score_news
  - score_news(duckdb_conn, target_date=date(2026,4,1), api_key="sk-...")

- レジーム判定（programmatic）:
  - from kabusys.ai.regime_detector import score_regime
  - score_regime(duckdb_conn, target_date=date(2026,4,1), api_key="sk-...")

運用上の注意
------------
- ログ:
  - ログはデフォルトで logs/<app_name>.log に日次ローテートで出力されます（logs ディレクトリを作成できない場合はコンソールのみ）。
  - setup_logging() が全起動スクリプトで呼ばれます。
- Kill Switch:
  - RiskMonitor 等の判定で data/kill.flag を書き込むと ExecutionEngine 停止のトリガーになります。起動時に KILL_FLAG_CLEAR_ON_START=1 を設定すると自動でクリアされますが、本番では 0 を推奨します。
- DB マイグレーション:
  - init_monitoring_db は冪等で実行され、必要なテーブルやカラム（例: latency_ms, peak_value）がなければ追加します。
- 自動 .env ロード:
  - config モジュールはプロジェクトルート（.git または pyproject.toml）を検出し、.env/.env.local を自動ロードします。自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

ディレクトリ構成（主なファイル）
----------------------------
（src/kabusys をルートにした主要ファイル・モジュール）
- __init__.py
- config.py                  — 環境変数 / Settings 管理
- config_setup.py            — .env 対話式ウィザード
- validate_config.py         — 設定検証 CLI
- run_execution.py           — ExecutionEngine 起動スクリプト
- run_monitoring.py          — Monitoring ポーリング起動スクリプト

サブパッケージ:
- ai/
  - news_nlp.py              — ニュース NLP スコアリング（OpenAI）
  - regime_detector.py       — 市場レジーム判定（AI + MA）
- monitoring/
  - monitoring_db.py         — SQLite 永続化層
  - system_monitor.py
  - trade_monitor.py         — (trade_monitor モジュールが存在、監視ロジック)
  - risk_monitor.py
  - kill_switch.py
  - monitoring_engine.py
  - alert_manager.py         — （アラート送信ロジック）
- execution/
  - execution_engine.py      — ExecutionEngine 本体（発注セッション管理）
  - broker_factory.py        — BrokerClientFactory（本番 / mock 切替）
  - order_manager.py
  - order_repository.py
  - reconciler.py
  - risk_manager.py
- portfolio/
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py
- research/
  - factor_research.py
  - feature_exploration.py
- tools/
  - paper_verification_report.py
- utils/
  - logging_setup.py
  - process_priority.py

補足
----
- 本リポジトリのコードはモジュール化されており、多くの関数はプログラムから直接インポートして利用できます（例: factor 計算、ポートフォリオ計算、AI スコアリング）。
- OpenAI API を利用する機能は API キーが必要です。API 呼び出しはリトライ・検証ロジックを持っており、失敗時にはフェイルセーフ（スキップやデフォルト値）で継続する設計です。
- 本番実行前に validate_config による検証、ログ設定の確認、kill.flag の取り扱い方針を必ずレビューしてください。

ライセンス / バージョン
-----------------------
- パッケージバージョンは kabusys.__version__ = "0.1.0"
- ライセンス情報はリポジトリのトップレベルに置いてください（ここには含めていません）。

問題報告・貢献
--------------
- バグ報告や改善提案は issue を作成してください。コードへの貢献はプルリクエストを歓迎します。

以上。必要なら README に含める具体的なコマンド例や想定 requirements.txt を追記します。どの部分を補完しますか？