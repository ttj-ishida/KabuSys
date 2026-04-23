# KabuSys

日本株自動売買システム（KabuSys）用のコアモジュール群。  
このリポジトリには、設定管理・検証、発注エンジン、モニタリング、データ収集などの主要コンポーネントが含まれます。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は、kabuステーション / J-Quants 等を利用した日本株の自動売買を想定したソフトウェア基盤です。本コードベースは次の機能を持つモジュールで構成されています。

- 環境設定ウィザード（.env の作成・更新）
- 起動前の設定検証ツール（.env / config/*.yaml のチェック）
- 発注エンジン（ExecutionEngine）：シグナル駆動の発注ループ、WebSocket push 処理、キルスイッチ
- ブローカークライアント（実プロキシ: KabuStationClient、テスト用: MockBrokerClient）
- 注文状態管理（OrderRecord）、永続化（SQLite）、OrderManager（発注ワークフロー）
- リスク管理（3段階ガード: Gate1/2/3）、リコンシリエーション
- 監視ループ（SystemMonitor）と監視データの永続化
- データモジュール（マーケットカレンダー、ニュース収集）

本 README は開発者向けの簡易ガイドです。

---

## 機能一覧

- .env 対話式ウィザード（python -m kabusys.config_setup）
- 設定検証 CLI（python -m kabusys.validate_config）：
  - 必須環境変数の有無チェック
  - KABUSYS_ENV / LOG_LEVEL の検証
  - DB パスの親ディレクトリ存在チェック
  - config/*.yaml の存在と（PyYAML があれば）パース検証
  - 本番（live）向けの追加ガード
- ExecutionEngine：
  - シグナル読込 → Gate1/2 検査 → 発注（OrderManager）
  - WebSocket push ドレイン（注文状態同期 + Gate3 ドローダウン監視）
  - Kill switch（kill.flag）による安全停止と全 active 注文のキャンセル
- Reconciler：再起動時の OrderSent 状態照合 & ポジション差分検出
- MockBrokerClient：ペーパートレード・単体テスト用のモック
- リスクマネージャ：
  - 個別銘柄上限、総資産利用率、レート制限、サーキットブレーカー、ドローダウン
- データ系：
  - マーケットカレンダー管理（DuckDB）
  - ニュース収集（RSS → raw_news、SSRF/XML 攻撃対策等を考慮）

---

## セットアップ手順

前提
- Python 3.9 以上を推奨（型ヒント・標準ライブラリの使用から）
- SQLite は Python 標準ライブラリで利用可能
- ローカルで kabuステーション を使う場合は kabuステーションアプリが必要

推奨パッケージ（最低限）
- duckdb
- httpx
- websocket-client
- PyYAML（設定ファイル検証時に利用、任意）
- defusedxml
- （必要に応じて）その他テストツールや開発ツール

例: pip でインストール
```bash
python -m pip install duckdb httpx websocket-client PyYAML defusedxml
```

リポジトリ準備
1. このリポジトリをチェックアウトする
2. 作業ディレクトリ直下に data/ ディレクトリを作る（多くのデフォルト DB パスは data/ を参照）
   ```bash
   mkdir -p data
   ```

環境変数設定
- 推奨手順は対話式ウィザードで .env を作成すること:
  ```bash
  python -m kabusys.config_setup
  ```
  ウィザードは既存の `.env` を読み込み、対話形式で更新できます。.env は絶対に Git にコミットしないでください。

自動 .env ロード
- 起動時、デフォルトでプロジェクトルートの `.env` と `.env.local` を自動的に読み込みます（OS 環境変数は上書きされません）。
- 自動ロードを無効にする場合:
  ```bash
  export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  ```

必須環境変数（最低限）
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

オプション（よく使う）
- KABUSYS_ENV（development / paper_trading / live、デフォルト: development）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（paper_trading 時の独立 DB、デフォルト: data/paper_trading.db）
- LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- KABU_API_BASE_URL（kabuステーションの base URL）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（本番通知用）

検証
- .env 作成後、設定検証を実行:
  ```bash
  python -m kabusys.validate_config
  ```
  警告を FAIL 扱いにしたい場合は `--strict` を付与します:
  ```bash
  python -m kabusys.validate_config --strict
  ```

---

## 使い方（主要スクリプト）

- 環境設定ウィザード（.env 作成）
  ```
  python -m kabusys.config_setup
  ```

- 設定検証（起動前チェック）
  ```
  python -m kabusys.validate_config [--strict]
  ```

- Execution（発注エンジン）起動
  ```
  python -m kabusys.run_execution
  ```
  補足:
  - KABUSYS_ENV が `paper_trading` の場合は MockBrokerClient を使い、paper_trading 用 SQLite（デフォルト: data/paper_trading.db）に記録されます（本番 DB と分離）。
  - `kill.flag` / `stop_requested.flag` による外部制御が可能。PID ファイルはデフォルトで `data/execution.pid` に書き込まれます。

- Monitoring（システム監視）起動
  ```
  python -m kabusys.run_monitoring
  ```
  補足:
  - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL`（秒）で上書き可能（デフォルト 60 秒）。
  - Monitoring は KABUSYS_ENV に依らず本番 sqlite_path を使用します（設定に注意）。

---

## 主要ファイル／ディレクトリ構成

（リポジトリの src/kabusys を起点に抜粋）

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数読み込み（.env/.env.local 自動ロード）
    - Settings クラス（アプリ設定アクセサ）
  - config_setup.py
    - 対話式 .env ウィザード（python -m kabusys.config_setup）
  - validate_config.py
    - 起動前チェック CLI（python -m kabusys.validate_config）
  - run_execution.py
    - ExecutionEngine 起動スクリプト（python -m kabusys.run_execution）
  - run_monitoring.py
    - SystemMonitor ポーリングループ（python -m kabusys.run_monitoring）
  - execution/
    - broker_api.py
      - BrokerAPIProtocol, データモデル, 例外, create_broker_api()
    - kabu_client.py
      - KabuStationClient（httpx & websocket 実装）
    - mock_client.py
      - MockBrokerClient（テスト/ペーパー用）
    - broker_factory.py
      - 設定に応じたブローカークライアント生成
    - order_record.py
      - OrderRecord と状態遷移ロジック（状態マシン）
    - order_repository.py
      - SQLite を使った永続化（orders テーブル定義・CRUD）
    - order_manager.py
      - 発注ワークフロー（create/send/sync/cancel）
    - execution_engine.py
      - ExecutionEngine（シグナル処理 / push ドレイン / kill switch）
    - reconciler.py
      - 起動時のリコンシリエーション
    - risk_manager.py
      - Gate1/2/3 のリスク制御
  - data/
    - calendar_management.py
      - マーケットカレンダー管理（DuckDB）
    - news_collector.py
      - RSS ニュース収集（defusedxml 等を使用）
  - monitoring/
    - （monitoring_db, system_monitor 等のモジュールを想定）
  - utils/
    - logging_setup.py, process_priority.py 等（ログ設定やプロセス優先度制御を想定）

補足:
- デフォルトの DB パスは `data/` 配下を想定しています。
  - DuckDB: data/kabusys.duckdb
  - Monitoring SQLite: data/monitoring.db
  - Paper trading SQLite: data/paper_trading.db

---

## 動作上の注意・運用メモ

- 本番環境（KABUSYS_ENV=live）では特に注意:
  - validate_config は live のときに警告を出します（LINE 通知設定や KILL_FLAG_CLEAR_ON_START 等）。
  - KILL_FLAG_CLEAR_ON_START が `1` に設定されていると起動時に kill.flag が自動でクリアされるため本番では `0` を推奨します。
- .env/.env.local は OS 環境変数よりも下位（自動ロード時）に読み込まれるため、CI や運用では OS 環境変数で上書き可能。
- PyYAML がインストールされていない場合、validate_config は YAML の中身チェックをスキップします（存在チェックのみ）。
- ExecutionEngine のログ・監視は設定に依存します。ログレベルは LOG_LEVEL で指定してください。

---

## 参考コマンドまとめ

- .env ウィザード:
  ```
  python -m kabusys.config_setup
  ```
- 設定検証:
  ```
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```
- 発注エンジン起動:
  ```
  python -m kabusys.run_execution
  ```
- 監視ループ起動:
  ```
  python -m kabusys.run_monitoring
  ```

---

この README はコードベースから抽出できる情報を元に作成しています。詳細な運用手順・デプロイ方法・追加設定（ログ出力先、外部通知設定、Docker 化など）は別途ドキュメント化することを推奨します。必要であれば README に追加すべき箇所を教えてください。