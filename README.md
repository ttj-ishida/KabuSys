# KabuSys

日本株自動売買システム（KabuSys）の一部実装。  
本リポジトリは設定管理、発注エンジン、監視ループ、ブローカークライアント（モック/実装）などのコアコンポーネントを含みます。

## プロジェクト概要
KabuSys は日本株向けの自動売買フレームワークです。  
主な設計方針は安全性（リスクガード、サーキットブレーカー、kill switch）、再起動耐性（リコンシリエーション）、テスト容易性（MockBrokerClient）です。  
設定は環境変数（.env / .env.local）で管理し、実行前に検証ツールでチェックできます。

## 主な機能一覧
- 環境変数/.env の対話式ウィザード（.env 作成・更新）
- 起動前の設定検証 CLI（必須項目や config/*.yaml の存在/パースをチェック）
- ExecutionEngine（シグナル読み込み→Gate1/2 を経て発注、WebSocket push のドレイン処理）
- モニタリング用ポーリングループ（SystemMonitor を周期的に実行）
- ブローカークライアント
  - MockBrokerClient（テスト/開発用・複数の fill_mode をサポート）
  - KabuStationClient（kabuステーション REST API 実装、WebSocket push 対応）
- 注文状態管理（OrderRecord の状態機械と検査）
- 永続化（orders を SQLite、分析用に DuckDB を利用）
- RiskManager（3段階のリスクガード: Gate1/2/3、レート制限、サーキットブレーカー、ドローダウン監視）
- Reconciler（再起動時の OrderSent 照合とポジション差分チェック）
- データ系ユーティリティ（マーケットカレンダー管理、ニュース収集など）
- ロギング・プロセス優先度設定・PID / kill flag 管理

## 必須／推奨環境変数
必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

任意（デフォルトあり）:
- KABUSYS_ENV (development | paper_trading | live) — default: development
- DUCKDB_PATH — default: data/kabusys.duckdb
- SQLITE_PATH — default: data/monitoring.db
- LOG_LEVEL — default: INFO
- KABU_API_BASE_URL — default: http://localhost:18080/kabusapi
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID — アラート通知用

その他、起動時の Kill Switch 関連やモニタリング間隔を調整する環境変数が存在します（例: KILL_FLAG_CLEAR_ON_START, MONITOR_POLL_INTERVAL）。

## セットアップ手順（ローカル開発向け）
1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo-root>
   ```

2. Python 仮想環境の作成・有効化（例）
   ```
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
   ```

3. 依存パッケージをインストール（最低限）
   ```
   pip install duckdb httpx websocket-client defusedxml
   ```
   追加（任意だが便利）:
   - PyYAML（config/*.yaml のパース検証を有効にする）:
     ```
     pip install pyyaml
     ```

   注: SQLite は標準ライブラリに含まれます。

4. .env を作成
   - 対話式ウィザードを利用:
     ```
     python -m kabusys.config_setup
     ```
   - もしくは手動でプロジェクトルートに `.env` を作成して必要な環境変数を設定してください。

5. 設定検証
   ```
   python -m kabusys.validate_config
   # 警告も失敗扱いにする場合:
   python -m kabusys.validate_config --strict
   ```

## 使い方（主なスクリプト）
- 実行エンジンを起動（通常はデーモン/サービスとして起動）
  ```
  python -m kabusys.run_execution
  ```
  - KABUSYS_ENV が `paper_trading` の場合、モックブローカーを使い paper_trading 用 SQLite（data/paper_trading.db）に記録します。
  - プロセス優先度を高く設定し、PID ファイル / kill flag を管理します。

- 監視ループ起動
  ```
  python -m kabusys.run_monitoring
  ```
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を変更可能（デフォルト 60 秒）。
  - 監視は常に本番用 sqlite_path を用いて実行されます（環境に依らず）。

- 設定ウィザード
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config [--strict]
  ```

注意:
- KabuStationClient を利用するにはローカルで kabuステーションアプリが起動している前提です（API エンドポイントとポートを合わせてください）。その場合 KABU_API_BASE_URL を設定します。
- 実運用での `KABUSYS_ENV=live` は慎重に。validate_config は live 時に追加の警告を出します（LINE 通知の未設定など）。

## ディレクトリ構成（主要ファイル）
以下はパッケージの主要ファイルと役割です（リポジトリの src/kabusys を想定）。

- src/kabusys/
  - __init__.py — パッケージ定義（バージョン等）
  - config.py — 環境変数/.env の自動ロード、Settings クラス（設定値の抽象化）
  - config_setup.py — .env 対話式ウィザード（生成・更新）
  - validate_config.py — 起動前の設定検証 CLI（必須環境変数・config YAML の検証等）
  - run_execution.py — ExecutionEngine 起動スクリプト（発注エンジン）
  - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト

  - execution/  — 発注周りのコアロジック
    - broker_api.py — Broker API のデータモデル、Protocol、例外、ファクトリ
    - broker_factory.py — Settings に基づくブローカークライアント生成
    - kabu_client.py — kabuステーション REST/WebSocket クライアント（実装）
    - mock_client.py — MockBrokerClient（テスト用）
    - order_record.py — Order の状態機械（純粋ビジネスロジック）
    - order_repository.py — SQLite による永続化（orders テーブルの作成/CRUD）
    - order_manager.py — OrderRecord + Repository + Broker を結びつける外向き API
    - execution_engine.py — 実際のセッション制御（シグナル処理／WebSocket ドレイン）
    - reconciler.py — 再起動時の照合・復旧ロジック
    - risk_manager.py — 3段階リスクガード（Gate1/2/3）

  - data/  — データ関連ユーティリティ
    - calendar_management.py — マーケットカレンダー（営業日判定、next/prev 等）
    - news_collector.py — RSS ニュースの収集と前処理（SSRF 等対策含む）
    - （jquants_client 等のクライアントを想定）

  - monitoring/  — 監視用（DB 初期化や SystemMonitor 実装がここに存在）
    - monitoring_db.py
    - system_monitor.py

  - utils/  — 補助ユーティリティ
    - logging_setup.py — ログ設定
    - process_priority.py — プロセス優先度設定

（注）上記は主要なモジュールの抜粋です。実際のファイル数はプロジェクトにより異なります。

## その他の運用メモ
- データベース
  - DuckDB: シグナルや分析用（デフォルト data/kabusys.duckdb）
  - SQLite: 監視・注文履歴（data/monitoring.db、paper_trading 用に data/paper_trading.db を使用することがある）

- Kill Switch
  - kill.flag（デフォルト: data/kill.flag）を検出するとセッションを停止し、全 active 注文をキャンセルします。
  - KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に既存の kill.flag を自動クリアします（本番では推奨されません）。

- 再起動耐性
  - 発注は二相永続化（OrderSent 保存 → broker 呼び出し → broker_order_id を保存 → OrderAccepted へ遷移）により、途中クラッシュ時に照合可能な状態を残す設計です。
  - Reconciler は起動時に OrderSent の不確定注文を broker と照合します。

## よく使うコマンドまとめ
- 仮想環境作成/有効化、依存インストール
- .env 作成:
  ```
  python -m kabusys.config_setup
  ```
- 設定検証:
  ```
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```
- 実行エンジン起動:
  ```
  python -m kabusys.run_execution
  ```
- 監視ループ起動:
  ```
  python -m kabusys.run_monitoring
  ```

---

README の内容は開発中の実装を元に作成しています。実運用前には各モジュールの詳細な設定、監視、バックアップ、テスト（特に live 環境）を慎重に行ってください。必要ならば README に追記・補足を行います。