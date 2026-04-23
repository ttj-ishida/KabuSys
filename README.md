# KabuSys

日本株自動売買システムのサブモジュール群。  
このリポジトリは、環境設定の読み書き・検証、ExecutionEngine（発注エンジン）、Monitoring（監視ループ）、およびデータ管理ユーティリティ群を含みます。

---

## プロジェクト概要

KabuSys は、kabuステーション（ローカルのブローカ REST API）や J-Quants 等を利用して発注・監視する日本株自動売買システムのコア実装を含むライブラリです。設計方針として、ビジネスロジックと永続化（SQLite）や分析用 DB（DuckDB）を明確に分離し、テスト用に Mock ブローカも提供します。

主な目的：
- 発注フロー（OrderState マシン）と永続化
- 発注前後の多段階リスクガード（Gate1/2/3）
- クラッシュ耐性のある発注シーケンスとリコンシリエーション
- 監視ループ（SystemMonitor）
- 環境設定ウィザード・自動読み込み・検証 CLI

---

## 機能一覧

- 環境設定管理
  - .env / .env.local の自動読み込み（プロジェクトルートを .git / pyproject.toml で検出）
  - 対話式ウィザードによる .env 作成（python -m kabusys.config_setup）
  - 設定検証 CLI（python -m kabusys.validate_config）:
    - 必須環境変数チェック
    - KABUSYS_ENV / LOG_LEVEL 等の妥当性チェック
    - DB パスの親ディレクトリ存在チェック
    - config/*.yaml の存在チェック（PyYAML があればパース検証）
    - KABUSYS_ENV=live 時の追加ガード
- 発注エンジン（ExecutionEngine）
  - Signal Queue ベースのバッチ発注（8:50-9:10）と WebSocket プッシュドレイン（9:10-15:30）
  - OrderRecord（状態遷移ロジック）、OrderRepository（SQLite 永続化）、OrderManager（外向き API）
  - Broker クライアント切替（Mock / 実装済みの KabuStationClient）
  - Reconciler：起動時に OrderSent 状態をブローカー照合して同期
  - RiskManager：Gate1（シグナルレベル） / Gate2（レート制限・サーキットブレーカー） / Gate3（ドローダウン監視）
- 監視ループ（run_monitoring）
  - SystemMonitor のポーリング（MONITOR_POLL_INTERVAL で間隔指定可）
  - monitoring 用 SQLite と DuckDB を使用
- データユーティリティ
  - マーケットカレンダー管理（DuckDB ベース）
  - ニュース収集モジュール（RSS 収集、正規化、SSRF 対策）

---

## セットアップ手順（開発用 / 実行前準備）

1. Python 仮想環境を作成・有効化
   - 例:
     - python -m venv .venv
     - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージをインストール  
   （プロジェクトに requirements.txt がある場合はそれを使用。ない場合は最低限以下をインストールしてください）
   - 推奨パッケージ例:
     - duckdb
     - httpx
     - websocket-client
     - PyYAML (設定検証で YAML パースを行う場合)
     - defusedxml (news_collector 用)
   - 例:
     - pip install duckdb httpx websocket-client PyYAML defusedxml

3. プロジェクトルートに .env を準備
   - 手動で作るかウィザードを使う:
     - python -m kabusys.config_setup
   - 自動ロード:
     - .env と .env.local はプロジェクトルート（.git または pyproject.toml を起点）から自動読み込みされます。
     - テスト等で自動ロードを無効にする場合:
       - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

4. data ディレクトリを作る（DB ファイルの親ディレクトリを作成）
   - mkdir -p data

5. （任意）config/*.yaml を配置
   - validate_config は config/system_config.yaml 等の存在をチェックします。
   - リポジトリ内に生成スクリプトがある場合はそれで生成してください（validate_config のメッセージは python scripts/generate_config.py を参照しています）。

---

## 環境変数（主要）

必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

任意（代表例）:
- KABUSYS_ENV — 実行環境（有効値: development, paper_trading, live）デフォルト: development
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視 DB（デフォルト: data/monitoring.db）
- LOG_LEVEL — DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）
- KABU_API_BASE_URL — kabu station base URL（デフォルト: http://localhost:18080/kabusapi）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — 本番通知用（live 時は未設定注意）
- KILL_FLAG_CLEAR_ON_START — 起動時 kill.flag を自動クリア(1)するか（デフォルト: 0）

Execution / Broker / Paper trading 関連:
- PAPER_FILL_MODE — paper_trading の fill 動作（instant / partial / never / reject）
- PAPER_TRADING_SQLITE_PATH — paper_trading 用 SQLite（デフォルト: data/paper_trading.db）

ログ・監視・PID:
- PID_FILE_PATH — pid ファイルパス（デフォルト: data/execution.pid）
- KILL_FLAG_PATH — kill.flag（デフォルト: data/kill.flag）
- MONITOR_POLL_INTERVAL — 監視ループ間隔（秒、デフォルト 60）

例: 最低限の .env（サンプル）
```
JQUANTS_REFRESH_TOKEN=your_token_here
KABU_API_PASSWORD=your_kabu_password
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
LOG_LEVEL=INFO
```

---

## 使い方（主要 CLI / スクリプト）

- 環境設定ウィザード（.env 作成／更新）
  - python -m kabusys.config_setup

- 設定検証（起動前チェック）
  - python -m kabusys.validate_config
  - 警告を FAIL 扱いにする（CI 等）:
    - python -m kabusys.validate_config --strict

- 実行エンジン起動（本番／ペーパートレード切替は KABUSYS_ENV で制御）
  - python -m kabusys.run_execution

- 監視ループ起動
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数で間隔変更可能（秒）

- 開発用モックブローカ有効化
  - KABUSYS_ENV が paper_trading または development の場合、MockBrokerClient が使用されます。

---

## 動作上の注意点 / 運用メモ

- KABUSYS_ENV=live の場合は本番用ガードが働きます。LINE 通知設定や KILL_FLAG_CLEAR_ON_START の設定を慎重に確認してください。
- kill.flag の存在は起動拒否・停止トリガとして利用されます。KILL_FLAG_CLEAR_ON_START=1 により自動クリアできますが、本番では推奨されません。
- ExecutionEngine は起動時に PID ファイルを生成します。正常終了時に削除されます。
- Order のクラッシュ耐性
  - send_order のフローは OrderSent を永続化してからブローカー呼び出しを行い、broker_order_id を先に永続化する等の 2 フェーズ永続化を行い、リコンシリエーションで整合を取れる設計です。
- DB 初期化
  - SQLite のテーブル（orders 等）や monitoring DB 初期化用関数が用意されています（init_orders_db / init_monitoring_db）。スクリプトや起動時に呼んでください。

---

## ディレクトリ構成（主要ファイルと説明）

- src/kabusys/
  - __init__.py
    - パッケージ定義（__version__ 等）
  - config.py
    - 環境変数読み込み・Settings クラス（自動 .env 読み込み含む）
  - config_setup.py
    - .env 対話式ウィザード（python -m kabusys.config_setup）
  - validate_config.py
    - 起動前設定検証 CLI（python -m kabusys.validate_config）
  - run_execution.py
    - ExecutionEngine 起動スクリプト（python -m kabusys.run_execution）
  - run_monitoring.py
    - SystemMonitor ポーリングループ起動（python -m kabusys.run_monitoring）
  - execution/
    - broker_api.py
      - BrokerAPIProtocol、データモデル、例外、create_broker_api ファクトリ
    - kabu_client.py
      - kabu station REST API クライアント実装（httpx）
    - mock_client.py
      - MockBrokerClient（テスト／開発用）
    - broker_factory.py
      - Settings に応じたブローカ生成（Mock / Live）
    - order_record.py
      - OrderState、OrderRecord（状態遷移ロジック）
    - order_repository.py
      - SQLite 永続化ロジック（orders テーブル）
    - order_manager.py
      - 外向き注文 API（create/send/sync/cancel）
    - execution_engine.py
      - ExecutionEngine（シグナル処理 + WebSocket ドレイン）
    - reconciler.py
      - 起動時リコンシリエーション（OrderSent の同期、ポジション差分検知）
    - risk_manager.py
      - Gate1/2/3 リスクガード
  - monitoring/
    - monitoring_db.py
      - 監視 DB 初期化とログ機能（SQLite）
    - system_monitor.py
      - SystemMonitor の実装（run_monitoring から使用）
  - data/
    - calendar_management.py
      - マーケットカレンダー管理（DuckDB 使用）
    - news_collector.py
      - RSS ニュース収集（正規化・SSRF 対策）
    - jquants_client.py
      - J-Quants API クライアント（calendar などの取得に利用）
  - utils/
    - logging_setup.py
      - ロギング初期化ユーティリティ
    - process_priority.py
      - プロセス優先度設定ユーティリティ

- data/
  - 実行時に生成される DB / PID / flag ファイルの配置先（デフォルト）
  - 例: data/kabusys.duckdb, data/monitoring.db, data/paper_trading.db, data/execution.pid, data/kill.flag

---

## よくある操作例

- .env をウィザードで作る:
  - python -m kabusys.config_setup

- 設定チェック（開発時に毎回実行推奨）:
  - python -m kabusys.validate_config

- Execution を起動（デフォルト development / mock）:
  - KABUSYS_ENV=development python -m kabusys.run_execution

- Monitoring 実行（デフォルト 60 秒ごと）:
  - python -m kabusys.run_monitoring

---

必要な追加情報（依存関係リストや DB 初期化スクリプトなど）があれば、README を拡張します。どの形式（簡易 / 詳細）でさらに書きたいか指定してください。