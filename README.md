# KabuSys

日本株向け自動売買フレームワーク（プロトタイプ）

このリポジトリは、kabuステーションやモックブローカーを使った発注エンジン、監視ループ、環境設定ウィザード、各種ユーティリティ（マーケットカレンダー管理・ニュース収集など）を含む自動売買システムのコア部分を提供します。

---

## 概要

KabuSys は以下の責務を持つモジュール群で構成されています：

- 環境設定の管理とウィザード（.env の生成 / 読み込み）
- 起動前の設定検証 CLI（必須環境変数や設定ファイルの整合チェック）
- 発注エンジン（ExecutionEngine）：シグナル読み込み → リスクチェック → 発注 → WebSocket ドレイン
- ブローカー抽象化（実環境向けの KabuStationClient / テスト向けの MockBrokerClient）
- 注文状態管理（OrderRecord, OrderRepository, OrderManager）
- リスク管理（3段階：Gate1/2/3、サーキットブレーカー、レート制御、ドローダウン監視）
- 起動時リコンシリエーション（Reconciler）
- 監視ループ（SystemMonitor 起動スクリプト）
- データ関連ユーティリティ（マーケットカレンダー更新、RSS ニュース収集等）

主要な設計方針は「DB への永続化（SQLite/DuckDB）を活用してクラッシュ耐性を高める」「ブローカー呼び出しは抽象化してモックでの検証を容易にする」「明示的なリスクゲートで安全性を確保する」ことです。

---

## 機能一覧

- 環境設定ウィザード（python -m kabusys.config_setup）
  - .env ファイルの対話的作成/更新をサポート
- 設定検証 CLI（python -m kabusys.validate_config）
  - 必須環境変数の有無、config/*.yaml の存在と YAML パース（PyYAML があれば）を検査
  - --strict オプションで警告も失敗扱いに
- 発注エンジン（ExecutionEngine）
  - シグナルの読み込み（DuckDB）
  - Gate1〜Gate3 のリスク検査
  - 発注のクラッシュ耐性（OrderSent 永続化、2相コミット的フロー）
  - WebSocket push のドレイン処理
- ブローカー抽象化
  - MockBrokerClient（fill_mode: instant/partial/never/reject）を用いたローカルテスト
  - KabuStationClient（httpx / websocket-client を利用した実ブローカー接続）
- 注文永続化（SQLite）
  - orders テーブル、部分ユニークインデックスで同一 signal の重複を防止
- リコンシリエーション（起動時に OrderSent を突合）
- 監視ループ（run_monitoring）で SystemMonitor を周期実行
- データユーティリティ
  - マーケットカレンダー管理（DuckDB と J-Quants 連携）
  - RSS ベースのニュース収集（XML 等の安全処理を行う）

---

## 必要条件

- Python 3.9+
- 必須 / 推奨パッケージ（requirements.txt を用意している想定）
  - duckdb
  - httpx
  - websocket-client
  - defusedxml
  - PyYAML（YAML パース検証用、無くても動作は可能だが警告が出ます）
- 標準ライブラリ：sqlite3 等

（実行環境に合わせて requirements.txt を作成してください）

---

## セットアップ手順

1. リポジトリをクローンしてワークディレクトリへ移動
   - git clone ... && cd <repo>

2. 仮想環境を作成して有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存関係をインストール
   - pip install -r requirements.txt
   - requirements.txt が無い場合は上記の主要パッケージを個別にインストールしてください。
     例:
       pip install duckdb httpx websocket-client defusedxml PyYAML

4. .env を作成
   - 対話式ウィザードを利用:
       python -m kabusys.config_setup
   - 生成された .env を編集して、少なくとも必須環境変数を設定します（下記参照）。

5. 設定検証を実行
   - python -m kabusys.validate_config
   - 問題がなければ OK と表示されます。CI 等では厳格モードで失敗させることも可能:
       python -m kabusys.validate_config --strict

---

## 環境変数（主なもの）

必須（最低限設定が必要）
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

任意 / 推奨
- KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
- DUCKDB_PATH — デフォルト: data/kabusys.duckdb
- SQLITE_PATH — デフォルト: data/monitoring.db
- LOG_LEVEL — デフォルト: INFO
- KABU_API_BASE_URL — デフォルト: http://localhost:18080/kabusapi
- LINE_CHANNEL_ACCESS_TOKEN — 本番での通知用
- LINE_USER_ID — 本番での通知先
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（0/1）

.env の自動読み込み
- ランタイム起動時に .env（および .env.local）が自動で読み込まれます（OS 環境変数が優先）。
- 自動読み込みを無効化したい場合: KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## 使い方（実行例）

- 環境設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 厳格モード（警告も失敗扱い）:
    - python -m kabusys.validate_config --strict

- Execution（発注エンジン）
  - 実行例（デフォルトで .env の KABUSYS_ENV によってモック/本番が切り替わります）:
    - python -m kabusys.run_execution

  - 注意:
    - paper_trading（ペーパートレード）では MockBrokerClient を使用し、paper_trading 用の SQLite（PAPER_TRADING_SQLITE_PATH または data/paper_trading.db）に記録します。
    - 本番（live）は未実装ブローカーがあるため注意が必要（BrokerClientFactory で NotImplementedError を投げる設計）。

- Monitoring（監視ループ）
  - python -m kabusys.run_monitoring
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL（秒）で上書き可。デフォルト: 60 秒。

---

## 開発者向けメモ

- 設定は kabusys.config.Settings または singleton の settings から取得できます。
  - 例: from kabusys.config import settings; settings.duckdb_path
- 発注ロジックとブローカー API は厳密に分離されています（create_broker_api により Mock/Kabu を切り替え可能）。
- 発注フローはクラッシュ耐性を考慮して設計されています（OrderSent の永続化、broker_order_id の先行保存、リコンシリエーション）。
- RiskManager は Token Bucket（レート制御）、サーキットブレーカー、ドローダウン検知を実装しています。
- DuckDB はシグナルやマーケットデータ、分析用途のストアとして想定されています。監視等は SQLite を使用します。

---

## ディレクトリ構成（主要ファイル）

src/kabusys/
- __init__.py
  - パッケージ定義、バージョン情報
- config.py
  - 環境変数の自動読み込みロジックと Settings クラス
- config_setup.py
  - .env を対話的に作成・更新するウィザード
- validate_config.py
  - 起動前に .env や config/*.yaml の整合性をチェックする CLI
- run_execution.py
  - ExecutionEngine 起動スクリプト（PID 管理、停止フラグ対応）
- run_monitoring.py
  - SystemMonitor ポーリングループ 起動スクリプト
- execution/
  - broker_api.py
    - BrokerAPIProtocol、データモデル、例外、ファクトリ
  - broker_factory.py
    - Settings に基づきブローカークライアントを生成
  - kabu_client.py
    - kabuステーション用 HTTP/WebSocket クライアント（httpx/websocket-client）
  - mock_client.py
    - テスト用の MockBrokerClient（fill_mode 等を指定可能）
  - order_record.py
    - OrderRecord（状態遷移ロジック）、OrderState enum
  - order_repository.py
    - SQLite を使った注文の永続化レイヤ
  - order_manager.py
    - OrderRecord と OrderRepository、BrokerAPI を組み合わせた高レベル API（作成・送信・同期・キャンセル）
  - execution_engine.py
    - 発注エンジン本体（シグナル処理、WebSocket ドレイン、kill_switch 等）
  - reconciler.py
    - 起動時リコンシリエーション（OrderSent の突合、ポジション差分検出）
  - risk_manager.py
    - 3段階リスクガード（Gate1/2/3）、サーキットブレーカー、レート制御
- data/
  - calendar_management.py
    - マーケットカレンダー管理、営業日計算、J-Quants との同期ジョブ
  - news_collector.py
    - RSS フィードからのニュース収集、URL 正規化、XML の安全処理
  - (その他 jquants_client 等、外部連携モジュールが想定される)
- monitoring/
  - monitoring_db.py (参照あり)
  - system_monitor.py (参照あり)
  - 監視用テーブルやログ出力を扱うモジュール群（詳細は該当ファイルを参照）
- utils/
  - logging_setup.py
  - process_priority.py
  - などユーティリティ

補足:
- validate_config.py が参照する config/*.yaml（system_config.yaml 等）は config ディレクトリに置く想定です。ファイル一覧:
  - system_config.yaml
  - data_config.yaml
  - strategy_config.yaml
  - risk_config.yaml
  - execution_config.yaml
  - monitoring_config.yaml

---

## 参考・次のステップ

- .env を作成し、python -m kabusys.validate_config で検証してください。
- 開発/テストでは KABUSYS_ENV=development または paper_trading を使用し、MockBrokerClient を活用して実行フローを検証してください。
- 実運用を検討する場合は、KabuStationClient 周りの実装や安全設定（LINE 通知設定、Kill Switch の運用など）を十分に検討してください。

---

作成された README に関して追記・修正したい点や、各コマンドの例（.env のサンプル等）を追加したい場合は指示ください。