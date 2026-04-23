# KabuSys

日本株自動売買システム（KabuSys）のリポジトリ向け README。  
この README はコードベース（src/kabusys 以下）に基づいて日本語で作成しています。

---

## プロジェクト概要

KabuSys は、kabuステーション（ローカルの REST / WebSocket インターフェース）またはモックブローカーを用いて日本株の自動売買を行うためのコンポーネント群です。主に以下の責務を持ちます。

- 発注エンジン（ExecutionEngine）によるシグナル読み込み・発注
- ブローカークライアント（実ブローカー：KabuStationClient / テスト用モック：MockBrokerClient）
- 注文永続化（SQLite）および注文状態管理（OrderRecord）
- 起動時の自動リコンシリエーション（Reconciler）
- リスクガード（RiskManager：Gate1/2/3）
- 監視（SystemMonitor）と監視データ蓄積（SQLite/DuckDB）
- データ系ユーティリティ（マーケットカレンダー管理、ニュース収集など）
- .env 生成ウィザードと設定検証ツール

本リポジトリは、開発（development）、ペーパートレード（paper_trading）、本番（live）を想定した設定管理と実行フローを提供します。

---

## 主な機能一覧

- 設定管理
  - .env ファイル自動読み込み（.env, .env.local）
  - 対話式設定ウィザード（python -m kabusys.config_setup）
  - 設定検証 CLI（python -m kabusys.validate_config）
- 実行系
  - ExecutionEngine：シグナル読み込み・発注・WebSocket ドレイン
  - Broker クライアント：KabuStationClient（実装） / MockBrokerClient（テスト向け）
  - OrderManager / OrderRepository：注文作成・送信・同期・キャンセル
  - Reconciler：起動時の OrderSent 状態の同期とポジション差分チェック
- リスク管理
  - RiskManager：Gate1（シグナル検査）/ Gate2（レート制限・CB）/ Gate3（ドローダウン監視）
- 監視
  - run_monitoring.py によるポーリング監視（SQLite + DuckDB）
  - 監視用 DB 初期化ユーティリティ
- データ処理（ユーティリティ）
  - マーケットカレンダー管理（DuckDB / J-Quants 連携）
  - ニュース収集（RSS → raw_news）
- 開発・運用補助
  - PID / stop フラグ、kill flag による安全停止制御
  - ロギング設定、プロセス優先度設定ユーティリティ

---

## 必要な環境変数（概要）

必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

任意（代表的なもの）:
- KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
- DUCKDB_PATH — デフォルト: data/kabusys.duckdb
- SQLITE_PATH — デフォルト: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH — Paper Trading 用 DB（デフォルト: data/paper_trading.db）
- LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL)
- KABU_API_BASE_URL — kabuステーション API のベース URL
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID — 本番アラート用（任意）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアする(0/1)

詳細は src/kabusys/validate_config.py と src/kabusys/config.py を参照してください。

---

## セットアップ手順（開発環境向け）

1. リポジトリをクローン
   - git clone <リポジトリ URL>

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要なパッケージをインストール  
   ※ requirements.txt が用意されている場合はそれを使用してください。なければ主要ライブラリを例示します:
   - pip install duckdb httpx websocket-client defusedxml pyyaml

   主に使用される外部パッケージ（抜粋）:
   - duckdb
   - httpx
   - websocket-client
   - defusedxml
   - PyYAML（config 検証を行う場合に推奨）

4. .env を作成
   - 対話式ウィザードを使う（推奨）
     - python -m kabusys.config_setup
   - または手動でプロジェクトルートに `.env` を作成して必要な環境変数を設定

5. 設定検証
   - python -m kabusys.validate_config
   - 警告も失敗扱いにする: python -m kabusys.validate_config --strict

6. DB 初期化（実行前に必要な場合）
   - Execution 系は起動時に SQLite/DuckDB を使用します。初期化ユーティリティ（init_orders_db, init_monitoring_db 等）を呼ぶコードがあるため、通常は実行スクリプトが自動で用意します。
   - 必要に応じて data ディレクトリを作成:
     - mkdir -p data

---

## 使い方（主要コマンド）

- 環境設定ウィザード（.env 作成 / 更新）
  - python -m kabusys.config_setup
  - 対話形式で .env を生成・更新します。生成後は python -m kabusys.validate_config で検証してください。

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告も exit code 1（FAIL）になります。

- 実行（Execution Engine）を起動
  - python -m kabusys.run_execution
  - KABUSYS_ENV が `paper_trading` の場合は MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に記録します。
  - プロセスは data/execution.pid に PID を書きます。
  - 停止手順: data/stop_requested.flag を作成すると安全に停止処理を行います。
  - 起動時に data/kill.flag が存在すると、KILL_FLAG_CLEAR_ON_START に依存して起動を拒否します。

- 監視ループを起動
  - python -m kabusys.run_monitoring
  - 環境にかかわらず監視は本番 sqlite_path を使用します（デフォルト data/monitoring.db）。
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL（秒）で上書き可能（デフォルト: 60）。

- モックブローカー（テスト用）
  - create_broker_api(mock=True, fill_mode="instant"|"partial"|"never"|"reject")
  - MockBrokerClient はテストでの発注・約定・キャンセルの挙動をシミュレートします。

- その他
  - stop フラグ: data/stop_requested.flag（Execution/Monitoring の外部停止）
  - kill フラグ: settings.kill_flag_path（デフォルト data/kill.flag） — エンジン内で kill_switch を発動するトリガー

---

## 運用上の注意

- .env は機密情報を含むため絶対に Git にコミットしないでください。
- 本番環境（KABUSYS_ENV=live）では LINE 通知の設定や KILL_FLAG_CLEAR_ON_START の値を慎重に確認してください（validate_config で注意喚起があります）。
- ExecutionEngine は発注ロジックで DB の状態とブローカーの状態を二相的に永続化する設計（クラッシュ耐性を考慮）になっています。実稼働前にペーパートレードで十分に検証してください。
- Reconciler により起動時の OrderSent 状態をブローカーと同期できますが、broker の API が失敗するケース等はログに注意してください。

---

## ディレクトリ構成（抜粋）

（プロジェクトルートから見た主要ファイル・ディレクトリ）

- src/
  - kabusys/
    - __init__.py
    - config.py                      — 環境変数読み込み / Settings クラス
    - config_setup.py                — .env 対話式ウィザード
    - validate_config.py             — 起動前検証 CLI
    - run_execution.py               — ExecutionEngine 起動スクリプト
    - run_monitoring.py              — SystemMonitor 起動スクリプト
    - execution/
      - __init__.py
      - broker_api.py                — Broker API のデータモデル / Protocol / ファクトリ
      - broker_factory.py            — Settings に基づく Broker クライアント生成
      - kabu_client.py               — kabuステーション実クライアント (HTTP/WS)
      - mock_client.py               — テスト用モッククライアント
      - order_record.py              — 注文状態モデル・状態遷移ロジック
      - order_repository.py          — SQLite 永続化層（orders テーブル）
      - order_manager.py             — 発注フローの外向き API
      - execution_engine.py          — シグナル処理 / WebSocket ドレイン / セッション管理
      - reconciler.py                — 起動時リコンシリエーション
      - risk_manager.py              — 3段階リスクガード
    - monitoring/
      - monitoring_db.py             — 監視用 DB 初期化・ログユーティリティ
      - system_monitor.py            — 実際の監視ロジック（run_monitoring で使用）
    - data/
      - calendar_management.py       — マーケットカレンダー管理（DuckDB, J-Quants）
      - news_collector.py            — RSS ニュース収集
      - jquants_client.py            — （J-Quants API 用クライアント、存在する前提）
    - utils/
      - logging_setup.py             — ログ初期化
      - process_priority.py          — プロセス優先度設定ユーティリティ
    - その他ユーティリティや補助モジュール...

- data/                               — デフォルトで使われる DB / フラグファイル群（生成される）
  - kabusys.duckdb (デフォルト)
  - monitoring.db (SQLite, デフォルト)
  - paper_trading.db (Paper Trading 用 SQLite)
  - execution.pid
  - stop_requested.flag
  - kill.flag

---

## 開発・テストのヒント

- Unit テストや統合テストでは MockBrokerClient を使うと外部依存を切り離せます。
- validate_config は PyYAML が未インストールだと YAML パース検証をスキップしますが、可能であれば PyYAML を入れておくことを推奨します。
- ExecutionEngine のセッション制御は時間帯（signal_send_start / end / market_close）に依存します。テストでは直接 _process_signals / _drain_push_queue を呼ぶことで時間依存性を排除できます。

---

必要であれば、README に以下の拡張を追加できます：
- インストール用の requirements.txt サンプル
- サービス化（systemd ユニット）やデプロイ手順
- 詳細な設定項目（全環境変数一覧と説明）テーブル
- さらに詳しいアーキテクチャ図 / シーケンス図

どの追加が必要か教えてください。