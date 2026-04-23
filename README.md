# KabuSys

日本株自動売買システムのコア実装（ライブラリ＋起動スクリプト群）

バージョン: 0.1.0

---

## 概要

KabuSys は日本株の自動売買を念頭に設計された Python 製のシステムコアです。  
主な責務は以下です。

- シグナルに基づく発注（ExecutionEngine）
- 発注の永続化・状態管理（SQLite）
- ブローカー API 抽象（kabu station 実装および Mock 実装）
- 起動時のリコンシリエーション（Reconciler）
- 3段階のリスクガード（Gate1〜3）
- マーケットカレンダー管理・ニュース収集用ユーティリティ
- 環境設定ウィザード（.env の作成）および設定検証 CLI
- 監視用ポーリングループ（SystemMonitor 起動スクリプト）

設計方針として、ビジネスロジック（OrderRecord 等）と永続化（OrderRepository）を分離し、発注のクラッシュ安全性（2相的な永続化）や再起動後の自動復旧を重視しています。

---

## 機能一覧

- 環境設定
  - 対話式ウィザードで .env を生成・更新（python -m kabusys.config_setup）
  - .env の自動読み込み（.env.local が .env を上書き）
  - 設定検証 CLI（python -m kabusys.validate_config、--strict オプション）

- 発注・実行
  - ExecutionEngine によるシグナルプル方式の発注フロー
  - OrderManager（状態遷移チェック + broker 呼び出しの安全な永続化）
  - OrderRepository（SQLite による永続化、unique index による同一 signal の保護）
  - Reconciler による起動時の OrderSent 照合とポジション差分検出
  - MockBrokerClient による Paper/Dev での安全な試験（fill_mode 切替可能）
  - KabuStationClient による kabu station REST API 実装（HTTP/WebSocket）

- リスク管理
  - Gate1: 発注前（余力／重複／銘柄・全体上限）
  - Gate2: エグゼキューション（レート制限／サーキットブレーカー）
  - Gate3: 実行後メトリクス（ドローダウン監視 → kill_switch 発動）

- データ系ユーティリティ
  - JPX カレンダー管理（DuckDB）
  - RSS ニュース収集・正規化（defusedxml を使用した安全な XML 処理）
  - 監視用 DB（SQLite）と長期分析用 DuckDB の利用

- 運用補助
  - PID / stop flag / kill flag の管理
  - 監視ループ（run_monitoring.py）による定期的な状態収集

---

## 必要要件（推奨）

- Python 3.10+
- SQLite（Python 標準ライブラリで利用）
- 推奨 Python パッケージ
  - duckdb
  - httpx
  - websocket-client
  - defusedxml
  - pyyaml （config 検証で YAML パースを行う場合に必要）

（実際のプロジェクトでは requirements.txt を用意して pip install -r でインストールしてください）

---

## セットアップ手順

1. リポジトリをクローン
   - git clone <repo-url>

2. 仮想環境を作成して有効化（例）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存パッケージをインストール（例）
   - pip install duckdb httpx websocket-client defusedxml pyyaml

4. 対話式ウィザードで .env を作成
   - python -m kabusys.config_setup
   - ウィザードに従って必須項目（J-Quants トークン / Kabu API パスワード 等）を入力してください。

5. 設定検証
   - python -m kabusys.validate_config
   - 警告も失敗扱いにする場合:
     - python -m kabusys.validate_config --strict

注意:
- 自動的に .env を読み込む仕組みがあり（プロジェクトルートの .env → .env.local）、OS 環境変数が優先されます。自動読み込みを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 をセットしてください。
- .env は絶対に Git にコミットしないでください。

---

## 主要環境変数

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants API 用リフレッシュトークン（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）

任意 / 上書き可能:
- KABUSYS_ENV — 実行環境（development | paper_trading | live）デフォルト: development
  - paper_trading / development: MockBrokerClient を使用
  - live: 本番（注意: 現状 Live ブローカー実装は未実装の場合があります）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト data/monitoring.db）
- LOG_LEVEL — ログレベル（DEBUG|INFO|WARNING|ERROR|CRITICAL、デフォルト INFO）
- KABU_API_BASE_URL — kabu station ベース URL（デフォルト http://localhost:18080/kabusapi）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID — LINE 通知用（任意）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（0/1、デフォルト 0）
- MONITOR_POLL_INTERVAL — 監視ポーリング間隔（秒、run_monitoring 用）

補足:
- Paper Trading 時のモック挙動は PAPER_FILL_MODE（instant|partial|never|reject）で制御可能（Settings.paper_fill_mode）。

---

## 使い方（コマンド例）

- 環境設定ウィザード（.env 作成/更新）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 警告を fail 扱いにする場合:
    - python -m kabusys.validate_config --strict

- 実行エンジン起動（発注）
  - python -m kabusys.run_execution
  - 注意: KABUSYS_ENV が paper_trading / development の場合は MockBrokerClient を使用します。live は未実装の可能性あり（BrokerClientFactory 参照）。

- 監視ループ起動
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（秒、デフォルト 60）

運用・停止:
- 停止フラグ: プロジェクトの data/stop_requested.flag を作成するとループが検知して終了します。
- kill.flag: settings.kill_flag_path（デフォルト data/kill.flag）を用いて kill_switch を制御します。起動時に KILL_FLAG_CLEAR_ON_START=1 を設定すれば既存の kill.flag を自動でクリアして起動しますが、本番では注意してください。

ログ:
- PID ファイルやログ出力は Settings で指定されたパスに保存されます（PID ファイルは execution 起動時に作成され、終了時に削除されます）。

---

## ディレクトリ構成（主要ファイル）

プロジェクトのソースは src/kabusys 以下に配置されています。代表的なファイル・モジュールと簡単な説明は以下の通り。

- src/kabusys/
  - __init__.py — パッケージ定義（バージョン情報）
  - config.py — 環境変数読み込み / Settings クラス（.env 読み込みロジック含む）
  - config_setup.py — 対話式 .env ウィザード
  - validate_config.py — 起動前の設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト

- src/kabusys/execution/
  - broker_api.py — ブローカー API のデータモデル・Protocol・ファクトリ
  - kabu_client.py — kabu station 実装（HTTP + WebSocket）
  - mock_client.py — MockBrokerClient（テスト/開発用）
  - broker_factory.py — Settings によるブローカーファクトリ
  - order_record.py — Order の状態遷移ロジック（純粋ビジネスロジック）
  - order_repository.py — SQLite 永続化層（orders テーブル定義 / CRUD）
  - order_manager.py — 発注フロー（OrderRecord + Repository + Broker）
  - execution_engine.py — セッション管理（シグナル処理、push ドレイン、kill_switch 等）
  - reconciler.py — 起動時リコンシリエーション（OrderSent 照合 / ポジション差分）
  - risk_manager.py — 3段階リスクガード（Gate1〜3）

- src/kabusys/data/
  - calendar_management.py — マーケットカレンダー管理（DuckDB）
  - news_collector.py — RSS ニュース収集 / 正規化

- src/kabusys/monitoring/
  - （監視 DB 初期化や SystemMonitor 実装ファイル群 — 監視関連の実装）

- src/kabusys/utils/
  - logging_setup.py — ロギングのセットアップ
  - process_priority.py — プロセス優先度設定（運用補助）

（上記に無いモジュールやスクリプトはプロジェクト内に追加されている可能性があります。実運用前に該当ディレクトリを確認してください。）

---

## 運用上の注意点

- production (KABUSYS_ENV=live) 設定時は全ての設定（LINE 通知等）を慎重に確認してください。validate_config が live を検出すると警告を出します。
- live モードのブローカー実装（KabuStationClient）を使用する場合、kabuステーション アプリがローカルで稼働していることが前提です。
- .env は機密情報を含むため、絶対に VCS にコミットしないでください。
- Order の状態管理は厳密に設計されています。DB の状態とブローカーの状態を突合し、リコンシリエーションを適切に行ってください。
- Paper / Dev 環境では MockBrokerClient を使うことで安全に動作確認が可能です（PAPER_FILL_MODE 等で挙動を変更できます）。

---

必要があれば README に含めるサンプル .env のテンプレートや詳しい起動手順（systemd サービス化やコンテナ化例）を追加できます。どの情報がさらに欲しいか教えてください。