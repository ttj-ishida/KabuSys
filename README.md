README
=====

概要
----
KabuSys は日本株向けの自動売買基盤（リサーチ、ポートフォリオ構築、発注・リスク管理、監視、AI支援分析）を想定した Python パッケージです。本リポジトリには以下の主要コンポーネントが含まれます。

- ExecutionEngine（発注エンジン）: 本番 / ペーパートレードを切り替え可能
- Monitoring（システム監視）: CPU/メモリ/ディスク・データ鮮度・注文状態・リスクを監視、必要時に Kill Switch を発動
- Research: DuckDB を使ったファクター計算・特徴量解析
- Portfolio: 銘柄選定、重み算出、ポジションサイジング、セクター調整
- AI モジュール: OpenAI を使ったニュースセンチメント / 市場レジーム判定
- 各種ツール: ペーパートレード検証レポート等

機能一覧
--------
- 環境設定ウィザード（.env 生成 / 更新）: kabusys.config_setup
- 設定検証 CLI: kabusys.validate_config（必須環境変数や config/*.yaml の簡易チェック）
- 発注エンジン起動スクリプト: python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading 時は MockBrokerClient を使用し、paper DB に完全分離して記録
- 監視ループ起動スクリプト: python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL でポーリング間隔を変更可能（デフォルト 60 秒）
- 監視 DB 永続化（SQLite）: system_status / trade_logs / positions / risk_logs / dashboard
- RiskMonitor / KillSwitch による自動停止トリガー（kill.flag 書き込み）
- DuckDB を用いたリサーチ関数（ファクター計算・forward returns・IC 等）
- OpenAI を使ったニュース NLP（銘柄別センチメント）とレジーム判定（gpt-4o-mini 想定）
- ペーパートレード検証レポート生成スクリプト:
  - python -m kabusys.tools.paper_verification_report --from YYYY-MM-DD --to YYYY-MM-DD

前提（依存ライブラリ）
--------------------
本コードで参照している主なライブラリ（環境に応じてインストールしてください）:
- Python 3.9+
- duckdb
- psutil
- openai
- PyYAML（config YAML の検証を行う場合）
（プロジェクトには requirements.txt / pyproject.toml が存在する想定で、そこからインストールしてください。）

セットアップ手順
---------------
1. リポジトリをクローンして作業ディレクトリへ移動
   - git clone ... && cd <repo>

2. 仮想環境を作成して有効化（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Linux/macOS)
   - .venv\Scripts\activate     (Windows)

3. 依存パッケージをインストール
   - pip install -U pip
   - pip install duckdb psutil openai PyYAML
   - （プロジェクト固有の依存がある場合は requirements.txt / pyproject.toml からインストール）

4. 環境変数設定
   - 対話式ウィザードで .env を作成する:
     - python -m kabusys.config_setup
   - もしくは手動で .env を作成。最低限必須なのは:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - 推奨: .env を作成したら設定検証を実行:
     - python -m kabusys.validate_config
     - strict モード: python -m kabusys.validate_config --strict

主要な環境変数（抜粋）
---------------------
- 必須
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD

- 実行モード
  - KABUSYS_ENV: development | paper_trading | live  (default: development)

- データベース / ファイルパス
  - DUCKDB_PATH: data/kabusys.duckdb (default)
  - SQLITE_PATH: data/monitoring.db (default)
  - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db (paper_trading 用 DB)
  - PID_FILE_PATH: data/execution.pid (ExecutionEngine の PID ファイル)
  - KILL_FLAG_PATH: data/kill.flag (Kill Switch 用)

- ログ
  - LOG_LEVEL: DEBUG|INFO|WARNING|ERROR|CRITICAL (default: INFO)
  - LOG_DIR: ログ出力ディレクトリ（default: logs/）

- Monitoring / Execution
  - MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、default: 60）
  - KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動削除する場合は "1"（開発のみ推奨）
  - PAPER_FILL_MODE: ペーパートレードの約定モード ("instant" | "partial" | "never" | "reject")

- OpenAI
  - OPENAI_API_KEY: OpenAI API キー（ai モジュール利用時に必要）

使い方（起動・ツール）
--------------------

1) 環境設定ウィザード
   - python -m kabusys.config_setup
   - 対話式に .env を生成・更新します。

2) 設定検証
   - python -m kabusys.validate_config
   - --strict を付けると警告もエラー扱いになります。

3) 監視ループ起動
   - python -m kabusys.run_monitoring
   - MONITOR_POLL_INTERVAL で間隔を制御（秒）
   - 監視は常に本番 sqlite (Settings.sqlite_path) を参照します（環境に関係なく）。

4) 発注エンジン起動
   - python -m kabusys.run_execution
   - KABUSYS_ENV=paper_trading の場合、MockBrokerClient が使われ、PAPER_TRADING_SQLITE_PATH に記録されます。
   - 起動時に data/stop_requested.flag が存在すると起動せず終了します。
   - 実行中は data/execution.pid に PID を保存します（設定による）。

5) Kill Switch / 停止
   - KillSwitch はリスク監視で条件が満たされると KILL_FLAG_PATH（デフォルト data/kill.flag）を書き込みます。
   - 監視ループや ExecutionEngine の外部停止フラグは data/stop_requested.flag（起動スクリプトで参照）を作成することでループを終了させられます。

6) Paper Trading 検証レポート
   - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
   - デフォルト DB: data/paper_trading.db。--db でパスを指定可能。

7) AI スコアリング（ライブラリ利用）
   - kabusys.ai.score_news を呼び出して、指定日のニュースセンチメントを ai_scores テーブルへ書き込みます。
     - score_news(conn, target_date, api_key=None)
   - kabusys.ai.regime_detector.score_regime を呼び出して、市場レジームを計算・永続化します。
     - score_regime(conn, target_date, api_key=None)
   - 両関数とも OPENAI_API_KEY または引数 api_key の指定が必要です。

停止・強制停止
--------------
- 正常停止（監視/実行ループ）:
  - Ctrl+C（KeyboardInterrupt）で各ループは安全に停止します。
- 外部から停止指示:
  - data/stop_requested.flag を作成すると run_monitoring / run_execution のループが終了します。
- Kill Switch 発動:
  - KillSwitch が条件を満たすと data/kill.flag を作成し、ExecutionEngine に停止を促します。

設定・挙動の注意点
-----------------
- .env の自動ロード: パッケージの config モジュールはプロジェクトルート（.git または pyproject.toml）を探索し .env/.env.local を自動読み込みします。テストなどで自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。
- PAPER_TRADING は本番 DB と完全分離（paper_sqlite_path を使用）。
- MONITORING は環境に関係なく本番 sqlite_path を参照します（監視は本番対象で実行する想定）。
- OpenAI API の呼び出しはリトライ・バックオフを内蔵していますが、APIキーは安全に管理してください。
- LOG_DIR の作成に失敗した場合はコンソール出力のみで継続します。

ディレクトリ構成（抜粋）
----------------------
src/kabusys/
- __init__.py
  - パッケージ定義・バージョン

- config.py
  - 環境変数/設定の読み込み・検証（Settings クラス）

- config_setup.py
  - .env を対話式に生成するウィザード

- validate_config.py
  - 起動前の設定検証 CLI

- run_execution.py
  - ExecutionEngine 起動スクリプト

- run_monitoring.py
  - SystemMonitor ポーリングループ起動スクリプト

- utils/
  - logging_setup.py: ログ設定ユーティリティ（stdout + 日次ローテートファイル）
  - process_priority.py: プロセス優先度 / CPU affinity 設定ユーティリティ

- monitoring/
  - monitoring_db.py: SQLite による永続化層（schema 初期化、読み書き）
  - system_monitor.py: CPU/メモリ/ディスク・データ鮮度・実行プロセス監視
  - trade_monitor.py: （コード参照部分）発注ログ監視（滞留注文・約定異常など）
  - risk_monitor.py: ドローダウン・ポジション数を監視してリスクイベント記録
  - kill_switch.py: kill.flag 書込ロジック
  - monitoring_engine.py: 各モニタを束ねるエンジン

- execution/
  - execution_engine.py, order_manager.py, order_repository.py, risk_manager.py, reconciler.py, broker_factory.py
  - 発注エンジン / 注文管理 / リスク管理 など（run_execution から組み立てて利用）

- portfolio/
  - portfolio_builder.py: 候補選定・重み計算
  - position_sizing.py: 株数決定・スケーリング・単元丸め
  - risk_adjustment.py: セクターキャップ・レジーム乗数

- research/
  - factor_research.py: Momentum / Value / Volatility ファクター計算（DuckDB）
  - feature_exploration.py: 将来リターン計算・IC・統計サマリ

- ai/
  - news_nlp.py: ニュースセンチメント（OpenAI）→ ai_scores 書込
  - regime_detector.py: マクロセンチメント + ETF MA200 でレジーム判定

- tools/
  - paper_verification_report.py: ペーパートレードの検証レポート生成

付録: よく使うコマンド例
---------------------
- .env を作る（対話式）
  - python -m kabusys.config_setup

- 設定を検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- 監視ループをデバッグ実行（短い間隔）
  - MONITOR_POLL_INTERVAL=5 python -m kabusys.run_monitoring

- 発注エンジン（ペーパー）を起動
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution

- ペーパートレード検証レポート生成
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

- AI スコア付け（ライブラリ呼び出し例、DuckDB 接続を渡す）
  - from kabusys.ai.news_nlp import score_news
    score_news(duckdb_conn, date(2026,4,1), api_key="sk-...")

最後に
-----
本 README はコードベースの自動生成ドキュメントではなく、ソースコードから抽出した情報に基づく概要です。詳細な実装や追加の CLI、設定ファイルはリポジトリ内の各モジュール・スクリプトを参照してください。必要なら README を英語版にする、あるいは具体的な運用手順（systemd / supervisor 用の unit ファイル、Docker 化手順等）を追加で作成できます。必要に応じて指示してください。