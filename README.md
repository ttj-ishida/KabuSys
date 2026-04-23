# KabuSys

日本株自動売買システムの一部（設定管理・実行エンジン・監視・データユーティリティ等）の実装サンプルです。本 README はリポジトリ内のソースコードに基づいて、導入・起動手順や主要機能、ディレクトリ構成を日本語でまとめたものです。

---

## プロジェクト概要

KabuSys は、kabuステーション（ローカルのブローカー API）や J-Quants などと連携して日本株の自動売買を行うためのコンポーネント群です。本コードベースには以下が含まれます：

- 環境変数 / .env を対話的に作成するウィザード（config_setup）
- 起動前に .env や config/*.yaml を検証する CLI（validate_config）
- 発注処理を実行する ExecutionEngine（run_execution）
- システム監視ループ（run_monitoring）
- ブローカー API 抽象化（実際の kabu client と MockClient）
- 注文状態管理・永続化（OrderRecord / OrderRepository / OrderManager）
- リスクガード（3 段階の RiskManager）
- データ系ユーティリティ（マーケットカレンダー、ニュース収集など）

本リポジトリは、開発 / ペーパートレード / 本番（live）を環境ごとに切り替えて動作する設計になっています。

---

## 主な機能一覧

- 環境設定ウィザード（python -m kabusys.config_setup）による .env の対話式生成・更新
- 起動前チェック（python -m kabusys.validate_config）による必須環境変数・設定ファイルの検証（--strict オプションあり）
- ExecutionEngine：シグナルに基づく発注（Signal Pull + WebSocket push ドレイン）
- MockBrokerClient：ペーパートレード / テスト向けのモックブローカー（fill_mode を制御可能）
- Reconciler：クラッシュ後に OrderSent 状態の注文をブローカーと突合して自動復旧
- RiskManager：Gate1〜Gate3 による発注前・送信前・約定後の多段リスクガード（余力／重複／ポジション上限／レート制限／サーキットブレーカー／ドローダウン）
- データユーティリティ：DuckDB を使ったマーケットカレンダー管理、RSS ニュース収集（保護対策あり）

---

## 動作要件（推奨）

- Python 3.10 以上（型ヒントや union 表記（|）を使用しているため）
- SQLite（Python 標準ライブラリ）
- DuckDB Python パッケージ（duckdb）
- HTTP/WebSocket クライアント: httpx, websocket-client
- その他（機能に応じて）: PyYAML（config/*.yaml の内容検証時）、defusedxml（RSS パース保護）

推奨インストールパッケージ例:
pip install duckdb httpx websocket-client pyyaml defusedxml

（実際のプロジェクトでは requirements.txt / poetry / pipfile を用意してください）

---

## セットアップ手順

1. リポジトリをクローンする
   - git clone <repo-url>
   - cd <repo-root>

2. 仮想環境を作成して有効化（任意）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存パッケージをインストール
   - pip install duckdb httpx websocket-client pyyaml defusedxml
   - （必要に応じて他パッケージを追加）

4. 環境変数ファイル（.env）の作成
   - 対話式ウィザードを推奨:
     - python -m kabusys.config_setup
   - もしくは手動で .env を作成（下記「環境変数一覧」を参照）
   - .env.local を使ってローカル上書きも可能（自動読み込み順は: OS 環境 > .env.local > .env）

5. 設定の検証（起動前チェック）
   - python -m kabusys.validate_config
   - 警告もエラー扱いにする場合:
     - python -m kabusys.validate_config --strict

6. DB の初期化等（必要に応じて）
   - ExecutionEngine 起動時に orders テーブルなどの初期化処理（init_orders_db / init_monitoring_db）を呼ぶ設計になっています。手動で初期化したい場合は当該関数を呼び出してください。

---

## 環境変数（主要項目）

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants API のリフレッシュトークン（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）

任意（デフォルトあり／運用に便利なもの）:
- KABUSYS_ENV — 実行環境: development / paper_trading / live（デフォルト: development）
  - paper_trading: MockBrokerClient を使い paper_trading 用 SQLite DB に記録（data/paper_trading.db）
  - live: 本番（注意深い設定確認が必要）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite ファイルパス（デフォルト: data/monitoring.db）
- LOG_LEVEL — ログレベル（DEBUG, INFO, WARNING, ERROR, CRITICAL）
- KABU_API_BASE_URL — kabu station API のベース URL（例: http://localhost:18080/kabusapi）
- LINE_CHANNEL_ACCESS_TOKEN — LINE 通知用トークン（本番アラート用、任意）
- LINE_USER_ID — LINE 通知先ユーザー ID（任意）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（0/1、デフォルト 0）
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、デフォルト 60）※環境変数で上書き可能
- PAPER_FILL_MODE — paper_trading 時の Mock の fill 動作（instant, partial, never, reject）

注意:
- .env/.env.local は自動ロードされます（OS 環境変数 > .env.local > .env）。自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。
- .env は絶対にリポジトリにコミットしないでください（config_setup でも警告あり）。

---

## 使い方（起動例）

- 環境設定ウィザード
  - python -m kabusys.config_setup
    - 対話的に .env を作成 / 更新します。

- 設定検証（起動前チェック）
  - python -m kabusys.validate_config
  - strict モード（警告を FAIL とする）
    - python -m kabusys.validate_config --strict

- 実行エンジン起動（発注処理）
  - python -m kabusys.run_execution
  - KABUSYS_ENV が paper_trading の場合、MockBrokerClient を使い data/paper_trading.db を使用します。
  - 実行中の停止は data/stop_requested.flag や kill.flag で制御されます。

- 監視ループ起動
  - python -m kabusys.run_monitoring
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL（秒）で上書き可。
  - 監視は常に sqlite_path（デフォルト data/monitoring.db）を使用します（環境にかかわらず本番監視 DB を参照する設計）。

- デバッグ / テスト用
  - MockBrokerClient を直接利用して単体テストを書くことが容易です（create_broker_api(mock=True, fill_mode=...)）。

停止 / 制御:
- data/stop_requested.flag を作成すると run_execution / run_monitoring はループを終了して停止します。
- kill.flag（KILL_FLAG_PATH, デフォルト data/kill.flag）が存在すると ExecutionEngine は起動を拒否するか（KILL_FLAG_CLEAR_ON_START=0 の場合） kill_switch を発動して注文をキャンセルします。

---

## 開発者向けメモ

- 発注のクラッシュ安全性:
  - OrderManager.send_order は「OrderSent を永続化 → broker 呼び出し → broker_order_id を永続化 → OrderAccepted に遷移」といった二相的な永続化を設計しており、クラッシュ後のリカバリ性を考慮しています。
  - Reconciler は起動時に OrderSent 状態の注文を突合し、可能な限り整合性を復元します。

- RiskManager:
  - Gate1: シグナル単位（余力・重複・ポジション上限）
  - Gate2: 実行単位（レート制限・サーキットブレーカー）
  - Gate3: 約定後メトリクス（ドローダウン）

- WebSocket push:
  - KabuStationClient.stream_push はブロッキングで push を受け取り、ExecutionEngine はそれを _push_queue 経由で処理します。
  - WebSocket の接続再試行や stop_event による強制クローズを実装しています。

- YAML 設定ファイル:
  - config/*.yaml（system_config.yaml, data_config.yaml, strategy_config.yaml, risk_config.yaml, execution_config.yaml, monitoring_config.yaml）を想定。
  - python -m kabusys.validate_config は PyYAML があれば YAML のパース検証を行います（PyYAML 未インストール時はパース検証をスキップして警告）。

---

## ディレクトリ構成（主要ファイル）

以下は src/kabusys 以下の主要ファイルと簡単な説明です。

- src/kabusys/
  - __init__.py — パッケージ定義（バージョン等）
  - config.py — 環境変数/.env 読み込みと Settings クラス（アプリ設定）
  - config_setup.py — .env 対話式ウィザード（python -m kabusys.config_setup）
  - validate_config.py — 起動前設定検証 CLI（python -m kabusys.validate_config）
  - run_execution.py — ExecutionEngine 起動スクリプト（python -m kabusys.run_execution）
  - run_monitoring.py — SystemMonitor ポーリング起動スクリプト（python -m kabusys.run_monitoring）
  - execution/  — 発注関連モジュール
    - __init__.py
    - broker_api.py — BrokerAPIProtocol, データモデル, 例外, ファクトリ
    - kabu_client.py — kabuステーション実装（httpx + websocket）
    - mock_client.py — テスト用 MockBrokerClient
    - broker_factory.py — Settings に応じたブローカー生成
    - order_record.py — 注文状態モデルと遷移ロジック
    - order_repository.py — SQLite 永続化層
    - order_manager.py — 注文の外向き API（送信・同期・キャンセル）
    - execution_engine.py — 発注エンジン（シグナル処理 + push ドレイン）
    - reconciler.py — 起動時リコンシリエーション
    - risk_manager.py — 3 段階リスクガード
  - data/  — データ系ユーティリティ
    - calendar_management.py — マーケットカレンダー管理（DuckDB）
    - news_collector.py — RSS ニュース収集（安全対策付き）
    - (jquants_client 等が参照されるが省略されているファイルがある可能性あり)
  - monitoring/  — 監視関連（run_monitoring から利用）
    - monitoring_db.py — 監視 DB 初期化 / ロギング（参照されているが一覧に省略あり）
    - system_monitor.py — システム監視ロジック（参照あり）
  - utils/
    - logging_setup.py — ロギング初期化（参照あり）
    - process_priority.py — プロセス優先度設定（参照あり）

（上記はソースの抜粋に基づく主要構成です。完全なファイル一覧は git リポジトリのツリーをご確認ください）

---

## トラブルシューティング / 注意点

- validate_config の PyYAML 未インストールのメッセージ:
  - PyYAML がない場合、config/*.yaml の内容検証はスキップされます。YAML の文法チェックを行いたい場合は pyyaml をインストールしてください。

- KabuStation 実機連携:
  - 実機連携（live）を行う場合は kabuステーション アプリがローカルで起動している必要があります。ローカルの API エンドポイントは通常 http://localhost:18080/kabusapi です。
  - 本番実行時は KABUSYS_ENV=live を設定すると追加のガード（LINE 設定チェックや kill flag の警告）が入り安全確認が促されます。

- DB の分離:
  - paper_trading 環境では paper_trading 用 SQLite（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）を使用して本番 DB と分離します。
  - 監視（monitoring）は常に sqlite_path（data/monitoring.db）を参照する点に注意してください。

---

必要であれば README にインストール用の requirements.txt や設定例 (.env.example)、起動用 systemd ユニットや Dockerfile の雛形を追加で作成できます。どの情報を追記したいか教えてください。