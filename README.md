# KabuSys

日本株自動売買システムのコアライブラリ（簡易版）。  
このリポジトリは、設定管理・発注エンジン・ブローカークライアント（モック含む）・監視処理・データ補助機能（カレンダー・ニュース収集など）を含みます。

## 概要
- 環境変数／`.env` を読み込んで設定を構成し、実行時に各コンポーネントがそれを参照します。
- 発注フローは Signal Queue → OrderManager → BrokerAPI（kabu station または Mock）という構成。
- 再起動時のリコンシリエーション、3段階のリスクガード（Gate1～3）、監視ループなど安全性を重視した設計。
- paper_trading モードでは MockBrokerClient を使用し、本番 DB と分離してテスト可能。

## 主な機能一覧
- 環境設定ウィザード（.env を対話式に作成・更新）: kabusys.config_setup
- 設定検証ツール（.env と config/*.yaml を検査）: kabusys.validate_config
- 発注エンジン（ExecutionEngine）: シグナル読み込み → 発注・状態管理・push ドレイン
- 注文管理: OrderManager / OrderRecord / OrderRepository（SQLite）
- ブローカークライアント:
  - MockBrokerClient（テスト用、fill_mode 制御可能）
  - KabuStationClient（kabu station REST / WebSocket 実装）
- リスク管理: RiskManager（Gate1: シグナル、Gate2: 実行、Gate3: メトリクス／ドローダウン）
- リコンシリエーション: Reconciler（OrderSent の突合・ポジション差分検出）
- 監視プロセス（SystemMonitor 起動ループ）
- データ補助:
  - DuckDB ベースのカレンダー管理（next_trading_day 等）
  - ニュース収集（RSS 取得・前処理）など

## セットアップ手順（ローカル実行向け）
1. Python 環境を用意（推奨: 3.10+）
2. 必要なパッケージをインストール（プロジェクトに requirements.txt が無い場合は最低限以下を入れると良い）
   - httpx, websocket-client, pyyaml, duckdb, defusedxml
   例:
   ```
   python -m pip install httpx websocket-client pyyaml duckdb defusedxml
   ```
3. プロジェクトルートに `.env` を作成する（自動ウィザードを利用できます、後述）。
4. データディレクトリの準備（デフォルトでは `data/` 配下に DB と PID/flag ファイルを作成します）。
   - 必要に応じて `DUCKDB_PATH` / `SQLITE_PATH` を .env で指定してください。

※ 注意: `.env` は決して Git にコミットしないでください（config_setup の出力にも警告が入っています）。

## 環境変数（主要）
必須:
- JQUANTS_REFRESH_TOKEN — J-Quants API 用リフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API パスワード

よく使う任意 / 既定値:
- KABUSYS_ENV — 実行環境: `development` / `paper_trading` / `live`（デフォルト: development）
- DUCKDB_PATH — DuckDB ファイル（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視 DB（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — paper_trading 用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- KABU_API_BASE_URL — kabu station API のベース URL
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — 本番アラート用（任意）
- PAPER_FILL_MODE — paper_trading 用のモック約定動作: `instant` / `partial` / `never` / `reject`
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリア（0/1）

自動ロード挙動:
- OS 環境変数 > `.env.local` > `.env` の順で読み込まれます。
- プロジェクトルートは `.git` または `pyproject.toml` を親階層に探して決定します。
- `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定すると自動ロードを無効化できます（テスト等で便利）。

## 使い方（代表的なコマンド）
- 環境ウィザード（.env 作成）
  ```
  python -m kabusys.config_setup
  ```
  対話式に入力して `.env` を生成します。

- 設定検証（.env と config/*.yaml の存在 / パースを確認）
  ```
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict   # 警告も失敗扱い（exit 1）
  ```

- 実行エンジン起動（通常は systemd 等で管理する想定）
  ```
  python -m kabusys.run_execution
  ```
  - KABUSYS_ENV が `paper_trading` の場合は MockBrokerClient を使い、`PAPER_TRADING_SQLITE_PATH` に発注履歴を記録します。
  - 起動時に `data/stop_requested.flag` が存在すると起動を行わず終了します。
  - 起動中に `data/stop_requested.flag` を作成すると安全に停止します。
  - `KILL_FLAG_PATH`（デフォルト: data/kill.flag）により Kill Switch を管理します。`KILL_FLAG_CLEAR_ON_START=1` を設定すると起動時に自動クリアします（注意: 本番では推奨されません）。

- 監視プロセス起動
  ```
  python -m kabusys.run_monitoring
  ```
  - 環境変数 `MONITOR_POLL_INTERVAL`（秒）でポーリング間隔を上書きできます（デフォルト: 60）。
  - 監視では常に本番 sqlite_path を使用します（環境にかかわらず）。

## example: 最小限の .env（例）
```
KABUSYS_ENV=development
JQUANTS_REFRESH_TOKEN=your_jquants_token_here
KABU_API_PASSWORD=your_kabu_password_here
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
LOG_LEVEL=INFO
```

## 停止・安全機構
- 停止フラグ: data/stop_requested.flag — 存在を検知して監視ループ / 実行ループを終了します。
- Kill Switch: `KILL_FLAG_PATH`（デフォルト data/kill.flag）で外部から即時停止・全注文キャンセルをトリガできます。
- Reconciliation: 再起動時に OrderSent 状態の注文を突合して状態復帰を試みます。

## ディレクトリ構成（主なファイル・モジュールの説明）
- src/kabusys/
  - __init__.py — パッケージ定義、バージョン
  - config.py — 環境変数の自動読み込み・Settings（設定プロパティ）
  - config_setup.py — 対話式 .env ウィザード
  - validate_config.py — 起動前設定検証 CLI（.env + config/*.yaml）
  - run_execution.py — ExecutionEngine 起動スクリプト（本番/ペーパー切替）
  - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト
  - execution/ — 発注関連の主要モジュール
    - broker_api.py — Broker API の Protocol / データモデル / ファクトリ
    - kabu_client.py — kabu station REST & WebSocket 実装
    - mock_client.py — MockBrokerClient（テスト用）
    - broker_factory.py — Settings に基づくクライアント生成
    - order_record.py — 注文状態モデルと遷移検証（純粋ロジック）
    - order_repository.py — SQLite 永続化（orders テーブル）
    - order_manager.py — 外向き注文 API（create/send/sync/cancel）
    - execution_engine.py — ExecutionEngine（シグナル処理 + push ドレイン）
    - reconciler.py — 再起動時のリコンシリエーション
    - risk_manager.py — 3段階リスクガード
    - その他（order_* など）
  - data/ — データ関連のユーティリティ
    - calendar_management.py — JPX カレンダー管理（DuckDB）
    - news_collector.py — RSS ニュース収集・前処理
    - （jquants_client 等が別ファイルで存在する前提）
  - monitoring/ — 監視 DB / SystemMonitor（run_monitoring から利用）
  - utils/ — ロギングセットアップ、プロセス優先度設定など補助ユーティリティ

（上記は主要ファイルを抜粋した構成です。詳細は src/kabusys 配下の各モジュールを参照してください）

## 開発上の注意事項
- 本番接続（KABUSYS_ENV=live）時は設定ミスが重大な影響を及ぼすため、validate_config の実行を強く推奨します。
- `.env` のプレースホルダ（例: your_value や *_here）をそのままにしないでください。validate_config はプレースホルダ値を警告します。
- DB 周り（SQLite / DuckDB）はファイルベースなのでバックアップ・権限に注意してください。
- 実ネット発注実装（KabuStationClient の live 運用）にはローカルの kabu station アプリやネットワーク設定、trade パスワード等の準備が必要です。現状、BrokerClientFactory は live の実装を未実装・警告している箇所があります（ソース参照）。

## テスト・ローカル検証
- `paper_trading`（または `development`）であれば MockBrokerClient を利用して発注フローをローカルで検証できます。
- Mock では `PAPER_FILL_MODE` を `instant`, `partial`, `never`, `reject` で挙動を切替可能です。
- ExecutionEngine の run_session はテスト時に内部メソッド（_process_signals / _drain_push_queue）を直接呼ぶことで時間依存を避けた単体テストが可能です。

---

README はこのリポジトリ内の実装（src/kabusys 以下）を簡潔にまとめたものです。詳細な実装・追加機能は各モジュールの docstring を参照してください。必要であれば、README にサンプル .env ファイル、systemd ユニット例、データベース初期化手順（init_orders_db / init_monitoring_db の呼び出し方法）などを追加で追記できます。どの情報が必要か教えてください。