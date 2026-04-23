# KabuSys

日本株自動売買システムの一部を実装したPythonパッケージ。  
このリポジトリには設定管理、実行エンジン、監視ループ、ブローカー抽象、リスクガード、データ処理ユーティリティ（カレンダー／ニュース収集）などの主要コンポーネントが含まれます。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は、kabuステーション等のブローカー API を用いた自動売買システムのコア部分を提供するモジュール群です。  
主な役割:

- 環境変数/.env の管理とウィザード（対話式）での作成
- 起動前設定の検証 CLI
- 発注エンジン（ExecutionEngine）とその周辺（OrderManager / OrderRepository / OrderRecord）
- ブローカークライアントの抽象化（Mock と kabu station 実装）
- リスク管理（3段階ガード: Gate1/2/3）
- 起動時のリコンシリエーション（Reconciler）
- 監視（SystemMonitor を起動する run_monitoring）
- データユーティリティ（マーケットカレンダー、ニュース収集など）

設計の基本方針として、「ビジネスロジック」と「永続化/IO」を分離し、テスト可能かつクラッシュ耐性の高い逐次処理フローを提供します。

---

## 主な機能一覧

- 環境設定ウィザード（./src/kabusys/config_setup.py）
  - 対話式に `.env` を作成・更新
- 設定検証 CLI（./src/kabusys/validate_config.py）
  - .env と config/*.yaml の存在・基本妥当性チェック
  - `--strict` オプションで警告も失敗扱いに
- 実行エンジン（./src/kabusys/run_execution.py / execution/execution_engine.py）
  - シグナル取得 → Gate1/2 的検査 → 発注 → push ドレイン
  - Paper Trading モードのサポート（MockBrokerClient）
- 監視ループ（./src/kabusys/run_monitoring.py）
  - SystemMonitor の定期ポーリング
- 注文関連
  - OrderRecord（状態遷移検証）
  - OrderRepository（SQLite を用いた永続化）
  - OrderManager（発注フローの高レベル API）
- ブローカー抽象（./src/kabusys/execution/broker_api.py）
  - Protocol を定義、Mock/KabuStation 実装を切り替え可能
- RiskManager（./src/kabusys/execution/risk_manager.py）
  - Gate1: シグナルレベル（余力・重複・ポジション上限）
  - Gate2: エグゼキューション（レート制限・サーキットブレーカー）
  - Gate3: ドローダウン監視（約定後）
- Reconciler（起動時の自動復旧）
- データ関連ユーティリティ
  - マーケットカレンダー（DuckDBベースの判定・更新ロジック）
  - ニュース収集（RSS パーサ、安全対策、正規化）

---

## セットアップ手順

前提:
- Python 3.9+（タイプアノテーションや Path 機能を想定）
- 仮想環境の利用を推奨

1. リポジトリをクローンして仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. 依存パッケージをインストール（プロジェクトの requirements.txt があればそれを使用）
   - 例（必要になりやすい主要パッケージ）:
     pip install pyyaml duckdb httpx websocket-client defusedxml

   ※ 本コード中で optional に扱っているライブラリ:
   - PyYAML: config/*.yaml の検証のため
   - duckdb: 信号・カレンダー読み取り等
   - httpx, websocket-client: kabu station クライアント
   - defusedxml: RSS パース安全化

3. データディレクトリの準備
   - デフォルトで使用されるパスの親ディレクトリを作成しておくと良い:
     mkdir -p data

   多くの起動処理は起動時に DB 初期化関数（init_monitoring_db, init_orders_db など）を呼び出し、必要なテーブルを作成します。実行前に data ディレクトリを作成しておくとファイルパス周りでのエラーを防げます。

4. 環境変数の設定
   - 対話式ウィザードで `.env` を作成するのが簡単です（下記参照）。

---

## 環境変数（主なもの）

必須（起動前に設定すること）:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

任意 / 推奨:
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（デフォルト: data/monitoring.db）
- LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL
- KABU_API_BASE_URL: kabu station API のベース URL
- LINE_CHANNEL_ACCESS_TOKEN: LINE 通知用（本番では必須推奨）
- LINE_USER_ID: LINE 通知先ユーザー
- KILL_FLAG_CLEAR_ON_START: 0/1（本番: 0 を推奨）
- PAPER_FILL_MODE: instant | partial | never | reject（ペーパートレードの挙動）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 SQLite（デフォルト: data/paper_trading.db）
- PID_FILE_PATH, KILL_FLAG_PATH, CPU/MEM/DISK 閾値など（監視関連）

サンプル `.env`（一部）:
JQUANTS_REFRESH_TOKEN=your_value
KABU_API_PASSWORD=your_value
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
LOG_LEVEL=INFO
KILL_FLAG_CLEAR_ON_START=0

※ `.env` は決して Git に含めないでください。

---

## 使い方

1. 対話式で `.env` を作る（推奨）
   - python -m kabusys.config_setup
   - 指示に従って入力すると `.env` が作成 / 更新されます。

2. 設定検証
   - python -m kabusys.validate_config
   - 警告も失敗扱いにする場合:
     python -m kabusys.validate_config --strict

   このツールは必須環境変数の有無、KABUSYS_ENV や LOG_LEVEL の基本チェック、DB パスの親ディレクトリ存在、config/*.yaml の有無・YAML パース（PyYAML がインストールされている場合）などを検査します。

3. 実行エンジン起動（本番/ペーパーどちらも）
   - 実行例:
     python -m kabusys.run_execution

   注意:
   - KABUSYS_ENV=paper_trading なら MockBrokerClient が使用され、ペーパートレード用の SQLite（デフォルト data/paper_trading.db）を使用して本番 DB と分離します。
   - run_execution は内部で PID ファイルを書き、停止フラグファイル（data/stop_requested.flag）を監視します。停止は stop flag の作成で行えます。

4. 監視ループ起動
   - python -m kabusys.run_monitoring
   - 環境変数 MONITOR_POLL_INTERVAL（秒）でポーリング間隔を変更可能（デフォルト 60）。

5. 開発・テスト
   - モックブローカーや ExecutionEngine の個別メソッドをユニットテストで呼び出して検証できます（MockBrokerClient は fill_mode を変更して様々な挙動をシミュレート可能）。

---

## 注意事項 / 運用メモ

- KABUSYS_ENV=live の場合は本番運用になります。LINE の通知設定や killflag の扱い（KILL_FLAG_CLEAR_ON_START）を慎重に設定してください。
- `.env` の自動ロードはデフォルトで有効です。テストなどで無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- OrderManager はクラッシュ耐性のため「OrderSent の状態を永続化してからブローカー API を呼ぶ」フローを採用しています。異常検知・リコンシリエーションのための設計が組み込まれています。
- データベースのスキーマ初期化はコード内の init_* 関数（例: init_orders_db, init_monitoring_db）で行われます。通常は run_* スクリプト実行時に冪等的に作成されますが、事前に確認したい場合は Python REPL でこれら関数を呼び出してください。

例: orders テーブルの初期化を手動で行う
python -c "import sqlite3; from kabusys.execution.order_repository import init_orders_db; conn=sqlite3.connect('data/monitoring.db'); init_orders_db(conn); conn.close()"

---

## ディレクトリ構成（主要ファイル）

リポジトリ内の主要なモジュール構成（src/kabusys 配下）:

- __init__.py
- config.py
- config_setup.py           — .env 対話式ウィザード
- validate_config.py       — 設定検証 CLI
- run_execution.py         — ExecutionEngine 起動スクリプト
- run_monitoring.py        — SystemMonitor 起動スクリプト

パッケージ: execution/
- execution/__init__.py
- broker_api.py            — BrokerAPIProtocol, データモデル, 例外, ファクトリ
- broker_factory.py        — Settings に応じたクライアント生成
- kabu_client.py           — kabu station REST/WebSocket 実装
- mock_client.py           — テスト用 MockBrokerClient
- order_record.py          — OrderRecord / 状態遷移ロジック
- order_repository.py      — SQLite DB 永続化層
- order_manager.py         — 発注フロー管理（外向き API）
- execution_engine.py      — ExecutionEngine（シグナル処理・push ドレイン）
- reconciler.py            — 起動時リコンシリエーション
- risk_manager.py          — 3段階リスクガード

パッケージ: data/
- calendar_management.py   — マーケットカレンダー管理
- news_collector.py        — RSS ニュース収集・正規化

パッケージ: monitoring/
- （監視 DB 初期化 / SystemMonitor 実装等 — run_monitoring から呼ばれる）

ユーティリティ:
- utils/（logging_setup, process_priority などがある想定）

その他:
- config/*.yaml            — 各種設定ファイル（存在が推奨される）
- .env / .env.local        — 環境変数定義ファイル（絶対に Git にコミットしないでください）
- data/                    — デフォルトの DB / PID / フラグファイルを配置

（実際のファイル一覧はソースツリーを参照してください）

---

## 開発者向けメモ

- コードは「ビジネスロジックを IO から分離」するよう設計されています。ユニットテストでは MockBrokerClient やメモリ接続を用いることで副作用を抑えられます。
- Reconciler や ExecutionEngine は実行中のクラッシュやネットワーク障害を想定した冗長性を持っています。
- 設定検証と設定ウィザードを組み合わせて、運用前に安全性チェックを自動化してください。

---

もし README に追記してほしいサンプルコマンド、シーケンス（例: 開発環境での起動手順）や、利用する Python バージョン/パッケージの固定（requirements.txt）を含めたい場合は教えてください。README を運用フローに合わせてカスタマイズします。