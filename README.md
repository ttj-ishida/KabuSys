# KabuSys README

KabuSys は日本株向けの自動売買基盤（プロトタイプ）です。シグナルに基づく発注フロー、リスクガード、リコンシリエーション、監視ループ、ローカル／モックブローカーなどを備え、開発・ペーパートレードでの検証を主目的としています。

主な設計方針
- ビジネスロジックと永続化（SQLite）を分離
- 発注フローはクラッシュ耐性を意識した多段永続化（OrderCreated → OrderSent → broker_order_id 保存 → OrderAccepted など）
- 3段階リスクガード（Gate1: シグナル、Gate2: API エグゼキューション、Gate3: ドローダウン監視）
- ペーパートレード時は MockBrokerClient を使用して本番 DB と分離
- .env / .env.local を使った環境設定（自動ロードあり）

---

## 機能一覧
- 環境設定ウィザード（対話式 .env 作成）: python -m kabusys.config_setup
- 設定検証 CLI (.env と config/*.yaml のチェック): python -m kabusys.validate_config [--strict]
- ExecutionEngine（シグナル読込 → 発注 → push ドレイン）: python -m kabusys.run_execution
- SystemMonitor（監視ポーリングループ）: python -m kabusys.run_monitoring
- ブローカー抽象化層（Mock / 将来的に KabuStation）
- 注文状態管理（OrderRecord）と SQLite 永続化（OrderRepository）
- リスク管理（Rate limit, Circuit breaker, Drawdown, Position limits）
- リコンシリエーション（起動時の OrderSent 照合、ポジション差分検出）
- データ処理ユーティリティ（マーケットカレンダー、ニュース収集など）

---

## 必要な環境変数（主要）
必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

任意（ただし多くは運用で使用）:
- KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
- DUCKDB_PATH — デフォルト: data/kabusys.duckdb
- SQLITE_PATH — デフォルト: data/monitoring.db
- LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL) — デフォルト: INFO
- KABU_API_BASE_URL — kabu station のベース URL（デフォルト: http://localhost:18080/kabusapi）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID — 本番での通知設定
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（0/1）

設定は .env（および .env.local）が自動読み込みされます（OS 環境 > .env.local > .env）。自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`。

---

## セットアップ手順（開発環境向け）
1. Python 環境を用意（推奨: 3.10+）
2. 依存ライブラリをインストール（プロジェクトに requirements.txt があればそれを使用）  
   例（必要な主要パッケージ）:
   - duckdb
   - httpx
   - websocket-client
   - defusedxml
   - PyYAML（YAML 検証を行う場合）
   - そのほか標準ライブラリ以外のパッケージ

   例:
   pip install duckdb httpx websocket-client defusedxml pyyaml

3. プロジェクトルートに移動し、.env を準備
   - 対話式で生成するには:
     python -m kabusys.config_setup
   - もしくは .env を直接作成（下の「.env 例」参照）

4. 設定を検証:
   python -m kabusys.validate_config
   - 警告もエラー扱いにする場合:
     python -m kabusys.validate_config --strict

5. 実行:
   - 監視ループ:
     python -m kabusys.run_monitoring
     （環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可）
   - 発注エンジン（Execution）
     python -m kabusys.run_execution
     ※ KABUSYS_ENV=paper_trading のときは paper_trading 用 SQLite に記録され、本番 DB と分離される

注: monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する点に注意してください（監視は本番 DB を参照する設計）。

---

## .env の例
config_setup が生成するデフォルト構成の一部（例）:
JQUANTS_REFRESH_TOKEN=your_value
KABU_API_PASSWORD=your_value
KABU_API_BASE_URL=http://localhost:18080/kabusapi
LINE_CHANNEL_ACCESS_TOKEN=
LINE_USER_ID=
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
KABUSYS_ENV=development
LOG_LEVEL=INFO
KILL_FLAG_CLEAR_ON_START=0

重要: .env は敏感情報を含むため、絶対に Git にコミットしないでください。

---

## 使い方（主要コマンド）
- 環境ウィザード（.env 作成/更新）
  python -m kabusys.config_setup

- 設定検証
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict

- 実行エンジン起動（本番相当のセッション実行）
  python -m kabusys.run_execution

  特記事項:
  - 起動時に data/kill.flag が存在すると、KILL_FLAG_CLEAR_ON_START に応じて起動拒否またはクリアされます。
  - PID ファイルはデフォルトで data/execution.pid に書き出されます。

- 監視ループ起動
  python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を指定可能（デフォルト 60）
  - 停止は data/stop_requested.flag ファイルを配置することで行います

---

## 運用ファイル・フラグ
- 停止要求ファイル:
  data/stop_requested.flag — 存在すると監視・実行ループが終了（検知時に安全に停止）
- Kill スイッチ:
  data/kill.flag — 発注ループで検知した際に全 active 注文をキャンセルして停止
- PID ファイル:
  data/execution.pid（デフォルト） — 実行エンジンが起動時に書き出す

---

## 重要な挙動と注意点
- KABUSYS_ENV:
  - development / paper_trading / live のいずれか。live は本番想定（現状 Live broker client は未実装でエラーになります）。
  - paper_trading: 発注はモックで処理され、paper_trading 用 SQLite（デフォルト data/paper_trading.db）に記録されます（本番データと分離）。

- 発注のクラッシュ耐性:
  - 発注は複数段階で永続化されるため、クラッシュ後でも Reconciler により broker 側と照合して状態回復を試みます。

- 設定自動ロード:
  - デフォルトで OS 環境 > .env.local > .env の順に読み込まれます（既に OS 環境にあるキーは上書きされません）。
  - 自動ロードを無効化する場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

- YAML 検証:
  - validate_config は PyYAML がインストールされていれば config/*.yaml をパース検証します。PyYAML がない場合は警告を出して検証をスキップします。

---

## 主要ディレクトリ構成（抜粋）
- src/kabusys/
  - __init__.py
  - config.py — 環境変数読み込み・Settings 定義（.env 自動読み込み含む）
  - config_setup.py — .env 対話式ウィザード
  - validate_config.py — 起動前チェック CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor 起動スクリプト
  - execution/
    - broker_api.py — Broker API のデータモデル・Protocol・ファクトリ
    - broker_factory.py — Settings に基づくブローカーファクトリ
    - kabu_client.py — kabu station REST クライアント（HTTP/WebSocket 実装）
    - mock_client.py — テスト用 MockBrokerClient
    - order_record.py — 注文状態モデルと遷移ロジック
    - order_repository.py — SQLite 永続化層（orders テーブル初期化含む）
    - order_manager.py — 発注・同期・キャンセルの高レベル API
    - execution_engine.py — 発注ループ / WebSocket ドレイン / セッション制御
    - reconciler.py — OrderSent 照合とポジション差分検出
    - risk_manager.py — Gate1/2/3 のリスクガード実装
  - data/
    - calendar_management.py — マーケットカレンダー / 営業日ロジック
    - news_collector.py — RSS 収集と前処理（セキュリティ考慮）
  - monitoring/ (監視 DB 初期化や SystemMonitor 実装がある想定)
  - utils/
    - logging_setup.py — ロギング設定ユーティリティ
    - process_priority.py — プロセス優先度設定ユーティリティ

（上記はソースコード内の主要ファイルを抜粋しています。実際のリポジトリではさらに補助モジュールやスクリプトが存在する可能性があります。）

---

## 開発・拡張メモ
- Live broker client（kabu station 実装）の本格導入には KabuStationClient の利用を検討。現在は MockBrokerClient が test/dev 用として安定。
- Reconciler と OrderManager の協調によりクラッシュ後の自動回復を実現しているため、テストでは list_uncertain()/sync_order() に対する挙動を重点的に確認してください。
- calendar_update_job は J-Quants API との連携を想定（jquants_client モジュール参照）。夜間バッチ処理の運用スケジュールを検討してください。
- セキュリティ: .env に秘密情報が含まれるため運用時は適切なアクセス制御とシークレット管理を検討してください。

---

この README はコードベースから抽出した情報をまとめたものです。実行時の詳細や追加のユーティリティはリポジトリ内のスクリプトとドキュメント（存在する場合）を参照してください。必要であれば、README に含めるサンプル .env.example や起動スクリプトの systemd ユニット例なども作成できます。必要なら指示してください。