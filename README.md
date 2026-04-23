# KabuSys

日本株向け自動売買システムのコア実装（ライブラリ＋実行スクリプト群）。

このリポジトリは、発注フロー・リスクガード・リコンシリエーション・監視・データ収集（カレンダー／ニュース）など、実運用を想定したコンポーネントを含むモジュール群を提供します。開発／ペーパートレード環境向けに Mock ブローカーを備えており、本番接続（kabuステーション）へ接続できるクライアント実装も用意されています（ただしファクトリ経由の live 実装は未実装で例外が出ます）。

主な設計方針:
- DB（SQLite / DuckDB）は永続化・分析用に分離
- 発注は Signal Queue を引く型（ExecutionEngine）
- リスクは Gate1/2/3 の三段階ガードで制御
- 再起動後のリコンシリエーションで不整合を自動回復

---

## 機能一覧 (Highlights)

- 環境設定ウィザード (.env 作成・更新) — kabusys.config_setup
- 起動前チェック CLI — kabusys.validate_config（必須環境変数・config/*.yaml・パス等を検査）
- ExecutionEngine — シグナルを読み発注を管理するメインエンジン
  - OrderManager / OrderRecord / OrderRepository による堅牢な注文状態管理
  - RiskManager による Gate1/2/3（重複・余力・ポジション上限 / レート制限・CB / ドローダウン）
  - Reconciler による OrderSent のブローカー照合・ポジション差分検出
  - MockBrokerClient（paper_trading / development 向け）と KabuStationClient（kabuステーション用）
- Monitoring（run_monitoring） — SystemMonitor をポーリングして監視データを収集・保存
- Data モジュール
  - calendar_management：J-Quants カレンダーを使った営業日ロジック（next_trading_day 等）
  - news_collector：RSS からの記事収集と前処理（SSRF/XML 脆弱性対策済み）
- ユーティリティ
  - env 自動ロード（.env/.env.local 読み込み、KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）
  - 設定を一元化する Settings クラス（環境変数アクセスラッパ）

---

## 動作環境・依存

- Python >= 3.10（型アノテーションに `|` を使用）
- 主要依存パッケージ（例）
  - duckdb
  - httpx
  - websocket-client
  - defusedxml
  - PyYAML（YAML 検証を有効にする場合）
- 標準ライブラリ: sqlite3, logging, threading, pathlib など

インストール例:
- requirements.txt がある場合:
  - pip install -r requirements.txt
- 個別:
  - pip install duckdb httpx websocket-client defusedxml PyYAML

---

## 環境変数（主要）

必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

任意（デフォルトあり／またはオプション）:
- KABUSYS_ENV (development | paper_trading | live) — default: development
- DUCKDB_PATH — default: data/kabusys.duckdb
- SQLITE_PATH — default: data/monitoring.db
- LOG_LEVEL — DEBUG/INFO/… (default: INFO)
- KABU_API_BASE_URL — kabu station base URL（デフォルト: http://localhost:18080/kabusapi）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID — 通知用（任意）
- PAPER_FILL_MODE — paper_trading 用 fill モード: instant | partial | never | reject（default: instant）
- PAPER_TRADING_SQLITE_PATH — paper_trading 用 SQLite（default: data/paper_trading.db）
- PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START 等（kill/cmd 制御用）
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング秒数（デフォルト 60）

自動 .env ロード:
- デフォルトでプロジェクトルートの .env / .env.local を読み込みます。
- 自動ロードを無効化するには: export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

注意:
- KABUSYS_ENV=live は本番想定ですが、BrokerFactory は現在 live クライアントを未実装で NotImplementedError を出す仕様です。開発・ペーパー運用では paper_trading / development を使用してください。

---

## セットアップ手順

1. リポジトリをクローン
   - git clone <repo-url>

2. Python 環境を作成
   - python -m venv .venv
   - source .venv/bin/activate

3. 依存ライブラリをインストール
   - pip install -r requirements.txt
     または
   - pip install duckdb httpx websocket-client defusedxml PyYAML

4. .env を作成（推奨: ウィザードで対話的に作成）
   - python -m kabusys.config_setup
     例: python -m kabusys.config_setup --env-file .env

   ウィザードは既存 .env を読み込み、対話的に編集・保存します。
   保存後、python -m kabusys.validate_config で検証してください。

5. 設定検証
   - python -m kabusys.validate_config
   - 警告も失敗として扱う場合:
     - python -m kabusys.validate_config --strict

6. 実行（モニタ / 実行エンジン）
   - 監視ループ:
     - python -m kabusys.run_monitoring
     - MONITOR_POLL_INTERVAL 環境変数で間隔を変更可能（秒）
   - 実行エンジン（発注）:
     - python -m kabusys.run_execution
     - Paper trading の場合、KABUSYS_ENV=paper_trading を設定すると MockBrokerClient を使用して data/paper_trading.db に記録します。

注意:
- .env は絶対にリポジトリにコミットしないでください（ウィザードのヘッダにも注意書きがあります）。
- 本番（live）では LINE 通知や kill flag の設定を必ず確認してください（validate_config が警告を投げます）。

---

## 使い方（主要コマンド）

- 環境設定ウィザード（.env 作成）
  - python -m kabusys.config_setup
- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict
- 実行エンジン起動（1セッション）
  - python -m kabusys.run_execution
- 監視ポーリング起動
  - python -m kabusys.run_monitoring

実行時ファイル:
- PID ファイル／kill flag は data/ 以下に書き込まれます（Settings の pid_file_path / kill_flag_path でカスタマイズ可）。
- 停止制御: 実行中に data/stop_requested.flag を作成すると run_* スクリプトは安全に終了します（run_execution では停止フラグを検出してエンジン停止を行う）。

---

## ディレクトリ構成（主要ファイル）

- src/kabusys/
  - __init__.py — パッケージメタ情報
  - config.py — 環境変数読み込み・Settings クラス（自動 .env ロード含む）
  - config_setup.py — .env 対話式ウィザード
  - validate_config.py — 起動前チェック CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — Monitoring 起動スクリプト

  - execution/ （発注ロジック）
    - broker_api.py — BrokerAPI の型、例外、ファクトリ
    - kabu_client.py — kabuステーション向け HTTP/WebSocket クライアント
    - mock_client.py — MockBrokerClient（テスト用）
    - broker_factory.py — Settings に基づくクライアント生成
    - execution_engine.py — ExecutionEngine（シグナル読み・発注ループ）
    - order_record.py — OrderRecord / 状態遷移ロジック
    - order_repository.py — SQLite 永続化レイヤ
    - order_manager.py — 発注ワークフロー（create/send/sync/cancel）
    - reconciler.py — 起動時のリコンシリエーション
    - risk_manager.py — Gate1/2/3 のリスク管理
    - (その他: order_*)

  - data/ （データ収集・カレンダー）
    - calendar_management.py — 営業日ロジック・カレンダー更新ジョブ
    - news_collector.py — RSS ニュース収集・前処理
    - jquants_client.py — （参照されるがここでは省略）J-Quants API ラッパ想定

  - monitoring/
    - monitoring_db.py — 監視 DB 初期化・ログ記録用ユーティリティ
    - system_monitor.py — SystemMonitor（run_monitoring が利用）

  - utils/
    - logging_setup.py — ロギング設定
    - process_priority.py — プロセス優先度設定ユーティリティ

- config/
  - system_config.yaml, data_config.yaml, strategy_config.yaml, risk_config.yaml, execution_config.yaml, monitoring_config.yaml
    - validate_config はこれらの存在と YAML のパース可否をチェックします（PyYAML が無ければ内容検証はスキップ）。

- data/
  - (実行時に生成される DB・PID・flag ファイルなど。例: data/kabusys.duckdb, data/monitoring.db, data/execution.pid)

---

## 開発メモ / 注意点

- 発注フローはクラッシュ耐性を考慮して段階的に DB を更新する設計（OrderCreated → OrderSent を永続化してから broker 呼び出し等）。
- OrderSent のままクラッシュした場合、Reconciler がブローカー照合で復旧を試みます。
- Paper trading / development 環境では MockBrokerClient を使って安全に動作確認が可能です（PAPER_FILL_MODE により挙動を変更可）。
- 実運用（live）接続は注意深く設定を確認してください（LINE 通知や KILL フラグなど）。validate_config で live 時の追加チェックを行います。
- YAML 設定ファイルは scripts/generate_config.py（参照箇所あり）で生成可能と示唆されています。

---

README はここまでです。追加で README に記載したい別セクション（例: API リファレンス、開発ワークフロー、CI 設定、テストの書き方など）があれば教えてください。