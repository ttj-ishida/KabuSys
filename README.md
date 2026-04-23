KabuSys — 日本株自動売買システム（README）
======================================

概要
----
KabuSys は日本株の自動売買を目的とした小規模なフレームワークです。  
主に以下の責務を持ちます。

- シグナルに基づく発注ワークフロー（ExecutionEngine）
- ブローカー API 抽象化（kabu station クライアント / Mock クライアント）
- 注文永続化（SQLite）
- 起動時リコンシリエーション（Reconciler）
- リスクガード（3 段階：Gate1/Gate2/Gate3）
- 監視用ポーリング（SystemMonitor）
- 環境設定ウィザード・設定検証ツール

本リポジトリはライブラリ部分（src/kabusys）と、起動用スクリプト（python -m kabusys.run_execution 等）を提供します。

主な機能
--------
- 環境設定ウィザード（python -m kabusys.config_setup）
  - .env を対話式に生成 / 更新
- 設定検証 CLI（python -m kabusys.validate_config）
  - .env と config/*.yaml の存在／簡易検証。--strict で警告も失敗扱いに
- 実行エンジン（ExecutionEngine）
  - シグナルプル型の発注ループ、WebSocket の push ドレイン、kill switch など
- ブローカー API 層
  - 実装：KabuStationClient（kabu station REST）および MockBrokerClient（テスト用）
  - factory で環境に応じて生成
- 注文永続化（SQLite）
  - orders テーブル、active/uncertain の取得 API
- リスク管理（RiskManager）
  - 余力、重複、ポジション上限、レート制限、サーキットブレーカー、ドローダウン監視
- リコンシリエーション（Reconciler）
  - 起動時に OrderSent 状態の注文をブローカーと突合して同期
- データ系ユーティリティ
  - DuckDB を使ったマーケットカレンダー管理、ニュース収集等
- 監視プロセス（run_monitoring）
  - システム監視のポーリングループ（SQLite / DuckDB 使用）

セットアップ手順
----------------
以下は基本的なセットアップ手順の例です。用途に合わせて調整してください。

1. リポジトリをクローン
   - git clone <repo_url>
   - cd <repo_root>

2. Python 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存パッケージのインストール
   - requirements.txt がある場合:
     - pip install -r requirements.txt
   - または最低限（実行に必要な主要ライブラリ）:
     - pip install duckdb httpx websocket-client defusedxml PyYAML
   - テスト・開発用に Mock クライアントのみ使う場合は kabu station 環境は不要

4. 初期設定ファイルの作成
   - 対話式ウィザードを実行して .env を作成:
     - python -m kabusys.config_setup
   - 生成された .env を編集して必須項目を設定してください。

5. 設定検証
   - python -m kabusys.validate_config
   - 警告も含めて失敗扱いにしたい場合:
     - python -m kabusys.validate_config --strict

使い方（主要コマンド）
--------------------

- 環境設定ウィザード（.env の作成/更新）
  - python -m kabusys.config_setup
  - 対話式に項目を入力し、.env に保存します。

- 設定検証
  - python -m kabusys.validate_config
  - オプション: --strict（警告も exit(1) として扱う）
  - exit code: 0=OK（警告なしまたは警告のみ）, 1=FAIL（エラーあり、または --strict で警告あり）

- 実行エンジン起動（実際の発注セッション）
  - python -m kabusys.run_execution
  - KABUSYS_ENV により振る舞いが変わります（development / paper_trading / live）
  - paper_trading は MockBrokerClient を使用し、paper_trading 用 SQLite（デフォルト: data/paper_trading.db）に記録します

- 監視プロセス起動
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を変更可能（デフォルト: 60）
  - 監視は環境にかかわらず本番用 sqlite_path を使用します

主要な環境変数（抜粋）
--------------------
- 必須
  - JQUANTS_REFRESH_TOKEN — J-Quants API 用トークン（必須）
  - KABU_API_PASSWORD — kabu station API パスワード（必須）
- 任意（デフォルトあり / 機能に応じて必要）
  - KABUSYS_ENV — 実行環境（development / paper_trading / live）。デフォルト: development
  - DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH — 監視 DB（デフォルト: data/monitoring.db）
  - LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
  - KABU_API_BASE_URL — kabu station のベース URL（デフォルト: http://localhost:18080/kabusapi）
  - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID — 本番でのアラート通知に使用
  - KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（1=yes、0=no、デフォルト 0）

安全に関する注意
----------------
- KABUSYS_ENV=live を使うと本番発注が行われます。必ず全設定（特に API パスワード、通知設定、kill flag の取り扱い）を確認してください。
- .env は絶対にリポジトリへコミットしないでください（README ヘッダの警告や config_setup の出力にも明記あり）。
- 起動前に python -m kabusys.validate_config で設定を確認することを推奨します。
- run_execution/run_monitoring は stop フラグや kill.flag を監視し、安全に停止できる仕組みを内蔵しています。flag ファイルの場所は設定（デフォルト data/kill.flag など）で確認してください。

プログラムからの利用例
--------------------
- 設定の参照:
  - from kabusys.config import settings
  - token = settings.jquants_refresh_token
- Broker クライアント生成（プログラム的に）:
  - from kabusys.execution.broker_api import create_broker_api
  - api = create_broker_api(mock=True, fill_mode="instant")

ディレクトリ構成（主要ファイル）
------------------------------
以下は src/kabusys 以下の主要ファイル・モジュール（抜粋）です。

- src/kabusys/
  - __init__.py
  - config.py               — 環境変数の読み込み・Settings
  - config_setup.py         — .env 対話式ウィザード
  - validate_config.py      — 設定検証 CLI
  - run_execution.py        — 実行エンジン起動スクリプト
  - run_monitoring.py       — 監視プロセス起動スクリプト
  - execution/
    - __init__.py
    - broker_api.py         — BrokerAPI の Protocol / データモデル / factory
    - kabu_client.py        — kabu station REST クライアント
    - mock_client.py        — テスト用モック実装
    - broker_factory.py     — Settings に応じたクライアント生成
    - order_record.py       — 注文状態モデル・遷移
    - order_repository.py   — SQLite 永続化層
    - order_manager.py      — 発注ワークフロー API
    - execution_engine.py   — メイン発注エンジン（シグナル処理 / push ドレイン）
    - reconciler.py         — 起動時リコンシリエーション
    - risk_manager.py       — 3 段階リスクガード
    - ...（その他）
  - data/
    - calendar_management.py — マーケットカレンダー（DuckDB）
    - news_collector.py      — RSS ニュース収集
    - ...（その他）
  - monitoring/
    - monitoring_db.py      — 監視用 DB 初期化・ログ関数
    - system_monitor.py     — システム監視ロジック
  - utils/
    - logging_setup.py      — ロギング初期化
    - process_priority.py   — プロセス優先度設定

補足情報 / トラブルシュート
--------------------------
- PyYAML が未インストールだと validate_config は YAML の中身チェックをスキップしますが、ファイルの存在は確認します。YAML の構文チェックを行いたい場合は pyyaml をインストールしてください。
- KabuStationClient を使う場合は kabuステーション® アプリがローカル PC 上で稼働しており、指定した KABU_API_BASE_URL にアクセス可能である必要があります。
- run_execution では PID ファイル（デフォルト data/execution.pid）と停止フラグ（data/stop_requested.flag）を利用します。運用ツールからこれらを操作してプロセス管理を行えます。
- Paper trading は MockBrokerClient による安全なテスト運用フローを提供します。実 DB と分離して data/paper_trading.db に記録します。

ライセンス・寄稿
----------------
（プロジェクトのライセンスやコントリビュート方法をここに記載してください。省略可）

以上。開発者向けに API やユーティリティ関数のドキュメントを別途整備しておくと運用が楽になります。必要であれば README に追加するサンプル .env テンプレートや systemd ユニット例なども作成できます。必要な場合はお知らせください。