# KabuSys

日本株自動売買システムのコア実装サンプル（ライブラリ / 実行スクリプト群）

---

## プロジェクト概要

KabuSys は日本株アルゴリズム取引向けの自動売買コンポーネント群です。  
主な役割は以下の通りです。

- 発注エンジン（ExecutionEngine）によるシグナル取込みと発注処理
- ブローカー API 抽象（kabu station 実装 + Mock 実装）
- 注文状態管理（OrderRecord / OrderRepository / OrderManager）
- リスクガード（3段階: Gate1/Gate2/Gate3）
- 起動時のリコンシリエーション（Reconciler）
- 監視ループ（SystemMonitor を使った polling）
- データ系ユーティリティ（マーケットカレンダー、ニュース収集など）
- 環境設定ウィザード、検証ユーティリティ

本 README はリポジトリ内の主要モジュール（src/kabusys 以下）に基づく使い方・設定方法を示します。

---

## 機能一覧

- 環境設定ウィザード（対話式 .env 作成 / 更新）
  - python -m kabusys.config_setup
- 起動前設定検証（.env / config/*.yaml の存在・基本チェック）
  - python -m kabusys.validate_config [--strict]
- 発注エンジン（ExecutionEngine）
  - Signal の Pull 処理 / WebSocket Push ドレイン
  - kill.flag による安全停止、PID ファイル管理
- ブローカークライアント
  - KabuStationClient（kabu station REST / WebSocket 実装）
  - MockBrokerClient（paper_trading / 開発用のモック）
- 注文管理
  - OrderRecord（状態遷移ロジック）
  - OrderRepository（SQLite による永続化）
  - OrderManager（発注フロー、送信/同期/取消）
- リスク管理（RiskManager）
  - Gate1: シグナルレベル（余力・重複・ポジション上限）
  - Gate2: エグゼキューション（レート制限・サーキットブレーカー）
  - Gate3: メトリクス（ドローダウン監視）
- 起動時リコンシリエーション（Reconciler）
- データ系
  - calendar_management（営業日判定、J-Quants カレンダー更新ジョブ）
  - news_collector（RSS から記事収集・整形）
- 監視ループ起動スクリプト（run_monitoring）
- 実行エンジン起動スクリプト（run_execution）

---

## 動作要件

- Python 3.10 以上（型注釈に | を使っているため）
- 主な Python パッケージ（例）
  - duckdb
  - httpx
  - websocket-client
  - PyYAML（config/*.yaml の内容検証に必要。未インストール時は検証をスキップ）
  - defusedxml（RSS パーサ安全化）
- SQLite（標準ライブラリ）
- kabuステーションを使う場合は kabu station アプリが動作していること

※ 実際の要件はプロジェクトの requirements.txt を参照してください（本コード抜粋に requirements は含まれていません）。

---

## セットアップ手順（開発環境向け）

1. リポジトリをクローン / チェックアウト

2. 仮想環境を作成・有効化（例）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存パッケージをインストール（例）
   - pip install duckdb httpx websocket-client defusedxml PyYAML

4. データディレクトリを作成（必要に応じて）
   - mkdir -p data config

5. 環境設定（.env）の作成
   - python -m kabusys.config_setup
     - 対話式で .env を作成／更新します。
     - 重要な必須変数: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD
     - オプションやデフォルト値の説明がウィザードに表示されます。

6. 設定検証
   - python -m kabusys.validate_config
   - 問題があれば表示されます。--strict を付けると警告も失敗扱い（exit 1）になります。

---

## 環境変数（主な一覧）

- 必須
  - JQUANTS_REFRESH_TOKEN — J-Quants API 用リフレッシュトークン
  - KABU_API_PASSWORD — kabuステーション API パスワード

- 任意 / 推奨
  - KABUSYS_ENV — 実行環境: development | paper_trading | live（デフォルト: development）
  - DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH — SQLite 監視 DB（デフォルト: data/monitoring.db）
  - LOG_LEVEL — DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）
  - KABU_API_BASE_URL — kabu station API のベース URL
  - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID — 本番アラート用（任意）
  - KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリア (0/1、デフォルト 0)
  - PAPER_FILL_MODE — paper_trading 時のモック約定モード (instant|partial|never|reject)
  - PAPER_TRADING_SQLITE_PATH — paper_trading 用 SQLite（デフォルト data/paper_trading.db）
  - MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、デフォルト 60）

.env の自動読み込み順序（起動時）:
- OS 環境変数 ＞ .env.local ＞ .env
- 自動ロードを無効化するには: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

---

## 使い方（代表的コマンド）

- 環境設定ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 厳密モード（警告も FAIL）
    - python -m kabusys.validate_config --strict

- 実行エンジン起動（本番／ペーパートレードいずれもこのスクリプトで起動）
  - python -m kabusys.run_execution
  - ペーパートレード／開発モードでは MockBrokerClient が使われ、DB は data/paper_trading.db を使用します（Settings に準拠）。

- 監視ループ起動
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を調整できます（デフォルト 60 秒）。

- 開発用: モックブローカーを使った単体テスト (例)
  - ExecutionEngine は BrokerAPIProtocol を受け取るため、create_broker_api(mock=True) で MockBrokerClient を利用してテストできます。

---

## 運用・運転上の注意

- KABUSYS_ENV=live の場合は追加の安全チェックや LINE 通知設定の確認が行われます。live 設定は慎重に。
- kill.flag（設定: KILL_FLAG_PATH、デフォルト data/kill.flag）を置くとエンジン起動拒否や kill_switch による停止が行われます。
- stop_requested.flag（data/stop_requested.flag）を作ると polling ループなどが検知して安全に停止します（run_monitoring/run_execution の停止制御に使用）。
- PID ファイル（設定: PID_FILE_PATH、デフォルト data/execution.pid）は起動中プロセス管理に使われます。
- .env はセキュアに管理（絶対に Git にコミットしないこと）。

---

## ディレクトリ構成（主なファイル）

（リポジトリルート /src を想定）

- src/kabusys/
  - __init__.py
  - config.py                    — 環境変数 / Settings（.env 自動ロード機構含む）
  - config_setup.py              — 対話式 .env ウィザード
  - validate_config.py           — 起動前設定検証 CLI
  - run_execution.py             — ExecutionEngine 起動ラッパ
  - run_monitoring.py            — SystemMonitor ポーリング起動ラッパ
  - execution/
    - __init__.py
    - broker_api.py              — BrokerAPI の Protocol / 型 / ファクトリ
    - kabu_client.py             — kabu station 実装（HTTP + WebSocket）
    - mock_client.py             — Mock ブローカー（テスト用）
    - broker_factory.py          — Settings に基づくクライアント生成
    - order_record.py            — 注文状態モデル（状態遷移）
    - order_repository.py        — SQLite 永続化層（orders テーブル）
    - order_manager.py           — 発注フローの外向き API
    - execution_engine.py        — Signal Pull 型発注エンジン
    - reconciler.py              — 起動時リコンシリエーション
    - risk_manager.py            — 3 段階リスクガード
    - ...（その他関連モジュール）
  - data/
    - calendar_management.py     — マーケットカレンダー管理（DuckDB 使用）
    - news_collector.py          — RSS ニュース収集
    - jquants_client.py?         — J-Quants 連携（参照あり）
  - monitoring/
    - monitoring_db.py           — 監視 DB 初期化 / 書き込みユーティリティ（参照）
  - utils/
    - logging_setup.py           — ロギング初期化ユーティリティ（参照）
    - process_priority.py        — プロセス優先度設定ユーティリティ（参照）

- config/
  - system_config.yaml
  - data_config.yaml
  - strategy_config.yaml
  - risk_config.yaml
  - execution_config.yaml
  - monitoring_config.yaml
  （config/*.yaml は任意。validate_config は存在確認および PyYAML があればパース検証を行います）

- data/
  - （デフォルトの DB ファイルやフラグファイルを格納：data/kabusys.duckdb, data/monitoring.db, data/paper_trading.db, data/kill.flag, data/stop_requested.flag, data/execution.pid 等）

---

## 開発メモ / 補足

- MockBrokerClient は paper_trading やユニットテストでの挙動再現に有用（fill_mode により instant/partial/never/reject を選択可能）。
- 発注フローはクラッシュ安全性を意識して実装（OrderSent の永続化 → ブローカー呼び出し → broker_order_id 永続化 → OrderAccepted 遷移 等の 2 相永続化パターン）。
- Reconciler は起動時に OrderSent の注文を照合し、ポジション差分を検出してログに残します。
- calendar_management は DuckDB 上の market_calendar を参照し、未登録日は曜日フォールバックで判断します。
- news_collector は外部 RSS 取得時に SSRF / XML 脆弱性対策（defusedxml, URL 検証等）を組み込んでいます。

---

## トラブルシューティング

- PyYAML がないと config/*.yaml の内容検証がスキップされます。YAML の内容検証を行いたい場合は `pip install PyYAML` を実施してください。
- kabu station を利用する場合、API のベース URL と API パスワードが正しく設定されていることを確認してください。
- 起動中の PID ファイルや残留 kill.flag により起動が拒否されることがあります。状況に応じて確認・削除してください（ただし本番環境では慎重に）。

---

以上。必要であれば README にサンプル .env テンプレート、より詳細な起動フロー図、ユニットテスト／CI 手順を追加できます。どの情報を優先して追加しますか？