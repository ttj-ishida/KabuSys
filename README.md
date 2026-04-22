# KabuSys

日本株自動売買用のミニマルな実装サンプル (KabuSys)。  
このリポジトリは発注エンジン、ブローカー API 抽象、リスクガード、監視/リコンシリエーション、データ処理ユーティリティなどを含みます。

バージョン: 0.1.0

---

## 概要

KabuSys は以下の目的を持つコンポーネント群を提供します。

- 発注ワークフロー（Signal → Order 作成 → broker 送信 → 同期）
- ブローカークライアント抽象（実装: Mock / kabu station クライアント）
- 発注状態管理（OrderState, OrderRecord）
- 永続化（SQLite: orders テーブル）
- 実行エンジン（ExecutionEngine）と監視ループ（SystemMonitor）
- リスク管理（Gate1/Gate2/Gate3 の三段階防護）
- 環境設定ウィザード（.env 作成補助）と設定検証 CLI

設計方針として、DB との整合性（永続化順序・リコンシリエーション）や発注のクラッシュ耐性を重視しています。開発/ペーパートレード環境向けに Mock ブローカーを用意しており、本番接続は将来的な拡張を想定しています。

---

## 機能一覧

- .env 自動読み込み（プロジェクトルートの .env / .env.local、OS 環境変数優先）
- 対話式 .env 作成ウィザード（python -m kabusys.config_setup）
- 起動前設定検証ツール（python -m kabusys.validate_config）
  - 必須環境変数チェック（JQUANTS_REFRESH_TOKEN / KABU_API_PASSWORD）
  - KABUSYS_ENV / LOG_LEVEL 等の妥当性検査
  - config/*.yaml 存在・YAML パースチェック（PyYAML があればパースも実施）
  - --strict モードで警告も FAIL 扱い
- ExecutionEngine
  - シグナル読み込み（DuckDB）
  - Gate1/Gate2/Gate3 によるリスク検査
  - OrderManager を介した発注、送信、同期、キャンセル
  - WebSocket push (kabu station) による order 状態同期
  - kill.flag による安全停止
- Monitoring（run_monitoring）
  - 定周期ポーリングでシステム監視イベントを記録
  - monitoring 用の SQLite / DuckDB 接続
- ブローカー実装
  - MockBrokerClient（テスト用、fill_mode: instant/partial/never/reject）
  - KabuStationClient（kabu station REST/WebSocket クライアント）
- リコンシリエーション（Reconciler）
  - OrderSent の不確定注文を broker と突合して復旧
  - ブローカーポジションとローカル推定ポジションの差分検出
- データユーティリティ
  - カレンダー管理（next_trading_day 等）
  - ニュース収集（RSS 取得・前処理・保存） — SSRF/サイズ/XML インジェクション対策済みロジック

---

## 前提要件

- Python 3.10+
  - 型注釈に X | Y 形式と list[str] などを使用しているため 3.10 以上を推奨します
- 推奨 Python パッケージ（主要機能を使う場合）:
  - duckdb
  - httpx
  - websocket-client
  - PyYAML（config/*.yaml の内容検証に利用）
  - defusedxml（RSS パースで使用）
- 標準ライブラリ: sqlite3, logging 等

インストール例（venv 内で）:
```
pip install duckdb httpx websocket-client PyYAML defusedxml
```

（requirements.txt があればそちらを用意して pip install -r でインストールしてください）

---

## セットアップ手順（簡易）

1. リポジトリを取得
   ```
   git clone <repo-url>
   cd <repo>
   ```

2. Python 環境を用意（推奨: venv）
   ```
   python -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate
   pip install --upgrade pip
   pip install duckdb httpx websocket-client PyYAML defusedxml
   ```

3. 環境変数ファイルを用意
   - 対話式ウィザードで作成:
     ```
     python -m kabusys.config_setup
     ```
     プロンプトに従って入力するとプロジェクトルートの `.env` に保存されます。

   - 主要な必須環境変数:
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
   - 代表的な任意環境変数:
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（デフォルト: data/monitoring.db）
     - LOG_LEVEL（DEBUG|INFO|WARNING|ERROR|CRITICAL）
     - KABU_API_BASE_URL（kabu station URL）
     - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID（本番アラート用）

4. 設定検証（起動前に推奨）
   ```
   python -m kabusys.validate_config
   # 警告を FAIL 扱いにする場合:
   python -m kabusys.validate_config --strict
   ```
   PyYAML がインストールされていると config/*.yaml のパース検証も行います。

5. DB 初期化
   - orders テーブル等は Execution 起動時や init ルーチンで自動作成されます（init_orders_db / init_monitoring_db を呼び出します）。
   - 必要に応じて data/ ディレクトリを作成:
     ```
     mkdir -p data
     ```

---

## 使い方（主要 CLI/モジュール）

- 環境設定ウィザード（.env 作成/更新）
  ```
  python -m kabusys.config_setup
  ```

- 設定検証（.env と config/*.yaml のチェック）
  ```
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- 実行エンジン（ExecutionEngine）を起動
  - 開発 / ペーパートレードモード（Mock ブローカーを利用）:
    - KABUSYS_ENV を `development` または `paper_trading` に設定
    ```
    python -m kabusys.run_execution
    ```
    - paper_trading の場合、paper 用 SQLite DB（デフォルト `data/paper_trading.db`）を使用
    - 起動時に data/execution.pid が書かれます
    - 停止は data/stop_requested.flag を作成するか、プロセスに SIGINT を送る

- 監視ループを起動
  ```
  python -m kabusys.run_monitoring
  ```
  - 環境に関わらず本番の sqlite_path を使用して監視 DB に記録します
  - 簡易停止フラグ: data/stop_requested.flag を作成するとループが終了します
  - ポーリング間隔を変更する場合:
    ```
    export MONITOR_POLL_INTERVAL=30  # 秒
    ```

- デバッグ / テスト用
  - MockBrokerClient の fill_mode を環境変数 PAPER_FILL_MODE で切り替え可能（Settings.paper_fill_mode）
    - instant / partial / never / reject

---

## 停止・保護に関する注意点

- kill.flag（KILL_FLAG_PATH, デフォルト data/kill.flag）
  - ExecutionEngine は起動前に kill.flag の存在をチェックします。
  - KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に自動でクリアして起動します（本番では推奨されません）。
- stop_requested.flag（data/stop_requested.flag）
  - run_execution / run_monitoring のループ継続を止めるための簡易フラグです。
- PID ファイル
  - ExecutionEngine は起動時に PID を data/execution.pid 等に書きます（設定可能）。

---

## 主要な環境変数（抜粋）

- 必須
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD

- 任意 / 推奨
  - KABUSYS_ENV: development | paper_trading | live
  - DUCKDB_PATH: data/kabusys.duckdb
  - SQLITE_PATH: data/monitoring.db
  - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
  - LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL
  - KABU_API_BASE_URL: kabu station API ベース URL
  - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: 本番アラート用
  - MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒）
  - KILL_FLAG_CLEAR_ON_START: 0/1

例（.env の一部）:
```
JQUANTS_REFRESH_TOKEN=your_token_here
KABU_API_PASSWORD=your_kabu_password
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
LOG_LEVEL=INFO
```

---

## ディレクトリ構成（抜粋）

プロジェクトルート（src 以下がパッケージ）:

- src/kabusys/
  - __init__.py
  - config.py
    - Settings: 環境変数読み取り・自動ロードロジック
  - config_setup.py
    - 対話式 .env ウィザード
  - validate_config.py
    - 起動前設定検証 CLI
  - run_execution.py
    - ExecutionEngine 起動ラッパー
  - run_monitoring.py
    - SystemMonitor ポーリングループ起動
  - execution/ (発注関連)
    - broker_api.py         — BrokerAPIProtocol、データモデル、ファクトリ
    - broker_factory.py     — Settings に基づくブローカー生成
    - kabu_client.py        — kabu station REST/WebSocket 実装
    - mock_client.py        — テスト向け MockBrokerClient
    - order_record.py       — OrderRecord（状態遷移ロジック）
    - order_repository.py   — SQLite 永続化（orders テーブル）
    - order_manager.py      — 外向け発注 API（create/send/sync/cancel）
    - execution_engine.py   — ExecutionEngine（シグナル処理・push ドレイン）
    - reconciler.py         — 起動時リコンシリエーション
    - risk_manager.py       — Gate1/2/3 リスクガード
    - ...（その他 execution 周辺）
  - data/ (データ処理)
    - calendar_management.py — 市場カレンダー管理
    - news_collector.py      — RSS ニュース収集（前処理・保存ロジック）
    - jquants_client.py      — （参照される想定、J-Quants 絡み）
  - monitoring/
    - monitoring_db.py      — 監視用 DB 初期化 / ログ関数（run_monitoring で使用）
    - system_monitor.py     — 実際の監視ロジック
  - utils/
    - logging_setup.py      — ログ初期化ユーティリティ
    - process_priority.py   — プロセス優先度設定ユーティリティ

（実際のリポジトリには他にも補助モジュールやスクリプトが含まれる可能性があります）

---

## 実装上のポイント / 注意点

- 実行フローはクラッシュ安全性を意識して設計されています。OrderManager.send_order は OrderSent を先に永続化した上で broker 呼び出しを行い、broker_order_id の永続化と状態遷移を二段階で行います。これにより再起動時に Reconciler が不確定注文を復旧できます。
- Paper Trading と本番は DB を分離する（paper_trading 用 SQLite を使用）ことで誤操作による混入を防ぎます。
- カレンダー関連は DuckDB の market_calendar を優先し、未登録日は曜日ベースのフォールバックを行います。
- RSS 収集は SSRF や XML インジェクション対策（defusedxml を使用）を踏まえた実装方針です。
- KabuStationClient は httpx（同期）と websocket-client を使用。トークン管理は内部で行い、401 時は自動再取得してリトライします。
- 本番（KABUSYS_ENV=live）では LINE 通知等の設定確認が重要です。validate_config が警告を出します。

---

## トラブルシュート

- validate_config でエラーが出る場合はまず .env の必須キー（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD）を確認してください。
- start/stop フラグ関連:
  - 起動しない場合は data/kill.flag の存在を確認。KILL_FLAG_CLEAR_ON_START=1 でクリア可（本番では注意）。
  - 監視・実行を止めたい場合は data/stop_requested.flag を作成してください。
- YAML のパース検証を有効にするには PyYAML をインストールしてください（pip install PyYAML）。

---

この README は主要な利用手順と設計上の注意点をまとめたものです。より詳細な API 仕様や運用手順は各モジュールの docstring / コメントを参照してください。必要であれば起動例やデプロイ手順、CI での検証フローなども追記できます。