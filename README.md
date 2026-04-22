KabuSys — 日本株自動売買システム
================================

概要
----
KabuSys は日本株向けの自動売買システムの骨組み（ライブラリ + 実行スクリプト）です。
- シグナルに基づく発注フロー（ExecutionEngine）
- 発注状態管理（OrderRecord / OrderRepository / OrderManager）
- ブローカー抽象（KabuStationClient / MockBrokerClient）
- リスク制御（3段階ガード: Gate1〜3、サーキットブレーカー、レート制限）
- 起動時リコンシリエーション（Reconciler）
- 監視デーモン（SystemMonitor を起動する run_monitoring）
- .env 対応の設定管理と対話式ウィザード / 検証ツール

注意: 本リポジトリの Live broker（実ブローカー接続）は未実装です。paper_trading / development では MockBrokerClient を使用します。

主な機能
--------
- 環境設定ウィザード（.env の対話形式生成）: python -m kabusys.config_setup
- 設定検証ツール（.env と config/*.yaml の事前チェック）: python -m kabusys.validate_config
- 発注エンジン実行スクリプト（ExecutionEngine）: python -m kabusys.run_execution
- 監視ループ実行スクリプト（SystemMonitor ポーリング）: python -m kabusys.run_monitoring
- ブローカー抽象層（Protocol）とモック実装（テスト用）
- DuckDB / SQLite を用いたデータ保存（デフォルト path: data/kabusys.duckdb, data/monitoring.db）
- RSS ニュース収集やマーケットカレンダー管理（Data モジュール群）
- 発注リコンシリエーション（クラッシュ復旧のための同期処理）

セットアップ手順
----------------
1. リポジトリをクローン
   - git clone <repo-url>
   - cd <repo-root>

2. Python 仮想環境を作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - pip install -r requirements.txt
   - （requirements.txt がない場合は主に以下を入れてください）
     - duckdb, httpx, websocket-client, pyyaml, defusedxml

4. 初期設定ファイルの準備
   - python -m kabusys.config_setup
     - 対話式で .env を生成／更新します（.env は決してコミットしないでください）
   - 生成した .env を確認・必要に応じ編集してください

5. 設定検証
   - python -m kabusys.validate_config
   - 警告も失敗させたい場合:
     - python -m kabusys.validate_config --strict

使い方
------
- .env の自動読み込み挙動
  - 起動時、自動でプロジェクトルート（.git または pyproject.toml を基準）を検出し、
    .env を読み込み（既存 OS 環境変数は上書きしない）、.env.local があればそれで上書きします。
  - 自動ロード無効化: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

- 主要 CLI
  - 環境設定ウィザード:
    - python -m kabusys.config_setup
  - 設定検証:
    - python -m kabusys.validate_config
    - --strict を付けると警告もエラー扱いで exit(1)
  - 実行エンジン（発注）:
    - python -m kabusys.run_execution
    - KABUSYS_ENV=paper_trading または development では MockBrokerClient を使用
  - 監視ループ:
    - python -m kabusys.run_monitoring
    - ポーリング間隔を変更: MONITOR_POLL_INTERVAL=10 など（秒）

- 重要な環境変数（README 抜粋）
  - 必須
    - JQUANTS_REFRESH_TOKEN — J-Quants API 用リフレッシュトークン
    - KABU_API_PASSWORD — kabuステーション API パスワード
  - 主要任意 / 設定
    - KABUSYS_ENV — 実行環境: development | paper_trading | live
    - DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
    - SQLITE_PATH — 監視 DB（デフォルト: data/monitoring.db）
    - LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
    - KABU_API_BASE_URL — kabu station base URL
    - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — 本番通知用（live 時に推奨）
    - KILL_FLAG_CLEAR_ON_START — 起動時に kill flag を自動クリアするか（0/1）
  - 実行時ファイル
    - PID ファイル: デフォルト data/execution.pid（Settings.pid_file_path）
    - kill flag: data/kill.flag（Settings.kill_flag_path）
    - stop フラグ（監視／実行プロセス停止トリガ）: data/stop_requested.flag

- 実装上の注意事項
  - Paper trading / development では MockBrokerClient が使われ、発注・約定の振る舞い（instant/partial/never/reject）を設定できます。
  - live 環境は現時点で未実装（BrokerClientFactory は NotImplementedError を投げます）。
  - ExecutionEngine はセッション（シグナル処理 8:50-9:10、push ドレイン 9:10-15:30）を想定しています。

ディレクトリ構成（主要ファイル）
-------------------------------
以下は src/kabusys 以下の主要ファイル / モジュールと役割の抜粋です。

- src/kabusys/
  - __init__.py
  - config.py
    - Settings クラス: 環境変数から設定を取得・検証
    - .env の自動読み込みロジック（.env, .env.local）
  - config_setup.py
    - 対話式ウィザードで .env を生成 / 更新
  - validate_config.py
    - 起動前に .env と config/*.yaml の整合性をチェックする CLI
  - run_execution.py
    - ExecutionEngine を起動するエントリポイント
  - run_monitoring.py
    - SystemMonitor ポーリングループ起動スクリプト
  - execution/
    - broker_api.py: Broker API の Protocol・データモデル・Factory
    - kabu_client.py: kabuステーション向け実装（HTTP/WebSocket）
    - mock_client.py: テスト用 MockBrokerClient
    - broker_factory.py: Settings に基づくクライアント生成
    - execution_engine.py: 発注エンジンのコアロジック
    - order_record.py: 注文状態と遷移ロジック（純粋ロジック）
    - order_repository.py: SQLite ベースの永続化層
    - order_manager.py: OrderRecord と broker を繋ぐ外向け API
    - reconciler.py: 起動時のリコンシリエーション
    - risk_manager.py: Gate1〜3 のリスク制御
  - data/
    - calendar_management.py: マーケットカレンダー管理（DuckDB）
    - news_collector.py: RSS ニュース収集（defusedxml, URL 正規化等）
    - jquants_client など（外部 API 統合用モジュール想定）
  - monitoring/
    - monitoring_db.py, system_monitor.py など（監視 DB と監視処理）
  - utils/
    - logging_setup.py, process_priority.py 等の補助ユーティリティ

補足・運用メモ
--------------
- .env は決して Git にコミットしないでください（config_setup でも警告あり）。
- validate_config により、必須環境変数の欠如やプレースホルダ値、KABUSYS_ENV の不正値、YAML パースエラーなどを事前に検出できます。
- 実運用では KABUSYS_ENV=live の場合、LINE 通知などのアラート設定が重要です（validate_config は live 時に未設定なら警告を出します）。
- kill.flag（Settings.kill_flag_path）によりエンジンを即時停止できます。起動時に KILL_FLAG_CLEAR_ON_START=1 を設定すると既存の kill.flag を自動クリアしますが、本番では推奨されません。

ライセンス / 貢献
-----------------
（ここにプロジェクトのライセンス情報や貢献方法を記載してください）

問題報告 / 要望
----------------
不具合や要望は Issue を立ててください。実運用での live ブローカー接続、運用手順書、config/*.yaml のジェネレータ等は今後の改善候補です。

以上が本コードベースの README です。必要であれば「実行例」「.env のサンプル」「設定ファイル生成スクリプトの使い方」などの追記も作成します。どの部分をより詳細に記載しますか？