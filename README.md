# KabuSys

日本株向けの自動売買システムのプロジェクトテンプレート。発注フロー、リスクガード、監視、カレンダー管理、ニュース収集などの主要コンポーネントを含むモジュール群を提供します。

## 概要
- 発注エンジン（ExecutionEngine）によりシグナルに基づく発注を実行
- Broker クライアントは実運用（kabuステーション）とモック（ペーパートレード / 開発）を切り替え可能
- 安全性のための 3 段階リスクガード（Gate1/2/3）を実装
- 起動時の設定検証ツール、対話式の .env 作成ウィザードを提供
- DuckDB / SQLite を利用したデータ管理、監視用のループ実装あり
- 再起動時のリコンシリエーション（Reconciler）で不整合を自動復旧

## 主な機能
- config_setup: 対話式に .env を生成／更新するウィザード（python -m kabusys.config_setup）
- validate_config: .env と config/*.yaml の存在・妥当性を起動前に検証する CLI（python -m kabusys.validate_config）
- run_execution: 実際の ExecutionEngine を起動するエントリスクリプト（python -m kabusys.run_execution）
  - KABUSYS_ENV=paper_trading では MockBrokerClient を使用し、本番 DB と分離
- run_monitoring: SystemMonitor のポーリングループを起動（python -m kabusys.run_monitoring）
  - MONITOR_POLL_INTERVAL で間隔を制御
- Broker クライアント層
  - KabuStationClient: kabuステーション REST / WebSocket 実装
  - MockBrokerClient: テスト用モック（fill_mode 等で挙動制御）
- 注文管理
  - OrderRecord（状態遷移ロジック）、OrderRepository（SQLite 永続化）、OrderManager（外向き API）
- リスク管理
  - RiskManager: check_signal / check_execution / check_metrics（ドローダウン監視等）
- データ処理
  - カレンダ管理（market_calendar）と営業日判定（next_trading_day 等）
  - ニュース収集モジュール（RSS 取得、前処理、保存ロジック）

## 要求環境
- 推奨 Python バージョン: 3.10+
  - （ソース内で | 型合成演算子や型注釈の記法を使用）
- 主な外部依存（機能に応じて必要）
  - duckdb
  - httpx
  - websocket-client
  - defusedxml
  - PyYAML（config/*.yaml のパース検証を行う場合）
- 標準ライブラリ: sqlite3, logging, threading, pathlib, os など

インストール例:
- 仮想環境作成 → pip install:
  - pip install duckdb httpx websocket-client defusedxml PyYAML

（プロジェクトに requirements.txt がある場合はそれを使用してください）

## セットアップ手順
1. リポジトリをクローンしてワークディレクトリへ移動
2. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate（Windows は .venv\Scripts\activate）
3. 依存パッケージをインストール
   - pip install duckdb httpx websocket-client defusedxml PyYAML
4. 対話式ウィザードで .env を生成（推奨）
   - python -m kabusys.config_setup
   - 生成後、python -m kabusys.validate_config で検証
5. DB 初期化
   - Execution / Monitoring で起動時に必要なテーブルを作成する関数（init_orders_db / init_monitoring_db）があるため、起動時に自動で作成されます。必要ならスクリプトで事前に実行してください。

注意:
- .env は絶対に Git にコミットしないでください（config_setup の出力にも注記あり）。
- 自動で .env を読み込む動作は import 時に行われます（.env → .env.local の優先順）。自動ロードを無効にする場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

## 環境変数（主要）
- 必須
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- 推奨 / 任意
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
  - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH（デフォルト: data/monitoring.db）
  - LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL）
  - KABU_API_BASE_URL（kabu station のベース URL）
  - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（本番アラート用）
  - KILL_FLAG_CLEAR_ON_START（0/1、本番での自動クリア防止）
  - MONITOR_POLL_INTERVAL（run_monitoring のポーリング間隔秒数）

.env 自動ロードの仕組み:
- プロジェクトルート（.git または pyproject.toml を基準）を探索して .env を読み込みます。
- OS 環境変数が優先され、.env.local は .env をオーバーライドします（既存 OS 変数は保護）。

## 使い方（主なコマンド）
- .env 作成（対話式）
  - python -m kabusys.config_setup
- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict  # 警告も失敗扱いで exit 1
- 実行エンジン起動（セッション実行）
  - python -m kabusys.run_execution
  - 停止: プロジェクトルート/data/stop_requested.flag を作成すると graceful に停止します
  - PID ファイル: data/execution.pid（設定で変更可能）
  - kill.flag: data/kill.flag により即時 kill_switch を発動（起動時に存在すると起動を拒否する設定がデフォルト）
- 監視ループ起動
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL でポーリング間隔変更（秒）
  - 監視でも stop_requested.flag を検知して終了

デバッグ / テスト:
- KABUSYS_ENV=paper_trading または development では MockBrokerClient を使うため、kabuステーション を用意せずに動作検証が可能。
- MockBrokerClient の挙動は paper_fill_mode（instant / partial / never / reject）で制御。

## 停止・保護
- 停止フラグ: data/stop_requested.flag を作成すると両プロセスは安全にループを終了します。
- Kill スイッチ: settings.kill_flag_path（デフォルト data/kill.flag）を検知すると発注ループが全ての active 注文をキャンセルして停止します。KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に kill.flag を自動でクリアします（本番では 0 を推奨）。

## 開発者向け補足
- 設定読み込み
  - モジュール kabusys.config.Settings を通じてアプリ設定を参照します。settings = Settings() / from kabusys.config import settings を使用してください。
- 注文永続化
  - OrderRepository は SQLite を使用。orders テーブルは init_orders_db() で初期化可能（冪等）。
- リコンシリエーション
  - 起動時に OrderSent 状態の不確かな注文をブローカーと照合して状態を回復します（Reconciler）。
- WebSocket push
  - KabuStationClient.stream_push() はブロッキングで接続を維持し、切断時は再接続します。WebSocket の受信は ExecutionEngine の別スレッドで処理されます。
- ロギング
  - setup_logging() でアプリ名を指定してロギング設定を行います（各 run_*.py 内で呼ばれています）。

## ディレクトリ構成（抜粋）
- src/kabusys/
  - __init__.py
  - config.py                — 環境変数読み込み・Settings
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 起動前設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py       — Monitoring 起動スクリプト
  - execution/               — 発注ロジック一式
    - broker_api.py
    - kabu_client.py
    - mock_client.py
    - broker_factory.py
    - order_record.py
    - order_repository.py
    - order_manager.py
    - execution_engine.py
    - reconciler.py
    - risk_manager.py
  - data/                    — データ関連ユーティリティ
    - calendar_management.py
    - news_collector.py
    - (jquants クライアント等)
  - monitoring/              — 監視関連（DB初期化・SystemMonitor等）
  - utils/                   — ログ設定やプロセス優先度設定等ユーティリティ
  - その他: strategy, execution の上位結合コード（プロジェクトにより追加）

（実際のプロジェクトでは config/*.yaml や scripts/generate_config.py、data ディレクトリ等が存在する想定です）

## よくある操作例
- .env を作ったらまず検証:
  - python -m kabusys.validate_config
- ペーパートレードで動かす:
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
- 監視をバックグラウンドで回す:
  - python -m kabusys.run_monitoring &

---

不明点や README に追加したい使用例・運用手順があれば教えてください。必要に応じて起動フロー図や設定テンプレート（.env.example）も作成します。