KabuSys — 日本株自動売買システム（簡易 README）
概要
本リポジトリは日本株向けの自動売買コンポーネント群です。主に以下を提供します。
- 環境設定ウィザード／検証ツール（.env の作成・検証）
- ExecutionEngine（シグナルを受けて発注を行うエンジン、ペーパートレード対応）
- ブローカークライアント（Mock / kabu station 実装）
- 注文永続化（SQLite）、約定リコンシリエーション
- 監視ループ（SystemMonitor）
- マーケットカレンダー管理、ニュース収集などのデータ処理ユーティリティ

特徴（主な機能）
- .env 対話ウィザード（kabusys.config_setup）で初期設定を簡単に生成
- 設定検証 CLI（kabusys.validate_config）で起動前に環境変数や config/*.yaml をチェック
- ExecutionEngine による「Signal Queue Pull 型」発注フロー（Gate1/2/3 によるリスクガード）
- MockBrokerClient によるペーパートレード実行（fill_mode 制御）
- 注文状態を管理する OrderRecord（状態遷移の検証）と永続化レイヤ（SQLite）
- リコンシリエーション（再起動時に OrderSent を突合して復旧）
- DuckDB を用いたデータ分析用 DB、監視用 SQLite DB を利用

前提（推奨）
- Python 3.10+（型エイリアスや typing 機能を使用）
- pip 環境（開発時は仮想環境推奨）

主要依存パッケージ（例）
- duckdb
- httpx
- websocket-client
- PyYAML（config 検証で任意）
- defusedxml
（実際の requirements.txt がある場合はそちらを使用してください）

セットアップ手順（簡易）
1. リポジトリをクローンしてプロジェクトルートへ移動
   - プロジェクトルートには .env/.env.local や data/ ディレクトリを置く想定です。

2. 必要パッケージをインストール（例）
   pip install duckdb httpx websocket-client pyyaml defusedxml

3. .env の作成（対話式ウィザード）
   python -m kabusys.config_setup
   ウィザードが .env ファイルを生成します。既存 .env がある場合は読み込んで編集できます。

4. 設定検証
   python -m kabusys.validate_config
   - --strict を付けると警告も FAIL（exit 1）扱いになります。
   - PyYAML がインストールされていると config/*.yaml の YAML パースチェックも行います。

5. 実行
   - ペーパートレード（開発）モードで実行（例）
     KABUSYS_ENV=paper_trading python -m kabusys.run_execution
   - 監視ループ起動
     python -m kabusys.run_monitoring
     - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可能（デフォルト 60）

主要環境変数（抜粋）
- 必須
  - JQUANTS_REFRESH_TOKEN : J-Quants API 用リフレッシュトークン（必須）
  - KABU_API_PASSWORD     : kabuステーション API パスワード（必須）
- 任意 / 推奨
  - KABUSYS_ENV           : execution 環境（development / paper_trading / live）
  - DUCKDB_PATH           : DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
  - SQLITE_PATH           : 監視用 SQLite（デフォルト data/monitoring.db）
  - LOG_LEVEL             : ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
  - KABU_API_BASE_URL     : kabu station ベース URL（デフォルト http://localhost:18080/kabusapi）
  - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID : 本番通知用（live 時に警告）
  - KILL_FLAG_CLEAR_ON_START : 起動時に kill.flag を自動クリアするか（0/1、デフォルト 0）
- Paper trading 関連
  - PAPER_FILL_MODE       : instant / partial / never / reject（デフォルト instant）
  - PAPER_TRADING_SQLITE_PATH : ペーパートレード専用 SQLite（デフォルト data/paper_trading.db）
- 自動 .env ロード
  - デフォルトでプロジェクトルートの .env → .env.local を自動読み込み（OS 環境変数が優先）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動ロードを無効化

よく使うコマンド（サンプル）
- 設定ウィザード:
  python -m kabusys.config_setup
- 設定検証:
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
- 実行エンジン（本番/ペーパーは KABUSYS_ENV に依存）:
  KABUSYS_ENV=paper_trading python -m kabusys.run_execution
- 監視ループ:
  python -m kabusys.run_monitoring
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

運用上の注意
- KABUSYS_ENV=live を設定した場合、設定ミスは実際の発注につながります。validate_config の警告は特に注意してください（--strict 推奨）。
- kill.flag（デフォルト data/kill.flag）が存在する場合、ExecutionEngine は基本的に起動を拒否します。KILL_FLAG_CLEAR_ON_START=1 で起動時に自動クリアできますが、本番では 0 を推奨します。
- ExecutionEngine は PID ファイル（デフォルト data/execution.pid）を書きます。停止フラグは data/stop_requested.flag を使用します。
- ペーパートレードは MockBrokerClient を使い、本番 DB と分離するため PAPER_TRADING_SQLITE_PATH が利用されます。

ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py — パッケージ定義、バージョン
  - config.py — 環境変数読み込み・Settings（自動 .env ロード、require helper）
  - config_setup.py — .env 対話式ウィザード（python -m kabusys.config_setup）
  - validate_config.py — 起動前設定検証 CLI（python -m kabusys.validate_config）
  - run_execution.py — ExecutionEngine 起動スクリプト（python -m kabusys.run_execution）
  - run_monitoring.py — SystemMonitor ポーリングループ（python -m kabusys.run_monitoring）
  - execution/
    - __init__.py — execution レイヤの公開 API
    - broker_api.py — BrokerAPI の Protocol / データモデル / 例外 / ファクトリ
    - kabu_client.py — kabu station REST/WebSocket クライアント（HTTP + WS）
    - mock_client.py — MockBrokerClient（テスト・ペーパートレード用）
    - broker_factory.py — Settings に基づくブローカーファクトリ
    - order_record.py — OrderRecord（状態遷移ロジック）
    - order_repository.py — SQLite による永続化層（orders テーブル初期化 helper）
    - order_manager.py — Order 管理（作成・送信・同期・キャンセル）
    - execution_engine.py — ExecutionEngine（シグナル処理・push ドレイン・kill_switch 等）
    - reconciler.py — リコンシリエーション（OrderSent の突合・ポジション差分検出）
    - risk_manager.py — Gate1/2/3 によるリスク統制
  - data/
    - calendar_management.py — マーケットカレンダー管理 / 営業日判定 / 夜間更新ジョブ
    - news_collector.py — RSS ニュース収集・正規化・保存ロジック
  - monitoring/  — 監視関連（SystemMonitor / monitoring_db など、実装ファイルは省略）
  - utils/       — ロギングセットアップ、プロセス優先度設定などユーティリティ（実装ファイルは参照）

補足（設計メモ）
- Execution の発注フローはクラッシュ耐性を考慮した 2 相永続化（OrderSent の保存 → broker 呼び出し → broker_order_id の保存 → OrderAccepted の更新）を採用しています。これによりクラッシュ後の再照合で状態を回復できます。
- リスク管理は 3 段階（Gate1: シグナル、Gate2: 実行（レート制御/CB）、Gate3: ドローダウン）で設計されています。
- DuckDB はデータ分析・シグナル読み込み用に使用します。market_calendar などデータ更新ジョブも用意されています。

トラブルシュート（簡易）
- validate_config が警告／エラーを出す場合は .env の必須項目（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD 等）を確認してください。
- PyYAML が無いと config/*.yaml の検証がスキップされます。YAML 検証を行うには pip install pyyaml。
- WebSocket 関連で接続できない場合は KABU_API_BASE_URL のスキーム・ポート、kabuステーションの稼働を確認してください。

以上がこのコードベースの概要と利用方法の要点です。必要であれば、README に含めるサンプル .env テンプレートやより詳細な運用手順（デプロイ手順、systemd ユニット例、監視指標の説明など）を追加します。どの部分を詳しく書きたいか教えてください。