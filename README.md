# KabuSys

日本株自動売買基盤 (KabuSys) のリポジトリ。シグナル→発注→監視の主要コンポーネントを含む、ローカル開発・ペーパートレード・（将来的な）本番運用を想定した設計です。

## 概要

KabuSys は次の責務を持ちます：

- シグナルに基づく発注フロー（ExecutionEngine）
- 発注状態の永続化とリコンシリエーション（SQLite）
- ブローカー API 抽象化（Mock / KabuStation クライアント）
- システム監視（SystemMonitor）と監視用 DB（SQLite / DuckDB）
- データ処理（マーケットカレンダー・ニュース収集等）
- 環境設定ウィザード（.env 生成）および設定検証ツール

開発中は KABUSYS_ENV に応じて MockBrokerClient（ペーパートレード / 開発）を用いることで、kabuステーション実環境を用いずに動作検証できます。

## 主な機能一覧

- 環境設定ウィザード（対話式）: .env を生成 / 更新
- 設定検証 CLI: 必須環境変数・config/*.yaml・パス等の事前チェック
- ExecutionEngine: シグナル処理（発注）と push ドレイン、kill switch、リスクガード（Gate1/2/3）
- Order 管理: OrderRecord（状態遷移）、OrderRepository（SQLite 永続化）、OrderManager（発注フロー）
- ブローカー抽象化: BrokerAPIProtocol、MockBrokerClient、KabuStationClient（httpx / websocket）
- リコンシリエーション: 起動時の OrderSent 照合・ポジション差分検出
- 監視プロセス: SystemMonitor ポーリングループ（SQLite / DuckDB 使用）
- データ関連: JPX カレンダー管理、RSS ニュース収集等

## セットアップ手順

1. Python 仮想環境を作成・有効化
   - macOS / Linux:
     ```
     python -m venv .venv
     source .venv/bin/activate
     ```
   - Windows (PowerShell):
     ```
     python -m venv .venv
     .\.venv\Scripts\Activate.ps1
     ```

2. 依存パッケージをインストール
   - 最低限推奨パッケージ（プロジェクトの requirements.txt がある場合はそれを使用してください）:
     ```
     pip install duckdb httpx websocket-client defusedxml
     ```
   - YAML の内容検証を行いたい場合:
     ```
     pip install pyyaml
     ```

3. パッケージを開発モードでインストール（任意）
   ```
   pip install -e .
   ```
   （setup.py / pyproject.toml がある前提。なければ src を PYTHONPATH に追加してください）

4. プロジェクトルートに `data/` ディレクトリ（DB・pid・フラグ保存用）を作成
   ```
   mkdir -p data
   ```

## 初期設定（.env 作成）

対話式ウィザードで .env を生成できます:

```
python -m kabusys.config_setup
```

ウィザードは既存の .env を読み込み、シークレットはマスク表示されます。完了後は `.env` に書き込まれます。

自動環境読み込みの挙動：
- 起動時にプロジェクトルート（.git または pyproject.toml を基準）を探索して `.env`、`.env.local` を自動的に読み込みます。
- OS 環境変数が優先されます。
- 自動読み込みを無効化する場合:
  ```
  export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  ```

必須環境変数（最低限設定が必要）:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

よく使うオプション環境変数:
- KABUSYS_ENV (development | paper_trading | live)
- DUCKDB_PATH（例: data/kabusys.duckdb）
- SQLITE_PATH（例: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（paper_trading 用 SQLite）
- LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID（本番での通知）

## 設定検証

起動前に設定を検証する CLI を提供します。警告を FAIL 扱いにする strict モードあり。

```
python -m kabusys.validate_config
python -m kabusys.validate_config --strict
```

- PyYAML がインストールされていると config/*.yaml のパース検証が行われます。
- 必須 env が未設定の場合はエラー、プレースホルダ値や不整合は警告として報告されます。

## 実行方法

- 実エンジン（ExecutionEngine）起動:
  - ペーパートレード / 開発（Mock ブローカーを利用）:
    ```
    python -m kabusys.run_execution
    ```
  - KABUSYS_ENV によって paper_trading/dev/live の動作が切り替わります。paper_trading は専用 SQLite（PAPER_TRADING_SQLITE_PATH、デフォルト data/paper_trading.db）を使用します。

- 監視プロセス起動（SystemMonitor ポーリング）:
  ```
  python -m kabusys.run_monitoring
  ```
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を調整（デフォルト 60 秒）。
  - 監視は環境にかかわらず本番 sqlite_path を使用します（監視用 DB の分離に注意）。

運用上のフラグやファイル:
- 停止フラグ（監視・実行スクリプトは data/stop_requested.flag をチェック）
- kill フラグ（実行エンジン内で検査する kill.flag、 KILL_FLAG_PATH で変更可）
- PID ファイル（デフォルト data/execution.pid、設定で変更可）

## 開発者向けメモ（主要モジュール）

- kabusys/config.py
  - .env 読み込みロジック、Settings クラス（環境変数から値を取得）
- kabusys/config_setup.py
  - 対話式 .env ウィザード
- kabusys/validate_config.py
  - 起動前検証ツール（必須 env, config ファイル, パス等）
- kabusys/run_execution.py
  - ExecutionEngine の起動スクリプト（kill flag / PID 管理 / DB 接続）
- kabusys/run_monitoring.py
  - SystemMonitor ポーリングループ起動スクリプト
- kabusys/execution/
  - broker_api.py: BrokerAPIProtocol、データモデル、ファクトリ
  - kabu_client.py: kabuステーション REST/WebSocket 実装（httpx + websocket-client）
  - mock_client.py: テスト用 MockBrokerClient（paper_trading 用）
  - order_record.py / order_repository.py / order_manager.py: 注文ライフサイクル管理
  - execution_engine.py: 発注フロー（シグナル処理／push ドレイン／kill switch）
  - reconciler.py: 起動時リコンシリエーション
  - risk_manager.py: Gate1/2/3 のリスク管理
  - broker_factory.py: Settings に基づく Broker クライアント生成
- kabusys/data/
  - calendar_management.py: マーケットカレンダー処理（DuckDB）
  - news_collector.py: RSS 収集・正規化（defusedxml 使用）
  - jquants_client (外部参照): J-Quants からデータ取得用クライアント（実装されている想定）

## ディレクトリ構成（主要ファイル抜粋）

（プロジェクトルート / src 以下を想定）

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
      - broker_factory.py
      - kabu_client.py
      - mock_client.py
      - order_record.py
      - order_repository.py
      - order_manager.py
      - execution_engine.py
      - reconciler.py
      - risk_manager.py
    - monitoring/
      - monitoring_db.py (監視 DB 操作)
      - system_monitor.py (ポーリング・チェック実装)
    - data/
      - calendar_management.py
      - news_collector.py
      - jquants_client.py (外部 API インターフェース)
    - utils/
      - logging_setup.py
      - process_priority.py
- config/
  - system_config.yaml
  - data_config.yaml
  - strategy_config.yaml
  - risk_config.yaml
  - execution_config.yaml
  - monitoring_config.yaml

※ config/*.yaml はプロジェクト構成に合わせて用意してください。PyYAML がインストールされていれば validate_config にて内容チェックが行われます。

## 運用上の注意

- 本番環境（KABUSYS_ENV=live）では、LINE の通知設定や kill flag の設定などが安全性に直結します。validate_config の警告をよく確認してください。
- kill.flag や PID ファイル、stop_requested.flag の扱いに注意してください（誤ったクリアは想定外の発注につながる恐れがあります）。
- ExecutionEngine は発注の冪等性・クラッシュ安全性（OrderSent の two-phase persistence 等）を考慮していますが、実ブローカー接続時は入念な検証が必要です。
- KabuStationClient はローカルで kabuステーションアプリケーションが稼働していることを前提とします。実利用前に API 仕様・認証方法を確認してください。

---

何か追加したい項目（例: CI やテストの実行方法、具体的な config.yaml のサンプル、運用手順書など）があれば教えてください。README を拡張して手順や例を追加します。