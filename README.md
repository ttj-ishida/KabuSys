KabuSys — 日本株自動売買システム（ドキュメント）
======================================

概要
----
KabuSys は日本株の自動売買を想定した小規模なフレームワークです。  
主な設計方針は「発注ロジック（ExecutionEngine）」「注文状態の永続化（SQLite）」「監視（Monitoring）」「リスクガード」の分離で、安全性（kill switch / リコンシリエーション / サーキットブレーカー等）を重視しています。

主な機能
--------
- 環境設定ウィザード（.env の対話的作成 / 更新）
  - python -m kabusys.config_setup
- 設定検証 CLI（.env と config/*.yaml の整合性チェック）
  - python -m kabusys.validate_config [--strict]
- 実行エンジン（ExecutionEngine）
  - シグナル読み取り → Gate1/2 のリスクチェック → 発注 → push ドレイン
  - paper_trading モード時は MockBrokerClient を使用し、本番 DB と分離
  - 起動: python -m kabusys.run_execution
- 監視プロセス（SystemMonitor のポーリングループ）
  - 起動: python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）
- ブローカー API 層
  - KabuStationClient（kabuステーション REST）と MockBrokerClient（テスト用）
  - create_broker_api によるファクトリ
- 注文の状態管理（OrderRecord / OrderManager / OrderRepository）
  - SQLite に発注履歴を保存、状態遷移を厳密に検証
- リコンシリエーション（起動時に OrderSent の不確定注文を復旧）
- データ関連ユーティリティ
  - マーケットカレンダー管理（DuckDB）
  - ニュース収集（RSS, defusedxml を使用した安全な実装）

セットアップ手順
---------------
1. リポジトリをチェックアウト
   - 例: git clone <repo-url>

2. Python 仮想環境（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 必要なパッケージをインストール
   - 最低限（実行に必要な主要ライブラリの例）:
     - duckdb
     - httpx
     - websocket-client
     - defusedxml
     - pyyaml（config/*.yaml を内容検証したい場合）
   - 例:
     - pip install duckdb httpx websocket-client defusedxml pyyaml

   （requirements.txt がある場合はそれを使ってください:
    pip install -r requirements.txt）

4. .env の準備
   - 対話式ウィザードを使う（推奨）:
     - python -m kabusys.config_setup
     - ウィザードは .env（デフォルト）を生成・更新します。
   - 手動で作成する場合は .env.example を参考にしてください（存在する場合）。
   - 自動ロードについて:
     - 起動時に .env / .env.local がプロジェクトルートから自動読み込みされます（OS 環境変数が優先）。
     - 自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

5. 設定の検証
   - python -m kabusys.validate_config
   - --strict を付けると警告も exit(1) 扱いになります:
     - python -m kabusys.validate_config --strict

基本的な使い方
--------------
- 実行環境の選択
  - KABUSYS_ENV 環境変数で環境を切替:
    - development（開発） / paper_trading（ペーパートレード） / live（本番）
  - paper_trading または development では MockBrokerClient が使用され、実際の発注は行われません。
  - live は本番動作を意図します（現状 Live broker client は未実装箇所があります。エラーになる可能性があります）。

- 実行例
  - 環境変数をセットしてウィザードや検証を行う:
    - python -m kabusys.config_setup
    - python -m kabusys.validate_config --strict
  - 実行エンジン起動（当日セッションを実行）:
    - python -m kabusys.run_execution
  - 監視プロセス起動:
    - python -m kabusys.run_monitoring
    - MONITOR_POLL_INTERVAL 環境変数で間隔を秒指定可能（デフォルト 60）

主要な環境変数（抜粋）
--------------------
- 必須
  - JQUANTS_REFRESH_TOKEN — J-Quants API 用リフレッシュトークン
  - KABU_API_PASSWORD — kabuステーション API パスワード
- 任意 / 設定例
  - KABUSYS_ENV — development / paper_trading / live（デフォルト: development）
  - DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
  - LOG_LEVEL — DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）
  - KABU_API_BASE_URL — kabu station の base URL（デフォルト: http://localhost:18080/kabusapi）
  - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — 本番アラート用（任意）
  - KILL_FLAG_CLEAR_ON_START — 起動時 kill flag を自動クリア（0/1、デフォルト 0）
  - MONITOR_POLL_INTERVAL — 監視ポーリング間隔（秒、デフォルト 60）

注意点・運用メモ
----------------
- .env は機密情報を含むため Git にコミットしないこと（README でも警告有）。
- validate_config は PyYAML がインストールされていない場合、YAML 内容検証をスキップします（警告）。
- 監視プロセスは常に sqlite_path を利用します（環境にかかわらず本番用パスを参照する設計）。
- paper_trading モードでは sqlite_path を PAPER_TRADING_SQLITE_PATH で上書きして専用 DB を使えます。
- ExecutionEngine は kill.flag（デフォルト data/kill.flag）を検出すると起動拒否またはセッション停止します。
- 起動時の kill.flag 自動クリアは KILL_FLAG_CLEAR_ON_START=1 で許可できますが、本番では推奨されません。
- Live 環境でのLINE通知設定が不十分だとアラートが届きません。validate_config の警告を確認してください。

ディレクトリ構成（抜粋）
----------------------
src/kabusys/
- __init__.py
- config.py                      — 環境変数/ .env 自動ロード/ Settings
- config_setup.py                — .env 対話式ウィザード
- validate_config.py             — 起動前設定検証 CLI
- run_execution.py               — ExecutionEngine 起動スクリプト
- run_monitoring.py              — SystemMonitor 起動スクリプト

- execution/
  - __init__.py
  - broker_api.py                 — BrokerAPI の Protocol / データモデル / ファクトリ
  - kabu_client.py                — kabuステーション REST クライアント
  - mock_client.py                — MockBrokerClient（テスト用）
  - broker_factory.py             — 設定に応じたクライアント生成
  - order_record.py               — 注文状態モデル（状態遷移ロジック）
  - order_repository.py           — SQLite 永続化層
  - order_manager.py              — 発注 API（DB とブローカーの橋渡し）
  - execution_engine.py           — ExecutionEngine（メインの発注ロジック）
  - reconciler.py                 — リコンシリエーション（起動時復旧）
  - risk_manager.py               — 3 段階のリスクガード

- data/
  - calendar_management.py        — マーケットカレンダー管理（DuckDB）
  - news_collector.py             — RSS ニュース収集処理
  - (その他データ系モジュール)

- monitoring/
  - monitoring_db.py              — 監視用 DB 初期化 / ログ関係
  - system_monitor.py             — システム監視ロジック

- utils/
  - logging_setup.py              — ロギング初期化ユーティリティ
  - process_priority.py           — プロセス優先度設定ユーティリティ

- （config/*.yaml が期待される — validate_config でチェックされるファイル）
  - config/system_config.yaml
  - config/data_config.yaml
  - config/strategy_config.yaml
  - config/risk_config.yaml
  - config/execution_config.yaml
  - config/monitoring_config.yaml

開発・拡張のヒント
------------------
- Broker 実装
  - create_broker_api(mock=True, ...) で MockBrokerClient を返し、テストを容易にしています。
  - live ブローカーの実装（KabuStationClient の運用上の検討）を実装することで本番対応が可能になります。
- リコンシリエーション
  - OrderSent（送信済みだが状態未確定）を起動時に復旧する仕組みがあるため、クラッシュ耐性が向上します。
- テスト
  - MockBrokerClient とローカル DuckDB / SQLite を使えばユニット・統合テストが実行しやすい設計です。

問題・要望
---------
- ライブラリ依存や実運用に関する問題は Issue を作成してください。README に載せてほしい補足や手順があればお知らせください。

以上。必要であれば、README に含めるサンプル .env テンプレートや起動例（systemd ユニット例、Dockerfile 例）なども追記します。どの情報を追加しますか？