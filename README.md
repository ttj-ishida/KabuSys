# KabuSys

日本株向け自動売買システム（KabuSys）の軽量なコア実装。  
発注ロジック、ブローカー抽象化、監視・リコンシリエーション、データ収集等の主要コンポーネントを含みます。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は以下の責務を持つモジュール群で構成された自動売買プラットフォームのコアです。

- ブローカー API 抽象化（kabuステーション向け実装 + テスト用モック）
- 発注エンジン（ExecutionEngine） — シグナルベースの発注と push ドレイン
- 注文永続化（SQLite）と状態遷移ロジック（OrderRecord）
- 起動時のリコンシリエーション（Reconciler）
- リスクガード（3段階: Gate1/2/3）
- 監視ループ（SystemMonitor 用スクリプト）
- 環境設定ウィザード（.env 作成）と設定検証 CLI
- データ系ユーティリティ（マーケットカレンダー・ニュース収集等）

設計方針として、ビジネスロジックと永続化を責務分離し、テスト容易性（MockBrokerClient）とクラッシュ耐性（OrderSent の二相永続化など）を重視しています。

---

## 主な機能一覧

- 設定管理
  - .env / .env.local 自動ロード（プロジェクトルート検出）
  - 対話式 .env 生成ウィザード（python -m kabusys.config_setup）
  - 設定検証 CLI（python -m kabusys.validate_config）
- 発注・注文管理
  - OrderRecord による状態遷移検証
  - SQLite による永続化（orders テーブル・インデックス）
  - OrderManager による発注フロー（クラッシュ耐性を考慮した二段階永続化）
- ブローカー
  - KabuStationClient（kabuステーション REST API 実装）
  - MockBrokerClient（テスト/ペーパートレード用）
  - BrokerAPIProtocol による抽象化・ファクトリ
- ExecutionEngine
  - シグナル処理（発注時間帯）と WebSocket push ドレイン
  - リスクガード（Gate1: シグナル、Gate2: 実行、Gate3: メトリクス）
  - kill switch（全注文キャンセル・セッション停止）
- リコンシリエーション
  - OrderSent 状態の突合（起動時の自動復旧）
  - ブローカーとローカルポジションの差分検出
- 監視
  - run_monitoring.py によるポーリング監視ループ
- データユーティリティ
  - マーケットカレンダー管理（DuckDB）
  - RSS ニュース収集（defusedxml 等を利用した安全な実装）

---

## セットアップ手順（ローカル開発向け）

前提: Python 3.9+（ソースは typing/Path 等を使用）。UNIX 系環境を想定。

1. リポジトリをクローンしてワークツリーへ移動
   - （省略）

2. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate

3. 必要なパッケージをインストール
   - 主要依存（例）:
     - duckdb
     - httpx
     - websocket-client
     - PyYAML (任意だが設定検証で有用)
     - defusedxml
   - 例:
     - pip install duckdb httpx websocket-client PyYAML defusedxml

   ※ 実際の requirements.txt がある場合は `pip install -r requirements.txt` を使用してください。

4. .env の準備
   - 推奨フロー:
     1. 対話式ウィザードを実行して .env を生成:
        - python -m kabusys.config_setup
     2. 生成した .env を検証:
        - python -m kabusys.validate_config
        - 必要に応じて `--strict` を付けると警告も失敗扱いになります
   - 自動ロード: .env および .env.local は Settings モジュール起動時に自動で読み込まれます（環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能）。

5. データディレクトリ
   - デフォルトで以下が使用されます（必要に応じて .env で上書き）:
     - DUCKDB_PATH: data/kabusys.duckdb
     - SQLITE_PATH: data/monitoring.db
     - PID / flag ファイル: data/*.pid / data/kill.flag / data/stop_requested.flag
   - ディレクトリは自動作成される箇所もありますが、権限等を確認してください。

---

## 必要な環境変数（主要）

- 必須
  - JQUANTS_REFRESH_TOKEN — J-Quants API 用リフレッシュトークン
  - KABU_API_PASSWORD — kabuステーション API パスワード

- 任意 / 推奨（デフォルトあり）
  - KABUSYS_ENV — 実行環境: development / paper_trading / live （デフォルト: development）
  - DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
  - LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL、デフォルト: INFO）
  - KABU_API_BASE_URL — kabu station base url（デフォルト: http://localhost:18080/kabusapi）
  - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — 本番アラート用（live 環境で重要）
  - KILL_FLAG_CLEAR_ON_START — 起動時 kill.flag を自動クリアするか（0/1, デフォルト 0）

- Paper Trading 特有
  - PAPER_FILL_MODE — instant / partial / never / reject（デフォルト: instant）
  - PAPER_TRADING_SQLITE_PATH — ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）

- Monitoring
  - MONITOR_POLL_INTERVAL — 監視ポーリング間隔（秒、デフォルト: 60）

設定検証ツール（python -m kabusys.validate_config）が多くのチェックを行います。まずそれを実行してください。

---

## 使い方（主要スクリプト）

- 設定ウィザード（.env を対話的に作成/更新）
  - python -m kabusys.config_setup

- 設定検証（.env と config/*.yaml の存在・基本妥当性をチェック）
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict   # 警告も FAIL 扱い

- 実際の発注エンジン起動（本番相当セッション）
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading を指定すると MockBrokerClient（ペーパートレード）を使用し、paper_trading 用 DB に書き込みます。

- 監視ループ起動
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更可能（デフォルト 60 秒）

注意点:
- 実際のライブ運用（KABUSYS_ENV=live）は慎重に。validate_config や config_setup は live を意識した警告を出します。
- 実行時の停止制御は data/stop_requested.flag と data/kill.flag を利用します。詳細はコード内の説明を参照してください。

---

## 主要コンポーネント（簡潔な説明）

- config.py / Settings
  - .env 自動ロード、環境変数取得、必須チェックを提供します。

- config_setup.py
  - 対話式ウィザードで .env を作成・更新します。

- validate_config.py
  - 起動前に環境変数や config/*.yaml の欠落や妥当性をチェックします。

- execution/
  - broker_api.py — ブローカー API のデータモデル・Protocol・ファクトリ
  - kabu_client.py — kabuステーション向け実実装（HTTP + WebSocket）
  - mock_client.py — テスト/ペーパートレード用モック
  - order_record.py — 注文状態遷移のビジネスロジック
  - order_repository.py — SQLite ベースの永続化層
  - order_manager.py — 発注フロー制御（DB + broker 連携）
  - execution_engine.py — セッション実行、シグナル処理、push ドレイン
  - risk_manager.py — Gate1/2/3 のリスクチェック
  - reconciler.py — 起動時リコンシリエーション
  - broker_factory.py — Settings に基づくクライアント生成

- data/
  - calendar_management.py — マーケットカレンダー管理（DuckDB）
  - news_collector.py — RSS ニュース収集（セキュア実装）

- monitoring/
  - monitoring_db / SystemMonitor など（監視関連）

---

## ディレクトリ構成（src/kabusys の主要ファイル）

- src/kabusys/
  - __init__.py — パッケージ定義（__version__ 等）
  - config.py — 設定読み込み・Settings
  - config_setup.py — .env 対話式ウィザード
  - validate_config.py — 設定検証 CLI
  - run_execution.py — ExecutionEngine を起動するスクリプト
  - run_monitoring.py — 監視ループ起動スクリプト
  - execution/
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
  - data/
    - calendar_management.py
    - news_collector.py
    - (jquants_client 等外部 API クライアントが存在する想定)
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
  - utils/
    - logging_setup.py
    - process_priority.py

（全てのファイルを列挙していませんが、上が主要な構成です。実装内の docstring を参照してください。）

---

## 運用上の注意・ベストプラクティス

- .env を絶対に Git にコミットしないでください（config_setup.py の生成ファイルでも同様の注意書きがあります）。
- KABUSYS_ENV=live の場合は LINE 通知設定（LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID）等、本番向けのアラートを必ず確認してください。validate_config は live の際に追加警告を出します。
- kill.flag の扱いに注意:
  - KILL_FLAG_CLEAR_ON_START=1 にすると起動時に kill.flag を自動クリアします（開発向け）。本番では 0（クリアしない）を推奨します。
- 発注時のクラッシュ耐性:
  - OrderManager は OrderSent を DB に永続化してから broker 呼び出しを行う等、クラッシュ後の復旧を考慮した設計です。再起動時は reconciler による同期が実施されます。
- テスト環境では MockBrokerClient や PAPER_FILL_MODE を活用して実稼働と分離してください。

---

## 参考コマンドまとめ

- 環境ウィザード:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict
- 実行エンジン起動:
  - python -m kabusys.run_execution
- 監視ループ起動:
  - python -m kabusys.run_monitoring

---

README はここまでです。特定ファイルの詳細な API ドキュメントや設定例（.env.example、config/*.yaml サンプル）、運用手順（systemd ユニット、ログローテーション等）を追加したい場合は教えてください。