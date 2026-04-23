# KabuSys

日本株自動売買システム（モジュール群）  
このリポジトリは、シグナルに基づく発注エンジン、リコンシリエーション、監視、データ収集などを含む自動売買プラットフォームのコア部分です。実運用（live）・ペーパートレード（paper_trading）・開発（development）を想定した設計になっています。

注意: 本リポジトリは教育 / 内部用途を想定しています。本番運用する場合は必ずコードと設定を十分にレビューしてください。

## 主な特徴（機能一覧）
- 環境設定ウィザード（.env 生成）: kabusys.config_setup
- 設定検証 CLI: kabusys.validate_config（.env と config/*.yaml のチェック）
- 発注エンジン（ExecutionEngine）
  - Signal Queue Pull 型の発注フロー
  - 3 段階のリスクガード（Gate1/2/3）
  - 注文状態マシン（OrderRecord / OrderManager / OrderRepository）
  - リコンシリエーション（起動時の自動復旧）
- ブローカークライアント抽象化
  - MockBrokerClient（ペーパートレード / テスト用）
  - KabuStationClient（kabuステーション REST 実装）
- 監視プロセス（SystemMonitor）を定期実行する run_monitoring
- データ処理モジュール（マーケットカレンダー、ニュース収集など）
- DuckDB / SQLite を用いたデータ保存・監視

## 必要要件
- Python 3.10 以上（型注釈で `X | None` 等を使用しているため）
- 推奨: 仮想環境（venv / poetry / pipx 等）

主な外部依存パッケージ（プロジェクトに requirements.txt が無い場合は下記をインストールしてください）:
- duckdb
- httpx
- websocket-client
- defusedxml
- pyyaml (任意: validate_config で YAML パース検証を行う場合)
- その他、実行環境に応じて必要なパッケージ

例:
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb httpx websocket-client defusedxml pyyaml
```

## 環境変数
必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

任意（一般的に設定されるもの）:
- KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
- DUCKDB_PATH — デフォルト: data/kabusys.duckdb
- SQLITE_PATH — デフォルト: data/monitoring.db
- LOG_LEVEL — DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）
- KABU_API_BASE_URL — kabu station API のベース URL
- LINE_CHANNEL_ACCESS_TOKEN — LINE 通知用（本番では設定推奨）
- LINE_USER_ID — LINE 通知先（本番では設定推奨）
- PAPER_FILL_MODE — paper_trading 時のモック約定モード（instant|partial|never|reject）
- PAPER_TRADING_SQLITE_PATH — paper_trading 用 SQLite（デフォルト: data/paper_trading.db）
- PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START（起動時の Kill Switch 制御）

設定ファイル（config/*.yaml）も一部利用されます（生成スクリプトあり）。

## セットアップ手順（簡易）
1. リポジトリをクローンして仮想環境を用意
   ```
   git clone <repo-url>
   cd <repo>
   python -m venv .venv
   source .venv/bin/activate
   pip install duckdb httpx websocket-client defusedxml pyyaml
   ```
2. 環境ファイルの作成（ウィザード推奨）
   ```
   python -m kabusys.config_setup
   ```
   - 対話形式で .env を作成できます。
   - 既存 .env があれば読み込んで編集できます。
3. 設定検証（任意）
   ```
   python -m kabusys.validate_config
   python -m kabusys.validate_config --strict  # 警告も FAIL 扱い
   ```
   - PyYAML が未インストールの場合、YAML パース検証はスキップされます。
4. 実行に必要な DB フォルダ（data/ など）を作成する
   ```
   mkdir -p data
   ```
   実行スクリプトは起動時に親ディレクトリを自動作成することもありますが、権限等に注意してください。

## 使い方（主要スクリプト）
- 環境ウィザード（.env の作成／更新）
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config          # 警告は表示のみ
  python -m kabusys.validate_config --strict # 警告があると exit(1)
  ```

- 監視プロセス起動（SystemMonitor ポーリング）
  ```
  python -m kabusys.run_monitoring
  ```
  - 環境変数 `MONITOR_POLL_INTERVAL`（秒）でポーリング間隔を上書きできます（デフォルト 60 秒）。
  - 監視は KABUSYS_ENV にかかわらず本番 sqlite_path を使います。

- 実行エンジン起動（ExecutionEngine）
  ```
  python -m kabusys.run_execution
  ```
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使い、paper_trading 用 SQLite（デフォルト: data/paper_trading.db）を使用して本番 DB と分離します。
  - KABUSYS_ENV=live の live ブローカークライアントは現在未実装で、BrokerClientFactory は NotImplementedError を投げます（本番を使う場合は実装が必要です）。

- 停止フラグ
  - プロジェクトルートの `data/stop_requested.flag` を作成するとループが検知して終了します（監視・実行スクリプト両方）。
  - `KILL_FLAG_PATH`（デフォルト: data/kill.flag）を使った kill switch により発注ループを中断・全注文キャンセルが可能です。`KILL_FLAG_CLEAR_ON_START=1` を設定すると起動時に kill.flag を自動クリアします（本番では推奨されません）。

## 主要コンポーネントと責務（簡易説明）
- kabusys.config
  - .env の自動読み込み（.env / .env.local）と Settings クラスにより環境値を提供
- kabusys.config_setup
  - .env を対話式に生成・更新するウィザード
- kabusys.validate_config
  - 環境変数や config/*.yaml の存在・妥当性をチェックする CLI
- kabusys.run_execution
  - ExecutionEngine の起動スクリプト（セッション管理、PID ファイル、stop flag の監視）
- kabusys.execution
  - ブローカークライアント（KabuStationClient / MockBrokerClient）
  - Order の状態管理（OrderRecord, OrderRepository）
  - OrderManager（発注フロー）
  - ExecutionEngine（シグナル処理、WebSocket push 処理、kill switch、monitoring DB 書込）
  - Reconciler（再起動時の自動復旧）
  - RiskManager（Gate1/2/3 の実装）
- kabusys.monitoring
  - 監視関連（SystemMonitor, monitoring DB 初期化）
- kabusys.data
  - マーケットカレンダー、ニュース収集、J-Quants API 周りのユーティリティ

## ディレクトリ構成
（主要ファイルのみ抜粋）

- src/
  - kabusys/
    - __init__.py
    - config.py                  — 環境設定読み込み / Settings
    - config_setup.py            — .env 対話式ウィザード
    - validate_config.py         — 設定検証 CLI
    - run_execution.py           — 実行エンジン起動スクリプト
    - run_monitoring.py          — 監視プロセス起動スクリプト
    - execution/
      - broker_api.py            — Broker API のデータモデル・Protocol・ファクトリ
      - kabu_client.py           — kabuステーション実装（HTTP/WebSocket）
      - mock_client.py           — モックブローカークライアント（テスト用）
      - broker_factory.py        — Settings に基づくクライアント生成
      - order_record.py          — 注文状態マシンのドメインモデル
      - order_repository.py      — SQLite 永続化層（orders テーブル）
      - order_manager.py         — 発注ワークフロー（DB + ブローカ）
      - execution_engine.py      — 発注エンジン（シグナル処理 / push ドレイン）
      - reconciler.py            — 起動時リコンシリエーション
      - risk_manager.py          — 3 段階リスクガード
      - ... (その他)
    - data/
      - calendar_management.py   — マーケットカレンダー管理（DuckDB）
      - news_collector.py        — RSS ニュース収集（DefusedXML 等）
      - ... (J-Quants クライアント等)
    - monitoring/
      - monitoring_db.py         — 監視 DB 初期化・ログテーブル等
      - system_monitor.py        — システム監視ロジック
    - utils/
      - logging_setup.py         — ロギング初期化
      - process_priority.py      — プロセス優先度設定ユーティリティ

## 注意事項 / 運用メモ
- KABUSYS_ENV=live 用の実ブローカークライアントは一部未実装（BrokerClientFactory は NotImplementedError を投げます）。実運用を行うには実装と十分な検証が必要です。
- .env は機密情報（API トークン・パスワード等）を含むため絶対に Git 等へコミットしないでください。config_setup の注意書きにも同様の記述があります。
- 本番環境での kill_flag 自動クリア（KILL_FLAG_CLEAR_ON_START=1）は危険です。デフォルト 0 を推奨します。
- validate_config を起動前チェックに組み込むことで、よくある設定ミスを検出できます。
- DuckDB / SQLite ファイルはデフォルトで data/ 配下に作成されます。適切なバックアップ・ディスク容量管理を行ってください。

---

README に載せてほしい追加情報（例: 実行例、詳しい設定項目、CI の使い方、ライセンス等）があれば教えてください。必要に応じて README を拡張します。