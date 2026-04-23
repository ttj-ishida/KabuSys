# KabuSys

バージョン: 0.1.0

KabuSys は日本株向けの自動売買システム（プロトタイプ）です。  
シグナルを読み込み、発注・約定管理・監視・リコンシリエーションを行うための実装を含みます。開発／ペーパートレード／本番（将来対応）を想定した設計です。

主な設計方針:
- 帳票（DB）とビジネスロジックの分離（OrderRecord は DB に触れない等）
- 冪等性・クラッシュ耐性（2相永続化や Reconciler による復旧）
- 3段階リスクガード（Gate1: シグナル、Gate2: 実行、Gate3: メトリクス）
- ペーパートレード用の MockBrokerClient による環境分離

---

## 機能一覧

- 環境設定ウィザード（.env の対話式生成）: kabusys.config_setup
- 設定検証 CLI（.env と config/*.yaml の検証）: kabusys.validate_config
- ExecutionEngine（シグナルプル型発注エンジン）
  - シグナルの読み込み、Gate1/2 を通した発注、WebSocket push のドレイン処理
  - 発注の永続化（SQLite）、履歴管理、監視 DB へのログ
- Order 管理
  - OrderRecord（状態遷移）／OrderRepository（SQLite 永続化）／OrderManager（外向 API）
  - Reconciler：起動時の OrderSent 状態の復旧とポジション差分照合
- Broker クライアント群
  - KabuStationClient（kabuステーション REST 実装）
  - MockBrokerClient（テスト／開発用）
  - Broker のファクトリ create_broker_api をラップする BrokerClientFactory
- RiskManager（Gate1〜3: 余力・重複・ポジション上限、レート制限・CB、ドローダウン監視）
- Data モジュール
  - カレンダー管理（JPX カレンダーを扱う：next_trading_day 等）
  - ニュース収集（RSS 収集・正規化・保存ロジック）
- Monitoring
  - SystemMonitor のポーリング起動スクリプト（kabusys.run_monitoring）
- ユーティリティ
  - ロギング設定、プロセス優先度設定等（utils 以下）

---

## セットアップ手順

前提:
- Python 3.9+（型ヒントや一部記法を想定）
- SQLite は標準搭載、DuckDB は別途インストール

推奨手順（Unix/macOS）:

1. 仮想環境作成（任意）
   ```
   python -m venv .venv
   source .venv/bin/activate
   ```

2. 依存パッケージをインストール
   必要最小限（用途によって追加）:
   ```
   pip install duckdb httpx websocket-client defusedxml
   ```
   - PyYAML は config/*.yaml のパース検証に必要（任意）
     ```
     pip install pyyaml
     ```

3. リポジトリルートで data ディレクトリや必要ディレクトリを作成（多くは起動時に自動作成されます）
   ```
   mkdir -p data
   mkdir -p config
   ```

4. .env 作成
   - 対話式ウィザードを使う:
     ```
     python -m kabusys.config_setup
     ```
   - あるいは .env を手動作成（下記「環境変数」参照）。

注意:
- 自動で .env をロードする仕組みが入っています（OS 環境変数 > .env.local > .env）。自動ロードを無効化する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## 環境変数（主なもの）

必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

重要（省略時はデフォルトあり）:
- KABUSYS_ENV: execution 環境（development / paper_trading / live）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（デフォルト: data/monitoring.db）
- LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL
- KABU_API_BASE_URL: kabu station API ベース URL
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: 本番アラート用（live 時に推奨）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（0/1）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒, デフォルト 60）

簡易 .env の例:
```
KABUSYS_ENV=development
JQUANTS_REFRESH_TOKEN=your_token_here
KABU_API_PASSWORD=your_password_here
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
LOG_LEVEL=INFO
```

---

## 使い方

主要 CLI / モジュール:

- 環境設定ウィザード（.env 生成）
  ```
  python -m kabusys.config_setup
  ```

- 設定検証（.env と config/*.yaml の存在・基本整合チェック）
  ```
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict   # 警告も失敗扱いにする
  ```

- 実行エンジンを起動（通常は systemd 等で運用）
  ```
  python -m kabusys.run_execution
  ```
  - KABUSYS_ENV が paper_trading または development の場合は MockBrokerClient を使用して発注（本番環境では未実装の箇所あり）。
  - 起動時に kill.flag の取り扱い、pid ファイルの生成を行います。

- 監視プロセス起動（SystemMonitor のポーリング）
  ```
  python -m kabusys.run_monitoring
  ```
  - 環境変数 MONITOR_POLL_INTERVAL で間隔を上書き可能（秒、デフォルト 60）。

開発・テスト向け:
- MockBrokerClient を用いたユニットテストや動作確認が可能（paper_trading が想定環境）。
- ExecutionEngine はテスト時に内部メソッド（_process_signals / _drain_push_queue）を直接呼んで単体テストが行えます。

ログ:
- utils.logging_setup で設定。LOG_LEVEL 環境変数で制御できます。

停止:
- run_execution / run_monitoring はプロジェクトルートの data/stop_requested.flag を作成すると検知して安全停止します（または kill.flag による kill_switch の発動）。

---

## 内部アーキテクチャ（概略）

- Execution フロー:
  - ExecutionEngine
    - シグナルの DuckDB からの読み込み
    - Gate1（RiskManager.check_signal） → Gate2（RiskManager.check_execution）を通し OrderManager.create_order/send_order を呼び出す
    - WebSocket push を受け取り sync_order（OrderManager.sync_order）で状態更新
    - Gate3（RiskManager.check_metrics）でドローダウンや異常を検出し必要時 kill_switch を実行
  - OrderManager は OrderRecord（状態遷移ロジック）と OrderRepository（SQLite 永続化）を組み合わせる
  - Reconciler は起動時に OrderSent の注文をブローカーと照合して状態を回復、ポジション差分をログに記録

- Broker 層:
  - broker_api に Protocol とデータモデルを定義
  - create_broker_api で Mock / KabuStation の切替
  - KabuStationClient は httpx / websocket-client を使用して kabuステーションと通信

- Data:
  - calendar_management: 営業日判定、next_trading_day / get_trading_days 等
  - news_collector: RSS 収集・正規化・DB 保存（SSRF 対策・XML の安全パース等考慮）

---

## ディレクトリ構成

（プロジェクトルート想定。主要ファイルのみ抜粋）

- config/
  - system_config.yaml
  - data_config.yaml
  - strategy_config.yaml
  - risk_config.yaml
  - execution_config.yaml
  - monitoring_config.yaml
- data/
  - (duckdb / sqlite / pid / flag 等のランタイムファイル)
- src/
  - kabusys/
    - __init__.py
    - config.py                 — 環境変数読み込み・Settings
    - config_setup.py           — .env ウィザード
    - validate_config.py        — 設定検証 CLI
    - run_execution.py          — 実行エンジン起動スクリプト
    - run_monitoring.py         — 監視ループ起動スクリプト
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
      - order_record.py
      - ...（その他実装）
    - data/
      - calendar_management.py
      - news_collector.py
      - jquants_client.py (参照)
    - monitoring/
      - monitoring_db.py
      - system_monitor.py
    - utils/
      - logging_setup.py
      - process_priority.py
    - ...（その他モジュール）

---

## 注意点・運用上のヒント

- KABUSYS_ENV の値は "development", "paper_trading", "live" のいずれかです。live は本番想定で、設定ミスに注意する設計になっています（validate_config でも警告）。
- .env は絶対にバージョン管理にコミットしないでください（config_setup のヘッダにも記載）。
- 本実装では本番向けの KabuStationClient の利用は想定されていますが、Live broker client の一部は未実装の箇所があります（BrokerClientFactory でも live は NotImplementedError を出します）。ペーパートレード／開発用に MockBrokerClient を利用して検証してください。
- 設定検証 CLI で PyYAML がインストールされていない場合、YAML の内容検証はスキップされます。config/*.yaml を使用する場合は PyYAML の導入を推奨します。

---

この README はコードベースの主要機能と操作手順をまとめたものです。個々のモジュール（ExecutionEngine, OrderManager, RiskManager, Reconciler など）はそれぞれドキュメント化されており、詳細は該当ソースの docstring を参照してください。