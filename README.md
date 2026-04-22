# KabuSys

日本株向けの自動売買システム用ライブラリ / 実行フレームワーク (開発中)

---

## プロジェクト概要

KabuSys は、シグナルに基づいて発注を行う Execution エンジン、監視（Monitoring）、カレンダー管理やニュース収集などを備えた日本株自動売買の基盤ライブラリです。  
主要な責務を明確に分離しており、ブローカークライアント実装（kabuステーション実装 / テスト用モック）を差し替えて本番・テスト環境を切り替えられる設計になっています。

主な設計方針：
- ビジネスロジックと永続化/ネットワーク層を分離
- 再起動後の自動復旧（Reconciler）
- 複数段階のリスクガード（Gate1~3）
- .env による設定管理と起動前の設定検証ツール

---

## 機能一覧

- 環境設定ウィザード（.env 作成）: `kabusys.config_setup`
- 設定検証 CLI（.env と config/*.yaml の事前チェック）: `kabusys.validate_config`
- Execution エンジン（シグナル読み込み → 発注 → push ドレイン）: `kabusys.run_execution`
  - KABUSYS_ENV により mock/live を切替（現状 live は未実装、paper_trading / development は MockBrokerClient）
  - 発注フローのクラッシュ耐性（OrderSent 永続化など）
  - リスクガード（Gate1: シグナル・残高・重複・ポジション上限、Gate2: レート制御・CB、Gate3: ドローダウン）
  - Reconciler による起動時の状態同期
- Monitoring（SystemMonitor のポーリング）: `kabusys.run_monitoring`
- データ処理モジュール
  - マーケットカレンダー管理（DuckDB ベース）
  - ニュース収集（RSS 取得・前処理・DB 保存）
- Broker クライアント群
  - MockBrokerClient（テスト用）
  - KabuStationClient（kabuステーション REST / WebSocket 実装）
- SQLite / DuckDB を用いた永続化（orders、monitoring、market_calendar 等）

---

## 必要条件（概略）

- Python 3.9+
- 依存例（プロジェクトにより異なる）：duckdb, httpx, websocket-client, defusedxml, PyYAML（オプション; validate_config の YAML 検証に使用）
- SQLite（Python 標準ライブラリで利用可能）

requirements.txt がある場合はそれに従ってください。開発時は editable install を推奨します。

例:
```
pip install -e .
# または
pip install duckdb httpx websocket-client defusedxml PyYAML
```

PyYAML がない場合、`python -m kabusys.validate_config` 実行時に YAML の内容検証はスキップされますが存在確認は行われます。

---

## セットアップ手順

1. リポジトリをクローン / ダウンロード
2. 仮想環境を作成して有効化（推奨）
   - python -m venv .venv
   - Windows: .venv\Scripts\activate
   - macOS/Linux: source .venv/bin/activate
3. 依存パッケージをインストール
   - 開発中: `pip install -e .`
   - 必要なパッケージだけを入れる場合:
     ```
     pip install duckdb httpx websocket-client defusedxml
     # validate_config の YAML 検証を有効にするなら:
     pip install PyYAML
     ```
4. 初期設定 (.env) を作成
   - 対話式ウィザードを実行:
     ```
     python -m kabusys.config_setup
     ```
   - もしくは手動でプロジェクトルートに `.env` を作成（下記参照）
5. 設定検証を実行
   ```
   python -m kabusys.validate_config
   # 警告も失敗扱いにする:
   python -m kabusys.validate_config --strict
   ```

注意: `.env` は絶対に Git 管理に含めないでください（ウィザードもその旨を警告してファイルを生成します）。

---

## 環境変数（主要なもの）

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants API 用リフレッシュトークン（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）

主要（任意・デフォルトありを含む）:
- KABUSYS_ENV — 実行環境: `development` | `paper_trading` | `live`（デフォルト: development）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite 監視 DB（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL — ログレベル: DEBUG|INFO|WARNING|ERROR|CRITICAL（デフォルト: INFO）
- KABU_API_BASE_URL — kabu station のベース URL（デフォルト: http://localhost:18080/kabusapi）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — 本番時のアラート送信先（任意）
- MONITOR_POLL_INTERVAL — 監視ポーリング間隔（秒、デフォルト 60）
- PID_FILE_PATH — PID ファイルパス（デフォルト: data/execution.pid）
- KILL_FLAG_PATH — kill flag ファイルパス（デフォルト: data/kill.flag）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（0/1、デフォルト 0）
- PAPER_FILL_MODE — paper_trading の fill 動作: instant|partial|never|reject（デフォルト instant）

自動 .env ロード挙動:
- OS 環境変数 > .env.local > .env の順でロードされます。
- テスト等で自動ロードを無効化する場合: `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`

---

## 使い方（主要コマンド）

- 環境設定ウィザード（.env を対話的に作成/更新）
  ```
  python -m kabusys.config_setup
  ```

- 設定検証（起動前に .env と config/*.yaml をチェック）
  ```
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict  # 警告も失敗扱い
  ```

- 実際の Execution エンジンを起動（長時間プロセス）  
  KABUSYS_ENV に応じてモックまたは本番クライアントが選択されます（現状 live 実装未実装）
  ```
  python -m kabusys.run_execution
  ```

- 監視プロセスを起動（SystemMonitor のポーリングループ）
  ```
  python -m kabusys.run_monitoring
  # ポーリング間隔は MONITOR_POLL_INTERVAL 環境変数で上書き可能（秒）
  ```

運用ノート:
- Paper trading（KABUSYS_ENV=paper_trading）は mock ブローカーを使用し、`PAPER_TRADING_SQLITE_PATH` に別 DB を書きます。本番 DB と分離されます。
- Monitoring は環境にかかわらず本番用の `SQLITE_PATH` を使用します（監視データは一貫した場所へ）。

停止制御:
- プロジェクトルート内の `data/stop_requested.flag` を作るとループが検知して終了します。
- `KILL_FLAG_PATH`（デフォルト data/kill.flag）を利用した kill switch 機構があります。`KILL_FLAG_CLEAR_ON_START=1` を設定すると起動時に kill.flag を自動クリアします（本番では 0 を推奨）。

---

## .env の例

以下はウィザードが生成する形式の抜粋例（実運用ではシークレットを実際の値に置き換えてください）。

```
# --- J-Quants API ---
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here

# --- kabuステーション API ---
KABU_API_PASSWORD=your_kabu_password_here
KABU_API_BASE_URL=http://localhost:18080/kabusapi

# --- LINE Messaging API (アラート通知用) ---
LINE_CHANNEL_ACCESS_TOKEN=
LINE_USER_ID=

# --- データベース ---
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db

# --- システム設定 ---
KABUSYS_ENV=development
LOG_LEVEL=INFO

# --- Kill Switch ---
KILL_FLAG_CLEAR_ON_START=0
```

注意: 実際のトークンやパスワードは必ず安全に保管し、Git 等にコミットしないでください。

---

## 典型的な運用フロー

1. `.env` を作成（ウィザード推奨）
2. 設定検証:
   ```
   python -m kabusys.validate_config --strict
   ```
3. 監視プロセスを起動（常駐）
   ```
   python -m kabusys.run_monitoring
   ```
4. 発注プロセスを起動（トレード当日のセッション）
   ```
   python -m kabusys.run_execution
   ```

Reconciliation（再起動時の自動同期）は ExecutionEngine 起動時に自動で走ります（Reconciler）。

---

## ディレクトリ構成（主要ファイル）

簡易ツリー（src/kabusys 以下の主要モジュール）:

- src/kabusys/
  - __init__.py
  - config.py                     — 環境変数ロード / Settings
  - config_setup.py               — .env 作成ウィザード CLI
  - validate_config.py            — 起動前設定検証 CLI
  - run_execution.py              — ExecutionEngine 起動スクリプト
  - run_monitoring.py             — Monitoring 起動スクリプト
  - execution/
    - __init__.py
    - broker_api.py               — Broker API モデル / Protocol / ファクトリ
    - broker_factory.py           — Settings に基づくブローカー生成
    - kabu_client.py              — kabuステーション REST/WebSocket クライアント
    - mock_client.py              — テスト用モッククライアント
    - execution_engine.py         — 発注エンジン（セッション制御）
    - order_record.py             — OrderState と OrderRecord（状態遷移ロジック）
    - order_repository.py         — SQLite 永続化レイヤ
    - order_manager.py            — 外向きの発注 / sync / cancel API
    - reconciler.py               — リコンシリエーション（起動時復旧）
    - risk_manager.py             — Gate1~3 のリスク制御
  - data/
    - calendar_management.py      — マーケットカレンダー管理（DuckDB）
    - news_collector.py           — RSS ニュース収集（前処理）
    - jquants_client.py           — J-Quants API クライアント（想定）
  - monitoring/
    - monitoring_db.py            — 監視 DB 初期化・ロギング
    - system_monitor.py           — システム監視ロジック
  - utils/
    - logging_setup.py            — ログ設定ユーティリティ
    - process_priority.py         — プロセス優先度設定ユーティリティ
  - その他：scripts、config/*.yaml（テンプレート設定ファイルなど）

各モジュールは README や docstring に設計意図や注意点が記載されています。詳細は該当ファイルの docstring を参照してください。

---

## 開発者向けメモ / トラブルシューティング

- validate_config で YAML のパースエラーが出る場合は PyYAML のインストールを確認してください。
- KABUSYS_ENV=live を使用する場合は十分に設定を確認してください（LINE 通知などの本番向け設定）。
- ExecutionEngine は PID ファイルと kill.flag を利用します。残留する PID/flag によって起動拒否される場合があるので注意してください。
- Paper trading は mock ブローカーを用いるため実際の資金移動は発生しません。実運用前にリスクガード設定（max_position_pct, max_utilization, max_drawdown 等）を見直してください。

---

この README はコードベースの主要部分に基づいて作成しています。各モジュールの追加説明やセットアップ手順の詳細（例: データベーススキーマの作成や J-Quants API の取得手順）が必要であれば追記します。