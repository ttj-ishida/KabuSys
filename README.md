# KabuSys

日本株自動売買システムの一部を実装した Python パッケージ群です。  
このリポジトリには環境設定（.env）管理、設定検証、監視プロセス、発注実行エンジン、ブローカー抽象化、マーケットカレンダー・ニュース収集などのコンポーネントが含まれます。

## プロジェクト概要
- 複数コンポーネント（ExecutionEngine / Monitoring / Data 等）から構成される自動売買基盤のコアロジック。
- kabuステーション（kabu station）API と連携するためのクライアント層（同期 HTTP / WebSocket）。
- 発注の永続化・状態遷移管理、リコンシリエーション（再起動後の整合処理）、リスクガード（3段階）を備える。
- 開発・テスト用に broker をモック化する仕組み（MockBrokerClient）を提供。paper_trading / development 環境で利用可能。
- .env 管理のウィザード（config_setup）と起動前検証ツール（validate_config）を備え、安全に運用できるように支援。

## 主な機能一覧
- 環境設定ウィザード（python -m kabusys.config_setup）
  - .env の対話式生成 / 更新
- 設定検証 CLI（python -m kabusys.validate_config）
  - .env と config/*.yaml の存在／基本整合性チェック。--strict オプションで警告も失敗扱いに。
- 監視ループ（python -m kabusys.run_monitoring）
  - SystemMonitor を定期ポーリングして監視データを記録（MONITOR_POLL_INTERVAL で間隔調整）。
- 発注実行（python -m kabusys.run_execution）
  - ExecutionEngine による signal → 発注フロー（Gate1/2/3 のリスクガード、WebSocket push ドレインなど）。
  - paper_trading 環境では MockBrokerClient を使用して本番 DB と分離。
- ブローカー抽象化
  - BrokerAPIProtocol に基づく実装（MockBrokerClient、KabuStationClient）。
- 発注永続化（SQLite）
  - orders テーブル定義、永続化・更新・検索 API（OrderRepository）。
- 注文状態管理（OrderRecord）
  - 状態遷移の検証・更新（OrderState、InvalidStateTransitionError）。
- リコンシリエーション（Reconciler）
  - OrderSent の不確定注文を broker と突合して復旧／同期。
- データモジュール
  - マーケットカレンダー管理（DuckDB ベース）とニュース収集（RSS、前処理、SSRF 防止等）。

## 必要条件
- Python 3.10 以上（PEP 604 の型 | を利用しているため）
- SQLite（標準ライブラリ）
- 推奨（機能に応じてインストール）:
  - duckdb
  - httpx
  - websocket-client
  - pyyaml（config/*.yaml の中身検証に使用）
  - defusedxml（ニュース収集の安全な XML パース）

例（仮の requirements）:
pip install duckdb httpx websocket-client pyyaml defusedxml

※ 実際の requirements.txt / pyproject.toml がある場合はそちらを使用してください。

## セットアップ手順（ローカル開発向け）
1. リポジトリをクローンして作業ディレクトリへ移動
   - 例: git clone ... && cd <repo>

2. 仮想環境を作成して有効化
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存パッケージをインストール
   - pip install -U pip
   - pip install duckdb httpx websocket-client pyyaml defusedxml

   （プロジェクトに requirements.txt / pyproject.toml がある場合はそちらを利用）

4. data ディレクトリを作成（以下は多くのコンポーネントが使用）
   - mkdir -p data

5. .env を作成
   - 対話式ウィザードを使う: python -m kabusys.config_setup
   - あるいは手動で .env を作成（下にテンプレート例を記載）

6. 設定検証（起動前チェック）
   - python -m kabusys.validate_config
   - 警告を FAIL としたい場合: python -m kabusys.validate_config --strict
   - exit code: 0 = OK（もしくは警告のみ）, 1 = エラー（--strict で警告も含める）

## 簡単な使い方 / 実行例
- 環境設定ウィザード（.env 作成）
  - python -m kabusys.config_setup
  - 完了後に .env がプロジェクトルートに保存されます（デフォルト）。

- 設定検証
  - python -m kabusys.validate_config
  - PyYAML が未インストールなら YAML パースはスキップ（警告）。

- 監視ループ起動
  - MONITOR_POLL_INTERVAL（秒）を環境変数で調整可能（デフォルト 60 秒）。
  - python -m kabusys.run_monitoring

- 実行エンジン起動（発注）
  - KABUSYS_ENV によって動作が変わる:
    - development / paper_trading: MockBrokerClient を利用（安全）
    - live: 本番ブローカークライアント（実装による）
  - python -m kabusys.run_execution

- ログレベル:
  - LOG_LEVEL 環境変数で設定（DEBUG / INFO / WARNING / ERROR / CRITICAL）

- .env 自動読み込み:
  - デフォルトで .env と .env.local を自動読み込み（OS 環境変数 > .env.local > .env の優先順位）
  - 自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定

## 主要環境変数（抜粋）
必須（起動・主要機能に必要）:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

任意 / 重要:
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- DUCKDB_PATH: DuckDB ファイル（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）
- KABU_API_BASE_URL: kabu station API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: 本番通知用（任意）
- KILL_FLAG_CLEAR_ON_START: 0 / 1（本番で 1 は危険）
- MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒）

注意: Settings._require を使う箇所は未設定だと ValueError を投げます。validate_config で事前にチェックしてください。

## .env テンプレート例
（config_setup によって自動生成されるフォーマットに準じます）
KABUSYS_ENV=development
JQUANTS_REFRESH_TOKEN=your_token_here
KABU_API_PASSWORD=your_password_here
KABU_API_BASE_URL=http://localhost:18080/kabusapi
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
LINE_CHANNEL_ACCESS_TOKEN=
LINE_USER_ID=
LOG_LEVEL=INFO
KILL_FLAG_CLEAR_ON_START=0

※ セキュリティ上 .env は絶対にリポジトリにコミットしないでください。

## ディレクトリ構成（主要ファイル）
以下は src/kabusys 以下の主要ファイル・モジュールの一覧と簡単な説明です。

- src/kabusys/
  - __init__.py — パッケージ定義（__version__ 等）
  - config.py — 環境変数の自動読み込みロジック、Settings クラス（アプリ設定）
  - config_setup.py — .env 対話式ウィザード CLI
  - validate_config.py — 起動前検証 CLI（.env / config/*.yaml の整合性チェック）
  - run_execution.py — ExecutionEngine 起動スクリプト（発注フロー）
  - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト
  - execution/
    - broker_api.py — BrokerAPIProtocol、データモデル、例外、create_broker_api
    - broker_factory.py — Settings に基づくブローカーファクトリ
    - kabu_client.py — kabu station の HTTP / WebSocket 実装（KabuStationClient）
    - mock_client.py — MockBrokerClient（開発・テスト用）
    - order_record.py — OrderRecord と状態遷移ロジック
    - order_repository.py — SQLite を使った永続化（orders テーブル）
    - order_manager.py — 発注フロー（create/send/sync/cancel）を実装
    - execution_engine.py — ExecutionEngine（シグナル処理、push ドレイン、kill switch）
    - reconciler.py — 再起動時のリコンシリエーション
    - risk_manager.py — Gate1/2/3 のリスクガード
  - data/
    - calendar_management.py — マーケットカレンダー管理（DuckDB）
    - news_collector.py — RSS 収集・正規化・保存（defusedxml 等使用）
    - jquants_client.py — （外部）J-Quants API との連携用クライアント（参照があるが実装ファイルが別途存在）
  - monitoring/
    - monitoring_db.py — 監視 DB 初期化とログ API（init_monitoring_db 等） ※参照箇所あり
    - system_monitor.py — SystemMonitor 本体（参照が run_monitoring にあり）
  - utils/
    - logging_setup.py — ログ設定ユーティリティ（setup_logging）
    - process_priority.py — プロセス優先度変更ユーティリティ（set_process_priority）

（プロジェクトに含まれるファイル群の一部を抜粋しています。実際のツリーはリポジトリ内を参照してください。）

## 運用上の注意 / ベストプラクティス
- 本番（KABUSYS_ENV=live）では LINE 通知等の監視設定を必ず確認してください。validate_config は live 時に追加チェックを行います。
- kill.flag により外部から安全にエンジン停止が可能です。KILL_FLAG_CLEAR_ON_START=1 は本番での自動クリアを避けるべきです。
- SQLite / DuckDB のパスは既定で data/ 配下を使います。data ディレクトリに適切な権限で作成してください。
- 発注処理は状態遷移と DB 永続化の順序に注意しており、部分的なクラッシュ耐性（OrderSent の永続化など）を考慮しています。DB スキーマを変更する場合は互換性を考慮してください。
- 本番ブローカークライアント（KabuStationClient）を有効にする場合は、kabu station が動作している環境とネットワーク設定を確認してください。

## 開発者向けメモ
- 自動 .env ロードはプロジェクトルート（.git もしくは pyproject.toml）を基準に行われます。配布後もカレントワーキングディレクトリに依存しない設計です。
- テスト・CI では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自動ロードを無効化し、環境を明示的に構築してください。
- ExecutionEngine / Monitoring はそれぞれ独立プロセスとして運用する想定です（systemd 等で管理するのが推奨）。

---

この README はコードベースの主要な使い方と構成をまとめたものです。より詳しい設計やデータプラットフォーム連携（J-Quants や market_calendar の仕様等）は各モジュールの docstring とプロジェクト内ドキュメント（DataPlatform.md 等）を参照してください。必要であれば README に追加したい項目（例: 実稼働手順、systemd ユニット例、CI 設定など）を教えてください。