KabuSys
======

日本株自動売買システム（簡易版） - ドキュメント

概要
----
KabuSys は日本株向けの自動売買システムの骨組みを提供する Python プロジェクトです。  
主要な責務は以下の通りです。

- 環境設定の対話的セットアップおよび検証（.env）
- 注文発行／状態管理（ExecutionEngine, OrderManager, OrderRepository）
- ブローカークライアント（kabuステーション実装 / Mock 実装）
- リスクガード（Gate1〜3: 重複・余力・レート制限・ドローダウン等）
- 起動時のリコンシリエーション（Reconciler）
- マーケットカレンダー・ニュース収集などのデータ処理コンポーネント
- 監視（monitoring サービス用のポーリングスクリプト）

主な機能
--------
- .env 対話式ウィザード（kabusys.config_setup）
  - .env の新規作成・既存更新を支援
- 設定検証ツール（kabusys.validate_config）
  - 必須環境変数のチェック、YAML ファイルのパース確認等
  - --strict オプションで警告も失敗扱いに
- 実行スクリプト
  - run_execution.py: 発注エンジンを起動（本番 / ペーパートレード対応）
  - run_monitoring.py: 監視ループを起動（システムメトリクス等の記録）
- ブローカー API 抽象化（kabusys.execution.broker_api）
  - MockBrokerClient（テスト用） / KabuStationClient（kabuステーション 連携）
- 注文状態管理（State Machine）
  - OrderRecord / OrderManager / OrderRepository による堅牢な永続化と遷移
- リスク管理（kabusys.execution.risk_manager）
  - 3 段階のガード（シグナル・エグゼキューション・メトリクス）
- リコンシリエーション（再起動時の自動復旧）
- データ系ユーティリティ
  - マーケットカレンダー管理、ニュース収集など

セットアップ手順
---------------
前提
- Python 3.9+（型アノテーションや一部ライブラリを想定）
- SQLite（標準ライブラリ）
- duckdb Python パッケージ（DuckDB を使う機能があるため）

推奨手順（プロジェクトルートで実行）
1. 仮想環境の作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージのインストール
   プロジェクトに requirements.txt がある場合はそれを使用してください。
   ない場合の主要依存例:
   - pip install duckdb httpx websocket-client defusedxml PyYAML

   主要ライブラリ（コードから参照）
   - duckdb
   - httpx
   - websocket-client
   - defusedxml
   - PyYAML（config/*.yaml の内容検証に使用。無くても起動は可能）
   - （その他: typing標準モジュール／sqlite3などは標準に含まれます）

3. .env の用意
   - 対話式ウィザード: python -m kabusys.config_setup
     - 必須: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD
     - その他の変数はウィザードで設定できます
   - または手動で .env を作成（.env.example を参考に）

4. 設定検証
   - python -m kabusys.validate_config
   - --strict を付けると警告もエラー扱い（exit code 1）になります

5. DB 初期化（必要に応じて）
   - Execution 実行時に init_orders_db / init_monitoring_db が呼ばれるようになっています。
   - ディレクトリ data/ が無い場合は自動的に作成される処理も多く含まれますが、権限等を確認してください。

使い方（起動例）
----------------

環境変数について
- 必須:
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- 推奨 / 任意:
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
  - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH（監視DB、デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH（paper_trading 用の分離DB）
  - LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL）
  - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（本番アラート）
  - KILL_FLAG_CLEAR_ON_START（1 で起動時に kill.flag を自動クリア）
  - MONITOR_POLL_INTERVAL（run_monitoring 用、秒。デフォルト: 60）

主要コマンド
- 環境ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 厳格モード: python -m kabusys.validate_config --strict

- 発注エンジン（Execution）
  - python -m kabusys.run_execution
  - KABUSYS_ENV が paper_trading の場合は MockBrokerClient を使用し、paper_trading 用 SQLite（デフォルト: data/paper_trading.db）に記録します。
  - 実行中に data/stop_requested.flag を作成すると安全に停止します。

- 監視サービス
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更できます（デフォルト 60 秒）。
  - 監視は本番用 sqlite_path を使って記録します（環境に依らず本番 DB を参照する設計）。

注意事項
- .env は絶対に VCS にコミットしないでください（秘密情報・パスワードが含まれます）。
- 本番環境 (KABUSYS_ENV=live) では LINE 通知や kill flag 設定等を慎重に行ってください。validate_config は live の場合に追加チェック（警告）を行います。
- run_execution は PID ファイルを data/execution.pid に書きます。既存の kill.flag が存在する場合の挙動は KILL_FLAG_CLEAR_ON_START に依存します。

ディレクトリ構成
----------------
（プロジェクトルート直下に src/ がある想定。以下は主要なファイルと概要）

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数の自動読み込み（.env / .env.local）、Settings クラス（アプリ設定の取得）
  - config_setup.py
    - .env の対話式ウィザード（python -m kabusys.config_setup）
  - validate_config.py
    - .env と config/*.yaml の事前検証 CLI（python -m kabusys.validate_config）
  - run_execution.py
    - ExecutionEngine の起動スクリプト（python -m kabusys.run_execution）
  - run_monitoring.py
    - 監視ポーリングループ起動スクリプト（python -m kabusys.run_monitoring）
  - execution/
    - broker_api.py
      - ブローカー API の Protocol、データモデル、例外、ファクトリ関数
    - broker_factory.py
      - Settings に応じたブローカークライアント生成
    - kabu_client.py
      - kabuステーション REST API クライアント実装
    - mock_client.py
      - テスト用の MockBrokerClient（fill_mode 等で挙動を切替可能）
    - order_record.py
      - 注文状態遷移ロジック（State Machine）
    - order_repository.py
      - SQLite を使った永続化層（orders テーブル）
    - order_manager.py
      - 上位 API（Order 作成 / 送信 / 同期 / キャンセル）
    - execution_engine.py
      - シグナル処理 / WebSocket ドレイン / セッション制御 等の中心ロジック
    - reconciler.py
      - 起動時の自動復旧（OrderSent の突合・ポジション差分検出）
    - risk_manager.py
      - Gate1〜3 のリスク検査ロジック
  - data/
    - calendar_management.py
      - JPX カレンダー管理（DuckDB ベース）、next_trading_day 等
    - news_collector.py
      - RSS からニュース収集、前処理、DB 保存ロジック
  - monitoring/
    - monitoring_db.py  (監視 DB 初期化／ログ用API 等)
      - run_monitoring や Execution の監視ロギングに利用（ファイルはプロジェクトに含まれている前提）
  - utils/
    - logging_setup.py
      - ログ設定ユーティリティ（起動時に呼ばれる）
    - process_priority.py
      - プロセス優先度設定ユーティリティ
  - その他:
    - config/*.yaml
      - system_config.yaml, data_config.yaml, strategy_config.yaml, risk_config.yaml, execution_config.yaml, monitoring_config.yaml
      - validate_config.py が存在確認・パース検査を行います（PyYAML が必要）

サンプル .env（抜粋）
--------------------
# J-Quants
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here

# kabu station
KABU_API_PASSWORD=your_kabu_api_password_here
KABU_API_BASE_URL=http://localhost:18080/kabusapi

# データベース
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db

# システム
KABUSYS_ENV=development
LOG_LEVEL=INFO
KILL_FLAG_CLEAR_ON_START=0

よくある質問（短め）
------------------
- Q: テスト環境で実際の証券会社に接続せず動かせますか？
  - A: はい。KABUSYS_ENV=paper_trading または development の場合、MockBrokerClient が使用されます。PAPER_FILL_MODE で fill の挙動を制御できます。

- Q: 設定検証で YAML ファイルが見つからないと警告が出ます。どうすればよいですか？
  - A: validate_config は config/*.yaml の存在を確認します。生成スクリプト（scripts/generate_config.py）がある場合はそれで生成するか、手動で用意してください。PyYAML が無ければパース検査はスキップされます（警告）。

- Q: 起動時の kill.flag の扱いは？
  - A: 実行時に data/kill.flag が存在すると起動を拒否します（KILL_FLAG_CLEAR_ON_START=1 の場合は自動クリアして起動可）。実行中は stop_requested.flag により安全停止が可能です。

貢献・拡張
----------
- Live broker client（KabuStationClient）を本番仕様に合わせて拡張する（現在の設計はテスト重視で Mock をサポート）
- モニタリング・アラートの強化（LINE/外部通知）
- カレンダー・ニュース ETL のジョブ化（スケジューラへの統合）
- テストカバレッジの充実（ユニット・統合テスト）

ライセンス・注意
----------------
- .env に API トークンやパスワードを含むため、絶対にバージョン管理システムへ含めないでください。README 内のサンプル値はプレースホルダです。

以上。必要であれば README の英語版、requirements.txt のテンプレート、あるいは各モジュールの詳細ドキュメント (API リファレンス) を別途作成します。どれを優先しますか？