KabuSys
======

日本株向けの自動売買システムのコア実装（モジュール群）。  
このリポジトリは、設定管理・起動スクリプト・発注エンジン・モックブローカー・監視・データユーティリティ等を含む小規模な自動売買フレームワークを提供します。

主な目的
- ローカル環境やペーパートレード環境での安全な発注ワークフロー検証
- 起動時の設定検証・対話的な .env 作成ウィザード
- 発注の状態管理（Order State Machine）、リコンシリエーション、リスクガード
- kabuステーション（将来）やモックブローカー経由での発注（現状はモック実装が中心）
- DuckDB / SQLite を用いたデータ管理（シグナル / ポジション / 監視ログ等）

主な機能
- .env 対話式ウィザード（kabuys.config_setup.run_wizard）
- 起動前に .env / config/*.yaml を検証する CLI（kabusys.validate_config）
- ExecutionEngine：シグナルの読み取り → Gate チェック → 発注 → Push ドレインのセッション実行
- Order 管理：OrderRecord（状態遷移） / OrderRepository（SQLite 永続化） / OrderManager（API 呼び出しワークフロー）
- ブローカー抽象化：BrokerAPIProtocol とファクトリ（MockBrokerClient/KabuStationClient）
- RiskManager：Gate1/2/3 による多段ガード（余力、重複、ポジション上限、レート制限、サーキットブレーカー、ドローダウン）
- Reconciler：起動時リコンシリエーション（OrderSent の照合、ポジション差分検出）
- Monitoring：監視ループ（run_monitoring）で監視DBへログ記録
- データユーティリティ：マーケットカレンダー管理、RSS ニュース収集等（DuckDB ベース）

要件（推奨）
- Python 3.10 以上
- パッケージ（代表例、プロジェクトの requirements.txt に合わせてください）:
  - duckdb
  - httpx
  - websocket-client
  - defusedxml
  - PyYAML（config/*.yaml を厳密に検証する場合に必要）
- SQLite（標準ライブラリに含まれます）

セットアップ手順（開発環境向け）
1. レポジトリをクローン
   - git clone <repo-url>
2. 仮想環境の作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 依存関係をインストール
   - pip install duckdb httpx websocket-client defusedxml PyYAML
     （実運用で最小化したい場合は PyYAML をオプション扱いにできます）
4. .env を準備
   - 対話式ウィザードを使う（推奨）:
     - python -m kabusys.config_setup
   - もしくは .env を手動で作成（下記に必要な環境変数の一覧あり）
5. 設定検証
   - python -m kabusys.validate_config
   - 警告も失敗扱いにする場合:
     - python -m kabusys.validate_config --strict

主要な環境変数（重要度 / デフォルト）
- 必須
  - JQUANTS_REFRESH_TOKEN — J-Quants API 用リフレッシュトークン
  - KABU_API_PASSWORD — kabuステーション API 用パスワード
- 任意 / デフォルトあり
  - KABUSYS_ENV — 実行環境。development / paper_trading / live（デフォルト: development）
  - DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH — 監視 DB（デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH — ペーパートレーディング専用 SQLite（デフォルト: data/paper_trading.db）
  - LOG_LEVEL — DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）
  - KABU_API_BASE_URL — kabu station API のベース URL（デフォルト: http://localhost:18080/kabusapi）
  - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — 本番アラート用（任意）
  - KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（0/1、デフォルト 0）
  - MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、デフォルト 60）

推奨 .env 最小例
（必須項目のみ）
JQUANTS_REFRESH_TOKEN=your_jquants_token
KABU_API_PASSWORD=your_kabu_password
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
LOG_LEVEL=INFO

起動 / 実行方法
- 設定ウィザード（.env の作成）
  - python -m kabusys.config_setup
- 設定検証（起動前チェック）
  - python -m kabusys.validate_config
  - --strict をつけると警告も exit 1 とする
- 実行エンジン（発注セッション）
  - python -m kabusys.run_execution
  - KABUSYS_ENV が paper_trading の場合、MockBrokerClient を使用し paper_trading 用 SQLite に記録
- 監視ループ（SystemMonitor）
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更可能（デフォルト 60 秒）

挙動・運用に関する注記
- KABUSYS_ENV
  - development: 開発モード（発注はモック）
  - paper_trading: ペーパートレード（実際の発注は行わず、モックで動作を確認）
  - live: 本番（実装に応じてリアルブローカーを使う設計。現状は live 向けクライアントが未実装な箇所あり）
- ペーパートレードでは paper_sqlite_path に記録し、本番の監視 DB / 実DB と分離します。
- kill.flag / stop_requested.flag, PID ファイル等で外部制御可能：
  - 起動時に kill.flag が残っていると起動を拒否（KILL_FLAG_CLEAR_ON_START=1 の場合はクリアして起動）
  - 停止フラグ（data/stop_requested.flag）を置くことで監視/実行ループを終了させる
- Order の永続化は SQLite（orders テーブル）で行い、OrderSent などの不確定状態に対しては Reconciler による照合で回復を試みます
- WebSocket Push（kabu station）をサポートし、push による注文同期 / Gate 3（ドローダウン）チェックを行います

ディレクトリ構成（主要ファイルと概要）
- src/kabusys/
  - __init__.py — パッケージ定義（バージョン等）
  - config.py — 環境変数 / .env 自動読み込み、Settings クラス（全設定の取得ロジック）
  - config_setup.py — .env 対話式ウィザード（python -m kabusys.config_setup）
  - validate_config.py — 起動前検証 CLI（python -m kabusys.validate_config）
  - run_execution.py — ExecutionEngine を起動するスクリプト（python -m kabusys.run_execution）
  - run_monitoring.py — SystemMonitor をポーリング起動するスクリプト（python -m kabusys.run_monitoring）
  - data/
    - calendar_management.py — マーケットカレンダー管理（J-Quants 連携を想定）
    - news_collector.py — RSS ニュース収集ロジック
    - (その他データ関連ユーティリティ)
  - execution/
    - broker_api.py — BrokerAPIProtocol / データモデル / ファクトリ
    - broker_factory.py — Settings に基づくブローカーファクトリ
    - kabu_client.py — kabuステーション REST API クライアント（httpx）
    - mock_client.py — MockBrokerClient（テスト・ペーパートレード用）
    - execution_engine.py — ExecutionEngine（セッション管理、シグナル処理、push ドレイン）
    - order_record.py — OrderRecord（状態遷移の純粋ロジック）
    - order_repository.py — SQLite を用いた永続化層（orders テーブル定義 / CRUD）
    - order_manager.py — OrderManager（OrderRecord と Repository、Broker 呼び出しの調停）
    - reconciler.py — 起動時のリコンシリエーション（OrderSent の照合、ポジション差分検出）
    - risk_manager.py — RiskManager（Gate1/2/3 の実装）
    - (その他 execution 関連)
  - monitoring/
    - monitoring_db.py — 監視用 DB 初期化 / ログ関係（run_monitoring が利用）
    - system_monitor.py — システムメトリクス監視ロジック
  - utils/
    - logging_setup.py — ログ設定ユーティリティ
    - process_priority.py — プロセス優先度設定ユーティリティ

拡張ポイント / 注意事項
- live 環境での実ブローカークライアント（KabuStationClient の本番利用）は実装とテストが必要です。現行設計では paper_trading / development が安全に動くよう設計されています。
- config/*.yaml ファイル（system_config.yaml 等）は存在チェックと YAML パース検証を行います。PyYAML がない場合は内容検証をスキップします。
- .env はセキュリティ上 Git にコミットしないでください（config_setup.py でも注意書きを出しています）。
- 実運用前に validate_config を実行し、警告・エラーを解消してください。--strict を CI に組み込むとより安全です。

開発・デバッグのヒント
- ExecutionEngine.run_session() は時間帯ベースのループを持ちます。テストでは内部メソッド（_process_signals / _drain_push_queue）を直接呼び出すと高速に検証できます。
- MockBrokerClient は fill_mode（instant/partial/never/reject）を切り替え可能で、各種コードパスのテストに有用です。
- Reconciler は起動時に OrderSent の状態を broker 側と同期し、ポジション差分を検出します。クラッシュ復旧テストに有用です。

お問い合わせ / 貢献
- バグレポートや改善提案は Issue を立ててください。プルリクエスト歓迎です。
- 重大な設計変更（特に本番ブローカーインターフェース周り）は慎重に議論してください（安全優先）。

以上がこのリポジトリの概要と運用手順です。まずは python -m kabusys.config_setup で .env を作成し、python -m kabusys.validate_config で検証、その後 paper_trading モードで run_execution を実行して動作確認することを推奨します。