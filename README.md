# KabuSys

日本株自動売買システムのコアライブラリ（開発中）

このリポジトリは、kabuステーション（ローカル API）や J-Quants 等を利用した自動売買エンジンの主要コンポーネントを含みます。開発 / ペーパートレード / 本番（live）を想定した設定管理、発注エンジン、モニタ、監視・リコンシリエーション、ニュース収集、マーケットカレンダー管理などを提供します。

基本方針：
- DB 操作（SQLite / DuckDB）は永続層に限定
- ブローカークライアントは抽象化（Mock 実装あり）
- 起動時に設定検証とリコンシリエーションを実施して安全に再起動可能にする

---

## 主な機能一覧

- 環境設定ウィザード (.env) の対話式生成（config_setup.py）
- 起動前の設定検証 CLI（必須環境変数や YAML 設定ファイルのチェック）（validate_config.py）
- ExecutionEngine：シグナル取得 → Gate（リスクチェック） → 発注 → push ドレインのセッション実行
- Broker クライアント層（KabuStationClient、MockBrokerClient、ファクトリ）
- Order 管理：OrderRecord（状態遷移）、OrderRepository（SQLite 永続化）、OrderManager（送信 / 同期 / キャンセル）
- Reconciler：クラッシュ復旧のための OrderSent 照合とポジション差分検出
- RiskManager：Gate1/2/3（余力・重複・ポジション上限、レート制限/サーキットブレーカー、ドローダウン監視）
- Monitoring 用ループ（run_monitoring.py）
- マーケットカレンダー管理（DuckDB ベース、J-Quants 連携想定）
- ニュース収集モジュール（RSS 収集・正規化・保存）

---

## 必要条件（推奨）

- Python 3.10+
- pip 等
- ランタイム依存（使用機能に応じて）:
  - duckdb
  - httpx
  - websocket-client
  - defusedxml
  - PyYAML（YAML 検証を有効にする場合）
- 標準ライブラリ: sqlite3, logging, threading, pathlib 等

インストール例:
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb httpx websocket-client defusedxml PyYAML
```

（プロジェクト側で requirements.txt がある場合はそれを利用してください）

---

## セットアップ手順

1. リポジトリを取得し、仮想環境を作成して依存関係をインストールする。

2. .env の作成
   - 対話式ウィザードを使う（推奨）:
     ```
     python -m kabusys.config_setup
     ```
     ウィザードは .env（デフォルトはプロジェクトルート/.env）を作成／更新します。シークレット項目はマスク表示されます。
   - 手動で作成する場合は .env.example を参考にしてください（※リポジトリに含めないこと）。

3. 設定の自動読み込み
   - 起動時、OS 環境変数 > .env.local > .env の順で読み込まれます。
   - テスト等で自動読み込みを無効化するには環境変数を設定:
     ```
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```

4. 設定検証
   - .env を作成したら起動前に検証を行います:
     ```
     python -m kabusys.validate_config
     ```
   - 警告もエラー扱いにする厳格モード:
     ```
     python -m kabusys.validate_config --strict
     ```

5. DB 初期化
   - Execution/Monitoring が使用する SQLite / DuckDB の親ディレクトリは自動作成されることがありますが、アクセス権などに注意してください。
   - monitoring の実行は監視用 SQLite を使用します（設定によりパスを指定可能）。

---

## 環境変数（主要）

必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

よく使うオプション（デフォルト値があるものも含む）:
- KABUSYS_ENV: development | paper_trading | live （デフォルト: development）
- DUCKDB_PATH: data/kabusys.duckdb
- SQLITE_PATH: data/monitoring.db
- LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL
- KABU_API_BASE_URL: http://localhost:18080/kabusapi
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID（本番アラート用）
- PAPER_FILL_MODE: instant | partial | never | reject（paper_trading 用）
- PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
- PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START
- MONITOR_POLL_INTERVAL（run_monitoring 用、秒）

設定の自動ロード順:
- OS 環境変数（最優先）
- .env.local（存在すれば .env を上書き）
- .env

KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化できます。

注意:
- .env は絶対に Git 管理下にコミットしないでください。
- validate_config は config/*.yaml（system_config.yaml 等）の存在や YAML パースも検証します。PyYAML 未導入時は YAML 検証をスキップして警告を出します。

---

## 使い方（主なエントリポイント）

- 環境設定ウィザード（.env の作成／更新）
  ```
  python -m kabusys.config_setup
  ```

- 設定検証（起動前の安全確認）
  ```
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- 実行エンジン起動（取引セッション）
  ```
  python -m kabusys.run_execution
  ```
  - KABUSYS_ENV が `paper_trading` または `development` の場合、MockBrokerClient を使用（本番 API への送信は行われません）。
  - `live` は現時点で未実装（BrokerClientFactory が NotImplementedError を投げます）。

- 監視ループ起動（SystemMonitor をポーリング）
  ```
  python -m kabusys.run_monitoring
  ```
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL（秒）で上書き可能（デフォルト 60 秒）。
  - Monitoring は環境にかかわらず本番 sqlite_path を用います（監視 DB は共有される設計）。

停止方法:
- 実行中のプロセスはプロジェクト内 data/stop_requested.flag の作成で優雅に停止できます。
- kill.flag（デフォルト data/kill.flag）によって ExecutionEngine は起動を拒否 / kill switch を発動します。KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に自動クリアできます（本番では推奨されません）。

---

## ディレクトリ構成（主要ファイル）

（プロジェクトルート）/
- src/kabusys/
  - __init__.py
  - config.py                — 環境変数読み込みと Settings クラス（自動ロード機能）
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 起動前設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor 起動スクリプト
  - execution/
    - __init__.py
    - broker_api.py          — Broker API の Protocol / データモデル / ファクトリ
    - broker_factory.py      — Settings に基づくクライアント生成
    - kabu_client.py         — kabuステーション実装（httpx）
    - mock_client.py         — テスト用モック実装
    - order_record.py        — Order の状態遷移ロジック（純粋ビジネスロジック）
    - order_repository.py    — SQLite 永続化
    - order_manager.py       — 外向け Order API（create/send/sync/cancel）
    - execution_engine.py    — 発注エンジン本体（シグナル処理 / push ドレイン / kill switch）
    - reconciler.py          — リコンシリエーション / 再起動復旧
    - risk_manager.py        — Gate1/2/3 リスク制御
  - monitoring/
    - monitoring_db.py       — 監視 DB 初期化 / 書き込み（使用箇所あり）
    - system_monitor.py      — SystemMonitor 実装（別ファイル）
  - data/
    - calendar_management.py — マーケットカレンダー管理（DuckDB）
    - news_collector.py      — RSS ニュース収集
  - utils/
    - logging_setup.py       — ロギング設定ユーティリティ
    - process_priority.py    — プロセス優先度設定ユーティリティ

付記:
- config/*.yaml（system_config.yaml, data_config.yaml, strategy_config.yaml, risk_config.yaml, execution_config.yaml, monitoring_config.yaml）は設定ファイル群。存在しない場合は警告が出ます（validate_config 参照）。生成スクリプト（python scripts/generate_config.py）があればそれで作成可能というメッセージが出ます。

---

## 実装上の注意 / トラブルシュート

- PyYAML 未インストール時、validate_config は YAML 内容検証をスキップして警告を出します。YAML 検証を有効にするには PyYAML をインストールしてください。
- run_monitoring は MONITOR_POLL_INTERVAL を正の整数で指定します。0 以下や無効な値はデフォルト（60秒）にフォールバックします。
- ExecutionEngine 実行時、既に data/stop_requested.flag が存在すると起動せず終了します。
- 本番（KABUSYS_ENV=live）では LINE 関連設定や Kill Switch 設定のチェックが追加で行われます（validate_config の警告）。
- MockBrokerClient の PAPER_FILL_MODE を使うことでテスト時の約定動作を制御できます（instant/partial/never/reject）。

---

## 開発メモ

- Order の状態遷移は order_record.OrderState と Allowed transitions に厳密に従います。OrderManager ではクラッシュ許容性のため 2 相コミット風の永続化順序を採用しています（OrderSent の永続化 → broker 呼び出し → broker_order_id の永続化 → OrderAccepted 等）。
- Reconciler は再起動時に OrderSent（不確定）注文を突合し、ポジション差分を検出してログを残します。
- RiskManager はトークンバケツ（レート制限）、サーキットブレーカー、ドローダウン監視などを内包します。

---

この README はコードベースの主要点を抜粋した概要です。詳細は各モジュールの docstring / コメントを参照してください。質問や補足が必要であれば教えてください。