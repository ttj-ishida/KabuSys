KabuSys — 日本株自動売買システム（ドキュメント）
概要
- KabuSys は日本株向けの自動売買コンポーネント群（発注エンジン、リスクガード、モニタリング、データ処理など）を集めたライブラリ / 実行スクリプト群です。
- 設計方針の要点：
  - 発注のクラッシュ安全性（OrderSent の永続化、Reconciliation による復旧）
  - 3 段階のリスクガード（Gate1: シグナル、Gate2: 実行、Gate3: メトリクス）
  - 本番 (live) / ペーパートレード (paper_trading) / 開発 (development) を環境で切替
  - DB は DuckDB（シグナル・分析）と SQLite（監視・注文履歴）を利用

主な機能一覧
- 環境設定ウィザード: python -m kabusys.config_setup による .env の対話生成
- 設定検証: python -m kabusys.validate_config で .env と config/*.yaml の存在・基本整合性を検査
- 実行エンジン: python -m kabusys.run_execution — Signal Queue を処理して発注を行う
- 監視ループ: python -m kabusys.run_monitoring — SystemMonitor による定期ポーリング
- ブローカー抽象化:
  - MockBrokerClient: ペーパートレード / テスト用のモック（fill_mode 切替可）
  - KabuStationClient: kabuステーション REST API クライアント（実稼働用、httpx）
- 注文永続化: SQLite に orders テーブルを実装（OrderRepository / init_orders_db）
- リコンシリエーション: 起動時に OrderSent レコードをブローカーと突合して同期
- データモジュール:
  - calendar_management: 営業日判定・カレンダーの夜間更新ロジック
  - news_collector: RSS 収集・前処理・保存（SSRF / XML 攻撃対策を考慮）

必須 / 任意の環境変数
- 必須:
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- 任意（主なもの）:
  - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
  - DUCKDB_PATH — デフォルト: data/kabusys.duckdb
  - SQLITE_PATH — デフォルト: data/monitoring.db
  - LOG_LEVEL — デフォルト: INFO
  - KABU_API_BASE_URL — kabu station の URL（デフォルト: http://localhost:18080/kabusapi）
  - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — 本番通知用
- 注意:
  - 自動で .env / .env.local を読み込みます（プロジェクトルートは .git または pyproject.toml を基準に探索）。
  - 自動読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

セットアップ手順（ローカル開発向け）
1. Python バージョン
   - Python 3.9+（型アノテーションや pathlib を利用）。使用環境に合わせてください。

2. 必要パッケージ（例）
   - httpx, websocket-client, defusedxml, duckdb, PyYAML
   - インストール例:
     - pip install httpx websocket-client defusedxml duckdb PyYAML
     - またはプロジェクトに requirements.txt があれば: pip install -r requirements.txt

3. .env の作成
   - 対話式ウィザードで作成:
     - python -m kabusys.config_setup
   - ウィザード終了後、.env ファイルが生成されます（Git へはコミットしないこと）。

4. 設定検証
   - python -m kabusys.validate_config
   - 警告もエラー扱いにする場合:
     - python -m kabusys.validate_config --strict

5. DB 初期化（監視 / orders テーブル 等）
   - 実行スクリプトが起動時に必要なテーブルを作成する関数を呼びます（init_monitoring_db, init_orders_db）。
   - 例（監視を先に使う場合）:
     - python -c "from kabusys.run_monitoring import main; main()"
   - 注意: 具体的な DB 初期化スクリプトがプロジェクトにある場合はそちらを利用してください。

基本的な使い方
- .env を準備し、validate_config で確認した後にコンポーネントを起動します。

1) 環境ウィザード
- python -m kabusys.config_setup
  - 既存 .env を読み込んで更新、または新規生成します。

2) 設定検証
- python -m kabusys.validate_config
- --strict を付けると警告も失敗扱いになります。

3) 実行エンジン（デイリー発注）
- python -m kabusys.run_execution
  - KABUSYS_ENV が paper_trading または development の場合、MockBrokerClient が使用されます（settings.paper_fill_mode で挙動を制御）。
  - 実行前に kill.flag（data/kill.flag）が存在すると起動拒否されます（KILL_FLAG_CLEAR_ON_START=1 の場合は例外的にクリア可能）。

4) 監視ループ（SystemMonitor）
- python -m kabusys.run_monitoring
  - 環境にかかわらず本番の sqlite_path を使用して監視情報を記録します。
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を設定（秒、デフォルト: 60）。

5) Mock ブローカーの利用（テスト）
- KABUSYS_ENV=paper_trading または development を設定すると MockBrokerClient が生成されます。
- MockBrokerClient は fill_mode（instant|partial|never|reject）で約定挙動を切替可能。

運用に関する注意点
- 本番環境 (KABUSYS_ENV=live) を使用する際は LINE 通知等のアラート設定を確実に行ってください。validate_config は live での危険な設定（KILL_FLAG_CLEAR_ON_START=1 等）を警告します。
- 発注ロジックはクラッシュ安全性を考慮していますが、監視・ログ・バックアップを整備してください。
- PID ファイル / kill.flag の扱いに注意。stop フラグにより安全にプロセス停止できます。

ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py                 — パッケージ定義（__version__ 等）
  - config.py                   — 環境変数読み込み・Settings
  - config_setup.py             — .env 対話式ウィザード
  - validate_config.py          — 起動前設定検証 CLI
  - run_execution.py            — ExecutionEngine 起動スクリプト
  - run_monitoring.py           — SystemMonitor 起動スクリプト
  - execution/
    - __init__.py
    - broker_api.py             — Broker API Protocol / データモデル / ファクトリ
    - broker_factory.py         — Settings に基づくブローカー生成
    - kabu_client.py            — kabu station 実 API クライアント (httpx)
    - mock_client.py            — MockBrokerClient（テスト用）
    - order_record.py           — OrderRecord（状態遷移ロジック）
    - order_repository.py       — SQLite 永続化層（orders テーブル）
    - order_manager.py          — 注文管理（作成・送信・同期・キャンセル）
    - execution_engine.py       — ExecutionEngine（シグナル処理・push ドレイン）
    - reconciler.py             — リコンシリエーション（再起動復旧）
    - risk_manager.py           — 3 段階リスクガード
  - data/
    - calendar_management.py    — マーケットカレンダー管理
    - news_collector.py         — RSS ニュース収集前処理
    - (jquants_client は別モジュールとして想定)
  - monitoring/
    - monitoring_db.py          — 監視用 SQLite 初期化・ログ機能（利用される）
  - utils/
    - logging_setup.py          — ロギング設定ユーティリティ
    - process_priority.py       — プロセス優先度設定ユーティリティ

補足（開発者向け）
- Settings クラスにより環境変数の取得とバリデーションが集中管理されています。ユニットテストでは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を使って自動読み込みを無効化できます。
- OrderManager はクラッシュ安全性のため send_order 前に OrderSent を永続化し、broker 側で order_id が返ったらそれを DB に保存する 2 相永続化を採用しています。Reconciler がクラッシュ後の整合性回復を担います。
- calendar_management の営業日ロジックは DuckDB の market_calendar テーブルが存在しない場合に曜日ベースでフォールバックします。

その他
- 実稼働で kabuステーション を利用する場合、KabuStationClient の base_url と API パスワード設定を適切に行ってください。
- セキュリティ上 .env は絶対に Git にコミットしないでください（config_setup.py でも注意書きがあります）。

問い合わせ / 変更
- この README はコードベースの現状に基づく概要です。実運用前に必ずローカルで .env 作成 → validate_config → 小規模テスト（paper_trading）で動作確認してください。必要なら README に運用手順・稼働監視手順を追記してください。