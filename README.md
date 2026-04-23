# KabuSys

日本株自動売買システム（KabuSys）のリポジトリ内ドキュメントです。  
この README はローカル開発・テスト用途に焦点を当て、設定方法・起動方法・主要モジュールの概要を日本語でまとめています。

## プロジェクト概要
KabuSys は、シグナルに基づく自動発注エンジンおよび監視機能を備えた日本株向け自動売買フレームワークです。  
主な設計ポイントは以下の通りです。

- シグナル駆動（DuckDB からシグナルを読み取り発注）
- ExecutionEngine による発注ワークフロー（信号→Gate1/2でのリスク検査→発注→Reconciliation）
- MockBrokerClient によるペーパートレード/開発用テスト（live 実装は未完成）
- 起動前設定検証・対話式 .env 作成ウィザード
- 監視（SystemMonitor）プロセスの起動スクリプト
- J-Quants カレンダー・ニュース収集など Data 周りのユーティリティ

## 機能一覧
- .env 対話式ウィザード（config_setup）
- 起動前の設定検証 CLI（validate_config、--strict で警告も fail）
- ExecutionEngine：シグナル読み取り→発注→push drain・kill switch
- Order 管理：OrderRecord（状態遷移）、OrderRepository（SQLite 永続化）、OrderManager（発注フロー）
- Broker クライアント層：MockBrokerClient / KabuStationClient（REST / WebSocket）
- RiskManager：Gate1/2/3 によるリスク統制（余力、ポジション上限、レート制限、サーキットブレーカー、ドローダウン）
- Reconciler：起動時の OrderSent 照合・ポジション差分検出
- Data utilities：マーケットカレンダー管理、ニュース収集（RSS）
- 監視ループ起動スクリプト（run_monitoring）

## 必要条件（推奨）
- Python 3.10+
- SQLite（標準ライブラリ）
- 以下の外部パッケージ（最低限、実行する機能に応じて）:
  - duckdb
  - httpx
  - websocket-client
  - PyYAML（config YAML のパース検証に使用）
  - defusedxml（ニュース収集）
- （任意）J-Quants API トークン / kabuステーション のセットアップ（本番接続時）

※ requirements.txt は本リポジトリに含まれていません。開発環境では仮想環境を作成し、上記パッケージをインストールしてください。

例:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb httpx websocket-client PyYAML defusedxml
```

## セットアップ手順（ローカル開発向け）
1. リポジトリをクローンしてワークディレクトリへ移動
2. 仮想環境を作成・有効化
3. 必要な Python パッケージをインストール（上記参照）
4. .env の準備
   - 対話式で作成する（推奨）:
     ```bash
     python -m kabusys.config_setup
     ```
     指示に従って入力するとプロジェクトルートに `.env` が作成されます。
   - 手動作成の場合は `.env.example` を参照（本リポジトリに例がない場合は config_setup の出力フォーマットを参考にしてください）。
5. 設定検証（起動前チェック）:
   ```bash
   python -m kabusys.validate_config
   # 警告も失敗扱いにする場合
   python -m kabusys.validate_config --strict
   ```

## 環境変数（主なもの）
以下は主要な環境変数の一覧です。必須は特に明記しています。

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants API 用リフレッシュトークン（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）

任意 / 推奨:
- KABUSYS_ENV — 実行環境: development / paper_trading / live（デフォルト: development）
  - 注意: live を設定すると本番ガードがいくつか有効化されます（LINE 通知未設定等で警告）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視 DB（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — paper_trading 用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- KABU_API_BASE_URL — kabu station API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — 本番通知用（任意）
- KILL_FLAG_CLEAR_ON_START — 起動時 kill.flag を自動クリア（0/1、デフォルト 0）

注意: .env は絶対に Git にコミットしないでください（config_setup のヘッダにも注意書きあり）。

## 使い方（主なコマンド）
- 環境設定ウィザード（.env の作成・更新）
  ```bash
  python -m kabusys.config_setup
  ```

- 設定検証（起動前チェック）
  ```bash
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- 監視プロセス起動（SystemMonitor のポーリング）
  ```bash
  python -m kabusys.run_monitoring
  ```
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を変更可能（デフォルト 60 秒）。
  - 監視は KABUSYS_ENV にかかわらず本番 sqlite_path（SQLITE_PATH）を使用します。

- 実行エンジン起動（ExecutionEngine）
  ```bash
  python -m kabusys.run_execution
  ```
  - KABUSYS_ENV=paper_trading または development の場合は MockBrokerClient が使用されます（paper_trading 用 DB に記録されます）。
  - KABUSYS_ENV=live の場合、BrokerClientFactory は NotImplementedError を投げます（live 実装は未実装）。
  - 停止フラグ: プロジェクトルートの `data/stop_requested.flag` を作成するとループが終了します。
  - PID ファイルや kill.flag の仕組みを参照（Settings でパスを設定可能）。

- ライブラリとしての利用（コード内で）
  - 設定取得:
    ```py
    from kabusys.config import settings
    token = settings.jquants_refresh_token
    ```
  - Broker クライアント生成:
    ```py
    from kabusys.execution.broker_factory import BrokerClientFactory
    client = BrokerClientFactory.create(settings)
    ```

## 注意点・運用上のポイント
- 本番環境（KABUSYS_ENV=live）では設定ミスが致命的になり得ます。validate_config の結果を必ず確認してください。
- 設計上、OrderSent 状態でクラッシュしても Reconciler により再照合できるよう 2相永続化の工夫があります（OrderManager の処理フロー参照）。
- paper_trading モードは実データベース（paper_trading 用 SQLite）に分離され、本番データを汚染しないよう配慮されています。
- WebSocket（kabu push）受信は KabuStationClient の stream_push によりスレッドで実行されます。stop_event によるクリーンシャットダウンに対応しています。
- live broker client は現状未実装のため、本番運用するには追加実装が必要です。

## ディレクトリ構成（主要ファイルと説明）
（リポジトリ内 src/kabusys 配下の主要ファイルを抜粋）

- src/kabusys/__init__.py
  - パッケージ定義、バージョン情報

- src/kabusys/config.py
  - 環境変数 / .env 自動ロード / Settings クラス（アプリ設定の集中管理）

- src/kabusys/config_setup.py
  - .env 対話式ウィザード（python -m kabusys.config_setup）

- src/kabusys/validate_config.py
  - 起動前設定検証 CLI（python -m kabusys.validate_config）

- src/kabusys/run_execution.py
  - ExecutionEngine を起動するスクリプト（python -m kabusys.run_execution）

- src/kabusys/run_monitoring.py
  - SystemMonitor ポーリングループ起動スクリプト（python -m kabusys.run_monitoring）

- src/kabusys/execution/
  - broker_api.py — Broker API の Protocol / データモデル / ファクトリ
  - broker_factory.py — 設定に応じたブローカークライアント生成
  - kabu_client.py — kabu station 実装（HTTP + WebSocket）
  - mock_client.py — MockBrokerClient（テスト・開発用）
  - order_record.py — Order 状態遷移ロジック（純粋なビジネスロジック）
  - order_repository.py — SQLite 永続化層
  - order_manager.py — OrderManager（外向き API、発注フロー）
  - execution_engine.py — ExecutionEngine（シグナルの読み取り、発注ロジック）
  - reconciler.py — リコンシリエーション（再起動時の復旧）
  - risk_manager.py — 3 段階リスクガード（Gate1/2/3）

- src/kabusys/data/
  - calendar_management.py — 市場カレンダー管理（J-Quants 経由の更新・営業日判定）
  - news_collector.py — RSS ニュース収集・前処理（defusedxml 等利用）

- src/kabusys/monitoring/
  - monitoring_db.py — 監視用 SQLite テーブル初期化・ログ記録など
  - system_monitor.py — SystemMonitor（ポーリングでシステム指標を記録）  ※（コードは run_monitoring から参照）

- src/kabusys/utils/
  - logging_setup.py — ロギング初期化ヘルパ
  - process_priority.py — プロセス優先度の設定ユーティリティ

（上記は主要ファイルの抜粋です。他にも補助的なモジュールが含まれます）

## 開発・テストのヒント
- ExecutionEngine の単体テストやロジック検証は MockBrokerClient を用いて行うと容易です。
- Reconciler、OrderManager、OrderRepository はトランザクションや状態遷移の整合性が重要なのでユニットテストを充実させてください。
- news_collector などはネットワーク依存なので外部接続をモックしてテストを行うと安定します。

---

問題や追加したいドキュメント（アーキテクチャ図、API 仕様、運用手順など）があれば知らせてください。README を用途に合わせて追記します。