# KabuSys

日本株自動売買システム（KabuSys）リポジトリの README。  
このドキュメントはコードベースから主要なコンポーネント・使い方・セットアップ手順をまとめたものです。

> バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株の自動売買システム向けライブラリ／実行環境です。  
主な目的は以下のとおりです。

- シグナルに基づく発注エンジン（ExecutionEngine）
- ブローカー API 抽象化（kabu station 実装＋テスト用の Mock）
- 発注ライフサイクル（OrderRecord / OrderRepository / OrderManager）
- 起動時リコンシリエーション（Reconciler）
- 3段階リスクガード（RiskManager: Gate1〜3）
- マーケットカレンダー管理、ニュース収集などデータ処理モジュール
- 設定ウィザード、起動前設定検証 CLI、監視プロセス用スクリプト

設計上、DB（SQLite / DuckDB）はローカルファイルベースで、paper_trading（ペーパートレード）モードでは本番 DB と分離して動作します。

---

## 機能一覧

- 環境変数ベースの設定管理（.env / .env.local の自動読み込み）
- 対話式 .env 生成ウィザード（kabusys.config_setup）
- 起動前設定検証ツール（kabusys.validate_config）
  - 必須環境変数チェック、YAML ファイルの存在・パース検証（PyYAML がある場合）
  - KABUSYS_ENV の妥当性チェック（development / paper_trading / live）
- ExecutionEngine：シグナル取得 → リスクガード → 発注 → push ドレイン（WebSocket）処理
- Broker クライアント抽象化（実装: KabuStationClient、MockBrokerClient）
- Order の永続化（SQLite）と状態遷移ロジック（OrderRecord）
- 起動時リコンシリエーション（OrderSent の突合）
- RiskManager：余力、重複、ポジション上限、レート制限、サーキットブレーカー、ドローダウン監視
- Monitoring 用スクリプト（run_monitoring）: SystemMonitor のポーリングループ
- Data モジュール: カレンダー管理（JPX 営業日），ニュース収集（RSS）

---

## 前提 / 依存ライブラリ（主なもの）

必要な主なパッケージ（環境によって追加で必要になる場合があります）:

- Python 3.9+
- duckdb
- httpx
- websocket-client
- defusedxml
- PyYAML（設定検証で YAML 内容チェックをする場合に必要）
- その他標準ライブラリ（sqlite3, logging, threading, etc.）

インストール例（仮想環境推奨）:

```
python -m venv .venv
source .venv/bin/activate
pip install duckdb httpx websocket-client defusedxml PyYAML
```

（プロジェクトに requirements.txt / pyproject.toml があればそちらを使ってください）

---

## セットアップ手順

1. リポジトリをクローンしてプロジェクトルートへ移動。

2. 仮想環境を作成して依存パッケージをインストール（上記参照）。

3. .env の作成
   - 対話式ウィザードを使う（推奨）:

     ```
     python -m kabusys.config_setup
     ```

     ウィザードは .env の既存値を読み込みつつ、対話で設定を更新・生成します。シークレット項目（J-Quants トークンや kabu API パスワード）は入力時にマスク表示されます。

   - もしくは手動で `.env` を作成。最低限必要な環境変数:
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
     - KABUSYS_ENV（development / paper_trading / live、デフォルト: development）
     - その他（オプション）: DUCKDB_PATH, SQLITE_PATH, LOG_LEVEL, KABU_API_BASE_URL, LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID, など

4. 設定検証（起動前に推奨）

```
python -m kabusys.validate_config
# 警告も失敗扱いにする場合
python -m kabusys.validate_config --strict
```

validate_config は .env と config/*.yaml（存在する場合）をチェックします。PyYAML が未インストールの場合 YAML の内容検証はスキップされます。

5. DB 初期化
   - 実行スクリプト（run_execution/run_monitoring）起動時に必要テーブルを初期化するコードが含まれているため基本的には手動での初期化不要です（ただし環境に応じて事前に data/ ディレクトリを作るとよい）。

---

## 使い方

主要な CLI / 実行スクリプト:

- 環境設定ウィザード（.env 作成／更新）
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- 実行エンジン起動（実際の発注処理を行うプロセス）
  ```
  python -m kabusys.run_execution
  ```
  - KABUSYS_ENV が `paper_trading` の場合は MockBrokerClient を使用し `data/paper_trading.db` に記録して本番 DB と分離します。
  - 起動時に `data/kill.flag`（kill.flag）ファイルが存在すると、KILL_FLAG_CLEAR_ON_START の設定によっては起動を拒否します。

- 監視プロセス起動（SystemMonitor のポーリング）
  ```
  python -m kabusys.run_monitoring
  ```
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を変更可能（デフォルト: 60）。
  - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用します。

重要な環境変数（抜粋）:

- 必須
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD

- 主要オプション
  - KABUSYS_ENV: development | paper_trading | live
  - DUCKDB_PATH: デフォルト data/kabusys.duckdb
  - SQLITE_PATH: デフォルト data/monitoring.db
  - PAPER_TRADING_SQLITE_PATH: paper_trading 用 DB（デフォルト data/paper_trading.db）
  - LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL
  - KILL_FLAG_CLEAR_ON_START: 0 | 1
  - MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒）
  - PAPER_FILL_MODE: instant | partial | never | reject（paper_trading の挙動）

サンプル minimal .env（参考）

```
JQUANTS_REFRESH_TOKEN=your_token_here
KABU_API_PASSWORD=your_kabu_password
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
LOG_LEVEL=INFO
KILL_FLAG_CLEAR_ON_START=0
```

---

## ディレクトリ構成

以下は `src/kabusys` の主要ファイル／モジュール構成（抜粋）と簡単な説明です。

- src/kabusys/
  - __init__.py
    - パッケージ定義（バージョン等）
  - config.py
    - 環境変数の自動読み込み（.env / .env.local）
    - Settings クラス（各種設定プロパティ）
  - config_setup.py
    - 対話式 .env ウィザード（python -m kabusys.config_setup）
  - validate_config.py
    - 起動前設定検証 CLI（python -m kabusys.validate_config）
  - run_execution.py
    - ExecutionEngine 起動スクリプト（発注プロセス）
  - run_monitoring.py
    - SystemMonitor ポーリングループ起動スクリプト
  - execution/
    - __init__.py
      - execution 層のエクスポート
    - broker_api.py
      - BrokerAPI のデータモデル、Protocol、例外、ファクトリ
    - kabu_client.py
      - kabu station REST API クライアント（HTTP + WebSocket）
    - mock_client.py
      - MockBrokerClient（テスト・ペーパートレード用）
    - broker_factory.py
      - Settings に基づくブローカーファクトリ
    - execution_engine.py
      - ExecutionEngine（信号処理、WebSocket ドレイン、セッション管理）
    - order_record.py
      - OrderRecord と状態遷移ロジック（純粋ビジネスロジック）
    - order_repository.py
      - SQLite による永続化層（orders テーブルの初期化含む）
    - order_manager.py
      - OrderRecord + OrderRepository + Broker を組み合わせた外向き API
    - reconciler.py
      - 起動時リコンシリエーション（OrderSent の突合、ポジション照合）
    - risk_manager.py
      - 3 段階リスクガード（Gate1〜3）
  - data/
    - calendar_management.py
      - JPX カレンダー管理・営業日判定・夜間バッチ
    - news_collector.py
      - RSS 収集・正規化・DB 保存（セキュリティ対策あり）
  - monitoring/
    - monitoring_db.py (参照のみ。コード内で使用)
    - system_monitor.py (参照のみ。コード内で使用)
  - utils/
    - logging_setup.py
    - process_priority.py
    - （その他ユーティリティ）

data/ ディレクトリ（ランタイム）
- data/kabusys.duckdb (DuckDB データベース、デフォルト)
- data/monitoring.db (SQLite 監視 DB、デフォルト)
- data/paper_trading.db (ペーパートレード用 SQLite DB)
- data/execution.pid (PID ファイル)
- data/kill.flag (kill スイッチファイル)
- data/stop_requested.flag (監視ループ停止用フラグなど)

---

## 運用上の注意点

- KABUSYS_ENV=live を設定すると本番扱いになります。validate_config は live 時に追加警告を出します（LINE 通知設定の確認、KILL_FLAG_CLEAR_ON_START の警告など）。
- kill.flag による安全措置:
  - 起動前に kill.flag が存在すると起動を拒否します（KILL_FLAG_CLEAR_ON_START=1 の場合は起動時に自動でクリア可能）。
  - 実行中に kill.flag を検出すると ExecutionEngine は kill_switch を発動し全 active 注文をキャンセルします。
- paper_trading モードでは MockBrokerClient を使用して本番データと完全に分離されます。PAPER_FILL_MODE で約定振る舞いを制御可能。

---

## 開発／テストに関する補足

- MockBrokerClient は fill_mode（instant/partial/never/reject）を提供しており、テスト時に実際の API 呼び出しなしで挙動確認ができます。
- ExecutionEngine.run_session はセッション時間（発注時間帯）に合わせた挙動を実装していますが、ユニットテストでは内部メソッド（_process_signals, _drain_push_queue 等）を直接呼んで検証することが想定されています。
- .env の自動読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化できます（テストで環境依存を排除する際に有用）。

---

この README はコードベースに含まれる実装・コメントを元に作成しています。個別モジュールの詳細（API 仕様や関数説明）はソース内の docstring / コメントを参照してください。質問や追加で README に含めてほしい情報があれば教えてください。