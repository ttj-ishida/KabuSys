# KabuSys

日本株向け自動売買システムのサンプル実装（KabuSys）。  
このリポジトリは発注ロジック、リスクガード、監視、リコンシリエーション、ダミーブローカー等を含む実践的な構成を備えています。

---

## プロジェクト概要

KabuSys は以下を主眼に設計された自動売買フレームワークです。

- シグナルに基づく発注エンジン（ExecutionEngine）
- 注文状態管理（OrderRecord / OrderManager / OrderRepository）
- リスクガード（3段階: Gate1/2/3）
- ブローカー抽象（実運用用の KabuStationClient とテスト用の MockBrokerClient）
- 起動時のリコンシリエーション（Reconciler）
- 監視ループ（SystemMonitor を用いる監視プロセス）
- 環境設定ウィザードと事前設定検証ツール（.env の作成 / 検証）

設計は「ビジネスロジックと永続化の分離」「クラッシュ耐性（2相永続化など）」「テスト容易性（MockClient）」を重視しています。

---

## 主な機能一覧

- 環境設定ウィザード（.env の対話的作成 / 更新）
- 起動前設定検証 CLI（必須環境変数や config/*.yaml の妥当性チェック）
- 発注エンジン（シグナル読み込み、リスクゲート、発注、push ドレイン）
- 注文状態の堅牢な管理（状態遷移検証、永続化、Uncertain 注文の検出）
- リコンシリエーション（起動時に OrderSent 状態をブローカーと突合）
- Mock ブローカー（fill_mode による instant/partial/never/reject の振る舞い）
- DuckDB を使ったデータ分析用ストレージ、SQLite を使った監視/注文履歴
- ニュース収集、マーケットカレンダー管理（DataPlatform の設計に基づく）

---

## 前提 / 依存ライブラリ（代表例）

以下は主要な依存です。実際の requirements はプロジェクトに合わせて管理してください。

- Python 3.9+
- duckdb
- httpx
- websocket-client
- PyYAML（config YAML のパースを行う場合）
- defusedxml
- その他標準ライブラリ（sqlite3, threading, pathlib, logging 等）

インストール例:
pip install duckdb httpx websocket-client pyyaml defusedxml

※ PyYAML が無い場合、validate_config は YAML の内容検証をスキップします（ファイル存在チェックは行います）。

---

## セットアップ手順

1. リポジトリをクローンしてワークディレクトリに移動
2. 仮想環境を作成・有効化（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 依存パッケージをインストール
   - pip install duckdb httpx websocket-client pyyaml defusedxml
4. 初期設定ファイル (.env) を作る
   - python -m kabusys.config_setup
     - 対話形式で .env を生成・更新します。生成後は .env を絶対に VCS にコミットしないでください。
5. 設定を検証
   - python -m kabusys.validate_config
   - 警告も FAIL にしたい場合: python -m kabusys.validate_config --strict

補足:
- 自動で .env を読み込む挙動
  - プロジェクトルートにある `.env` を既存の OS 環境変数を上書きしない形で読み込み、`.env.local` があればそれで上書きします。
  - 自動ロードを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## 主要な環境変数（必須 / 代表例）

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants API 用リフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API パスワード

任意/設定例:
- KABUSYS_ENV — 実行環境: development / paper_trading / live（デフォルト: development）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視 DB（デフォルト: data/monitoring.db）
- LOG_LEVEL — DEBUG / INFO / WARNING / ERROR / CRITICAL
- KABU_API_BASE_URL — kabu station API のベース URL
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — 通知用（本番では必須になる場合あり）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（0/1、デフォルト 0）

本番環境（KABUSYS_ENV=live）では LINE 通知設定や KILL_FLAG の扱いに注意してください（validate_config や実行時に警告が出ます）。

---

## 使い方（主要コマンド）

- 環境設定ウィザード（.env の作成 / 更新）
  - python -m kabusys.config_setup

- 設定検証（起動前チェック）
  - python -m kabusys.validate_config
  - --strict を付けると警告もエラー扱い（exit 1）

- 実行エンジン（発注プロセス）
  - python -m kabusys.run_execution
  - 注意: KABUSYS_ENV によって MockBrokerClient（paper_trading / development）を使います。本番用クライアント実装は未実装（live は NotImplementedError）。

- 監視プロセス（SystemMonitor のポーリングループ）
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可能（デフォルト 60）

実行上の安全策:
- 起動前に validate_config を実行して設定を確認してください。
- 起動時に存在する `data/kill.flag` を消さずに起動すると実行を拒否する設計です（KILL_FLAG_CLEAR_ON_START=1 の場合はクリアして起動可能）。
- 実行中に stop を指示するには `data/stop_requested.flag` を作成してください（スクリプトはこのフラグを監視して安全に終了します）。

---

## ディレクトリ構成（主要ファイル説明）

リポジトリルート（省略可）  
- config/             — 各種 config YAML (system_config.yaml 等)
- data/               — データファイル（DuckDB / SQLite / PID / フラグ等）
- src/kabusys/        — ソースコード本体

src/kabusys/ 以下の主要モジュール:

- __init__.py
  - パッケージ宣言・バージョン

- config.py
  - 環境変数の読み込みロジック（.env / .env.local の自動ロード）と Settings クラス
  - Settings を通じて設定値へ型安全にアクセスする

- config_setup.py
  - .env を対話的に作成 / 更新するウィザード

- validate_config.py
  - 起動前チェック CLI（必須環境変数・KABUSYS_ENV・LOG_LEVEL・DB パス・config/*.yaml 等の検証）

- run_execution.py
  - ExecutionEngine を組み立て & 起動するエントリポイント

- run_monitoring.py
  - SystemMonitor をポーリングで実行するエントリポイント

- execution/
  - broker_api.py         — BrokerAPI の Protocol / データモデル / 例外 / ファクトリ
  - kabu_client.py        — kabuステーションの REST/WebSocket クライアント
  - mock_client.py        — テスト用 MockBrokerClient
  - broker_factory.py     — Settings に基づきクライアントを生成するファクトリ
  - order_record.py       — 注文状態遷移ロジック（ビジネスロジック）
  - order_repository.py   — SQLite による永続化レイヤ
  - order_manager.py      — 外向き API（OrderRecord + OrderRepository + Broker）
  - execution_engine.py   — 発注ループ（シグナル処理・push ドレイン・kill switch）
  - reconciler.py         — 起動時の自動復旧 / 突合処理
  - risk_manager.py       — 3段階リスクガード（Gate1/2/3）

- data/
  - calendar_management.py — マーケットカレンダー操作（DuckDB ベース）
  - news_collector.py      — RSS からのニュース収集（正規化・SSRF 対策等）

- monitoring/
  - monitoring_db.py (参照されるモジュール) — 監視用 SQLite 初期化 / ログ関数 等
  - system_monitor.py — 実際の監視ロジック（run_monitoring から呼ばれる）

（上記は主要ファイルの抜粋です。詳細は各モジュールの docstring を参照してください。）

---

## 運用上の注意

- 本番環境（KABUSYS_ENV=live）は慎重に扱ってください。本リポジトリの KabuStationClient の本番接続は設計上存在しますが、テストやローカル実行では paper_trading / development を推奨します（MockBrokerClient が動作します）。
- .env は機密情報を含みます。絶対に Git 等へコミットしないでください（config_setup.py のヘッダにも同様の注意があります）。
- kill.flag / stop_requested.flag により安全な起動/停止制御を行う設計です。運用時はこれらのファイルの取り扱いに注意してください。
- DB ファイル（DuckDB / SQLite）は data/ 以下に保存されます。バックアップや排他制御（同一 DB への多重接続）の運用ルールを確立してください。

---

以上。必要があれば README に追記すべき項目（例: 開発用のテスト手順、CI 設定、より詳しい設定例など）を教えてください。