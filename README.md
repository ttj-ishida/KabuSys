# KabuSys

日本株自動売買システム（KabuSys）のリポジトリ内 README。  
この README はコードベース（src/kabusys 以下）の主要な概要、起動・設定手順、使い方、ディレクトリ構成をまとめたものです。

---

## プロジェクト概要

KabuSys は日本株自動売買のためのミニマルなフレームワークです。  
主な機能は以下の通りです：

- シグナルに基づく発注エンジン（ExecutionEngine）
- ブローカークライアント抽象化（kabu station 実装 + モック）
- 注文状態管理（OrderRecord / OrderManager / OrderRepository）
- 発注前後の 3 段階リスクガード（RiskManager）
- 起動時のリコンシリエーション（Reconciler）
- 監視（SystemMonitor / monitoring DB）
- データ周り（マーケットカレンダー、ニュース収集等）
- 環境設定ウィザード（.env の対話的生成）
- 起動前設定検証 CLI（.env と config/*.yaml の簡易チェック）

設計方針として、ビジネスロジックと永続化層を分離し、モッククライアントによりローカル開発・テストを実行可能にしています。

---

## 主な機能一覧

- 環境設定ウィザード: python -m kabusys.config_setup  
  対話的に `.env` を作成 / 更新します。

- 設定検証ツール: python -m kabusys.validate_config [--strict]  
  必須環境変数や config/*.yaml の存在・パースをチェックします。

- 実行エンジン: python -m kabusys.run_execution  
  ExecutionEngine を起動し、シグナルに基づく発注セッションを実行します。paper_trading/development ではモックブローカーを使用します（live は未実装）。

- 監視ループ: python -m kabusys.run_monitoring  
  SystemMonitor のポーリングループを起動してシステムメトリクス等を監視します。

- ブローカー層:
  - 実ブローカー: KabuStationClient（kabu station REST API 実装）
  - テスト用モック: MockBrokerClient（fill_mode 等で動作を制御）

- 注文永続化: SQLite（orders テーブル）を利用する OrderRepository。DB 初期化用関数あり。

- データ処理:
  - DuckDB ベースのマーケットデータ / シグナル参照
  - カレンダー管理（JPX 営業日判定）
  - ニュース収集（RSS の正規化・保存ロジック）

---

## セットアップ手順（ローカル開発向け）

1. リポジトリをクローンして適切な Python 環境を用意します（推奨: venv / pyenv）。
2. 依存パッケージをインストールします（requirements.txt が無い場合は主な依存を個別に入れてください）:

   例（推奨パッケージ）:
   - duckdb
   - httpx
   - websocket-client
   - PyYAML (config/*.yaml のパース検証に必要)
   - defusedxml

   pip 例:
   ```
   python -m pip install duckdb httpx websocket-client pyyaml defusedxml
   ```

3. .env を作成します（2通り）:
   - 対話ウィザードで作成:
     ```
     python -m kabusys.config_setup
     ```
   - 既存のテンプレート（.env.example）がある場合はコピーして編集:
     ```
     cp .env.example .env
     ```

   自動ロードについて:
   - package の import 時に .env / .env.local をプロジェクトルートから自動ロードします（OS 環境変数 > .env.local > .env）。
   - 自動ロードを無効にする場合は環境変数を設定:
     ```
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```

4. .env の中身を検証します:
   ```
   python -m kabusys.validate_config
   # 警告も失敗にしたい場合:
   python -m kabusys.validate_config --strict
   ```

5. データディレクトリ（デフォルト: data/）を確認します。DB ファイルパスは .env で上書き可能です（下記参照）。

---

## 必要な環境変数（主要）

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants API のリフレッシュトークン（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）

オプション / デフォルト:
- KABUSYS_ENV — 実行環境 ("development" / "paper_trading" / "live")（デフォルト: development）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト: data/monitoring.db）
- LOG_LEVEL — ログレベル ("DEBUG","INFO","WARNING","ERROR","CRITICAL")（デフォルト: INFO）
- KABU_API_BASE_URL — kabu station のベース URL（デフォルト: http://localhost:18080/kabusapi）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — LINE 通知設定（本番で必要）

その他（実装上利用）:
- PAPER_FILL_MODE — paper_trading モードのモック約定挙動 ("instant"|"partial"|"never"|"reject")
- PAPER_TRADING_SQLITE_PATH — paper trading 用 SQLite（デフォルト: data/paper_trading.db）
- PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START 等（監視・停止制御に利用）

注意:
- validate_config は .env のプレースホルダや未設定を検出します。
- KABUSYS_ENV=live を指定する場合は注意（本番設定、警告多数）。現時点で Live broker client は部分未実装の箇所があります（Factory では NotImplementedError を投げる箇所あり）。

---

## 使い方（コマンド例）

- 環境設定ウィザード（.env を生成 / 更新）
  ```
  python -m kabusys.config_setup
  ```

- 起動前設定検証
  ```
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict  # 警告も FAIL 扱い
  ```

- 実行エンジンを起動（本番セッションのエントリポイント）
  ```
  python -m kabusys.run_execution
  ```
  - KABUSYS_ENV が `paper_trading` または `development` の場合はモックブローカーを使用します。
  - `live` は現状 NotImplemented（例外が出るので注意）。

- 監視ループを起動
  ```
  python -m kabusys.run_monitoring
  ```
  - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）。
  - 停止制御はプロジェクトルートの `data/stop_requested.flag` ファイルを作成することで行います。

- 停止 / 強制停止
  - エンジン・監視は `data/stop_requested.flag`、および `data/kill.flag`（kill switch）等で制御します。`.env` の `KILL_FLAG_CLEAR_ON_START` によって起動時の挙動が変わります。

---

## 注意事項 / ヒント

- DB:
  - DuckDB は分析・シグナル取得用（デフォルト: data/kabusys.duckdb）。
  - SQLite は監視・注文永続化に使用（デフォルト: data/monitoring.db）。paper_trading では data/paper_trading.db を使うよう分離されています。
  - orders テーブル作成用の init_orders_db / init_monitoring_db 関数が用意されています（各起動処理で呼ばれます）。

- リコンシリエーション:
  - 起動時に OrderSent 状態で残った不確定注文をブローカーと突合して同期する処理（Reconciler）が組み込まれています。

- WebSocket:
  - KabuStationClient は push（WebSocket）受信をサポートし、ExecutionEngine の push drain ループで処理します（モックは stream_push を持たない場合があります）。

- テスト:
  - MockBrokerClient により fill_mode を変えて発注挙動をテスト可能（instant/partial/never/reject）。

---

## ディレクトリ構成（主要ファイル）

リポジトリの src/kabusys 以下の主な構成：

- kabusys/
  - __init__.py
  - config.py — 環境変数読み込み / Settings（自動 .env ロード含む）
  - config_setup.py — 対話式 .env ウィザード
  - validate_config.py — 起動前設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト（エントリポイント）
  - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト
  - execution/
    - broker_api.py — Broker API の Protocol / データモデル / ファクトリ
    - broker_factory.py — Settings に基づく Broker client 作成
    - kabu_client.py — kabu station REST API 実装（HTTP + WebSocket）
    - mock_client.py — 開発用モック実装
    - order_record.py — 注文状態モデルと状態遷移ロジック
    - order_repository.py — SQLite 永続化層（orders）
    - order_manager.py — OrderRecord と Broker を結ぶ管理層
    - execution_engine.py — 発注エンジン本体
    - reconciler.py — 起動時のリコンシリエーション処理
    - risk_manager.py — Gate1/2/3 のリスク制御ロジック
  - data/
    - calendar_management.py — マーケットカレンダー管理（DuckDB）
    - news_collector.py — RSS ニュース収集（defusedxml 等を使用）
    - (jquants_client 等の補助モジュールが想定)
  - monitoring/
    - monitoring_db.py — 監視用 DB 初期化・操作（参照のみのファイル起点あり）
    - system_monitor.py — 実際の監視ロジック（run_monitoring が使用）
  - utils/
    - logging_setup.py — ロギング初期化ヘルパ
    - process_priority.py — プロセス優先度設定ユーティリティ

（上記はコードベースから参照されている主要モジュール群。実際のファイル・実装はリポジトリに依存します。）

---

## 追加情報 / 開発者向けメモ

- Settings クラスは環境変数を厳密に検証します。誤った設定値は ValueError を発生させることがあります。
- validate_config は PyYAML 未インストール時に YAML 内容検証をスキップします（ただしファイルの存在チェックは行う）。
- ExecutionEngine は PID ファイルの書き込み・kill flag の検査等の安全機構を備えています。起動前に kill.flag が残っている場合は .env の `KILL_FLAG_CLEAR_ON_START` に応じて起動を拒否またはクリアします。
- Live ブローカー（kabu station）との連携は慎重に扱ってください。local 環境や paper_trading で十分検証した上で本番に移行してください。

---

必要であれば、README に具体的な .env テンプレートや依存関係の requirements.txt、起動例やログ確認方法、単体テストの実行手順などを追加できます。どの情報をさらに追加しますか？