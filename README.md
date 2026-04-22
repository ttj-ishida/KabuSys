KabuSys — 日本株自動売買システム (README)
=================================

プロジェクト概要
---------------
KabuSys は日本株の自動売買を想定した軽量なフレームワークです。  
主要コンポーネントはシグナル取り込み → リスクチェック → 発注 → リコンシリエーション → 監視のワークフローを提供します。  
実運用（live）・ペーパートレード（paper_trading）・開発（development）を想定した設定切替と、kabuステーション API / Mock クライアントの切り替え機能を備えています。

主な特徴（機能一覧）
-------------------
- 環境設定ウィザード（対話的に .env を生成・更新）
  - python -m kabusys.config_setup
- 起動前設定検証 CLI（.env と config/*.yaml をチェック）
  - python -m kabusys.validate_config [--strict]
- ExecutionEngine：Signal → 発注の一連フロー（Gate1/2/3 による 3 段階リスクチェック）
- Broker クライアント群
  - MockBrokerClient（fill_mode: instant/partial/never/reject）: テスト・開発用
  - KabuStationClient（HTTP / WebSocket 実装）: 本番想定（要 kabuステーション）
- 注文状態管理（OrderRecord の状態遷移と永続化）
- リコンシリエーション（起動時の OrderSent の突合せ、ポジション差分検出）
- 監視プロセス（SystemMonitor 用ポーリングループ）
- データモジュール
  - 市場カレンダー管理（J-Quants 取得を想定）
  - ニュース収集・正規化ロジック（RSS 収集、SSRF 対策、正規化、ID 生成）
- SQLite / DuckDB を用いたローカル永続化（デフォルトパスは data/*.db）

前提（Requirements）
-------------------
- Python 3.10+（型アノテーションや match 等に依存する箇所はないが、typing の新仕様を利用）
- 推奨パッケージ（例）:
  - duckdb
  - httpx
  - websocket-client
  - PyYAML（config/*.yaml のパース検証に必要）
  - defusedxml
- 実行に必要な外部依存:
  - 本番で kabuステーション を使う場合は kabuステーションアプリが動作していること

セットアップ手順
----------------
1. リポジトリをクローン
   - git clone ...

2. 仮想環境を作成して有効化
   - python -m venv .venv
   - source .venv/bin/activate  （Windows は .venv\Scripts\activate）

3. 必要パッケージをインストール（例）
   - pip install duckdb httpx websocket-client PyYAML defusedxml

   ※ 実プロジェクトでは requirements.txt / pyproject.toml を参照してください。

4. 環境変数準備（.env）
   - 初回は対話式ウィザードで .env を生成するのが簡単です:
     - python -m kabusys.config_setup
   - 重要な必須環境変数:
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
   - 任意／上書き可能な設定例:
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト development
     - DUCKDB_PATH（デフォルト data/kabusys.duckdb）
     - SQLITE_PATH（監視 DB、デフォルト data/monitoring.db）
     - LOG_LEVEL（DEBUG/INFO/...、デフォルト INFO）
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（本番でのアラート用）
   - 自動 .env ロード:
     - パッケージ読み込み時にプロジェクトルート（.git または pyproject.toml がある場所）を探索し、.env → .env.local の順で読み込みます。
     - OS 環境変数が優先されます。
     - 自動ロードを無効にする場合:
       - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

使い方（主要 CLI / スクリプト）
----------------------------

- 環境ウィザード（.env 作成・更新）
  - python -m kabusys.config_setup
  - .env を対話形式で生成・既存値の再利用が可能。

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告も FAIL として exit(1) を返します。
  - PyYAML が未インストールの場合は YAML 内容検証はスキップされます。

- 実行エンジン（Execution）
  - python -m kabusys.run_execution
  - KABUSYS_ENV によって MockBrokerClient が使われます（paper_trading / development）。live 未実装（NotImplementedError）。

- 監視プロセス（Monitoring）
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL（秒）でポーリング間隔を変更可能（デフォルト 60 秒）。
  - 監視は environment にかかわらず本番用の sqlite_path を使用します（監視データは共有）。

- 注意: 停止制御
  - data/stop_requested.flag ファイルを作成するとループは検知して停止します。
  - PID ファイル・kill.flag 等を利用した起動制御を行います（settings でパス指定）。

設定と挙動のポイント
-------------------
- .env 読み込み順:
  - OS 環境 > .env.local（override=True）> .env（override=False）
  - protected パラメータで OS 環境変数を上書きしない設計。

- KABUSYS_ENV:
  - 有効値: development, paper_trading, live
  - live は本番動作を想定し、LINE 通知設定や KILL_FLAG_CLEAR_ON_START の確認など追加チェックあり。

- データベース:
  - デフォルト: DUCKDB_PATH=data/kabusys.duckdb, SQLITE_PATH=data/monitoring.db
  - paper_trading では paper_sqlite_path (data/paper_trading.db) を使用して本番 DB と分離。

- MockBrokerClient:
  - fill_mode: instant / partial / never / reject により挙動を切り替え可能。テスト時に便利。

簡易フロー（ExecutionEngine）
----------------------------
1. 起動時にリコンシリエーション（Reconciler）を実行し、OrderSent 等の不確定注文を broker 側と照合。
2. シグナル処理（デフォルト 8:50-9:10）でシグナルを読み込み、Gate1（シグナルレベル）・Gate2（実行レベル）を経て発注。
3. 9:10-15:30 の間は WebSocket Push をドレインして注文状態同期や Gate3（ドローダウン監視）を実行。
4. 異常検知時は kill_switch() を呼んで全 active 注文をキャンセルしセッションを停止。

ディレクトリ構成
----------------
（主要ファイルのみ抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数読み込み / Settings
  - config_setup.py           — .env 作成ウィザード（CLI）
  - validate_config.py        — 起動前設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — SystemMonitor 起動スクリプト
  - execution/
    - __init__.py
    - broker_api.py           — Broker Protocol / データモデル / ファクトリ
    - broker_factory.py       — Settings に基づくクライアント生成
    - kabu_client.py          — kabuステーション REST/WebSocket クライアント
    - mock_client.py          — MockBrokerClient（テスト用）
    - order_record.py         — Order の状態遷移ロジック
    - order_repository.py     — SQLite 永続化層
    - order_manager.py        — 発注フローの外向き API
    - execution_engine.py     — ExecutionEngine（セッション管理）
    - reconciler.py           — リコンシリエーション（起動復旧）
    - risk_manager.py         — Gate1/2/3 のリスクガード
  - data/
    - calendar_management.py  — 市場カレンダー管理（J-Quants 連携想定）
    - news_collector.py       — RSS 取得 / 前処理 / 保存ロジック
    - (jquants_client.py 等のクライアント想定)
  - monitoring/
    - monitoring_db.py        — 監視 DB 初期化 / ログ書き込み（参照）
    - system_monitor.py       — 監視ロジック（参照）
  - utils/
    - logging_setup.py        — ロギング設定
    - process_priority.py     — プロセス優先度設定
  - その他: config/*.yaml（システム/データ/戦略/リスク/実行/監視の YAML 設定）

補足・運用上の注意
-----------------
- .env は機密情報を含むため絶対に Git にコミットしないでください（config_setup.py の警告参照）。
- KABUSYS_ENV=live の際は LINE 通知等の設定を必ず確認してください（validate_config による注意喚起あり）。
- 本リポジトリサンプルでは live 用の KabuStationClient の利用は想定できますが、実運用前に十分な検証が必要です（NotImplementedError を投げる箇所がある場合があります）。
- データベースファイルの親ディレクトリが存在しない場合、起動時に自動作成されることがありますが、パーミッション等は事前に確認してください。

ライセンス・貢献
----------------
- 本 README はコードベースに基づく導入・利用説明です。実際の配布リポジトリでは LICENSE・CONTRIBUTING ドキュメントを参照してください。

以上。セットアップや実行で詰まる点があれば、環境変数の内容（機密情報以外）や実行ログを教えてください。必要に応じてトラブルシューティング手順を提供します。