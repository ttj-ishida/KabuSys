# KabuSys

日本株自動売買システムの軽量コアライブラリ（README 抜粋）

> 本リポジトリは、シグナルに基づく発注エンジン、リスクガード、ブローカークライアントの抽象化、
> 監視（Monitoring）およびデータユーティリティ（カレンダー、ニュース収集等）を含むモジュール群です。
> この README はリポジトリの利用開始手順・主要機能・ディレクトリ構成を説明します。

## 概要

KabuSys は日本株向けの自動売買基盤のコア部分を実装した Python パッケージです。  
主な目的は「発注ワークフローの堅牢化（クラッシュ耐性・リコンシリエーション）」「多段階リスクガード」「開発/ペーパー/本番切替の容易化」を提供することです。

主なコンポーネント
- ExecutionEngine: シグナルを読み込み発注を行うメインエンジン（シグナルループ + push ドレイン）
- Broker クライアント群: 実ブローカー（kabu station）用クライアント / MockBrokerClient（テスト用）
- Order 管理: OrderRecord（状態遷移ロジック）、OrderRepository（SQLite 永続化）、OrderManager（外向き API）
- RiskManager: Gate1/2/3 による多段階リスクチェック（余力・重複・レート制限・ドローダウン等）
- Reconciler: 再起動時の OrderSent 照合とポジション差分チェック
- Monitoring: システム監視ループ（SQLite / DuckDB を利用）
- Data utilities: マーケットカレンダー管理、ニュース収集等
- 設定ユーティリティ: .env ウィザード、設定検証 CLI、Settings クラスによる環境変数管理

## 機能一覧

- .env 対話式ウィザードでの初期設定 (.env/.env.local)
- 設定検証 CLI（config/*.yaml・環境変数・パス等の検査）
- ExecutionEngine によるシグナル→発注の自動化
- MockBrokerClient によるペーパートレーディング / 開発環境での検証
- 発注の永続化（SQLite）と状態遷移チェック（OrderRecord）
- 再起動時のリコンシリエーション（OrderSent の突合／ポジション差分検査）
- リスク管理（single-stock limit、utilization、rate limit、circuit breaker、drawdown）
- DuckDB を使ったデータ処理（シグナル・ポートフォリオ等）
- 監視ループ（SystemMonitor）と監視 DB（SQLite）
- カレンダー・ニュース収集ユーティリティ（J-Quants 連携想定）

## 前提・依存関係

推奨 Python バージョン: 3.10+

必須（実行する機能に応じて）:
- duckdb
- httpx
- websocket-client
- defusedxml
- PyYAML（config.yaml のパース検証を有効にする場合）
- sqlite3（標準ライブラリ）
- その他、標準ライブラリ（logging, threading, pathlib など）

インストール例（仮想環境推奨）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install duckdb httpx websocket-client defusedxml pyyaml
```

※ 実際には pyproject.toml / requirements.txt があればそちらを利用してください。

## セットアップ手順

1. リポジトリをクローン・必要パッケージをインストールする。

2. .env を作成する（対話式ウィザード推奨）:
   ```bash
   python -m kabusys.config_setup
   ```
   ウィザードは既存の .env を読み取り、対話的に値を入力して .env を上書き（または作成）します。
   生成された .env を絶対に Git にコミットしないでください。

3. 設定を検証する:
   ```bash
   python -m kabusys.validate_config
   # 警告を fail 扱いにする場合
   python -m kabusys.validate_config --strict
   ```
   validate_config は環境変数の存在・プレースホルダ検知、KABUSYS_ENV の妥当性、LOG_LEVEL、DB パスや config/*.yaml の存在（および PyYAML がある場合はパース検証）などをチェックします。

4. データディレクトリ準備:
   デフォルトでは data/ 以下のファイルを参照します（DuckDB: data/kabusys.duckdb, monitoring SQLite: data/monitoring.db 等）。必要に応じて .env で DUCKDB_PATH / SQLITE_PATH を変更してください。起動時に親ディレクトリが存在しない場合は自動作成される場合がありますが、権限等に注意してください。

## 環境変数（主要）

必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

任意（よく使うもの）:
- KABUSYS_ENV: execution 環境（development / paper_trading / live）。デフォルト: development
  - development / paper_trading: MockBrokerClient を使用
  - live: 実ブローカー利用（現時点では一部未実装箇所があります）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト data/paper_trading.db）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: 本番通知用（任意）
- LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト INFO）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（0/1）

自動 .env ロード:
- プロジェクトルート（.git または pyproject.toml を含む親ディレクトリ）を基準に .env と .env.local を自動読み込みします。
- 読み込み優先度: OS 環境変数 > .env.local > .env
- 自動ロードを無効化するには: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

注意:
- .env.example 等を参考に .env を作成してください（ウィザードが便利です）。
- 本番（KABUSYS_ENV=live）では LINE 通知などの設定を整える必要があります。

## 使い方（実行例）

- 設定ウィザード
  ```bash
  python -m kabusys.config_setup
  ```

- 設定検証
  ```bash
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- 実行エンジン（ExecutionEngine）
  ```bash
  # 実際にセッションを開始（通常はデーモンや systemd 等で起動）
  python -m kabusys.run_execution
  ```
  - KABUSYS_ENV=paper_trading / development なら MockBrokerClient が使用され、paper_trading は data/paper_trading.db に分離して記録します。
  - 起動時に data/execution.pid に PID が書き込まれ、data/stop_requested.flag を作成するとエンジンは停止処理を行います。
  - 起動直後に Reconciler によるリカバリ（OrderSent の突合）が実行されます。

- 監視ループ（SystemMonitor）
  ```bash
  python -m kabusys.run_monitoring
  ```
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL（秒）で変更可能（デフォルト 60 秒）。
  - 監視は KABUSYS_ENV に関わらず本番 sqlite_path（SQLITE_PATH）を使用します。

- 開発向け / テスト:
  - MockBrokerClient の挙動は PAPER_FILL_MODE（instant / partial / never / reject）で制御できます（Settings.paper_fill_mode）。
  - ExecutionEngine やコンポーネントはユニットテストから個別に呼び出して検証可能です。

## 注意事項 / 運用メモ

- .env は機密情報を含むため必ず環境内にのみ保管し、リポジトリにコミットしないでください。
- KABUSYS_ENV=live を使用すると本番発注が行われます。validate_config は live 時に警告を出します。LINE 通知設定や KILL_FLAG_CLEAR_ON_START 等を慎重に確認してください。
- ExecutionEngine は起動時に kill.flag を検査します。既存の kill.flag がある場合、KILL_FLAG_CLEAR_ON_START が 1 でない限り起動を拒否します。
- Order のデータ整合性は OrderRepository（SQLite）の UNIQUE インデックスなどで一部保証していますが、複数プロセスからの同時操作は想定していません。実運用ではプロセス管理に注意してください。

## ディレクトリ構成（主要ファイル）

以下は本 README に含まれているコードファイルを中心にしたツリー（抜粋）です。

- src/
  - kabusys/
    - __init__.py
    - config.py                 # Settings, .env 自動読み込みロジック
    - config_setup.py           # 対話式 .env ウィザード
    - validate_config.py        # 設定検証 CLI
    - run_execution.py          # ExecutionEngine 起動スクリプト
    - run_monitoring.py         # SystemMonitor 起動スクリプト
    - execution/
      - __init__.py
      - broker_api.py           # BrokerAPIProtocol, データモデル, ファクトリ
      - broker_factory.py       # Settings に基づく Broker クライアント生成
      - kabu_client.py          # KabuStation REST client（実装）
      - mock_client.py          # MockBrokerClient（テスト用）
      - order_record.py         # OrderRecord（状態遷移ロジック）
      - order_repository.py     # SQLite 永続化層
      - order_manager.py        # Order 管理（外向き API）
      - execution_engine.py     # ExecutionEngine（シグナル→発注ロジック）
      - reconciler.py           # リコンシリエーション / 再起動回復
      - risk_manager.py         # RiskManager（Gate1/2/3）
    - monitoring/
      - monitoring_db.py        # 監視 DB 初期化 / ログ機能（参照ファイル内で使用）
      - system_monitor.py       # SystemMonitor（ポーリングロジック）
    - data/
      - calendar_management.py  # マーケットカレンダー管理（DuckDB）
      - news_collector.py       # RSS ニュース収集（セキュア実装）
    - utils/
      - logging_setup.py        # ロギング設定ユーティリティ
      - process_priority.py     # プロセス優先度設定ユーティリティ
    - config/                    # YAML 設定ファイル群（テンプレート / 実ファイル）
      - system_config.yaml
      - data_config.yaml
      - strategy_config.yaml
      - risk_config.yaml
      - execution_config.yaml
      - monitoring_config.yaml

（実際のリポジトリにはさらに多くのファイル・サブモジュールがある場合があります。本 README は提示コードの抜粋に基づいた説明です。）

## 例: 基本的な起動フロー（ローカル・ペーパートレード想定）

1. 仮想環境を作成、依存をインストール
2. python -m kabusys.config_setup で .env を作成
3. python -m kabusys.validate_config で問題がないか確認
4. python -m kabusys.run_monitoring を別プロセスで起動（監視）
5. python -m kabusys.run_execution を起動（エンジン稼働）

## ライセンス / 貢献

本 README ではライセンスは明記していません。実際のリポジトリの LICENSE ファイルを参照してください。バグ修正や機能追加の貢献は Pull Request を受け付けます。

---

この README はコードベースの主要点をまとめたものです。追加で API ドキュメント、実運用手順（systemd unit ファイル・監視構成・バックアップ方針等）やユニットテストの実行手順が必要であれば、その内容に合わせて追記できます。