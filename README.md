# KabuSys

日本株向け自動売買システム（開発中）  
このリポジトリは、kabuステーション（ローカルの REST/WebSocket サーバ）またはモックブローカを用いた発注・監視・リコンシリエーション機能を備えた実行基盤を提供します。

主な設計方針
- 発注ロジックと永続化（SQLite）を分離
- 発注フローはクラッシュ耐性を考慮した二相的永続化
- 3 段階のリスクガード（Gate1/2/3）による安全性確保
- Paper trading（モック）と live（本番）を環境で切替可能

バージョン: 0.1.0

---

## 主な機能一覧
- 環境設定ウィザード（.env の対話的作成・更新）
- 設定検証ツール（.env および config/*.yaml の存在・形式チェック）
- ExecutionEngine: シグナルを読み取って発注を行うメインエンジン
  - シグナル処理（発注ウィンドウ）と push（WebSocket）ドレイン
  - kill-switch / PID ファイル管理
- Order 管理
  - OrderRecord（状態遷移ロジック）
  - OrderRepository（SQLite 永続化）
  - OrderManager（ブローカ API 経由の発注フロー）
  - Reconciler（起動時の OrderSent 照合とポジション差分検出）
- Broker クライアント群
  - KabuStationClient（kabuステーション REST＋WebSocket 実装）
  - MockBrokerClient（テスト／ペーパートレード用モック）
  - create_broker_api() ファクトリ
- RiskManager：Gate1/2/3 による余力・重複・レート制限・サーキットブレーカー・ドローダウン監視
- Monitoring（SystemMonitor）: 監視ループ（SQLite/DUCKDB を使用）
- データモジュール
  - マーケットカレンダー管理（DuckDB 上の market_calendar）
  - ニュース収集（RSS 取得と正規化）

---

## セットアップ手順（開発向け）
前提
- Python 3.10+（型注釈や match 等は不要ですが、コードは近代的な構成を想定）
- システムに duckdb, sqlite3 が利用可能

1. リポジトリをクローン
   - git clone ... && cd <repo>

2. 仮想環境を作成して有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存パッケージをインストール
   - 主要依存例（プロジェクトに requirements.txt が無い場合の最低限）
     - pip install duckdb httpx websocket-client defusedxml pyyaml
   - 注意: PyYAML は config/*.yaml のパース検証に使用されます（未インストールなら検証はスキップされます）。

4. ディレクトリ作成（必要なら）
   - data ディレクトリを作成（DB / PID / フラグファイル用）
     - mkdir -p data

5. .env の作成
   - 対話式ウィザードを使う（推奨）
     - python -m kabusys.config_setup
   - 手動で作る場合は .env.example を参照して .env を作成してください（.env.example が無い場合は README の「環境変数」を参照）。

6. 設定検証
   - python -m kabusys.validate_config
   - 警告を FAIL 扱いにしたい場合:
     - python -m kabusys.validate_config --strict

7. 初回実行
   - 監視ループ（monitoring）:
     - python -m kabusys.run_monitoring
   - 実行エンジン（execution）:
     - python -m kabusys.run_execution

   実行すると必要な DB テーブル（orders / monitoring 系など）は起動時に初期化されます。

---

## 環境変数（主な項目）
必須
- JQUANTS_REFRESH_TOKEN — J-Quants API リフレッシュトークン（必須）
- KABU_API_PASSWORD — kabuステーション API 用パスワード（必須）

任意 / 推奨（デフォルトあり）
- KABUSYS_ENV — 実行環境: development / paper_trading / live（デフォルト: development）
  - paper_trading または development では MockBrokerClient を使用します
  - live は本番（KabuStationClient）想定（実装状況に注意）
- DUCKDB_PATH — DuckDB のファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite のファイルパス（デフォルト: data/monitoring.db）
- LOG_LEVEL — ログレベル（DEBUG / INFO / WARNING / ERROR / CRITICAL）
- KABU_API_BASE_URL — kabu station のベース URL（例: http://localhost:18080/kabusapi）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — LINE 通知設定（本番でのアラート用）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（0/1; デフォルト 0）
- PAPER_FILL_MODE — paper_trading 用の fill 動作（instant / partial / never / reject）
- PAPER_TRADING_SQLITE_PATH — paper_trading 用に SQLite を分離する場合のパス

.env 自動ロード
- 起動時にプロジェクトルート（.git または pyproject.toml を基準）から .env と .env.local を自動読み込みします
  - OS 環境変数 > .env.local > .env の優先順位
  - 自動ロードを無効にする場合:
    - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

重要ファイル（実行制御）
- data/kill.flag — エンジンを停止して kill-switch を発動するために外部で作成するフラグ
- data/stop_requested.flag — 監視・実行ループを優雅に停止するためのフラグ
- data/execution.pid, data/<...>.pid — PID ファイル

---

## 使い方（主なコマンド）
- 環境設定ウィザード（.env を対話的に生成/更新）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 厳密モード（警告もエラー扱い）:
    - python -m kabusys.validate_config --strict

- 実行エンジン（ExecutionEngine）起動
  - python -m kabusys.run_execution
  - KABUSYS_ENV が paper_trading / development の場合は MockBrokerClient が使われます
  - 停止は data/stop_requested.flag を作成するか、kill.flag を作成して kill_switch を発動してください

- 監視ループ起動
  - python -m kabusys.run_monitoring
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL（秒）で上書き可能（デフォルト 60）

- テスト用モック（PAPER_FILL_MODE）
  - PAPER_FILL_MODE=instant  → 即時全約定（デフォルト）
  - PAPER_FILL_MODE=partial  → 一部約定（半分）
  - PAPER_FILL_MODE=never    → 注文は pending（OrderSentPendingError を発生させる）
  - PAPER_FILL_MODE=reject   → 発注拒否（OrderRejectedError）

注意: live モードはコード内で NotImplementedError を投げる箇所があります。実運用では実装状況を確認してください。

---

## 主要ファイル / ディレクトリ構成（抜粋）
- src/kabusys/
  - __init__.py — パッケージ情報（バージョン等）
  - config.py — 環境変数読み込み・Settings クラス（.env 自動ロードを含む）
  - config_setup.py — 対話式 .env 作成ウィザード
  - validate_config.py — 起動前の環境検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト（発注）
  - run_monitoring.py — SystemMonitor 起動スクリプト（監視）
  - execution/
    - broker_api.py — Broker API のデータモデル、Protocol、ファクトリ
    - broker_factory.py — Settings に応じた Broker クライアント生成
    - kabu_client.py — 実ブラウザ用 KabuStationClient 実装（HTTP/WebSocket）
    - mock_client.py — MockBrokerClient（テスト/ペーパートレード用）
    - order_record.py — Order の状態遷移ロジック（純粋モデル）
    - order_repository.py — SQLite 永続化層（orders テーブルの初期化含む）
    - order_manager.py — 発注フロー（create/send/sync/cancel）
    - execution_engine.py — ExecutionEngine（シグナル処理 / push ドレイン）
    - reconciler.py — 起動時リコンシリエーション（OrderSent の突合せ・ポジション差分）
    - risk_manager.py — Gate1/2/3 のリスクガード
  - data/
    - calendar_management.py — マーケットカレンダー管理（DuckDB）
    - news_collector.py — RSS ニュース収集・正規化（defusedxml 等使用）
  - monitoring/ (監視関連モジュール: DB 初期化・SystemMonitor 等)
  - utils/
    - logging_setup.py — ログ初期化ユーティリティ
    - process_priority.py — プロセス優先度操作ユーティリティ

詳細は各ファイルの docstring / コメントを参照してください。コメントは設計判断や使用例を含んでいます。

---

## 運用上の注意
- 本番（live）動作時は設定（LINE 通知・KILL_FLAG の動作など）を慎重に確認してください。validate_config の警告は無視しないことを推奨します。
- .env は機密情報を含むため、絶対にバージョン管理（git）へコミットしないでください。
- ExecutionEngine は PID ファイルや kill.flag を使って外部オペレーションと連携します。運用ツールを組む際はこれらのファイルを使ってください。
- Order の状態遷移は OrderRecord の定義に従います。不正な遷移は例外を投げます。

---

## 開発 / テストヒント
- 単体テストやローカル検証では KABUSYS_ENV=paper_trading を使用し、MockBrokerClient を使って副作用を避けられます。
- Reconciler は OrderSent の不確定注文を照合して回復するので、クラッシュ耐性の検証に有効です。
- DuckDB をデータ分析用に使用しているため、signals / portfolio_targets 等を DuckDB にロードして発注シミュレーションが可能です。

---

必要に応じて README に追加すべき箇所（例: requirements.txt の正確な内容、運用手順書、監視項目ドキュメントなど）を教えてください。README をそれに合わせて拡張します。