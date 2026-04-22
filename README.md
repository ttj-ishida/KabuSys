# KabuSys

日本株向け自動売買システムのコアライブラリ（読み取り専用の簡易説明）。  
このリポジトリには設定管理、発注エンジン、モニタリング、データユーティリティなどの主要コンポーネントが含まれます。

バージョン: 0.1.0

---

目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 使い方
- ディレクトリ構成（主要ファイルと簡単な説明）
- 重要な環境変数一覧と説明
- 運用上の注意

---

## プロジェクト概要

KabuSys は kabuステーション（ローカルのブローカーAPI）および J-Quants 等の外部サービスを使って日本株の自動売買を行うための内部ライブラリ群です。  
設計上、発注・状態管理・リスクガード・リコンシリエーション・監視機能を分離しており、テストしやすいようにモックブローカークライアント（MockBrokerClient）も提供します。

主な設計方針:
- 発注フローのクラッシュ耐性（OrderSent の二相永続化や起動時のリコンシリエーション）
- 3段階のリスクガード（Gate1：シグナル検査、Gate2：レート制限／CB、Gate3：ドローダウン監視）
- 環境別挙動（development / paper_trading / live）
- .env による設定管理、自動読み込み（プロジェクトルート検出ベース）

---

## 機能一覧

- .env 対話式ウィザード（config_setup.py）
- 起動前の設定検証 CLI（validate_config.py）  
  - --strict オプションで警告も失敗扱いに
- ExecutionEngine：シグナルに基づく発注エンジン（run_execution.py）
  - 発注、send/cancel/sync のワークフロー
  - PID / kill flag 管理
- Broker クライアント群
  - KabuStationClient（kabuステーション REST API 実装）
  - MockBrokerClient（テスト用）
  - create_broker_api ファクトリ
- Order 層
  - OrderRecord（状態遷移ロジック）
  - OrderRepository（SQLite 永続化）
  - OrderManager（高レベル API）
  - Reconciler（起動時リコンシリエーション）
- RiskManager（3段階リスクガード）
- Monitoring（run_monitoring.py: SystemMonitor ポーリング）
- Data utilities
  - カレンダー管理（market_calendar を基に営業日判定）
  - ニュース収集（RSS 前処理、SSRF 対策等）
- 設定管理（config.py）
  - .env 自動読み込み（.env, .env.local）をサポート
  - Settings クラスで型安全に環境変数を取得

---

## セットアップ手順

1. Python 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要なパッケージをインストール  
   （プロジェクト内に requirements.txt がない場合の例）
   - pip install duckdb httpx websocket-client defusedxml PyYAML

   注意:
   - PyYAML が無い場合、validate_config の YAML パース検証はスキップされます（警告）。
   - duckdb は分析用 DB、sqlite は標準ライブラリ。

3. プロジェクトルートに .env を作成する（推奨: ウィザードを使用）
   - python -m kabusys.config_setup
   - 生成された .env は Git にコミットしないでください（README 等にも明記）。

4. 設定検証を実行
   - python -m kabusys.validate_config
   - 警告も失敗扱いにしたい場合:
     - python -m kabusys.validate_config --strict

---

## 使い方

基本的な CLI 実行例:

- 環境設定ウィザード（.env 作成）
  - python -m kabusys.config_setup
  - オプション: --env-file を指定して別パスの .env を作成可能

- 設定検証
  - python -m kabusys.validate_config
  - --strict: 警告も FAIL 扱い（exit code 1）

- 実行エンジン（Execution）
  - python -m kabusys.run_execution
  - 注意: KABUSYS_ENV が paper_trading または development のときは MockBrokerClient を使用。
    - live 環境の実ブローカークライアントは未実装（BrokerClientFactory で NotImplementedError が投げられる）。

- 監視ループ（Monitoring）
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL（秒）でポーリング間隔を変更可能（デフォルト 60 秒）

運用フラグ・ファイル:
- 停止リクエスト（Graceful stop）
  - data/stop_requested.flag を作成すると run_execution / run_monitoring はループを抜けて停止する
- Kill Switch（即時停止）
  - settings.kill_flag_path（デフォルト: data/kill.flag）を作成すると ExecutionEngine は kill_switch() を発動し全 active 注文をキャンセル
  - KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に既存の kill.flag を自動で削除して起動できる（本番では推奨しない）

ログ・PID:
- 実行時に PID ファイル（デフォルト: data/execution.pid 等）を生成
- ログレベルは LOG_LEVEL 環境変数で制御（DEBUG/INFO/WARNING/ERROR/CRITICAL）

---

## ディレクトリ構成（主要ファイルと説明）

（プロジェクトルート: src/kabusys 以下に実装ファイルが配置されています）

- src/kabusys/__init__.py
  - パッケージ定義（__version__ 等）
- src/kabusys/config.py
  - .env 自動読み込みロジック、Settings クラス
- src/kabusys/config_setup.py
  - .env 対話式ウィザード
- src/kabusys/validate_config.py
  - 起動前設定検証 CLI（必須 env, YAML ファイル存在チェック等）
- src/kabusys/run_execution.py
  - ExecutionEngine 起動スクリプト（PID / stop flag 管理）
- src/kabusys/run_monitoring.py
  - SystemMonitor ポーリングスクリプト
- src/kabusys/execution/
  - broker_api.py            — BrokerAPIProtocol、データモデル、例外、ファクトリ
  - kabu_client.py          — kabuステーション用 HTTP クライアント（httpx）
  - mock_client.py          — テスト用 MockBrokerClient
  - broker_factory.py       — 設定からクライアントを生成
  - order_record.py         — OrderRecord と状態遷移ロジック
  - order_repository.py     — SQLite を使った永続化レイヤ
  - order_manager.py        — 高レベルの注文管理（create/send/sync/cancel）
  - execution_engine.py     — ExecutionEngine（シグナル処理・push ドレイン等）
  - reconciler.py           — 起動時リコンシリエーション
  - risk_manager.py         — 3段階リスクガード
- src/kabusys/data/
  - calendar_management.py  — マーケットカレンダー管理（営業日判定など）
  - news_collector.py       — RSS ニュース収集・前処理（SSRF 対策等）
  - jquants_client.py       — （参照される想定の J-Quants クライアントモジュール）
- src/kabusys/monitoring/
  - monitoring_db.py        — 監視用 SQLite 初期化等
  - system_monitor.py       — システムリソース監視ロジック
- src/kabusys/utils/
  - logging_setup.py        — ログのセットアップユーティリティ
  - process_priority.py     — プロセス優先度設定ユーティリティ

補足:
- config/*.yaml（system_config.yaml 等）を想定する設定ファイル群があり、validate_config は存在確認と（PyYAML があれば）パース検証を行います。
- scripts/generate_config.py のようなスクリプトで雛形を生成することが想定されています（validate_config のメッセージ参照）。

---

## 重要な環境変数（抜粋）

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants API のリフレッシュトークン
- KABU_API_PASSWORD     — kabuステーション API パスワード

推奨 / 任意:
- KABUSYS_ENV           — 実行環境 (development / paper_trading / live)
  - paper_trading: MockBrokerClient を使い paper_trading 用 SQLite に分離して実行
  - development: テスト用
  - live: 本番（注意: BrokerClientFactory は live を未実装）
- DUCKDB_PATH           — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH           — 監視 DB（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — paper_trading 用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL             — ログレベル（DEBUG/INFO/...）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID — 本番アラート用（任意）
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動でクリアする（0/1）

その他:
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると config.py による .env 自動読み込みを抑制できます（テスト等で使用）。

---

## 運用上の注意

- .env は機密情報を含むため Git には絶対にコミットしないでください。config_setup のヘッダーにもその旨を出力します。
- 本番（live）モードは慎重に使用してください。validate_config は KABUSYS_ENV=live を検知すると警告を出します（LINE 通知等が未設定だとアラートが届きません）。
- kill.flag / stop_requested.flag の動作を理解してから運用してください。特に KILL_FLAG_CLEAR_ON_START=1 は本番では危険です（自動で kill.flag をクリアして起動するため）。
- ExecutionEngine と Monitoring は SQLite / DuckDB の接続を行います。データディレクトリ（data/）の権限やマウントを確認してください。
- live クライアント（KabuStationClient）で実際に発注する場合は事前に充分な検証を行ってください。BrokerClientFactory は現在 paper_trading/development（Mock）を推奨します。

---

必要であれば README にサンプル .env テンプレート、または運用手順（デプロイ / systemd ユニット例 / ログローテーション）の追加も作成できます。どの情報を優先して追加しますか？