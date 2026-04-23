# KabuSys

日本株自動売買システムのコアライブラリ（ミニマム実装）。  
このリポジトリは発注フロー（ExecutionEngine）、注文永続化（SQLite）、モック／実ブローカークライアント、監視ループ、データ処理ユーティリティ（カレンダー・ニュース収集）などを含みます。

バージョン: 0.1.0

---

目次
- プロジェクト概要
- 主な機能
- 前提・依存関係
- セットアップ手順
- 使い方（主要コマンド）
- 環境変数（主要項目）
- ディレクトリ構成
- 注意事項

---

プロジェクト概要
- ExecutionEngine による Signal Queue ベースの発注処理（シグナルの読み込み → Gate1/2 を通じて発注 → push ドレインで状態同期）
- OrderRecord / OrderRepository / OrderManager による注文状態管理と永続化（SQLite）
- Broker 抽象化（BrokerAPIProtocol）により MockBrokerClient と KabuStationClient を切り替え可能
- RiskManager による 3 段階のリスクガード（Signal レベル、Execution レート/サーキットブレーカー、約定後のドローダウン監視）
- 設定ウィザード（.env 作成支援）と設定検証 CLI
- 監視（SystemMonitor）を定期ポーリングするスクリプト
- データ関連ユーティリティ（DuckDB を使ったマーケットカレンダー管理、ニュース収集など）

主な機能
- 環境変数 / .env 自動読み込み（config.Settings）
- 対話式 .env ウィザード（kabusys.config_setup）
- 起動前設定検証ツール（kabusys.validate_config。--strict オプションで警告も FAIL 扱い）
- ExecutionEngine（シグナル処理・push ドレイン・kill switch 実装）
- MockBrokerClient（paper_trading / development 用の挙動シミュレーション）
- KabuStationClient（kabuステーション REST API クライアント。トークン管理、REST/WebSocket をサポート）
- SQLite による orders 永続化、リコンシリエーション（起動時の復旧ロジック）
- DuckDB ベースのデータ処理（calendar_management、news_collector）

前提・依存関係
- Python 3.9+
- 推奨ライブラリ（少なくとも実行に必要なもの）
  - duckdb
  - httpx
  - websocket-client
  - pyyaml (設定 YAML 内容検証用。無くても動作するが警告)
  - defusedxml (news collector 用)
- 標準ライブラリ：sqlite3, logging, threading, datetime 等

セットアップ手順（ローカル開発）
1. リポジトリをクローン
2. 仮想環境作成（例）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 依存インストール（例）
   - pip install duckdb httpx websocket-client pyyaml defusedxml
4. .env の作成
   - 対話式ウィザードを使う:
     - python -m kabusys.config_setup
     - 実行後に .env が作成されます（.env の保存確認プロンプトあり）
   - もしくは手動で .env を作成（.env.example を参照する想定）

使い方（主要コマンド）
- 設定ウィザード
  - python -m kabusys.config_setup
    - .env の初期作成 / 更新を対話形式で支援します。
- 設定検証（起動前チェック）
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict
    - 必須環境変数の未設定や config/*.yaml のパースエラー等を検出します。
    - --strict をつけると警告も FAIL（exit code 1）になります。
- 実行エンジン起動（日次セッション）
  - python -m kabusys.run_execution
    - settings に応じて mock broker（paper_trading / development）を使用して発注を行います。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用 SQLite（settings.paper_sqlite_path）を使用して本番 DB と分離します。
    - 起動時に既存の stop flag（data/stop_requested.flag）や kill flag を確認します。
- 監視ループ起動
  - python -m kabusys.run_monitoring
    - SystemMonitor のポーリングループを開始します（デフォルト 60 秒間隔）。
    - 環境変数 MONITOR_POLL_INTERVAL で間隔を変更可能。
- 補助:
  - ライブラリ内 API を直接インポートしてテストや統合利用が可能（例: from kabusys.execution import ExecutionEngine）

主要な環境変数（要点）
- 必須
  - JQUANTS_REFRESH_TOKEN — J-Quants API 用リフレッシュトークン（Settings.jquants_refresh_token）
  - KABU_API_PASSWORD — kabuステーション API パスワード（Settings.kabu_api_password）
- 任意 / 推奨
  - KABUSYS_ENV — 実行環境: development | paper_trading | live（Settings.env）
    - live は注意喚起・追加チェックあり（ただし現状 live ブローカークライアントは未実装）
  - DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH — 監視 DB（デフォルト: data/monitoring.db）
  - LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
  - KABU_API_BASE_URL — kabu station の base URL（デフォルト: http://localhost:18080/kabusapi）
  - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — 本番用アラート通知（任意）
  - KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（0/1、デフォルト 0。開発時のみ 1 を使う）
  - PAPER_FILL_MODE — paper_trading 時のモック約定モード（instant/partial/never/reject）

主要ファイル・モジュール（抜粋）
- src/kabusys/config.py
  - .env 自動読み込みロジック（プロジェクトルート検出）、Settings クラス
- src/kabusys/config_setup.py
  - .env 対話式ウィザード（run_wizard）
- src/kabusys/validate_config.py
  - 起動前設定検証 CLI
- src/kabusys/run_execution.py
  - ExecutionEngine 起動スクリプト（PID/stop フラグ管理、DB 接続）
- src/kabusys/run_monitoring.py
  - SystemMonitor のポーリングループ起動
- src/kabusys/execution/
  - broker_api.py — BrokerAPIProtocol とデータモデル / 例外 / create_broker_api ファクトリ
  - kabu_client.py — 実際の kabu station REST/WebSocket クライアント
  - mock_client.py — テスト用モック（fill_mode 等の挙動指定可能）
  - order_record.py, order_repository.py, order_manager.py — 注文状態モデル・永続化・オペレーション
  - execution_engine.py — 発注エンジンのコアロジック（シグナル読み込み・push ドレイン・kill switch）
  - reconciler.py — 起動時リコンシリエーション（OrderSent の突合、ポジション差分検出）
  - risk_manager.py — Gate1/2/3 のリスクチェック
  - broker_factory.py — Settings に基づいて Broker を生成
- src/kabusys/data/
  - calendar_management.py — DuckDB を使ったマーケットカレンダー管理（営業日判定など）
  - news_collector.py — RSS 収集・前処理（SSRF対策、トラッキングパラメータ除去 等）
- その他
  - src/kabusys/monitoring/**（監視 DB / SystemMonitor 実装）
  - src/kabusys/utils/**（logging_setup, process_priority 等の補助）

ディレクトリ構成（抜粋）
- src/
  - kabusys/
    - __init__.py
    - config.py
    - config_setup.py
    - validate_config.py
    - run_execution.py
    - run_monitoring.py
    - execution/
      - __init__.py
      - broker_api.py
      - broker_factory.py
      - kabu_client.py
      - mock_client.py
      - order_record.py
      - order_repository.py
      - order_manager.py
      - execution_engine.py
      - reconciler.py
      - risk_manager.py
      - ...（その他実装）
    - data/
      - calendar_management.py
      - news_collector.py
      - ...（jquants_client 等）
    - monitoring/
      - monitoring_db.py
      - system_monitor.py
    - utils/
      - logging_setup.py
      - process_priority.py
- config/
  - system_config.yaml
  - data_config.yaml
  - strategy_config.yaml
  - risk_config.yaml
  - execution_config.yaml
  - monitoring_config.yaml
  (※ config/*.yaml は検証や起動で参照されます。存在しない場合はワーニング。PyYAML があればパース検証を行います)

注意事項 / 開発上のポイント
- live ブローカーは未実装: BrokerClientFactory.create() は development/paper_trading で MockBrokerClient を返します。KABUSYS_ENV=live を使う場合は実装を追加してください（現在は NotImplementedError を送出）。
- .env は決してリポジトリにコミットしないでください（config_setup でも注意喚起あり）。
- ExecutionEngine はセッション単位（当日）で動作します。テストやデバッグ時は個別メソッド（_process_signals / _drain_push_queue）を呼んで検証可能です。
- Order のクラッシュ安全性を考慮し、OrderManager.send_order は 2 相永続化（OrderSent 保存 → broker 呼び出し → broker_order_id 保存 → OrderAccepted へ更新）を採用しています。OrderSent のまま残るケースを reconciliation で補う設計です。
- kill.flag / stop_requested.flag を用いた外部停止制御をサポートします（data/ ディレクトリ下にフラグファイルを配置）。
- 設定検証（validate_config）は起動前チェックとして有用です。--strict を CI に組み込むことで警告も合格条件にできます。

問題の報告 / 貢献
- バグ報告や機能追加は Issue を立ててください。プルリクエスト歓迎。

---

README はここまでです。補足（実行例等）が必要であれば、どのコマンドやユースケースの詳細を載せるか教えてください。