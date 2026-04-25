KabuSys — 日本株自動売買システム
==============================

概要
----
KabuSys は日本株の自動売買 / 研究用ユーティリティ群を含む軽量なプロジェクトです。  
主な目的は以下です。

- 発注エンジン（ExecutionEngine）による実売買（あるいはペーパートレード）
- システム監視・アラート（Monitoring）
- ポートフォリオ構築・ポジションサイジングのユーティリティ
- 研究用ファクター計算・特徴量解析（DuckDB ベース）
- ニュースの NLP によるセンチメントスコアリング（OpenAI）
- 運用支援ツール（設定ウィザード・設定検証・ペーパートレード検証レポート生成 等）

機能一覧
--------
- Execution
  - ExecutionEngine による注文管理、リスク管理、再整合（Reconciler）
  - paper_trading（KABUSYS_ENV=paper_trading）時は MockBrokerClient を使用し、paper_trading 専用 DB に記録
- Monitoring
  - SystemMonitor（CPU/メモリ/ディスク、データ鮮度、実行プロセス検出）
  - TradeMonitor / RiskMonitor による滞留注文監視・ドローダウン監視
  - Kill Switch（条件に応じて data/kill.flag を書き込んで実行エンジンを停止）
  - Monitoring DB（SQLite）への永続化（system_status / trade_logs / risk_logs / dashboard / positions）
- Portfolio（純粋関数群）
  - 候補選定（select_candidates）
  - 等配分・スコア加重配分（calc_equal_weights / calc_score_weights）
  - セクター上限適用（apply_sector_cap）
  - レジーム乗数（calc_regime_multiplier）
  - ポジションサイズ算出（calc_position_sizes）
- Research
  - Momentum / Volatility / Value ファクター計算（DuckDB 接続を受ける）
  - 将来リターン算出、IC（Information Coefficient）計算、統計サマリー
- AI
  - ニュース NLP による銘柄別センチメントスコア（OpenAI を利用）
  - 市場レジーム判定（ETF MA + マクロ記事の LLM センチメントの合成）
- ツール
  - .env 対話式作成ウィザード（kabusys.config_setup）
  - 設定検証 CLI（kabusys.validate_config）
  - Paper Trading 検証レポート生成（kabusys.tools.paper_verification_report）
- ロギング
  - 統一的なログ設定ユーティリティ（stdout + 日次ローテーションログ）

前提 / 要件
------------
- Python 3.9+
- 必須 Python パッケージ（少なくとも）:
  - duckdb
  - psutil
  - openai (AI 機能を使う場合)
- 任意:
  - PyYAML（config/*.yaml のパース検証に必要）
- SQLite（Python 標準ライブラリの sqlite3 を使用）
- OpenAI を利用する機能は OPENAI_API_KEY が必要

セットアップ手順
----------------
1. リポジトリをクローン
   - git clone <repo-url>
2. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 必要パッケージをインストール
   - pip install -r requirements.txt
   - requirements.txt がない場合は少なくとも以下をインストール:
     - pip install duckdb psutil openai
     - 開発用に PyYAML が必要なら: pip install pyyaml
4. ディレクトリ初期化
   - data/ および logs/ はコード実行時に自動作成されます。必要なら事前に作成して権限を調整してください。
5. 環境変数設定 (.env)
   - 対話式ウィザードで .env を作成:
     - python -m kabusys.config_setup
   - もしくはプロジェクトルートに .env を作成して以下のキーを設定（最低限必須）:
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
     - KABUSYS_ENV（development / paper_trading / live、デフォルト: development）
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（ペーパートレード用 DB、paper_trading 時に使用）
     - OPENAI_API_KEY（AI 機能を使用する場合）
   - 設定を検証:
     - python -m kabusys.validate_config
     - 本番チェック（警告も FAIL とする）: python -m kabusys.validate_config --strict
6. ログ設定
   - デフォルトでは logs/ ディレクトリへアプリ別に日次ログが出力されます（設定は kabusys.utils.logging_setup 参照）。

重要な環境変数（主なもの）
-------------------------
- KABUSYS_ENV: 実行環境。development / paper_trading / live（デフォルト: development）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 SQLite（paper_trading 用）
- LOG_LEVEL: ログレベル（DEBUG / INFO / WARNING / ERROR / CRITICAL）
- MONITOR_POLL_INTERVAL: monitoring のポーリング間隔（秒、デフォルト: 60）
- PAPER_FILL_MODE: ペーパートレード時の約定モード（instant, partial, never, reject）
- OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合）

使い方
------
基本的な起動・ユーティリティの使い方例を示します。

1. 実行エンジン（ExecutionEngine）起動
   - 通常起動:
     - python -m kabusys.run_execution
   - KABUSYS_ENV=paper_trading の場合は MockBroker が使われ、PAPER_TRADING_SQLITE_PATH に記録されます。
   - 停止: data/stop_requested.flag を作成すると起動中のループが安全に終了します。
   - 実行中は data/execution.pid に PID が書き込まれます（設定で変更可）。

2. 監視プロセス（Monitoring）起動
   - python -m kabusys.run_monitoring
   - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更できます（秒、デフォルト 60）。
   - 監視は常にプロダクション sqlite_path を使用して状態を記録します（環境に依らず）。
   - 停止フラグ: data/stop_requested.flag が存在すると監視ループを終了します。
   - kill_switch により data/kill.flag が書き込まれると ExecutionEngine に停止シグナルを送れます。

3. .env 対話式作成
   - python -m kabusys.config_setup

4. 設定検証
   - python -m kabusys.validate_config
   - --strict を付けると警告もエラー扱いになります。

5. Paper Trading 検証レポート生成
   - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
   - デフォルト DB は data/paper_trading.db。--db オプションで別パス指定可。

6. AI / 研究機能（ライブラリ API）
   - ニューススコア付与:
     - Python から呼び出す例:
       from kabusys.ai.news_nlp import score_news
       score_news(duckdb_conn, target_date, api_key="...")
     - OpenAI の API キーが必要（引数または環境変数 OPENAI_API_KEY）。
   - レジームスコア:
     - from kabusys.ai.regime_detector import score_regime
       score_regime(duckdb_conn, target_date, api_key="...")
   - ファクター計算:
     - from kabusys.research import calc_momentum, calc_volatility, calc_value
       calc_momentum(duckdb_conn, datetime.date(2026,4,1))

運用上の注意
------------
- KABUSYS_ENV=live の場合は設定ミスが重大な影響を与えるため validate_config を実行してから起動してください。
- .env は絶対にリポジトリにコミットしないでください。
- OpenAI への大量リクエストは料金・レート制限に注意してください。score_news / score_regime はリトライとレート制御を備えていますが、運用前に試験することを推奨します。
- ログディレクトリや data ディレクトリのファイル権限を適切に設定してください。
- stop/kill フラグの取り扱いに注意（KILL_FLAG_CLEAR_ON_START = 1 は本番では危険）。

ディレクトリ構成（主要ファイル）
------------------------------
以下はパッケージルート src/kabusys 以下の主な構成です（抜粋）。

- kabusys/
  - __init__.py
  - config.py                  — 環境変数読み込み / Settings
  - config_setup.py            — .env 対話式ウィザード
  - validate_config.py         — 設定検証 CLI
  - run_execution.py           — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — SystemMonitor 起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート
  - utils/
    - logging_setup.py         — ログ設定ユーティリティ
    - process_priority.py      — プロセス優先度 / CPU affinity
  - monitoring/
    - monitoring_db.py         — SQLite 持続化（テーブル作成・CRUD ヘルパ）
    - system_monitor.py
    - risk_monitor.py
    - trade_monitor.py         — （監視の一部）
    - monitoring_engine.py     — 各 Monitor を束ねる
    - kill_switch.py
    - alert_manager.py         — （アラート送信ロジック、LINE など）
  - execution/
    - execution_engine.py
    - broker_factory.py
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
  - ai/
    - news_nlp.py
    - regime_detector.py
  - data/                      — 実行時に生成される（data/monitoring.db, data/kabusys.duckdb 等）
  - logs/                      — ログ出力先（デフォルト）

（注）上記はコードベースの主要モジュールの抜粋です。実際のファイル・フォルダはリポジトリの現状を参照してください。

開発・テストのヒント
-------------------
- 自動で .env を読み込む仕組みがありますが、テストや CI では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自動読み込みを無効化できます。
- DuckDB 接続を作って研究関数を単体で実行し、データが揃っているかを確認してください。
- OpenAI 呼び出し部分は呼び出し関数を patch / モックすることでユニットテストしやすく設計されています（_call_openai_api を置き換え）。

ライセンス / 貢献
-----------------
（ここにプロジェクトのライセンス情報や貢献方法を記載してください。）

補足
----
この README はプロジェクト内のコードコメントと設計意図に基づき作成しています。具体的な運用手順・設定値は運用環境に合わせて調整してください。質問や追加のドキュメントが必要であれば教えてください。