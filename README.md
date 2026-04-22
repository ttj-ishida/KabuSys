# KabuSys

日本株自動売買システム（KabuSys）のコードベース README。

この README はリポジトリ内の実装に基づき、プロジェクト概要、機能、セットアップ／起動手順、使い方、ディレクトリ構成をまとめたものです。

---

## プロジェクト概要

KabuSys は日本株向けの自動売買フレームワークです。  
主な目的は「シグナルに基づく発注」「堅牢な発注ワークフロー」「起動時のリコンシリエーション」「監視・ログ収集」を提供することです。設計の特徴として、

- 発注フローは DB 永続化（SQLite）と状態遷移（OrderRecord）でクラッシュ耐性を確保
- 発注前の多段階リスクガード（Gate1/2/3）
- 本番／ペーパートレード／開発モードを切り替え可能（KABUSYS_ENV）
- Mock ブローカー（テスト用）と実ブローカー（kabuステーション）クライアントを分離
- 起動前に .env / config/*.yaml の設定検証ツールを提供

といった点を重視しています。

---

## 主な機能一覧

- 設定管理
  - .env ファイルの自動ロード（プロジェクトルートにある .env / .env.local）
  - 対話式設定ウィザード（python -m kabusys.config_setup）
  - 設定検証ツール（python -m kabusys.validate_config）
- 発注エンジン
  - ExecutionEngine: シグナルの読み込み→発注（Signal Queue Pull 型）
  - OrderManager / OrderRepository / OrderRecord による堅牢な発注フロー
  - Reconciler: 起動時の OrderSent 照合とポジション差分検出
- ブローカークライアント
  - MockBrokerClient（テスト／paper_trading / development 用）
  - KabuStationClient（kabuステーション REST API 実装）
  - ファクトリ経由で切替（create_broker_api / BrokerClientFactory）
- リスク管理
  - RiskManager: Gate1（シグナルレベル）/ Gate2（実行レベル：レート制限・サーキットブレーカー）/ Gate3（ドローダウン監視）
- 監視
  - SystemMonitor（モニタリングループ）
  - 監視用 DB（SQLite）へのイベント記録
- データユーティリティ
  - DuckDB を利用したシグナル・カレンダー参照（calendar_management 等）
  - ニュース収集ユーティリティ（RSS パーサなど）

---

## セットアップ手順（開発環境向け）

1. リポジトリをクローン
   - git clone ...（省略）

2. Python 仮想環境を作成・有効化
   - python -m venv .venv
   - Unix/macOS: source .venv/bin/activate
   - Windows: .venv\Scripts\activate

3. 必要なパッケージをインストール
   - リポジトリに requirements.txt がある想定で:
     - pip install -r requirements.txt
   - 主要な依存（実行に必要なもの）:
     - duckdb, httpx, websocket-client, defusedxml, PyYAML（設定検証用）、pytest（テスト時）、など
   - 最低限動かすだけなら PyYAML は任意（validate_config は YAML パースをスキップして警告出力します）。

4. .env の準備
   - 対話式ウィザードを使う（推奨）:
     - python -m kabusys.config_setup
   - 手動作成する場合はプロジェクトルートに `.env` を置く。必須環境変数:
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
   - その他のオプション変数:
     - KABUSYS_ENV（development | paper_trading | live）デフォルト: development
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（デフォルト: data/monitoring.db）
     - LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL）
     - KABU_API_BASE_URL, LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID, など

5. .env の自動ロードについて
   - デフォルトではプロジェクトルートの `.env`（および `.env.local`）を自動で読み込みます。
   - 自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## 使い方（主要スクリプト）

- 設定ウィザード（.env 作成／更新）
  - python -m kabusys.config_setup

- 設定検証（起動前チェック）
  - python -m kabusys.validate_config
  - 警告も失敗扱いにする（CI などで利用）:
    - python -m kabusys.validate_config --strict

- 実行エンジン（発注）
  - python -m kabusys.run_execution
  - 注意:
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient が使用され、paper_trading 用 SQLite（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）に記録されます。
    - PID / kill flag の制御: data/execution.pid, data/kill.flag を使用します。起動時に kill.flag が存在すると起動時の挙動は設定に依存します（KILL_FLAG_CLEAR_ON_START）。

- 監視ループ（SystemMonitor）
  - python -m kabusys.run_monitoring
  - ポーリング間隔を変更:
    - MONITOR_POLL_INTERVAL（秒、デフォルト 60）
  - 監視は環境に関係なく本番 sqlite_path を使用します（監視の一貫性のため）。

- 注意点（運用）
  - 本番モード（KABUSYS_ENV=live）では LINE 通知設定（LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID）や Kill Switch 設定を必ず確認してください。
  - run_execution は stop flag（data/stop_requested.flag）を検出すると安全に停止します。

---

## よく使う環境変数（例）

必須（起動・動作に必須）:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

主要（任意だが推奨）:
- KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視 DB（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — paper_trading 時の SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL — ログレベル（例: INFO）
- KABU_API_BASE_URL — kabuステーション API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID — 本番でのアラート送信に必要

実行制御:
- KILL_FLAG_CLEAR_ON_START (0|1) — 起動時に kill.flag を自動クリアするか（本番は 0 推奨）
- MONITOR_POLL_INTERVAL — 監視ポーリング間隔（秒）

---

## 設定ファイル（config/*.yaml）

validate_config で期待される YAML ファイル:
- config/system_config.yaml
- config/data_config.yaml
- config/strategy_config.yaml
- config/risk_config.yaml
- config/execution_config.yaml
- config/monitoring_config.yaml

これらはプロジェクトにより運用時に追加される想定です。PyYAML がインストールされていれば内容のパース検証が行われます。存在しない場合、validate_config は警告を出します（生成スクリプトがある場合は README 内の指示に従って生成してください）。validate_configの警告は --strict で失敗扱いにできます。

---

## ディレクトリ構成（主要ファイル）

以下はソースツリー（src/kabusys）の主要ファイル群です。実際のリポジトリに応じて若干の差分があるかもしれません。

- src/
  - kabusys/
    - __init__.py
    - config.py                        # 環境変数 / Settings
    - config_setup.py                  # 対話式 .env ウィザード
    - validate_config.py               # 起動前の設定検証 CLI
    - run_execution.py                 # ExecutionEngine 起動スクリプト
    - run_monitoring.py                # SystemMonitor 起動スクリプト
    - execution/
      - __init__.py
      - broker_api.py                  # Broker API の Protocol・データモデル・ファクトリ
      - broker_factory.py              # Settings に基づくクライアント生成
      - kabu_client.py                 # kabuステーションの実装（HTTP/WebSocket）
      - mock_client.py                 # Mock ブローカー（テスト用）
      - order_record.py                # 注文状態モデルと遷移ロジック
      - order_repository.py            # SQLite 永続化層
      - order_manager.py               # 発注の外向き API（状態管理 + broker 呼び出し）
      - execution_engine.py            # 発注エンジン（セッション制御）
      - reconciler.py                  # リコンシリエーション / 起動時同期
      - risk_manager.py                # Gate1/2/3 リスクガード
    - data/
      - calendar_management.py         # 市場カレンダー管理（DuckDB）
      - news_collector.py              # RSS ニュース収集
      - ...                            # その他データ関連
    - monitoring/
      - monitoring_db.py               # 監視用 DB 初期化 / 操作
      - system_monitor.py              # 監視ループ（run_monitoring から起動）
    - utils/
      - logging_setup.py               # ロギング設定ユーティリティ
      - process_priority.py            # プロセス優先度設定
    - strategy/                         # 戦略関連（存在する場合）
    - ...

補足:
- データベースファイルや pid / flag ファイルは `data/` ディレクトリ配下に置かれます（例: data/kabusys.duckdb, data/monitoring.db, data/execution.pid, data/kill.flag）。
- ExecutionEngine は DuckDB（分析用）と SQLite（監視／永続化用）を併用します。

---

## 運用上の注意点

- 本番モード（KABUSYS_ENV=live）は慎重に扱ってください。validate_config では live モードでの設定不備に対し警告が出ます（LINE 通知未設定など）。
- kill.flag（KILL_FLAG_PATH）は安全停止のために重要です。起動時に kill.flag が存在するとデフォルトで起動を拒否します。`KILL_FLAG_CLEAR_ON_START=1` を設定すると自動でクリアしますが、本番では推奨されません。
- 発注フローは二相永続化（OrderSent の前後で DB 更新）を行い、クラッシュ回復用に Reconciler による再同期を実装しています。DB スキーマを変更すると互換性に注意してください。
- Docker 化／systemd などで常駐させる場合はログ・PID・stop フラグの扱いを明確にしてください。

---

## トラブルシューティング

- validate_config が PyYAML の警告を出す:
  - PyYAML がインストールされていないため YAML のパース検証をスキップしています。pip install pyyaml で解消します。
- DuckDB/SQLite ファイルの親ディレクトリが存在しない:
  - 起動時に自動作成されることがありますが、権限などで失敗する場合は手動で `mkdir -p data` 等を作成してください。
- WebSocket 接続や API 認証エラー:
  - KabuStationClient は kabuステーションの稼働と API パスワード・トークンが必要です。テスト・開発は KABUSYS_ENV=paper_trading を利用し MockBrokerClient を使うことを推奨します。

---

## 最後に

この README はコードベースの主要な利用フローと運用上の注意をまとめたものです。実運用の前には必ず `python -m kabusys.config_setup` → `python -m kabusys.validate_config --strict` を実行して設定を確認してください。

さらに詳しい開発ドキュメントや API 仕様、運用手順はリポジトリ内の別ドキュメント（ある場合）を参照してください。ご不明点があれば実装箇所（上記の各モジュール）を確認し、必要ならば追加ドキュメント化を行ってください。