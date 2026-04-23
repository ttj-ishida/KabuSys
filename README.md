# KabuSys

日本株向け自動売買システムのコアモジュール群（ライブラリ＋起動スクリプト群）。

このリポジトリは、発注エンジン（ExecutionEngine）、発注管理（OrderManager / OrderRepository）、ブローカークライアント（実運用 / モック）、リスクガード、監視ループ、カレンダー・ニュース取得などの基本機能を含みます。開発・ペーパートレード・本番（live）環境に対応する設計です。

注意: 本 README はソースツリー内の実装ファイルに基づいています。実運用での接続先（kabuステーション等）や秘密情報は .env にて管理してください。

---

## 主要機能

- 環境設定管理
  - .env / .env.local の自動読み込み（プロジェクトルート検出）
  - 対話式ウィザードで .env を生成・更新（kabusys.config_setup）
  - 設定検証 CLI（必須環境変数・YAML 設定ファイル・本番ガード等）（kabusys.validate_config）
- 実行エンジン
  - Signal Queue Pull 型の発注エンジン（ExecutionEngine）
  - 発注の2相永続化やリコンサイルを考慮した注文ライフサイクル管理
  - OrderRecord（状態遷移ロジック）、OrderRepository（SQLite 永続化）
- ブローカークライアント層
  - BrokerAPIProtocol に準拠したクライアント設計
  - MockBrokerClient: テスト／開発用のモック（fill_mode 指定可）
  - KabuStationClient: kabuステーション REST / WebSocket 実装（httpx / websocket-client）
  - create_broker_api ファクトリで環境に応じて生成
- リスク管理
  - Gate 1 (シグナルレベル): 余力 / 重複 / ポジション上限
  - Gate 2 (エグゼキューションレベル): レート制限（トークンバケツ）・サーキットブレーカー
  - Gate 3 (メトリクスレベル): ドローダウン監視（キルスイッチ）
- リコンシリエーション
  - 起動時に OrderSent の未確定注文をブローカーと突合して状態を復旧
  - ブローカーポジションとローカル推定ポジションの差分検出
- 監視
  - SystemMonitor のポーリングループ（run_monitoring）
  - 監視用 DB（SQLite）／監視ログ保存
- データ周り
  - マーケットカレンダー管理（DuckDB ベース）
  - ニュース収集（RSS）モジュール（XML の安全なパースや SSRF 対策などを考慮）

---

## 必要な環境変数（主要）

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants API 用リフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API パスワード

任意・上書き可:
- KABUSYS_ENV — 実行環境（development / paper_trading / live）デフォルト: development
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視 DB（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- KABU_API_BASE_URL — kabu station のベース URL（デフォルト: http://localhost:18080/kabusapi）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID — 本番時の通知先（任意）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（0/1、デフォルト 0）

設定検証時に詳細は `python -m kabusys.validate_config` で確認できます。

---

## セットアップ手順（開発向け）

1. Python 環境を準備（推奨: venv）
   ```
   python -m venv .venv
   source .venv/bin/activate   # Linux/Mac
   .venv\Scripts\activate      # Windows
   ```

2. 依存パッケージをインストール
   - ソースには requirements.txt は含まれていない想定のため、少なくとも以下をインストールしてください:
     ```
     pip install duckdb httpx websocket-client PyYAML defusedxml
     ```
   - 実行環境に応じて追加パッケージが必要になる場合があります（例: sqlite3 は標準ライブラリ）。

3. .env を作成
   - 対話式で作成する:
     ```
     python -m kabusys.config_setup
     ```
   - または手動でプロジェクトルートに `.env` を作成（最小例）:
     ```
     JQUANTS_REFRESH_TOKEN=your_jquants_token_here
     KABU_API_PASSWORD=your_kabu_api_password_here
     KABUSYS_ENV=development
     DUCKDB_PATH=data/kabusys.duckdb
     SQLITE_PATH=data/monitoring.db
     LOG_LEVEL=INFO
     KILL_FLAG_CLEAR_ON_START=0
     ```

4. 設定の検証（任意）
   ```
   python -m kabusys.validate_config
   # 警告を FAIL 扱いにする場合
   python -m kabusys.validate_config --strict
   ```

5. DB 初期化等
   - 実行スクリプトやユーティリティで必要テーブルを作成してください（Order DB 初期化等は起動時に自動で行うことが多いです）。各コンポーネントの init メソッドを利用します（例: init_monitoring_db、init_orders_db）。

---

## 実行方法（例）

- 監視ループを起動:
  ```
  python -m kabusys.run_monitoring
  # ポーリング間隔を環境変数で上書き
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  ```

- 実行エンジン（発注）を起動:
  ```
  python -m kabusys.run_execution
  ```
  - KABUSYS_ENV が `paper_trading` の場合は MockBrokerClient が使用され、paper_trading 用の別 DB に記録されます。
  - `live` モードの実ブローカークライアントは未実装（現在は NotImplementedError）。

- 環境設定ウィザード:
  ```
  python -m kabusys.config_setup
  ```

- 設定検証:
  ```
  python -m kabusys.validate_config [--strict]
  ```

---

## 主要モジュール（概要）

- kabusys.config
  - Settings クラス、.env 自動ロード、環境取得ユーティリティ
- kabusys.config_setup
  - .env を対話的に生成/更新する CLI
- kabusys.validate_config
  - .env と config/*.yaml の事前チェック用 CLI
- kabusys.run_execution
  - ExecutionEngine の起動スクリプト（セッション管理・PID/kill flag）
- kabusys.run_monitoring
  - SystemMonitor のポーリングループ起動スクリプト
- kabusys.execution.*
  - broker_api.py: Protocol / データモデル / ファクトリ
  - kabu_client.py: kabu station 実装（REST / WebSocket）
  - mock_client.py: モックブローカー（テスト用）
  - order_record.py: 注文状態遷移ロジック
  - order_repository.py: SQLite 永続化レイヤ
  - order_manager.py: 発注フロー（作成・送信・同期・取消）
  - execution_engine.py: 発注エンジン本体（Signal 処理 / push ドレイン等）
  - risk_manager.py: 3段階のリスクガード
  - reconciler.py: 起動時の自動復旧・突合処理
  - broker_factory.py: Settings に基づくクライアント生成
- kabusys.data.*
  - calendar_management.py: マーケットカレンダー管理（DuckDB ベース）
  - news_collector.py: RSS ニュース収集（セキュアに実装）
- kabusys.monitoring.*
  - monitoring_db / system_monitor 等（監視関連処理）
- kabusys.utils.*
  - logging_setup, process_priority など補助ユーティリティ

---

## ディレクトリ構成（抜粋）

プロジェクトルート（例）
- .env (生成推奨、絶対に Git にコミットしない)
- config/
  - system_config.yaml
  - data_config.yaml
  - strategy_config.yaml
  - risk_config.yaml
  - execution_config.yaml
  - monitoring_config.yaml
- data/
  - kabusys.duckdb (デフォルト)
  - monitoring.db (SQLite)
  - paper_trading.db (ペーパートレード用 SQLite)
  - stop_requested.flag / kill.flag / execution.pid / ...
- src/
  - kabusys/
    - __init__.py
    - config.py
    - config_setup.py
    - validate_config.py
    - run_execution.py
    - run_monitoring.py
    - execution/
      - broker_api.py
      - kabu_client.py
      - mock_client.py
      - broker_factory.py
      - order_record.py
      - order_repository.py
      - order_manager.py
      - execution_engine.py
      - reconciler.py
      - risk_manager.py
    - data/
      - calendar_management.py
      - news_collector.py
      - jquants_client.py (外部データ取得用クライアント想定)
    - monitoring/
      - monitoring_db.py
      - system_monitor.py
    - utils/
      - logging_setup.py
      - process_priority.py
- pyproject.toml / setup.cfg / README.md

（実際のファイルはソースを参照してください。ここは代表的なツリーです）

---

## 運用上の注意

- .env に秘密情報（API トークン・パスワード等）を含め、決してリポジトリにコミットしないでください。
- 本番モード（KABUSYS_ENV=live）では更なる慎重な設定と本番向け通知（LINE など）の設定が必要です。validate_config は live 特有の警告を出します。
- ExecutionEngine は外部システム（kabuステーション）の挙動やネットワーク障害を考慮した設計になっていますが、実運用時は十分なステージング検証を行ってください。
- KabuStationClient の使用には kabuステーションアプリの起動等、外部環境が必要です。開発・テストは MockBrokerClient を使うことを推奨します。

---

## 追加・拡張ポイント（今後の案）

- Live ブローカークライアントの完成（現在は未実装箇所あり）
- ヘルスチェック / サービス監視向けエンドポイントの追加
- CI ワークフローでの validate_config の自動実行
- 詳細なチューニング用ドキュメント（risk_config / execution_config）

---

必要であれば、README に含める具体的な .env.example、Docker / systemd の起動例、または各モジュール（ExecutionEngine, RiskManager 等）の使い方サンプルを追記します。どの情報を優先して追加しましょうか？