# KabuSys

日本株自動売買システム（KabuSys）のリポジトリ向け README（日本語）

## プロジェクト概要
KabuSys は日本株の自動売買フレームワークです。ブローカークライアント（kabuステーション）とのやり取り、発注の状態管理、リスクガード、リコンシリエーション、監視ループ、マーケットカレンダー管理、ニュース収集など、実運用を想定したコンポーネント群を提供します。テスト／開発用にブローカーのモック実装（MockBrokerClient）も備え、ペーパートレード環境での検証が可能です。

主な設計方針：
- 発注ロジックと永続化（SQLite）を分離しクラッシュ耐性を考慮
- 3段階のリスクガード（Gate1/2/3）
- 起動時の自動リコンシリエーション（OrderSent → broker の照合）
- .env による環境設定と対話式ウィザード／検証 CLI を提供

## 機能一覧
- 環境設定ウィザード（.env 生成 / 更新）: `kabusys.config_setup`
- 設定検証 CLI（.env と config/*.yaml の存在・基本検証）: `kabusys.validate_config`
- 監視プロセス（SystemMonitor のポーリングループ）: `kabusys.run_monitoring`
- 発注実行エンジン（ExecutionEngine）: `kabusys.run_execution`
- ブローカークライアント
  - KabuStationClient（kabuステーション REST/WebSocket 実装）
  - MockBrokerClient（テスト用モック、fill_mode 指定可）
- 注文状態管理：OrderRecord（状態遷移の検証）
- 永続化層：OrderRepository（SQLite）
- リスク管理：RiskManager（Gate1/2/3）、RateLimiter、Circuit Breaker、ドローダウン監視
- リコンシリエーション：Reconciler（再起動時の自動復旧）
- データユーティリティ：マーケットカレンダー管理、ニュース収集（RSS）
- モニタリング DB 初期化ロジック、ログ設定、プロセス優先度設定ユーティリティ

## 必要環境
- Python 3.9+（型アノテーションや一部ライブラリ互換性のため）
- 推奨パッケージ（代表例）
  - duckdb
  - httpx
  - websocket-client
  - PyYAML（config/*.yaml のパース検証を行う場合）
  - defusedxml
  - その他（プロジェクト内で利用されるユーティリティにより追加）

（プロジェクトには requirements.txt を別途用意する想定です。実行環境に合わせて pip install してください。）

## 環境変数（重要）
必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

主な任意／推奨項目（一部）:
- KABUSYS_ENV: `development` | `paper_trading` | `live`（デフォルト: development）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（デフォルト: data/monitoring.db）
- LOG_LEVEL: `DEBUG`|`INFO`|`WARNING`|`ERROR`|`CRITICAL`（デフォルト: INFO）
- KABU_API_BASE_URL: kabu station のベース URL
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: 本番環境でのアラート通知用
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（0/1）
- MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、デフォルト 60）

注意:
- .env ファイルは決して Git にコミットしないこと（ウィザードはその旨を出力します）。

## セットアップ手順（例）
1. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate (または Windows の場合 .venv\Scripts\activate)

2. 依存パッケージをインストール
   - pip install duckdb httpx websocket-client defusedxml PyYAML
   - （requirements.txt がある場合は pip install -r requirements.txt）

3. プロジェクトルートに移動（pyproject.toml または .git があるルート）
   - 自動的に .env をロードする仕組みがあるため、プロジェクトルートを正しく検出できる位置で実行してください。

4. 対話式で .env を作成 / 更新
   - python -m kabusys.config_setup
   - ウィザードに従い入力してください（シークレットはマスクされます）。
   - 保存後に README の案内に従い検証を実行してください。

5. 設定検証
   - python -m kabusys.validate_config
   - --strict を付けると警告も exit 1 として扱います:
     - python -m kabusys.validate_config --strict

6. DB の初期化（監視 DB / orders テーブル 等）
   - 実行スクリプトが起動時に必要なテーブルを作成します（例: init_monitoring_db, init_orders_db）。
   - 実行前に data/ ディレクトリ等の親ディレクトリが作成されていることを確認してください（自動作成される場合あり）。

## 使い方（主なコマンド）
- 環境ウィザード（.env 生成/更新）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- 監視ループ起動
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒で上書き可能（例: export MONITOR_POLL_INTERVAL=30）

- 実行エンジン起動（発注）
  - python -m kabusys.run_execution
  - KABUSYS_ENV が `paper_trading` の場合は MockBrokerClient を使用して data/paper_trading.db に記録します。
  - run_execution は PID ファイル（data/execution.pid 等）を書き、stop フラグ（data/stop_requested.flag）で終了を制御します。

- プログラムからの利用（ライブラリ的に）
  - from kabusys.config import settings
  - token = settings.jquants_refresh_token
  - settings.env / settings.is_live / settings.is_paper 等で環境判定可能

## 運用上のワークフロー（例）
1. .env を作成（config_setup）
2. validate_config で検証（--strict 推奨、本番前）
3. 監視プロセスを起動（run_monitoring）
4. 開始当日に run_execution を起動
5. 停止は data/stop_requested.flag を作成してプロセスに検知させるか、kill.flag による挙動を確認のうえ停止

## 注意事項 / 本番運用上のガード
- KABUSYS_ENV=live を設定すると強い警告が出ます。LINE 通知などアラート設定を必ず確認してください。
- KILL_FLAG_CLEAR_ON_START=1 を本番で有効にすると既存の kill.flag を起動時にクリアしてしまうため推奨されません（デフォルト 0）。
- .env ファイルはセキュアに管理し、リポジトリに含めないでください。
- 本システムでの「Filled は即座に Closed にならない」など設計上の注意点があります。コード内の docstring を参照して挙動を理解してください。

## ディレクトリ構成（主要ファイル）
（プロジェクトルート: src/kabusys を想定）

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数の自動読み込み（.env, .env.local）、Settings クラス
  - config_setup.py
    - .env 対話式ウィザード（python -m kabusys.config_setup）
  - validate_config.py
    - 起動前の設定検証 CLI（python -m kabusys.validate_config）
  - run_monitoring.py
    - SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py
    - ExecutionEngine 起動スクリプト（発注）
  - execution/
    - broker_api.py          — BrokerAPIProtocol、データモデル、例外、factory
    - kabu_client.py         — kabu station REST / WebSocket 実装
    - mock_client.py         — MockBrokerClient（テスト用）
    - broker_factory.py      — Settings に基づくクライアント生成
    - order_record.py        — 注文状態モデルと遷移ロジック
    - order_repository.py    — SQLite 永続化層（orders テーブル）
    - order_manager.py       — 外向き注文 API（create/send/sync/cancel）
    - execution_engine.py    — ExecutionEngine（シグナル処理 / push ドレイン）
    - reconciler.py          — 起動時のリコンシリエーション
    - risk_manager.py        — Gate1/2/3 を実装するリスク管理
  - data/
    - calendar_management.py — マーケットカレンダー管理（next_trading_day 等）
    - news_collector.py      — RSS ベースのニュース収集（raw_news 保存）
    - (jquants_client 等の補助モジュールを想定)
  - monitoring/
    - monitoring_db.py       — 監視 DB（SQLite）初期化とロギングユーティリティ（参照）
    - system_monitor.py      — システム監視ロジック（参照）
  - utils/
    - logging_setup.py       — 共通ログ設定ユーティリティ
    - process_priority.py    — プロセス優先度設定ユーティリティ
  - strategy/ (想定)
    - 戦略関連コード（ポートフォリオ生成 / signals）

（上記はリポジトリ内の主要モジュールの一覧と役割。詳細は各ファイルの docstring を参照してください。）

## 開発者向けメモ
- MockBrokerClient を用いることで外部環境（kabuステーション）を必要とせずテスト可能
  - fill_mode: "instant" | "partial" | "never" | "reject"
- ExecutionEngine と Monitoring はそれぞれ別プロセスで運用することを想定
- 発注のクラッシュ耐性は OrderManager の 2 相永続化や Reconciler の照合ロジックで考慮済み
- duckdb はシグナル・マーケットデータの分析に利用

## 参考コマンドまとめ
- .env ウィザード:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict
- 監視起動:
  - python -m kabusys.run_monitoring
- 実行エンジン起動:
  - python -m kabusys.run_execution

---

README の内容は主要ファイルの docstrings を参照して手早くまとめています。実運用やデプロイ手順（systemd / supervisor / container 化、ログローテーション、監視アラートの構成など）は環境に合わせて別途ドキュメント化してください。必要ならデプロイ手順や systemd ユニットファイル例、Dockerfile のテンプレートなども作成できます。必要であれば指示してください。