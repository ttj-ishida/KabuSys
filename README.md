KabuSys — 日本株自動売買システム
================================

本ドキュメントはこのリポジトリ（src/kabusys 以下）の概要、セットアップ、使い方、ディレクトリ構成をまとめた README です。
コード内のドキュメント文字列・コメントを基に記載しています。

プロジェクト概要
---------------
KabuSys は日本株の自動売買・研究・監視を行うためのモジュール群です。主な責務は以下の通りです。

- 発注エンジン（ExecutionEngine）：ブローカークライアントを介した注文管理と発注制御。paper_trading 環境では MockBroker を利用し本番 DB と分離。
- 監視（Monitoring）：システム状態・注文ログ・リスク（ドローダウン等）を定期的にチェックし、Kill Switch（停止フラグ）やアラート発行を行う。
- ポートフォリオ構築（Portfolio）：銘柄選定、重み計算、ポジションサイズ決定、セクター制限・レジームによる調整。
- リサーチ（Research）：DuckDB の価格・財務データを使ったファクター計算、フォワードリターン、IC 計算など。
- AI（news_nlp / regime_detector）：OpenAI（gpt-4o-mini 等）を利用したニュースセンチメント評価や市場レジーム判定。
- ユーティリティ：設定読み込み、ログ設定、プロセス優先度設定など。

主な特徴
---------
- 環境切替（development / paper_trading / live）をサポート。paper_trading は本番 DB と分離して記録。
- .env ベースの設定管理（自動ロード機能あり）と対話式ウィザードでの .env 生成支援。
- DuckDB（分析用）・SQLite（監視・発注履歴）を併用。
- OpenAI 連携モジュールはフェイルセーフ（API 失敗時はスコアをスキップ／デフォルト化）。
- ログはコンソール + 日次ローテーションファイル出力（logs/*.log）。

必要要件
--------
- Python 3.9+（ソースは typing と新しい構文を使用）
- Python パッケージ（例）
  - duckdb
  - psutil
  - openai
  - PyYAML（config 検証時に任意であるが推奨）
- SQLite（標準ライブラリに含まれます）
- システム上で外部プロセス優先度設定が必要な場合は管理者権限が必要になることがあります。

セットアップ手順
----------------

1. リポジトリをクローン（例）
   - git clone <this-repo>

2. 仮想環境を作成・有効化（任意だが推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - pip install duckdb psutil openai
   - 開発・検証用に PyYAML を使うなら: pip install PyYAML

   （requirements.txt がある場合はそれを使用してください）

4. .env を作成
   - 対話式ウィザード:
     - python -m kabusys.config_setup
   - 必須環境変数（代表例）:
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
     - OPENAI_API_KEY（AI 機能を使う場合）
   - .env の自動読み込み:
     - デフォルトでプロジェクトルートの .env / .env.local を自動ロードします。
     - 自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

5. 設定の検証（推奨）
   - python -m kabusys.validate_config
   - --strict を付けると警告もエラー扱い（exit(1)）になります。

6. 必要ディレクトリの準備
   - data/ （SQLite ファイルや PID、フラグファイルを格納）
   - logs/ （ログファイル）
   上記は起動時に自動生成されることが多いですが、権限等で作成できない場合は手動で作成してください。

基本的な使い方
--------------

- 実行エンジン（ExecutionEngine）を起動する:
  - python -m kabusys.run_execution
  - 挙動:
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し paper_sqlite_path（デフォルト data/paper_trading.db）に記録。
    - 起動時に execution.pid を作成し、data/stop_requested.flag が存在すれば起動をスキップ。
    - 停止は data/stop_requested.flag を作成することでスレッドを安全に停止できます。

- 監視（Monitoring）を起動する:
  - python -m kabusys.run_monitoring
  - 主な挙動:
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書き（デフォルト: 60 秒）。
    - SystemMonitor は KABUSYS_ENV に関係なく本番 sqlite_path を使用して監視ログを記録します。
    - 停止は data/stop_requested.flag を作成することで行います。

- .env 設定ウィザード:
  - python -m kabusys.config_setup

- 設定検証:
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- Paper Trading 検証レポート生成:
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - デフォルトの DB: 環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db

- AI 機能（ニューススコア / レジーム判定）
  - プログラム的に呼ぶ API:
    - kabusys.ai.score_news(conn, target_date, api_key=None)
    - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - OPENAI_API_KEY を環境変数に設定するか、関数引数で渡してください。
  - API 呼び出しはリトライ・フォールバックを備えており、失敗時でもシステムは稼働継続を優先します。

監視・停止フラグの仕組み
------------------------
- 停止リクエスト:
  - data/stop_requested.flag を作成すると run_execution/run_monitoring のループが終了します（起動スクリプトがチェック）。
- Kill Switch（自動停止）:
  - RiskMonitor 等が条件を満たすと KILL_FLAG（Settings.kill_flag_path; デフォルト data/kill.flag）を書き込み、ExecutionEngine に停止させる仕組みがあります。
  - KillSwitch クラスは既存フラグがある場合は再書き込みを行いません（冪等）。

ログ
---
- ログは kabusys.utils.logging_setup.setup_logging を通して統一設定されます。
- 出力:
  - コンソール（stdout）
  - 日次ローテーションファイル: logs/<app_name>.log（デフォルト 30 日保持）
- ログレベルは環境変数 LOG_LEVEL または引数で指定可能。

ディレクトリ構成（主要ファイル）
------------------------------
以下は src/kabusys 配下の主要モジュールと簡単な説明です。

- kabusys/
  - __init__.py : パッケージ定義（__version__ 等）
  - config.py : 環境変数 / 設定読み込みロジック、Settings クラス
  - config_setup.py : .env 対話式ウィザード
  - validate_config.py : 起動前設定検証 CLI
  - run_execution.py : ExecutionEngine 起動スクリプト
  - run_monitoring.py : SystemMonitor ポーリングループ起動スクリプト

- kabusys/execution/
  - execution_engine.py, order_manager.py, order_repository.py, reconciler.py, risk_manager.py, broker_factory.py
    - 発注・注文管理・リスク管理の実装（本体は該当ファイルを参照）

- kabusys/monitoring/
  - monitoring_db.py : SQLite による監視ログ永続化
  - system_monitor.py : CPU/MEM/DISK/データ鮮度/Execution プロセス監視
  - trade_monitor.py : 発注ログの整合性チェック（スタック）
  - risk_monitor.py : ドローダウン・ポジション上限監視
  - kill_switch.py : kill.flag 書き込みロジック
  - monitoring_engine.py : 各 Monitor を束ねるエンジン
  - alert_manager.py : （アラート送信用の抽象化レイヤ、LINE 等）

- kabusys/portfolio/
  - portfolio_builder.py : 候補選定・重み計算（等金額・スコア重み）
  - position_sizing.py : 発注株数計算・単元丸め・キャップ処理
  - risk_adjustment.py : セクターキャップ・レジーム乗数

- kabusys/research/
  - factor_research.py : momentum / volatility / value 等のファクター計算（DuckDB を使用）
  - feature_exploration.py : 将来リターン計算・IC 計算・統計サマリ

- kabusys/ai/
  - news_nlp.py : ニュース記事の LLM を使った銘柄別センチメントスコア化
  - regime_detector.py : ETF（1321）MA と LLM マクロセンチメントを合成したレジーム判定

- kabusys/utils/
  - logging_setup.py : ログ初期化ユーティリティ
  - process_priority.py : プロセス優先度 / CPU affinity 設定
  - 他ユーティリティ群

- kabusys/tools/
  - paper_verification_report.py : ペーパートレードの検証レポート生成スクリプト

データ / ログの出力先（デフォルト）
-----------------------------------
- DuckDB: data/kabusys.duckdb (環境変数 DUCKDB_PATH)
- SQLite (監視): data/monitoring.db (環境変数 SQLITE_PATH)
- SQLite (paper_trading): data/paper_trading.db (PAPER_TRADING_SQLITE_PATH)
- PID / フラグ: data/execution.pid, data/stop_requested.flag, data/kill.flag
- ログ: logs/<app_name>.log

よくある操作例
--------------
- .env を作る（ウィザード）:
  - python -m kabusys.config_setup

- 設定チェック:
  - python -m kabusys.validate_config

- Paper Trading レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

- 実行エンジン起動（デーモンや Supervisor / systemd で管理する想定）:
  - python -m kabusys.run_execution

- 監視エンジン起動:
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

トラブルシューティング / 注意点
------------------------------
- ファイル作成権限:
  - data/ や logs/ に書き込み権限が必要です。権限不足だと起動時にファイル作成に失敗することがあります。
- OpenAI API:
  - API キーは OPENAI_API_KEY 環境変数に設定してください。API 呼び出しには料金が発生します。
- 本番環境（KABUSYS_ENV=live）:
  - 本番では KILL_FLAG_CLEAR_ON_START=0 を推奨します（自動で Kill Flag をクリアしない）。
  - LINE の通知設定（LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID）は本番アラートに重要です。
- DB マイグレーション:
  - monitoring_db.init_monitoring_db は冪等であり、必要に応じてスキーマ追加（ALTER TABLE）処理も行いますが、重要な変更は事前にバックアップを取ってください。

ライセンス / 署名
----------------
本リポジトリのライセンス情報はリポジトリルートの LICENSE を参照してください（本 README にライセンス条項は含めていません）。

最後に
-----
この README はコードのドキュメント文字列およびコメントに基づいて作成しています。実運用する際は必ず .env を正しく設定し、validate_config で検証した上でサービスを起動してください。必要に応じて systemd / Docker / Supervisor 等でプロセス管理を行うことを推奨します。