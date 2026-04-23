# KabuSys

日本株自動売買システム（KabuSys）のリポジトリ向け README（日本語）

概要
---
KabuSys はローカルで動作する日本株向け自動売買プラットフォームの骨組みを提供するプロジェクトです。  
主に以下を含みます：

- Signal を読み込んで発注する ExecutionEngine（ペーパートレード / モック対応）
- 発注の状態管理・永続化（SQLite）
- リスクガード（3段階: Gate1/2/3、サーキットブレーカー、レート制限）
- リコンシリエーション（クラッシュ復旧）
- 監視デーモン（SystemMonitor）
- 市場カレンダー管理・ニュース収集などのデータ処理ユーティリティ
- .env ベースの設定管理と対話式ウィザード / 検証ツール

主な機能一覧
---
- 環境設定ウィザード (.env の作成/更新)
  - python -m kabusys.config_setup
- 設定検証ツール (.env と config/*.yaml の検証)
  - python -m kabusys.validate_config [--strict]
- 発注エンジン起動スクリプト（ExecutionEngine）
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading で MockBrokerClient を使用し paper_trading 用 SQLite に記録
- 監視ループ起動スクリプト（SystemMonitor）
  - python -m kabusys.run_monitoring
  - モニタリング DB は環境に関わらず本番 sqlite_path を使用
- Broker クライアント抽象化
  - 実運用向け KabuStationClient（kabu station REST API）
  - テスト向け MockBrokerClient（fill_mode を指定可能）
- 注文状態管理
  - OrderRecord（状態遷移ロジック）
  - OrderRepository（SQLite 永続化）
  - OrderManager（送信、同期、キャンセルなどの外向き API）
- リスク管理
  - RiskManager（Gate1: シグナルレベル、Gate2: 実行レベル、Gate3: 約定後監視）
- カレンダー / ニュース収集 / J-Quants 統合用ユーティリティ
- DuckDB を使った分析・シグナル取得

前提・依存
---
- Python 3.10 以上（typing の | などを使用）
- システムライブラリ（標準）
  - sqlite3
- 推奨 / 必要な外部パッケージ（例）
  - duckdb
  - httpx
  - websocket-client
  - defusedxml
  - PyYAML（config/*.yaml の内容検証に使用。無くても検証は軽度で継続）
- 実運用で kabu station を使う場合は kabuステーション® アプリの起動と API 設定が必要

セットアップ手順
---
1. リポジトリをクローン
   - git clone <repo-url>
   - cd <repo-root>

2. Python 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存パッケージをインストール
   - (推奨) requirements.txt が用意されている場合:
     - pip install -r requirements.txt
   - 例（最小）:
     - pip install duckdb httpx websocket-client defusedxml PyYAML

4. 環境設定ファイルの作成
   - 対話式ウィザードを使う:
     - python -m kabusys.config_setup --env-file .env
   - ウィザードは .env（または .env.local）を生成し、必須トークンを入力できます。
   - 自動ロード: デフォルトでプロジェクトルートの .env / .env.local を自動読み込みします。
     - 自動ロードを無効化する場合: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

5. 設定検証（推奨）
   - python -m kabusys.validate_config
   - 警告も失敗扱いにする場合:
     - python -m kabusys.validate_config --strict

6. DB やデータディレクトリの準備
   - デフォルトでは data/ 以下に DB ファイルや PID / フラグを作成します（自動作成されます）。
   - 監視・実行スクリプトを起動すると必要なテーブルは初期化されます。

使い方（主要コマンド）
---
- 環境設定ウィザード（.env の作成 / 更新）
  - python -m kabusys.config_setup
  - 対話式に各環境変数を設定できます（シークレットはマスク表示）。

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告も exit code 1（FAIL）扱いになります。

- 発注エンジン（Execution）
  - python -m kabusys.run_execution
  - 実行中に data/stop_requested.flag が作られると安全に停止します。
  - KABUSYS_ENV が paper_trading のとき、MockBrokerClient を使い paper_trading 用 SQLite（PAPER_TRADING_SQLITE_PATH）に記録します。

- 監視ループ（Monitoring）
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を変更できます（デフォルト 60）。
  - 停止は data/stop_requested.flag により検知します。

主な環境変数
---
必須
- JQUANTS_REFRESH_TOKEN — J-Quants API のリフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API パスワード

任意 / 推奨
- KABUSYS_ENV — 実行環境: development | paper_trading | live（デフォルト: development）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite path（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード専用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL — ログレベル: DEBUG|INFO|WARNING|ERROR|CRITICAL
- KABU_API_BASE_URL — kabu station API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID — LINE 通知用（本番でのアラート）

プロセス / 制御フラグ
- PID ファイル: デフォルト data/execution.pid（設定は PID_FILE_PATH）
- kill.flag: KILL_FLAG_PATH（デフォルト data/kill.flag） — kill switch 用
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアする（0/1、デフォルト 0）
- stop_requested.flag: data/stop_requested.flag（run_* スクリプトはこれを見て停止します）

安全設計上の注意
---
- KABUSYS_ENV=live 設定時は多数の警告が表示されるようになっています。実運用の前に全設定を確認してください。
- kill.flag（KILL_FLAG_PATH）と KILL_FLAG_CLEAR_ON_START の設定は運用上重要です。誤って 1 を本番で設定すると自動クリアされ安全性が損なわれる可能性があります。
- 発注ロジックはクラッシュ耐性を考慮した多段階永続化（OrderSent の永続化や broker_order_id の先行コミット）を行っていますが、実運用前に十分にテストしてください。

ディレクトリ構成（抜粋）
---
プロジェクトの主要ファイル/ディレクトリ構成（src 以下ベース）:

- config/                       # YAML 設定ファイル群（system_config.yaml など）
- data/                         # DB / PID / フラグを置くディレクトリ（実行時に作成）
- src/
  - kabusys/
    - __init__.py                # バージョン情報など
    - config.py                  # 環境変数読み込み / Settings クラス
    - config_setup.py            # 対話式 .env ウィザード
    - validate_config.py         # 起動前設定検証 CLI
    - run_execution.py           # ExecutionEngine 起動スクリプト
    - run_monitoring.py          # SystemMonitor ポーリング起動スクリプト
    - execution/
      - broker_api.py            # Broker API Protocol / データモデル / ファクトリ
      - kabu_client.py           # KabuStation REST API クライアント
      - mock_client.py           # テスト用 MockBrokerClient
      - broker_factory.py        # Settings を見てクライアント生成
      - order_record.py          # 注文状態マシン（純粋ロジック）
      - order_repository.py      # SQLite 永続化層
      - order_manager.py         # 注文の高レベル API（送信・同期・取消）
      - execution_engine.py      # ExecutionEngine（シグナル処理 + push ドレイン）
      - reconciler.py            # 起動時リコンシリエーション
      - risk_manager.py          # Gate1/2/3 のリスクガード
    - data/
      - calendar_management.py   # マーケットカレンダー管理 (DuckDB)
      - news_collector.py        # RSS 収集・前処理
      - ...                     # jquants クライアント等
    - monitoring/
      - monitoring_db.py         # 監視 DB 初期化・ログ書き込み
      - system_monitor.py        # システム監視ロジック
    - utils/
      - logging_setup.py         # ロギング設定ユーティリティ
      - process_priority.py      # プロセス優先度設定ユーティリティ
    - strategy/                   # 戦略関連（signals 生成等）
    - data/                       # データパイプライン用モジュール

（実際のツリーはリポジトリ内のファイルに従ってください。上は抜粋）

開発・テストのヒント
---
- ペーパートレード / 開発時は KABUSYS_ENV=paper_trading または development を使用し、MockBrokerClient（PAPER_FILL_MODE）でテストできます。
- MockBrokerClient は fill_mode を "instant" / "partial" / "never" / "reject" にして各種挙動（即時約定・部分約定・保留・拒否）を模擬できます。
- .env は絶対に Git にコミットしないでください（config_setup.py にも注意書きあり）。
- validate_config.py は PyYAML が未インストールのとき YAML のパース検証をスキップしますが、可能な限り PyYAML を入れておくことを推奨します。
- DB スキーマ初期化は run_execution/run_monitoring の起動時に行われますが、テスト用に sqlite3/duckdb の接続を直接叩いて init 関数を呼んでも構いません。

付記
---
- README はコードの主要設計意図と運用手順のサマリを提供することを目的としています。詳細は各モジュールの docstring（ソースコード内コメント）を参照してください。
- 実運用（実際の発注）前には十分な検証、運用手順（監視・アラート・ロールバック）を整備してください。

この README に含めてほしい追加情報や、サンプル .env/.yaml のテンプレート、起動スクリプトの systemd ユニット例などが必要であれば教えてください。