# KabuSys

日本株自動売買システム（開発中）  
このリポジトリは、シグナルに基づく発注エンジン、リスクガード、モニタリング、ブローカー API クライアント等を含む自動売買のコアロジックを提供します。

---

## 概要

KabuSys は以下の主要な責務を持つコンポーネント群で構成された自動売買フレームワークです。

- シグナルに基づく発注フロー（ExecutionEngine）
- 注文の状態管理と永続化（OrderRecord / OrderRepository / OrderManager）
- ブローカー API クライアント（kabuステーション 実装 / Mock 実装）
- リスク管理（3 段階ガード: Gate1/2/3）
- 起動時のリコンシリエーション（Reconciler）
- 監視ループ（SystemMonitor 起動スクリプト）
- .env 対話式セットアップ・設定検証ツール

本リファレンスはローカル実行・開発を想定した説明と、起動に必要な設定手順をまとめた README です。

---

## 主な機能一覧

- ExecutionEngine
  - シグナルプル型の発注ループ（指定時間帯にシグナル処理、プッシュドレイン）
  - WebSocket プッシュ受信（kabu push）対応
  - 起動時リコンシリエーション（OrderSent の突合せ & ポジション差分検出）
  - Kill Switch（kill.flag）検出で安全にキャンセル/停止

- ブローカークライアント
  - KabuStation REST API クライアント実装（httpx）
  - MockBrokerClient（paper_trading / development 向け）
  - create_broker_api ファクトリで切替可能

- 注文管理
  - OrderRecord を基に状態遷移を厳密に検証
  - SQLite による永続化（orders テーブル）
  - list_uncertain / list_active 等のクエリでリコンシリエーションを支援

- リスク管理（RiskManager）
  - Gate1: シグナルレベル（余力・重複・ポジション上限）
  - Gate2: エグゼキューション（レート制限・サーキットブレーカー）
  - Gate3: メトリクス（ドローダウン監視）

- データユーティリティ
  - マーケットカレンダー管理（DuckDB、J-Quants 経由の更新ジョブ用）
  - ニュース収集（RSS）・前処理（SSRF 対策・正規化・ID 生成など）

- 開発・運用補助
  - .env 対話式ウィザード（config_setup）
  - 起動前設定検証 CLI（validate_config）
  - 監視・実行起動スクリプト（run_monitoring / run_execution）

---

## 要件（依存パッケージ）

最低限必要な Python パッケージ（例）:

- python >= 3.9（コードは型注釈で新しい構文を使用）
- duckdb
- httpx
- websocket-client
- defusedxml
- pyyaml（YAML 検証を行う場合に任意で必要）
- その他標準ライブラリ（sqlite3, logging, threading 等）

実行環境に合わせて pip でインストールしてください。例:

pip install duckdb httpx websocket-client defusedxml pyyaml

（requirements ファイルがある場合はそちらを使用してください）

---

## セットアップ手順

1. リポジトリをクローンして適切な Python 仮想環境を作成・有効化します。

2. 依存パッケージをインストールします（上記参照）。

3. .env を作成する
   - 推奨: 対話式ウィザードを使用して .env を生成します。

   コマンド:
   python -m kabusys.config_setup

   ウィザードは既存の .env を読み込み、対話的に入力を促します。完了すると .env が書き出されます。

4. 起動前に設定を検証する

   コマンド:
   python -m kabusys.validate_config

   警告も失敗扱いにしたい場合:
   python -m kabusys.validate_config --strict

   validate_config は必須環境変数の未設定、KABUSYS_ENV の不正値、DB パスの親ディレクトリ存在確認や config/*.yaml の存在/パース検証（PyYAML がインストールされている場合）を行います。

---

## 環境変数（主要）

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants API 用リフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API パスワード

任意／よく使うもの:
- KABUSYS_ENV — 実行環境: development / paper_trading / live（live は注意。実装によっては未対応の箇所あり）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — paper_trading 用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL — ログレベル（DEBUG, INFO, WARNING, ERROR, CRITICAL）
- KILL_FLAG_CLEAR_ON_START — 起動時に既存 kill.flag を自動クリアするか（0/1）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — LINE 通知設定（本番環境でのアラート用）
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、デフォルト 60）

Settings は環境変数から値を取得します。自動で .env / .env.local を読み込みますが、OS 環境変数が優先されます。自動ロードを無効化するには:

export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

.env の読み込み優先度:
OS 環境変数 > .env.local > .env

注意: .env は決して Git にコミットしないでください。

例（最小 .env）:
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
KABU_API_PASSWORD=your_kabu_api_password
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
LOG_LEVEL=INFO

---

## 使い方（主要スクリプト）

- 環境設定ウィザード（.env 生成・更新）
  python -m kabusys.config_setup
  - 対話式で主要な環境変数を設定して .env を生成します。

- 設定検証
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict

  - --strict を使うと警告も exit code 1（FAIL）として扱います。

- 監視ループ起動（SystemMonitor をポーリング）
  python -m kabusys.run_monitoring

  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒単位で上書きできます（デフォルト 60）。
  - 監視は KABUSYS_ENV に関係なく本番 sqlite_path（SQLITE_PATH）を使用します。
  - 停止は data/stop_requested.flag の作成で行えます。

- 実行（ExecutionEngine）起動
  python -m kabusys.run_execution

  - KABUSYS_ENV により挙動が異なります:
    - development / paper_trading: MockBrokerClient を使用（paper_trading は paper_sqlite_path を使用）
    - live: 実ブローカークライアントは未実装で NotImplementedError を投げる設計箇所があります（実運用の際は実装が必要）
  - 停止は data/stop_requested.flag の作成で検出して安全に終了します。
  - PID ファイル: data/execution.pid（デフォルト、設定で変更可）
  - 起動時、kill.flag が残っている場合は KILL_FLAG_CLEAR_ON_START の設定によっては起動を拒否するか自動クリアします。

---

## 運用上の注意

- 本番（KABUSYS_ENV=live）設定時は LINE 通知等のアラート設定を必ず確認してください。validate_config は live の場合に警告を出します。
- paper_trading / development では MockBrokerClient により実ブローカーを不要にテストできます。Mock の fill_mode は Settings の PAPER_FILL_MODE（またはデフォルト）で制御できます（instant/partial/never/reject）。
- orders テーブルには「同一 signal_id の active 注文は 1 件のみ許可する」ユニーク制約があります（レース対策）。
- リコンシリエーション（Reconciler）は起動時に OrderSent 状態の注文をブローカーと突合して状態を回復し、ポジション差分をログに出します。
- config/*.yaml は一部コンポーネントで使用されます（validate_config で存在確認）。サンプル生成スクリプトがある場合はそれを利用してください（validate_config のメッセージにある通り）。

---

## ディレクトリ構成（主要ファイル解説）

src/kabusys/
- __init__.py
  - パッケージ定義・バージョン

- config.py
  - Settings クラス: 環境変数から設定を取得する中心モジュール
  - .env 自動ロード（.env, .env.local）ロジックを含む

- config_setup.py
  - .env 対話式ウィザード（python -m kabusys.config_setup）

- validate_config.py
  - 起動前の設定検証 CLI（python -m kabusys.validate_config）

- run_monitoring.py
  - SystemMonitor のポーリングループ起動スクリプト

- run_execution.py
  - ExecutionEngine 起動スクリプト（発注フローのエントリポイント）

- execution/
  - broker_api.py — BrokerAPIProtocol、データモデル、例外、ファクトリ
  - kabu_client.py — KabuStationClient（kabuステーション REST 実装）
  - mock_client.py — MockBrokerClient（テスト・開発用）
  - broker_factory.py — Settings に応じてクライアントを生成
  - execution_engine.py — ExecutionEngine（シグナル処理 / push ドレイン / セッション管理）
  - order_record.py — OrderRecord と状態遷移ロジック
  - order_repository.py — SQLite 永続化層（orders テーブル）
  - order_manager.py — OrderManager（外向き API、送信/同期/キャンセル）
  - reconciler.py — 起動時リコンシリエーション
  - risk_manager.py — 3 段階リスクガード

- data/
  - calendar_management.py — マーケットカレンダー管理（DuckDB / J-Quants 連携）
  - news_collector.py — RSS ニュース収集と前処理

- monitoring/
  - monitoring_db.py — 監視 DB 初期化・書き込み（使用箇所: run_monitoring/run_execution）

- utils/
  - logging_setup.py — ログ設定
  - process_priority.py — プロセス優先度設定ユーティリティ

config/
- system_config.yaml
- data_config.yaml
- strategy_config.yaml
- risk_config.yaml
- execution_config.yaml
- monitoring_config.yaml

（上記 YAML ファイルはプロジェクトの設定ファイル群。validate_config は存在確認とパース検証を行います。存在しない場合はウィザードやスクリプトで生成してください。）

data/
- 実行時に使用するデータファイル群（DuckDB/SQLite/PID/flag 等）。デフォルトはプロジェクトルート直下の data/ を使用します。

---

## 開発・テストに役立つ情報

- MockBrokerClient を使えば kabuステーション 環境を用意せずに発注フロー・リコンシリエーション・リスクガードの挙動をローカルで検証できます。
- ExecutionEngine は run_session() を中心に設計されており、テストでは _process_signals() や _drain_push_queue() を直接呼び出して個別のロジックを検証できます。
- OrderRecord の状態遷移ロジックは細かく定義されており、不正遷移は InvalidStateTransitionError を投げます。ユニットテストはこれを利用して遷移制約を検証してください。

---

## 最後に

- .env の取り扱いに注意してください（セキュリティ上、Git へコミットしない）。
- 本番運用前に validate_config で検証を行い、LINE などのアラート経路や kill_flag の設定を確認してください。
- live ブローカークライアントの実装・検証は慎重に行ってください（現在一部設計で NotImplementedError を投げる箇所があります）。

質問や README の追加情報が必要であれば、どの項目を詳しく書くか教えてください。