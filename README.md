# KabuSys

日本株自動売買システムの一部を切り出した Python パッケージです。  
この README はリポジトリ内の実装（src/kabusys 以下）を基に作成しています。

注意: このプロジェクトは実際の発注処理や資金管理を伴います。テスト／開発環境以外で使用する場合は十分に理解した上で慎重に運用してください。

---

## プロジェクト概要

KabuSys は「シグナルを受け取り、リスクガードを通してブローカーに発注し、発注状態を永続化・監視・リコンシリエーションする」ことを目的とした自動売買エンジンの骨組みです。  
主に以下の責務を持つコンポーネントで構成されています。

- 設定管理 (.env の読み込み、Settings)
- 発注フロー（ExecutionEngine / OrderManager / OrderRepository）
- ブローカークライアント（Mock / KabuStationClient のラッパー）
- リスク管理（3 段階ガード: Gate1..3、レート制限、サーキットブレーカー、ドローダウン監視）
- 起動時リコンシリエーション（Reconciler）
- 監視ループ（SystemMonitor を使った監視 / run_monitoring）
- 運用支援ツール（.env ウィザード、設定検証 CLI）

---

## 主な機能一覧

- .env / 環境変数による設定読み込み（自動ロード、.env / .env.local）
- 対話式 .env 作成ウィザード（kabusys.config_setup）
- 実行前の設定検証 CLI（kabusys.validate_config）
- 発注状態を SQLite へ永続化する OrderRepository（冪等性・部分ユニット設計）
- 発注状態遷移を検証する OrderRecord（状態遷移ルールを厳密に定義）
- ExecutionEngine：シグナルの読み込み → Gate1/Gate2 を通した発注 → WebSocket push ドレイン
- Broker API 抽象（BrokerAPIProtocol）とファクトリ（mock / live 切替）
- MockBrokerClient：テスト向けモック（instant / partial / never / reject の fill_mode）
- RiskManager：Gate1（余力・重複・ポジション上限）、Gate2（レート制限・サーキットブレーカー）、Gate3（ドローダウン）
- Reconciler：OrderSent 状態の自動照合、ポジション差分検出
- 監視ループ（run_monitoring）によるリソース監視と監視 DB への記録

---

## 必要環境

- Python 3.10 以上（PEP 604 の | 型注釈等を利用）
- 推奨パッケージ（少なくとも実行する機能に応じてインストール）:
  - duckdb
  - httpx
  - websocket-client
  - defusedxml
  - PyYAML（config YAML の内容検証を有効にする場合）
- SQLite（Python 標準ライブラリで使用）
- Linux / macOS 環境を想定したプロセス優先度設定処理（utils/process_priority）

インストール例:
pip install duckdb httpx websocket-client defusedxml PyYAML

---

## セットアップ手順

1. リポジトリをチェックアウトし、Python 仮想環境を作成して有効化
   - python -m venv .venv
   - source .venv/bin/activate  （Windows では .venv\Scripts\activate）

2. 必要パッケージをインストール
   - pip install -r requirements.txt
   （requirements.txt がない場合は上の推奨パッケージを個別にインストール）

3. .env を作成する
   - 対話式ウィザードを実行して .env を作成:
     - python -m kabusys.config_setup
     ウィザードで入力した値がプロジェクトルートの .env に保存されます（デフォルト）。
   - 既に .env を持っている場合は .env.local で上書きできます。

4. 作成した設定を検証する（任意）
   - python -m kabusys.validate_config
   - 警告も失敗扱いにしたい場合:
     - python -m kabusys.validate_config --strict

5. DB ディレクトリ作成（必要に応じて）
   - デフォルト DB パス: data/kabusys.duckdb, data/monitoring.db, data/paper_trading.db
   - これらの親ディレクトリは起動時に自動作成される場合もありますが事前に確認してください。

---

## 環境変数（重要なもの）

必須 (validate_config でチェックされます):
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

任意（推奨/デフォルトあり）:
- KABUSYS_ENV (development / paper_trading / live) — デフォルト: development
- DUCKDB_PATH — デフォルト: data/kabusys.duckdb
- SQLITE_PATH — デフォルト: data/monitoring.db
- LOG_LEVEL — デフォルト: INFO (DEBUG/INFO/WARNING/ERROR/CRITICAL)
- KABU_API_BASE_URL — デフォルト: http://localhost:18080/kabusapi
- LINE_CHANNEL_ACCESS_TOKEN — 本番でのアラート送信に使用
- LINE_USER_ID — 本番でのアラート送信先
- KILL_FLAG_CLEAR_ON_START — 本番起動時の kill.flag 自動クリア (0/1)

注意:
- 自動で .env を読み込む仕組みが導入されています（OS 環境 > .env.local > .env）。自動ロードを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## 使い方（主要スクリプト）

基本的にモジュールはパッケージ内のエントリポイント（python -m ...）で起動します。

- .env 作成ウィザード
  - python -m kabusys.config_setup
  - 対話式に値を入力して .env を作成または更新します。

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告も失敗扱いで exit code 1 を返します。

- 実行エンジン（実際の発注ループ）
  - python -m kabusys.run_execution
  - 実行時の動作:
    - Settings() に基づき SQLite / DuckDB に接続
    - Broker クライアントを作成（development / paper_trading → MockBrokerClient）
    - ExecutionEngine を起動し、セッション（シグナル処理・push ドレイン）を実行
  - 注意: KABUSYS_ENV=paper_trading は MockBrokerClient を使用し、paper_trading 用 DB (data/paper_trading.db) に切り替えて本番 DB と分離します。

- 監視ループ（SystemMonitor ポーリング）
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を変更可能（デフォルト 60）。
  - 監視は KABUSYS_ENV にかかわらず本番 sqlite_path を使用します（監視用 DB）。

- その他
  - 開発時は MockBrokerClient を利用してユニットテスト的な動作確認が可能です。
  - ExecutionEngine のログや PID / kill flag の管理により安全に起動・停止できます。

---

## 実行時のファイル / フラグ

- PID / Kill
  - PID ファイル: data/execution.pid（デフォルト、起動時に書き込む）
  - Kill flag: data/kill.flag（存在する場合は起動拒否または kill_switch の発動）
  - stop_requested.flag: run_monitoring / run_execution が監視する停止要求フラグ

- DB
  - DuckDB: デフォルト data/kabusys.duckdb
  - SQLite (監視): デフォルト data/monitoring.db
  - Paper trading 用 SQLite: data/paper_trading.db（paper_trading 用）

---

## ディレクトリ構成（主なファイル説明）

以下は src/kabusys の主要ファイルと役割です。実際のリポジトリにはさらにファイルやサブパッケージが存在する想定です。

- src/kabusys/
  - __init__.py — パッケージ定義（__version__ 等）
  - config.py — 環境変数読み込み、自動 .env 読み込みロジック、Settings クラス
  - config_setup.py — 対話式 .env 作成ウィザード（python -m kabusys.config_setup）
  - validate_config.py — 起動前設定検証 CLI（python -m kabusys.validate_config）
  - run_execution.py — ExecutionEngine を起動するスクリプト（python -m kabusys.run_execution）
  - run_monitoring.py — SystemMonitor をポーリングするスクリプト（python -m kabusys.run_monitoring）

  - execution/  — 発注周りの実装
    - broker_api.py — BrokerAPI のデータモデル、Protocol、例外、create_broker_api ファクトリ
    - broker_factory.py — Settings に基づくブローカークライアント生成ファクトリ
    - kabu_client.py — KabuStationClient（kabu station REST API 実装）
    - mock_client.py — MockBrokerClient（テスト用）
    - execution_engine.py — ExecutionEngine（シグナル処理 / push ドレイン / セッション管理）
    - order_record.py — OrderRecord（状態遷移と検証）
    - order_repository.py — SQLite を使った Orders 永続化
    - order_manager.py — OrderManager（外向き API：作成・送信・同期・キャンセル）
    - reconciler.py — Reconciler（起動時の OrderSent 照合、ポジション照合）
    - risk_manager.py — RiskManager（Gate1/2/3, rate limit, circuit breaker）

  - data/ — データ関連処理
    - calendar_management.py — マーケットカレンダー管理（DuckDB と J-Quants 連携）
    - news_collector.py — RSS ニュース収集（正規化・SSRF 対策・defusedxml 利用）

  - monitoring/ — 監視関連（監視 DB 初期化・SystemMonitor 実装は別ファイル）
    - monitoring_db.py — 監視 DB 初期化 / ログ書き込み
    - system_monitor.py — システムリソース監視（CPU/MEM/DISK 等）

  - utils/
    - logging_setup.py — ログ初期化ユーティリティ
    - process_priority.py — プロセス優先度設定ユーティリティ

---

## 開発・運用上の注意

- 本番環境（KABUSYS_ENV=live）では設定を厳密に確認してください。validate_config はライブ環境に特別な警告を出します。
- .env は絶対にリポジトリにコミットしないでください（config_setup.py にもその旨が書かれています）。
- ExecutionEngine は外部ネットワークやブローカー API に依存するため、paper_trading / development モードでまず動作確認を行ってください。
- Reconciler はクラッシュ後の状態を自動復旧するよう設計されていますが、重大な不整合が検出された場合は手動確認が必要です。
- 監視（run_monitoring）は運用中の重要な補助機能です。LINE 連携等を設定しておくとアラート受信が容易になります。

---

## 参考コマンドまとめ

- 仮想環境作成・有効化:
  - python -m venv .venv
  - source .venv/bin/activate

- 依存インストール:
  - pip install duckdb httpx websocket-client defusedxml PyYAML

- .env ウィザード:
  - python -m kabusys.config_setup

- 設定検証:
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- 実行エンジン（発注）:
  - python -m kabusys.run_execution

- 監視ループ:
  - python -m kabusys.run_monitoring

---

必要に応じて、README に追加したい点（例: サンプル .env.example、generate_config スクリプトの説明、テスト方法、CI 設定など）があれば教えてください。README をそれに合わせて拡張します。