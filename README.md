KabuSys
=======

日本株向け自動売買システムのサンプル実装（ライブラリ＋起動スクリプト群）。  
このリポジトリはトレード実行、監視、リサーチ、ポートフォリオ構築、AI を用いたニュース解析などの主要コンポーネントを含みます。

主な特徴
--------
- 実行エンジン（ExecutionEngine）と監視プロセス（Monitoring）を分離して運用可能
- Paper Trading（ペーパートレード）モードをサポート（本番 DB と分離）
- SQLite（監視 / ペーパーデータ）と DuckDB（分析用）を併用
- Kill Switch（ファイルベース）による緊急停止機能
- リスク監視（ドローダウン、ポジション数など）とアラート統合
- ファクター計算・特徴量探索（DuckDB 上で完結）
- ニュースの LLM（OpenAI）によるセンチメント評価・レジーム判定機能
- ログはコンソール出力＋日次ローテーションでファイルに保存

Requirements（前提）
------------------
- Python 3.9+
- 必須 / 推奨パッケージ（例）:
  - duckdb
  - psutil
  - openai
  - pyyaml（config 検証：任意だがインストールすると YAML の内容検査が有効）
- データディレクトリ（デフォルト: data/）およびログディレクトリ（デフォルト: logs/）への書き込み権限

簡単なセットアップ
-----------------
1. 仮想環境作成・有効化（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール（例）
   - pip install duckdb psutil openai pyyaml

   （プロジェクトに requirements.txt がある場合はそれを使用してください）

3. .env を作成（推奨）
   - インタラクティブウィザード:
     - python -m kabusys.config_setup
   - 生成後、内容を編集して API キーやパスなどを設定してください。

4. 設定検証（起動前に実行推奨）
   - python -m kabusys.validate_config
   - 警告を FAIL 扱いにするには --strict を付ける:
     - python -m kabusys.validate_config --strict

主要な環境変数（代表例）
-----------------------
- KABUSYS_ENV: 実行モード ("development" | "paper_trading" | "live") — デフォルト: development
  - paper_trading の場合、Execution は MockBrokerClient を使用し DB を data/paper_trading.db に分離
- JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD: 各種 API 用必須トークン／パスワード
- OPENAI_API_KEY: OpenAI 呼び出し（ニュース解析 / レジーム判定）に必要
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- DUCKDB_PATH: DuckDB ファイル（デフォルト: data/kabusys.duckdb）
- LOG_LEVEL: ログレベル（"INFO" など）
- LOG_DIR: ログ保存先（デフォルト: logs/）
- MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、デフォルト 60）
- KILL_FLAG_CLEAR_ON_START: 本番環境での kill.flag 自動クリアを抑止するためのフラグ（"0"/"1"）

主要な使い方
-------------

- 環境設定ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - strict モード: python -m kabusys.validate_config --strict

- 実行エンジン起動（ExecutionEngine）
  - python -m kabusys.run_execution
  - 注意:
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient が使われ、データは data/paper_trading.db に書き込まれます。
    - 起動時に data/stop_requested.flag が存在すると起動せず終了します。
    - 実行中は data/execution.pid に PID を書きます。

- 監視プロセス起動（SystemMonitor のポーリング）
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可（秒、デフォルト: 60）
  - 監視は本番の sqlite_path を使う（KABUSYS_ENV にかかわらず同じ監視 DB を参照）
  - 監視ループは data/stop_requested.flag の存在で終了します。

- ペーパートレード検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB パスは --db で上書き可能。環境変数 PAPER_TRADING_SQLITE_PATH も使用可。

- AI / LLM 機能
  - ニュースセンチメント（ai.score_news）やレジーム判定（ai.regime_detector.score_regime）は OpenAI API キーが必要
  - 直接スクリプトとして利用する場合は OPENAI_API_KEY を .env / 環境変数で設定してください

Kill Switch / 停止フロー
-----------------------
- Kill Switch は data/kill.flag を書き込むことで ExecutionEngine に停止シグナルを送る仕組みです（監視側が条件を検知して書き込む）。
- 手動停止のためのファイル（監視・実行ループの終了条件）:
  - data/stop_requested.flag — run_monitoring / run_execution のループ終了に使用
  - data/kill.flag — KillSwitch による自動停止指示（ExecutionEngine はこのファイルを検出して停止します）
- 実行時にこれらのファイルを直接作成・削除することで停止・再開を操作できます（運用ポリシーに従って使用してください）。

ディレクトリ構成（抜粋）
----------------------
プロジェクトの主要なファイル・パッケージ構成（src/kabusys 以下）:

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / .env 自動読み込みロジック
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 起動前検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリング起動スクリプト

  - ai/
    - news_nlp.py            — ニュースを LLM でスコアリングするロジック
    - regime_detector.py     — 市場レジーム判定（MA + マクロセンチメント）

  - monitoring/
    - monitoring_db.py       — SQLite 永続化層（system_status / trade_logs / positions / risk_logs / dashboard）
    - system_monitor.py      — システム状態・データ鮮度チェック
    - trade_monitor.py       — （trade 関連の監視）※コードベースに含まれるはずのモジュール
    - risk_monitor.py        — ドローダウン、ポジション上限監視
    - monitoring_engine.py   — 各モニタを束ねるエンジン
    - kill_switch.py         — kill.flag の管理

  - execution/
    - execution_engine.py    — 実行エンジン（EngineConfig / run_session 等）
    - broker_factory.py      — ブローカークライアントの生成（本番 / モック）
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

  - data/                    — スキーマ定義やデータパイプライン（prices_daily など）想定のモジュール群
  - tools/
    - paper_verification_report.py

  - utils/
    - logging_setup.py       — ログ設定ユーティリティ（コンソール＋日次ファイルローテーション）
    - process_priority.py    — プロセス優先度 / CPU affinity 設定ユーティリティ

運用上の注意・トラブルシューティング
--------------------------------
- OpenAI を使用する機能を実行するには OPENAI_API_KEY が必須です。未設定時は ValueError が投げられます。
- validate_config は PyYAML がないと config/*.yaml の内容検証をスキップします（警告）。
- run_monitoring は監視用 DB と DuckDB を開いてログを残します。監視は常に sqlite_path（本番）を使用する点に注意してください。
- run_execution は KABUSYS_ENV が paper_trading の場合、paper_sqlite_path を使用して本番 DB と分離します。
- ログディレクトリ作成に失敗するとファイル出力は無効になり、コンソール出力のみになります（ログ出力先の権限を確認してください）。
- プロセス優先度設定（set_process_priority）は OS と権限によって失敗することがあります。失敗時は警告を出して継続します。
- データディレクトリ（data/）が存在しない場合はスクリプト側で自動作成されることがありますが、事前に作成しておくとパーミッション周りの問題を減らせます。

開発・拡張のヒント
------------------
- DuckDB 上のテーブル（prices_daily / raw_financials / raw_news など）を整備すれば、research／ai の関数をそのまま活用して解析や運用自動化が可能です。
- ポートフォリオ構築部分（portfolio/*）は純粋関数群なのでテストが容易です。ユニットテストを追加してロジックの正当性を担保してください。
- OpenAI 呼び出し部はリトライやレスポンス検証を実装済みですが、利用量・コストを考慮してローカルのキャッシュやスケジューリングを検討してください。

ライセンス・バージョン
----------------------
- 現在のパッケージバージョン: 0.1.0（src/kabusys/__init__.py の __version__）
- ライセンスについては本リポジトリの root にある LICENSE を参照してください（無ければ運用ポリシーに従って追加してください）。

補足
----
この README はコードベースから抽出した動作・設定情報の要約です。実際の運用前には必ず python -m kabusys.validate_config で設定を検証し、.env の機密情報は Git 等にコミットしないでください。