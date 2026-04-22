KabuSys — 日本株自動売買システム
==============================

概要
----
KabuSys は日本株向けの自動売買システム（プロトタイプ）です。  
主な設計方針は「分離された責務」「クラッシュ耐性」「発注安全ガード」で、以下の主要機能を備えます：

- シグナルに基づく発注エンジン（ExecutionEngine）
- ブローカー API 抽象化（kabu station / モック）
- 発注履歴の永続化（SQLite）
- 発注状態のリコンシリエーション（再起動後の復旧）
- 複数段階のリスクガード（Gate1/2/3）
- マーケットカレンダー管理・ニュース収集などのデータ基盤ユーティリティ
- 設定ウィザード（.env 作成）と起動前設定検証ツール

主な機能一覧
--------------
- 環境設定管理
  - .env / .env.local の自動ロード（必要時に無効化可）
  - 対話式ウィザードで .env を生成/更新（python -m kabusys.config_setup）
  - 起動前に設定を検証（python -m kabusys.validate_config）
- 発注実行
  - ExecutionEngine によるシグナル読み取り→発注フロー
  - ブローカー実装の差し替え（MockBrokerClient / KabuStationClient）
  - 発注状態管理（OrderRecord の状態遷移検証）
  - OrderRepository（SQLite）による堅牢な永続化
  - リコンシリエーション（Reconciler）によるクラッシュ復旧
- リスク管理
  - Gate1: シグナルレベル（余力・重複・ポジション上限）
  - Gate2: エグゼキューション（レート制限・サーキットブレーカー）
  - Gate3: 約定後メトリクス（ドローダウン監視）
- 監視プロセス
  - SystemMonitor イベントの定期記録（python -m kabusys.run_monitoring）
  - MONITOR_POLL_INTERVAL でポーリング間隔上書き可能
- データ関連ユーティリティ
  - DuckDB を使ったマーケットカレンダー管理（next_trading_day 等）
  - RSS ニュース収集（トラッキングパラメータ除去、SSRF対策等）

セットアップ手順
----------------
1. リポジトリを取得
   - この README があるプロジェクトルートを想定します。

2. 仮想環境（推奨）
   - python3 -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - 必要な外部ライブラリ（例、環境により）:
     - duckdb
     - httpx
     - websocket-client
     - defusedxml
     - PyYAML（config 検証時に YAML 構文チェックを行いたい場合）
   - 例:
     - pip install duckdb httpx websocket-client defusedxml pyyaml

   （プロジェクトに requirements.txt があればそれを使用してください）

4. .env を用意
   - 対話型ウィザードで作成するのが簡単です:
     - python -m kabusys.config_setup
   - または .env を手動作成（下記サンプル参照）。

5. 設定検証（必須）
   - python -m kabusys.validate_config
     - --strict を付けると警告も失敗扱いで exit(1) になります。

6. 実行
   - 実際の発注エンジン（Execution）:
     - python -m kabusys.run_execution
   - 監視プロセス（Monitoring）:
     - python -m kabusys.run_monitoring
   - いずれも .env の設定に従います（KABUSYS_ENV 等）。

使い方（主要コマンド）
--------------------
- 環境設定ウィザード（.env の作成／更新）
  - python -m kabusys.config_setup
  - オプション: --env-file /path/to/.env

- 設定検証（起動前チェック）
  - python -m kabusys.validate_config
  - オプション: --strict（警告も FAIL として扱う）

- 実行エンジン起動（発注）
  - python -m kabusys.run_execution
  - KABUSYS_ENV により挙動が変わる:
    - development: MockBrokerClient（テスト向け）
    - paper_trading: MockBrokerClient を使用し、paper_trading 用 sqlite（PAPER_TRADING_SQLITE_PATH）に記録
    - live: 本番（本実装では Live client は制約あり／設定要注意）

- 監視ループ起動
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング秒数を調整（デフォルト 60）。

主要環境変数（抜粋）
-------------------
必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

任意（設定が推奨されるものを含む）:
- KABUSYS_ENV  (development | paper_trading | live) — デフォルト: development
- DUCKDB_PATH (例: data/kabusys.duckdb)
- SQLITE_PATH (監視 DB、例: data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH (paper_trading 用 DB、デフォルト: data/paper_trading.db)
- LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL) — デフォルト: INFO
- KABU_API_BASE_URL (kabu station のベース URL)
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID（本番アラート用）
- KILL_FLAG_CLEAR_ON_START (0|1) — 起動時に kill.flag を自動クリアするか
- MONITOR_POLL_INTERVAL — 監視ポーリング間隔（秒）

.env 自動ロード挙動
------------------
- 自動ロード順:
  1. OS 環境変数（最優先）
  2. .env（プロジェクトルート）
  3. .env.local（.env を上書き）
- 自動ロードを無効化したい場合:
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると .env の自動読み込みをスキップします。

重要ファイル・フラグ
-------------------
- data/kill.flag (デフォルトパス) — kill switch（存在すると ExecutionEngine 起動を拒否または停止）
- data/stop_requested.flag — 監視／実行ループの外部停止フラグ
- data/execution.pid（PID ファイル。デフォルト path は設定可）

サンプル .env（ウィザードで生成される形式）
--------------------------------------------
（実際は .env をリポジトリにコミットしないこと）
JQUANTS_REFRESH_TOKEN=your_refresh_token_here
KABU_API_PASSWORD=your_kabu_api_password_here
KABU_API_BASE_URL=http://localhost:18080/kabusapi
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
KABUSYS_ENV=development
LOG_LEVEL=INFO
KILL_FLAG_CLEAR_ON_START=0
LINE_CHANNEL_ACCESS_TOKEN=
LINE_USER_ID=

ディレクトリ構成（主要ファイル説明）
----------------------------------
- src/kabusys/
  - __init__.py
  - config.py
    - .env/.env.local 自動ロードと Settings クラス（環境変数の一元管理）
  - config_setup.py
    - 対話式ウィザード（.env の生成/更新）
  - validate_config.py
    - 起動前チェック CLI（環境変数 / config/*.yaml / パスなどの検証）
  - run_execution.py
    - ExecutionEngine の起動スクリプト（pid / stop flag / DB 初期化 等を扱う）
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト
  - execution/
    - broker_api.py
      - BrokerAPIProtocol（インターフェース）、データモデル、例外、ファクトリ
    - kabu_client.py
      - kabu station REST API 実装（httpx, websocket）
    - mock_client.py
      - テスト用の MockBrokerClient（fill_mode 等を指定可）
    - broker_factory.py
      - Settings に基づきブローカークライアントを生成
    - order_record.py
      - 注文状態モデルと遷移（純粋ロジック）
    - order_repository.py
      - SQLite を使った永続化層
    - order_manager.py
      - 発注フローの外向け API（OrderRecord + OrderRepository + Broker）
    - execution_engine.py
      - 発注エンジン本体（signal の読み取り / push ハンドリング / kill switch）
    - reconciler.py
      - 起動時リコンシリエーション（OrderSent の照合、ポジション差分検出）
    - risk_manager.py
      - Gate1/2/3 のリスクチェック実装
  - data/
    - calendar_management.py
      - JPX カレンダー管理と営業日判定（DuckDB 使用）
    - news_collector.py
      - RSS からニュース収集（SSRF 対策・正規化・前処理）
  - monitoring/
    - monitoring_db.py (参照される監視DB 初期化やログ機能等がここにある想定)
  - utils/
    - logging_setup.py (ログ設定)
    - process_priority.py (プロセス優先度設定)

設計上の注意点と運用上のヒント
-----------------------------
- 本番運用時は KABUSYS_ENV=live の設定に注意（validate_config は live を警告ありで検出します）。
- kill.flag（KILL_FLAG_PATH）により安全に起動拒否/停止が可能です。KILL_FLAG_CLEAR_ON_START を 1 にすると起動時に自動で消去されますが、本番では 0 を推奨します。
- paper_trading モードは MockBrokerClient を使用し、本番 DB と分離された PAPER_TRADING_SQLITE_PATH を使用します。実運用での誤操作を防ぐため DB パス設定に注意してください。
- 発注処理はクラッシュ安全性を考慮して 2 相永続化（OrderSent の永続化 → broker 呼び出し → broker_order_id の保存 → OrderAccepted）を採用しています。OrderSent 状態の注文はリコンシリエーション対象です。

拡張・開発のヒント
------------------
- Live broker client の本格実装は KabuStationClient の完成度に依存します（現在の実装は httpx / websocket を使った同期クライアント）。
- YAML 設定ファイル（config/*.yaml）を使う設計が散見されます。PyYAML を入れると validate_config がファイルのパース検証を行います。
- DuckDB を使ったデータ処理・シグナル生成パイプラインを拡張して、バックテストやポートフォリオターゲット生成を行うと良いです。

問い合わせ・貢献
----------------
- バグや改善提案は Issue を作成してください。プルリク歓迎です。
- セキュリティ上の指摘がある場合は公開 Issue ではなく、管理者に直接連絡してください。

以上。必要であれば README に「インストール用 requirements.txt」や CI / systemd サービス定義、デプロイ手順などの追記も対応します。どの情報を追加しますか？