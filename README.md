# KabuSys

日本株向け自動売買フレームワーク（プロジェクトの一部）。  
このリポジトリには、設定管理、発注エンジン、モニタリング、データ処理などの基盤コンポーネントが含まれます。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は、kabuステーション等のブローカー API を使った日本株自動売買のための基盤ライブラリ / 実行スクリプトを提供します。  
主な設計方針は以下の通りです。

- 設定は .env ファイルまたは環境変数で指定（自動ロード機構あり）
- 発注フローは Signal Queue Pull 型（ExecutionEngine）
- 発注の永続化は SQLite（orders テーブル）
- モックブローカー（MockBrokerClient）でペーパートレードやテストが可能
- 起動前に設定検証ツールを提供（validate_config）
- 起動時にリコンシリエーションを行いクラッシュ復旧を支援

---

## 主な機能一覧

- 環境・設定管理
  - Settings クラス（環境変数経由で設定取得）
  - 自動 `.env` ロード（プロジェクトルートの `.env` / `.env.local`）
  - 設定ウィザード（python -m kabusys.config_setup）で .env を対話的に作成
- 設定検証
  - .env / config/*.yaml の存在や基本的妥当性をチェック（python -m kabusys.validate_config）
  - `--strict` オプションで警告も失敗扱い
- 発注実行系
  - ExecutionEngine：シグナルの読み込み・Gate ベースのリスク管理・発注・push ドレイン等
  - OrderManager / OrderRepository / OrderRecord：状態遷移と永続化ロジック
  - RiskManager：Gate1/2/3 によるリスクガード（余力、レート制限、ドローダウン等）
  - Reconciler：OrderSent 状態の照合、起動時の復旧処理
- ブローカークライアント
  - MockBrokerClient（テスト／ペーパートレード向け）
  - KabuStationClient（kabuステーション REST + WebSocket 実装）
  - create_broker_api() ファクトリで選択
- 監視
  - SystemMonitor をポーリングする run_monitoring スクリプト
  - MONITOR_POLL_INTERVAL によるポーリング間隔上書き可能
- データ
  - DuckDB ベースのマーケットカレンダー管理、ニュース収集など（data パッケージ）

---

## セットアップ手順

前提
- Python 3.10 以上（型ヒントや | 演算子、annotations フューチャーを使用）
- 必要なパッケージは機能に応じて導入（最低限は以下参照）

推奨インストール（プロジェクトルートで）:

1. 仮想環境作成（任意）
   - python -m venv venv
   - source venv/bin/activate もしくは venv\Scripts\activate

2. 必須依存のインストール（必要に応じて追加）
   - pip install duckdb httpx websocket-client defusedxml
   - PyYAML があると config/*.yaml のパース検証が有効化される: pip install pyyaml

3. （任意）パッケージとして開発インストール
   - pip install -e .

注意:
- プロジェクトは .env / .env.local を自動で読み込みます。自動ロードを無効にする場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## 必要な環境変数（主要）

必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

任意（デフォルト値ありまたはオプション）:
- KABUSYS_ENV (development | paper_trading | live) — default: development
- DUCKDB_PATH — default: data/kabusys.duckdb
- SQLITE_PATH — default: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH — ペーパートレード時の sqlite（default: data/paper_trading.db）
- LOG_LEVEL — DEBUG/INFO/WARNING/ERROR/CRITICAL
- KABU_API_BASE_URL — kabu station API の base URL
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID — 本番アラート用（任意）
- PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START など監視・制御用

環境変数の読み込み順:
OS 環境 > .env.local > .env

---

## 使い方（主なコマンド）

- 設定ウィザード（.env の作成／更新）
  - python -m kabusys.config_setup
  - 対話式に値を入力し .env を生成します。

- 設定検証（起動前チェック）
  - python -m kabusys.validate_config
  - 警告も失敗扱いにする: python -m kabusys.validate_config --strict

- 実行エンジンを起動（本番／ペーパートレードの実行）
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合はペーパートレード用 DB に記録し MockBroker を使用します。

- 監視ループを起動
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒単位で上書き（デフォルト 60）

実行時の挙動・ファイル:
- PID ファイル、kill.flag 等はデフォルトで data/ 配下に作成されます（パスは環境変数で変更可能）。
- run_execution は起動時に既存の stop flag を検査し、kill flag が存在する場合は起動を拒否します（KILL_FLAG_CLEAR_ON_START=1 でクリアして起動可能）。

---

## よく使うファイル / モジュールの説明

- kabusys/config.py
  - Settings クラス：環境変数から設定値を取得（必須変数は _require で検査）
  - .env 自動読み込みロジック（プロジェクトルートを .git や pyproject.toml で検出）

- kabusys/config_setup.py
  - 対話的に .env を作るウィザード

- kabusys/validate_config.py
  - 起動前に .env と config/*.yaml の存在や基本的な妥当性をチェック

- kabusys/run_execution.py
  - ExecutionEngine を組み立てて起動するスクリプト（発注エンジン）

- kabusys/run_monitoring.py
  - SystemMonitor のポーリングループを実行するスクリプト

- kabusys/execution/
  - broker_api.py: BrokerAPIProtocol とデータモデル、ファクトリ
  - kabu_client.py: kabuステーション向け REST + WebSocket 実装
  - mock_client.py: MockBrokerClient（テスト用）
  - order_record.py: OrderRecord と状態遷移ルール（純粋ビジネスロジック）
  - order_repository.py: SQLite 永続化（orders テーブル）
  - order_manager.py: 発注フロー API（create/send/sync/cancel）
  - execution_engine.py: セッション制御・シグナルループ・push ドレイン
  - reconciler.py: 起動時の OrderSent 照合・ポジション差分検出
  - risk_manager.py: Gate1/2/3 のリスクチェック

- kabusys/data/
  - calendar_management.py: マーケットカレンダー管理（DuckDB）
  - news_collector.py: RSS からニュース収集（安全対策付き）

- kabusys/monitoring/
  - monitoring_db, system_monitor 等（監視周りの実装）

- kabusys/utils/
  - logging_setup, process_priority などユーティリティ

---

## ディレクトリ構成（主要部分）

src/
  kabusys/
    __init__.py
    config.py
    config_setup.py
    validate_config.py
    run_execution.py
    run_monitoring.py
    execution/
      __init__.py
      broker_api.py
      broker_factory.py
      kabu_client.py
      mock_client.py
      order_record.py
      order_repository.py
      order_manager.py
      execution_engine.py
      reconciler.py
      risk_manager.py
      order_record.py
      order_repository.py
      ...（他実装ファイル）
    data/
      calendar_management.py
      news_collector.py
      jquants_client.py  (データ取得ラッパ等)
      ...
    monitoring/
      monitoring_db.py
      system_monitor.py
      ...
    utils/
      logging_setup.py
      process_priority.py
      ...
    strategy/  (戦略関連コードが入る想定)
    ...（そのほか）

注: 上記は主要ファイルの抜粋です。実際のツリーにはさらにモジュールや補助ファイルがあります。

---

## .env のサンプル（抜粋）

以下は config_setup で生成される .env の例（機密情報は実際の値に置換してください）。

JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here
KABU_API_PASSWORD=your_kabu_api_password_here
KABU_API_BASE_URL=http://localhost:18080/kabusapi
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
KABUSYS_ENV=development
LOG_LEVEL=INFO
KILL_FLAG_CLEAR_ON_START=0
LINE_CHANNEL_ACCESS_TOKEN=
LINE_USER_ID=

注意: .env は絶対にリポジトリにコミットしないでください。

---

## 運用上の注意

- KABUSYS_ENV=live を使用する場合は十分な注意が必要です（validate_config で警告が表示されます）。本番運用前に設定・通知周り（LINE）・kill switch の挙動を必ず確認してください。
- Orders の状態遷移や永続化は堅牢化を意識して設計されていますが、実環境では事前にペーパートレードで検証してください。
- run_execution / run_monitoring の実行ユーザが data/ への書き込み権限を持っていることを確認してください。
- .env 自動ロードを理解しておかないとテスト実行時に想定外の環境値が混入することがあります。必要なら KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して手動で環境を管理してください。

---

必要であれば、README に含める具体的な .env のテンプレート、docker-compose 例、または各モジュール（ExecutionEngine / RiskManager / Reconciler）の詳細ドキュメントを追加作成します。どの情報を優先して追加しますか？