README
=====

概要
----
KabuSys は日本株向けの自動売買 / 研究用ツール群です。本コードベースは以下の主要機能を含みます。

- 発注・Execution エンジン（本番 / ペーパートレード切替）
- 監視（System / Trade / Risk）のポーリングとアラート・Kill Switch
- ポートフォリオ構築（候補選定・重み付け・ポジションサイズ計算・リスク調整）
- 研究用ファクター計算・特徴量探索（DuckDB を利用）
- ニュースを使った LLM ベースの NLP スコアリング・市場レジーム判定（OpenAI）
- ユーティリティ（.env ウィザード・設定検証・プロセス優先度設定 等）
- ペーパートレード検証用レポート生成ツール

重要な設計方針（抜粋）
- 環境設定は .env を利用。自動読み込みと対話ウィザードを提供。
- Paper Trading は本番 DB と分離（data/paper_trading.db）。
- LLM 呼び出しは失敗しても致命化しないようフェイルセーフ設計。
- DuckDB を使った研究処理は外部 API に依存せず、データのみ参照する。

主な機能一覧
--------------
- config_setup.py: .env の対話式生成ウィザード
- validate_config.py: 起動前に環境変数・config/*.yaml を検証する CLI
- run_execution.py: ExecutionEngine 起動スクリプト（KABUSYS_ENV により挙動切替）
- run_monitoring.py: SystemMonitor のポーリングループ起動スクリプト
- monitoring/*: system/trade/risk モニタ、監視 DB 永続化、Kill Switch、MonitoringEngine
- portfolio/*: 候補選定・重み付け・リスク調整・株数決定（純粋関数）
- research/*: ファクター計算（momentum/value/volatility）、IC 計算、統計サマリ
- ai/*: news_nlp（ニュースセンチメント→ai_scores）、regime_detector（市場レジーム判定）
- tools/paper_verification_report.py: ペーパートレード検証レポート出力
- utils/process_priority.py: プロセス優先度 / CPU affinity のユーティリティ

前提（推奨環境）
----------------
- Python 3.10+（型ヒントに | を用いているため 3.10 以上を推奨）
- SQLite は標準ライブラリに同梱
- 必要パッケージ（機能により異なる）:
  - duckdb
  - psutil
  - openai（AI 機能を使う場合）
  - PyYAML（validate_config で config/*.yaml を検証する場合）
例:
  pip install duckdb psutil openai PyYAML

セットアップ手順
----------------
1. リポジトリをクローン / 展開
2. Python 仮想環境を作成・有効化（推奨）
   python -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate
3. 依存パッケージをインストール
   pip install duckdb psutil openai PyYAML
   （AI や YAML 検証を使わない場合は一部不要）
4. .env を作成
   - 対話式で作る（推奨）:
     python -m kabusys.config_setup
   - またはサンプル .env を手動で作成し、必須値を設定:
     - JQUANTS_REFRESH_TOKEN （必須）
     - KABU_API_PASSWORD （必須）
     - OPENAI_API_KEY （AI 機能を使う場合）
     - その他: KABUSYS_ENV, DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH, LOG_LEVEL など
   補足:
   - 自動ロードを無効化する: KABUSYS_DISABLE_AUTO_ENV_LOAD=1
   - .env は決してバージョン管理にコミットしないこと
5. 設定検証（任意）
   python -m kabusys.validate_config
   --strict を付けると警告も失敗扱い（exit code 1）

主要な環境変数（抜粋）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（AI 機能で必須）
- KABUSYS_ENV: execution 動作モード（development / paper_trading / live）
  - paper_trading: MockBrokerClient を使い data/paper_trading.db を使用
  - live: 本番（実際に発注）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 SQLite（デフォルト data/paper_trading.db）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）
- PAPER_FILL_MODE: paper_trading 時の約定モード (instant|partial|never|reject)

使い方（実行例）
----------------
- ExecutionEngine を起動（通常）
  python -m kabusys.run_execution
  動作:
    - KABUSYS_ENV により本番/ペーパー切替
    - paper_trading の場合は MockBrokerClient を使い paper DB に記録
    - data/stop_requested.flag があれば起動せず終了
    - 実行中は data/execution.pid に PID を書く（PID ファイルは実装側で管理）
    - 停止するには data/stop_requested.flag を作成するかプロセスを終了

- Monitoring を起動（常駐ポーリング）
  python -m kabusys.run_monitoring
  動作:
    - Settings から sqlite_path（監視 DB）を開き monitoring テーブルを初期化
    - SystemMonitor.check_once を定期実行（MONITOR_POLL_INTERVAL 秒）
    - data/stop_requested.flag を検出するとループ終了

- 設定ウィザード
  python -m kabusys.config_setup

- 設定検証
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict

- ペーパートレード検証レポート
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  オプション --db で DB パスを直接指定可能（環境変数 PAPER_TRADING_SQLITE_PATH が優先されます）

フラグ / 停止制御
-----------------
- data/stop_requested.flag: run_monitoring / run_execution のループ停止チェックに使用
- data/kill.flag: KillSwitch が書き込むと ExecutionEngine に停止要求を送る（Execution 側は kill_flag_path を監視）
- KILL_FLAG_CLEAR_ON_START=1 を設定すると Execution 起動時に kill.flag を自動クリア（本番では 0 推奨）

コード内の注意点 / 補足
-----------------------
- Settings クラスは .env（および .env.local）と OS 環境変数から設定を読み込みます。
  - 自動ロードはプロジェクトルート（.git または pyproject.toml）から行います。
- run_execution.py は paper_trading モード時に paper 用 DB を使用し、本番 DB と完全に分離します。
- AI 機能（ai/news_nlp.py, ai/regime_detector.py）は OpenAI API を用います。API キー未設定時は例外を投げますが、LLM 呼び出しの多くは内部でリトライやフォールバック（スコア=0 等）を行う設計です。
- monitoring/monitoring_db.py は既存 DB のマイグレーション（カラム追加）を起動時に自動で実行します（冪等処理）。
- utils/process_priority.set_process_priority はプラットフォーム差分を吸収しますが、権限不足時は警告を出してスキップします。

ディレクトリ構成（主要ファイル）
-------------------------------
（src/kabusys 以下の主要モジュールを抜粋）

- kabusys/
  - __init__.py
  - config.py                  # 環境変数/設定読み込み
  - config_setup.py            # .env ウィザード
  - validate_config.py         # 設定検証 CLI
  - run_execution.py           # ExecutionEngine 起動スクリプト
  - run_monitoring.py          # SystemMonitor 起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py         # （アラート送信管理）
  - execution/                  # 実行系（発注/Order 管理等）
    - broker_factory.py
    - execution_engine.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
    - order_record.py
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
  - utils/
    - process_priority.py
    - __init__.py
  - data/                       # 実行時に使うデータファイル（例: monitoring.db, kabusys.duckdb, paper_trading.db）
  - config/                     # YAML 設定ファイル群（system_config.yaml 等）

よくある運用フロー（例）
-----------------------
1. 初期設定
   - python -m kabusys.config_setup
   - python -m kabusys.validate_config

2. データ準備（DuckDB に価格・財務データをロード）

3. ペーパートレードでの検証
   - KABUSYS_ENV=paper_trading を設定
   - python -m kabusys.run_execution
   - 取引ログは data/paper_trading.db に保存される
   - 結果の検証: python -m kabusys.tools.paper_verification_report --from ... --to ...

4. 監視体制
   - python -m kabusys.run_monitoring を常時稼働させ、system/trade/risk の監視・Kill Switch を運用

ライセンス / 注意
-----------------
- .env は機密情報を含むため、Git 等のバージョン管理へは絶対に含めないでください。
- 本システムで実際の発注を行う場合は設定（KABUSYS_ENV, API キー等）の取り扱いに十分注意してください。
- live モードでは実際に発注が行われます。事前に validate_config の警告を確認してください。

お問い合わせ / 開発者メモ
-------------------------
- コード内の docstring やログメッセージに実装方針・注意点が多数記載されています。実装変更や運用ルールを決める際は該当箇所のコメントを参照してください。
- tests や CI 設定はこの README に含まれていません。ユニットテストを追加する場合は AI 呼び出し部分（外部 API）はモック化して下さい（モジュール内にモック用のパッチポイントを想定しています）。

以上。必要であれば README の英語版や、各モジュールの API リファレンス（関数シグネチャ・戻り値詳細）版も作成します。どの形式がよいか教えてください。