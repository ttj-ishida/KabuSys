# KabuSys

日本株自動売買システムのサンプル実装（ライブラリ／起動スクリプト群）。  
このリポジトリは、発注フロー、リスクガード、リコンシリエーション、監視、データ（カレンダー・ニュース収集）などの主要コンポーネントを含む構成になっています。

## プロジェクト概要
- 発注エンジン（ExecutionEngine）により、シグナルに基づく発注・状態管理を行います。
- Broker クライアントは環境に応じて実装を切り替え可能（開発／ペーパートレードではモックを使用）。
- リスク管理は Gate1（シグナルレベル） / Gate2（エグゼキューション） / Gate3（約定後メトリクス）で構成。
- 起動時に設定検証や .env の対話式セットアップウィザードを提供します。
- 監視プロセス（SystemMonitor）を定期実行するためのスクリプトを含みます。
- DuckDB / SQLite をデータ保存に使用します。

## 主な機能一覧
- 環境変数・.env 管理（自動ロード、.env/.env.local）
- 対話式 .env 作成ウィザード（python -m kabusys.config_setup）
- 起動前設定検証 CLI（python -m kabusys.validate_config、--strict オプションあり）
- ExecutionEngine：シグナルの読み込み、発注、push ドレイン、kill switch、PID 管理
- Broker 抽象化（BrokerAPIProtocol）＋ Mock / kabu station 実装
- Order 管理：OrderRecord（状態遷移ロジック）、OrderRepository（SQLite 永続化）、OrderManager（外向き API）
- Reconciler：再起動時の OrderSent 照合とポジション差分検出
- RiskManager：3 段階のリスクガード（余力・重複・ポジション上限、レート制限／サーキット、ドローダウン）
- データモジュール：マーケットカレンダー管理（DuckDB）、ニュース収集（RSS）
- Monitoring：監視ループ（別プロセスで起動）

## セットアップ手順（開発向け）
1. Python 環境を用意
   - 推奨: Python 3.9+（コードは型ヒントに対応しています）
   - 仮想環境作成例:
     - python -m venv .venv
     - source .venv/bin/activate (Windows: .venv\Scripts\activate)

2. 依存パッケージをインストール
   - 必要なライブラリ（主なもの）:
     - duckdb
     - httpx
     - websocket-client
     - defusedxml
     - PyYAML （YAML 検証を有効にする場合）
   - 例:
     - pip install duckdb httpx websocket-client defusedxml PyYAML

   > 補足: プロジェクトに requirements.txt がない場合は上記を手動でインストールしてください。

3. プロジェクトルートに .env を用意
   - 推奨は対話式ウィザードで作成:
     - python -m kabusys.config_setup
   - もしくは手動で .env を作成（例は下の「.env の例」参照）。

4. 設定検証
   - .env を作成したら起動前に検証:
     - python -m kabusys.validate_config
     - 警告もエラー扱いにする（CI 等）場合:
       - python -m kabusys.validate_config --strict

5. データベース初期化（orders テーブルなど）
   - 実行プロセス（run_execution / run_monitoring）が起動時に DB 初期化処理を呼ぶ箇所を備えています。SQLite 接続は Settings の SQLITE_PATH（または PAPER_TRADING_SQLITE_PATH）に対して行われます。

## 使い方（起動例）
- 環境変数の自動ロード
  - パッケージ読み込み時にプロジェクトルート（.git または pyproject.toml）を探索して `.env` / `.env.local` を自動ロードします。
  - OS 環境変数は上書きされません。`.env.local` は override=True（ただし OS の既存キーは保護）です。
  - 自動ロードを無効化するには:
    - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

- .env の対話式作成
  - python -m kabusys.config_setup
  - ウィザード完了後に .env を保存できます。

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告があっても exit code 1（FAIL）になります。

- 実行エンジン起動（発注）
  - python -m kabusys.run_execution
  - KABUSYS_ENV が paper_trading / development の場合は MockBrokerClient を使用します（paper_trading では paper DB に記録）。
  - KABUSYS_ENV=live は Live ブローカー実装が未実装のため起動しません（NotImplementedError）。

- 監視ループ起動
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒単位で上書き（デフォルト 60 秒）。
  - 監視は KABUSYS_ENV にかかわらず本番 sqlite_path を使用します。

- 停止フラグ / PID
  - 停止リクエストはリポジトリルートの data/stop_requested.flag を作成することで行えます（該当ファイルを検出するとループが終了します）。
  - kill スイッチは Settings.kill_flag_path（デフォルト data/kill.flag）を利用。起動時に kill.flag が存在すると、KILL_FLAG_CLEAR_ON_START の設定に応じて起動を拒否またはクリアします。
  - PID ファイルは Settings.pid_file_path（デフォルト data/execution.pid）に書き出されます。

## .env の例
最小（必須）:
- JQUANTS_REFRESH_TOKEN=your_refresh_token
- KABU_API_PASSWORD=your_password

推奨（例）:
- KABUSYS_ENV=development
- JQUANTS_REFRESH_TOKEN=your_refresh_token
- KABU_API_PASSWORD=your_password
- KABU_API_BASE_URL=http://localhost:18080/kabusapi
- DUCKDB_PATH=data/kabusys.duckdb
- SQLITE_PATH=data/monitoring.db
- LOG_LEVEL=INFO
- LINE_CHANNEL_ACCESS_TOKEN=your_line_token
- LINE_USER_ID=your_line_user_id
- KILL_FLAG_CLEAR_ON_START=0

（対話式作成: python -m kabusys.config_setup を推奨）

## 注意点・トラブルシューティング
- 必須環境変数が未設定だと実行時に例外を投げる箇所があります。validate_config で事前チェックを行ってください。
- PyYAML がインストールされていない場合、validate_config は YAML のパース検証をスキップします（警告）。
- KABUSYS_ENV=live は本番動作向けのフラグですが、現在 Live ブローカークライアントは未実装です。paper_trading / development を使用してください。
- MONITOR_POLL_INTERVAL に 0 や負の数を設定すると無効値としてデフォルト（60秒）にフォールバックします。
- run_execution / run_monitoring は DB コネクション（SQLite / DuckDB）を開きます。path が指す親ディレクトリがない場合は自動作成されない箇所があります（validate_config が親ディレクトリの有無を警告します）。

## ディレクトリ構成（主要ファイル）
以下はパッケージ内の主要モジュール一覧（抜粋）です。実際のファイルは src/kabusys 以下に存在します。

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数/.env 読み込みと Settings クラス
  - config_setup.py           — .env 対話式ウィザード
  - validate_config.py        — 起動前設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — SystemMonitor 起動スクリプト
  - execution/
    - __init__.py
    - broker_api.py           — Broker API の Protocol / データモデル / ファクトリ
    - kabu_client.py          — kabuステーション REST クライアント
    - mock_client.py          — MockBrokerClient（テスト / ペーパー用）
    - broker_factory.py       — Settings に応じてクライアント生成
    - order_record.py         — OrderRecord（状態遷移ロジック）
    - order_repository.py     — SQLite 永続化（orders テーブル）
    - order_manager.py        — 外向き注文 API（作成 / 送信 / 同期 / 取消）
    - execution_engine.py     — ExecutionEngine（シグナル処理・push ドレイン・kill）
    - reconciler.py           — 再起動時リコンシリエーション
    - risk_manager.py         — リスクガード（Gate1/2/3）
  - data/
    - calendar_management.py  — マーケットカレンダー管理（DuckDB）
    - news_collector.py       — RSS ニュース収集
    - (jquants_client.py などはデータ取得用モジュール)
  - monitoring/
    - monitoring_db.py        — 監視用 SQLite テーブル初期化 / ログ
    - system_monitor.py       — システム監視ロジック
  - utils/
    - logging_setup.py        — ロギングセットアップヘルパ
    - process_priority.py     — プロセス優先度設定

（上記はコード内参照に基づく主要構成です。実際のファイル一覧はリポジトリを参照してください）

## 開発者向けメモ
- ExecutionEngine は時間枠（発注時間帯・マーケットクローズ）を持ち、その範囲に応じて _process_signals / _drain_push_queue を実行します。テスト時はこれらを直接呼ぶ運用が可能です。
- OrderManager の send_order はクラッシュ耐性を考慮した2相永続化（OrderSent 状態の永続化 → ブローカー送信 → broker_order_id の永続化 → OrderAccepted）を実装しています。
- Reconciler は OrderSent の状態をブローカー照合で復旧し、ポジション差分を検出します。
- RiskManager はトークンバケツによるレート制御、サーキットブレーカー、ドローダウン監視を備えます。

---

まずは .env を用意（または python -m kabusys.config_setup）し、python -m kabusys.validate_config で検証してください。その後、python -m kabusys.run_execution（または run_monitoring）でプロセスを起動できます。開発・検証目的では KABUSYS_ENV=paper_trading を推奨します。