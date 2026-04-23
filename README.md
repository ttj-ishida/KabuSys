# KabuSys

バージョン: 0.1.0

KabuSys は日本株向けの自動売買システムの骨格を提供する Python パッケージです。実行環境（development / paper_trading / live）に応じたブローカークライアントや、発注エンジン、リスク管理、リコンシリエーション、監視ループ、データ処理（カレンダー・ニュース収集）など、運用に必要な主要コンポーネントを含みます。

主な設計方針は以下のとおりです。
- ビジネスロジックと永続化（SQLite, DuckDB）を明確に分離
- 発注フローのクラッシュ耐性（2相永続化、リコンシリエーション）
- Gate1/2/3 による多段階リスクガード
- 開発/ペーパートレードで使える Mock ブローカー実装を提供

---

## 機能一覧

- 環境設定ウィザード（.env 作成 / 更新）: kabusys.config_setup
- 起動前設定検証 CLI（.env + config/*.yaml のチェック）: kabusys.validate_config
- 発注エンジン（ExecutionEngine）: シグナル読み取り、発注、push ドレイン、kill-switch
- ブローカークライアント群:
  - MockBrokerClient（テスト/開発用、PAPER_FILL_MODE 制御可能）
  - KabuStationClient（kabuステーション REST API 実装）
- 注文状態管理（OrderRecord）と永続化（OrderRepository: SQLite）
- OrderManager（注文作成・送信・同期・キャンセルの一連処理）
- リスク管理（RiskManager: Gate1/2/3、レート制限、サーキットブレーカー、ドローダウン）
- リコンシリエーション（Reconciler：再起動時の自動復旧）
- 監視ループ（SystemMonitor を用いる run_monitoring）
- データモジュール:
  - カレンダー管理（市場営業日判定・更新）
  - ニュース収集（RSS → raw_news）
- ユーティリティ（ログ設定・プロセス優先度設定等）

---

## セットアップ手順（ローカル開発向け）

1. リポジトリをクローンして作業ディレクトリへ移動
   ```
   git clone <repo-url>
   cd <repo-root>
   ```

2. Python 仮想環境を作成・有効化（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
   ```

3. 依存ライブラリをインストール（requirements.txt がある場合はそれを利用）
   推奨依存例:
   ```
   pip install duckdb httpx websocket-client pyyaml defusedxml
   ```
   - PyYAML は config/*.yaml のパース検証で使用（必須ではない）
   - defusedxml はニュース RSS パースで使用

4. （任意）パッケージを開発モードでインストール
   ```
   pip install -e .
   ```

5. デフォルトの DB / data ディレクトリ作成
   ```
   mkdir -p data
   ```

---

## 環境変数・設定 (.env)

- 自動読み込み順序:
  1. OS 環境変数
  2. .env.local（存在すれば上書き）
  3. .env（プロジェクトルート）

- 自動ロードを無効化するには:
  ```
  export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  ```

- 主要な必須環境変数:
  - JQUANTS_REFRESH_TOKEN（必須）
  - KABU_API_PASSWORD（必須）

- 任意 / デフォルト値がある環境変数:
  - KABUSYS_ENV (development / paper_trading / live) — default: development
  - DUCKDB_PATH — default: data/kabusys.duckdb
  - SQLITE_PATH — default: data/monitoring.db
  - PAPER_TRADING_SQLITE_PATH — default: data/paper_trading.db
  - LOG_LEVEL — default: INFO
  - KABU_API_BASE_URL — default: http://localhost:18080/kabusapi
  - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — 通知用（任意）
  - KILL_FLAG_CLEAR_ON_START — 起動時の kill.flag 自動クリア（0/1）
  - MONITOR_POLL_INTERVAL — 監視ポーリング間隔（秒、run_monitoring）

- .env の作成はウィザードを推奨（下記参照）。

---

## 使い方（主要コマンド）

- 環境設定ウィザード（対話式で .env を作成/更新）
  ```
  python -m kabusys.config_setup
  ```
  オプション:
  - --env-file で .env のパスを指定可能

- 起動前設定検証
  ```
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict  # 警告も FAIL 扱い
  ```
  - .env と config/*.yaml の存在・基本妥当性をチェックします。PyYAML が無い場合は YAML 内容検証はスキップされます。
  - config/*.yaml が無ければ警告が出ます（generate_config.py による生成参照）。

- 実行エンジン起動（デフォルト: settings に従う）
  ```
  python -m kabusys.run_execution
  ```
  - KABUSYS_ENV が paper_trading / development の場合は MockBrokerClient が使われます。
  - 実行中は data/execution.pid（PID ファイル）を書き、stop フラグは data/stop_requested.flag を確認して停止します。
  - kill.flag（data/kill.flag）で発注停止（kill switch）をトリガできます。
  - paper_trading モードでは専用 SQLite（PAPER_TRADING_SQLITE_PATH）を使用し本番 DB と分離します。

- 監視ループ起動
  ```
  python -m kabusys.run_monitoring
  ```
  - 環境にかかわらず本番 sqlite_path を使用して監視データを記録します。
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で上書き可能（デフォルト 60 秒）。

- ログレベル:
  LOG_LEVEL 環境変数で設定（DEBUG/INFO/WARNING/ERROR/CRITICAL）

---

## 主要設定例（最小 .env）
以下は最小限の例（実運用では実際のトークン・パスワードに置き換えてください）。

```
JQUANTS_REFRESH_TOKEN=your_jquants_token_here
KABU_API_PASSWORD=your_kabu_password_here
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
LOG_LEVEL=INFO
```

ウィザードで入力すれば .env ファイルがプロジェクトルートに生成されます。

---

## 実運用上の注意点

- KABUSYS_ENV=live の場合は本番運用向けガードが多数働きます。LINE 通知設定などの必須性が高まるほか、KILL_FLAG_CLEAR_ON_START=1 は危険と見なされ警告が出ます。
- 発注フローはクラッシュ耐性を考慮して設計されていますが、実際の本番注文は極めて慎重にテストを行ってから行ってください。
- .env は機密情報を含むため Git にはコミットしないでください。
- config/*.yaml（system_config.yaml 等）はプロジェクトの実行に必要であれば生成スクリプトを実行してください（validate_config は欠落時に警告を出します）。
- PyYAML がインストールされていない場合、YAML のパース検証がスキップされます。運用前には PyYAML を入れて精密チェックを行ってください。

---

## ディレクトリ構成（主なファイルと役割）

- src/kabusys/
  - __init__.py — パッケージ宣言（バージョン情報）
  - config.py — 環境変数の自動ロード・Settings クラス（設定アクセス）
  - config_setup.py — .env 対話式ウィザード
  - validate_config.py — 起動前設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト
  - execution/
    - __init__.py — 公開 API のまとめ
    - broker_api.py — Broker API のデータモデル・Protocol・ファクトリ
    - broker_factory.py — Settings に基づくブローカー生成
    - kabu_client.py — kabuステーション REST API クライアント実装
    - mock_client.py — MockBrokerClient（テスト用）
    - order_record.py — OrderRecord（状態遷移ロジック）
    - order_repository.py — SQLite による永続化層
    - order_manager.py — 外向き注文 API（create/send/sync/cancel）
    - execution_engine.py — ExecutionEngine（シグナル処理、push ドレイン、kill）
    - reconciler.py — リコンシリエーション（再起動時の同期）
    - risk_manager.py — RiskManager（Gate1/2/3）
  - data/
    - calendar_management.py — 市場カレンダー管理（J-Quants 連携）
    - news_collector.py — RSS ニュース収集
    - (その他データ関連モジュール)
  - monitoring/
    - monitoring_db.py — 監視 DB 初期化／ログ
    - system_monitor.py — システム監視ロジック
  - utils/
    - logging_setup.py — ログ設定ユーティリティ
    - process_priority.py — プロセス優先度設定ユーティリティ
  - strategy/ (戦略関連モジュール群、ここでは実装の骨子を想定)

- config/
  - system_config.yaml
  - data_config.yaml
  - strategy_config.yaml
  - risk_config.yaml
  - execution_config.yaml
  - monitoring_config.yaml
  （上記 YAML はプロジェクト起動時に必要になることがあります。validate_config で確認します。）

- data/
  - デフォルトで使用される DB / PID / flag ファイル置き場
    - kabusys.duckdb (default: data/kabusys.duckdb)
    - monitoring.db (default: data/monitoring.db)
    - paper_trading.db (paper_trading 用)
    - execution.pid, stop_requested.flag, kill.flag など

---

## 開発者向けメモ

- Settings クラス経由で設定値へアクセスしてください（kabusys.config.settings）。
- ブローカーの振る舞いを切り替える際は BrokerClientFactory を利用してください。
- 発注フローのクラッシュ耐性やリコンシリエーションの挙動を理解した上で変更してください（特に OrderSent → broker 呼び出し周りの永続化順序）。
- テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自動読み込みを無効化できます。

---

README の内容はコードベースから抽出した概要です。追加で README に含めたい情報（CI、テスト実行方法、依存バージョン、デプロイ手順など）があれば教えてください。