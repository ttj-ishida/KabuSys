# KabuSys

日本株自動売買システムのコア実装（ライブラリ／実行スクリプト群）

以下はこのリポジトリに含まれる主要機能の概要、セットアップ手順、使い方、ディレクトリ構成の説明です。

※ 本 README は提供されたソースコード（src/kabusys 以下）に基づいて作成しています。

---

## プロジェクト概要

KabuSys は日本株向けの自動売買フレームワークです。  
主な役割は以下の通りです。

- シグナルに基づく発注フロー（ExecutionEngine）
- ブローカー API 抽象化（kabu ステーション用クライアントとモック）
- 注文状態管理（OrderRecord, OrderRepository）
- リスク管理の多段ガード（Gate1/Gate2/Gate3）
- 再起動時のリコンシリエーション（Reconciler）
- 監視ループ（SystemMonitor 起動）
- 環境設定ウィザードおよび設定検証ツール
- データ系ユーティリティ（マーケットカレンダー、ニュース収集等）

設計上、DB（SQLite / DuckDB）や .env による設定で動作を切り替えられます。paper_trading モードではモックブローカーを用いて本番 DB と分離した動作が可能です。

---

## 機能一覧（抜粋）

- 環境設定ウィザード（python -m kabusys.config_setup）
  - 対話式で .env を生成・更新
- 設定検証 CLI（python -m kabusys.validate_config）
  - 必須環境変数・config/*.yaml の存在や基本整合性をチェック
  - --strict で警告も失敗として扱う
- 実行エンジン（python -m kabusys.run_execution）
  - Signal Queue を引いて発注を行うメインエンジン
  - KABUSYS_ENV に応じて MockBrokerClient を使用（paper_trading / development）
- 監視ループ（python -m kabusys.run_monitoring）
  - SystemMonitor のポーリングを行うデーモン（MONITOR_POLL_INTERVAL で間隔指定）
- Broker API 層
  - KabuStationClient（kabu ステーション REST / WebSocket）
  - MockBrokerClient（テスト用、fill_mode などを指定可能）
- 注文状態管理
  - OrderRecord（状態遷移の検証）
  - OrderRepository（SQLite による永続化、スキーマ生成関数あり）
  - OrderManager（作成・送信・同期・キャンセルの高レベル API）
- リスク管理（RiskManager）
  - Gate1: シグナルレベル（余力・重複・ポジション上限）
  - Gate2: 実行レベル（レート制限・サーキットブレーカー）
  - Gate3: メトリクス（ドローダウン監視）
- データユーティリティ
  - calendar_management: 営業日判定・次営業日の取得
  - news_collector: RSS 収集・前処理（SSRF 対策・XML サニタイズ等）

---

## セットアップ手順（開発 / 実行）

前提: Python 3.9+ を想定（typing の構文から）。

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境を作成して有効化
   ```
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
   ```

3. 必要パッケージをインストール  
   プロジェクトに requirements.txt がある想定で:
   ```
   pip install -r requirements.txt
   ```
   最低限必要になる主なパッケージ（examples）:
   - duckdb
   - httpx
   - websocket-client
   - defusedxml
   - PyYAML（config/*.yaml のパース検証を行う場合）
   - その他（プロジェクト固有の依存がある場合は requirements.txt を参照）

4. .env の作成（推奨: ウィザードを使う）
   ```
   python -m kabusys.config_setup
   ```
   ウィザードで J-Quants トークンや kabu API パスワード等を入力して .env を生成します。

5. 設定検証
   ```
   python -m kabusys.validate_config
   ```
   必須環境変数が未設定の場合はエラー（exit code 1）になります。警告を FAIL 扱いにするには --strict を付与します。

---

## 主要環境変数（代表例）

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants API のリフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API パスワード

任意・上書き可能:
- KABUSYS_ENV — 実行環境 (development | paper_trading | live)（デフォルト: development）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- LOG_LEVEL — ログレベル（DEBUG|INFO|WARNING|ERROR|CRITICAL）
- KABU_API_BASE_URL — kabu station base URL（例: http://localhost:18080/kabusapi）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — 本番通知用

その他:
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（0 or 1）
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒）
- PAPER_FILL_MODE — paper_trading 時のモックの fill_mode（instant|partial|never|reject）

注意:
- .env は Git にコミットしないでください（config_setup.py のヘッダにも警告あり）。
- 自動的に .env / .env.local がプロジェクトルートから読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。

---

## 使い方（主要コマンド）

- 環境設定ウィザード（.env を生成／更新）
  ```
  python -m kabusys.config_setup
  ```

- 設定検証（起動前チェック）
  ```
  python -m kabusys.validate_config
  # 警告も FAIL とする:
  python -m kabusys.validate_config --strict
  ```

- 実行エンジン起動（発注処理）
  ```
  python -m kabusys.run_execution
  ```
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、paper_trading 用 SQLite（PAPER_TRADING_SQLITE_PATH）に書き込みます。
  - 実行中は data/execution.pid（デフォルト）に PID を書きます。
  - data/stop_requested.flag を置くと安全に停止できます。
  - 起動前に kill.flag（KILL_FLAG_PATH）が存在する場合の挙動は KILL_FLAG_CLEAR_ON_START による。

- 監視ループ起動（SystemMonitor のポーリング）
  ```
  python -m kabusys.run_monitoring
  ```
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書きできます（デフォルト 60 秒）。

- ライブラリ利用サンプル（内部 API）
  - 設定取得:
    ```py
    from kabusys.config import settings
    print(settings.duckdb_path)
    ```
  - ブローカー生成:
    ```py
    from kabusys.execution.broker_factory import BrokerClientFactory
    broker = BrokerClientFactory.create(settings)
    ```

---

## 開発者向けノート

- .env の自動読み込みは、プロジェクトルート（.git または pyproject.toml があるディレクトリ）を基準に行われます。
- config/*.yaml の詳細な検証は PyYAML がインストールされている場合にのみ行われます。未インストール時は警告によりスキップされます。
- ExecutionEngine の信頼性設計:
  - 発注は db に OrderSent を先に保存 → ブローカー呼び出し → broker_order_id を保存 → OrderAccepted に遷移、という 2 相永続化を用いてクラッシュ耐性を高めています。
  - リコンシリエーション（Reconciler）は起動時に OrderSent の未確定注文をブローカーと突合して復旧します。
- MockBrokerClient は fill_mode を変えてテスト可能（instant / partial / never / reject）。

---

## ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py
- config.py                — 環境変数 / .env の読み込み・Settings
- config_setup.py          — .env 対話式ウィザード
- validate_config.py       — 設定検証 CLI
- run_execution.py         — ExecutionEngine 起動スクリプト
- run_monitoring.py        — SystemMonitor 起動スクリプト
- execution/
  - __init__.py
  - broker_api.py          — Broker API のデータモデル・Protocol・ファクトリ
  - broker_factory.py      — Settings に基づくクライアント生成
  - kabu_client.py         — kabu ステーション実装（HTTP/WS）
  - mock_client.py         — モックブローカー
  - order_record.py        — OrderRecord（状態遷移）
  - order_repository.py    — SQLite 永続化層
  - order_manager.py       — 注文操作（高レベル API）
  - execution_engine.py    — ExecutionEngine（シグナル処理 / push drain）
  - reconciler.py          — 起動時リコンシリエーション
  - risk_manager.py        — Gate1/2/3 リスク制御
- data/
  - calendar_management.py — 営業日管理・カレンダー更新
  - news_collector.py      — RSS ニュース収集（途中まで）
- monitoring/
  - monitoring_db.py       — 監視 DB 初期化 / ログ（参照されている）
- utils/
  - logging_setup.py       — ログ設定（参照されている）
  - process_priority.py    — プロセス優先度設定（参照されている）
- config/                  — 設定用 YAML（system_config.yaml 等）を想定
- data/                    — データファイル（DuckDB, SQLite, PID/flag ファイル等）

（上記は提供コードに基づく代表的ファイル群です。リポジトリ全体の完全な一覧は git ls-files 等で確認してください。）

---

## よくある Q&A / トラブルシューティング

- Q: validate_config が YAML のパースエラーを報告する  
  A: PyYAML が必要です。pip install pyyaml を実行してください。YAML が壊れている場合は config/*.yaml を修正。

- Q: run_execution を実行しても発注が行われない（paper_trading なのに）  
  A: .env で KABUSYS_ENV が適切に設定されているか確認してください。paper_trading / development は MockBroker を使用します。

- Q: kill.flag や stop_requested.flag の意味は？  
  A: kill.flag は外部からの「強制停止（起動拒否 or 起動時の kill スイッチ）」用。stop_requested.flag は稼働中プロセスに安全停止を促すためのフラグです。

---

## 最後に

- .env は機密情報を含みます。Git 等で共有・コミットしないでください。  
- 本 README はソースコードに基づく概要ドキュメントです。詳細実装・追加モジュールはソースを参照してください。

ご希望があれば、README に以下を追加できます:
- 例: サンプル .env.example
- requirements.txt の推奨内容
- 実行時のログ出力例 / トラブルシュート手順
- 各モジュールの詳細設計図（シーケンス図など）

必要があれば指示ください。