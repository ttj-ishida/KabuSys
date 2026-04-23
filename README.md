# KabuSys

日本株向け自動売買システム（KabuSys）のリポジトリ用 README。  
この README はリポジトリ内の主要モジュール（設定管理、実行エンジン、発注管理、リスクガード、データ処理、監視）を簡潔にまとめ、セットアップと基本的な使い方を示します。

> 注意: .env は機密情報を含むため絶対に Git にコミットしないでください。.env の生成には本プロジェクト付属のウィザードを使用してください。

## 概要

KabuSys は以下を目的としたコンポーネント群を持つ自動売買基盤です。

- シグナルを元に発注を行う ExecutionEngine（発注・状態管理・再同期待ち合わせ）
- ブローカー API 抽象化（実環境の kabu station / テスト用 MockBroker）
- 3段階のリスクガード（Gate1: シグナル、Gate2: 実行／レート制限、Gate3: ドローダウン）
- 起動時のリコンシリエーション（OrderSent 状態の照合）
- Dataplatform 用のデータ処理（マーケットカレンダー、ニュース収集など）
- 監視プロセス（SystemMonitor）と監視データ保存用 SQLite
- .env の対話的生成（config_setup）および起動前チェック（validate_config）

## 主な機能一覧

- 環境設定ウィザード（python -m kabusys.config_setup）
  - .env の対話的作成／更新。必須トークン類を安全に入力できる。
- 設定検証 CLI（python -m kabusys.validate_config）
  - .env と config/*.yaml の存在・妥当性を起動前にチェック。--strict オプションで警告も FAIL 扱い。
- 実行エンジン（python -m kabusys.run_execution）
  - Signal Queue ベースの発注フロー、WebSocket push ドレイン、kill flag による安全停止。
  - KABUSYS_ENV により Mock（paper_trading / development） or live 動作を切替（現状 live クライアントは未実装の旨例外）。
- 監視プロセス（python -m kabusys.run_monitoring）
  - SystemMonitor をポーリングしてシステム資源や健全性を監視。MONITOR_POLL_INTERVAL で間隔変更可能。
- ブローカークライアント（kabu station 実装 + Mock）
  - KabuStationClient: httpx を用いた REST/WebSocket クライアント（トークン自動管理、リトライ、429/5xx ハンドリング）
  - MockBrokerClient: テスト用の振る舞い（instant/partial/never/reject）
- 注文永続化（SQLite）と OrderRecord（状態遷移の厳密検証）
- リスク管理（RateLimit / CircuitBreaker / Drawdown / Position・Utilization チェック）
- データ処理
  - market_calendar 管理（DuckDB）
  - RSS ニュース収集（defusedxml, トラッキング削除, SSRF 対策）

## 必要環境 / 依存

- Python 3.10 以上（型記法に | を使用しているため）
- 推奨パッケージ（一例）
  - duckdb
  - httpx
  - websocket-client
  - defusedxml
  - PyYAML（config 検証で利用。未インストールでも動作するが YAML パースはスキップされる）
- SQLite は標準ライブラリで利用

インストール例（仮の requirements）:
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb httpx websocket-client defusedxml pyyaml
# さらに必要なパッケージがあれば追加
```

※ 実際の requirements.txt がある場合はそれを使ってください。

## セットアップ手順

1. リポジトリをクローンしてワークスペースへ移動
   ```
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境作成・依存パッケージをインストール（上記参照）

3. .env の生成（対話ウィザード）
   ```
   python -m kabusys.config_setup
   ```
   - 必須: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD
   - GUI ではなくターミナル対話です。入力後に .env に保存されます。

4. 設定の検証（起動前チェック）
   ```
   python -m kabusys.validate_config
   ```
   - --strict を付けると警告もエラー扱い（exit 1）

5. データディレクトリ（data）や DB ファイルは起動時に自動生成することが多いです。必要に応じて .env の DUCKDB_PATH / SQLITE_PATH を調整してください。

## 使い方（基本コマンド）

- 環境ウィザード（.env 作成）
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- 実行エンジン起動（本番・ペーパートレードともにコマンドは同じ。KABUSYS_ENV に依存）
  ```
  python -m kabusys.run_execution
  ```
  - KABUSYS_ENV=paper_trading / development では MockBrokerClient を使用（PAPER_FILL_MODE 等で挙動制御）。
  - 実行中に data/stop_requested.flag を作成すると安全に停止されます。
  - PID ファイルは .env の PID_FILE_PATH（デフォルト data/execution.pid）へ書き込まれます。

- 監視プロセス起動
  ```
  python -m kabusys.run_monitoring
  ```
  - 環境にかかわらず監視は本番 sqlite_path を参照します（監視 DB は共通）。
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を変更できます。

## 主要環境変数

（validate_config でチェックされる主なキー）

必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

任意 / 推奨:
- KABUSYS_ENV: development | paper_trading | live （デフォルト development）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 SQLite（デフォルト data/paper_trading.db）
- LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL
- KABU_API_BASE_URL: kabu station のベース URL
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: 本番での通知用（live 環境では未設定だと警告）
- KILL_FLAG_CLEAR_ON_START: 1 にすると起動時に既存 kill.flag を自動クリア（本番は 0 推奨）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒）

kill / stop ファイル:
- KILL_FLAG_PATH（デフォルト data/kill.flag）: kill switch 起動用
- stop_requested.flag（data/stop_requested.flag）: スクリプト外からの停止指示に使用

## 動作モードについて

- development: 開発用（発注は行わない、もしくは Mock を利用）
- paper_trading: ペーパートレード（MockBrokerClient を使い、paper_trading 用 DB に記録）
- live: 本番（実際に発注を行う想定。注意: 現状 live 用 KabuStationClient は例外を投げる箇所があるため設定・実装の確認が必要）

## 主要コンポーネント（ファイルと役割）

以下は src/kabusys 以下の主要ファイル／ディレクトリと概要です。

- src/kabusys/__init__.py
  - パッケージ定義・バージョン

- 設定関連
  - src/kabusys/config.py
    - .env 自動読み込みロジック、Settings クラス（環境変数ラッパ）
  - src/kabusys/config_setup.py
    - .env の対話的ウィザード（生成／更新）
  - src/kabusys/validate_config.py
    - 起動前チェック CLI（必須環境変数・config/*.yaml の存在などを検証）

- エントリスクリプト
  - src/kabusys/run_execution.py
    - 実行エンジン（ExecutionEngine）の起動スクリプト
  - src/kabusys/run_monitoring.py
    - 監視プロセスの起動スクリプト

- execution/（発注関連）
  - broker_api.py: BrokerAPIProtocol、データモデル、例外、ファクトリ
  - kabu_client.py: kabu station REST / WebSocket クライアント実装
  - mock_client.py: テスト用 MockBrokerClient（fill_mode 制御）
  - broker_factory.py: Settings に基づくクライアント生成
  - order_record.py: OrderState / OrderRecord（状態遷移ロジック）
  - order_repository.py: SQLite による永続化層（orders テーブルの初期化含む）
  - order_manager.py: 発注フロー（create/send/sync/cancel）の外向き API
  - execution_engine.py: セッション（シグナル読み込み・発注ループ・push ドレイン）
  - reconciler.py: 再起動時の照合（OrderSent 照合とポジション差分）

- data/（データ処理）
  - calendar_management.py: マーケットカレンダー管理（DuckDB）
  - news_collector.py: RSS ニュース収集（前処理/SSRF 対策）
  - jquants_client.py: J-Quants との連携（参照のみ。カレンダー取得など）

- monitoring/
  - monitoring_db.py: 監視用 SQLite テーブル初期化・ログ機能（run_monitoring から利用）

- utils/
  - logging_setup.py: ロギング初期化ユーティリティ
  - process_priority.py: プロセス優先度設定ユーティリティ

（上記は主要ファイルの抜粋です。実コードではさらに細分化されたモジュールが存在します。）

## 開発上の注意点 / 運用メモ

- .env は OS 環境変数より下位で自動ロードされます。.env.local（存在すれば上書き）にも対応。
- 自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能（テスト時に便利）。
- orders テーブルは signal_id の「active 注文は 1 件のみ」を UNIQUE INDEX で保証しています。DuplicateOrder の扱いは注意。
- ExecutionEngine は kill.flag を検出すると安全停止して全 active 注文を CANCEL します。KILL_FLAG_CLEAR_ON_START に注意。
- run_monitoring は常に本番 sqlite_path を参照します（監視 DB は環境に依存せず本番 DB を想定）。
- config/*.yaml（strategy, risk, execution など）が存在すれば YAML パースも実行して妥当性を確認します（PyYAML が必要）。

## よく使うコマンドまとめ

- 仮想環境作成・依存インストール
  ```
  python -m venv .venv
  source .venv/bin/activate
  pip install -r requirements.txt   # もしあれば
  ```

- .env 作成
  ```
  python -m kabusys.config_setup
  ```

- 設定チェック
  ```
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- 実行エンジン起動
  ```
  python -m kabusys.run_execution
  ```

- 監視起動
  ```
  python -m kabusys.run_monitoring
  ```

## ライセンス / 責任免除

本 README はコードベースの説明です。実際の資金を用いた運用は自己責任で行ってください。実運用前に十分なテスト・レビュー、安全弁（kill switch、監視、アラート）を確認してください。

---

追加で README に含めたい情報（例: CI 手順、テスト実行方法、具体的な環境変数の例、config YAML フォーマットの仕様など）があれば教えてください。必要に応じてサンプル .env.example や起動フロー図も作成できます。