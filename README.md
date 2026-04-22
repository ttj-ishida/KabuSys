# KabuSys

日本株自動売買システムのコアライブラリ（README）

このリポジトリは、シンプルな発注エンジン・モニタリング・データ処理基盤の核を提供します。実行環境はローカル（開発）／ペーパートレード（検証）／本番（live）を想定しており、.env による設定管理、DuckDB / SQLite を使ったデータ永続化、kabuステーション向けクライアント（Mock クライアント含む）などを備えています。

項目:
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 使い方（主要スクリプト）
- ディレクトリ構成
- よくある注意点 / トラブルシューティング

---

## プロジェクト概要

KabuSys は次の責務を持つモジュール群で構成されています（抜粋）:

- 設定管理: .env の自動読み込み / Settings クラス（kabusys.config）
- 環境セットアップ: 対話式ウィザードで .env を生成（kabusys.config_setup）
- 設定検証: 起動前に環境変数や config/*.yaml をチェック（kabusys.validate_config）
- 発注エンジン: Signal を読み発注・状態管理を行う ExecutionEngine（kabusys.execution）
  - Broker API 層（抽象プロトコル）：Mock / KabuStation 実装
  - OrderRecord / OrderRepository / OrderManager / RiskManager / Reconciler
- 監視（Monitoring）: SystemMonitor のポーリング（run_monitoring）
- データ処理: マーケットカレンダー管理、ニュース収集等（kabusys.data）
- テスト用モック: MockBrokerClient による発注挙動の模擬

設計方針の例:
- ビジネスロジックと永続化を分離（OrderRecord は DB に触らない）
- 再起動耐性（OrderSent 中のクラッシュ対策 → Reconciler）
- 3 段階のリスクガード（Gate1/2/3）

---

## 機能一覧

主な機能:

- .env 対話式ウィザード（kabusys.config_setup）
- 設定検証 CLI（kabusys.validate_config）
  - 必須環境変数チェック、KABUSYS_ENV 検証、YAML パース（PyYAML 使用時）
  - --strict で警告も失敗扱い
- 発注エンジン（ExecutionEngine）
  - signal 読み込み → Gate1/2 を通して発注 → WebSocket push 処理（realtime 同期）
  - ペーパートレード時は MockBrokerClient を利用（完全に本番 DB と分離）
  - kill_switch（全注文キャンセル）/ PID 管理 / stop flag チェック
- Broker クライアント群
  - KabuStationClient: kabuステーション REST / WebSocket（httpx, websocket-client）
  - MockBrokerClient: テスト用（fill_mode 等で挙動変更可）
- Order 永続化（SQLite）とリコンシリエーション（Reconciler）
- 監視ループ（run_monitoring）: SQLite + DuckDB を使用して監視情報を収集・保存
- データ側: カレンダー管理（DuckDB ベース）、ニュース収集（RSS、SSRF 防御等）

---

## セットアップ手順

前提:
- Python 3.9+（typing の一部構文を利用）
- システムに DuckDB/SQLite を使える環境

1. リポジトリをクローン・移動
   - 例: git clone <repo> && cd <repo>

2. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - Linux/macOS: source .venv/bin/activate
   - Windows: .venv\Scripts\activate

3. 必要パッケージをインストール
   - 代表的な依存（プロジェクトに requirements.txt がない場合の例）:
     - pip install duckdb httpx websocket-client defusedxml
     - YAML の内容検証をしたい場合: pip install pyyaml
   - （選択）ニュース収集に defusedxml を使うため defusedxml は必要

4. .env を作成
   - 対話式ウィザードを使う:
     - python -m kabusys.config_setup
   - あるいは手動でプロジェクトルートに .env を作成
   - .env は絶対に Git にコミットしないでください

5. 設定検証（起動前確認）
   - python -m kabusys.validate_config
   - 警告も失敗扱いにしたい場合:
     - python -m kabusys.validate_config --strict

6. データディレクトリ（data 等）の確認
   - デフォルト DB パスは data/ 以下。必要に応じてディレクトリを作成してください（多くは起動時に自動作成されますが権限エラー等に注意）。

---

## 環境変数（主要なもの）

必須:
- JQUANTS_REFRESH_TOKEN: J-Quants API 用リフレッシュトークン
- KABU_API_PASSWORD: kabuステーション API パスワード

主な任意 / 設定:
- KABUSYS_ENV: 実行環境（development / paper_trading / live）デフォルト: development
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: SQLite（監視 DB）パス（デフォルト: data/monitoring.db）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）デフォルト: INFO
- KABU_API_BASE_URL: kabu station ベース URL（デフォルト: http://localhost:18080/kabusapi）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: LINE 通知（任意）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（0/1、デフォルト 0）
- PAPER_FILL_MODE: paper_trading 用の fill 挙動（instant|partial|never|reject）
- PAPER_TRADING_SQLITE_PATH: paper_trading 専用 SQLite（デフォルト: data/paper_trading.db）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）

自動ロード:
- プロジェクトルートの .env を自動で読み込みます（OS 環境変数が優先）。
- .env.local があれば上書き読み込みされます。
- 自動読み込みを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## 使い方（主要スクリプト）

- 環境ウィザード（.env を作る）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - strict モード（警告も失敗扱い）
    - python -m kabusys.validate_config --strict

- 発注エンジンを起動（通常は systemd / supervisor 等で実行）
  - python -m kabusys.run_execution
  - 注意: KABUSYS_ENV が paper_trading や development の場合は MockBrokerClient が使用されます。live は実装上未提供の箇所があります（BrokerFactory が NotImplementedError を出す場合があります）。

- 監視ループを起動
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL を環境変数で上書き可（秒）。例: MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

ログ・制御:
- PID ファイル: デフォルト data/execution.pid（Settings.pid_file_path）
- 停止フラグ: data/stop_requested.flag を置くとループは検知して終了
- kill.flag（Settings.kill_flag_path）: 存在すると起動を拒否または kill_switch を発動

---

## ディレクトリ構成（主要ファイル）

src/kabusys/
- __init__.py
- config.py                — 環境変数と Settings
- config_setup.py          — .env 対話式ウィザード
- validate_config.py       — 設定検証 CLI
- run_execution.py         — ExecutionEngine 起動スクリプト
- run_monitoring.py        — SystemMonitor ポーリングスクリプト

src/kabusys/execution/
- __init__.py
- broker_api.py            — Broker API の Protocol / データモデル / ファクトリ
- kubu_client.py           — KabuStationClient 実装（httpx/websocket）
- mock_client.py           — MockBrokerClient（テスト用）
- broker_factory.py        — 設定に応じたクライアント生成
- execution_engine.py      — ExecutionEngine（主要な発注ループ）
- order_record.py          — OrderRecord（状態遷移ロジック）
- order_repository.py      — SQLite 永続化層
- order_manager.py         — 発注フロー（OrderManager）
- reconciler.py            — 起動時リコンシリエーション
- risk_manager.py          — 3 段階リスクガード

src/kabusys/monitoring/
- monitoring_db.py         — 監視 DB 初期化・ログ（参照される）

src/kabusys/data/
- calendar_management.py   — マーケットカレンダー管理（DuckDB）
- news_collector.py        — RSS ニュース収集

utils 等:
- utils/logging_setup.py
- utils/process_priority.py

（注）一部ファイル・モジュールは README 用に抜粋しています。実際のファイル構成はリポジトリを参照してください。

---

## 注意点・トラブルシューティング

- .env を Git にコミットしないでください（シークレット情報含む）。
- validate_config は PyYAML がなければ YAML 内容検証をスキップします（警告が出ます）。YAML のパース検証をしたい場合は pyyaml をインストールしてください。
- KABUSYS_ENV=live は慎重に設定してください。コード中に「本番のみの追加チェック」があり、LINE の通知設定や KILL_FLAG_CLEAR_ON_START の値などをチェックします。
- run_execution は stop フラグ（data/stop_requested.flag）や kill.flag を監視します。開発時にファイルの残存があると起動を拒否されるため注意してください。
- DB の親ディレクトリがない場合は起動時に自動作成される場合がありますが、権限エラーに注意してください。
- 本リポジトリの MockBrokerClient は単体テストやローカル検証向けに設計されています。実運用（ライブブローカー接続）の場合は別途実装の確認が必要です（BrokerFactory は live 用クライアントを未実装の箇所があります）。

---

必要であれば、README に
- requirements.txt の候補
- systemd ユニットファイルの例
- サンプル .env.example
などを追加で作成します。どれが必要か教えてください。