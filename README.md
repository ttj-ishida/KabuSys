# KabuSys

バージョン: 0.1.0

KabuSys は日本株向けの自動売買システムのコアライブラリです。本リポジトリは発注ロジック、ブローカー API 抽象化、リスク管理、監視、データ収集などの主要コンポーネントを含みます。開発 / ペーパートレード / 本番（live）を想定した設定と、起動前検証・対話式設定ウィザードを備えています。

---

## 概要

- 発注フロー: シグナル取得 → Gate1/Gate2 のリスクチェック → 発注 → 約定同期 / リコンシリエーション
- Broker 抽象化: 実ブローカー（kabu station）とモック（テスト・ペーパートレード）を共通インターフェースで扱える設計
- リスク管理: 3 段階 (Signal / Execution / Metrics) のガード
- 監視: 独立した monitoring プロセスでシステム状況をポーリングして記録
- 開発支援: .env ウィザード（対話式）と設定検証 CLI を提供

---

## 主な機能一覧

- 環境設定の自動読み込み（.env, .env.local）と Settings クラスによる型安全なアクセス
- .env を対話式に生成・更新するウィザード（python -m kabusys.config_setup）
- 起動前に環境変数・config/*.yaml の妥当性を検証する CLI（python -m kabusys.validate_config）
- ExecutionEngine（シグナル駆動の発注エンジン）
- Order 管理（OrderRecord / OrderRepository / OrderManager）
- ブローカークライアント:
  - MockBrokerClient（テスト用）
  - KabuStationClient（kabu station REST / WebSocket 実装）
- リコンシリエーション（起動時の自動復旧）
- リスク制御（レート制限・サーキットブレーカー・ドローダウン監視）
- データ関連:
  - DuckDB ベースのマーケットカレンダー管理
  - RSS ニュース収集（前処理・SSRF 対策含む）
- 監視プロセス（run_monitoring）で SQLite / DuckDB に状態を記録

---

## セットアップ手順（ローカル開発向け）

1. リポジトリをクローンしてソースルートへ移動
   - 本 README 前提ではパッケージのトップに `src/` があり、パッケージは `src` 下に配置されています。

2. Python 仮想環境を作成・有効化
   - 例:
     - python -m venv .venv
     - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   - 最低限必要となるパッケージ例:
     - duckdb
     - httpx
     - websocket-client
     - PyYAML (config YAML のパース検証用。未インストールでも動作しますが validate_config は YAML 検証をスキップします)
     - defusedxml
   - 例:
     - pip install duckdb httpx websocket-client PyYAML defusedxml

   > 実プロジェクトでは requirements.txt / poetry / pyproject.toml に依存関係をまとめてください。

4. 初期設定（.env）の作成
   - 対話式ウィザードを使う（推奨）:
     - python -m kabusys.config_setup
     - ウィザードは `.env`（デフォルト）を作成・更新します。既存の `.env` があれば読み込んで上書き/再利用できます。
   - 手動で作る場合の例（.env）:
     ```
     JQUANTS_REFRESH_TOKEN=your_refresh_token_here
     KABU_API_PASSWORD=your_kabu_api_password_here
     KABU_API_BASE_URL=http://localhost:18080/kabusapi
     DUCKDB_PATH=data/kabusys.duckdb
     SQLITE_PATH=data/monitoring.db
     KABUSYS_ENV=development
     LOG_LEVEL=INFO
     KILL_FLAG_CLEAR_ON_START=0
     ```

5. 設定検証
   - 起動前に設定の妥当性をチェック:
     - python -m kabusys.validate_config
     - 警告もエラー扱いにする: python -m kabusys.validate_config --strict

6. 実行例
   - 実行エンジン（発注）:
     - python -m kabusys.run_execution
   - 監視プロセス:
     - python -m kabusys.run_monitoring

---

## 使い方（主要 CLI / 起動オプション）

- 環境設定ウィザード
  - python -m kabusys.config_setup
  - 対話式に .env を作成 / 更新します。保存確認あり。

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告も失敗扱いで exit(1) します。

- 実行エンジン（Execution）
  - python -m kabusys.run_execution
  - KABUSYS_ENV が paper_trading または development の場合は MockBrokerClient を使用します。
  - stop フラグファイル: data/stop_requested.flag
  - PID ファイル: data/execution.pid（存在する場合、起動制御に使用）
  - Kill flag: data/kill.flag（存在すると起動を拒否 or クリア条件により挙動が変わる）
  - Paper trading の DB: data/paper_trading.db（PAPER_TRADING_SQLITE_PATH で上書き可）

- 監視プロセス（SystemMonitor）
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書きできます（デフォルト 60）。
  - 監視は常に本番用 sqlite_path を使用（KABUSYS_ENV に依らず）。

---

## 重要な環境変数（抜粋）

- 必須
  - JQUANTS_REFRESH_TOKEN — J-Quants API 用リフレッシュトークン（必須）
  - KABU_API_PASSWORD — kabuステーション API パスワード（必須）

- 推奨 / オプション
  - KABUSYS_ENV — 実行環境: development / paper_trading / live（デフォルト: development）
  - DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
  - LOG_LEVEL — ログレベル（DEBUG, INFO, WARNING, ERROR, CRITICAL）
  - KABU_API_BASE_URL — kabu station API の base URL（デフォルト: http://localhost:18080/kabusapi）
  - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — 本番でのアラート用（live 時に警告）
  - KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（0/1、デフォルト 0）
  - PAPER_FILL_MODE — paper_trading の約定モード（instant, partial, never, reject）

- 自動読み込み
  - OS 環境変数 > .env.local > .env の順で読み込みます。
  - 自動読み込みを無効化: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

---

## 運用ファイル / フラグ

- data/execution.pid — 実行エンジンの PID ファイル
- data/kill.flag — kill スイッチ（存在すると起動拒否やランタイムで kill が発動）
- data/stop_requested.flag — monitoring/execution の外部停止要求フラグ
- DB ファイル（デフォルト）
  - data/kabusys.duckdb
  - data/monitoring.db
  - data/paper_trading.db（paper_trading 用）

注意: .env は絶対にバージョン管理にコミットしないでください（README ヘッダーにもウィザードが注意書きを出します）。

---

## ディレクトリ構成（抜粋）

プロジェクトは src/ 配下のパッケージとして配置されています。主要なファイル / モジュール:

- src/kabusys/
  - __init__.py — パッケージ定義（バージョン情報）
  - config.py — 環境変数読み込み・Settings クラス（.env 読み込みロジック含む）
  - config_setup.py — .env 対話式ウィザード
  - validate_config.py — 起動前設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor 起動スクリプト
  - execution/
    - broker_api.py — Broker API のデータモデル・Protocol・ファクトリ
    - broker_factory.py — Settings に基づく Broker クライアント生成
    - kabu_client.py — kabu station REST / WebSocket 実装
    - mock_client.py — MockBrokerClient（テスト用）
    - order_record.py — Order の状態遷移ロジック（ビジネスロジック）
    - order_repository.py — SQLite ベースの永続化層
    - order_manager.py — OrderRecord + OrderRepository を使った発注 API
    - execution_engine.py — シグナル駆動の発注エンジン
    - reconciler.py — 起動時のリコンシリエーション
    - risk_manager.py — 3 段階リスクガード
  - data/
    - calendar_management.py — マーケットカレンダー管理（DuckDB）
    - news_collector.py — RSS ニュース収集・前処理
  - monitoring/
    - (監視 DB 初期化等の実装ファイル群)
  - utils/
    - logging_setup.py — ロギング設定
    - process_priority.py — プロセス優先度設定

（リポジトリには上記以外の補助モジュール / スクリプトが含まれる可能性があります）

---

## 開発 / テストに関するメモ

- MockBrokerClient を使えば kabu station を実行せずに発注フローの統合テストが可能です（KABUSYS_ENV=paper_trading / development）。
- OrderRepository の init_orders_db(), monitoring_db の init_monitoring_db() などで DB スキーマを初期化できます。run_execution / run_monitoring は必要に応じて初期化処理を呼びます。
- validate_config は PyYAML が無ければ YAML の内容検証をスキップします。CI で厳密に検証する場合は PyYAML をインストールしてください。
- .env の上書きポリシー:
  - OS 環境変数は保護され、.env/.env.local による上書きを防止します（ただし .env.local は override=True で読み込まれ、既存の OS 環境変数は保護されます）。
- 本番稼働前に必ず:
  - KABUSYS_ENV が適切に設定されていること
  - 必須環境変数が設定されていること（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD）
  - LINE 通知設定や Kill Switch 周りの設定を確認すること（live 環境での警告あり）

---

## よくあるコマンドまとめ

- .env 作成ウィザード:
  - python -m kabusys.config_setup
- 設定チェック:
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict
- 実行エンジン起動:
  - python -m kabusys.run_execution
- 監視プロセス起動:
  - python -m kabusys.run_monitoring
- （開発）Mock ブローカーを使った実行:
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution

---

## ライセンス / 貢献

- この README はコードベースから生成された説明です。実運用前に必ず社内の安全手順・セキュリティレビューを行ってください。
- バグ報告や機能改善は Issue / PR でお願いします。

---

以上。必要に応じて README に含める詳細（例: requirements.txt、CI 設定、運用チェックリスト、SQL スキーマ例など）を追加します。どの情報を優先して追加しますか？