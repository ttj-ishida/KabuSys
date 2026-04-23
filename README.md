# KabuSys

日本株自動売買システム（KabuSys） — 軽量な発注エンジン、リスクガード、監視・リコンシリエーション機能を備えたプロジェクト。

バージョン: 0.1.0

## プロジェクト概要
KabuSys は日本株の自動売買を想定したモジュール群です。主な用途・設計方針は以下の通りです。

- Signal Queue を起点に発注を行う ExecutionEngine（シグナルフェーズ + WebSocket ドレイン）を提供。
- 発注のライフサイクルを OrderRecord（状態遷移）で厳密に管理し、SQLite に永続化することでクラッシュ耐性を担保。
- Broker 接続は抽象化されており、テスト用の MockBrokerClient（paper_trading / development）と将来の実運用クライアントを容易に切り替え可能。
- 3段階のリスクガード（Gate1: シグナル、Gate2: エグゼキューション、Gate3: メトリクス）で安全性を確保。
- 起動時の自動リコンシリエーション（Reconciler）で OrderSent 状態の復旧やポジション差分チェックを行う。
- 監視プロセス（SystemMonitor）を用いたポーリングループや監視用 SQLite / DuckDB との連携をサポート。
- .env ベースの設定・ウィザード・検証ツールを提供し、起動前に設定不備を検出できる。

## 主な機能一覧
- 環境設定ウィザード（python -m kabusys.config_setup）による .env 作成・更新
- 設定検証 CLI（python -m kabusys.validate_config）で必須環境変数や config/*.yaml の存在をチェック
- 実行エンジン（python -m kabusys.run_execution）
  - Signal 処理（発注枠）と WebSocket push ドレイン
  - OrderManager / OrderRepository による堅牢な発注フロー（2相永続化等）
  - RiskManager（Gate1/2/3）による発注制御（レート制限、サーキットブレーカー、ドローダウン等）
  - Reconciler による起動時復旧
- 監視ループ（python -m kabusys.run_monitoring）
  - システムメトリクスを監視し、SQLite / DuckDB に記録
- Broker クライアント抽象化
  - MockBrokerClient（テスト用・paper_trading 用）
  - KabuStationClient（kabu station REST API 実装、未実装・将来想定のライブクライアント）
- データユーティリティ
  - DuckDB を使ったマーケットカレンダー管理（next_trading_day など）
  - ニュース収集・前処理モジュール（RSS 収集、SSRF 対策、トラッキングパラメータ除去 等）

## セットアップ手順（開発・ローカル向け）
※ 実運用に関する詳細や本番リスクは別途ガイドラインに従ってください。

1. リポジトリをクローン
   ```bash
   git clone <repo-url>
   cd <repo>
   ```

2. Python バージョン
   - Python 3.10 以上を推奨（型ヒントに `X | Y` などを使用）。

3. 必要パッケージをインストール
   ※ プロジェクトの requirements.txt があればそれを使ってください。主要依存例:
   ```bash
   pip install duckdb httpx websocket-client defusedxml
   # 以下はオプション（YAML の検証などで利用）
   pip install PyYAML
   ```

4. .env の作成
   - 対話式ウィザードを実行して .env を作成・編集できます。
   ```bash
   python -m kabusys.config_setup
   ```
   - ウィザードで保存すると .env が生成されます（.env は絶対に Git にコミットしないでください）。

5. 設定検証
   - 作成した .env / 環境変数を検証します。
   ```bash
   python -m kabusys.validate_config
   python -m kabusys.validate_config --strict  # 警告も FAIL として扱う
   ```

6. 実行・監視用 DB（デフォルト）
   - DuckDB: data/kabusys.duckdb
   - SQLite (監視): data/monitoring.db
   - paper_trading 用 SQLite: data/paper_trading.db（KABUSYS_ENV=paper_trading 時に利用）
   - 起動スクリプトは必要に応じてテーブルを初期化します（init_monitoring_db、init_orders_db を利用）。

## 環境変数（主要）
必須:
- JQUANTS_REFRESH_TOKEN — J-Quants API 用リフレッシュトークン（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）

任意 / 推奨:
- KABUSYS_ENV — 実行環境（development | paper_trading | live）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- KABU_API_BASE_URL — kabu station base URL（デフォルト: http://localhost:18080/kabusapi）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — 通知用（任意）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアする（0/1）

自動ロード挙動:
- OS 環境変数 > .env.local > .env の順で読み込みます（プロジェクトルートは .git または pyproject.toml を基準に探索）。
- 自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

簡易 .env の例（秘密情報は設定しないこと）:
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here
KABU_API_PASSWORD=your_kabu_api_password_here
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
LOG_LEVEL=INFO
```

## 使い方（主要コマンド）
- 設定ウィザード（.env 作成）
  ```bash
  python -m kabusys.config_setup
  ```

- 設定検証
  ```bash
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- 実行エンジンの起動（Execution）
  - paper_trading / development 環境では MockBrokerClient が使われます（実際の発注は行われません）。
  ```bash
  # 環境変数で KABUSYS_ENV を設定するか .env を用意
  python -m kabusys.run_execution
  ```
  - 実行中の停止は data/stop_requested.flag を作成することで安全に停止できます（スクリプトはこのフラグを監視）。
  - PID ファイル: data/execution.pid

- 監視ループの起動（SystemMonitor）
  ```bash
  python -m kabusys.run_monitoring
  ```
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL（秒）で変更可能（デフォルト 60 秒）。
  - 監視も data/stop_requested.flag を監視し停止します。

- 実運用（注意）
  - KABUSYS_ENV=live は本番向けですが、現在 Live broker client の実装は未実装（BrokerClientFactory で NotImplementedError を投げます）。本番稼働前に必ず実装・レビューを行ってください。
  - kill.flag による起動拒否、KILL_FLAG_CLEAR_ON_START の挙動に注意してください。

## 重要な挙動・運用メモ
- 発注の堅牢性:
  - 発注フローは「OrderCreated → OrderSent（DBにまずコミット） → broker 呼出し → broker_order_id 永続化 → OrderAccepted」などの順序で2相永続化を行い、クラッシュからの復旧を容易にしています。
  - OrderSent のまま残る不確定注文は Reconciler で復旧対象となります。

- リスク管理:
  - Gate1: 余力・重複・銘柄/全体上限
  - Gate2: レート制限（トークンバケツ）・サーキットブレーカー
  - Gate3: ドローダウン監視（現在のポートフォリオ評価と比較）

- モック動作:
  - PAPER_FILL_MODE によって MockBrokerClient の約定挙動を変えられます（instant / partial / never / reject）。
  - paper_trading 環境は実運用 DB（monitoring.db）と分離して paper_trading.db を使用します。

## ディレクトリ構成（主要ファイル）
（リポジトリの src/kabusys 配下を抜粋）

- src/kabusys/
  - __init__.py — パッケージ定義（__version__ 等）
  - config.py — 環境変数の自動読み込み、Settings クラス（アプリケーション設定）
  - config_setup.py — .env 対話式ウィザード
  - validate_config.py — 起動前設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor 起動スクリプト
  - execution/
    - __init__.py
    - broker_api.py — BrokerAPIProtocol、データモデル、ファクトリ
    - broker_factory.py — 設定に応じた Broker クライアント生成
    - kabu_client.py — kabu station REST API 実装（HTTP + WebSocket）
    - mock_client.py — テスト用 MockBrokerClient
    - order_record.py — 注文状態遷移ロジック（OrderRecord, OrderState）
    - order_repository.py — SQLite 永続化（orders テーブル）
    - order_manager.py — 外向き発注 API（create/send/sync/cancel）
    - execution_engine.py — 発注エンジン本体（signal/drain/WS/killswitch）
    - reconciler.py — 起動時リコンシリエーション
    - risk_manager.py — Gate1/2/3 リスク制御
  - data/
    - calendar_management.py — マーケットカレンダー（DuckDB）管理
    - news_collector.py — RSS ニュース収集（SSRF 対策等）
    - jquants_client.py —（参照あり、J-Quants API クライアント）
  - monitoring/
    - monitoring_db.py — 監視用 DB 初期化・ログ記録（SQLite）
    - system_monitor.py — システム監視ロジック
  - utils/
    - logging_setup.py — ロギング初期化ユーティリティ
    - process_priority.py — プロセス優先度設定ユーティリティ

（上記は主要モジュールの抜粋です。細かなモジュールはソースを参照してください）

## 開発者向けメモ
- 自動ロード:
  - Settings モジュールは .env / .env.local をプロジェクトルート（.git または pyproject.toml があるディレクトリ）から自動ロードします。テストで自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD を利用してください。
- テスト:
  - MockBrokerClient を用いることで外部依存なしに発注フローの単体テストが可能です。
- 例外設計:
  - BrokerAPI のエラーは BrokerAPIError 系で表現され、OrderManager や Reconciler はこれらを適切にハンドリングします。

---

README に書かれている内容はコードベースの主要点をまとめたものです。実運用前にはコードと設定（特に認証情報・KABUSYS_ENV=live の振る舞い）を十分に検証・レビューしてください。必要があれば README を拡張しますので、追記したい情報（依存関係ファイル、デプロイ手順、CI 設定など）を教えてください。