# KabuSys

日本株向けの自動売買システム（KabuSys）の簡易実装サンプルです。  
本リポジトリは、設定管理・検証、発注エンジン、ブローカークライアント（Mock / kabuステーション想定）、リスクガード、リコンシリエーション、監視ループ、データ処理（マーケットカレンダー・ニュース収集）などの主要コンポーネントを含みます。

## プロジェクト概要
- 目的: シグナルに基づく発注フローを実装し、発注安全性（余力チェック、レート制限、サーキットブレーカー、ドローダウン監視）を担保する。
- 設計方針:
  - ビジネスロジック（OrderRecord 等）と永続化（OrderRepository）を分離
  - 発注フローのクラッシュ耐性（OrderSent を先に永続化 → broker 呼び出し）を考慮
  - ペーパートレード用モッククライアントにより実稼働なしで開発/テスト可能
  - .env / config/*.yaml による設定管理と起動前検証ツールを提供

## 主な機能一覧
- 設定関連
  - .env 自動読み込み（プロジェクトルートの .env / .env.local、OS 環境変数優先）
  - 対話式設定ウィザード（python -m kabusys.config_setup）
  - 起動前設定検証 CLI（python -m kabusys.validate_config --strict）
- 発注関連
  - ExecutionEngine: シグナルプル & WebSocket push ドレインの発注ループ
  - OrderRecord / OrderState: 注文状態遷移の純粋ロジック
  - OrderRepository: SQLite による永続化（orders テーブル、インデックス、制約）
  - OrderManager: 発注作成 / 送信 / 同期 / キャンセルの外向き API
  - Reconciler: 再起動時の OrderSent 照合とポジション差分検出
  - RiskManager: Gate1〜3 の3段階リスクガード（余力・重複・ポジション上限、レート制限・CB、ドローダウン）
- ブローカー API 層
  - BrokerAPIProtocol（Protocol）
  - MockBrokerClient（ペーパートレード/開発向け）
  - KabuStationClient（kabuステーション REST / WebSocket クライアント、HTTP/websocket）
  - BrokerClientFactory: Settings に応じたクライアント生成（現状 paper/development → mock、live は未実装）
- 監視 / バックグラウンド
  - run_monitoring: SystemMonitor のポーリングループ（監視用 SQLite/DUCKDB 接続）
  - run_execution: ExecutionEngine 起動スクリプト
- データ処理
  - calendar_management: JPX カレンダー管理（DuckDB）、営業日判定 / 次営業日取得等
  - news_collector: RSS から記事収集（正規化・SSRF 対策・defusedxml 使用）
- ユーティリティ（ログ・プロセス優先度設定等：utils 下）

## 必要条件 / 推奨環境
- Python 3.9+（型注釈や一部の構文を想定）
- 推奨パッケージ（一部は使う機能による）
  - duckdb
  - httpx
  - websocket-client
  - pyyaml（config YAML 検証時）
  - defusedxml（ニュース収集）
- 標準ライブラリ：sqlite3 等

（pip でインストール）
pip install duckdb httpx websocket-client pyyaml defusedxml

## セットアップ手順
1. レポジトリをクローン / ソースを配置
2. Python 仮想環境を作成し依存をインストール
   - python -m venv .venv
   - source .venv/bin/activate
   - pip install -r requirements.txt もしくは上記必要パッケージを個別インストール
3. 対話式で .env を生成（推奨）
   - python -m kabusys.config_setup
   - ウィザードに従って入力し、.env を保存
4. 設定を検証
   - python -m kabusys.validate_config
   - 警告もエラーにしたい場合: python -m kabusys.validate_config --strict
5. DB 初期化（監視用 SQLite / orders テーブル等は起動時に自動で初期化される処理がある）
   - 実行スクリプト（run_execution / run_monitoring）が必要に応じてテーブルを初期化します

## 環境変数（主なもの）
- 必須
  - JQUANTS_REFRESH_TOKEN — J-Quants API リフレッシュトークン
  - KABU_API_PASSWORD — kabuステーション API パスワード
- 任意 / デフォルトあり
  - KABUSYS_ENV — environment (development | paper_trading | live)（既定: development）
  - DUCKDB_PATH — DuckDB ファイルパス（既定: data/kabusys.duckdb）
  - SQLITE_PATH — 監視 DB（既定: data/monitoring.db）
  - LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL、既定: INFO）
  - KABU_API_BASE_URL — kabu API base URL（既定: http://localhost:18080/kabusapi）
  - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID — 本番向けアラート（任意）
  - PAPER_FILL_MODE — paper_trading 時の振る舞い（instant|partial|never|reject、既定: instant）
  - PAPER_TRADING_SQLITE_PATH — paper_trading 用 SQLite（既定: data/paper_trading.db）
  - PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START — 起動監視／kill スイッチ関連
  - MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、既定: 60）

.env は config_setup のウィザードで生成できます。サンプル（.env の例）:
JQUANTS_REFRESH_TOKEN=your_token_here
KABU_API_PASSWORD=your_password_here
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
LOG_LEVEL=INFO
LINE_CHANNEL_ACCESS_TOKEN=
LINE_USER_ID=
KILL_FLAG_CLEAR_ON_START=0

> 注意: .env は機密情報を含むため絶対に Git にコミットしないでください。

## 使い方（主要 CLI / スクリプト）
- 設定ウィザード（.env 作成）
  - python -m kabusys.config_setup
- 設定検証
  - python -m kabusys.validate_config
  - 警告も失敗扱いにする: python -m kabusys.validate_config --strict
- 実行エンジン起動（本番/テストの ExecutionEngine）
  - python -m kabusys.run_execution
  - 実行前に .env を設定し、KABUSYS_ENV を paper_trading / development にすることで MockBroker が使われます
  - KABUSYS_ENV=live は現在ライブブローカークライアント（BrokerClientFactory の live）が未実装であるため使用不可（NotImplementedError）
- 監視ループ起動
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（秒）
- 開発・テスト
  - MockBrokerClient はペーパートレードや単体テストで利用可能（fill_mode の挙動を変更して挙動を検証）

## よくあるワークフロー
1. python -m kabusys.config_setup で .env 作成
2. python -m kabusys.validate_config で設定確認
3. python -m kabusys.run_monitoring をデーモン/別プロセスで起動（監視）
4. python -m kabusys.run_execution を起動してセッションを実行

停止方法:
- data/stop_requested.flag ファイルを作成すると run_monitoring と run_execution のループは検知して終了します。
- 実行時に kill.flag（KILL_FLAG_PATH）を置くと ExecutionEngine は起動を拒否、または kill_switch を発動します。

## ディレクトリ構成（抜粋）
以下は src/kabusys 以下の主要ファイル・モジュールの説明です。

- __init__.py
  - パッケージ定義（__version__ 等）
- config.py
  - Settings クラス: 環境変数読み取り、.env 自動ロード、必須値チェック
- config_setup.py
  - 対話式ウィザードで .env を作成 / 更新
- validate_config.py
  - .env および config/*.yaml の起動前検証 CLI
- run_execution.py
  - ExecutionEngine の起動スクリプト（プロセス優先度設定、DB 接続、スレッド管理）
- run_monitoring.py
  - SystemMonitor のポーリングループ起動スクリプト
- execution/
  - broker_api.py — BrokerAPIProtocol、データモデル、例外、ファクトリ
  - broker_factory.py — Settings に基づくクライアント生成
  - kabu_client.py — kabuステーション用 REST/WebSocket クライアント
  - mock_client.py — テスト用 MockBrokerClient
  - order_record.py — 注文状態マシン（OrderRecord, OrderState）
  - order_repository.py — SQLite 永続化層（orders テーブル定義、CRUD）
  - order_manager.py — 発注フローの上位 API（create/send/sync/cancel）
  - execution_engine.py — シグナル処理 / push ドレイン のメインロジック
  - reconciler.py — 再起動時の照合（OrderSent の同期、ポジション差分）
  - risk_manager.py — Gate1〜3 のリスクガード
- data/
  - calendar_management.py — JPX カレンダー管理（DuckDB 統合）
  - news_collector.py — RSS ニュース収集／正規化
- monitoring/
  - monitoring_db.py — 監視用 DB 初期化／ログ関数（参照あり）
- utils/
  - logging_setup.py — ログ設定ユーティリティ（参照あり）
  - process_priority.py — プロセス優先度設定ユーティリティ（参照あり）

（この README に含まれるのは主要ファイルの要約であり、各モジュールの詳細実装はソースを参照してください）

## 注意事項 / 現状の制約
- Live ブローカークライアント（KabuStationClient を本番で使用するフロー）は BrokerClientFactory 側で live を NotImplementedError にしており、安全上ペーパー/開発モードを想定した実装になっています。実稼働を行う場合は本番環境のクライアント実装・検証が必要です。
- .env に API トークンなどの機密情報が含まれるため、必ず Git 等へコミットしないでください。
- YAML 設定の内容検証は PyYAML がインストールされていると有効になります。未インストールの場合は警告が出て検証はスキップされます。

---

詳細な API やテーブル定義、内部設計（Reconciliation の挙動や Gate の細かな仕様など）はソースコードのドキュメンテーション文字列を参照してください。質問や補足があればお知らせください。