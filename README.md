# KabuSys — 日本株自動売買システム（README）

概要
-
KabuSys は日本株自動売買のための小規模フレームワークです。  
主に以下を提供します。

- シグナルに基づく発注エンジン（ExecutionEngine）
- ブローカー API 抽象（kabu station 実装とモック）
- 発注履歴の永続化（SQLite）
- 監視用プロセス（SystemMonitor / monitoring）
- データ処理ユーティリティ（カレンダー管理、ニュース収集等）
- .env による環境設定と対話式ウィザード / 検証ツール

主な機能
-
- 環境設定ウィザード（python -m kabusys.config_setup）
  - 対話的に .env を作成 / 更新できます（シークレットはマスク表示）
- 設定検証ツール（python -m kabusys.validate_config）
  - .env と config/*.yaml の存在や基本的な整合性をチェック。--strict モードあり（警告も失敗扱い）
- ExecutionEngine
  - シグナルの読み込み → Gate1/Gate2 のリスクチェック → 発注 → WebSocket ドレイン
  - paper_trading / development 環境では MockBrokerClient を使い、本番 DB と分離
- Order 管理
  - OrderRecord（状態遷移ロジック）、OrderRepository（SQLite 永続化）、OrderManager（外向き API）
  - 再起動時のリコンシリエーション（Reconciler）で OrderSent の不確定状態を照合
- RiskManager（3段階ガード）
  - Gate1: 余力 / 重複 / ポジション上限
  - Gate2: レート制限・サーキットブレーカー
  - Gate3: ドローダウン監視（キルスイッチ）
- ブローカークライアント群
  - KabuStationClient（kabu station REST + WebSocket）
  - MockBrokerClient（fill_mode による挙動切替でテスト可能）
- データモジュール
  - DuckDB を用いたマーケットカレンダー管理、ニュース収集など

セットアップ手順
-
1. リポジトリをクローンし、プロジェクトルートへ移動する。

2. Python 環境を用意する（推奨: venv）。例:
   ```
   python -m venv .venv
   source .venv/bin/activate
   ```

3. 依存関係をインストールする（requirements.txt がある前提）。例:
   ```
   pip install -r requirements.txt
   ```
   注: YAML のパース検証を行いたい場合は PyYAML（pip install pyyaml）をインストールしてください。WebSocket 用に websocket-client、HTTP 用に httpx 等が必要です。

4. .env の作成
   - 対話式ウィザードを実行して初期設定を作成:
     ```
     python -m kabusys.config_setup
     ```
   - 既存の .env がある場合は .env.local を使って上書きできます。
   - 自動で .env を読み込む仕組みがあり、OS 環境 > .env.local > .env の優先順位です。自動ロードを無効化するには環境変数を設定:
     ```
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```

5. 設定検証
   - 基本チェック:
     ```
     python -m kabusys.validate_config
     ```
   - 警告も失敗扱いにする（CI 等）:
     ```
     python -m kabusys.validate_config --strict
     ```

6. DB 初期化
   - 監視用 SQLite / orders テーブル等は起動時に自動で初期化するユーティリティが呼ばれます（init_monitoring_db, init_orders_db）。手動で初期化する場合はコードの該当関数を呼んでください。

使い方（起動例）
-
- 実行エンジン（発注）
  - ローカル検証 / ペーパートレード:
    ```
    python -m kabusys.run_execution
    ```
    KABUSYS_ENV が paper_trading か development の場合、MockBrokerClient を使います。paper_trading は専用 SQLite（デフォルト: data/paper_trading.db）に記録され、本番 DB と分離されます。

- 監視プロセス
  ```
  python -m kabusys.run_monitoring
  ```
  MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書きできます（デフォルト 60 秒）。監視は常に本番の sqlite_path を参照します（設定により変更可）。

主要な環境変数
-
必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

任意（例）:
- KABUSYS_ENV = development | paper_trading | live
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（デフォルト: data/monitoring.db）
- LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- KABU_API_BASE_URL（kabu station のベース URL）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID（本番アラート用）
- KILL_FLAG_CLEAR_ON_START（起動時に kill.flag を自動クリアするか、0 or 1）

注意:
- .env は絶対に Git にコミットしないでください（ウィザードや README 内にも警告あり）。
- KABUSYS_ENV=live 設定は本番リスクを伴います。validate_config は live 時の追加警告を行います。

構成ファイル（config/*.yaml）
-
validate_config でチェックするファイル例:
- config/system_config.yaml
- config/data_config.yaml
- config/strategy_config.yaml
- config/risk_config.yaml
- config/execution_config.yaml
- config/monitoring_config.yaml

これらはプロジェクトの動作設定に使われます。generate_config スクリプト（リポジトリ内にある場合）で雛形を生成できます。

ディレクトリ構成（主要ファイル）
-
src/kabusys/
- __init__.py
- config.py — 環境変数の読み込み / Settings（自動 .env 読み込みロジック含む）
- config_setup.py — .env 対話式ウィザード
- validate_config.py — 起動前の設定検証 CLI
- run_execution.py — ExecutionEngine 起動スクリプト
- run_monitoring.py — SystemMonitor ポーリング起動スクリプト

パッケージ
- execution/
  - broker_api.py — BrokerAPIProtocol、データモデル、例外、ファクトリ
  - kabu_client.py — kabu station 実装（HTTP + WebSocket）
  - mock_client.py — MockBrokerClient（テスト用）
  - broker_factory.py — 設定に基づくクライアント生成
  - order_record.py — 注文状態モデルと状態遷移
  - order_repository.py — SQLite 永続化（orders テーブル）
  - order_manager.py — 注文作成・送信・同期 API
  - execution_engine.py — 発注エンジン（シグナル処理・push ドレイン）
  - reconciler.py — リコンシリエーション（再起動復旧）
  - risk_manager.py — 3段階リスクガード

- data/
  - calendar_management.py — マーケットカレンダー（DuckDB）管理
  - news_collector.py — RSS ニュース収集/前処理（SSRF/サイズ制限等に配慮）

- monitoring/
  - monitoring_db.py, system_monitor.py （監視関連 — run_monitoring で使用）

- utils/
  - logging_setup.py — ログ初期化ユーティリティ
  - process_priority.py — プロセス優先度設定等

運用上のポイント
-
- Kill スイッチ:
  - settings.kill_flag_path（デフォルト: data/kill.flag）を置くことでプロセスを停止させます。起動時に kill.flag があれば設定に応じて起動を拒否するか自動クリアするかが制御されます（KILL_FLAG_CLEAR_ON_START）。
- PID ファイル:
  - ExecutionEngine は PID を data/execution.pid 等へ書きます（設定可能）。
- リコンシリエーション:
  - 再起動時に OrderSent の不確定注文をブローカーと突合して状態回復を試みます（Reconciler）。

トラブルシューティング
-
- YAML 検証を行うには PyYAML をインストールしてください。validate_config は未インストール時に YAML 検証をスキップして警告を出します。
- 設定検証ツール（validate_config）は .env にプレースホルダ（your_value や *_here）を見つけると警告を出します。--strict では警告を失敗扱いにできます。

ライセンス / バージョン
-
- パッケージバージョンは src/kabusys/__init__.py の __version__ を参照してください（例: 0.1.0）。

問い合わせ / 変更履歴
-
- 詳細な設計メモや DataPlatform.md に基づく仕様はリポジトリ内のドキュメントを参照してください。

以上を参考に、まずは .env を作成 -> python -m kabusys.validate_config で検証 -> python -m kabusys.run_execution / run_monitoring で各プロセスを起動してください。必要があれば追加で README にデプロイ手順や CI 設定を追記できます。