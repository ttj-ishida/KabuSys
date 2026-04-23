# KabuSys

日本株向け自動売買システム（小規模プロトタイプ）

このリポジトリは、シグナルに基づく発注フロー、発注状態管理、リスクガード、リコンシリエーション、監視ループ、カレンダー/ニュース収集等の主要コンポーネントを含む実装例です。kabuステーション（ローカルのブローカAPI）や J-Quants 等の外部サービスと連携する設計になっています。開発／検証用途として Mock ブローカーが組み込まれており、ペーパートレード環境で実行できます。

注意: 本 README はソース内のコードから機能・使い方をまとめたものです。実運用で使う場合は必ず十分な検証と安全対策を行ってください。

---

## 主な機能

- 環境設定ウィザード（.env の作成／更新）
  - `kabusys.config_setup` による対話式ウィザード
- 起動前設定検証ツール
  - `.env` と `config/*.yaml` を起動前にチェック（`kabusys.validate_config`）
- 実行エンジン（ExecutionEngine）
  - シグナルの読み取り → 発注（Signal Queue Pull 型）
  - 発注の二相永続化、クラッシュ耐性を考慮した状態管理
  - WebSocket push のドレイン（kabu push を監視）
  - Kill switch（異常時に全注文キャンセル）
- 注文管理
  - OrderRecord（状態遷移ロジック）
  - OrderRepository（SQLite 永続化）
  - OrderManager（OrderRecord + Repository + Broker API の橋渡し）
- ブローカークライアント
  - MockBrokerClient（テスト／開発用、fill_mode 等を指定可能）
  - KabuStationClient（kabuステーション REST / WebSocket 実装）
  - 抽象 Protocol とファクトリ関数 `create_broker_api`
- リスク管理（3 段階のガード）
  - Gate1: シグナルレベル（余力、重複、ポジション上限）
  - Gate2: エグゼキューションレベル（レート制限、サーキットブレーカー）
  - Gate3: メトリクスレベル（ドローダウン監視）
- リコンシリエーション（起動時自動復旧）
  - OrderSent の突合、ブローカとローカルのポジション差分検出
- 監視ループ（SystemMonitor を定期的に実行）
- データモジュール（マーケットカレンダー、ニュース収集）
  - DuckDB を利用する想定の処理群

---

## 必要な環境変数

validate_config / config.py の記述に基づき、主要な環境変数は次のとおりです。

必須（少なくともこれらは設定が必要）
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

任意（推奨設定や上書き用）
- KABUSYS_ENV (valid: development, paper_trading, live) — デフォルト `development`
- DUCKDB_PATH (デフォルト: `data/kabusys.duckdb`)
- SQLITE_PATH (デフォルト: `data/monitoring.db`)
- LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL, デフォルト: INFO)
- KABU_API_BASE_URL (例: `http://localhost:18080/kabusapi`)
- LINE_CHANNEL_ACCESS_TOKEN (任意)
- LINE_USER_ID (任意)
- KILL_FLAG_CLEAR_ON_START (0|1, デフォルト: 0)

Execution / Paper Trading 関連
- PAPER_FILL_MODE (instant | partial | never | reject)
- PAPER_TRADING_SQLITE_PATH (paper_trading 用 SQLite パス)

監視/プロセス
- PID_FILE_PATH
- KILL_FLAG_PATH
- MONITOR_POLL_INTERVAL（監視ポーリング間隔、秒）

詳細はコード中の docstring / validate_config.py / config_setup.py を参照してください。

---

## .env の自動読み込み

`kabusys.config` モジュールはプロジェクトルート（.git または pyproject.toml を基準）を探索し、以下の順序で環境変数を自動ロードします（OS 環境変数が優先されます）:

1. `.env`（override=False：未設定キーのみ設定）
2. `.env.local`（override=True：既存の .env 値を上書き可能。ただし OS 環境変数は保護される）

自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

.env の作成・更新はウィザードで簡単に行えます（下記参照）。

---

## セットアップ手順（開発用）

1. リポジトリをクローン
2. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）
3. 依存パッケージをインストール
   - 代表的な依存（実際の requirements.txt があればそれを使ってください）:
     - duckdb
     - httpx
     - websocket-client
     - defusedxml
     - PyYAML (validate_config の YAML 検証に必要)
   - 例:
     - pip install duckdb httpx websocket-client defusedxml pyyaml
4. .env を作成
   - 対話式ウィザード:
     - python -m kabusys.config_setup
   - またはエディタで手動作成（.env.example があれば参照）
5. 設定を検証
   - python -m kabusys.validate_config
   - 警告も失敗とする厳格モード:
     - python -m kabusys.validate_config --strict

注意: 実ブローカー（kabuステーション）と接続する場合はローカルで kabuステーション が起動していて適切な API パスワードなどが設定されている必要があります。テストや開発では `KABUSYS_ENV=paper_trading` または `development` を使用すると MockBrokerClient が使われます。

---

## 使い方（起動例）

- 環境ウィザード（.env を作成または更新）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 警告を FAIL にする: python -m kabusys.validate_config --strict

- 監視ループの起動
  - python -m kabusys.run_monitoring
  - ポーリング間隔を変更する: MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- 発注エンジンの起動（本番相当のセッション実行）
  - python -m kabusys.run_execution
  - 実行前に KABUSYS_ENV を適切に設定してください（paper_trading / development / live）
  - Paper/trading: MockBrokerClient が使用され、paper_trading DB を利用します。

- ライブラリとしての利用
  - アプリ内から Settings を利用:
    - from kabusys.config import settings
    - settings.jquants_refresh_token / settings.duckdb_path などでアクセス可能

---

## 主要設計ポイント（簡単な説明）

- OrderRecord は状態遷移ルールを持ち、InvalidStateTransitionError を投げることで不正遷移を防ぐ。
- OrderManager は DB と Broker API の間の調停を行い、二相永続化（OrderSent 前後の保存）を実現してクラッシュ後の復旧性を担保。
- ExecutionEngine はシグナル取得 → Gate1/2 のリスクチェック → 発注 → push/drain による同期を行う。
- RiskManager はトークンバケツによるレート制限・サーキットブレーカーやドローダウン監視を実装。
- Reconciler は起動時に OrderSent の不確定注文を突合し、ポジション差分を検出してログに記録する。
- MockBrokerClient を用いることで kabuステーション を起動しなくても発注周りのロジックを検証可能。

---

## 主要ファイル / ディレクトリ構成

（src/kabusys をルートとするパッケージ構成）

- src/kabusys/
  - __init__.py
  - config.py
    - Settings クラス、.env 自動読み込みロジック
  - config_setup.py
    - .env 対話式ウィザード
  - validate_config.py
    - 起動前チェック CLI（.env / config/*.yaml の検証）
  - run_monitoring.py
    - SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py
    - ExecutionEngine 起動スクリプト
  - execution/ (発注周りの主要モジュール)
    - __init__.py
    - broker_api.py
      - BrokerAPIProtocol、データモデル、例外、ファクトリ
    - broker_factory.py
      - Settings を元に BrokerClient を生成するファクトリ
    - kabu_client.py
      - KabuStationClient（HTTP + WebSocket 実装）
    - mock_client.py
      - MockBrokerClient（テスト用）
    - order_record.py
      - OrderState / OrderRecord（状態遷移ロジック）
    - order_repository.py
      - SQLite を用いた永続化層（orders テーブルの初期化含む）
    - order_manager.py
      - OrderManager（外向き API）
    - execution_engine.py
      - ExecutionEngine（セッション制御、シグナル処理、push ドレイン）
    - reconciler.py
      - Reconciler（起動時突合）
    - risk_manager.py
      - RiskManager（Gate1/2/3）
  - data/
    - calendar_management.py
      - 市場カレンダー管理（DuckDB + J-Quants 連携を想定）
    - news_collector.py
      - RSS ニュースの収集と前処理
    - jquants_client.py (参照あり: 外部 API クライアントを別モジュールで想定)
  - monitoring/
    - monitoring_db.py (使用箇所あり: 監視 DB の初期化・ロギング用)
  - utils/
    - logging_setup.py (ロギング初期化)
    - process_priority.py (プロセス優先度設定)
  - その他: scripts/generate_config.py（config/*.yaml の生成スクリプトが案内されている箇所あり）

（注）上記の一部ファイルは README 作成時点のサンプル実装・参照を示すためにリストアップしています。実際のファイルはリポジトリのルートを参照してください。

---

## 備考 / 運用上の注意

- KABUSYS_ENV=live の場合は本番運用を想定した追加チェックや警告が出ます。LINE 通知等の設定や KILL_FLAG_CLEAR_ON_START の値に注意してください。
- .env は機密情報を含むため Git にコミットしないでください（config_setup.py もその旨を案内します）。
- validate_config は PyYAML が無い場合、YAML のパース検証をスキップします。PyYAML を導入すると config/*.yaml の構文チェックが行われます。
- DB パス（DuckDB / SQLite）はデフォルトで `data/` 配下に置かれます。オペレーションスクリプトは存在しない親ディレクトリを自動的に作成する場合がありますが、想定外の権限や配置に注意してください。
- 実運用での安全性（注文停止 / キルスイッチ / リコンシリエーション）は厳重にテストしてください。

---

この README はリポジトリ内の docstring と実装を元に作成しています。詳細や最新の使い方はコード内の docstring / コメントを参照してください。必要であれば、サンプル .env テンプレートや起動例を追記します。