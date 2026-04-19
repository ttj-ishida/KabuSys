README
=====

プロジェクト概要
----------------
KabuSys は日本株向けの自動売買・リサーチ基盤を想定した Python パッケージです。本コードベースは以下の主要機能を提供します。

- 実行エンジン（ExecutionEngine）の起動スクリプト / 停止フラグ管理
- システム監視（SystemMonitor）・トレード監視・リスク監視・Kill Switch
- ポートフォリオ構築（候補選定・重み付け・ポジションサイズ計算）
- リサーチ用ファクター計算（モメンタム、ボラティリティ、バリュー等）
- Paper Trading 検証レポート生成ツール
- ニュースの NLP スコアリング（OpenAI API を利用）
- 環境設定ウィザードと設定検証 CLI
- ログ設定・プロセス優先度ユーティリティ等のユーティリティ群

主な設計方針は「本番 DB と Paper Trading の分離」「ルックアヘッドバイアスを避ける」「外部 API 失敗時はフェイルセーフで継続する」ことです。

機能一覧
--------
- 起動スクリプト
  - run_execution.py: ExecutionEngine を起動（KABUSYS_ENV による Paper/Live 切替）
  - run_monitoring.py: SystemMonitor のポーリングループを起動
- 環境管理
  - config_setup.py: .env の対話式ウィザード（作成 / 更新）
  - validate_config.py: .env や config/*.yaml の事前検証 CLI
- 監視
  - monitoring_engine, SystemMonitor, TradeMonitor, RiskMonitor, KillSwitch
  - 監視ログ永続化: SQLite（monitoring_db.py）
- ポートフォリオ構築
  - 候補選定、等重・スコア重み、リスク調整、ポジションサイズ計算
- リサーチ
  - factor_research.py: momentum/volatility/value の計算（DuckDB 利用）
  - feature_exploration.py: 将来リターン、IC、統計サマリー等
- AI（OpenAI）
  - news_nlp.py: ニュースから銘柄ごとのセンチメントを生成し ai_scores に格納
  - regime_detector.py: ma200 とマクロセンチメントを組み合わせて市場レジーム判定
- ツール
  - tools/paper_verification_report.py: Paper Trading の検証レポート生成

依存関係（主なもの）
------------------
- Python 3.10+（型注釈や構文から推奨）
- duckdb
- psutil
- openai（AI 機能を利用する場合）
- PyYAML（config/*.yaml の内容検証を行う場合。なくても動作するが検証が省略されます）

セットアップ手順
----------------
1. 仮想環境を作成して有効化（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要なパッケージをインストール
   - pip install duckdb psutil openai PyYAML
   - （プロダクション用途では requirements.txt を用意して pip install -r で管理してください）

3. プロジェクトルート（.git または pyproject.toml がある場所）に移動して作業します。

4. 初期 .env の作成（対話式ウィザード）
   - python -m kabusys.config_setup
   - このウィザードは .env を生成します。.env は絶対に Git にコミットしないでください。

5. 設定検証（起動前に推奨）
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗（exit code 1）として扱います。

主な環境変数
--------------
（.env に書き込む想定の主要キー）
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL (default: http://localhost:18080/kabusapi)
- DUCKDB_PATH (default: data/kabusys.duckdb)
- SQLITE_PATH (default: data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH (default: data/paper_trading.db)
- KABUSYS_ENV (development | paper_trading | live)（default: development）
- LOG_LEVEL (DEBUG/INFO/WARNING/ERROR/CRITICAL)
- OPENAI_API_KEY（AI 機能を使う場合）
- PAPER_FILL_MODE (instant | partial | never | reject) — Paper Trading の約定挙動
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、デフォルト 60）

使い方
------
- ExecutionEngine を起動
  - 通常起動:
    - python -m kabusys.run_execution
  - Paper Trading: KABUSYS_ENV=paper_trading を設定して起動すると MockBrokerClient を使い、data/paper_trading.db に記録されます。
    - 例: KABUSYS_ENV=paper_trading python -m kabusys.run_execution

  - 実行時は data/execution.pid（デフォルト）に PID を書きます。stop フラグファイル data/stop_requested.flag が存在すると起動を停止/終了します。

- Monitoring を起動
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を変更できます（例: MONITOR_POLL_INTERVAL=30）。
  - 監視は monitoring.db（Settings.sqlite_path）へログを格納します（監視は環境にかかわらず本番 sqlite_path を使用する設計です）。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db で別の SQLite ファイルを指定できます（PAPER_TRADING_SQLITE_PATH 環境変数も利用可）。

- 設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config [--strict]

- AI 機能（プログラムから呼び出す例）
  - ニューススコアリング:
    - import duckdb, datetime
    - conn = duckdb.connect("data/kabusys.duckdb")
    - from kabusys.ai.news_nlp import score_news
    - score_news(conn, datetime.date(2026, 4, 1), api_key="YOUR_OPENAI_KEY")
  - レジーム判定:
    - from kabusys.ai.regime_detector import score_regime
    - score_regime(conn, datetime.date(2026,4,1), api_key="YOUR_OPENAI_KEY")
  - 注意: AI 機能を利用する場合は OPENAI_API_KEY を設定するか api_key を明示してください。API 呼び出し失敗時はフォールバック（安全側のデフォルト値）で継続する設計です。

DB とログの場所
----------------
- DuckDB: デフォルト data/kabusys.duckdb（Settings.duckdb_path）
- SQLite（監視）: デフォルト data/monitoring.db（Settings.sqlite_path）
- Paper Trading SQLite: data/paper_trading.db（Settings.paper_sqlite_path）
- ログ: logs/<app_name>.log（setup_logging により日次ローテーションで保存、デフォルト logs ディレクトリ）

kill / stop フラグ
-----------------
- ExecutionEngine の停止指示:
  - data/kill.flag: KillSwitch により書き込まれる（ExecutionEngine 停止のトリガー）
  - data/stop_requested.flag: 起動スクリプト（run_execution/run_monitoring）がこのファイルの存在を見て終了します
- KillSwitch はリスク条件（ドローダウン、ポジション上限など）でファイルを書き込みます。起動時に KILL_FLAG_CLEAR_ON_START=1 を設定すると自動で消去しますが、本番では 0 を推奨します。

開発・運用ヒント
----------------
- .env は OS の環境変数よりも低優先で読み込まれます（.env.local は自動上書きされる）。自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。
- config/*.yaml は存在が推奨され、validate_config で内容検証できます（PyYAML 必須）。
- ロギングは kabusys.utils.logging_setup.setup_logging を各起動スクリプトで呼び出して統一管理しています。ログディレクトリが作れない場合はコンソール出力のみにフォールバックします。
- psutil によるプロセス優先度設定はプラットフォーム依存で、権限不足の場合は警告ログを出してスキップされます。

ディレクトリ構成（抜粋）
---------------------
以下はコードベースの主要ファイル・ディレクトリ（src/kabusys 以下）の抜粋です。

- kabusys/
  - __init__.py
  - config.py                — 環境変数 / Settings
  - config_setup.py          — .env ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor 起動スクリプト
  - tools/
    - paper_verification_report.py
  - ai/
    - news_nlp.py
    - regime_detector.py
    - __init__.py
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - monitoring_engine.py
    - risk_monitor.py
    - kill_switch.py
    - (trade_monitor.py 等が存在する想定)
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
    - logging_setup.py
    - process_priority.py
    - __init__.py

（実際のレポジトリには execution/ や data/、config/ などの追加モジュール・ファイルがあります。）

最後に
------
- 本 README はコードベース（src/kabusys/*.py）を元に記載しています。プロダクション導入前に python -m kabusys.validate_config で設定を検証し、.env と DB の場所・バックアップ・権限を確認してください。
- AI 機能を運用する場合は API 利用コストとレートリミット、レスポンス検証に注意してください。

ご質問や README の追加補足（例: 各 CLI の詳細なオプション説明、ユニットテストの実行方法など）があれば教えてください。