KabuSys — 日本株自動売買システム
================================

概要
----
KabuSys は日本株自動売買システムのコアライブラリ群です。本リポジトリには、環境設定ウィザード、設定検証、発注エンジン、監視ループ、ブローカークライアントの抽象化、リコンシリエーション、リスクガード、マーケットカレンダー管理やニュース収集などの主要コンポーネントが含まれます。  
設計方針として、DB（SQLite / DuckDB）やブローカー API を分離しやすく、テスト時にはモック（MockBrokerClient）で完全に動作検証が可能です。

主な機能
---------
- 環境設定ウィザード（.env の対話式生成 / 更新）
- 起動前設定検証 CLI（環境変数・config/*.yaml の存在・パース検査）
- ExecutionEngine：シグナルプル型の発注エンジン（発注ルール・ドレインループ・WebSocket push 処理）
- Order 管理：OrderRecord（状態遷移）、OrderRepository（SQLite 永続化）、OrderManager（送信 / 同期 / キャンセル）
- Broker 抽象化：BrokerAPIProtocol、MockBrokerClient（テスト用）、KabuStationClient（kabuステーション実装）
- RiskManager：Gate1/2/3 による多層リスクガード（余力、重複、ポジション上限、レート制限、サーキットブレーカー、ドローダウン）
- Reconciler：再起動時の OrderSent 照合とポジション差分検出
- 監視ループ（SystemMonitor）と監視用 DB 初期化（monitoring 用 SQLite）
- データモジュール：JPX カレンダー管理（DuckDB）、ニュース収集（RSS）

セットアップ手順
----------------
前提
- Python 3.9+ を想定（型注釈に一部 >=3.9 の構文を使用）
- プロジェクトルートで作業すること（README と同階層に src ディレクトリがある構成）

インストール（例）
1. リポジトリをクローン／取得してプロジェクトルートへ移動
2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）
3. 必要パッケージをインストール（プロジェクトに requirements.txt がある場合はそれを使用）
   - pip install duckdb httpx websocket-client defusedxml
   - YAML の内容検証を有効にする場合: pip install pyyaml
   - （任意）pip install -e . で開発インストール（setup があれば）

注意:
- 本 README はコードベースから推定した依存を列挙しています。プロジェクトに requirements.txt / pyproject.toml がある場合はそちらを優先してください。

.env の準備
1. 対話式ウィザードで .env を作成・更新:
   - python -m kabusys.config_setup
   - デフォルトはプロジェクトルートの .env（--env-file でパス指定可）
2. 自動ロード:
   - config モジュールはプロジェクトルートを自動検出して .env / .env.local を自動読み込みします。自動読み込みを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

必須環境変数
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

主な任意・補助的な環境変数
- KABUSYS_ENV（development | paper_trading | live、デフォルト: development）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（監視用、デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（ペーパートレード専用 SQLite、デフォルト: data/paper_trading.db）
- LOG_LEVEL（DEBUG|INFO|WARNING|ERROR|CRITICAL）
- KABU_API_BASE_URL（kabu station API のベース URL）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（本番でのアラート用）
- KILL_FLAG_CLEAR_ON_START（0/1、本番で kill.flag を自動クリアするか）
- MONITOR_POLL_INTERVAL（監視ループのポーリング秒数、デフォルト: 60）

設定検証
--------
.env、config/*.yaml の初期検証に以下を使用します:
- python -m kabusys.validate_config
- 警告を FAIL 扱いにするには --strict を付与:
  - python -m kabusys.validate_config --strict

使い方（実行例）
----------------
実行時はプロジェクトルートで、src をパッケージとして使える状態（PYTHONPATH に src が含まれる、もしくは開発インストール）で行ってください。

1. 環境設定ウィザード（.env 作成）
   - python -m kabusys.config_setup

2. 設定検証
   - python -m kabusys.validate_config
   - python -m kabusys.validate_config --strict

3. 監視ループ起動
   - python -m kabusys.run_monitoring
   - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を変更可

4. 発注（Execution）起動
   - python -m kabusys.run_execution
   - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し paper_trading 用 DB（PAPER_TRADING_SQLITE_PATH）に記録します

停止・制御
- 実行エンジン / 監視はプロジェクトルートの data/stop_requested.flag の存在を検出してループ停止を行います（スクリプトから終了トリガーを与える場合に使用）。
- kill.flag（デフォルト: data/kill.flag）を使った Kill Switch 機能があります。ExecutionEngine は起動時 / ループ内に kill.flag を検出すると全 active 注文をキャンセルして停止します。起動時に clear したい場合は KILL_FLAG_CLEAR_ON_START=1 を設定します（本番では 0 推奨）。
- 各プロセスは pid ファイルを data 以下に出力します（Settings.pid_file_path で指定可）。

設計上の注意点
- ExecutionEngine は 8:50 のシグナル処理 → 9:10 発注締切 → 15:30 セッション終了の想定で実装されていますが、テスト時はメソッドを直接呼び出して制御できます。
- MockBrokerClient を利用することでブローカー実装なしでローカルにて発注フロー・リスク管理・リコンシリエーションのテストが可能です。
- Reconciler は再起動時に OrderSent の状態をブローカーと突合して状態復旧を行います（broker_order_id の有無や broker 側での状態を参照）。

ディレクトリ構成（主要ファイル）
------------------------------
src/kabusys/
- __init__.py
  - パッケージ定義・バージョン
- config.py
  - 環境変数の読み込み (.env 自動ロード) と Settings クラス
- config_setup.py
  - .env を対話式に作成/更新するウィザード CLI
- validate_config.py
  - .env と config/*.yaml を起動前に検査する CLI（--strict オプション）
- run_execution.py
  - ExecutionEngine 起動スクリプト（メインの発注プロセス）
- run_monitoring.py
  - SystemMonitor ポーリングループ起動スクリプト
- execution/
  - broker_api.py        — Broker API のデータモデル、Protocol、例外、ファクトリ
  - broker_factory.py    — Settings に基づくブローカークライアント生成
  - kabu_client.py       — kabuステーション実装（HTTP / WebSocket）
  - mock_client.py       — テスト用 MockBrokerClient
  - order_record.py      — Order の状態遷移ロジック（純粋ビジネスロジック）
  - order_repository.py  — SQLite を用いた永続化層
  - order_manager.py     — 発注フローの上位 API（作成/送信/同期/キャンセル）
  - execution_engine.py  — 発注エンジン本体（シグナル処理・push ドレイン・kill）
  - reconciler.py        — 再起動時のリコンシリエーション
  - risk_manager.py      — Gate1/2/3 のリスクガード
- data/
  - calendar_management.py — JPX カレンダーの管理（DuckDB）
  - news_collector.py      — RSS からのニュース収集ロジック
- monitoring/
  - monitoring_db.py (参照あり) — 監視用 DB 初期化 / ログ機能（コードは参照されるがここには省略）
- utils/
  - logging_setup.py (参照あり) — ロギング設定ユーティリティ
  - process_priority.py (参照あり) — プロセス優先度設定ユーティリティ
- config/
  - system_config.yaml, data_config.yaml, strategy_config.yaml, risk_config.yaml, execution_config.yaml, monitoring_config.yaml
    - 利用される設定ファイル（存在しない場合は validate_config で警告、PyYAML があればパースも検証）

補足
----
- YAML 内容検証は PyYAML を要求します（validate_config は未インストール時にパースチェックをスキップして警告を出します）。
- ニュース収集では defusedxml を用いて XML 関連の安全対策を行っています（XML Bomb 対策など）。
- DuckDB を使うことで分析向けテーブルをローカルに高速に格納できます。監視・永続化用に SQLite も併用しています。
- 本番環境設定（KABUSYS_ENV=live）では LINE 通知等の設定漏れで警告が出ます。validate_config の --strict で警告をエラー扱いにできます。

ライセンス / 貢献
-----------------
（ここには実際のライセンスや貢献方法を記載してください）

問題や拡張案がある場合は Issue / PR でご提案ください。

以上。必要であれば README にサンプル .env.example の内容やコマンドのより詳細な説明、各設定ファイル（config/*.yaml）のスキーマ説明を追加できます。どの情報を優先して補足しますか？