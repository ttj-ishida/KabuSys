# KabuSys

日本株自動売買システム（KabuSys）のコードベース README（日本語）

概要、機能、セットアップ手順、使い方、ディレクトリ構成をまとめています。

---

## プロジェクト概要

KabuSys は日本株の自動売買を想定した小規模なフレームワークです。  
主な目的は以下：

- シグナルを受け取って発注する ExecutionEngine
- 発注の永続化・状態管理（SQLite）
- ブローカー API 抽象化（実環境用の KabuStationClient とテスト用の MockBrokerClient）
- リスクガード（Gate1〜3：シグナル/実行/メトリクス）
- 起動時のリコンシリエーション（Reconciler）
- 監視プロセス（SystemMonitor）と監視 DB
- データ周り（DuckDB でのシグナル/ポートフォリオ、マーケットカレンダー、ニュース収集）
- .env による環境設定ウィザードと起動前検証ツール

設計方針として、ビジネスロジックと I/O（DB/API）を分離し、テスト容易性を高めています。

---

## 主な機能一覧

- 環境設定ウィザード（対話式で .env を作成/更新）
- 起動前の設定検証（.env と config/*.yaml のチェック）
- ExecutionEngine：
  - シグナルの取得（DuckDB）→ Gate1/2 チェック → 発注
  - WebSocket Push ドレイン（ブローカーからの通知処理）
  - kill_flag による安全停止・全注文キャンセル
- OrderManager / OrderRecord / OrderRepository による注文状態管理と永続化（SQLite）
- ブローカークライアント抽象化（Protocol）
  - MockBrokerClient（paper_trading / development 用）
  - KabuStationClient（kabuステーション API 実装、未完全実運用注意）
- リスク管理（レート制限、サーキットブレーカー、ポジション・利用率・ドローダウン）
- Reconciler による起動時の自動復旧・ブローカー照合
- 監視ループ（SystemMonitor）でリソース／メトリクス監視
- データユーティリティ（マーケットカレンダー、ニュース収集、J-Quants クライアント等）

---

## セットアップ手順（開発者向け）

前提：
- Python 3.9+ を想定（typing の表記等に依存）
- Git 等でリポジトリを取得

1. 仮想環境を作る（任意）
   - python -m venv .venv
   - source .venv/bin/activate (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール  
   基本的に使用されているライブラリ（例）:
   - duckdb
   - httpx
   - websocket-client
   - defusedxml
   - PyYAML（config の YAML 検証を行いたい場合）
   - そのほか標準ライブラリ（sqlite3 等）

   例:
   ```
   pip install duckdb httpx websocket-client defusedxml PyYAML
   ```

   （requirements.txt がある場合は `pip install -r requirements.txt` を使用）

3. .env の作成  
   対話式ウィザードを用意しています。プロジェクトルートで以下を実行：
   ```
   python -m kabusys.config_setup
   ```
   ウィザードは .env を生成します（デフォルト: プロジェクトルート/.env）。.env は絶対に Git にコミットしないでください。

4. 設定検証（起動前チェック）
   ```
   python -m kabusys.validate_config
   ```
   警告も FAIL 扱いにする場合:
   ```
   python -m kabusys.validate_config --strict
   ```
   PyYAML がインストールされていれば config/*.yaml の YAML パース検査も行います。

5. DB 初期化（必要に応じて）
   - Execution/Monitoring の起動スクリプトが起動時に DB テーブル初期化処理を呼ぶ設計です（init_monitoring_db / init_orders_db など）。
   - デフォルトの DB パスは .env の DUCKDB_PATH / SQLITE_PATH（デフォルト: data/kabusys.duckdb, data/monitoring.db）です。親ディレクトリがなければ自動作成されます。

---

## 使い方（実行方法）

- 環境設定ウィザード
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- 監視プロセス起動（SystemMonitor のポーリング）
  ```
  python -m kabusys.run_monitoring
  ```
  ※ 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒単位で上書き可能（デフォルト 60）。

- 発注エンジン起動（Execution）
  ```
  python -m kabusys.run_execution
  ```
  - KABUSYS_ENV に応じて動作：
    - development / paper_trading: MockBrokerClient を使用（本番ブローカ不要）
    - live: 実ブローカーは未実装（起動時に NotImplementedError をスローする箇所があります）
  - paper_trading では paper_sqlite_path（デフォルト data/paper_trading.db）を使用して本番の監視 DB と分離します。

- 停止フラグ
  - プロジェクトの data ディレクトリに stop_requested.flag（監視用）や kill.flag（実行停止用）などを配置することで挙動を制御できます。デフォルトのパスは Settings クラスのプロパティで確認してください（例: KILL_FLAG_PATH= data/kill.flag）。

---

## 主要な環境変数

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants API のリフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API パスワード

主な任意/構成値:
- KABUSYS_ENV — 実行環境（development / paper_trading / live）デフォルト: development
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- KABU_API_BASE_URL — kabuステーション API のベース URL（例: http://localhost:18080/kabusapi）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — 本番用の通知（任意）
- PID_FILE_PATH — PID ファイルの出力先（デフォルト: data/execution.pid）
- KILL_FLAG_PATH — kill.flag のパス（デフォルト: data/kill.flag）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（0/1）
- PAPER_FILL_MODE — paper_trading 時のモック挙動（instant / partial / never / reject）
- PAPER_TRADING_SQLITE_PATH — paper_trading 用 SQLite（デフォルト: data/paper_trading.db）

自動 .env 読み込み:
- プロジェクトルートの .env / .env.local が自動読み込みされます（OS 環境変数が優先）。
- 自動読み込みを無効にする場合: KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

注意:
- .env.example を参考に .env を作成してください（.env.example はプロジェクトに含める想定）。
- 本番 (KABUSYS_ENV=live) では LINE 通知等が未設定だと警告となります。慎重に設定してください。

---

## 実装上のポイント（簡易メモ）

- OrderRecord は状態遷移ロジックを持つ純粋オブジェクト（DB に依存しない）。
- OrderManager は送信の永続化順序（OrderSent を先に永続化する等）でクラッシュ耐性を確保する実装になっています（2相永続化戦略の採用）。
- Reconciler は起動時に OrderSent 状態の注文をブローカーと照合して同期を試みます。
- ExecutionEngine はシグナル処理（8:50-9:10）と push ドレイン（9:10-15:30）で区切られたルーチンを持ち、kill_switch による全注文キャンセルをサポートします。
- MockBrokerClient により paper_trading と development で本番 API を使わずに動作確認可能です。

---

## ディレクトリ構成（主要ファイルの説明）

プロジェクトの Python パッケージは `src/kabusys` に配置されています。主要なファイル/モジュール：

- src/kabusys/
  - __init__.py — パッケージ定義（バージョン等）
  - config.py — 環境変数読み込みと Settings クラス（.env の自動読み込みロジック含む）
  - config_setup.py — .env を対話式に生成するウィザード
  - validate_config.py — 起動前の設定検証 CLI
  - run_execution.py — ExecutionEngine の起動スクリプト（メインエントリ）
  - run_monitoring.py — SystemMonitor のポーリング起動スクリプト
  - execution/
    - broker_api.py — BrokerAPIProtocol、データモデル、例外、ファクトリ
    - kabu_client.py — kabuステーション REST API 実装（httpx / websocket）
    - mock_client.py — MockBrokerClient（テスト用）
    - broker_factory.py — Settings に基づきクライアントを返す
    - order_record.py — Order の状態モデルと遷移検証
    - order_repository.py — SQLite を使った永続化層（orders テーブル）
    - order_manager.py — 発注フロー（create/send/sync/cancel）
    - execution_engine.py — 実際のセッション実行ロジック（シグナル処理、push draining）
    - reconciler.py — リコンシリエーション・復旧ロジック
    - risk_manager.py — 3 段階リスクガード実装
  - data/
    - calendar_management.py — マーケットカレンダー管理（DuckDB）
    - news_collector.py — RSS ニュース収集（defusedxml 等を利用）
    - jquants_client.py —（参照されるクライアント；J-Quants 連携用）
  - monitoring/
    - monitoring_db.py — 監視用 SQLite 初期化とログ関数
    - system_monitor.py — システム資源監視ロジック
  - utils/
    - logging_setup.py — ログ設定ヘルパ
    - process_priority.py — プロセス優先度設定ユーティリティ
  - config/
    - *.yaml — 各種設定ファイル（system_config.yaml 等。validate_config で存在と YAML パースを検証）

（注）上記はコード内で参照されているモジュールを抜粋した一覧です。実際のリポジトリではさらに補助モジュールやスクリプトがある可能性があります。

---

## 注意事項 / 運用上のヒント

- .env は秘密情報を含むため絶対にリポジトリにコミットしないでください。
- production（live）環境については、KabuStationClient の運用および実ブローカー連携はリスクが高いため事前に十分なテストを行ってください。現状、BrokerClientFactory は live の場合 NotImplementedError を投げる設計箇所があります。
- Execution エンジン起動時に kill.flag が存在すると起動を拒否するか（設定による）自動クリアされます。運用ルールを明確にしてください。
- validate_config は起動前の簡易チェックに有用です。CI に組み込むと安全性が上がります（--strict オプションで警告も FAIL 扱い）。

---

必要があれば、README にサンプル .env.example（テンプレート）を追記したり、主要な設定ファイル（config/*.yaml）のサンプル生成手順や、ユニットテスト・CI の設定方法を追加できます。どの情報を追記したいか教えてください。