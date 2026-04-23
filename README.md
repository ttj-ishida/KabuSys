# KabuSys

日本株自動売買システム（KabuSys） — 軽量な発注エンジン・監視・データ整備を含むサンプル実装です。  
このリポジトリは実運用を想定した設計方針（リコンシリエーション、3段階リスクガード、PID/Kill フラグ管理、DB 分離など）を反映したモジュール群を提供します。

## 主な特徴
- シグナル駆動の発注エンジン（ExecutionEngine）
  - シグナル読取 → Gate1/2 のリスクチェック → 発注 → push/drain 処理
- Broker 抽象化（BrokerAPIProtocol）
  - MockBrokerClient によるペーパートレード／ローカルテスト対応
  - KabuStationClient（kabu-station REST API）を用いた実装（将来的に本番対応）
- 注文状態管理
  - OrderRecord（状態遷移／検証ロジック）
  - SQLite ベースの永続化（OrderRepository）
  - 起動時の Reconciler によるクラッシュ後復旧（OrderSent の照合）
- リスク管理（RiskManager）
  - Gate1: 余力／重複／ポジション上限
  - Gate2: レート制限・サーキットブレーカー
  - Gate3: ドローダウン監視（kill switch）
- 監視プロセス（SystemMonitor）と run_monitoring スクリプト
- 環境設定ウィザード（config_setup）と起動前検証ツール（validate_config）
- データ処理モジュール（マーケットカレンダー管理、ニュース収集など）
- DuckDB（分析用）と SQLite（監視 / 注文履歴）を利用したデータ層分離

---

## 機能一覧
- 環境設定ウィザード（.env の対話式生成 / 更新）
- 起動前設定検証（必須環境変数・YAML 設定ファイルの整合性チェック）
- ExecutionEngine（シグナル読み取り → 発注 → push 処理）
- Mock ブローカー（テスト用、fill_mode により instant/partial/never/reject を再現）
- Reconciler（OrderSent など不確定注文の照合、自動同期）
- OrderRepository（SQLite による永続化、active / uncertain リスト取得など）
- RiskManager（多層リスクガード、サーキットブレーカー、レート制限）
- 監視ループ（SystemMonitor を定期実行、停止フラグ対応）
- データモジュール（market_calendar 管理、RSS ニュース収集）

---

## セットアップ手順（開発 / テスト向け）
1. Python 環境を準備
   - Python 3.8+ を推奨（本コードベースでは型ヒントや一部ライブラリを利用）
2. 依存パッケージをインストール（例）
   - 必要パッケージの例:
     - duckdb
     - httpx
     - websocket-client
     - PyYAML（validate_config の YAML チェック用、なくても動作するが検証が省略されます）
     - defusedxml
   - インストール例:
     ```
     pip install duckdb httpx websocket-client PyYAML defusedxml
     ```
   - （requirements.txt がある場合は `pip install -r requirements.txt`）
3. プロジェクトルートに移動して .env を作成
   - 対話式ウィザードを利用:
     ```
     python -m kabusys.config_setup
     ```
   - 手動で作成する場合はプロジェクトルートに `.env` を置く（下記の最小例を参照）
4. 設定の検証
   ```
   python -m kabusys.validate_config
   python -m kabusys.validate_config --strict  # 警告も FAIL 扱い
   ```
5. DB 初期化・確認（Execution / Monitoring が起動時に必要に応じてテーブルを作ります）

---

## 環境変数（主なもの）
優先順位: OS 環境変数 > .env.local > .env  
自動ロードはプロジェクトルートの検出に基づき行われます。無効化する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

任意（よく使うもの）:
- KABUSYS_ENV: execution 環境（development / paper_trading / live）
  - paper_trading / development → MockBrokerClient を使用
  - live → 本番（現状 Live client は未実装で NotImplementedError）
- DUCKDB_PATH: 分析用 DB（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（0/1）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: 本番でのアラート通知

ペーパートレード設定:
- PAPER_FILL_MODE: instant / partial / never / reject

監視用:
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）

その他:
- PID_FILE_PATH, KILL_FLAG_PATH などは Settings でデフォルト値が割り当てられます。

最小 .env の例:
```
JQUANTS_REFRESH_TOKEN=your_refresh_token_here
KABU_API_PASSWORD=your_kabu_api_password_here
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
LOG_LEVEL=INFO
KILL_FLAG_CLEAR_ON_START=0
```

---

## 使い方（主要コマンド）
- 環境設定ウィザード（.env 作成 / 更新）
  ```
  python -m kabusys.config_setup
  ```

- 設定検証（起動前チェック）
  ```
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- 実行エンジン起動（Execution）
  - 開発 / ペーパートレードでは MockBrokerClient が使われます（.env の KABUSYS_ENV に依存）
  ```
  python -m kabusys.run_execution
  ```

- 監視ループ起動（SystemMonitor）
  ```
  python -m kabusys.run_monitoring
  ```
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更可能（秒）

基本的な起動手順（例: ペーパートレードで動かす場合）
1. .env を作成して KABUSYS_ENV=paper_trading を設定
2. 必要パッケージをインストール
3. 設定検証を実行
4. `python -m kabusys.run_execution` を起動

停止制御:
- プロジェクトルートの `data/stop_requested.flag` を配置すると監視 / 実行ループは安全に停止します。
- `data/kill.flag` が存在すると ExecutionEngine は基本的に起動を拒否します。`KILL_FLAG_CLEAR_ON_START=1` を設定している場合は起動時にクリアされます（注意：本番では推奨されません）。

ログ:
- 各プロセスは logging 設定を行います。LOG_LEVEL を環境変数で変更できます。

---

## ディレクトリ構成（主要ファイル）
以下は src/kabusys 以下の主要モジュールと簡単な説明です。

- src/kabusys/__init__.py
  - パッケージメタ情報（__version__ など）
- src/kabusys/config.py
  - 環境変数の自動読み込み（.env / .env.local）
  - Settings クラス（アプリ設定の取得）
- src/kabusys/config_setup.py
  - .env 対話式ウィザード（CLI）
- src/kabusys/validate_config.py
  - .env と config/*.yaml の起動前検証ツール（CLI）
- src/kabusys/run_execution.py
  - ExecutionEngine を起動するスクリプト
- src/kabusys/run_monitoring.py
  - SystemMonitor ポーリングループを起動するスクリプト
- src/kabusys/execution/
  - broker_api.py           — BrokerAPI のデータモデル・Protocol・ファクトリ
  - broker_factory.py       — Settings に応じた BrokerClient 生成
  - kabu_client.py          — kabu-station REST API クライアント
  - mock_client.py          — テスト用 MockBrokerClient
  - order_record.py         — 注文状態マシン（状態遷移ロジック）
  - order_repository.py     — SQLite 永続化層（orders テーブル）
  - order_manager.py        — DB + broker を結合した発注 API（create/send/sync/cancel）
  - execution_engine.py     — 発注エンジン（シグナル処理 + WebSocket ドレイン）
  - reconciler.py           — 再起動時のリコンシリエーション / ポジション照合
  - risk_manager.py         — Gate1/2/3 のリスクチェック
- src/kabusys/data/
  - calendar_management.py  — マーケットカレンダー処理（DuckDB）
  - news_collector.py       — RSS ニュース収集（前処理・SSR F対策 等）
- src/kabusys/monitoring/
  - monitoring_db.py        — 監視 DB 初期化 / ロギングヘルパ
  - system_monitor.py       — システム監視ロジック（CPU/Memory/Disk 等）
- src/kabusys/utils/
  - logging_setup.py        — 共通ログ設定
  - process_priority.py     — プロセス優先度設定ユーティリティ

（上記は主要ファイルの抜粋です。詳しい実装は各ソースファイルをご参照ください。）

---

## 開発上の注意
- 本実装は設計方針・教育目的で作成されています。本番運用をそのまま行う前に十分な検証と監査を行ってください。
- Live ブローカー（実際の kabu-station を用いた運用）は慎重に扱ってください。現状 factory は Live client の呼び出しで NotImplementedError を投げます。
- .env ファイルは決してリポジトリにコミットしないでください（config_setup でもその旨を明記しています）。
- validate_config は PyYAML がインストールされている場合のみ config/*.yaml の中身をパースして検証します。未インストール時は YAML の内容検証をスキップし警告を出します。

---

必要があれば、README に含めるサンプル .env.example、起動スクリプトの systemd ユニット例、またはユニットテストの実行方法などを追加で作成します。どの情報を優先して追記しますか？