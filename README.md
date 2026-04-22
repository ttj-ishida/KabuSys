# KabuSys

日本株向け自動売買フレームワーク（プロジェクト骨格）。  
このリポジトリは、発注エンジン（ExecutionEngine）、リスクガード、ブローカークライアント層、監視ループ、データ処理ユーティリティ等を含む設計例を提供します。実稼働向けの接続/運用ロジックは部分的にモック実装（paper_trading / development）で動作する設計です。

## 主な特徴
- 環境変数 / 設定ファイルの対話式ウィザード（.env 生成）と起動前検証ツール
- ExecutionEngine：シグナルプル型の発注エンジン（Gate1/2/3 によるリスクガード）
- Broker API 抽象化：実ブローカークライアント（kabu station）と Mock クライアントの切替が可能
- 注文状態管理：OrderRecord（状態遷移の検証）、SQLite 永続化（OrderRepository）
- リコンシリエーション：クラッシュ後の OrderSent レコード照合とポジション差分検出
- 監視ループ（SystemMonitor）と監視 DB（SQLite）
- データユーティリティ：マーケットカレンダー管理、ニュース収集 など（DuckDB ベース）

## 機能一覧（抜粋）
- .env 対話式作成: `kabusys.config_setup.run_wizard` / `python -m kabusys.config_setup`
- 設定検証 CLI: `.env` と `config/*.yaml` を起動前に検証（PyYAML があれば YAML パースも確認）  
  コマンド: `python -m kabusys.validate_config [--strict]`
- 発注エンジン起動スクリプト: `python -m kabusys.run_execution`
  - `KABUSYS_ENV=paper_trading` では MockBrokerClient を使用（本番 DB と分離）
  - 停止フラグファイル（data/stop_requested.flag）で外部停止を検知
- 監視ループ起動スクリプト: `python -m kabusys.run_monitoring`
  - ポーリング間隔は `MONITOR_POLL_INTERVAL` 環境変数で上書き可能（デフォルト 60 秒）
  - 監視は sqlite_path（本番パス）を使用
- Broker クライアント抽象化
  - `create_broker_api(mock=True, ...)` で MockBrokerClient を生成
  - `KabuStationClient` は kabu station REST API を扱う（httpx + websocket-client）
- RiskManager: 3 段階のガード（シグナルレベル・エグゼキューションレベル・メトリクスレベル）
- Reconciler: OrderSent の自動照合、ポジション差分検出

## 必要な環境（主な依存）
- Python 3.9+
- ランタイム依存パッケージ（例）
  - duckdb
  - httpx
  - websocket-client
  - defusedxml
  - PyYAML（YAML 検証を有効にする場合）
これらを requirements.txt にまとめている場合は以下のようにインストールしてください（仮）:
```
pip install duckdb httpx websocket-client defusedxml PyYAML
```

## セットアップ手順（簡易）
1. リポジトリをクローンして作業ディレクトリに移動
2. 必要な python パッケージをインストール（上記参照）
3. .env を作成
   - 対話式ウィザードを使う（推奨）
     ```
     python -m kabusys.config_setup
     ```
   - あるいは手動でプロジェクトルートに `.env` を作成
4. 設定を検証
   ```
   python -m kabusys.validate_config
   # 警告も失敗扱いにする場合
   python -m kabusys.validate_config --strict
   ```
5. DuckDB / SQLite のデータディレクトリ（デフォルト data/）を作成（必要に応じて）
   ```
   mkdir -p data
   ```

## 環境変数（重要なもの）
- 必須
  - JQUANTS_REFRESH_TOKEN — J-Quants API 用リフレッシュトークン
  - KABU_API_PASSWORD — kabuステーション API パスワード
- 任意 / 推奨（既定値あり）
  - KABUSYS_ENV — 実行環境（development / paper_trading / live）
  - DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH — 監視 DB（デフォルト: data/monitoring.db）
  - LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
  - KABU_API_BASE_URL — kabuステーション API ベース URL
  - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID — LINE 通知設定
  - KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリア（0/1）
- その他
  - MONITOR_POLL_INTERVAL — 監視ループのポーリング間隔（秒、デフォルト 60）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 — 自動で .env を読み込ませたくない場合（テスト用）

注意: Settings モジュールは起動時にプロジェクトルートの `.env` / `.env.local` を自動で読み込みます（OS 環境変数が優先）。自動ロード無効化は上記参照。

## 使い方（実行例）

- 設定ウィザード（.env 作成）
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- ExecutionEngine を起動（paper_trading / development では MockBrokerClient を使用）
  ```
  # 例: ペーパートレード環境で起動
  export KABUSYS_ENV=paper_trading
  python -m kabusys.run_execution
  ```
  実行時は data/execution.pid（PID ファイル）が書き込まれ、data/stop_requested.flag の存在で停止されます。paper_trading の場合、orders は `PAPER_TRADING_SQLITE_PATH`（デフォルト data/paper_trading.db）に保存され、本番 DB と分離されます。

- 監視プロセス起動
  ```
  python -m kabusys.run_monitoring
  # ポーリング間隔を変更する場合
  export MONITOR_POLL_INTERVAL=30
  python -m kabusys.run_monitoring
  ```
  監視は sqlite_path（Settings.sqlite_path）を使用して監視データを記録します。

- プログラムからの利用（設定取得）
  ```
  from kabusys.config import settings
  token = settings.jquants_refresh_token
  duckdb_path = settings.duckdb_path
  ```

- ブローカークライアント作成（コード内）
  - `create_broker_api(mock=True, fill_mode="instant")` などを利用して Mock / 実装切替
  - `BrokerClientFactory.create(settings)` により Settings に基づいたクライアントを得られます

## 起動上の注意
- 本番用 `KABUSYS_ENV=live` を使用する際は validate_config の警告・エラーを必ず確認してください。LINE 通知など本番特有の警告があります。
- `KILL_FLAG_CLEAR_ON_START=1` は本番では危険（kill flag を自動クリアしてしまう）なのでデフォルト 0 を推奨します。
- ExecutionEngine はセッション制御（8:50〜9:10 シグナル処理、9:10〜15:30 push ドレイン）に従います。テストでは直接メソッドを呼ぶことができます。

## ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py — パッケージ定義
  - config.py — Settings（環境変数読み込み・アクセス）
  - config_setup.py — .env 対話式ウィザード
  - validate_config.py — 起動前検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — 監視ループ起動スクリプト
  - execution/
    - __init__.py
    - broker_api.py — Broker API のデータモデル・Protocol・ファクトリ
    - kabu_client.py — kabu station 実装（HTTP/WebSocket）
    - mock_client.py — MockBrokerClient（テスト用）
    - broker_factory.py — Settings に基づくクライアント生成
    - execution_engine.py — ExecutionEngine（シグナル処理・push ドレイン）
    - order_record.py — OrderRecord（状態遷移ロジック）
    - order_repository.py — SQLite 永続化層（orders テーブル）
    - order_manager.py — 発注フロー（create/send/sync/cancel）
    - reconciler.py — リコンシリエーション（起動時の自動復旧）
    - risk_manager.py — 3 段階リスクガード
  - data/
    - calendar_management.py — マーケットカレンダー管理（DuckDB ベース）
    - news_collector.py — RSS ニュース収集（セキュリティ対策付き）
    - (その他データ関連モジュール)
  - monitoring/
    - (監視 DB 初期化 / SystemMonitor 実装 等)
  - utils/
    - logging_setup.py — ロギング設定ユーティリティ
    - process_priority.py — プロセス優先度設定ユーティリティ
  - scripts/
    - generate_config.py (参照のみ) — config/*.yaml の初期生成スクリプト（validate_config から参照）

（上記はコードベースで提供されている主要モジュールの抜粋です。詳細は各モジュールの docstring を参照してください。）

## 追加メモ
- config/*.yaml（system_config.yaml, data_config.yaml, strategy_config.yaml, risk_config.yaml, execution_config.yaml, monitoring_config.yaml）は設定ファイル群として想定されています。`validate_config.py` は存在確認と（PyYAML があれば）パース確認を行います。見つからない場合は警告を出します。
- news_collector や calendar_management は外部 API（J-Quants 等）を想定しており、実行には API トークン等が必要です。
- 自動ロードされる `.env` の優先順位は OS 環境 > .env.local > .env です。テスト等で自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

不明点や README に追記してほしい情報（例: 実行例のログ、より詳細な依存パッケージリスト、データベース初期化手順など）があれば教えてください。追加でサンプル .env テンプレートや起動スクリプトの systemd ユニット例なども用意できます。