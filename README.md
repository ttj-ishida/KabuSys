# KabuSys

日本株自動売買システム（KabuSys） — 軽量な実行エンジン、モック/本番ブローカー抽象、監視・リコンシリエーション・データ処理を備えたリポジトリです。

## 概要
KabuSys は銘柄シグナルから発注を行う ExecutionEngine、発注状態の永続化（SQLite）、発注と約定の突合（Reconciler）、リスクガード（3段階）、モック/実ブローカークライアントなどを提供する自動売買基盤です。DuckDB を分析用 DB として使用し、監視用に独立した SQLite を用います。

主な設計方針：
- 発注フローはクラッシュ耐性（2段階永続化）を重視
- Paper Trading は本番 DB と完全分離（別 SQLite）
- 起動時に設定検証と対話式の .env ウィザードを提供

## 主な機能
- 環境設定ウィザード（python -m kabusys.config_setup）
- 起動前設定検証 CLI（python -m kabusys.validate_config）
- ExecutionEngine（シグナル読み取り → 発注 → push ドレイン）
- MockBrokerClient（テスト / ペーパートレード用）
- KabuStationClient（kabu station REST API クライアント）
- Order 管理（OrderRecord / OrderRepository / OrderManager）
- RiskManager（Gate1/2/3：信号・送信制御・ドローダウン）
- Reconciler（再起動時の自動同期とポジション差分検出）
- 監視プロセスの起動スクリプト（run_monitoring）
- データモジュール：マーケットカレンダー管理、ニュース収集（RSS）
- 各種ユーティリティ（ログ設定、プロセス優先度など）

## 必要条件
- Python 3.10+
- 推奨パッケージ（例）
  - duckdb
  - httpx
  - websocket-client
  - defusedxml
  - PyYAML（YAML 検証を行いたい場合）
- 標準ライブラリ：sqlite3, logging, threading 等

（実際の requirements はプロジェクトの requirements.txt / pyproject.toml を参照してください）

## セットアップ手順（ローカル開発向け）
1. リポジトリをクローン
   - git clone <repo-url>
2. 仮想環境の作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 依存関係をインストール
   - pip install -U pip
   - pip install duckdb httpx websocket-client defusedxml PyYAML
     （プロジェクトに requirements.txt または pyproject.toml があればそれを使用）
4. .env を作成（対話式ウィザード推奨）
   - python -m kabusys.config_setup
     - ウィザードは .env を生成・更新します。機密値はマスク表示されます。
5. 設定を検証
   - python -m kabusys.validate_config
   - 警告を FAIL 扱いにしたい場合:
     - python -m kabusys.validate_config --strict

## 使い方（実行例）
- ExecutionEngine を起動（本番/ペーパートレードに応じて .env で KABUSYS_ENV を設定）
  - python -m kabusys.run_execution
  - 補足：
    - KABUSYS_ENV=paper_trading / development → MockBrokerClient を使い、paper_trading は data/paper_trading.db を使用
    - KABUSYS_ENV=live → 実ブローカー（KabuStationClient）を使う想定（現状未実装箇所あり）
- Monitoring（監視ループ）を起動
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で上書き可能（デフォルト 60 秒）
  - 監視は常に本番の sqlite_path を使用します（環境にかかわらず）
- 設定・起動関連
  - .env の自動読み込み：プロジェクトルート（.git または pyproject.toml を検出）から .env, .env.local を読み込みます
  - 自動ロード無効化（テスト等）：
    - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

## 主要な環境変数
（validate_config / Settings で使用される主なもの）

必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

任意（例・デフォルトを参照）:
- KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
- DUCKDB_PATH — デフォルト: data/kabusys.duckdb
- SQLITE_PATH — デフォルト: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH — ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL (DEBUG / INFO / WARNING / ERROR / CRITICAL)
- KABU_API_BASE_URL (kabu station のベース URL)
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — 本番での通知用
- PID_FILE_PATH — デフォルト: data/execution.pid
- KILL_FLAG_PATH — デフォルト: data/kill.flag
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするフラグ（0/1）

注意：
- run_monitoring は監視 DB に sqlite_path を使用します（環境にかかわらず本番のパスを用いる設計）。
- PAPER_FILL_MODE（instant | partial | never | reject）で Mock の挙動を制御可能（Settings.paper_fill_mode）。

## ディレクトリ構成（抜粋）
以下は主要モジュールのツリー（src/kabusys 内）です：

- src/
  - kabusys/
    - __init__.py
    - config.py               — 環境変数 / Settings
    - config_setup.py         — .env 対話式ウィザード
    - validate_config.py      — 起動前設定検証 CLI
    - run_execution.py        — ExecutionEngine 起動スクリプト
    - run_monitoring.py       — SystemMonitor 起動スクリプト
    - execution/
      - __init__.py
      - broker_api.py         — Broker API 型定義・ファクトリ
      - broker_factory.py     — Settings に応じたブローカー生成
      - kabu_client.py        — kabu station 実装（HTTP/WebSocket）
      - mock_client.py        — MockBrokerClient（テスト用）
      - order_record.py       — Order の状態機械（純粋ロジック）
      - order_repository.py   — SQLite 永続化層
      - order_manager.py      — 発注フロー / API 呼び出しの Orchestrator
      - execution_engine.py   — セッション実行ロジック
      - reconciler.py         — 再起動時のリコンシリエーション
      - risk_manager.py       — Gate1/2/3 のリスク制御
    - data/
      - calendar_management.py — マーケットカレンダー管理
      - news_collector.py      — RSS ニュース収集
      - (jquants_client など外部連携モジュールを想定)
    - monitoring/
      - monitoring_db.py      — 監視 DB 初期化 / ログ機能（参照される）
      - system_monitor.py     — システム監視ロジック（参照される）
    - utils/
      - logging_setup.py      — ロギング初期化
      - process_priority.py   — プロセス優先度設定

（実際のリポジトリには上記以外の補助モジュールやスクリプトが存在する可能性があります）

## 運用メモ / トラブルシューティング
- .env を Git にコミットしないでください（README 内にもウィザードで注意を出します）。
- PyYAML がインストールされていない場合、validate_config は config/*.yaml の内容検証をスキップして警告を出します。
- run_execution/run_monitoring は data ディレクトリや DB ファイルの親ディレクトリを自動作成する場合がありますが、権限やパスに注意してください。
- kill.flag / execution.pid の扱い：
  - 起動時に kill.flag が存在すると起動を拒否します（KILL_FLAG_CLEAR_ON_START=1 の場合は自動クリアして起動可能）。
  - 実行中は data/stop_requested.flag を作ることで外部から停止を要求できます。
- KabuStationClient は kabuステーション® がローカルで稼働している前提です。接続先 URL は KABU_API_BASE_URL で設定。

## 開発・拡張ポイント（参考）
- Live ブローカー統合（BrokerClientFactory の live 実装）
- 非同期化（httpx.AsyncClient / asyncio）による WebSocket / API の改善
- 監視・アラート（LINE 通知ルーティン）
- テストカバレッジ：OrderRecord の状態遷移、RiskManager の各 Gate、Reconciler の動作など

---

問題があればリポジトリ内の各モジュール（特に config.py / execution/*）を参照してください。README の補足や実行例の追加を希望する場合は、使用環境（OS、Python バージョン、インストール方法）を教えてください。