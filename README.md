# KabuSys

日本株向け自動売買システム（KabuSys）のリポジトリ。  
本 README はリポジトリ内の既存モジュールをもとに、セットアップや起動方法、構成について日本語でまとめたものです。

> NOTE: この README はソースコード（src/kabusys）を参照して作成しています。

---

## プロジェクト概要

KabuSys は、kabuステーション（またはモック）を用いた日本株の自動売買プラットフォームです。  
主な機能は以下のとおり：

- シグナルに基づく発注エンジン（ExecutionEngine）
- 発注の状態管理（OrderRecord / OrderManager）
- 発注履歴の永続化（SQLite）
- 取引データの分析保存（DuckDB）
- 3段階のリスクガード（Gate1/2/3）
- 起動時のリコンシリエーション（Reconciler）
- システム監視ポーリング（SystemMonitor / monitoring）
- 環境設定ウィザード（.env 作成支援）
- 設定検証 CLI（.env と config/*.yaml の基本チェック）

設計上、ビジネスロジック（OrderRecord 等）は DB に依存しない形で分離されており、MockBrokerClient によるローカル検証が可能です。`KABUSYS_ENV=paper_trading` または `development` 時は MockBrokerClient を使用します。`live` 用ブローカーは未実装です（NotImplementedError）。

---

## 機能一覧（主なモジュールと役割）

- kabusys.config
  - 環境変数の自動読み込み（`.env` / `.env.local`）と Settings クラス
  - 必須変数取得ヘルパ（_require）
- kabusys.config_setup
  - 対話式ウィザードで `.env` を作成 / 更新
- kabusys.validate_config
  - 起動前に環境変数や config/*.yaml の存在および基本的な妥当性をチェックする CLI
- kabusys.execution
  - broker_api: クライアント Protocol / データモデル / ファクトリ
  - kabu_client: kabuステーション REST クライアント（httpx）
  - mock_client: テスト用 MockBrokerClient（fill_mode を制御可能）
  - order_record / order_repository / order_manager: 注文の状態管理と永続化
  - risk_manager: Gate1~3 による多層リスク制御
  - reconciler: 起動時リコンシリエーション
  - execution_engine: セッション実行（シグナル処理 + push ドレイン）
  - broker_factory: Settings に基づいてブローカーを生成
- kabusys.data
  - calendar_management: 営業日ロジック、J-Quants との連携想定
  - news_collector: RSS からのニュース収集（SSR フィルタ等の堅牢化）
- kabusys.monitoring
  - monitoring 用 DB 初期化 / SystemMonitor（run_monitoring 起動スクリプトから使用）
- スクリプト
  - run_execution.py: ExecutionEngine を起動するエントリポイント
  - run_monitoring.py: SystemMonitor のポーリングループ起動

---

## セットアップ手順（開発環境向け）

1. リポジトリをクローン
   ```bash
   git clone <repo-url>
   cd <repo>
   ```

2. Python 仮想環境を作成・有効化（推奨）
   ```bash
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows (PowerShell など)
   ```

3. 必要パッケージをインストール  
   以下はコード中で使用されている主要依存例です（プロジェクトに requirements.txt があればそちらを使用してください）。
   ```bash
   pip install duckdb httpx websocket-client defusedxml pyyaml
   ```
   - PyYAML: config/*.yaml の内容チェック（validate_config）で使用。無くても実行可能だが YAML 検証はスキップされます。
   - duckdb: シグナル / カレンダー等の分析用 DB
   - websocket-client, httpx: kabuステーションとの通信（実運用時）
   - defusedxml: RSS パースの安全化

4. .env の作成  
   対話式ウィザードを使うと簡便です：
   ```bash
   python -m kabusys.config_setup
   ```
   手動で作成する場合はプロジェクトルートに `.env` を置きます（.env は絶対に Git にコミットしないこと）。

5. 設定の検証（起動前チェック）
   ```bash
   python -m kabusys.validate_config
   # 警告も FAIL にしたい場合:
   python -m kabusys.validate_config --strict
   ```

---

## 環境変数（主なもの）

必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

任意 / 推奨（デフォルトあり）:
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
  - live は本番。`KABUSYS_ENV=live` の場合は注意メッセージが出ます（本コードベースでは live ブローカー未実装）。
- DUCKDB_PATH: デフォルト `data/kabusys.duckdb`
- SQLITE_PATH: デフォルト `data/monitoring.db`
- LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL（デフォルト: INFO）
- KABU_API_BASE_URL: kabu API の base URL（デフォルト: http://localhost:18080/kabusapi）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: 本番アラート用（任意）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（0/1、デフォルト 0）
- PAPER_FILL_MODE: paper_trading 用のモック約定モード（instant / partial / never / reject）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）

設定の自動読み込み:
- プロジェクトルート（.git または pyproject.toml を基準）から `.env` と `.env.local` を自動読み込みします。
- OS 環境変数は上書きされません（.env の上書き保護）。
- 自動読み込みを無効化する場合:
  ```bash
  export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  ```

---

## 使い方（起動例）

1. .env 作成（上記参照）

2. 設定検証
   ```bash
   python -m kabusys.validate_config
   # --strict をつけると警告もエラーとして扱い exit code 1
   python -m kabusys.validate_config --strict
   ```

3. ExecutionEngine の起動（本番相当のフローを実行）
   - 通常、paper_trading では MockBrokerClient を使い、モック DB（PAPER_TRADING_SQLITE_PATH）に記録されます。
   - `KABUSYS_ENV=live` は未実装（例外が出ます）。
   ```bash
   python -m kabusys.run_execution
   ```

4. Monitoring の起動（監視ループ）
   ```bash
   python -m kabusys.run_monitoring
   # MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更可能（秒）
   export MONITOR_POLL_INTERVAL=30
   python -m kabusys.run_monitoring
   ```

5. ウィザードで .env を作り直す
   ```bash
   python -m kabusys.config_setup
   ```

注意点:
- 実運用で kill / stop 制御に使うファイル:
  - `data/kill.flag`（KILL_FLAG_PATH デフォルト）: 存在すると ExecutionEngine は起動を拒否するか kill switch を発動します。
  - `data/stop_requested.flag`: run_monitoring / run_execution のループで検出すると安全に停止します。
- PID ファイル: `PID_FILE_PATH`（デフォルト `data/execution.pid`）に起動 PID を書きます。

---

## ディレクトリ構成（抜粋）

以下はソース内の主要ファイルとディレクトリ（src/kabusys）です。実際のリポジトリではこれをトップレベルに置いてパッケージ化します。

- src/
  - kabusys/
    - __init__.py
    - config.py                    -- 環境変数 / Settings
    - config_setup.py              -- .env 対話式ウィザード
    - validate_config.py           -- 設定検証 CLI
    - run_execution.py             -- ExecutionEngine 起動スクリプト
    - run_monitoring.py            -- SystemMonitor 起動スクリプト
    - data/
      - calendar_management.py
      - news_collector.py
      - jquants_client.py?         -- J-Quants 連携を想定するクライアント（参照あり）
    - execution/
      - broker_api.py
      - broker_factory.py
      - kabu_client.py
      - mock_client.py
      - order_record.py
      - order_repository.py
      - order_manager.py
      - execution_engine.py
      - reconciler.py
      - risk_manager.py
      - ...（他、order_* 等）
    - monitoring/
      - monitoring_db.py
      - system_monitor.py
    - utils/
      - logging_setup.py
      - process_priority.py
    - strategy/                     -- 戦略関連（パッケージ公開対象）
    - monitoring/                   -- 監視関連（パッケージ公開対象）
    - data/                         -- データ関連（パッケージ公開対象）

（上記はコードベースから抜粋した代表的ファイル群です。実際のツリーはリポジトリを参照してください。）

---

## 依存関係（主なライブラリ）

- Python 標準ライブラリ: logging, sqlite3, threading, datetime, pathlib, json, socket, ipaddress, urllib, etc.
- サードパーティ:
  - duckdb
  - httpx
  - websocket-client
  - defusedxml
  - PyYAML（任意、config ファイル検証用）
  - （必要に応じて）requests 等

requirements.txt がある場合はそちらを使用してください。

---

## 動作・設計上の注意

- KABUSYS_ENV=live のブローカークライアントは未実装です。実運用を行う際は実装と十分なテストが必要です。
- .env は機密情報を含むため、絶対にリポジトリにコミットしないでください（config_setup も README 内に警告あり）。
- OrderManager の発注フローはクラッシュ耐性（2相永続化）を考慮した実装になっています。OrderSent のまま残る注文は list_uncertain / Reconciler で復旧対象となります。
- news_collector 等は SSRF 対策や受信サイズ上限などセキュリティ面を考慮していますが、外部に公開する場合は追加のハードニングが必要です。
- monitoring は常に本番用 sqlite_path を参照する仕様（run_monitoring の説明参照）。

---

この README はコードの主要点をまとめたものです。さらに詳しい仕様（API, DB スキーマ, DataPlatform.md 等）が別途あればそちらも参照してください。必要であれば README を拡張して開発フローやテスト手順、CI 設定例なども追記できます。