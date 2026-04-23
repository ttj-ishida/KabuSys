# KabuSys

日本株自動売買システムのコアライブラリ（README）。このリポジトリはシンプルな ExecutionEngine / Monitoring / 設定管理 / ブローカー抽象化などを含む実装です。

## 概要
KabuSys は、kabuステーション やモックブローカーを使って株式発注を行うための内部ライブラリ群です。主な目的は以下のとおりです。

- シグナルに基づく発注エンジン（ExecutionEngine）
- 発注の状態管理（OrderRecord / OrderRepository / OrderManager）
- ブローカー抽象化（実ブローカー／モック切替）
- 起動時のリコンシリエーション（Reconciler）
- 3段階のリスクガード（RiskManager）
- 監視ループ（SystemMonitor 用の run_monitoring）
- 設定ウィザード（.env の対話式生成）と設定検証 CLI
- データ周り（マーケットカレンダー管理、ニュース収集など）

本リポジトリはテスト・開発で使いやすいモック実装（MockBrokerClient）を用意しており、実運用（live）用の実ブローカークライアントは将来実装予定の箇所があります。

## 主な機能一覧
- .env 対話式ウィザード（kabusys.config_setup）
- 起動前設定検証 CLI（kabusys.validate_config）: 必須環境変数や config/*.yaml の存在・YAML パース確認
- ExecutionEngine: シグナルの読み込み、Gate1/2/3 によるリスクガード、発注／プッシュ処理、kill switch
- Order 管理: OrderRecord（状態遷移検証）、SQLite ベースの OrderRepository、OrderManager（送信・同期・キャンセル）
- Broker 抽象化: BrokerAPIProtocol／create_broker_api。MockBrokerClient と KabuStationClient（kabu station 用）を切替
- Reconciler: 再起動時に OrderSent の注文を突合して状態を回復し、ポジション差分を検出
- RiskManager: 余力・重複・ポジション上限・レート制限・サーキットブレーカー・ドローダウン監視
- Monitoring 用起動スクリプト（run_monitoring）: 定期ポーリングでシステム情報を記録
- Data モジュール: カレンダー管理（next_trading_day 等）、ニュース収集（RSS）など

## セットアップ手順（開発向け）
1. Python を用意
   - 推奨: Python 3.9+（コードは型ヒント・一部標準ライブラリ挙動を想定）
2. リポジトリをクローンしてワークディレクトリへ移動
   - git clone <repo>
   - cd <repo>
3. 仮想環境を作成・有効化（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
4. 必要パッケージをインストール
   - 実際の requirements.txt がある場合はそれを使ってください。例:
     - pip install duckdb httpx websocket-client defusedxml PyYAML
   - 注意: PyYAML は validate_config の YAML 内容検証で使用します（未インストールでも検証は「存在チェックのみ」になります）。
5. .env 初期化（推奨）
   - python -m kabusys.config_setup
     - 対話式に .env を生成 / 更新します。
6. 設定検証
   - python -m kabusys.validate_config
   - すべて合格なら 0 を返します。警告を FAIL 扱いにしたい場合は --strict を付与します。

## 使い方（主なコマンド）
- 環境設定ウィザード（.env の生成）
  - python -m kabusys.config_setup
- 設定検証
  - python -m kabusys.validate_config
  - オプション: --strict（警告を失敗扱いして exit(1)）
- 実行エンジン起動（本番相当 / ペーパートレード）
  - python -m kabusys.run_execution
  - KABUSYS_ENV に応じて:
    - development / paper_trading → MockBrokerClient を使用
    - live → 現状 NotImplementedError（将来の実ブローカー実装を想定）
- 監視ループ起動（SystemMonitor ポーリング）
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可能（デフォルト: 60）

### 主要な環境変数
（config_setup で設定可能な主要項目）
- 必須:
  - JQUANTS_REFRESH_TOKEN — J-Quants API 用リフレッシュトークン
  - KABU_API_PASSWORD — kabuステーション API パスワード
- 任意 / 推奨:
  - KABUSYS_ENV — execution 環境（development / paper_trading / live。デフォルト: development）
  - DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH — 監視 DB（デフォルト: data/monitoring.db）
  - LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
  - KABU_API_BASE_URL — kabu station のベース URL（デフォルト http://localhost:18080/kabusapi）
  - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID — 本番アラート用（live の場合は未設定だと警告になります）
  - KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（0/1、デフォルト 0。本番では 0 推奨）

### 停止・制御
- stop flag:
  - data/stop_requested.flag を作成すると run_execution / run_monitoring のループが検知して終了します。
- kill flag:
  - data/kill.flag を利用して ExecutionEngine の起動拒否や稼働中の kill switch のトリガーに使用します。
  - KILL_FLAG_CLEAR_ON_START=1 にすると起動時に自動クリアします（開発用、注意して使用）。

## 開発時のポイント・注意
- ExecutionEngine はシグナル処理（指定時刻範囲）と push ドレインを組み合わせた実装です。テストでは _process_signals() / _drain_push_queue() を直接呼ぶことが可能です。
- Order の状態遷移は OrderRecord.transition_to で厳密に制御され、不正な遷移は InvalidStateTransitionError を投げます。
- 発注フローはクラッシュ耐性を考慮した 2 相永続化の設計（OrderSent を先に永続化 → broker 呼び出し → broker_order_id を保存 → Accepted 更新）になっています。リコンシリエーションで残った不確定注文を復旧します。
- RiskManager にはトークンバケツによるレート制限とサーキットブレーカーがあります。API エラーが一定数を越えるとサーキットブレーカーが OPEN になり発注を抑止します。
- MockBrokerClient を使えば kabuステーション を起動せずに機能テストが可能です（PAPER_FILL_MODE によって fill の挙動を切替）。

## ディレクトリ構成（抜粋）
- src/kabusys/
  - __init__.py
  - config.py                  — 環境変数読み込み・Settings
  - config_setup.py            — .env 対話式ウィザード CLI
  - validate_config.py         — 起動前設定検証 CLI
  - run_execution.py           — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — Monitoring ポーリング起動スクリプト
  - execution/
    - __init__.py
    - broker_api.py            — BrokerAPIProtocol, データモデル, ファクトリ
    - broker_factory.py        — Settings によるクライアント生成
    - kabu_client.py           — kabuステーション API 実装（HTTP + WebSocket）
    - mock_client.py           — テスト用モック
    - order_record.py          — Order の状態遷移ロジック
    - order_repository.py      — SQLite 永続化層
    - order_manager.py         — 発注 API（作成・送信・同期・キャンセル）
    - execution_engine.py      — ExecutionEngine（シグナル処理・push ドレイン）
    - reconciler.py            — 起動時リコンシリエーション
    - risk_manager.py          — Gate1/2/3 リスクガード
  - monitoring/
    - monitoring_db.py         — 監視 DB 初期化 / 書き込み（参照のみ）
    - system_monitor.py        — 監視ロジック（参照）
  - data/
    - calendar_management.py   — マーケットカレンダー管理
    - news_collector.py        — RSS ニュース収集
    - jquants_client.py        — J-Quants API クライアント（参照）
  - utils/
    - logging_setup.py         — ロギング初期化（参照）
    - process_priority.py      — プロセス優先度設定ユーティリティ

（上記はコードベースにある主要ファイルを抜粋したツリーです）

## トラブルシュート
- PyYAML 未インストール:
  - validate_config は PyYAML がなければ YAML 内容検証をスキップし、該当の旨を警告します。静的に YAML の正しさを確認したい場合は PyYAML をインストールしてください。
- 設定検証でエラーが出る:
  - 必須環境変数（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD 等）が未設定の場合はエラーになります。.env を作成し再度 validate を実行してください。
- 本番環境（KABUSYS_ENV=live）での安全機構:
  - LINE トークン未設定や KILL_FLAG_CLEAR_ON_START の設定などで警告が出ます。本番では警告を無視せず適切な値を設定してください。
- 起動中に stop_requested.flag を検知すると安全にシャットダウンします。テストで即停止させたい場合は該当ファイルを作成してください。

## 開発者向けメモ
- ExecutionEngine は日次ターゲット日（EngineConfig.target_date）に基づき DuckDB からシグナルを読み込んで発注します。テストでは date を指定してインメモリ DB で検証できます。
- OrderRepository は SQLite のスキーマ初期化関数 init_orders_db(conn) を提供します。起動時に init_monitoring_db / init_orders_db を呼ぶことで DB スキーマを準備してください。
- Broker の本実装（KabuStationClient）は httpx と websocket-client を使っています。実運用では kabuステーション（ローカルアプリ）の起動と API 設定が必要です。

---

最後に: まずは仮想環境に依存パッケージを入れて、python -m kabusys.config_setup で .env を作成 → python -m kabusys.validate_config で確認 → python -m kabusys.run_execution（または run_monitoring）で動作確認する流れを推奨します。必要があれば README の補足や典型的な .env.example を追加で作成します。