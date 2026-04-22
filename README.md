# KabuSys

日本株自動売買システムのサンプル実装。  
本リポジトリは発注エンジン、リスクガード、監視、データ収集など主要コンポーネントを含み、ローカル開発／ペーパートレード／本番（設計上）の環境で動作することを想定しています。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は次のような責務を持つコンポーネント群で構成されています。

- 設定管理（.env 読み込み / Settings）
- 環境設定ウィザード（対話式で .env を生成）
- 起動前設定検証ツール（.env と config/*.yaml の存在・整合性検査）
- 発注エンジン（ExecutionEngine）：Signal Queue ベースで発注を実行、WebSocket push を処理
- ブローカー抽象化（BrokerAPIProtocol）とモック実装（MockBrokerClient）
- 注文永続化（SQLite）
- リスク管理（3 層の Gate）
- リコンシリエーション（再起動後の同期）
- 監視（SystemMonitor ポーリングループ）
- データ系ユーティリティ（カレンダ管理、ニュース収集など）

設計方針として、DB 操作とビジネスロジックを分離し、テストしやすいモジュール構成になっています。開発時／CI では MockBrokerClient を使って kabu station を不要にできます。

---

## 機能一覧

主要な機能：

- .env 自動読み込み（プロジェクトルートの `.env` および `.env.local`、OS 環境変数優先）
- 対話式 .env 作成ウィザード（python -m kabusys.config_setup）
- 設定検証 CLI（python -m kabusys.validate_config）
  - 必須環境変数のチェック、KABUSYS_ENV/LOG_LEVEL の妥当性、DB パスや config/*.yaml の検査
  - --strict オプションで警告も失敗扱いに
- ExecutionEngine（発注エンジン）
  - Signal の読み込み、Gate 1/2/3 によるリスクガード、WebSocket push ドレイン
  - paper_trading 時は MockBrokerClient を使用し paper_trading 用 SQLite を使用
- Broker クライアント群
  - KabuStationClient（kabu station REST 実装）
  - MockBrokerClient（テスト用）
- Order の状態管理（OrderRecord）と状態遷移検証
- OrderRepository（SQLite による永続化）と DB 初期化ユーティリティ
- Reconciler（起動時の OrderSent の突合とポジション差分検出）
- 監視ループ（run_monitoring）: polling で SystemMonitor を回す（MONITOR_POLL_INTERVAL で間隔上書き可能）
- データユーティリティ（市場カレンダー管理、RSS ニュース収集など）

---

## セットアップ手順

前提：Python 3.9+ を想定（typing や標準ライブラリの利用から）。プロジェクトルートは `.git` または `pyproject.toml` を含むディレクトリとして自動検出されます。

1. リポジトリをクローン／取得
2. 仮想環境を作成して有効化（例）

   - Unix/macOS:
     python -m venv .venv
     source .venv/bin/activate

   - Windows:
     python -m venv .venv
     .\.venv\Scripts\activate

3. 必要なパッケージをインストール

   必須（最小限）ライブラリの例:
   - duckdb
   - httpx
   - websocket-client
   - defusedxml

   validate_config の YAML パースを有効にするには PyYAML が必要です。

   例:
   pip install duckdb httpx websocket-client defusedxml PyYAML

   （プロジェクトに requirements.txt / pyproject.toml があればそれを利用してください）

4. .env を作成する

   - 対話式に作成:
     python -m kabusys.config_setup

   - 手動で作成: `.env.example` を参照して `.env` を作成（リポジトリに例ファイルがある場合）

5. 設定検証を行う（推奨）
   python -m kabusys.validate_config
   - 警告も失敗扱いにする場合:
     python -m kabusys.validate_config --strict

---

## 環境変数（主なもの）

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants API リフレッシュトークン（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）

任意 / 推奨（デフォルト値あり）:
- KABUSYS_ENV — 実行環境: development | paper_trading | live（デフォルト: development）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード専用 SQLite（default: data/paper_trading.db）
- LOG_LEVEL — DEBUG | INFO | WARNING | ERROR | CRITICAL（デフォルト: INFO）
- KABU_API_BASE_URL — kabu station base URL（デフォルト: http://localhost:18080/kabusapi）
- LINE_CHANNEL_ACCESS_TOKEN — LINE 通知トークン（任意）
- LINE_USER_ID — LINE 通知先ユーザーID（任意）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアする（0/1、デフォルト 0）
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、デフォルト 60）

自動読み込みの振る舞い:
- OS 環境変数 > .env.local > .env の優先順位で読み込みます。
- 自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト用途）。

ファイルパス（デフォルト）:
- stop flag: data/stop_requested.flag（run_monitoring/run_execution が検知）
- kill flag: data/kill.flag（ExecutionEngine の kill switch トリガ）

---

## 使い方

1. 環境作成（対話式）
   python -m kabusys.config_setup
   - ウィザードを完了すると `.env` を保存します。
   - 秘匿項目は表示がマスクされます。

2. 設定検証
   python -m kabusys.validate_config
   - 警告・エラーを表示。--strict をつけると警告もエラー扱いで exit(1) します。
   - PyYAML が未インストールだと config/*.yaml の中身検査はスキップされます（ファイル存在チェックは行う）。

3. 監視ループ起動
   python -m kabusys.run_monitoring
   - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更できます（デフォルト 60 秒）。
   - 監視は KABUSYS_ENV にかかわらず本番 sqlite_path を使用します。

4. 発注エンジン起動（本番相当のセッション）
   python -m kabusys.run_execution
   - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、paper_trading 用 SQLite に記録します。
   - 起動時に kill.flag が存在すると、KILL_FLAG_CLEAR_ON_START に応じて起動を拒否またはクリアします。
   - 実行中に data/stop_requested.flag を作成すると安全に停止します。

5. ローカルテスト（MockBrokerClient を直接使う）
   実装では BrokerClientFactory が settings を見て mock client を返すため、KABUSYS_ENV を development/paper_trading にすれば実際の kabu station を不要にテスト可能です。

---

## 主要ファイルとディレクトリ構成

以下は本リポジトリの主要なソース配置（抜粋）です。

- src/
  - kabusys/
    - __init__.py
    - config.py              — 環境変数読み込みと Settings
    - config_setup.py        — .env 対話式ウィザード
    - validate_config.py     — 起動前設定検証 CLI
    - run_monitoring.py      — 監視ポーリングループ起動スクリプト
    - run_execution.py       — ExecutionEngine 起動スクリプト
    - data/
      - calendar_management.py
      - news_collector.py
      - jquants_client.py (想定)
    - execution/
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
      - ...（その他関連モジュール）
    - monitoring/
      - monitoring_db.py
      - system_monitor.py
    - utils/
      - logging_setup.py
      - process_priority.py
    - strategy/               — 戦略ロジック（存在する場合）
    - monitoring/             — 監視関連（存在する場合）

（実際のファイルは上記リストを参照してください。config/*.yaml は外部設定ファイル群です）

---

## 実行時の注意点 / 運用メモ

- KABUSYS_ENV の値は "development", "paper_trading", "live" のいずれかにしてください。live を使うと本番向けの挙動（警告、通知など）が強化されます。
- run_monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する旨に注意してください（監視データは本番に統合して収集する設計）。
- run_execution は paper_trading の場合に paper_trading 用 SQLite を使用して本番 DB と分離します。
- 停止制御:
  - 一時停止・シャットダウンは data/stop_requested.flag を作成することで行えます（run_* スクリプトが検知して安全停止）。
  - kill.flag はエンジン側で kill switch のトリガとして使用します。起動時に存在する kill.flag に対しては KILL_FLAG_CLEAR_ON_START の値で挙動が変わります（0=起動拒否、1=自動クリアして起動）。
- validate_config は PyYAML がインストールされている場合に config/*.yaml のパース検査も行います。インストールがない場合は YAML 内容検査をスキップしますが、ファイルの存在はチェックします。
- 開発・CI で外部 API を呼びたくない場合は KABUSYS_ENV を development/paper_trading に設定し、MockBrokerClient を使用してください。

---

## 参考コマンドまとめ

- .env 対話式作成:
  python -m kabusys.config_setup

- 設定検証:
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict

- 監視起動:
  python -m kabusys.run_monitoring

- 発注エンジン起動:
  python -m kabusys.run_execution

---

必要であれば README にサンプル .env テンプレートや docker / systemd ユニット例、ユニットテストの実行方法（pytest）などを追記できます。どの情報を追加したいか教えてください。