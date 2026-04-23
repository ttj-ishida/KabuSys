README.md

プロジェクト概要
- KabuSys は日本株向けの自動売買（シグナル駆動）フレームワークです。
- シグナルの読み取り、発注・状態管理、リスクガード、リコンシリエーション、監視（Monitoring）やデータ管理（カレンダー・ニュース収集）などを含むモジュール群で構成されています。
- 設計方針：ビジネスロジックと IO（DB/API/ネットワーク）を明確に分離し、モッククライアントでローカルテスト可能なことを重視しています。

主な特徴（機能一覧）
- 環境設定ウィザード（.env を対話式に生成・更新）：kabusys.config_setup
- 設定検証 CLI（.env と config/*.yaml を起動前にチェック）：kabusys.validate_config
- ExecutionEngine：シグナルをもとに発注を行うエンジン（WebSocket プッシュ処理・発注ドレイン等）
- OrderManager / OrderRecord / OrderRepository：注文状態管理（状態遷移の検証 + SQLite 永続化）
- Broker クライアント群：
  - MockBrokerClient（fill_mode を変えて挙動を切替可能）— テスト/ペーパートレード用
  - KabuStationClient（kabuステーション REST/WebSocket クライアント）— 実運用向け（未完成箇所あり）
- RiskManager：Gate1/2/3 の 3 段階リスクガード（余力・重複・ポジション上限、レート制限/サーキットブレーカー、ドローダウン監視）
- Reconciler：再起動後の OrderSent 注文のブローカー照合・ポジション差分検出
- Monitoring：システム/発注イベントのポーリング・ログ記録
- Data モジュール：マーケットカレンダー管理、ニュース収集（RSS → raw_news）など

セットアップ手順（ローカル開発向け）
1. リポジトリをクローン
   - git clone <repo-url>
   - cd <repo-root>

2. 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  # Windows: .venv\Scripts\activate

3. 依存パッケージをインストール
   - pip install -r requirements.txt
   - 主要依存（本コードベースで想定）: duckdb, httpx, websocket-client, PyYAML（任意: validate_config の YAML 検証用）, defusedxml

   ※ requirements.txt が存在しない場合は上記パッケージを個別にインストールしてください。

4. .env の用意
   - 対話式ウィザードを使う（推奨）
     - python -m kabusys.config_setup
   - 手動で作成する場合はルートに .env を配置（下の「重要な環境変数」参照）
   - 自動ロード: 起動時にプロジェクトルートの .env → .env.local の順で読み込まれます（OS 環境変数が優先）。
   - 自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

5. 設定検証（起動前に推奨）
   - python -m kabusys.validate_config
   - 警告も失敗扱いにするには --strict を付与

使い方（主要コマンド）
- 環境設定ウィザード
  - python -m kabusys.config_setup
  - .env を対話的に作成/更新します。シークレットはマスク表示されます。

- 設定検証
  - python -m kabusys.validate_config [--strict]
  - 必須環境変数や config/*.yaml、DBパスなどの事前チェックを行います。
  - PyYAML 未インストール時は YAML の内容検証はスキップされます（警告）。

- 監視ループ起動（SystemMonitor）
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可能（デフォルト 60）。
  - 監視は常に本番 sqlite_path を使用します（環境に関係なく）。

- エンジン起動（発注）
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、paper_trading 用 SQLite（デフォルト: data/paper_trading.db）に記録します。
  - 停止フラグ: data/stop_requested.flag / data/kill.flag（存在を検知して動作を停止・kill switch を発動）
  - PID ファイル: data/execution.pid（設定で変更可能）

重要な環境変数
- 必須
  - JQUANTS_REFRESH_TOKEN — J-Quants API のリフレッシュトークン
  - KABU_API_PASSWORD — kabuステーション API パスワード

- 任意 / デフォルトあり
  - KABUSYS_ENV — execution モード: development | paper_trading | live（デフォルト: development）
  - DUCKDB_PATH — DuckDB ファイル（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
  - LOG_LEVEL — DEBUG|INFO|WARNING|ERROR|CRITICAL（デフォルト: INFO）
  - KABU_API_BASE_URL — kabuステーションのベース URL（デフォルト: http://localhost:18080/kabusapi）
  - LINE_CHANNEL_ACCESS_TOKEN — LINE 通知トークン（本番では必須推奨）
  - LINE_USER_ID — LINE 通知先ユーザーID
  - KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリア（0 or 1、デフォルト 0）
  - PAPER_FILL_MODE — ペーパートレード時の fill 挙動（instant|partial|never|reject、デフォルト instant）
  - PAPER_TRADING_SQLITE_PATH — ペーパートレード専用 SQLite（デフォルト data/paper_trading.db）
  - MONITOR_POLL_INTERVAL — 監視ポーリング間隔（秒、デフォルト 60）

.sample .env（テンプレート）
- .env は決して Git にコミットしないこと。
- 例:
  JQUANTS_REFRESH_TOKEN=your_token_here
  KABU_API_PASSWORD=your_kabu_password_here
  KABUSYS_ENV=development
  DUCKDB_PATH=data/kabusys.duckdb
  SQLITE_PATH=data/monitoring.db
  LOG_LEVEL=INFO
  KILL_FLAG_CLEAR_ON_START=0

注意点（運用上の安全策）
- KABUSYS_ENV=live の場合は本番運用となり、LINE 通知等の設定漏れは致命的な見落としにつながるため validate_config の警告を厳格に扱う（--strict）ことを推奨します。
- kill.flag（KILL_FLAG_CLEAR_ON_START により動作が変わる）や stop_requested.flag を用いた外部停止機構があります。運用前に挙動を確認してください。
- .env やシークレット情報は絶対にバージョン管理に含めないでください。

ディレクトリ構成（主要ファイル）
- src/
  - kabusys/
    - __init__.py
    - config.py                       — 環境変数読み込み・Settings クラス
    - config_setup.py                 — .env 対話式ウィザード
    - validate_config.py              — 起動前設定検証 CLI
    - run_execution.py                — ExecutionEngine 起動スクリプト
    - run_monitoring.py               — SystemMonitor 起動スクリプト
    - execution/
      - __init__.py
      - broker_api.py                 — BrokerAPI の Protocol / データモデル / ファクトリ
      - broker_factory.py             — Settings に基づくブローカ生成
      - kabu_client.py                — kabu station REST/WebSocket 実装
      - mock_client.py                — テスト用 MockBrokerClient
      - execution_engine.py           — ExecutionEngine（シグナル処理 + push drain）
      - order_record.py               — OrderRecord（状態遷移ロジック）
      - order_repository.py           — SQLite 永続化レイヤ
      - order_manager.py              — 発注フロー（作成→送信→同期→取消）
      - reconciler.py                 — 再起動時の照合処理
      - risk_manager.py               — 3 段階リスクガード
    - data/
      - calendar_management.py        — JPX カレンダー管理
      - news_collector.py             — RSS ニュース収集（raw_news へ保存）
      - jquants_client.py             —（参照される想定の J-Quants クライアント）
    - monitoring/
      - monitoring_db.py              — 監視 DB 初期化・書き込みユーティリティ
      - system_monitor.py             — システム監視ロジック（別ファイル）
    - utils/
      - logging_setup.py              — ログ設定
      - process_priority.py           — プロセス優先度設定ユーティリティ
    - scripts/
      - generate_config.py            — config/*.yaml 生成スクリプト（参照）

（上記は主要なモジュールを抜粋した構成です。実際のリポジトリではさらにファイルが存在する場合があります。）

起動フローの概略
- 実行ファイル（run_execution / run_monitoring）は Settings を読み、DB コネクションを確立してから主要コンポーネント（OrderRepository、BrokerClient、RiskManager、ExecutionEngine 等）を組み立てます。
- ExecutionEngine はセッション単位（当日）でシグナル処理→push ドレイン→セッション終了という流れを持ち、停止フラグや kill_switch による安全停止を備えています。
- 発注は「DB に OrderSent を永続化 → broker API 呼び出し → broker_order_id を永続化 → OrderAccepted へ遷移」という二相永続化を意識した実装です。クラッシュ耐性を考慮しています。

開発／テストのヒント
- paper_trading（または development）で MockBrokerClient を使えば kabu ステーションを立てずにローカルで動作検証できます。
- MockBrokerClient は fill_mode を instant/partial/never/reject に切り替えて各種シナリオを再現できます。
- validate_config で警告・エラーを事前に確認してください。
- DB 初期化関数（init_orders_db / init_monitoring_db 等）を実行して必要テーブルを作成してから実行してください（run_* スクリプト内で呼ばれる場合があります）。

貢献・拡張
- Live broker 実装（KabuStationClient の熟成）、追加メトリクスの監視、config/*.yaml のスキーマ検証強化、Docker イメージ化などが想定される拡張点です。

お問い合わせ
- 問い合わせ先や開発者情報はリポジトリのメンテナーにお問い合わせください。

以上。必要に応じて README のサンプル .env、requirements.txt、または起動手順に実運用向けの詳細（systemd ユニット、監視ポリシー等）を追記します。どの情報を追加しますか？