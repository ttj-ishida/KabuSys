# KabuSys

日本株自動売買システムの軽量コアライブラリ（実行スクリプト・モックブローカー・監視・データユーティリティ等を含む）。

## プロジェクト概要

KabuSys は、kabuステーション（またはモックブローカー）を用いた日本株の自動売買エンジンのコアコンポーネント群です。主な目的は以下です。

- シグナルに基づく発注フロー（ExecutionEngine）
- 注文の状態管理（OrderRecord / OrderManager / OrderRepository）
- ブローカー抽象化（KabuStationClient / MockBrokerClient / BrokerAPIProtocol）
- リスクガード（3段階：Gate1/2/3）
- 起動時のリコンシリエーション（Reconciler）
- 監視プロセス（SystemMonitor を用いる run_monitoring）
- 環境設定ウィザード・検証（config_setup / validate_config）
- データユーティリティ（市場カレンダー、ニュース収集など）

このリポジトリは「実行ロジック」と「DB永続化層（SQLite / DuckDB を想定）」に分離された設計になっており、テストしやすく、モックを使ったローカル検証が可能です。

---

## 機能一覧

- .env 自動ロード（プロジェクトルートの `.env` / `.env.local`。環境変数を OS の値で保護）
- 対話式環境設定ウィザード（python -m kabusys.config_setup）
- 起動前設定検証 CLI（python -m kabusys.validate_config）
- 発注エンジン（ExecutionEngine）:
  - シグナルの読み取り（DuckDB）
  - Gate1/2/3 のリスクチェック
  - 発注、キャンセル、同期、リコンシリエーション
  - WebSocket push ドレイン（kabu push）対応
- ブローカークライアント:
  - 実運用（KabuStationClient） — REST + WebSocket
  - テスト・開発用モック（MockBrokerClient） — fill_mode を指定可能
- 注文永続化（SQLite）: orders テーブルと helper（init_orders_db, OrderRepository）
- リスク管理（Rate limit / Circuit breaker / Drawdown / Position limits）
- 監視プロセス（run_monitoring）: 定期ポーリング、監視 DB（SQLite）接続、DuckDB 接続
- データユーティリティ:
  - 市場カレンダー管理（jquants 経由の更新・営業日判定）
  - ニュース収集（RSS 取得、前処理、安全対策）

---

## セットアップ手順

※ 以下は本リポジトリの Python 実行に必要な最低限の手順です。実環境では追加の依存や環境整備が必要です。

1. Python を準備
   - 推奨: Python 3.10 以上（typing と一部の機能を使用）
2. 仮想環境を作成・有効化（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 必要パッケージをインストール
   - 以下は主要なランタイム依存（requirements.txt があればそちらを使ってください）
     - duckdb
     - httpx
     - websocket-client
     - defusedxml
     - PyYAML（config 検証で YAML のパースを行う場合に推奨）
   - 例:
     - pip install duckdb httpx websocket-client defusedxml PyYAML
4. プロジェクトルートに `.env` を作成
   - 対話式で作成する場合:
     - python -m kabusys.config_setup
   - 既存の `.env` がある場合は `.env.local` で上書き可能
   - 自動ロードはデフォルトで有効。無効化する場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
5. DB ディレクトリの準備（必要な場合）
   - デフォルトは `data/` 配下に DB / PID / flag を作成します。権限とディレクトリを確認してください。

---

## 重要な環境変数（主なもの）

以下は本システムで使用される主要な環境変数の一覧（config_setup でも同名で扱います）。

- 必須:
  - JQUANTS_REFRESH_TOKEN — J-Quants API 用トークン（必須）
  - KABU_API_PASSWORD — kabuステーション API パスワード（必須）
- 任意 / 推奨:
  - KABUSYS_ENV — 実行環境: development / paper_trading / live（デフォルト: development）
  - DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH — 監視 DB（デフォルト: data/monitoring.db）
  - LOG_LEVEL — DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）
  - KABU_API_BASE_URL — kabu station の base URL（デフォルト: http://localhost:18080/kabusapi）
  - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — 本番通知用（任意）
  - KILL_FLAG_CLEAR_ON_START — 起動時 kill.flag を自動クリアするフラグ（0/1、デフォルト 0）
  - PAPER_FILL_MODE — paper_trading 時のモック約定モード: instant / partial / never / reject（デフォルト: instant）
- 監視用:
  - MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、デフォルト 60）

設定不足・不正値は python -m kabusys.validate_config で起動前に検出できます。
--strict オプションで警告も失敗（exit code 1）として扱うことができます。

---

## 使い方（よく使うコマンド）

- 環境設定ウィザード（対話式 .env 作成）
  - python -m kabusys.config_setup
- 設定検証（.env / config/*.yaml の存在・簡易チェック）
  - python -m kabusys.validate_config
  - 警告を FAIL 扱いにする: python -m kabusys.validate_config --strict
- 実行エンジン起動（実際のトレード／または paper_trading）
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  - 実行前に .env で環境変数を整えてください
- 監視プロセス起動
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数で間隔を変更可能（秒）
- .env の自動ロード
  - 起動コードはプロジェクトルート（.git または pyproject.toml を基準）を探索し、`.env` / `.env.local` を自動ロードします
  - OS 環境変数より .env が上書きされないよう保護されています
  - 自動ロードを無効化するには: export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

停止方法（run_execution / run_monitoring）
- 両プロセスはプロジェクトルートの data/stop_requested.flag を検出すると安全にループを終了します（run_execution, run_monitoring 内で参照）。
- また ExecutionEngine は kill.flag（デフォルト data/kill.flag）を kill switch として扱います。kill.flag が存在すると起動を拒否するか、実行中は kill_switch を発動して全 active 注文をキャンセルします。

---

## ディレクトリ構成（主要ファイル）

以下は src/kabusys の主要ファイルと簡単な説明です。

- src/kabusys/__init__.py
  - パッケージメタ情報（__version__）
- src/kabusys/config.py
  - 環境変数の自動ロード、Settings クラス（アプリケーション設定）の定義
- src/kabusys/config_setup.py
  - 対話式 .env 作成ウィザード
- src/kabusys/validate_config.py
  - 起動前の設定検証 CLI（必須環境変数・YAML 等のチェック）
- src/kabusys/run_execution.py
  - ExecutionEngine の起動スクリプト（メイン実行点）
- src/kabusys/run_monitoring.py
  - 監視プロセス起動スクリプト（SystemMonitor ポーリング）
- src/kabusys/execution/
  - broker_api.py — Broker API の Protocol / データモデル / ファクトリ
  - kabu_client.py — kabuステーション REST/WebSocket クライアント
  - mock_client.py — テスト用 MockBrokerClient
  - broker_factory.py — Settings に基づくブローカークライアント生成
  - execution_engine.py — ExecutionEngine（シグナル処理・push ドレイン等）
  - order_record.py — 注文状態モデルと状態遷移ロジック
  - order_repository.py — SQLite による永続化層
  - order_manager.py — 注文ワークフロー（作成・送信・同期・キャンセル）
  - reconciler.py — 起動時リコンシリエーション（OrderSent の突合せ・ポジション差分検出）
  - risk_manager.py — 3段階リスクガード（Gate1/2/3）
- src/kabusys/data/
  - calendar_management.py — 市場カレンダー管理（J-Quants 経由で更新）
  - news_collector.py — RSS ニュース収集・前処理
  - （jquants_client 等の補助モジュールを想定）
- src/kabusys/monitoring/
  - monitoring_db.py（参照されている初期化処理等）
  - system_monitor.py（SystemMonitor 実装）
- src/kabusys/utils/
  - logging_setup.py — ログ初期化
  - process_priority.py — プロセス優先度設定（high 等）

（上記は主要モジュールの抜粋です。実際のファイルはリポジトリに従ってください）

---

## 実装上の注意点 / 運用メモ

- .env / .env.local の取り扱い
  - OS 環境変数の保護を行い、.env の自動上書きは protected set に従って制御されます
- DB
  - orders 周りは SQLite（監視 DB）で永続化。init_orders_db() でテーブルを冪等作成する設計になっています
  - 分析・シグナル用は DuckDB を使用（data/kabusys.duckdb）
- 本番モード（KABUSYS_ENV=live）
  - validate_config は live 指定時に追加の注意喚起を行います（LINE 通知設定の確認など）
  - Broker の live 実装（KabuStationClient）を使用する際は充分な事前検証を行ってください
- 発注の耐障害性
  - OrderManager は 2相永続化（OrderSent 保存 → ブローカー送信 → broker_order_id 保存 → OrderAccepted へ）を意識して設計されています。クラッシュ時の復旧は Reconciler が担います
- テスト・ローカル検証
  - paper_trading / development 環境では MockBrokerClient が使われ、PAPER_FILL_MODE により挙動を切替可能です（instant / partial / never / reject）

---

## よくあるコマンドまとめ

- ウィザードで .env を作る
  - python -m kabusys.config_setup
- 設定検証（警告を FAIL 扱い）
  - python -m kabusys.validate_config --strict
- 実エンジン（paper_trading）を起動
  - export KABUSYS_ENV=paper_trading
  - python -m kabusys.run_execution
- 監視プロセスの起動（デフォルト60秒間隔）
  - python -m kabusys.run_monitoring
  - export MONITOR_POLL_INTERVAL=30

---

README に書かれている内容はコードのコメント・ドキュメントを要約したものです。さらに詳しい API 仕様や運用手順は該当モジュールの docstring / コメントを参照してください。質問や特定の機能の詳細説明が必要であれば教えてください。