KabuSys
======

日本株自動売買システム（ライブラリ / 実行スクリプト群）

概要
----
KabuSys は日本株の自動売買を想定した小規模なフレームワークです。  
主な目的は以下のとおりです：

- Signal → 発注フロー（ExecutionEngine）
- 発注の永続化と状態管理（SQLite）
- ブローカー API 抽象化（kabuステーション用実装 + テスト用モック）
- 起動時の設定ウィザード（.env 作成）と設定検証ツール
- 監視ループ（SystemMonitor）と監視用 DB（SQLite / DuckDB）
- カレンダー・ニュース収集などのデータユーティリティ

特徴（主な機能）
----------------
- .env 対話式ウィザードで初期設定を作成・更新（python -m kabusys.config_setup）
- 起動前に環境変数 / config/*.yaml を検証する CLI（python -m kabusys.validate_config）
  - --strict オプションで警告も失敗扱いにできます
- ExecutionEngine によるシグナル駆動発注（発注時間帯 / push ドレイン / kill switch 等の制御）
- OrderRecord（純粋な状態遷移ロジック） + OrderRepository（SQLite 永続化）
- RiskManager による 3 段階リスクガード（Gate1/2/3）
- MockBrokerClient によるペーパートレード / テスト用の発注シミュレーション
- Reconciler による起動時の注文同期（OrderSent の照合）とポジション差分検出
- DuckDB を用いた分析データ / カレンダー管理 / ニュース収集ユーティリティ

セットアップ（開発環境向け）
--------------------------
※ 実行には適宜 Python3.8+（または本プロジェクトが想定するバージョン）を想定します。

1. レポジトリをクローン・チェックアウトする
2. 仮想環境を作成して有効化する（例: python -m venv .venv; source .venv/bin/activate）
3. 依存パッケージをインストールする（例）:
   - duckdb
   - httpx
   - websocket-client
   - defusedxml
   - PyYAML （validate_config の YAML 構文チェックに必要）
   - （その他、開発ツールやテスト用パッケージ）

   例:
   pip install duckdb httpx websocket-client defusedxml PyYAML

4. データディレクトリを作る（必要に応じて自動作成されますが手動でも）:
   mkdir -p data

自動 .env 読み込み
------------------
- 起動時に .env/.env.local を自動で読み込みます（OS 環境変数 > .env.local > .env の優先順）。
- 自動読み込みを無効化する場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

重要な環境変数
----------------
必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

主要（任意・上書き可能）:
- KABUSYS_ENV: execution 環境（development / paper_trading / live）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（デフォルト data/monitoring.db）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- KABU_API_BASE_URL: kabu station API ベース URL
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: 本番アラート用

設定ウィザード（.env 作成）
--------------------------
対話式で .env を生成・更新できます。

コマンド:
python -m kabusys.config_setup

流れ:
- 既存の .env を読み込める（Enter で既存値を再利用）
- 質問に従って値を入力（シークレットはマスク表示）
- 最後に保存確認があり、.env を出力します

設定検証 CLI
------------
起動前に設定の不備を検出します（.env と config/*.yaml の存在・整合性など）。

コマンド:
python -m kabusys.validate_config
python -m kabusys.validate_config --strict   # 警告も FAIL 扱い（exit code 1）

戻り値:
- 0: OK（エラーなし、警告なしまたは許容）
- 1: FAIL（エラーあり、または --strict で警告あり）

実行方法（エンジン / 監視）
--------------------------
- 実際の発注エンジン（ExecutionEngine）起動:
  python -m kabusys.run_execution

  注意:
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し paper_trading 用 SQLite（デフォルト: data/paper_trading.db）へ記録されます。is_live は現在未実装で NotImplementedError になります。
  - 起動時に data/execution.pid（デフォルト）へ PID を書き込み、kill.flag（デフォルト data/kill.flag）があると起動を拒否します（KILL_FLAG_CLEAR_ON_START=1 の場合は自動クリアして起動可）。
  - run_session() はシグナル処理（8:50-9:10）→ push ドレイン（9:10-15:30）を想定します（テスト時は個別メソッド呼び出しが可能）。

- 監視ループ起動:
  python -m kabusys.run_monitoring

  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書き可能。デフォルト 60 秒。
  - 監視は設定にかかわらず（KABUSYS_ENV に関係なく）本番 sqlite_path を使用します。

プロジェクト内の注意点
--------------------
- DB ファイル（デフォルト data/*.db）は親ディレクトリがない場合に警告が出ますが、多くのスクリプトは起動時にディレクトリを作成します。
- validate_config は PyYAML 未インストール時に YAML パース検査をスキップします（警告）。
- mock クライアントの fill_mode は環境変数 PAPER_FILL_MODE（instant/partial/never/reject）で制御できます。
- .env は絶対に Git にコミットしないでください（config_setup のヘッダにも注意書きがあります）。

主要モジュール構成（抜粋）
-------------------------
src/kabusys/
- __init__.py
  - パッケージ情報（__version__ など）
- config.py
  - .env 読み込みロジック、自動ロード、Settings クラス（環境変数アクセスの集中）
- config_setup.py
  - .env 対話ウィザード（run_wizard）
- validate_config.py
  - 起動前設定検証 CLI（必須環境変数 / config/*.yaml / 本番ガード等）
- run_execution.py
  - ExecutionEngine の起動スクリプト（PID / stop flag / DB 接続等）
- run_monitoring.py
  - SystemMonitor のポーリングループ起動スクリプト
- execution/
  - broker_api.py: BrokerAPIProtocol, データモデル, 例外, create_broker_api ファクトリ
  - kabu_client.py: kabuステーション REST クライアント実装（httpx + websocket）
  - mock_client.py: MockBrokerClient（テスト用）
  - broker_factory.py: Settings に基づくクライアント生成
  - order_record.py: Order の状態遷移ロジック（純粋モデル）
  - order_repository.py: SQLite を用いた永続化層（orders テーブル初期化含む）
  - order_manager.py: 外向き API（create/send/sync/cancel）
  - execution_engine.py: ExecutionEngine（シグナル処理・push ドレイン・kill switch 等）
  - reconciler.py: 起動時リコンシリエーション（OrderSent の照合 / ポジション差分）
  - risk_manager.py: Gate1/2/3 によるリスク制御
- data/
  - calendar_management.py: マーケットカレンダ管理（DuckDB + J-Quants 連携想定）
  - news_collector.py: RSS ニュース収集（前処理 / SSRF 対策 / defusedxml 使用）
- monitoring/
  - monitoring_db.py (スクリプト内参照あり): 監視用 DB 初期化 / ロギングユーティリティ
- utils/
  - logging_setup.py: ロギング初期化ユーティリティ
  - process_priority.py: プロセス優先度設定ユーティリティ

例（最小の起動手順）
--------------------
1. .env を作成:
   python -m kabusys.config_setup

2. 設定検証:
   python -m kabusys.validate_config

3. 実行（ペーパートレード）:
   # 例: bash で一時的に環境変数を設定
   export KABUSYS_ENV=paper_trading
   python -m kabusys.run_execution

ライセンス / 貢献
-----------------
（レポジトリに LICENSE 等があれば追記してください）

補足（開発者向けメモ）
--------------------
- 設定自動読み込みはプロジェクトルート（.git または pyproject.toml があるディレクトリ）を基準に行います。パッケージ配布後も __file__ を基点に探索するため、CWD に依存しません。
- validate_config は config/*.yaml（system_config.yaml 等）をチェックします。テンプレート生成スクリプトがある想定（scripts/generate_config.py がメッセージ内に言及あり）。
- Live ブローカークライアントの完全実装は未完了（BrokerClientFactory は is_live で NotImplementedError を投げます）。

以上。必要であれば README にインストール用 requirements.txt のサンプルや、より詳しい起動オプションの一覧、実行フローのシーケンス図などを追加できます。どの情報を拡張しますか？