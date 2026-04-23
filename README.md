# KabuSys

日本株自動売買システム（KabuSys）のリポジトリ用 README。  
この README はコードベースから抽出した主要な機能・使い方・セットアップ手順・ディレクトリ構成を日本語でまとめたものです。

---

## プロジェクト概要

KabuSys は日本株向けの自動売買基盤です。  
主な責務は次のとおりです。

- シグナルに基づく発注（ExecutionEngine）
- 発注の永続化と状態管理（SQLite）
- ブローカー API 抽象化（kabuステーション実装 / Mock 実装）
- リスクガード（3段階：Signal / Execution / Metrics）
- 起動時のリコンシリエーション（リカバリ）
- 監視用ループ（SystemMonitor）
- データ基盤まわり（DuckDB を用いたシグナル・カレンダ管理・ニュース収集）
- 環境設定ウィザード・設定検証ツール

設計方針として、ブローカー呼び出し層は純粋に API を扱い、永続化・ビジネスロジックは別モジュールに分離されています。paper_trading（ペーパートレード）モードは MockBrokerClient を用いて本番 DB と分離して動作します。

---

## 主な機能一覧

- 環境設定ウィザード（.env の対話式生成）
  - `python -m kabusys.config_setup`
- 起動前の設定検証 CLI（.env と config/*.yaml をチェック）
  - `python -m kabusys.validate_config [--strict]`
- ExecutionEngine（シグナル読み取り → 発注 → WebSocket プッシュ処理）
  - `python -m kabusys.run_execution`
- 監視プロセス（SystemMonitor のポーリングループ）
  - `python -m kabusys.run_monitoring`
- ブローカー API の抽象化（BrokerAPIProtocol）
  - MockBrokerClient（テスト用、fill_mode 等を指定可能）
  - KabuStationClient（kabuステーション REST API 実装）
- 注文状態管理（OrderRecord：状態遷移の検証）
- 注文永続化（OrderRepository：SQLite ベース）
- リスク管理（RiskManager：Gate1/2/3）
- 起動時リコンシリエーション（Reconciler）
- データ系ユーティリティ（市場カレンダー、RSS ニュース収集など）

---

## 必要な環境変数（主要）

必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

推奨 / 任意（主要なもの）:
- KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
- DUCKDB_PATH — デフォルト: data/kabusys.duckdb
- SQLITE_PATH — デフォルト: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH — デフォルト: data/paper_trading.db（paper_trading 用）
- LOG_LEVEL (DEBUG/INFO/WARNING/ERROR/CRITICAL) — デフォルト: INFO
- KABU_API_BASE_URL — kabuステーション API ベース URL（例: http://localhost:18080/kabusapi）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — 本番でのアラート用（任意）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（0/1）

注：
- .env と .env.local は自動読み込みされます（OS 環境変数 > .env.local > .env）。
- 自動読み込みを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

---

## 依存関係（例）

（requirements.txt が無い場合は次を最低限用意してください）
- Python 3.10+
- duckdb
- httpx
- websocket-client
- PyYAML（validate_config の YAML 検証に必要。無くても動作しますが警告になります）
- defusedxml
- その他標準ライブラリ（sqlite3 等）

インストール例:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb httpx websocket-client pyyaml defusedxml
# または (プロジェクトに requirements.txt があれば)
# pip install -r requirements.txt
```

---

## セットアップ手順（基本）

1. リポジトリをクローンし、仮想環境を切る
2. 必要なパッケージをインストール（上記参照）
3. 環境変数を設定
   - 対話式で .env を作る:
     - `python -m kabusys.config_setup`
   - または手動で .env を作成（必須変数は JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD）
4. 設定検証:
   - `python -m kabusys.validate_config`
   - 警告も失敗扱いにしたい場合: `python -m kabusys.validate_config --strict`
5. 実行
   - 監視: `python -m kabusys.run_monitoring`
   - 実行エンジン: `python -m kabusys.run_execution`

注意:
- paper_trading モードでは MockBrokerClient が使われ、監視用 DB（PAPER_TRADING_SQLITE_PATH）に分離して書き込みます。
- KABUSYS_ENV=live のクライアントは現在未実装（BrokerClientFactory は NotImplementedError を投げます）。本番運用は将来の実装に依存します。

---

## 使い方（コマンド例）

- .env の作成（対話式ウィザード）
  ```bash
  python -m kabusys.config_setup
  ```

- 設定検証
  ```bash
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- 実行エンジン（セッション実行）
  ```bash
  # 例: ペーパートレードで起動
  export KABUSYS_ENV=paper_trading
  python -m kabusys.run_execution
  ```

- 監視ループ起動（ポーリング間隔を上書き）
  ```bash
  export MONITOR_POLL_INTERVAL=30
  python -m kabusys.run_monitoring
  ```

停止制御:
- 停止フラグファイル: `<project_root>/data/stop_requested.flag` を作るとループは終了します。
- kill.flag: `KILL_FLAG_PATH`（デフォルト: data/kill.flag）が存在すると発注ループは kill スイッチを発動します。起動時に `KILL_FLAG_CLEAR_ON_START=1` を設定すると自動でクリアして起動します（注意：本番では0推奨）。

---

## 設定のポイント / 注意点

- KABUSYS_ENV の有効値は `development`, `paper_trading`, `live`。`live` は注意喚起（本番）であり、いくつかの追加チェックが行われます（LINE 通知設定など）。
- `JQUANTS_REFRESH_TOKEN` と `KABU_API_PASSWORD` は必須です。未設定だと起動や Settings プロパティ参照時にエラーになります。
- SQLite / DuckDB のパスはデフォルトで `data/` 配下に配置されます。親ディレクトリが存在しない場合は起動時に自動作成されることがありますが、事前に作成しておくと安全です。
- validate_config は PyYAML がある場合は `config/*.yaml` のパース検証も行います。ない場合はパース検証をスキップして警告を出します。
- ExecutionEngine は次の時間帯に合わせたフローを持ちます（例: 8:50 にシグナル処理開始、9:10 発注締切、15:30 市場クローズ）。テストでは個別メソッドを呼んで動作確認できます。

---

## 主要ファイル / ディレクトリ構成

以下は主要なソース構成（抜粋）です。プロジェクトルートは `src/kabusys` を想定しています。

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数・設定読み込みロジック（.env 自動ロード含む）
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 起動前の設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリング起動スクリプト
  - execution/
    - __init__.py
    - broker_api.py          — BrokerAPI の Protocol / データモデル / ファクトリ
    - broker_factory.py      — Settings に応じてクライアントを作る
    - kabu_client.py         — kabuステーション REST API 実装
    - mock_client.py         — MockBrokerClient（テスト用）
    - execution_engine.py    — ExecutionEngine（シグナル処理・push ドレイン等）
    - order_record.py        — OrderRecord（状態遷移ロジック）
    - order_repository.py    — Order の SQLite 永続化層
    - order_manager.py       — OrderManager（外向き API：作成・送信・同期・キャンセル）
    - reconciler.py          — 起動時リコンシリエーション
    - risk_manager.py        — RiskManager（Gate1/2/3）
  - data/
    - calendar_management.py — マーケットカレンダー管理（DuckDB）
    - news_collector.py      — RSS ニュース収集（DuckDB へ保存）
    - jquants_client.py      — （参照）J-Quants API 用クライアント（実装ファイルが存在）
  - monitoring/
    - monitoring_db.py      — 監視 DB 初期化 / 書き込み
    - system_monitor.py     — SystemMonitor（ポーリング処理）
  - utils/
    - logging_setup.py      — ロギング設定ユーティリティ
    - process_priority.py   — プロセス優先度設定ユーティリティ

備考:
- `scripts/generate_config.py` のようなスクリプトが参照されており（config YAML 生成）、存在すれば config/*.yaml を生成できます（validate_config の警告メッセージ参照）。
- 実運用では `data/` ディレクトリ配下のファイル（DB・PID・flag）アクセス権に注意してください。

---

## 開発 / テストに関する補足

- MockBrokerClient により、kabuステーションなしで発注フローのユニット・統合テストが可能です。`paper_trading` または `development` では自動的に Mock が選択されます。
- OrderRecord は状態遷移の検証を内包しており、不正な遷移を検知して例外を送出します。OrderRepository はデータベース操作のみを担当します。
- 起動時のリコンシリエーション（Reconciler）は OrderSent の不確定注文をブローカーと同期し、ポジション差分を検出・ログ出力します。

---

## よくある操作手順（例：ローカルでペーパートレードを試す）

1. 仮想環境作成・依存インストール
2. .env を作成（対話式ウィザード）
   ```
   python -m kabusys.config_setup
   ```
3. 設定検証
   ```
   python -m kabusys.validate_config
   ```
4. 実行エンジン起動（別ターミナルで監視も起動可能）
   ```
   export KABUSYS_ENV=paper_trading
   python -m kabusys.run_execution
   ```

---

もし README に追加したい情報（例：実行ログのサンプル、詳細な設定例、CI の設定方法、requirements.txt の中身など）があれば教えてください。README を拡張して具体的なチュートリアルや運用ガイドを追記します。