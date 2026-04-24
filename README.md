README — KabuSys
=================

概要
----
KabuSys は日本株の自動売買（バックテスト / ペーパートレード / 実運用）を支援するライブラリ／スクリプト群です。  
このリポジトリには、シグナル生成・ポートフォリオ構築・ポジションサイジング・注文実行（ExecutionEngine）・監視（Monitoring）・AI を使ったニュースセンチメントやレジーム判定、各種ユーティリティが含まれます。

主な特徴
--------
- ポートフォリオ生成（候補選定、重み計算、ポジションサイズ算出）
- リスク制御（ドローダウン監視、ポジション数上限、リスクログ出力）
- ExecutionEngine：ブローカークライアント経由で発注（paper_trading ではモックブローカー）
- Monitoring：システム状態 / 注文ログ / リスク監視のポーリングとアラート連携
- AI モジュール：OpenAI を用いたニュースセンチメント（news_nlp）・市場レジーム判定（regime_detector）
- 管理ツール：.env 対話式ウィザード（config_setup）、設定検証（validate_config）、検証レポート生成（paper_verification_report）
- ロギング設定とプロセス優先度制御ユーティリティ

必要条件 / 依存
---------------
- Python 3.9+
- 主要ライブラリ（例）
  - duckdb
  - psutil
  - openai（AI 機能を使う場合）
  - PyYAML（設定ファイル検証を行う場合）
- OS 標準の sqlite3
- 環境変数（最低限必要）
  - JQUANTS_REFRESH_TOKEN（必須）
  - KABU_API_PASSWORD（必須）

セットアップ
-----------
1. リポジトリをクローン、仮想環境を作成して依存をインストールしてください。
   例:
   - python -m venv .venv
   - source .venv/bin/activate
   - pip install -r requirements.txt
   （requirements.txt がない場合は duckdb / psutil / openai を必要に応じてインストール）

2. .env を作成
   - 対話式ウィザードを使う: python -m kabusys.config_setup
   - または .env.example を参考に .env を作成して環境変数を設定してください
   - 注意: .env は絶対に Git にコミットしないでください

3. 設定検証（起動前チェック）
   - python -m kabusys.validate_config
   - 問題があると ERROR/WARNING が表示されます。--strict をつけると WARNING も失敗扱いになります。

使い方
------

共通
- ログ:
  - ログはデフォルトで logs/ ディレクトリに日次ローテーションで出力されます（kabusys.utils.logging_setup）。
  - 環境変数 LOG_DIR で変更可能。

- プロセス優先度:
  - 起動スクリプトは起動時にプロセス優先度を "high" に設定しようとします（psutil を使用）。

実行コンポーネント

1. ExecutionEngine（注文エンジン）
   - 概要: ブローカークライアントを作り、注文管理・リスク管理・照合を行う。
   - 起動:
     - python -m kabusys.run_execution
   - 環境:
     - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、デフォルトで data/paper_trading.db を使用（本番 DB と分離）。
     - 本番/開発は KABUSYS_ENV（development / paper_trading / live）で切り替え。
   - 停止:
     - 実行中に data/stop_requested.flag が作成されるとエンジンは停止処理を行います（手動停止用）。
     - Kill Switch（監視コンポーネント）がトリガすると data/kill.flag が書かれ、ExecutionEngine 側で設定された kill_flag_path を介して停止する設計です（Settings.kill_flag_path）。

2. Monitoring（監視）
   - 概要: SystemMonitor / TradeMonitor / RiskMonitor をポーリングして監視ログを保存し、必要に応じて Kill Switch を起動、アラートを送信します。
   - 起動:
     - python -m kabusys.run_monitoring
   - 設定:
     - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）。
     - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path（Settings.sqlite_path）を使用して監視データを保存します（監視 DB は共有の想定）。
   - 停止:
     - data/stop_requested.flag を作成すると監視ループが終了します。

3. 検証・レポートツール
   - Paper Trading 検証レポート:
     - python -m kabusys.tools.paper_verification_report
     - --from / --to で期間指定可能（YYYY-MM-DD）。DB は --db で指定可能、なければ PAPER_TRADING_SQLITE_PATH 環境変数または data/paper_trading.db。
   - 設定ウィザード:
     - python -m kabusys.config_setup
   - 設定検証:
     - python -m kabusys.validate_config

環境変数一覧（主なもの）
-----------------------
- 必須
  - JQUANTS_REFRESH_TOKEN : J-Quants API 用リフレッシュトークン
  - KABU_API_PASSWORD     : kabuステーション API パスワード

- 環境切替 / ログ
  - KABUSYS_ENV           : development / paper_trading / live （デフォルト: development）
  - LOG_LEVEL             : ログレベル（DEBUG/INFO/…）
  - LOG_DIR               : ログ出力ディレクトリ（デフォルト logs/）

- データベース
  - DUCKDB_PATH           : DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
  - SQLITE_PATH           : 監視 DB（monitoring）パス（デフォルト data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH : ペーパートレード用 SQLite（デフォルト data/paper_trading.db）
  - PAPER_FILL_MODE       : paper_trading の約定挙動（instant / partial / never / reject）

- AI（OpenAI）
  - OPENAI_API_KEY        : OpenAI API キー（news_nlp / regime_detector で必要）

- 監視・制御
  - MONITOR_POLL_INTERVAL : 監視ポーリング間隔（秒）
  - PID_FILE_PATH         : ExecutionEngine の PID ファイルパス（デフォルト data/execution.pid）
  - KILL_FLAG_PATH        : kill.flag のパス（デフォルト data/kill.flag）
  - KILL_FLAG_CLEAR_ON_START : 起動時に kill.flag を自動クリアするか（1 = 有効、開発用）

注意点 / 実装メモ
----------------
- 監視 DB（SQLite）は init_monitoring_db() でテーブル作成・軽微なマイグレーション（列追加）を行います。既存 DB に対しても冪等で実行されます。
- Monitoring は常に Settings.sqlite_path を使うため、監視データは環境にかかわらず同じ DB に記録されます。一方、ExecutionEngine は paper_trading の場合 paper_sqlite_path を使用して本番 DB と分離します。
- KillSwitch: RiskMonitor の検知に応じて kill.flag を書き、ExecutionEngine 側で参照して安全停止を行います。kill.flag は Settings.kill_flag_path（デフォルト data/kill.flag）に作成されます。
- stop_requested.flag はプロジェクトルートの data/stop_requested.flag（run_monitoring/run_execution が参照）で、これを作成するとサービスを止められます（手動運用用）。

ディレクトリ構成（主なファイル）
------------------------------
以下はリポジトリ内の主要パッケージ／ファイルの抜粋です（src/kabusys 以下）。

- src/kabusys/
  - __init__.py
  - config.py                  — 環境変数 / Settings 管理
  - config_setup.py            — .env 対話式ウィザード
  - validate_config.py         — 設定検証 CLI
  - run_execution.py           — ExecutionEngine 起動スクリプト
  - run_monitoring.py          — Monitoring 起動スクリプト
  - tools/
    - paper_verification_report.py  — ペーパートレード検証レポート生成
  - utils/
    - logging_setup.py         — ロギング初期化ユーティリティ
    - process_priority.py      — プロセス優先度 / CPU affinity
  - portfolio/
    - portfolio_builder.py     — 候補選定・重み計算
    - position_sizing.py       — 発注株数計算
    - risk_adjustment.py       — セクター上限・レジーム乗数
  - monitoring/
    - monitoring_db.py         — 監視 DB レイヤ
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - monitoring_engine.py
    - kill_switch.py
    - alert_manager.py
  - execution/
    - execution_engine.py
    - broker_factory.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py
    - regime_detector.py

プロジェクトルート（想定）
- .env                        — 環境変数（機密）
- config/                     — yaml 設定テンプレート（system_config.yaml など）
- data/                       — データベース・フラグ・PID ファイル（data/monitoring.db 等）
  - stop_requested.flag
  - kill.flag
  - execution.pid
  - monitoring.db
  - paper_trading.db
- logs/                       — ログファイル出力先

よくある運用フロー（例）
-----------------------
1. .env を作成（python -m kabusys.config_setup）
2. 設定検証（python -m kabusys.validate_config）
3. DuckDB / SQLite の初期データを準備（データ投入は別スクリプト）
4. 監視を起動（本番環境では監視は常時起動）
   - python -m kabusys.run_monitoring
5. 実行エンジンを起動（KABUSYS_ENV を適切に設定）
   - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
   - KABUSYS_ENV=live python -m kabusys.run_execution
6. 異常発生時は監視が kill.flag を書いて Execution を停止、または手動で data/stop_requested.flag を配置して終了

サポート / 拡張
----------------
- AI 機能を使う場合は OpenAI の API キー（OPENAI_API_KEY）が必須です。
- Paper Trading の検証やレポート生成は tools/paper_verification_report.py を参照してください。
- 新しい監視ルールやアラートチャネルを追加する場合、monitoring パッケージの AlertManager を拡張します。

ライセンス / 注意
-----------------
- この README はコードベースの説明です。実運用する際は各種 API の利用規約や市場ルールを遵守してください。
- 本リポジトリは学習・研究・運用補助を目的としたものであり、実取引に使用する際は十分な検証とリスク管理を行ってください。

以上。必要であれば各スクリプトの具体的な実行例や .env のテンプレート（サンプル）を追加で出力できます。