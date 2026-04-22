# KabuSys

日本株自動売買システム（KabuSys）のコードベース。  
この README はリポジトリ内の主要な CLI / モジュールの使い方、セットアップ手順、ディレクトリ構成を日本語でまとめたものです。

バージョン: 0.1.0

---

## 概要

KabuSys は、kabuステーション（ローカルの REST/WebSocket API）やテスト用のモックブローカーを用いて日本株の自動売買を行うためのシステムです。  
設計は以下のような責務分離を重視しています。

- 環境設定管理（.env 読み込み、Settings）
- 実行エンジン（ExecutionEngine）によるシグナル処理と発注
- 発注管理（OrderManager / OrderRepository / OrderRecord）
- ブローカー API 抽象化（BrokerAPIProtocol / KabuStationClient / MockBrokerClient）
- リスク管理（RiskManager: Gate1/2/3）
- リコンシリエーション（再起動時の同期）
- 監視ループ（SystemMonitor 用スクリプト）
- データ関連ユーティリティ（カレンダー、ニュース収集、DuckDB 連携等）
- 開発支援ツール（.env 作成ウィザード、設定検証 CLI）

---

## 主な機能一覧

- .env ウィザード（対話式）: `kabusys.config_setup`
  - .env の初期作成や更新を対話形式で実行
- 設定検証 CLI: `kabusys.validate_config`
  - .env と config/*.yaml の存在や基本的な妥当性を起動前にチェック
  - `--strict` オプションで警告も失敗扱いに
- 実行エンジン起動: `kabusys.run_execution`
  - Signal Queue を元に発注を行う ExecutionEngine を起動
  - KABUSYS_ENV に応じて MockBrokerClient（paper_trading/development）を利用
  - PID / stop flag / kill flag によるプロセス制御
- 監視ループ起動: `kabusys.run_monitoring`
  - SystemMonitor のポーリングループを起動（監視用 SQLite を使用）
  - 環境にかかわらず本番の sqlite_path を参照
- ブローカー抽象化
  - `BrokerAPIProtocol` により実装差し替え可能
  - 本番クライアント: `KabuStationClient`（httpx＋websocket）
  - テスト用モック: `MockBrokerClient`（fill_mode を指定可能）
- 注文管理の堅牢性
  - OrderRecord の状態遷移検証
  - OrderManager による二相保存やエラー取り扱い（OrderSentPending 等）
  - Reconciler による起動時の自動同期
- リスク管理（RiskManager）
  - Gate1: シグナルレベル（余力 / 重複 / ポジション上限）
  - Gate2: エグゼキューションレベル（トークンバケツによるレート制限、サーキットブレーカー）
  - Gate3: 約定後のドローダウン監視（kill_switch）

---

## 必要条件 / 推奨環境

- Python 3.10 以上（型アノテーション（| union）を使用しているため）
- OS 標準の sqlite3
- 推奨パッケージ（requirements の例）:
  - duckdb
  - httpx
  - websocket-client
  - defusedxml
  - PyYAML（config YAML のパース検証を行う場合）
- （任意）仮想環境の利用を推奨（venv / pyenv / poetry 等）

例（venv を使う場合）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install duckdb httpx websocket-client defusedxml PyYAML
```

プロジェクトの requirements がリポジトリにある場合はそれを利用してください:
```bash
pip install -r requirements.txt
```

---

## セットアップ手順

1. リポジトリをクローンして作業ディレクトリへ移動
2. 仮想環境を作成・有効化
3. 必要パッケージをインストール（上記参照）
4. 対話式ウィザードで .env を生成（推奨）
   ```bash
   python -m kabusys.config_setup
   ```
   - ウィザードは既存の .env を読み込み、入力を補完します
   - 作成された .env は Git にコミットしないでください（README とウィザード内でも注意あり）
5. 設定を検証
   ```bash
   python -m kabusys.validate_config
   # 警告も失敗扱いにする場合
   python -m kabusys.validate_config --strict
   ```
6. データディレクトリ（デフォルトは `data/`）や DB ファイルは起動時に自動作成される場合がありますが、必要に応じて事前に作成してください。

環境変数の自動ロード:
- デフォルトでプロジェクトルート（.git または pyproject.toml を基準）から `.env` を読み込みます（`.env.local` があれば上書き）。
- 自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します（テスト時に便利）。

必須環境変数（最低限）:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

その他の設定項目はウィザードや README を参照してください（例: KABUSYS_ENV, DUCKDB_PATH, SQLITE_PATH, LOG_LEVEL, KABU_API_BASE_URL, LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID）。

---

## 使い方（起動例）

- 設定ウィザード（.env 作成/更新）
  ```bash
  python -m kabusys.config_setup
  ```

- 設定検証
  ```bash
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- 実行エンジンを起動（発注ループ）
  ```bash
  python -m kabusys.run_execution
  ```
  挙動のポイント:
  - KABUSYS_ENV が `paper_trading` または `development` の場合は MockBrokerClient を使用（実売買は発生しない）。
  - `data/stop_requested.flag` の作成で安全に停止を依頼できます（stop フラグ検出でグレースフルに終了）。
  - PID ファイルはデフォルトで `data/execution.pid`（Settings で変更可能）に書き出されます。
  - `KILL_FLAG_CLEAR_ON_START=1` を設定すると起動時に既存の kill.flag を自動でクリアします（本番では 0 を推奨）。

- 監視ループを起動（SystemMonitor）
  ```bash
  python -m kabusys.run_monitoring
  ```
  オプション:
  - 環境変数 `MONITOR_POLL_INTERVAL`（秒）でポーリング間隔を変更可能（デフォルト 60 秒）。
  - 監視は環境に関わらず本番 sqlite_path を使用します。

- ローカル開発 / テスト
  - MockBrokerClient を利用し、fill_mode（instant/partial/never/reject）を `PAPER_FILL_MODE` 環境変数で切り替え可能。
  - ExecutionEngine は DuckDB からシグナルを読み取り発注を行います。テストでは直接メソッド呼び出しで動作を検証できます。

---

## 主要モジュール説明（抜粋）

- kabusys.config
  - Settings クラスを通じて環境変数から設定を取得。
  - .env 自動ロード（.env → .env.local）を行う（無効化可能）。
  - _require() により必須変数未設定時は明示的にエラーを出す。

- kabusys.config_setup
  - .env を対話的に生成・更新するウィザード。

- kabusys.validate_config
  - 起動前に .env と config/*.yaml の存在・簡易妥当性チェックを行う CLI。

- kabusys.run_execution
  - ExecutionEngine の起動スクリプト。PID / stop フラグを管理。

- kabusys.run_monitoring
  - SystemMonitor のポーリング起動スクリプト。

- kabusys.execution.*
  - broker_api.py: BrokerAPIProtocol、データモデル、例外、create_broker_api ファクトリ
  - kabu_client.py: kabuステーション（本番）用クライアント（httpx + websocket）
  - mock_client.py: テスト用 MockBrokerClient
  - order_record.py: 注文状態機械（OrderState）と OrderRecord（ビジネスロジックのみ）
  - order_repository.py: SQLite を用いた永続化層（orders テーブルの初期化関数含む）
  - order_manager.py: OrderRecord と OrderRepository を組み合わせた発注フロー管理（二相コミットの考慮など）
  - execution_engine.py: シグナルの取り込み、Gate1/2/3 のチェック、WebSocket のドレインなどセッション運用ロジック
  - reconciler.py: 起動時の自動リコンシリエーション（OrderSent の突合、ポジション差分検出）
  - risk_manager.py: Gate1/2/3 によるリスク検査（トークンバケツ、サーキットブレーカー、ドローダウン）

- kabusys.data.*
  - calendar_management.py: JPX カレンダーロジック（is_trading_day / next_trading_day 等）
  - news_collector.py: RSS からのニュース収集、正規化、保存（defusedxml 等を利用した安全設計）

- その他
  - utils: ロギング設定やプロセス優先度設定などユーティリティ（set_process_priority / setup_logging 等）

---

## .env / 設定についての注意点

- `.env` ファイルは絶対に公開リポジトリにコミットしないでください。
- 環境変数の優先順位:
  - OS 環境変数 > .env.local > .env
- 自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（ユニットテスト等で使用）。
- validate_config は必須変数未設定や明らかな設定ミスを起動前に検出します。デプロイ前に実行することを推奨します。

---

## よく使うコマンド例

- .env を作成 / 更新
  ```bash
  python -m kabusys.config_setup
  ```

- 設定チェック
  ```bash
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- エンジン起動（本番/ペーパートレード切り替えは KABUSYS_ENV）
  ```bash
  export KABUSYS_ENV=paper_trading
  python -m kabusys.run_execution
  ```

- 監視起動（ポーリング間隔を 30 秒に）
  ```bash
  export MONITOR_POLL_INTERVAL=30
  python -m kabusys.run_monitoring
  ```

- 安全停止（別プロセスから）
  ```bash
  touch data/stop_requested.flag
  ```

---

## ディレクトリ構成（抜粋）

以下はリポジトリ内の主要ファイル/ディレクトリの例（実際の構成はプロジェクトにより多少異なる可能性があります）。

- project-root/
  - pyproject.toml / setup.cfg / .git/
  - .env, .env.local (ユーザー環境)
  - data/                      # DB・PID・flag 等を配置（実行時に作成される）
    - monitoring.db
    - kabusys.duckdb
    - execution.pid
    - stop_requested.flag
    - kill.flag
  - config/
    - system_config.yaml
    - data_config.yaml
    - strategy_config.yaml
    - risk_config.yaml
    - execution_config.yaml
    - monitoring_config.yaml
  - src/
    - kabusys/
      - __init__.py
      - config.py
      - config_setup.py
      - validate_config.py
      - run_execution.py
      - run_monitoring.py
      - execution/
        - __init__.py
        - broker_api.py
        - kabu_client.py
        - mock_client.py
        - broker_factory.py
        - order_record.py
        - order_repository.py
        - order_manager.py
        - execution_engine.py
        - reconciler.py
        - risk_manager.py
      - data/
        - calendar_management.py
        - news_collector.py
        - jquants_client.py (データ取得用クライアント)
      - monitoring/
        - monitoring_db.py
        - system_monitor.py
      - utils/
        - logging_setup.py
        - process_priority.py
  - scripts/
    - generate_config.py (config/*.yaml を生成するためのスクリプト — validate_config のメッセージ参照)

---

## 開発上のヒント / 注意事項

- 本番ブローカークライアント（KabuStationClient）は、kabuステーションの実行環境（PC にインストールされたアプリ）を前提とします。本番運用前に充分な検証を行ってください。
- ExecutionEngine の発注フローは堅牢性を考慮して二相永続化の設計になっていますが、外部 API（kabu station）やネットワークの障害を考慮した運用設計が必要です。
- `KILL_FLAG_CLEAR_ON_START=1` は開発便利機能です。本番では既存の kill.flag による誤起動防止のため 0 を推奨します。
- config/*.yaml はシステムの振る舞い（戦略パラメータやモニタリング閾値）に重要な影響を与えます。validate_config によるチェックと、可能なら CI での静的検証を行ってください。
- DuckDB を分析用途に用いており、シグナルと portfolio_targets などを JOIN して発注対象を決定します。DuckDB のスキーマやテーブル生成は別スクリプト / マイグレーションで管理してください。

---

必要であれば、この README をベースに「環境変数一覧（デフォルト値／説明付き）」「config/*.yaml の各項目説明」「運用手順（デプロイ/監視/ログ管理）」などの詳細ドキュメントを追加します。どの章を優先して詳述しますか？