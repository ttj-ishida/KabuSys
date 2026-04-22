# KabuSys

日本株向けの自動売買システム（プロジェクトの一部）。  
このリポジトリには設定管理・検証ツール、発注エンジンの起動スクリプト、モック／実ブローカークライアント、注文管理・リコンシリエーション、リスクガード、データユーティリティ（カレンダー・ニュース収集）等の主要コンポーネントが含まれます。

バージョン: 0.1.0

---

## 概要

KabuSys は下記の役割を持つモジュール群で構成されています（コードは src/kabusys 配下）:

- 環境変数管理（.env の自動読み込み・手動ウィザード）
- 設定検証 CLI（.env と config/*.yaml の整合性チェック）
- 実行エンジン（ExecutionEngine）によるシグナル駆動の発注フロー
- 監視ループ（SystemMonitor）によるシステム状態の定期チェック
- ブローカー API 抽象（Mock と KabuStation 実装）
- 注文の状態管理（OrderRecord）と永続化（SQLite）
- リスクガード（Gate1〜3）とサーキットブレーカー
- リコンシリエーション（再起動時の注文同期）
- データ機能（マーケットカレンダー、RSS ニュース収集）  

設計方針として、ビジネスロジックと永続化層（DB）を分離し、クラッシュ耐性（2相永続化や再照合）・安全側（Kill Switch）を重視しています。

---

## 主な機能一覧

- .env 対話ウィザード（config_setup.py）による初期設定の生成・更新
- validate_config CLI による必須環境変数や YAML ファイルの起動前チェック（--strict オプションあり）
- ExecutionEngine：シグナル読み込み → Gate1/2（発注前チェック）→ ブローカー送信 → ドレイン（push 処理）までの一連フロー
- MockBrokerClient：テスト／ペーパートレード用のブローカー実装（fill_mode 切替可能）
- KabuStationClient：kabuステーション REST API クライアント（同期 httpx）
- OrderRepository（SQLite）による注文永続化、ユニークインデックスによる同一 signal の同時発注抑止
- Reconciler：OrderSent（不確定状態）をブローカー照合して復旧、ポジション差分検出
- RiskManager：3段階リスクガード（シグナル／エグゼキューション／メトリクス）
- data.calendar_management：DuckDB ベースの営業日判定・カレンダー更新
- data.news_collector：RSS 収集と前処理（SSRF 対策、XML セキュリティ）

---

## セットアップ手順（開発・ローカル実行向け）

1. Python 仮想環境を作成・有効化（例）
   - python3 -m venv .venv
   - source .venv/bin/activate  # macOS / Linux
   - .venv\Scripts\activate     # Windows (PowerShell 等)

2. 依存ライブラリをインストール（最低限）
   - pip install duckdb httpx websocket-client pyyaml defusedxml

   ※ プロジェクトに requirements.txt がある場合はそれを利用してください。

3. .env を作成する
   - 対話ウィザードを使う（推奨）
     - python -m kabusys.config_setup
     - ウィザードに従って必須項目（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD 等）を入力してください。
   - 手動で作成する場合は .env をプロジェクトルートに配置してください。
     - .env は決して Git にコミットしないでください。

4. 設定検証（起動前確認）
   - python -m kabusys.validate_config
   - 警告も失敗扱いにする場合:
     - python -m kabusys.validate_config --strict

5. DB やデータディレクトリの作成
   - デフォルトでは data/ 以下に DB（DuckDB, SQLite）や PID/flag ファイルを配置します。必要なら事前にディレクトリを作成してください（起動時に自動作成される場合もあります）。

---

## 環境変数（主要）

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants API 用リフレッシュトークン（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）

オプション（主なもの）:
- KABUSYS_ENV — 実行環境（development / paper_trading / live）
  - live の場合は本番挙動（注意喚起あり）。Broker の Live 実装は未実装箇所があります。
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード専用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- KABU_API_BASE_URL — kabu station API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — LINE 通知（任意）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリア（0/1）

自動 .env 読み込み:
- プロジェクトルート（.git または pyproject.toml を基準）を探索して .env を自動読み込みします（OS 環境変数を上書きしない既定の挙動）。
- 自動読み込みを無効化する: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

サンプル（.env の一部）
  JQUANTS_REFRESH_TOKEN=your_token_here
  KABU_API_PASSWORD=your_password_here
  KABUSYS_ENV=development
  DUCKDB_PATH=data/kabusys.duckdb
  SQLITE_PATH=data/monitoring.db
  LOG_LEVEL=INFO

---

## 使い方（主なコマンド）

- 環境設定ウィザード（.env 作成／更新）
  - python -m kabusys.config_setup
  - 実行後、.env に保存されます。

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告も失敗（exit code 1）扱いになります。

- 実行エンジン起動（本番セッションの起点）
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し paper_trading 用 SQLite（PAPER_TRADING_SQLITE_PATH）へ記録します。
  - 起動中は PID ファイル（data/execution.pid 等）が作成され、停止は data/stop_requested.flag の作成または kill.flag によって行えます。

- 監視ループ起動（SystemMonitor）
  - python -m kabusys.run_monitoring
  - 短い説明: MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）。

注意:
- 本番（KABUSYS_ENV=live）では LINE 通知設定や Kill Switch の扱いを特に注意してください。Broker の Live 実装が未実装である箇所があるため、現状は paper_trading / development を想定します。

---

## 実装上の重要ポイント（運用メモ）

- 発注フローの耐久性:
  - OrderCreated → OrderSent を DB に先に永続化し、broker 呼び出し後に broker_order_id を保存する二段階の永続化を行っています。クラッシュ回復用に Reconciler が用意されています。
- リスク管理:
  - Gate1（シグナル単位の余力・重複・ポジション上限）
  - Gate2（レート制限・サーキットブレーカー）
  - Gate3（約定後のドローダウン監視） — 異常時は kill_switch() により全 active 注文をキャンセルします。
- Kill Switch:
  - kill.flag（デフォルト: data/kill.flag）で外部から起動停止のシグナルを与えられます。KILL_FLAG_CLEAR_ON_START によって起動時の自動クリア挙動を制御します。
- DB 分離:
  - paper_trading モードは本番監視 DB と分離された paper_trading SQLite を使用します（事故防止）。

---

## ディレクトリ構成（抜粋 & ファイル説明）

src/kabusys/
- __init__.py — パッケージ定義（__version__ 等）
- config.py — 環境変数の自動読み込み・Settings クラス（アプリ設定）
- config_setup.py — .env 対話ウィザード（CLI）
- validate_config.py — 起動前の設定検証 CLI
- run_execution.py — ExecutionEngine の起動スクリプト（デーモン的にセッションを実行）
- run_monitoring.py — SystemMonitor（監視ループ）起動スクリプト

execution/
- broker_api.py — ブローカー API のデータモデル、Protocol、例外、ファクトリ
- broker_factory.py — Settings に基づいて適切なブローカークライアントを生成
- kabu_client.py — kabu station REST API クライアント実装（httpx）
- mock_client.py — MockBrokerClient（テスト用）
- order_record.py — 注文状態モデルと状態遷移ロジック（ビジネスロジック）
- order_repository.py — SQLite を用いた永続化層（orders テーブルの初期化含む）
- order_manager.py — 注文作成・送信・キャンセル・同期の外向き API（OrderRecord + Repository）
- execution_engine.py — ExecutionEngine 本体（セッション制御・シグナル処理・push ドレイン）
- reconciler.py — 起動時の自動復旧・リコンシリエーション
- risk_manager.py — 3段階リスクガード

data/
- calendar_management.py — JPX カレンダー管理（DuckDB ベース）
- news_collector.py — RSS ニュース収集と前処理

その他（プロジェクトルートに）
- config/*.yaml — システム設定用 YAML（存在確認・パース検証対象）
- .env / .env.local — 環境変数ファイル（自動読み込み）
- data/ — DB（duckdb/sqlite）、PID/flag ファイルを置くディレクトリ

---

## よくあるコマンド例

- .env を作成する:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config --strict
- 実行エンジン（ローカルテスト・ペーパートレード）:
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
- 監視ループ起動:
  - python -m kabusys.run_monitoring
- パッケージとして対話的に利用する場合:
  - from kabusys.config import settings
  - token = settings.jquants_refresh_token

---

## 注意事項 / 開発メモ

- .env は絶対にリポジトリにコミットしないでください（機密情報が含まれます）。
- 本番運用時は KABUSYS_ENV=live の設定や LINE 通知設定、KILL_FLAG の取り扱いを慎重に確認してください。live 用のブローカークライアントは未実装の箇所があるため、現在は主に development / paper_trading を想定しています。
- YAML 検証は PyYAML がインストールされている場合にのみ行われます（未インストール時はスキップして警告出力）。

---

必要なら README の英語版や、セットアップ用の requirements.txt / docker-compose サンプル、運用手順（サービス化、systemd ユニット例）も追加できます。どの情報を優先して追記しますか？