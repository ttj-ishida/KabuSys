# KabuSys

日本株向け自動売買システム（KabuSys）のリポジトリ向け README（日本語）

概要、主要機能、セットアップ手順、使い方、ディレクトリ構成などをまとめています。

※ この README はソースコード（src/kabusys/*.py）を元に作成しています。

---

## プロジェクト概要

KabuSys は日本株の自動売買を行うためのモジュール群です。  
主要な役割は以下のとおりです。

- ブローカー（kabuステーション等）との API 統合（発注、取消、残高/ポジション取得）
- 発注フロー（Order 管理、永続化、状態遷移、Reconciliation）
- リスクガード（Gate1〜3：余力/重複/ポジション上限、レート制限・サーキットブレーカー、ドローダウン監視）
- 実行エンジン（Signal を取り込み発注、WebSocket Push のドレイン）
- 監視プロセス（SystemMonitor を周期的に実行）
- 環境設定ウィザード・設定検証（.env の対話作成や config/*.yaml のチェック）
- テスト/開発用に MockBrokerClient を提供（paper_trading / development 向け）

---

## 主な機能一覧

- .env 対話式生成ウィザード（kabusys.config_setup）
- 起動前設定検証 CLI（kabusys.validate_config）:
  - 必須環境変数の有無チェック
  - KABUSYS_ENV / LOG_LEVEL の妥当性チェック
  - DB パスや config/*.yaml の存在とパースチェック（PyYAML がある場合）
  - 本番環境（KABUSYS_ENV=live）の追加ガード
- ExecutionEngine:
  - シグナル読み込み（DuckDB）
  - 発注フロー（OrderRecord / OrderRepository / OrderManager）
  - WebSocket Push ドレイン、Reconciler による再同期
  - kill.switch による全注文キャンセル
- RiskManager（Gate1〜3）:
  - 余力、重複、個別銘柄上限、全体投資上限
  - レート制限（トークンバケツ）、サーキットブレーカー
  - ドローダウン検知（キルスイッチ発動）
- MockBrokerClient：テストや開発で外部依存なしに発注/約定シミュレーション可能
- Monitoring loop（run_monitoring）: SystemMonitor のポーリング実行（SQLite/DUCKDB 利用）

---

## 必要な環境変数（主なもの）

validate_config.py に記載のうち、必須は次の 2 つです。

- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）

任意（またはデフォルトあり）:

- KABUSYS_ENV — 実行環境（development / paper_trading / live、デフォルト: development）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL、デフォルト: INFO）
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID — 本番アラート用（任意）

その他、実行時に使う設定:
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（0/1、デフォルト 0）
- MONITOR_POLL_INTERVAL — 監視ポーリング間隔（秒、run_monitoring 用）
- PAPER_FILL_MODE / PAPER_TRADING_SQLITE_PATH — ペーパートレード用設定

注意: .env ファイルは絶対にリポジトリにコミットしないでください（README 内にも警告あり）。

---

## セットアップ手順（開発用）

1. Python 環境を準備（推奨: 3.9+）

2. 必要ライブラリをインストール（プロジェクトに requirements.txt があればそれを利用）
   例（requirements.txt が無い場合の参考）:
   python -m pip install httpx websocket-client duckdb pyyaml defusedxml

   開発では MockBrokerClient を使うため、kabu station の実稼働クライアント依存は必須ではありません。

3. プロジェクトルート（.git または pyproject.toml のあるディレクトリ）に移動して、.env を作成:

   - 対話式ウィザードで作る:
     python -m kabusys.config_setup

   - 手動サンプル（.env）:
     JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     KABU_API_PASSWORD=your_kabu_api_password
     KABUSYS_ENV=development
     DUCKDB_PATH=data/kabusys.duckdb
     SQLITE_PATH=data/monitoring.db
     LOG_LEVEL=INFO

   生成・編集後、必ず設定検証を実行してください（次の節参照）。

4. 設定検証:
   python -m kabusys.validate_config
   警告を FAIL 扱いにする場合:
   python -m kabusys.validate_config --strict

5. DB 初期化などは、実行時に自動で必要なテーブル生成ロジック（init_monitoring_db / init_orders_db 等）を呼び出す実装があるため、通常は実行時に作成されます。

---

## 使い方（主なコマンド）

- 環境設定ウィザード（.env 生成／更新）
  python -m kabusys.config_setup

- 設定検証（起動前チェック）
  python -m kabusys.validate_config
  --strict を付けると警告も失敗（exit 1）扱いになります。

- 実行エンジン起動（発注エンジン）
  python -m kabusys.run_execution

  動作概要:
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用して data/paper_trading.db に記録（本番 DB と分離）
  - KABUSYS_ENV=development でも Mock を使用
  - KABUSYS_ENV=live は未実装（現状エラー）

  停止:
  - プロセスが参照する停止フラグ: data/stop_requested.flag を作成するとループは検知して終了します。
  - kill.flag（data/kill.flag）は kill switch（全注文キャンセル）や起動拒否の判定に使われます。
  - KILL_FLAG_CLEAR_ON_START=1 を設定すると、kill.flag があっても起動時に自動クリアされます（本番は推奨されません）。

- 監視プロセス（SystemMonitor ポーリング）
  python -m kabusys.run_monitoring

  MONITOR_POLL_INTERVAL 環境変数でポーリング秒数を指定可能（デフォルト 60 秒）。

---

## 運用上の注意

- 本番環境（KABUSYS_ENV=live）を使用する場合は validate_config の警告に注意してください。LINE 通知設定（LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID）が未設定だとアラートが届きません。
- .env は秘密情報を含むため絶対に Git にコミットしないでください。
- ExecutionEngine は PID ファイルを data/execution.pid（デフォルト）に書き込みます。PID/flag のパスは .env で上書き可能です。
- Reconciler（再同期）は起動時に OrderSent の不確定状態をブローカーと照合し復旧を試みます。これによりクラッシュ後の整合性を保ちます。
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると config.py による .env 自動読み込みを無効にできます（テスト目的など）。

---

## 主要ファイル・ディレクトリ構成

（src/kabusys を基準に主要モジュールを抜粋）

- src/
  - kabusys/
    - __init__.py  — パッケージ定義（version 等）
    - config.py  — 環境変数（.env）読み込みと Settings クラス
    - config_setup.py  — 対話式 .env 作成ウィザード
    - validate_config.py — 起動前の設定検証 CLI
    - run_execution.py — ExecutionEngine 起動スクリプト（発注エンジン）
    - run_monitoring.py — SystemMonitor ポーリング起動スクリプト

    - execution/  — 発注関連モジュール
      - broker_api.py — BrokerAPIProtocol / データモデル / ファクトリ
      - kabu_client.py — kabu station REST API クライアント実装
      - mock_client.py — MockBrokerClient（テスト用）
      - broker_factory.py — Settings によるクライアント生成ラッパ
      - order_record.py — Order の状態遷移ロジック（ビジネスロジック）
      - order_repository.py — SQLite 永続化層（orders テーブル）
      - order_manager.py — 発注ワークフロー（DB + broker 呼び出し）
      - execution_engine.py — 実行セッションのメインループ
      - reconciler.py — 再同期ロジック（起動時自動復旧）
      - risk_manager.py — Gate1〜3 のリスクチェック
      - ...（その他 execution 関連コンポーネント）

    - data/  — データ関連（DuckDB 連携、ニュース収集、カレンダー管理 等）
      - calendar_management.py — 営業日判定、calendar 更新ジョブ
      - news_collector.py — RSS ニュース収集（正規化・SSRF 対策 等）
      - jquants_client.py (参照されるがコードスナップショット未掲載)

    - monitoring/  — 監視（SystemMonitor、監視DB 初期化等）
      - monitoring_db.py
      - system_monitor.py

    - utils/  — 汎用ユーティリティ
      - logging_setup.py
      - process_priority.py

    - strategy/  — 戦略関連（スナップショットには詳細なし）
    - other configs: config/*.yaml — 各種設定ファイル（system_config.yaml, data_config.yaml, strategy_config.yaml, risk_config.yaml, execution_config.yaml, monitoring_config.yaml）

---

## 開発・拡張メモ

- BrokerClientFactory.create() は Settings を見て Mock（paper_trading / development）か Live を選択します。Live クライアントは未実装で NotImplementedError が投げられます。
- ExecutionEngine の run_session は 8:50-9:10 をシグナル処理、9:10-15:30 を push ドレインに割り当てる想定です（config で変更可能）。
- Order の堅牢な永続化パターン（OrderSent を先に永続化してから broker 呼び出し）や二相コミット風の扱いが実装されています。Reconciliation 周りの設計に注目してください。
- news_collector.py には SSRF 対策、XML パースの安全対策（defusedxml）、受信サイズ制限などが実装されています。

---

## 参考コマンドまとめ

- .env ウィザード:
  python -m kabusys.config_setup

- 設定検証:
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict

- 実行エンジン（発注）起動:
  python -m kabusys.run_execution

- 監視ループ起動:
  python -m kabusys.run_monitoring

---

必要であれば README にサンプル .env の完全なテンプレートや、依存パッケージ一覧（requirements.txt）/起動用 systemd ユニットの例 / Dockerfile サンプルなども追加できます。どの情報を優先して追加するか教えてください。