README
======

概要
----
KabuSys は日本株の自動売買システム（研究・ポートフォリオ構築・発注・監視・AI 補助機能を含む）を想定した Python パッケージです。本リポジトリは以下の主要機能を含みます。

- 戦略研究（ファクター計算、特徴量解析、IC 計算）
- ポートフォリオ構築（候補選定、重み計算、ポジションサイズ算出）
- 発注実行エンジン（paper_trading / live の切替サポート）
- 監視（プロセス・資産・注文・リスク監視と Kill Switch）
- AI 補助（ニュースの NLP スコアリング、レジーム判定）
- 運用ユーティリティ（設定ウィザード、設定検証、ペーパートレード検証レポート）

重要な設計方針として、ルックアヘッドバイアスを避けるために日付参照を明示的に受け渡す実装や、本番 DB と paper_trading DB を分離する仕組みが盛り込まれています。

機能一覧
--------
主な機能と対応モジュールの一覧：

- 設定管理
  - kabusys.config, config_setup.py（.env ウィザード）、validate_config.py（設定検証）
- 実行エンジン
  - run_execution.py（ExecutionEngine を起動）
  - paper_trading モードでは MockBrokerClient を利用し paper_trading DB に記録
- 監視
  - run_monitoring.py（SystemMonitor ポーリング）
  - monitoring モジュール（system_monitor, trade_monitor, risk_monitor, monitoring_engine, kill_switch, monitoring_db）
- ポートフォリオ構築・リスク調整
  - kabusys.portfolio（select_candidates, calc_equal_weights, calc_score_weights, calc_position_sizes, apply_sector_cap, calc_regime_multiplier）
- 研究 / リサーチ
  - kabusys.research（factor_research, feature_exploration）
  - DuckDB を使ったファクター・リターン計算
- AI（OpenAI 経由）
  - kabusys.ai.news_nlp（ニュースのセンチメントスコア）
  - kabusys.ai.regime_detector（市場レジーム判定）
- ユーティリティ
  - tools.paper_verification_report（ペーパートレード検証レポート生成）
  - utils.logging_setup（ログ設定）、utils.process_priority（プロセス優先度設定）

要件（依存ライブラリ）
--------------------
最低限の依存例（実行する機能により必要なパッケージが追加されます）:

- Python 3.9+
- duckdb
- psutil
- openai (AI 機能を使う場合)
- PyYAML（validate_config で YAML 検証を行う場合、任意）

セットアップ手順
--------------
1. リポジトリをクローンして作業ディレクトリに移動します。

2. 仮想環境を作成して有効化（推奨）：
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール：
   - pip install duckdb psutil openai
   - validate_config の YAML 検証を使う場合: pip install PyYAML

4. .env を作成：
   - 対話式ウィザードを使う（推奨）:
     - python -m kabusys.config_setup
   - または .env.example を参考に手動で .env を作成してください。
   - 自動ロード: kabusys.config はプロジェクトルートに .env/.env.local があれば起動時に自動読み込みします（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。

主な環境変数（要設定）
- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABUSYS_ENV（development / paper_trading / live、デフォルト: development）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト: data/paper_trading.db）
- OPENAI_API_KEY（AI 機能を利用する場合）
- LOG_LEVEL（DEBUG/INFO/…）

重要な運用フラグ
- KILL_FLAG_CLEAR_ON_START=1 にすると ExecutionEngine 起動時に kill.flag を自動クリア（本番では 0 推奨）
- MONITOR_POLL_INTERVAL（run_monitoring のポーリング間隔秒、デフォルト 60。環境変数で上書き可）
- PAPER_FILL_MODE（paper_trading の約定挙動: instant / partial / never / reject）

使い方（主要コマンド）
--------------------

1) 設定検証
- python -m kabusys.validate_config
  - --strict を付けると警告も FAIL 扱いで exit(1)

2) 設定ウィザード（.env 作成）
- python -m kabusys.config_setup

3) 実行エンジン（ExecutionEngine）起動
- python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は専用の paper_trading DB（PAPER_TRADING_SQLITE_PATH）に記録され、本番 DB と完全に分離されます。
  - 起動時に data/stop_requested.flag が存在すると起動を中止します。
  - 実行中は data/execution.pid に PID が作成されます（設定により変更可）。

4) 監視ループ起動
- python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒で上書き（例: MONITOR_POLL_INTERVAL=30）。
  - 監視は Settings.sqlite_path を使用して monitoring DB に書き込みます（環境に依らず本番 sqlite_path を使用する旨に注意）。
  - 停止は data/stop_requested.flag を作ることで行えます（run_execution と run_monitoring は stop フラグをチェックします）。

5) Paper Trading 検証レポート生成
- python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - デフォルト DB: 環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db

6) AI 機能（ニュース NLP / レジーム判定）
- kabusys.ai.score_news(conn, target_date, api_key=None)
  - DuckDB 接続を渡して実行。OPENAI_API_KEY が必要（api_key でも指定可）。
- kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - 同様に DuckDB 接続と API キーが必要。
- これらは直接モジュールをインポートして呼ぶ形です（CLI 起点のラッパーは実装されていません）。

稼働監視・Kill Switch
--------------------
- RiskMonitor / KillSwitch によりドローダウンやポジション過多を検出し data/kill.flag を書き込むと ExecutionEngine に停止シグナルを送れます。
- KillSwitch は冪等にファイルを書き（既存の場合は上書きしない）、ExecutionEngine 側は起動時やループ中にこのファイルをチェックしてシャットダウンします。
- Kill Switch のクリアは KillSwitch.clear() または KILL_FLAG を手動削除で可能。設定 KILL_FLAG_CLEAR_ON_START に注意してください（本番は自動クリアしないことが推奨）。

ログ
----
- ロギングは kabusys.utils.logging_setup.setup_logging によって統一管理されます。
- デフォルトは logs/<app_name>.log に日次ローテーションで保存、30 日分保持。
- コンソール出力は stdout に送られます。
- LOG_DIR 環境変数でログディレクトリを上書きできます。

開発・デバッグ
--------------
- 設定検証: python -m kabusys.validate_config で起動前チェックを推奨。
- .env は決して Git にコミットしないでください（config_setup にも注意書きあり）。
- unit テストや CI では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自動読み込みを抑止できます。
- run_monitoring の MONITOR_POLL_INTERVAL は 1 秒以上の整数にしてください（不正値はデフォルト 60 秒にフォールバック）。

ディレクトリ構成（抜粋）
------------------------
プロジェクトの主要ファイル/ディレクトリ（src/kabusys 以下）:

- src/kabusys/
  - __init__.py
  - config.py                  — 環境変数 / Settings 管理
  - config_setup.py            — .env 対話ウィザード（CLI）
  - validate_config.py         — 起動前設定検証（CLI）
  - run_execution.py           — ExecutionEngine 起動スクリプト（CLI）
  - run_monitoring.py          — SystemMonitor 起動スクリプト（CLI）
  - tools/
    - paper_verification_report.py
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
    - alert_manager.py (※コードベースにある場合)
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

ルートにある想定ディレクトリ/ファイル:
- .env, .env.local
- data/（実行時に生成される SQLite 等の DB、PID、フラグファイル）
  - data/monitoring.db (SQLITE_PATH デフォルト)
  - data/paper_trading.db (PAPER_TRADING_SQLITE_PATH デフォルト)
  - data/kabusys.duckdb (DUCKDB_PATH デフォルト)
  - data/execution.pid
  - data/kill.flag
  - data/stop_requested.flag
- logs/（ログ出力先）

補足・注意事項
--------------
- Monitoring は設計上、環境にかかわらず Settings.sqlite_path（本番向け monitoring DB）を使用して永続化します。一方、ExecutionEngine は KABUSYS_ENV=paper_trading 時に paper_trading 用 DB を使うため、本番データとペーパートレードは分離されます。
- OpenAI を用いる AI 機能は API 呼び出しの失敗耐性（リトライやフェイルセーフ）を備えていますが、API コストや利用制限にご注意ください。
- プロセス優先度の設定は psutil を通じ OS に依存した実装になっています。権限不足等で設定できない場合は警告ログが出ます。

問い合わせ / コントリビューション
---------------------------------
この README はコードベースの主要機能をまとめたもので、詳細は各モジュールの docstring を参照してください。Pull Request や Issue は歓迎します。

以上。