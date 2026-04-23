# KabuSys

日本株向け自動売買システム（プロジェクト骨格）。  
このリポジトリは発注エンジン・リスクガード・モニタリング・カレンダ／ニュース処理などの主要コンポーネントを含みます。

バージョン: 0.1.0

---

## 概要

KabuSys は kabu ステーション（ローカルの証券 API）や J-Quants 等の外部サービスと連携し、日本株の自動発注を行うためのコンポーネント群です。設計は次のような責務分離を意識しています。

- 設定管理（.env / 環境変数の読み込み・検証）
- ExecutionEngine（シグナル取得 → 発注 → リコンシリエーション）
- Broker クライアント（実ブローカー / モック）
- 注文永続化（SQLite）
- リスク管理（Gate1/Gate2/Gate3）
- 監視プロセス（SystemMonitor）
- データ処理（マーケットカレンダー、ニュース収集 など）

本 README では主要機能、セットアップ、使い方、およびディレクトリ構成を説明します。

---

## 機能一覧

- 環境設定ウィザード（対話式 `.env` 生成）: `python -m kabusys.config_setup`
- 設定検証 CLI（`.env` と config/*.yaml のチェック）: `python -m kabusys.validate_config`
  - `--strict` を付けると警告も失敗扱い（exit 1）
- ExecutionEngine（セッション実行、シグナル処理、push ドレイン、kill switch）
- OrderManager / OrderRecord / OrderRepository（状態遷移、DB 保存、クラッシュ耐性を考慮した永続化）
- Broker クライアント群
  - MockBrokerClient（テスト向け）
  - KabuStationClient（kabuステーション REST API 実装）
- RiskManager（3段階リスクガード: Signal / Execution / Metrics）
- Reconciler（起動時に OrderSent の注文をブローカーと突合）
- 監視ループ（SystemMonitor をポーリングして監視データを sqlite に記録）
- データモジュール
  - マーケットカレンダー管理（JPX カレンダーの取り込み、営業日判定）
  - ニュース収集（RSS 取得と前処理、安全対策付き）

---

## 必要なパッケージ（代表例）

- Python 3.9+
- duckdb
- httpx
- websocket-client
- defusedxml
- PyYAML（config YAML のパース検証に必要、未インストールでも警告でスキップ）
- （標準ライブラリ: sqlite3, logging, threading 等）

インストールはプロジェクトの pyproject / requirements を参照してください（このサンプルではファイルは省略）。

---

## セットアップ手順

1. リポジトリをクローンしてプロジェクトルートへ移動。

2. 仮想環境を作成・有効化し依存パッケージをインストール。

   例:
   - python -m venv .venv
   - source .venv/bin/activate
   - pip install duckdb httpx websocket-client defusedxml pyyaml

3. 環境変数ファイルの作成
   - 対話式ウィザード（推奨）:
     - python -m kabusys.config_setup
     - 画面の案内に従って .env を生成します。
   - 手動で .env を作る場合はプロジェクトルートに `.env` を配置します。
     - `.env.local` を用意すれば `.env` の上書き（OS の環境変数を除く）も可能。

4. 設定検証
   - python -m kabusys.validate_config
   - 警告もエラー扱いにする場合:
     - python -m kabusys.validate_config --strict

5. データベース初期化など（必要に応じて）
   - ExecutionEngine / Monitoring は起動時に必要テーブルを初期化するヘルパーを呼ぶ設計（例: init_monitoring_db / init_orders_db）。

---

## 主要環境変数

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants API のリフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API パスワード

重要（任意設定も可）:
- KABUSYS_ENV — 実行環境: development / paper_trading / live（デフォルト: development）
- DUCKDB_PATH — DuckDB のファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視 DB（デフォルト: data/monitoring.db）
- LOG_LEVEL — DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）
- KABU_API_BASE_URL — kabu station のベース URL（デフォルト: http://localhost:18080/kabusapi）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID — LINE 通知用（本番では設定推奨）
- PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START — 起動制御 / kill flag 関連

Execution / Paper trading 関連:
- PAPER_FILL_MODE — paper_trading 用の fill_mode（instant|partial|never|reject、デフォルト: instant）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード専用 SQLite（デフォルト: data/paper_trading.db）

監視関連:
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、デフォルト: 60）

自動ロード抑止:
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 — .env の自動読み込みを無効化（テスト等で利用）

注意:
- Settings モジュールはプロジェクトルート（.git または pyproject.toml）を基準に `.env` / `.env.local` を自動ロードします。OS 環境変数は優先されます。

---

## 使い方（コマンド）

- 環境ウィザード（対話式 .env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 厳密モード（警告も失敗にする）:
    - python -m kabusys.validate_config --strict

- 実行エンジン（Execution）
  - python -m kabusys.run_execution
  - 実行前に KABUSYS_ENV を設定:
    - paper_trading（モックブローカーを使用）:
      - export KABUSYS_ENV=paper_trading
      - python -m kabusys.run_execution
    - development もモックを使用

- 監視プロセス
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（秒）

- 注意点
  - 本リポジトリの KabuStationClient は実際の kabu ステーション API に依存します。ローカルで kabuステーションが動作していることが前提です（ただし paper_trading / development は MockBrokerClient が使われます）。
  - run_execution は PID ファイルや kill.flag を利用してプロセス間制御を行います（`data/execution.pid`, `data/kill.flag` 等）。

---

## .env の例（ウィザードが生成するデフォルトに基づく）

以下は生成される .env の主要項目例です（実際のトークンやパスワードは置き換えてください）。

JQUANTS_REFRESH_TOKEN=your_value_here
KABU_API_PASSWORD=your_value_here
KABU_API_BASE_URL=http://localhost:18080/kabusapi
LINE_CHANNEL_ACCESS_TOKEN=
LINE_USER_ID=
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
KABUSYS_ENV=development
LOG_LEVEL=INFO
KILL_FLAG_CLEAR_ON_START=0

---

## 開発・運用上の注意

- 設定検証は PyYAML があれば config/*.yaml の YAML パースもチェックします。PyYAML が未インストールの場合はスキップされます。
- `validate_config` は環境変数がプレースホルダ（例: endswith "_here" や "your_value"）の場合に警告を出します。
- ExecutionEngine はクラッシュ耐性を考慮した二相永続化（OrderSent 前後の扱い）や起動時の Reconciliation をサポートします。
- MockBrokerClient はテストで挙動を切り替えられるため、ローカル開発や CI 上で本番 API に依存せずテスト可能です。
- Security: `.env` は絶対に git にコミットしないでください（config_setup でもその旨の警告コメントが書き出されます）。

---

## ディレクトリ構成（主要ファイル）

src/kabusys/
- __init__.py — パッケージ定義、バージョン
- config.py — 環境変数の読み込み・Settings クラス（自動 .env ロードを含む）
- config_setup.py — 対話式 .env ウィザード（CLI）
- validate_config.py — 起動前設定検証 CLI
- run_execution.py — ExecutionEngine 起動スクリプト（メイン）
- run_monitoring.py — SystemMonitor 起動スクリプト
- execution/
  - __init__.py
  - broker_api.py — BrokerAPI のデータモデル・Protocol・ファクトリ・例外
  - kabu_client.py — 実ブローカー（kabu station）クライアント
  - mock_client.py — テスト用モックブローカー
  - broker_factory.py — Settings に基づくブローカー生成
  - order_record.py — Order 状態遷移ロジック（純粋モデル）
  - order_repository.py — SQLite を使った永続化層
  - order_manager.py — Order の外向き API（発注・同期・取消）
  - execution_engine.py — Signal Pull 型発注エンジン
  - reconciler.py — 起動時リコンシリエーション
  - risk_manager.py — Gate1/2/3 のリスク管理
- data/
  - calendar_management.py — マーケットカレンダー管理（DuckDB）
  - news_collector.py — RSS ニュース収集（XML パーサに defusedxml を使用）
  - jquants_client (想定) — J-Quants 連携クライアント（コードベースでの利用あり）
- monitoring/
  - monitoring_db.py (参照あり) — 監視 DB 初期化・ログ関数（プロジェクト内で使用）
- utils/
  - logging_setup.py — ロガー初期化ユーティリティ
  - process_priority.py — プロセス優先度設定ユーティリティ

（実際のサブモジュールは上のファイルリストに含まれているものを参照してください）

---

## 補足・参考

- `python -m kabusys.config_setup` 実行後は `python -m kabusys.validate_config` で検証することを推奨します。
- 本番（live）環境を使用する際は LINE 通知設定や KILL_FLAG_CLEAR_ON_START の値などを慎重に確認してください（validate_config は live 時に注意喚起を行います）。
- 監視やリコンシリエーション機構は、安全性を高めるための複数の防護層を備えています。実運用前にローカルでペーパートレード・モックを用いて十分にテストしてください。

---

必要であれば README にインストールコマンド（requirements.txt / poetry / pipx など）や CI のサンプル、より詳細な設定項目の表を追加します。追加希望があれば教えてください。