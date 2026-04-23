# KabuSys

日本株自動売買システムの軽量実装（ライブラリ/実行スクリプト群）

このリポジトリは、シグナル駆動の発注エンジン、モニタリング、環境設定ウィザード、検証ツールなどを含む自動売買プラットフォームのコア部分を提供します。設計はモジュール化されており、実運用（live）・ペーパートレード（paper_trading）・開発（development）で挙動を切り替えられます。

注意: 本リポジトリは実際の資金を扱う設計になっているため、本番環境での使用時は適切なテスト・検証を行ってください。

---

目次
- 概要
- 主な機能
- セットアップ手順
- 使い方（CLI / 環境変数）
- ディレクトリ構成（主なファイル）
- 付記（運用上の注意）

---

プロジェクト概要
- KabuSys は日本株の自動売買向けに設計された小規模なフレームワークです。
- 発注ロジック、リスクガード、注文の永続化（SQLite）、発注／照合用クライアント抽象、監視用ループ、環境設定ウィザードなどを備えています。
- 実際のブローカー接続（kabuステーション）用クライアントと、テスト用の MockBrokerClient を切り替えて利用できます。
- 環境設定は .env ファイル（プロジェクトルート）から自動読み込みされ、CLI ウィザードで作成・更新できます。

---

機能一覧
- 環境設定ウィザード（python -m kabusys.config_setup）で .env を対話的に作成/更新
- 設定検証 CLI（python -m kabusys.validate_config）で必須環境変数や config/*.yaml の整合性を検査
- ExecutionEngine：シグナルを読み取って発注する発注エンジン（Signal Pull + WebSocket Push ドレイン）
- Broker API 層：Protocol 定義、KabuStationClient（kabuステーション連携）、MockBrokerClient（テスト用）
- OrderManager / OrderRecord / OrderRepository：注文状態遷移・DB 永続化・送信ロジック
- Reconciler：起動時の OrderSent 状態の自動照合・ポジション差分検出
- RiskManager：Gate1/2/3 による多段リスクガード（余力、重複、ポジション上限、レート制限、サーキットブレーカー、ドローダウン）
- Monitoring：SystemMonitor を定期ポーリングして監視情報を記録（run_monitoring）
- Data モジュールの一部：マーケットカレンダー管理、RSS ニュース収集（raw_news 保存ロジック 等）
- 設定値は Settings クラスで一元管理（環境変数ベース）

---

セットアップ手順（開発環境向け）
1. 必要条件
   - Python 3.9+（一部 typing 機能を利用）
   - 推奨ライブラリ（実行に必要な依存）:
     - duckdb
     - httpx
     - websocket-client
     - PyYAML（config YAML 検証用、必須ではない）
     - defusedxml
     - そのほか標準ライブラリ

2. 仮想環境作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (macOS / Linux)
   - .venv\Scripts\activate     (Windows)

3. パッケージインストール（プロジェクトの配布形態に合わせて）
   - 直接インストール例（requirements ファイルがある場合）:
     - pip install -r requirements.txt
   - 開発インストール（セットアップが整っている場合）:
     - pip install -e .

4. 追加パッケージ（YAML 解析や WebSocket 等）
   - pip install PyYAML httpx websocket-client duckdb defusedxml

5. データディレクトリの作成（必要に応じて）
   - mkdir -p data
   - .env（プロジェクトルート）を作成するか、下記ウィザードを実行

---

環境設定（.env）
- 推奨ワークフロー:
  1. python -m kabusys.config_setup を実行して対話式ウィザードで .env を作成
  2. python -m kabusys.validate_config で検証（--strict で警告も FAIL 扱い）

- 主要な環境変数（必須 / 任意・デフォルトを含む）
  - 必須:
    - JQUANTS_REFRESH_TOKEN — J-Quants API 用リフレッシュトークン（必須）
    - KABU_API_PASSWORD — kabuステーション API パスワード（必須）
  - 任意 / 推奨:
    - KABUSYS_ENV — 実行環境: development / paper_trading / live（デフォルト: development）
    - DUCKDB_PATH — DuckDB ファイル（デフォルト: data/kabusys.duckdb）
    - SQLITE_PATH — 監視 DB（デフォルト: data/monitoring.db）
    - LOG_LEVEL — DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）
    - KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
    - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID — 本番アラート用（任意）
    - KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動でクリアするか（0/1, デフォルト: 0）
    - PAPER_FILL_MODE — paper_trading 用の fill モード（instant/partial/never/reject、デフォルト: instant）
    - PAPER_TRADING_SQLITE_PATH — paper_trading 時の SQLite（デフォルト: data/paper_trading.db）

- 注意:
  - .env は絶対に Git にコミットしないでください（README・config_setup のヘッダにも注意書きがあります）。
  - validate_config は config/*.yaml の存在と PyYAML でのパースを確認します（PyYAML が無い場合は内容検証をスキップして警告）。

---

使い方（主要 CLI）
- 環境ウィザード（.env を作成 / 更新）
  - python -m kabusys.config_setup
    - --env-file で保存先を指定可能

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict  （警告も FAIL 扱いで exit code=1）

- 実行エンジン（発注）
  - python -m kabusys.run_execution
    - KABUSYS_ENV によって MockBrokerClient（paper_trading / development）か実装済みクライアントへ切替
    - 起動時に data/execution.pid（デフォルト）へ PID を書き込み、data/stop_requested.flag で外部停止制御

- 監視ループ
  - python -m kabusys.run_monitoring
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可能（デフォルト 60）
    - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path（SQLITE_PATH）を使用します

- その他（内部 API の利用）
  - ライブラリとして import して利用可能:
    - from kabusys.config import settings
    - from kabusys.execution import ExecutionEngine, BrokerClientFactory, RiskManager など

---

実行時の挙動メモ
- paper_trading / development 環境では MockBrokerClient が使われ、data/paper_trading.db に記録して本番 DB と分離します（paper_trading 用の SQLite を使用）。
- run_monitoring はどの環境でも本番の SQLite を参照する設計になっています（監視は環境に依存しない）。
- kill.flag（設定で指定した KILL_FLAG_PATH による）により発注ループを停止できます。KILL_FLAG_CLEAR_ON_START=1 を本番で設定すると起動時に既存の kill.flag をクリアしてしまうため安全設定には注意してください。
- Reconciler（起動時の同期）は OrderSent の不確定状態をブローカーに照合して復旧します。

---

ディレクトリ構成（主要ファイル）
（src/kabusys 以下の主なモジュール・スクリプト）

- src/
  - kabusys/
    - __init__.py                — パッケージ定義（__version__ 等）
    - config.py                  — 環境変数読み込み / Settings クラス
    - config_setup.py            — .env 対話式ウィザード
    - validate_config.py         — 起動前検証 CLI
    - run_execution.py           — ExecutionEngine 起動スクリプト
    - run_monitoring.py         — 監視ループ起動スクリプト
    - execution/
      - __init__.py
      - broker_api.py            — BrokerAPI のデータモデル・Protocol・ファクトリ
      - broker_factory.py        — Settings に基づくクライアント生成
      - kabu_client.py           — kabuステーション用クライアント（HTTP/WebSocket）
      - mock_client.py           — MockBrokerClient（テスト用）
      - order_record.py          — OrderRecord（状態遷移ロジック）
      - order_repository.py      — SQLite 永続化層（orders テーブル）
      - order_manager.py         — 外向き発注 API（Create / Send / Sync / Cancel）
      - execution_engine.py      — 発注エンジン（シグナル処理 + push ドレイン）
      - reconciler.py            — 起動時リコンシリエーション
      - risk_manager.py          — Gate1/2/3 リスクガード
    - monitoring/
      - monitoring_db.py         — 監視 DB 関連（初期化・ログ） ※参照される
      - system_monitor.py        — システム監視ロジック ※参照される
    - data/
      - calendar_management.py   — カレンダー管理（営業日判定 / 取得ジョブ）
      - news_collector.py        — RSS ニュース収集（raw_news 保存）
      - jquants_client.py        — J-Quants API ラッパー（参照あり）
    - utils/
      - logging_setup.py         — ロギング設定ユーティリティ
      - process_priority.py      — プロセス優先度設定ユーティリティ
    - その他:
      - config/*.yaml            — 各種設定 YAML（存在を validate_config が検査）

（注）一部説明に出てくるスクリプト（例: scripts/generate_config.py）はリポジトリ内にない場合があります。validate_config は該当ファイルがないと警告を出します。

---

運用上の注意
- .env の内容（特にパスワード / トークン類）は厳重に管理し、バージョン管理システムに含めないでください。
- KABUSYS_ENV=live では実際に発注が行われます。LINE などのアラート設定、KILL スイッチなどを必ず整えてください。
- validate_config を起動前に実行し、設定を確認してください（--strict を併用して警告を許容しない運用も可）。
- SQLite / DuckDB パスの親ディレクトリが存在しない場合、起動時に自動生成される場面がありますが、パーミッションやバックアップの観点から事前に準備しておくことを推奨します。
- ブローカークライアント（kabu_client）はネットワーク・API の状態に依存します。Mock を使った包括的なテストを先に行ってください。

---

貢献・拡張
- Live ブローカーの完全実装や追加の監視メトリクス、運用用ユーティリティ（デーモン制御、プロセスマネージャー統合）などを歓迎します。
- 新しい config/*.yaml を導入する場合は validate_config の _CONFIG_FILES を更新して検査対象に追加してください。

---

以上がプロジェクトの概要と基本的な使い方です。詳細は各モジュールの docstring（ソース内コメント）を参照してください。質問や README の補足が必要であれば教えてください。