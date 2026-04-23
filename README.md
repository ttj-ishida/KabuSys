# KabuSys

バージョン: 0.1.0

日本株向けの自動売買システムの骨格実装です。シグナルから発注までのフロー、発注の永続化と状態管理、リスクガード、モニタリング、リコンシリエーション（再起動時の同期）等を含む実装が入っています。

---

## プロジェクト概要

KabuSys は以下を目的としたコンポーネント群を持つ自動売買フレームワークです。

- シグナルに基づく発注エンジン（ExecutionEngine）
- 注文状態管理（OrderRecord / OrderManager / OrderRepository）
- ブローカー API 抽象（BrokerAPIProtocol）とモック実装（MockBrokerClient）
- リスクガード（3段階: Gate1/2/3）
- 起動時のリコンシリエーション（Reconciler）
- 監視ループ（SystemMonitor 起動スクリプト）
- 環境設定ウィザード（.env 作成補助）と設定検証ツール

設計方針として、ビジネスロジックと DB/IO を明確に分離し、再起動・クラッシュ耐性（OrderSent の二相永続化やリコンシリエーション）を重視しています。

---

## 主な機能一覧

- .env による環境設定の自動読み込み（プロジェクトルートの .env / .env.local）
- 対話式設定ウィザード（python -m kabusys.config_setup）
- 設定検証 CLI（python -m kabusys.validate_config）
  - 必須環境変数の検出、YAML ファイルの存在/パース確認（PyYAML があれば内容検証）
  - --strict により警告も FAIL 扱いにできる
- ExecutionEngine（signal プル型発注 + push ドレイン）
  - Order 作成・送信・同期・キャンセル
  - Kill Switch（kill.flag）検出、全注文キャンセル処理
  - PID ファイル管理
- Broker API 抽象化
  - 実ブローカー実装（KabuStationClient、HTTP + WebSocket）
  - モック実装（MockBrokerClient）でローカルテスト可能（paper_trading / development 用）
- Order 永続化（SQLite）と orders スキーマ（冪等性を考慮）
- リスク管理（余力、重複、ポジション上限、レート制限、サーキットブレーカー、ドローダウン監視）
- 監視ループ（監視 DB へイベント書き込み・定期チェック）
- データ関連ユーティリティ
  - マーケットカレンダー（DuckDB）
  - ニュース収集モジュール（RSS 取得、SSRF 対策、トラッキング除去）

---

## セットアップ手順

以下はローカルで開発 / テスト実行する際の簡易手順です。

1. リポジトリをクローンしてプロジェクトルートへ移動

2. Python 仮想環境を作成して有効化
   - 例: python -m venv .venv && source .venv/bin/activate

3. 必要パッケージをインストール（プロジェクトに requirements.txt があればそれを使ってください）
   - 例（代表的な依存）:
     pip install duckdb httpx websocket-client defusedxml
   - 任意/推奨:
     pip install pyyaml  # validate_config の YAML 検証用
   - 標準ライブラリにある sqlite3 は別途インストール不要です。

4. 環境変数ファイルを用意する
   - 対話式ウィザードで作成:
     python -m kabusys.config_setup
   - または手動でプロジェクトルートに `.env` を作成してください。

5. 作成した .env の検証:
   python -m kabusys.validate_config
   - 警告も失敗にしたい場合:
     python -m kabusys.validate_config --strict

6. 実行用 DB ディレクトリ作成（必要な場合）
   - デフォルトでは data/ 以下に DB 等のファイルを置きます:
     - DUCKDB_PATH: data/kabusys.duckdb
     - SQLITE_PATH: data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db

---

## 環境変数（主なもの）

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants API 用リフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API パスワード

任意 / 推奨:
- KABUSYS_ENV — 実行環境: development | paper_trading | live（デフォルト: development）
- DUCKDB_PATH — DuckDB のファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード専用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL、デフォルト: INFO）
- KABU_API_BASE_URL — kabu station API のベース URL
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID — 本番時のアラート用（任意）

その他:
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag の自動クリア（0/1、デフォルト: 0。本番では 0 推奨）
- PID_FILE_PATH, KILL_FLAG_PATH — PID / kill flag のパスを上書き可能

注意:
- 自動で .env を読み込む機能は有効（デフォルト）。テスト等で無効化するには:
  export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

サンプル（.env の一部）:
JQUANTS_REFRESH_TOKEN=your_token_here
KABU_API_PASSWORD=your_password_here
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
LOG_LEVEL=INFO

---

## 使い方（主なコマンド）

- 設定ウィザード（.env 作成 / 更新）
  python -m kabusys.config_setup

- 設定検証（.env と config/*.yaml のチェック）
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict  # 警告も FAIL 扱い

- 実行エンジン起動（本番 / ペーパートレード）
  python -m kabusys.run_execution

  実行フロー:
  - PID ファイルを作成
  - DB 接続（paper_trading の場合は paper_sqlite_path を使用）
  - BrokerClient を生成（development / paper_trading では MockBrokerClient）
  - ExecutionEngine.run_session() をスレッドで実行

- 監視ループ起動
  python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（秒、デフォルト 60）
  - 停止は data/stop_requested.flag を作成して検出させる（または Ctrl-C）

停止・強制停止関連:
- kill.flag（デフォルト data/kill.flag）を作成すると ExecutionEngine 内の kill switch が動作し、全 active 注文をキャンセルして停止します。
- stop_requested.flag（data/stop_requested.flag）を作成するとループが通常終了します（run_monitoring/run_execution の停止トリガ）。

デバッグ / テスト:
- KABUSYS_ENV=paper_trading または development の場合、モックブローカー（MockBrokerClient）が使われるためローカルで安全に動作確認できます。
- Reconciler により起動時の OrderSent 状態の注文をブローカーと突合して同期します。

---

## 主要ファイル / ディレクトリ構成

プロジェクトの主要なツリー（src/kabusys 以下）:

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / Settings 管理（自動 .env ロード含む）
  - config_setup.py          — 対話式 .env 作成ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py       — SystemMonitor ポーリング起動スクリプト
  - execution/               — 発注周りの実装
    - broker_api.py          — Broker API 抽象（Protocol、データモデル、ファクトリ）
    - broker_factory.py      — Settings ベースで BrokerClient を生成するファクトリ
    - kabu_client.py         — kabuステーション 実装（HTTP + WebSocket）
    - mock_client.py         — モックブローカー（テスト用）
    - order_record.py        — 注文状態（OrderRecord）と遷移ロジック
    - order_repository.py    — SQLite 永続化層（orders テーブル）
    - order_manager.py       — Order の作成・送信・同期・キャンセル API
    - execution_engine.py    — ExecutionEngine（シグナル処理 + push ドレイン）
    - reconciler.py          — 起動時リコンシリエーション
    - risk_manager.py        — 3 段階のリスクガード
  - data/                    — データ関連（DuckDB 操作など）
    - calendar_management.py — マーケットカレンダー管理・営業日判定
    - news_collector.py      — RSS ニュース収集（SSRF 対策・正規化）
    - jquants_client.py      — (想定) J-Quants API クライアント（コードベースに含まれる想定モジュール）
  - monitoring/              — 監視 DB / SystemMonitor 実装（監視関連のコード）
  - utils/                   — ロギング設定、プロセス優先度などユーティリティ

その他:
- config/                   — YAML 設定ファイル群（system_config.yaml 等、存在が期待される）
- data/                     — 実行時に作成される DB ファイル / PID / フラグ類

（上記は主要ファイルの抜粋です。実際のリポジトリではさらにサブモジュールやテストコード等が存在する場合があります。）

---

## 実行時の注意点 / 補足

- .env はセキュアに管理してください（トークン・パスワードが含まれるため Git 等にコミットしない）。
- validate_config は PyYAML があれば config/*.yaml の中身もパースして検証します。未インストール時は YAML 内容検証をスキップして警告を出します。
- KABUSYS_ENV=live を使用する場合はすべての設定を慎重に確認してください。本番向けの追加ガードが validate_config と settings に入っています（LINE 通知設定のチェック、KILL_FLAG_CLEAR_ON_START の警告など）。
- 実ブローカー（kabu station）を使う場合は kabuステーション® がローカルで起動している必要があります（KabuStationClientが想定）。現状、ライブクライアントは未実装の箇所があるため、まずは paper_trading/development で Mock を使った動作確認を推奨します。
- DB スキーマ（orders テーブル等）は起動時に初期化するユーティリティが用意されています（init_orders_db など）。起動前にファイルパスの親ディレクトリが存在するか確認してください。validate_config は親ディレクトリの存在を警告します。

---

## 開発・拡張のヒント

- BrokerAPIProtocol を実装すれば別ブローカーへの接続も差し替え可能です。create_broker_api() を拡張してください。
- ExecutionEngine.run_session() はタイミング考慮の箇所が多いため、単体テストでは内部メソッド（_process_signals / _drain_push_queue / _handle_push）を直接呼ぶ設計でテスト可能です。
- リコンシリエーション（Reconciler）は起動時の安全性向上に寄与します。クラッシュ後の状態復元ロジックの改善はここを中心に行うとよいでしょう。

---

問題や追加説明が必要であれば、使いたい機能（例: live ブローカー接続、DuckDB の初期セットアップ、監視項目の拡張など）を教えてください。具体的な手順やサンプル設定を用意します。