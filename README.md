# KabuSys

日本株向け自動売買システムの軽量実装（ライブラリ兼デーモン起動スクリプト群）

バージョン: 0.1.0

---

## 概要

KabuSys は、kabuステーション（ローカルで動作するブローカー API）を経由して日本株の自動売買を行うためのコンポーネント群です。  
主な機能は発注エンジン（ExecutionEngine）、リスク管理（RiskManager）、注文永続化（SQLite）、監視（Monitoring）、および各種ユーティリティ（カレンダー管理、ニュース収集など）です。開発 / テスト用にブローカーのモック（MockBrokerClient）を備えており、Paper Trading（本番と分離したDB）モードで安全に検証できます。

このリポジトリには、設定ウィザード、設定検証ツール、起動用のスクリプトが含まれます。

---

## 機能一覧

- 環境設定
  - 対話式ウィザードで `.env` を生成・更新（kabusys.config_setup）
  - 起動前に必須環境変数・設定ファイルを検証（kabusys.validate_config）
- 実行（Execution）
  - Signal Queue 型の発注エンジン（ExecutionEngine）
  - Order 管理（OrderRecord / OrderRepository / OrderManager）
  - リスクガード（三段階: Gate1/2/3）およびサーキットブレーカー（RiskManager）
  - ブローカークライアント実装
    - MockBrokerClient（テスト/開発用）
    - KabuStationClient（kabuステーション REST API クライアント）
  - 起動時リコンシリエーション（Reconciler）
- 監視（Monitoring）
  - SystemMonitor 用ループ（run_monitoring）
  - 監視 DB（SQLite）へのログ記録
- データ関連
  - JPXカレンダー管理（duckdb ベース）: 営業日判定・次営業日など
  - ニュース収集モジュール（RSS 収集、正規化、raw_news 保存）
- ユーティリティ
  - 設定読み込み（.env 自動読み込みロジック）
  - ロギングセットアップ、プロセス優先度調整など

---

## 必要条件

- Python 3.10 以上（PEP 604 の型記法、型ヒントを使用）
- 推奨 Python パッケージ（環境に応じてインストール）:
  - duckdb
  - httpx
  - websocket-client
  - defusedxml
  - PyYAML（YAML 検証を行う場合）
- SQLite（標準ライブラリの sqlite3 を利用）

インストール例:
```
python -m pip install duckdb httpx websocket-client defusedxml PyYAML
```

（requirements.txt がある場合は `pip install -r requirements.txt` を使用してください）

---

## セットアップ手順

1. リポジトリをクローンし、Python 環境を準備する
   - 推奨: 仮想環境を作成して依存をインストールする
2. `.env` の作成
   - 対話式ウィザードを使う（推奨）
     ```
     python -m kabusys.config_setup
     ```
     ウィザードは `.env`（デフォルトプロジェクトルート配下）を生成または更新します。シークレットはマスクして表示されます。
   - 手動で作成する場合は `.env.example` を参考にしてください（プロジェクト内に存在する場合）。
   - `.env` は絶対に Git にコミットしないでください（ウィザードのヘッダにも注意書きあり）。
3. 設定の検証
   - .env の内容や config/*.yaml を検証します:
     ```
     python -m kabusys.validate_config
     ```
   - 警告も FAIL として扱う場合:
     ```
     python -m kabusys.validate_config --strict
     ```
   - PyYAML がインストールされていない場合は YAML 内容の検証をスキップします（警告が出ます）。
4. データディレクトリの作成
   - デフォルトでは `data/` 下に DB や PID/フラグファイルが作られます。必要なら手動で作成してください。
     ```
     mkdir -p data
     ```
5. 実行用設定
   - Paper Trading（本番と分離）を使う場合は `KABUSYS_ENV=paper_trading` を設定してください。development でも MockBroker が使われます。live は現状未実装（BrokerFactory が NotImplementedError を投げます）。

---

## 主要な環境変数

（validate_config と config_setup の定義を基に抜粋）

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants API のリフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API のパスワード

任意 / 推奨:
- KABUSYS_ENV — 実行環境 (development / paper_trading / live)（デフォルト: development）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite DB（デフォルト: data/monitoring.db）
- LOG_LEVEL — ログレベル（DEBUG / INFO / WARNING / ERROR / CRITICAL）（デフォルト: INFO）
- KABU_API_BASE_URL — kabu station のベース URL（デフォルト: http://localhost:18080/kabusapi）
- LINE_CHANNEL_ACCESS_TOKEN — LINE 通知用トークン（任意）
- LINE_USER_ID — LINE 通知受信者 ID（任意）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（0/1、デフォルト 0）
- MONITOR_POLL_INTERVAL — monitoring のポーリング間隔（秒、デフォルト 60）

その他（ExecutionEngine / RiskManager / Paper Trading などの詳細な設定はコード内 Settings を参照してください）。

自動 .env ロード:
- OS 環境変数 > .env.local > .env の順に読み込みます。
- 自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

---

## 使い方（起動例）

- 設定ウィザード
  ```
  python -m kabusys.config_setup
  ```

- 設定の検証
  ```
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- 実行エンジン（発注）
  - 開発 / テスト（MockBroker を使用）
    ```
    export KABUSYS_ENV=development
    python -m kabusys.run_execution
    ```
  - ペーパートレード（MockBroker・専用 SQLite を使用）
    ```
    export KABUSYS_ENV=paper_trading
    python -m kabusys.run_execution
    ```
  - 注意: live（本番）モードの Live broker client は未実装です（起動時にエラーになります）。

- 監視ループ
  ```
  python -m kabusys.run_monitoring
  ```
  - ポーリング間隔を変更するには:
    ```
    export MONITOR_POLL_INTERVAL=30
    python -m kabusys.run_monitoring
    ```

- 停止制御
  - 停止フラグ: プロジェクトルートの `data/stop_requested.flag` を作成すると、ループが検知して安全終了します。
  - キルスイッチ: `KILL_FLAG_PATH`（デフォルト data/kill.flag）により起動拒否や即時停止の制御を行います。

---

## 注意事項 / 運用上のヒント

- `.env` は機密情報を含むため、決して VCS にコミットしないでください（config_setup のヘッダにも注記あり）。
- `KABUSYS_ENV=live` を使用する場合は、LINE 通知設定など重要な監視設定の漏れが無いか validate_config で確認してください。validate_config は live 時に追加警告を出します。
- Paper Trading（`paper_trading`）では `PAPER_TRADING_SQLITE_PATH` により専用の SQLite を使用し、本番データと分離します。
- ExecutionEngine は起動時に Reconciler を呼ぶことで、クラッシュ後の OrderSent 状態の復旧を試みます。Order の永続化は SQLite（orders テーブル）で管理されます。
- モック（MockBrokerClient）は複数の fill_mode を持ち、テストシナリオ（instant / partial / never / reject）を再現できます。

---

## ディレクトリ構成（主要ファイル）

ルート: src/kabusys 以下を想定

- src/kabusys/
  - __init__.py  — パッケージ定義（バージョンなど）
  - config.py  — 環境変数の読み込み・Settings クラス（.env 自動ロード含む）
  - config_setup.py  — 対話式 .env ウィザード
  - validate_config.py — 起動前の設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor 起動スクリプト
  - execution/  — 発注関連コンポーネント
    - broker_api.py         — BrokerAPI のデータモデル / Protocol / ファクトリ
    - kabu_client.py        — kabu station REST クライアント（HTTP/WebSocket）
    - mock_client.py        — MockBrokerClient（テスト用）
    - broker_factory.py     — Settings に応じたクライアント生成
    - order_record.py       — Order の状態機械データモデル
    - order_repository.py   — SQLite 永続化層（orders テーブル）
    - order_manager.py      — 発注フローの上位 API（create/send/sync/cancel）
    - execution_engine.py   — ExecutionEngine（シグナル処理 / push drain / kill）
    - reconciler.py         — 起動時リコンシリエーション（OrderSent の突合）
    - risk_manager.py       — Gate1/2/3 等のリスク制御
    - ...（その他補助ファイル）
  - data/  — データ関連モジュール
    - calendar_management.py — 市場カレンダー管理（DuckDB）
    - news_collector.py      — RSS ニュース収集
    - jquants_client.py      — J-Quants 連携（参照される想定）
  - monitoring/ — 監視関連（SystemMonitor, monitoring_db 等）
  - utils/ — ロギング設定やプロセス優先度などのユーティリティ

（上記は主要ファイルの抜粋です。詳細はソースツリーを参照してください）

---

## 参考・補足

- DB 初期化:
  - orders テーブルなどは起動スクリプト内で `init_monitoring_db` / `init_orders_db` などの冪等初期化処理を呼ぶ設計になっています。手動で初期化する必要は通常ありませんが、デバッグ時に直接呼び出すこともできます。
- YAML 設定ファイル:
  - config/*.yaml（system_config.yaml 等）がある場合、validate_config は PyYAML を使ってパース検証を行います。インストールされていない場合は警告を出し検証はスキップされます。
- ログ:
  - ログレベルは `LOG_LEVEL` で制御します。デフォルトは INFO。
- テスト:
  - MockBrokerClient や ExecutionEngine の各コンポーネントは単体テストがしやすいよう分離されています。ユニットテスト作成時は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で自動ロードを無効化すると良いです。

---

必要があれば、README に含めるコマンド例（systemd unit / Dockerfile / CI 用スクリプト）や、より詳細な運用手順（ログローテーション、バックアップ、リリース手順）についても追記します。どの情報を優先して追加しますか？