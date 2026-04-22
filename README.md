# KabuSys

日本株自動売買システム（KabuSys）のコードベース用 README。

このドキュメントはリポジトリ内の主要スクリプト・設定・ディレクトリ構成と、ローカルでのセットアップ／起動手順を簡潔にまとめたものです。

---

## プロジェクト概要

KabuSys は日本株の自動売買を想定した小規模なトレーディングフレームワークです。  
主な責務は以下の通りです：

- シグナルに基づく発注フロー（ExecutionEngine）
- ブローカー API 抽象化（kabu station 実装／Mock 実装）
- 注文永続化（SQLite）
- 起動時のリコンシリエーション（Reconciler）
- 3段階のリスクガード（RiskManager）
- 監視ループ（SystemMonitor）および監視データ保存（SQLite / DuckDB）
- 環境設定ウィザード（.env 作成補助）と設定検証 CLI

設計方針として、ブローカー API 層と永続化層を分離し、クラッシュ後の復旧（注文状態の照合）を想定した堅牢な実装になっています。Paper Trading（モック）モードと Live モードを想定していますが、Live ブローカークライアントは未実装の箇所があります（コード内に該当箇所の注釈あり）。

---

## 主な機能一覧

- 環境設定ウィザード（対話式 .env 生成）: python -m kabusys.config_setup
- 起動前設定検証 CLI（.env + config/*.yaml 検査）: python -m kabusys.validate_config
- ExecutionEngine 起動スクリプト（発注エンジン）: python -m kabusys.run_execution
- Monitoring 起動スクリプト（監視ループ）: python -m kabusys.run_monitoring
- Broker API 抽象化（Protocol）と実装:
  - MockBrokerClient（テスト用）
  - KabuStationClient（kabu station REST API 実装）
- 注文状態管理（OrderRecord / OrderState）と状態遷移検証
- 注文永続化（SQLite を使用する OrderRepository）
- 起動時のリコンシリエーション（OrderSent の突合せ、ポジション差分検出）
- RiskManager による Gate1..3 の多層リスク検査（重複・余力・レート制限・サーキットブレーカー・ドローダウン等）
- DuckDB を用いたシグナル/ポートフォリオ操作・マーケットカレンダー管理・ニュース収集モジュール（RSS）

---

## 前提（Prerequisites）

- Python 3.10 以上（typing の新しい構文を使用）
- SQLite（標準ライブラリ）
- 推奨パッケージ（一例）:
  - duckdb
  - httpx
  - websocket-client
  - defusedxml
  - PyYAML（config/*.yaml のパース検証に使用。オプションだが推奨）
  - その他、要求されるパッケージは各モジュールの import を参照してください。

インストール例（仮に requirements.txt があれば）:
- pip install -r requirements.txt

または最小限のインストール例:
- pip install duckdb httpx websocket-client defusedxml pyyaml

（実際の依存関係はプロジェクトに同梱の requirements / pyproject.toml を参照してください）

---

## セットアップ手順

1. リポジトリをクローン / checkout
2. 仮想環境を用意してアクティベート
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 必要パッケージをインストール
   - pip install duckdb httpx websocket-client defusedxml pyyaml
4. .env の作成（対話式ウィザード）
   - python -m kabusys.config_setup
     - 対話形式で各種環境変数を設定します。
     - J-Quants トークンや kabu API のパスワードなど機密値はマスク入力の形で扱います。
5. 設定検証（起動前チェック）
   - python -m kabusys.validate_config
   - 警告も失敗扱いにしたい場合は --strict を付けます:
     - python -m kabusys.validate_config --strict
6. DB 初期化（必要に応じて）
   - Execution / Monitoring は起動時にテーブルを作成する関数を呼びます（init_orders_db / init_monitoring_db 等）。
   - 環境に応じて data ディレクトリを作成しておくと良いです:
     - mkdir -p data

---

## 環境変数（主なもの）

必須（起動前に必ず設定してください）
- JQUANTS_REFRESH_TOKEN : J-Quants API 用リフレッシュトークン
- KABU_API_PASSWORD     : kabuステーション API パスワード

任意 / 但し重要な設定
- KABUSYS_ENV           : 実行環境（development / paper_trading / live）
- DUCKDB_PATH           : DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH           : 監視 DB の SQLite パス（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH : ペーパートレーディング専用 SQLite（デフォルト data/paper_trading.db）
- LOG_LEVEL             : ログレベル（DEBUG / INFO / WARNING / ERROR / CRITICAL）
- KABU_API_BASE_URL     : kabu station のベース URL（デフォルト http://localhost:18080/kabusapi）
- LINE_CHANNEL_ACCESS_TOKEN : LINE 通知用（任意）
- LINE_USER_ID          : LINE 通知先（任意）
- KILL_FLAG_PATH        : kill.flag のパス（デフォルト data/kill.flag）
- KILL_FLAG_CLEAR_ON_START : 起動時に kill.flag を自動クリアするか（0/1）
- PID_FILE_PATH         : PID 保存先（デフォルト data/execution.pid）
- MONITOR_POLL_INTERVAL : run_monitoring のポーリング間隔（秒、デフォルト 60）

注意:
- KABUSYS_ENV=live にセットすると validate_config が警告を出します。実行は十分注意してください（本番環境での発注は取り返しがつきません）。
- .env は絶対に Git 管理下にコミットしないでください（config_setup の出力にもその注意文があります）。

---

## 使い方（主要スクリプト）

- 環境設定ウィザード（.env 生成）
  - python -m kabusys.config_setup
  - 対話形式で値を入力し、.env に保存します。

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告もエラー扱い（exit 1）になります。

- 実行エンジン（発注）
  - python -m kabusys.run_execution
  - KABUSYS_ENV が paper_trading の場合は MockBrokerClient を使用して data/paper_trading.db に記録します。
  - 実行中は data/execution.pid に PID が書き出され、停止には data/stop_requested.flag または kill.flag による制御を利用します。

- 監視ループ（System Monitor）
  - python -m kabusys.run_monitoring
  - デフォルトのポーリング間隔は 60 秒。環境変数 MONITOR_POLL_INTERVAL で上書きできます。

実行上のフラグ/ファイル:
- data/stop_requested.flag : このファイルが存在すると監視／実行ループは安全に終了します。
- data/kill.flag : 実行中のキルスイッチとして使用される。ExecutionEngine は起動時に kill.flag が存在すると起動を拒否する（KILL_FLAG_CLEAR_ON_START=1 の場合はクリアして起動）。
- data/execution.pid : ExecutionEngine が PID を書き込みます。

---

## よくあるトラブルと対処

- PyYAML が無くて config/*.yaml の詳細検証がスキップされる:
  - pip install pyyaml
- KabuStationClient の接続エラー / 認証エラー:
  - KABU_API_BASE_URL, KABU_API_PASSWORD の設定を確認してください。
- .env が読み込まれない / テストで環境を汚したくない:
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 をセットすると自動ロードを無効化できます。
- 本番起動前に設定チェックを徹底する:
  - python -m kabusys.validate_config --strict を CI 等で使うのが有効です。

---

## ディレクトリ構成（抜粋）

（src/kabusys 以下の主要ファイルと役割を示します）

- src/kabusys/
  - __init__.py                 — パッケージ定義、バージョン
  - config.py                   — 環境変数/.env 読み込み・Settings クラス
  - config_setup.py             — 対話式 .env 生成ウィザード
  - validate_config.py          — 起動前の設定検証 CLI
  - run_execution.py            — ExecutionEngine 起動スクリプト
  - run_monitoring.py           — SystemMonitor ポーリングループ起動スクリプト
  - execution/
    - __init__.py
    - broker_api.py             — Broker API の Protocol / データモデル / ファクトリ
    - kabu_client.py            — kabu station REST API クライアント
    - mock_client.py            — テスト用 MockBrokerClient
    - broker_factory.py         — Settings に応じてブローカークライアントを生成
    - order_record.py           — 注文状態モデルと状態遷移ロジック
    - order_repository.py       — SQLite 永続化層
    - order_manager.py          — 注文管理（状態遷移 / 発注フロー）
    - execution_engine.py       — セッション制御・シグナル処理・WebSocket push 処理
    - reconciler.py             — 起動時リコンシリエーション（OrderSent 照合等）
    - risk_manager.py           — Gate1..3 のリスク検査
  - data/
    - calendar_management.py    — マーケットカレンダー管理（DuckDB）
    - news_collector.py         — RSS ニュース収集・前処理
    - (その他 jquants_client 等)
  - monitoring/
    - monitoring_db.py          — 監視用 DB 初期化 / ログ関数（実装ファイルが存在）
    - system_monitor.py         — SystemMonitor 実装（実装ファイルが存在）
  - utils/
    - logging_setup.py          — ロギング設定ユーティリティ
    - process_priority.py       — プロセス優先度設定ユーティリティ
  - config/                     — YAML 設定ファイル群（system_config.yaml 等を想定）
  - data/                       — 実行時に使用する DB / フラグ / PID ファイル等

---

## 開発メモ / 注意事項

- Execution ロジックではクラッシュ耐性（2相永続化、OrderSent の扱いなど）を考慮しています。設計上、OrderSent 状態のレコードはリコンシリエーション対象となり、起動時に外部ブローカーと突合されます。
- Live ブローカー（kabu station）との統合は本番を想定するため、KABUSYS_ENV=live の設定は慎重に扱ってください。validate_config は live 環境で警告を出します。
- .env は機密情報を含むため、絶対に Git にコミットしないでください。
- DuckDB / SQLite のパスはデフォルトで data ディレクトリ下に書き込まれます。適切なバックアップやパーミッション管理を行ってください。

---

必要であれば、README に含める実行例（例: .env のサンプル、具体的な system_config.yaml/strategy_config.yaml のテンプレート、CI での validate_config 実行コマンドなど）を追加で作成します。どの情報をさらに詳しく書いてほしいか教えてください。