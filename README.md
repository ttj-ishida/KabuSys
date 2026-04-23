# KabuSys

日本株自動売買システムのコアモジュール群（ライブラリ＆起動スクリプト群）です。  
本リポジトリは発注エンジン、リスクガード、リコンシリエーション、監視、データ収集などの主要コンポーネントを含みます。

## 概要
- 環境変数／.env ベースで設定を管理し、起動前に設定検証を行うツールを提供します。
- 発注フローは Signal Queue をプルして Gate1/2/3 の三段階リスクガードを通して実行します。
- 実運用（live）・ペーパートレード（paper_trading）・開発（development）を切り替え可能。
- paper_trading / development では Mock ブローカーを使って DB を分離して動作可能（実際の取引を行わない）。
- 起動時にクラッシュや中断状態からの自動復旧（Reconciliation）処理を行います。

## 主な機能一覧
- 環境設定ウィザード（対話式 .env 生成）: python -m kabusys.config_setup
- 設定検証 CLI（.env と config/*.yaml を起動前にチェック）: python -m kabusys.validate_config
- ExecutionEngine（発注エンジン）
  - シグナル処理（8:50–9:10）と WebSocket push ドレイン（9:10–15:30）
  - OrderState マシン、OrderRepository (SQLite)、OrderManager、RiskManager、Reconciler を備える
- Broker クライアント実装
  - MockBrokerClient（テスト／ペーパー用）
  - KabuStationClient（kabuステーション API 用）
- Reconciler（起動時の OrderSent 照合、ポジション差分照合）
- Monitoring（SystemMonitor のポーリングループ）
- Data モジュール（カレンダー管理、ニュース収集等）

## セットアップ手順（開発向け）
1. Python のインストール（推奨: Python 3.10 以上）
2. 仮想環境の作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 依存パッケージのインストール
   - pip install -r requirements.txt
   - ※ requirements.txt がない場合は少なくとも以下をインストールしてください:
     - duckdb, httpx, websocket-client, defusedxml
     - config YAML の構文チェックを使う場合は PyYAML をインストールしてください（任意）
4. .env の準備
   - 対話式ウィザードを使う: python -m kabusys.config_setup
   - あるいは手動でプロジェクトルートに .env を作成（.env.example を参照）
   - 自動ロード: デフォルトで .env と .env.local が自動的に読み込まれます
     - 自動ロードを無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください

## 必要な環境変数（主要）
- 必須
  - JQUANTS_REFRESH_TOKEN — J-Quants API 用リフレッシュトークン
  - KABU_API_PASSWORD — kabuステーション API パスワード
- 任意（デフォルト値あり / 役割により必須となる場合あり）
  - KABUSYS_ENV: execution 環境 ("development" / "paper_trading" / "live") （デフォルト: development）
  - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH: 監視 DB（デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（デフォルト: data/paper_trading.db）
  - LOG_LEVEL: ログレベル（"DEBUG" / "INFO" / "WARNING" / "ERROR" / "CRITICAL"）
  - KABU_API_BASE_URL: kabu station API ベース URL（デフォルト: http://localhost:18080/kabusapi）
  - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: 本番での通知設定（任意）
  - KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（"0" / "1"）
- .env 自動ロード順:
  - OS 環境変数 > .env > .env.local（.env.local は既存の値を上書き）

※ 起動前に設定検証を強く推奨します（下記参照）。

## 設定検証
- 実行:
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict  （警告も FAIL 扱いにする）
- 機能:
  - 必須環境変数の有無チェック
  - KABUSYS_ENV / LOG_LEVEL の妥当性チェック
  - DB パス（親ディレクトリ存在）チェック
  - config/*.yaml の存在と PyYAML があればパースチェック（PyYAML 未インストール時はパースをスキップして警告）
  - KABUSYS_ENV=live の場合に追加ガード（LINE 設定や Kill Flag 設定の確認）

## 実行方法
- ExecutionEngine（発注エンジン）起動:
  - python -m kabusys.run_execution
  - 挙動:
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用、paper_sqlite_path に記録（本番 DB と分離）
    - 起動時に Reconciler による自動同期を実行（OrderSent の復旧等）
    - stop の仕組み: プロジェクトルートの data/stop_requested.flag が存在すると停止
    - PID ファイル: デフォルト data/execution.pid（環境変数 PID_FILE_PATH で変更可）
    - kill.flag の取り扱い: settings.kill_flag_clear_on_start に応じて起動可否を決定
- Monitoring（監視ループ）起動:
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒、デフォルト 60）
  - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する設計
- ログ設定:
  - ログは utils.logging_setup を利用しており、LOG_LEVEL 環境変数で制御します

## 停止・運用上の注意
- 強制停止・外部停止: data/stop_requested.flag を作成するとループが検知して安全に停止します。
- Kill Switch:
  - kill.flag（デフォルトパスは data/kill.flag）を検出すると kill_switch() が発動し全 active 注文をキャンセルします。
  - KILL_FLAG_CLEAR_ON_START=1 を誤って本番で使うと起動時に kill.flag を自動クリアしてしまうため注意してください（本番では 0 推奨）。
- 本番運用時（KABUSYS_ENV=live）の設定は慎重に確認してください。validate_config の警告は無視しないこと。

## Settings API（プログラムからの利用）
アプリケーションコード内から設定を使うには:
- from kabusys.config import settings
- 例:
  - settings.jquants_refresh_token
  - settings.kabu_api_password
  - settings.duckdb_path, settings.sqlite_path, settings.paper_sqlite_path
  - settings.env, settings.is_live, settings.is_paper, settings.is_dev

## ディレクトリ構成（主要ファイル）
以下はプロジェクト内の主要モジュール／ファイル配置の抜粋です（src/kabusys を想定）。

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / .env 自動ロード・Settings 定義
  - config_setup.py          — 対話式 .env ウィザード（python -m kabusys.config_setup）
  - validate_config.py       — 設定検証 CLI（python -m kabusys.validate_config）
  - run_execution.py         — 発注エンジン起動スクリプト（python -m kabusys.run_execution）
  - run_monitoring.py       — 監視ループ起動スクリプト（python -m kabusys.run_monitoring）

  - execution/
    - __init__.py
    - broker_api.py          — Broker API 用データモデル・Protocol・ファクトリ
    - broker_factory.py      — Settings に基づく Broker クライアント生成
    - kabu_client.py         — KabuStationClient（HTTP + WebSocket クライアント）
    - mock_client.py         — MockBrokerClient（テスト用）
    - order_record.py        — OrderState と OrderRecord（状態遷移ロジック）
    - order_repository.py    — SQLite ベースの永続化（orders テーブル）
    - order_manager.py       — OrderManager（外向き API、送信・同期・キャンセル）
    - execution_engine.py    — ExecutionEngine（シグナル処理 + push ドレイン）
    - reconciler.py          — Reconciliation（起動時自動復旧）
    - risk_manager.py        — 3段階リスクガード

  - data/
    - calendar_management.py — 市場カレンダ管理（DuckDB に基づく判定関数）
    - news_collector.py      — RSS ニュース収集（セキュア実装）
    - jquants_client.py      — （データ取得用クライアント、ここでは参照あり）

  - monitoring/
    - monitoring_db.py      — 監視用 SQLite スキーマ/書込ヘルパー
    - system_monitor.py     — SystemMonitor 実装（run_monitoring で使用）

  - utils/
    - logging_setup.py      — ログ初期化ユーティリティ
    - process_priority.py   — プロセス優先度設定ユーティリティ

- config/
  - system_config.yaml, data_config.yaml, strategy_config.yaml, risk_config.yaml, execution_config.yaml, monitoring_config.yaml
  - （YAML 設定ファイル群。validate_config が存在確認・パースチェックを行います）

- data/
  - (デフォルト保存先フォルダ。DB / PID / フラグファイルが置かれます)

## そのほかメモ
- config/*.yaml はプロジェクト固有の設定を格納するためのファイル群です。validate_config は PyYAML があればパースしてチェックします。生成スクリプト（scripts/generate_config.py）を参照する旨のメッセージが出ます。
- テストや CI で自動的に環境を操作する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると .env の自動読み込みを回避できます。
- MockBrokerClient の fill_mode（instant / partial / never / reject）や paper_trading の DB 分離など、開発時の挙動制御が可能です。

必要に応じて README にサンプル .env や起動例（systemd ユニット、Dockerfile、CI スクリプト）を追加できます。追加したい内容や、より詳しい運用手順（本番運用チェックリスト等）があれば指示してください。