# KabuSys

日本株自動売買システムのコアライブラリ（README）。  
この README はリポジトリ内のソースコードに基づき、プロジェクト概要・機能・セットアップ・使い方・ディレクトリ構成を日本語でまとめたものです。

注意: 本リポジトリは一部コンポーネントをモックで提供しており、"live" 環境向けの実ブローカークライアントは未実装です（KABUSYS_ENV=live を指定すると例外になります）。

---

## プロジェクト概要

KabuSys は日本株の自動売買を行うためのモジュール群です。  
主な責務は次の通りです：

- シグナルに基づく発注エンジン（ExecutionEngine）
- ブローカー API 抽象化（kabuステーション実装 / モック実装）
- 注文の永続化と状態管理（SQLite）
- 起動時リコンシリエーション（クラッシュ後復旧）
- 発注フローに対する 3 段階のリスクガード（Gate1/2/3）
- 監視ループ（SystemMonitor）と監視データ保存
- データ側ユーティリティ（マーケットカレンダー、ニュース収集 等）
- 環境設定ウィザード、起動前設定検証ツール

設計方針として、DB（SQLite / DuckDB）とブローカー呼び出しを分離し、クラッシュ耐性（2相永続化による整合性）や安全停止（kill switch）を重視しています。

---

## 主な機能一覧

- 環境設定ウィザード（.env を対話式に生成/更新）
  - `python -m kabusys.config_setup`
- 起動前の設定検証（必須環境変数・YAML 等の検査）
  - `python -m kabusys.validate_config [--strict]`
- ExecutionEngine
  - シグナル読み取り（DuckDB）→ 発注（kabuステーション or モック）
  - WebSocket Push ドレイン処理
  - kill switch による安全停止と全注文キャンセル
- モックブローカー（テスト用）
  - fill_mode: instant / partial / never / reject
- Order 管理
  - OrderRecord（状態機械）・OrderManager（API 呼び出しフロー）・OrderRepository（SQLite 永続化）
- リスク管理
  - Gate1: シグナルレベル（余力、重複、ポジション上限）
  - Gate2: エグゼキューション（レート制限、サーキットブレーカー）
  - Gate3: 約定後のドローダウン監視
- リコンシリエーション（再起動時の同期）
- 監視ループ（run_monitoring）で監視 DB にログ出力
- データユーティリティ
  - カレンダー管理（JPX カレンダーの取得・判定）
  - ニュース収集（RSS） — SSRF 対策・XML攻撃対策（defusedxml）

---

## 必須 / 任意環境変数

必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

任意（デフォルトありまたはオプション）:
- KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
- DUCKDB_PATH — デフォルト: data/kabusys.duckdb
- SQLITE_PATH — デフォルト: data/monitoring.db（監視 DB）
- PAPER_TRADING_SQLITE_PATH — paper_trading 用 DB（デフォルト: data/paper_trading.db）
- LOG_LEVEL — DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）
- KABU_API_BASE_URL — kabu station ベース URL（デフォルト: http://localhost:18080/kabusapi）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID — 本番通知（任意）
- KILL_FLAG_CLEAR_ON_START — 起動時 kill.flag を自動クリアするか（0/1）

その他（監視・プロセス等）:
- PID_FILE_PATH, KILL_FLAG_PATH, MONITOR_POLL_INTERVAL, PAPER_FILL_MODE, etc.

自動 .env ロード:
- プロジェクトルートの `.env` と `.env.local` を自動で読み込みます（OS 環境変数が優先）。
- 自動ロードを無効にする場合: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

---

## セットアップ手順 (開発 / 実行に必要な準備)

1. 必要な Python バージョン
   - Python 3.10 以上（型記法や構文で 3.10 の union 型 `X | Y` を使用）

2. 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージのインストール  
   以下は主にコードで使われているパッケージ例です（リポジトリに requirements.txt がある場合はそちらを使用してください）。
   - pip install duckdb httpx websocket-client pyyaml defusedxml

   注意:
   - sqlite3 は標準ライブラリに含まれます。
   - PyYAML がない場合、設定検証（validate_config）の YAML パースはスキップされます（警告）。

4. .env の作成
   - 対話式で作成する: python -m kabusys.config_setup
   - 既存の .env がある場合は `.env.local` で上書き可能

5. 設定検証（起動前に推奨）
   - python -m kabusys.validate_config
   - 厳密モード（警告も失敗扱い）: python -m kabusys.validate_config --strict

6. DB 初期化
   - Execution / Monitoring が起動時に必要なテーブルを作成します（init_* 関数が冪等で行います）。
   - 事前に手動でディレクトリを作る場合: mkdir -p data

---

## 使い方（実行例）

- 設定ウィザード（.env 作成・更新）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- 実行エンジン（ExecutionEngine）
  - 本番風の挙動をローカルで試す（ペーパートレード: モックブローカー使用）
    - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  - 開発（モック）
    - KABUSYS_ENV=development python -m kabusys.run_execution
  - live 環境は未実装（create_broker_api および BrokerClientFactory が NotImplementedError を投げます）

- 監視ループ
  - python -m kabusys.run_monitoring
  - ポーリング間隔を変更: MONITOR_POLL_INTERVAL=10 python -m kabusys.run_monitoring

- 停止制御
  - プロセスに対する外部停止: プロジェクトルートの `data/stop_requested.flag` ファイル作成でループを検出して終了します。
  - 起動拒否（kill switch）: `data/kill.flag` を置くと ExecutionEngine 起動時に拒否されます。KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に自動でクリアして強制起動します（本番では 0 推奨）。

---

## 開発時のポイント

- モックブローカー
  - BrokerFactory は development / paper_trading 環境で `MockBrokerClient` を返します。テストはこれで完結できます。
  - Mock の fill_mode は `PAPER_FILL_MODE` または Settings.paper_fill_mode で制御（instant/partial/never/reject）。

- 注文フローの耐障害性
  - OrderManager.send_order は「OrderSent を先に永続化 → ブローカー呼び出し → broker_order_id を永続化 → OrderAccepted に遷移」という2相永続化の設計を採用し、クラッシュ後の照合（Reconciler）で復旧可能です。

- リスク制御
  - Circuit breaker / token bucket（レート制限） / ポジション・ドローダウン監視を実装済み。

- WebSocket Push
  - KabuStation の push を受けるための `stream_push` インターフェースを Broker に実装していれば、ExecutionEngine が別スレッドで受信して処理します。
  - MockBrokerClient は `stream_push` を提供しないため WebSocket スレッドはスキップされます（warning が出ます）。

---

## 主要ファイル・ディレクトリ構成

（ソースは `src/kabusys` 配下にあります。主要モジュールを抜粋しています。）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / .env 自動ロードと Settings
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 起動前設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py       — SystemMonitor ポーリング起動スクリプト

  - execution/               — 発注関連（API 抽象化・エンジン・管理）
    - __init__.py
    - broker_api.py          — BrokerAPIProtocol, データモデル, factory
    - broker_factory.py      — Settings に基づくクライアント生成
    - kabu_client.py         — kabuステーション実装（httpx + websocket）
    - mock_client.py         — モックブローカー（テスト用）
    - execution_engine.py    — ExecutionEngine（シグナル処理、push ドレイン）
    - order_record.py        — Order 状態遷移ロジック（純粋モデル）
    - order_repository.py    — SQLite 永続化（orders テーブル）
    - order_manager.py       — 発注フロー（create/send/sync/cancel）
    - reconciler.py          — 起動時リコンシリエーション
    - risk_manager.py        — Gate1/2/3 の実装

  - monitoring/              — 監視関連（Monitoring DB, SystemMonitor 等）
    - monitoring_db.py       — 監視 DB 初期化・ログ機能（参照）
    - system_monitor.py      — システム監視ロジック（参照）

  - data/                    — データ関連ユーティリティ
    - calendar_management.py — マーケットカレンダーの取得・営業日判定
    - news_collector.py      — RSS ニュース収集（SSRF/XML 攻撃対策）
    - jquants_client.py      — J-Quants API ラッパ（参照）

  - utils/
    - logging_setup.py       — ログ設定ユーティリティ
    - process_priority.py    — プロセス優先度設定ユーティリティ

- data/                      — 実行環境で使用する DB / フラグファイル（自動作成推奨）
  - stop_requested.flag
  - kill.flag
  - monitoring.db
  - kabusys.duckdb
  - execution.pid
  - ...（データファイル）

---

## 実行例（シンプルな流れ）

1. .env を作成
   - python -m kabusys.config_setup

2. 設定を検証
   - python -m kabusys.validate_config

3. ペーパートレードでエンジン実行
   - KABUSYS_ENV=paper_trading python -m kabusys.run_execution

4. 監視プロセスを実行（別プロセスで）
   - python -m kabusys.run_monitoring

---

## 注意事項 / 運用上のヒント

- .env は決してリポジトリにコミットしないこと（config_setup にも警告あり）。
- `KABUSYS_ENV=live` は本番想定だが、現在ライブラリ内で Live broker client が未実装のため利用不可です。実稼働は実装と十分な検証が必要です。
- validate_config は PyYAML がないと config/*.yaml のパースチェックをスキップします。YAML の内容チェックを行う場合は PyYAML をインストールしてください。
- kill.flag / stop_requested.flag によるプロセス制御や PID ファイル管理は慎重に運用してください（自動クリア設定は本番で危険になることがあります）。

---

## 貢献 / テスト

- ユニットテストや統合テストはモック（MockBrokerClient）を使って容易に作成できます。
- リコンシリエーション、Order 状態遷移、RiskManager の各ロジックはテスト対象として重要です。
- ニュース収集や外部 API 呼び出しはネットワークの外部依存をモック化してテストしてください。

---

この README はリポジトリ内のコードベースに基づいて作成しています。追加のドキュメント（DataPlatform.md 等）やスクリプト（scripts/generate_config.py）が存在する場合はそちらも併せて参照してください。質問や補足が必要であれば具体的に教えてください。