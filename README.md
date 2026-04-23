# KabuSys

日本株向け自動売買システム（KabuSys）のリポジトリ内ドキュメント（README）。  
この README はソースコード（src/kabusys 配下）を基に作成されています。

---

## プロジェクト概要

KabuSys は、日本株を対象とした自動売買システムの骨組み（Execution Engine、Risk Manager、Broker API 抽象、監視、データ処理ユーティリティなど）を提供する Python パッケージ群です。  
環境変数と .env による設定管理、発注の状態管理（State Machine）、発注の永続化（SQLite）、シグナル処理と WebSocket ベースのプッシュ受信、リコンシリエーション（クラッシュ後復旧）、監視ループなどの機能を含みます。

主な設計方針は「クラッシュ安全性」「発注の耐障害性」「本番とペーパートレードの分離」です。

---

## 主な機能一覧

- 環境設定ウィザード（.env の対話式作成／更新）
  - `python -m kabusys.config_setup`
- 設定検証 CLI（.env と config/*.yaml の事前チェック）
  - `python -m kabusys.validate_config [--strict]`
- Execution Engine（シグナル読み取り→発注、WebSocket push ドレイン、kill switch）
  - `python -m kabusys.run_execution`
- Monitoring Loop（定期的なシステム監視ポーリング）
  - `python -m kabusys.run_monitoring`
- Broker API 抽象（Protocol）とファクトリ
  - MockBrokerClient（テスト・ペーパートレード用）
  - KabuStationClient（kabuステーション REST API 実装）
- 注文状態管理（OrderState + OrderRecord）と SQLite 永続化（OrderRepository）
- リスク管理（3 段階ガード：Gate1/2/3、レート制限、サーキットブレーカー、ドローダウン監視）
- リコンシリエーション（起動時に OrderSent を突合して状態を回復）
- データユーティリティ（マーケットカレンダー管理、ニュース収集等）

---

## 要件

- Python 3.10 以上（型注釈に `X | Y` を使用しているため）
- 推奨パッケージ（機能に応じて必要）
  - duckdb
  - httpx
  - websocket-client
  - PyYAML（config/*.yaml の内容検証に使用。未インストールでも警告となりスキップされます）
  - defusedxml（RSS/XML パースの安全化）
- SQLite（Python 標準ライブラリで利用）
- OS による起動環境（kabuステーションを利用する場合、ローカルで kabu station アプリが必要）

インストール例（venv 内で）:
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb httpx websocket-client pyyaml defusedxml
```

---

## セットアップ手順

1. リポジトリをクローンして、仮想環境を作成・有効化する
2. 必要なパッケージをインストール（上記参照）
3. .env を作成する
   - 対話式ウィザードを利用:
     - `python -m kabusys.config_setup`
   - あるいは手動で `.env` をプロジェクトルートに配置（.env.example を参照して作成）
4. 設定を検証する:
   - `python -m kabusys.validate_config`
   - 警告も失敗扱いにしたい場合は `--strict` を付ける
5. DB ディレクトリ等が必要なら作成（多くは実行時に自動作成されます）
   - デフォルトの DB パス:
     - DuckDB: `data/kabusys.duckdb`
     - SQLite (監視): `data/monitoring.db`
     - Paper trading SQLite: `data/paper_trading.db`（PAPER_TRADING_SQLITE_PATH により上書き可）

---

## 環境変数（主要）

必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

任意／設定例:
- KABUSYS_ENV: execution モード（`development` / `paper_trading` / `live`、デフォルト `development`）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト `data/kabusys.duckdb`）
- SQLITE_PATH: 監視 DB（デフォルト `data/monitoring.db`）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード時の SQLite（デフォルト `data/paper_trading.db`）
- LOG_LEVEL: `DEBUG` / `INFO` / `WARNING` / `ERROR` / `CRITICAL`（デフォルト `INFO`）
- KABU_API_BASE_URL: kabu station API ベース URL（デフォルト `http://localhost:18080/kabusapi`）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE 通知用（本番時推奨）
- KILL_FLAG_PATH: kill flag のパス（デフォルト `data/kill.flag`）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアする（`1`でクリア、デフォルト `0`）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、デフォルト 60）

補足:
- 自動 .env ロード順序: OS 環境変数 > .env.local > .env
- 自動ロードを無効にするには: `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`

---

## 使い方

- 環境設定ウィザード（.env 作成／更新）
  - python -m kabusys.config_setup
  - 実行後、`.env` に設定が保存されます

- 設定検証
  - python -m kabusys.validate_config
  - オプション: `--strict`（警告も失敗扱いし exit(1)）

- 実行（監視）
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を変更可能（デフォルト 60 秒）
  - 監視は KABUSYS_ENV にかかわらず本番用 sqlite_path を使用します

- 実行（エンジン）
  - python -m kabusys.run_execution
  - KABUSYS_ENV が `paper_trading` の場合、MockBrokerClient を使用して `data/paper_trading.db` に記録します
  - 起動時に `data/stop_requested.flag` が存在すると起動を停止します
  - kill flag（KILL_FLAG_PATH）で起動拒否またはセッション中に kill switch を発動

---

## 実行モードの違い

- development
  - 開発用。MockBrokerClient を用いる想定（発注は実行されない）
- paper_trading
  - ペーパートレード。MockBrokerClient を用い、paper_trading 用 SQLite に記録して本番 DB と分離
- live
  - 本番。警告: KabuStationClient（実注文）を使う想定だが、現在 live のブローカークライアントは未実装箇所がありエラーになることがあります（コード内で NotImplementedError を投げる箇所あり）

注意: BrokerClientFactory により settings.is_paper または settings.is_dev で mock を生成し、settings.is_live で NotImplementedError を投げる設計です。

---

## 安全関連の挙動（重要）

- kill.flag（デフォルト: data/kill.flag）
  - 存在すると ExecutionEngine は起動を中止（KILL_FLAG_CLEAR_ON_START=1 の場合は起動時に削除して継続）
  - ExecutionEngine 内で kill_switch() が発動すると全 active 注文をキャンセルしループを停止します
- 停止フラグ（stop_requested.flag）
  - run_monitoring / run_execution はプロジェクトルートの `data/stop_requested.flag` を監視し、存在するとループを終了します
- Reconciliation（再起動時の復旧）
  - OrderSent の不確定状態を broker と照合して状態を回復します

---

## ディレクトリ構成（主要ファイル）

（プロジェクトルート）
- src/
  - kabusys/
    - __init__.py
    - config.py                   — 環境変数・.env 読み込みロジックおよび Settings
    - config_setup.py             — .env 対話式ウィザード
    - validate_config.py          — 起動前設定検証 CLI
    - run_execution.py            — ExecutionEngine 起動スクリプト
    - run_monitoring.py           — SystemMonitor ポーリングループ起動スクリプト
    - execution/
      - __init__.py
      - broker_api.py             — Broker API Protocol / モデル / ファクトリ
      - broker_factory.py         — Settings に基づく BrokerClient ファクトリ
      - kabu_client.py            — KabuStationClient 実装（httpx）
      - mock_client.py            — MockBrokerClient（テスト用）
      - order_record.py           — OrderState / OrderRecord（状態遷移ロジック）
      - order_repository.py       — SQLite 永続化層（orders テーブル）
      - order_manager.py          — OrderManager（発注フロー実装）
      - execution_engine.py       — ExecutionEngine（シグナル処理 + push ドレイン）
      - reconciler.py             — リコンシリエーション処理
      - risk_manager.py           — リスク管理（Gate 1/2/3）
    - data/
      - calendar_management.py    — マーケットカレンダー管理（DuckDB）
      - news_collector.py         — RSS ニュース収集（defusedxml 等で安全に処理）
      - (その他 data 関連モジュール)
    - monitoring/
      - monitoring_db.py         — 監視 DB 初期化 / 書き込みユーティリティ
      - system_monitor.py        — システム監視ロジック
    - utils/
      - logging_setup.py         — ログ設定ユーティリティ
      - process_priority.py      — プロセス優先度設定ユーティリティ
- config/
  - system_config.yaml
  - data_config.yaml
  - strategy_config.yaml
  - risk_config.yaml
  - execution_config.yaml
  - monitoring_config.yaml
  (※これらのファイルはプロジェクトで必要に応じて生成／編集。validate_config は存在チェックと PyYAML によるパース検証を行います。)

- data/
  - (デフォルトで DB や PID / flag ファイルを配置する場所)

---

## 追加メモ / 開発者向けポイント

- .env の自動読み込みは config.py で実装されています。テスト等で自動ロードを抑止するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- validate_config は PyYAML 未インストール時に YAML 内容検証をスキップします（警告表示）。
- ExecutionEngine のメインループはシグナル処理（8:50–9:10）→ push ドレイン（9:10–15:30）という時間帯ロジックをコード内で扱っています。テストでは該当メソッドを直接呼ぶことを推奨します。
- Live broker（実注文）に関しては実装が未完の箇所があります。実運用での使用は注意してください。

---

もし README に追加したい項目（例: サンプル .env.example、詳細な起動オプション、運用手順、テスト手順など）があれば教えてください。必要に応じて追記します。