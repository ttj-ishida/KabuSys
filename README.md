# KabuSys

日本株自動売買システム（KabuSys）の軽量コア。  
このリポジトリは、実行環境の設定管理、発注エンジン、モニタリング、データ処理ユーティリティなどを含むモジュール群を提供します。

---

## 概要

KabuSys は以下の機能を備えた自動売買フレームワークのコア実装です（抜粋）:

- 環境変数 / .env 管理（自動読み込み / ウィザード）
- 起動前設定検証ツール（YAML / 環境変数のチェック）
- Signal Queue Pull 型の ExecutionEngine（発注、WebSocket push ドレイン、kill switch）
- Broker クライアントの抽象化（実装: MockBrokerClient / KabuStationClient）
- 注文状態マシン（OrderRecord）と永続化（SQLite）
- リスク管理（3段階ガード: Gate1/2/3、サーキットブレーカー、レート制限）
- リコンシリエーション（クラッシュ後の自動復旧）
- 監視プロセス（SystemMonitor 用のポーリングループ）
- データユーティリティ（マーケットカレンダー管理、ニュース収集など）

設計上、データベース（DuckDB、SQLite）や外部 API（kabu ステーション、J-Quants）との結合は明確に分離され、テスト用に MockBrokerClient を使えるようになっています。

---

## 主な機能一覧

- 環境設定ウィザード: python -m kabusys.config_setup
  - .env の作成・更新を対話式で支援
- 設定検証 CLI: python -m kabusys.validate_config [--strict]
  - 必須環境変数や config/*.yaml、パスの存在などを起動前にチェック
- 実行エンジン起動: python -m kabusys.run_execution
  - KABUSYS_ENV に応じて MockBroker を利用
  - PID / stop フラグ / kill flag を使った安全停止
- 監視ループ起動: python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL によるポーリング
- 発注レイヤー
  - OrderRequest / OrderResponse / OrderStatus 等のデータモデル
  - OrderManager: 発注フロー（create / send / sync / cancel）
  - OrderRepository: SQLite 永続化（orders テーブル、インデックス、ユニーク制約）
- リスク管理
  - RiskManager: check_signal, check_execution, check_metrics（ドローダウン）
  - トークンバケツによるレート制限、サーキットブレーカー実装
- Broker クライアント
  - MockBrokerClient（テスト用）
  - KabuStationClient（kabu ステーション REST / WebSocket 対応）
- データ
  - calendar_management: 営業日判定 / next_trading_day 等
  - news_collector: RSS 取得・前処理・保存ルール（SSRF 対策等）

---

## セットアップ手順

前提: Python 3.10 以上を推奨（typing, Path API を多用しているため）。

1. リポジトリをクローン
   - git clone <リポジトリURL>
2. 仮想環境作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）
3. 依存パッケージをインストール
   - 必要な主要パッケージ（プロジェクトに合わせて requirements.txt を参照してください）。代表的には:
     - duckdb
     - httpx
     - websocket-client
     - defusedxml
     - PyYAML（config の YAML 検証を有効化）
   - 例:
     - pip install duckdb httpx websocket-client defusedxml PyYAML
   - （パッケージはプロジェクトの要件に合わせて追加してください）
4. （任意）パッケージを開発モードでインストール
   - pip install -e .
5. 環境変数の初期設定
   - プロジェクトルートに .env を作成するか、./.env.local を用います。
   - 自動ロード: modules/config.py がプロジェクトルート（.git または pyproject.toml を基準）を検出すると自動で .env を読み込みます。自動ロードを無効にする場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

必須環境変数:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

任意の環境変数（よく使うものの例）:
- KABUSYS_ENV（development / paper_trading / live）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（デフォルト: data/monitoring.db）
- LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- KABU_API_BASE_URL
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID

---

## 使い方

1. .env を作成する（ウィザード推奨）
   - python -m kabusys.config_setup
     - 対話式に入力して .env を生成します（既存 .env を読み込んで更新可能）。
   - 生成後、設定を検証:
     - python -m kabusys.validate_config
     - 警告も失敗扱いにしたい場合:
       - python -m kabusys.validate_config --strict

2. 実行エンジンを起動
   - 本番・ペーパーの切り替え: KABUSYS_ENV を設定
     - KABUSYS_ENV=paper_trading を推奨してまずは動作確認（MockBroker を使用）
   - 実行:
     - python -m kabusys.run_execution
   - 停止:
     - 実行ディレクトリの data/stop_requested.flag を作成すると安全に停止します（stop flag）。
     - kill flag（data/kill.flag）は即時 kill switch を誘発します。KILL_FLAG_CLEAR_ON_START が 1 の場合は起動時に自動クリアされます（本番では 0 推奨）。

3. 監視プロセスを起動
   - python -m kabusys.run_monitoring
   - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL（秒）で上書き可（デフォルト 60 秒）。

4. ログ / PID / データファイル
   - PID: data/execution.pid（ExecutionEngine が起動時に書き込み）
   - DuckDB: デフォルト data/kabusys.duckdb（分析用）
   - SQLite（監視 DB）: data/monitoring.db
   - Paper trading 用 SQLite: data/paper_trading.db（KABUSYS_ENV=paper_trading 時は切替）

5. 開発用／テスト用
   - MockBrokerClient により、kabu ステーションを稼働させずに発注フロー・リコンシリエーションなどをテストできます。
   - create_broker_api(mock=True, fill_mode="instant"|"partial"|"never"|"reject") で動作モードを設定可能。

---

## 重要な設計上の注意点

- .env ファイルは絶対にリポジトリにコミットしないでください（config_setup にも明記）。
- Settings モジュールは起動時にプロジェクトルートを探索し .env/.env.local を自動読み込みします。OS 環境変数は .env より優先されます。
- KABUSYS_ENV=live は本番モードです。validate_config は live の場合に追加警告を出します（LINE 通知設定など）。
- ExecutionEngine は発注フローの堅牢性のために 2 相永続化を取り入れています（OrderSent 前後のクラッシュ回復を考慮）。
- OrderRepository の orders テーブルには「同一 signal_id の active 注文は 1 件のみ許可」する部分ユニークインデックスがあります（レース対策）。
- RiskManager は Gate1（余力・重複・ポジション上限）、Gate2（レート制限・サーキットブレーカー）、Gate3（ドローダウン）を別々に扱います。

---

## ディレクトリ構成（抜粋）

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数読み込み / Settings
  - config_setup.py           — .env 対話式ウィザード
  - validate_config.py        — 起動前設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — Monitoring 起動スクリプト
  - execution/
    - __init__.py
    - broker_api.py           — Broker API の Protocol / データモデル / ファクトリ
    - broker_factory.py       — Settings に応じたクライアント生成
    - kabu_client.py          — KabuStationClient（REST + WebSocket）
    - mock_client.py          — MockBrokerClient（テスト用）
    - order_record.py         — Order の状態マシン（pure business logic）
    - order_repository.py     — SQLite 永続化層
    - order_manager.py        — 発注フロー（create/send/sync/cancel）
    - execution_engine.py     — ExecutionEngine（シグナル処理 + push ドレイン）
    - reconciler.py           — 起動時のリコンシリエーション
    - risk_manager.py         — 3段階リスクガード
    - ...（他の実装ファイル）
  - monitoring/
    - monitoring_db.py        — 監視 DB 初期化 / ログ機能
    - system_monitor.py       — SystemMonitor 実装（省略ファイル参照）
  - data/
    - calendar_management.py  — 営業日ロジック / calendar 更新ジョブ
    - news_collector.py       — RSS ニュース収集
  - utils/
    - logging_setup.py        — ロギング設定ユーティリティ
    - process_priority.py     — プロセス優先度設定ユーティリティ
  - config/                   — YAML 設定ファイルを置く（system_config.yaml 等）

config/ に期待されるファイル（validate_config で確認）:
- system_config.yaml
- data_config.yaml
- strategy_config.yaml
- risk_config.yaml
- execution_config.yaml
- monitoring_config.yaml

---

## コマンドまとめ（例）

- 環境設定ウィザード:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict
- 実行エンジン（デフォルトは .env に従う）:
  - python -m kabusys.run_execution
- 監視ループ:
  - python -m kabusys.run_monitoring

---

## トラブルシューティング / 補足

- validate_config は PyYAML が無い場合、YAML の内容検証はスキップします（警告出力）。YAML 検証を有効にするには PyYAML をインストールしてください。
- .env の読み込み順:
  - OS 環境変数（最優先） > .env.local（上書き） > .env（未設定のみ）
- プロジェクトルートの検出は __file__ を起点に .git または pyproject.toml を探します。配布後や別ディレクトリから実行する場合は注意してください。
- 本番運用時は KABUSYS_ENV=live に設定しますが、LINE 通知設定や KILL_FLAG_CLEAR_ON_START の扱いに十分注意してください。

---

必要に応じて README を拡張して、設定ファイル（config/*.yaml）のフォーマットや DB スキーマ、開発用テスト手順（ユニット/統合テスト）、CI 設定などを追加できます。追加で欲しいセクションがあれば教えてください。