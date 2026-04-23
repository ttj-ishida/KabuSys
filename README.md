# KabuSys

日本株自動売買システム（ミニマル実装）  
このリポジトリは、シグナル駆動の発注エンジン、モニタリング、設定管理を備えた自動売買フレームワークの一部実装です。主にローカル開発 / ペーパートレード向けに設計されています。

バージョン: 0.1.0

---

## 概要

- 環境変数 / YAML 設定の検証ツール、対話式 .env 設定ウィザードを提供します。
- 発注処理は「ExecutionEngine」で実行され、3段階のリスクガード（Gate1/2/3）と Reconciliation 機能を備えます。
- ブローカークライアントは抽象化されており、開発／テスト用に MockBrokerClient（ペーパートレード用）が組み込まれています。KabuStation 実クライアント（KabuStationClient）も実装されていますが、実稼働クライアントの使用は環境に応じて注意が必要です（README 内で注意）。
- データは DuckDB（分析用）と SQLite（監視・注文永続化）に保存します。

---

## 主な機能一覧

- 環境設定ウィザード（python -m kabusys.config_setup）
  - .env の初期作成／更新を対話式で実行
- 設定検証 CLI（python -m kabusys.validate_config）
  - .env と config/*.yaml の存在・妥当性チェック（--strict で警告を失敗扱い）
- ExecutionEngine（発注エンジン）
  - シグナルの読み取り→Gate1/2 を通した発注→WebSocket push のドレイン
  - Reconciler による再起動後の注文同期、kill_switch による一斉キャンセル
- Broker クライアント抽象化
  - MockBrokerClient（fill_mode 指定可能: instant/partial/never/reject）
  - KabuStationClient（httpx / websocket を使用した kabu station API クライアント）
- Order 管理
  - OrderRecord（状態遷移の検証）、OrderRepository（SQLite 永続化）、OrderManager（送信・同期・キャンセル）
- RiskManager（3段階リスクガード: シグナル・実行・メトリクス）
- Monitoring 用ループ（python -m kabusys.run_monitoring）
  - system リソース監視・監視 DB ロギング
- Data ユーティリティ
  - マーケットカレンダー管理（DuckDB ベース）
  - ニュース収集モジュール（RSS 収集、前処理、SSRF 対策等）

---

## セットアップ手順（開発用）

1. Python 環境の準備（推奨: 3.9+）
   - 仮想環境を作成・有効化:
     - python -m venv .venv
     - Windows: .venv\Scripts\activate
     - macOS/Linux: source .venv/bin/activate

2. 依存パッケージのインストール（最低限）
   - 必要なライブラリ（用途に応じて追加）:
     - httpx, websocket-client, duckdb, defusedxml, pyyaml
   - 例:
     - pip install httpx websocket-client duckdb defusedxml pyyaml

   （requirements.txt がある場合はそれを使用してください:
   pip install -r requirements.txt）

3. プロジェクトルート内に `data/` ディレクトリを作成（DB / PID / フラグ保存用）
   - mkdir -p data

4. .env の作成
   - 対話式ウィザードを推奨:
     - python -m kabusys.config_setup
   - もしくは手動で .env ファイルを作成（.env.example を参照する想定）

5. 設定検証
   - python -m kabusys.validate_config
   - 警告もエラー扱いにしたい場合:
     - python -m kabusys.validate_config --strict

注意:
- 設定の自動読み込みは Settings モジュールがプロジェクトルートを検出して .env / .env.local を読み込みます。自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- よく使うオプション環境変数（例）:
  - KABUSYS_ENV (development | paper_trading | live)
  - DUCKDB_PATH, SQLITE_PATH, LOG_LEVEL, KABU_API_BASE_URL
  - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID（本番のアラート用）

---

## 使い方（簡易ガイド）

1. .env を作成（wizard 推奨）
   - python -m kabusys.config_setup

2. 設定検証
   - python -m kabusys.validate_config
   - --strict を付けると警告があると exit(1) になります。

3. モニタリングを起動
   - python -m kabusys.run_monitoring
   - ポーリング間隔を変更するには環境変数:
     - MONITOR_POLL_INTERVAL（秒、デフォルト 60）

4. 発注エンジンを起動
   - python -m kabusys.run_execution
   - KABUSYS_ENV=paper_trading なら MockBrokerClient（paper_trading 用 SQLite を使用）で動作します。
   - 実稼働（KABUSYS_ENV=live）のサポートは限定的／注意が必要です（BrokerClientFactory は live 時 NotImplementedError を投げる設計）。

5. 停止制御
   - 起動時の kill.flag の扱い:
     - settings.kill_flag_clear_on_start が True（KILL_FLAG_CLEAR_ON_START=1）なら起動時に kill.flag を自動クリアします（開発向け）。
     - 普通は 0 を推奨（存在する場合は起動拒否）。
   - 実行中に停止したい場合は `data/stop_requested.flag` を作成すると各ループが検知して安全に停止します。
   - PID ファイルはデフォルトで data/execution.pid（設定で上書き可）。

---

## 主要設定と挙動（補足）

- Settings 自動読み込み
  - 読み込み順: OS 環境変数 > .env.local > .env
  - OS 環境変数は保護され、.env.local の override でも上書きされません。
- DB
  - DuckDB: 分析用（デフォルト data/kabusys.duckdb）
  - SQLite: 監視 / Orders（デフォルト data/monitoring.db）
  - paper_trading 環境では paper_trading 用 SQLite（data/paper_trading.db）を使用して本番 DB と分離
- Broker の挙動
  - MockBrokerClient はテスト用に各種 fill_mode をサポート（instant/partial/never/reject）
  - KabuStationClient は実際の kabu station API に接続（httpx と websocket-client を使用）
- リスク管理
  - RiskManager が Gate1（シグナル検査）/ Gate2（レート・CB）/ Gate3（ドローダウン）を担当
  - サーキットブレーカー、トークンバケツ（レート制限）などを実装

---

## ディレクトリ構成

（抜粋）主要ファイルと簡単な説明:

- src/kabusys/
  - __init__.py — パッケージ定義
  - config.py — 環境変数読み込みと Settings クラス（自動 .env ロード含む）
  - config_setup.py — .env 対話式ウィザード（python -m kabusys.config_setup）
  - validate_config.py — 起動前設定検証ツール（python -m kabusys.validate_config）
  - run_execution.py — ExecutionEngine を起動するスクリプト（python -m kabusys.run_execution）
  - run_monitoring.py — SystemMonitor をループ実行するスクリプト（python -m kabusys.run_monitoring）

  - execution/
    - broker_api.py — BrokerAPI のデータモデル、Protocol、ファクトリ
    - broker_factory.py — Settings に基づく Broker クライアント生成
    - kabu_client.py — kabu station の HTTP/WebSocket クライアント
    - mock_client.py — テスト用 MockBrokerClient
    - order_record.py — 注文状態モデルと遷移検証
    - order_repository.py — SQLite を使った永続化層
    - order_manager.py — DB + broker を組み合わせた発注 API
    - execution_engine.py — セッション／発注ループの本体
    - reconciler.py — 再起動時の注文照合とポジション差分検出
    - risk_manager.py — Gate1/2/3 の実装

  - monitoring/
    - monitoring_db.py — 監視用 DB 初期化とログ関数（参照）
    - system_monitor.py — システムリソース監視（参照）

  - data/
    - calendar_management.py — マーケットカレンダー管理（DuckDB）
    - news_collector.py — RSS ニュース収集と前処理

---

## 注意事項 / 制約

- 本リポジトリの実稼働（資金を使う運用）は慎重に行ってください。特に KABUSYS_ENV=live の動作や外部 API 連携は安全確認が必要です（BrokerClientFactory は live を未実装にしている箇所があります）。
- .env は秘密情報を含むため Git にコミットしないでください。
- YAML 設定（config/*.yaml）は PyYAML がインストールされていないとパース検証がスキップされます（validate_config が警告します）。
- ネットワーク接続や外部 API に依存する機能はローカルテスト時にモックを使ってください（paper_trading / MockBrokerClient）。

---

## 追加情報 / トラブルシューティング

- validate_config が .env のプレースホルダ（your_value や *_here）を検出した場合は警告を出します。--strict を使うとそれをエラー扱いにできます。
- モニタリング / 実行プロセスの停止は data/stop_requested.flag を作成するとループが検知して終了します。
- PID ファイルはデフォルトで data/execution.pid に作成されます（上書きされるので注意）。

---

必要であれば、README に含めるサンプル .env のテンプレート、requirements.txt の想定内容、さらに詳細な起動シナリオ（Docker / systemd ユニット例）なども追記します。どの情報を追加しますか？