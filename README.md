KabuSys — 日本株自動売買システム (README)
=========================================

概要
----
KabuSys は日本株の自動売買を想定した軽量なフレームワークです。本リポジトリは以下の機能を備えたモジュール群を提供します。

- 環境変数 / .env 管理ウィザード（対話式）と自動ロード
- 起動前の設定検証 CLI
- 発注エンジン（ExecutionEngine）：シグナル読み取り → 発注 → 状態同期（Reconciliation）
- ブローカー抽象化層（実際の kabu station クライアント / テスト用モック）
- 注文永続化（SQLite）
- リスク管理（3段階ガード：Signal / Execution / Metrics）
- 起動時リコンシリエーションと監視プロセス用スクリプト
- データユーティリティ（マーケットカレンダー、ニュース収集等）

主な特徴
--------
- 環境変数 / .env をプロジェクトルートベースで自動ロード（.env, .env.local）
- validate_config による起動前チェック（必須 env／YAML／パス等）
- ExecutionEngine は paper_trading / development では MockBrokerClient を使用し本番環境との分離を実現
- 注文フローはクラッシュ耐性を考慮した 2 相永続化（OrderSent 前後の整合性）
- Reconciler による OrderSent 状態の自動同期とポジション差分検出
- RiskManager による rate limit / circuit breaker / ドローダウン監視
- DuckDB / SQLite を利用した分析・監視データ管理

セットアップ手順
----------------

1. Python の準備
   - 推奨: Python 3.9+（コードは typing | 型ヒントを使用）
   - 仮想環境を作成・有効化しておくことを推奨

2. 必要パッケージのインストール（代表例）
   - 最低限:
     - duckdb
     - httpx
     - websocket-client
     - defusedxml
   - 開発 / 追加機能:
     - PyYAML（config/*.yaml のパース検証に使用）
   - 例:
     - pip install duckdb httpx websocket-client defusedxml PyYAML

   （プロジェクトに requirements.txt が無い場合は上記を手動インストールしてください）

3. .env の作成
   - 対話式ウィザードを使って .env を生成:
     - python -m kabusys.config_setup
   - もしくは .env を手動で作成（.env.example を参考に）

4. 設定検証
   - 起動前に設定を検証:
     - python -m kabusys.validate_config
   - 警告をエラー扱いにする（CI 等で利用）:
     - python -m kabusys.validate_config --strict

使い方
------

基本的な実行方法（プロジェクトルートで実行）:

- 設定ウィザード（.env の作成・更新）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - オプション --strict を付けると警告も失敗と見なして exit(1)

- 発注エンジン（Execution）を起動
  - python -m kabusys.run_execution
  - 注意: KABUSYS_ENV が paper_trading / development の場合は MockBrokerClient を使用します。live は未実装（Broker の Live 実装は NotImplementedError）。

- 監視プロセスを起動
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）

主要な環境変数（抜粋）
---------------------
- 必須:
  - JQUANTS_REFRESH_TOKEN — J-Quants API 用トークン（Settings.jquants_refresh_token）
  - KABU_API_PASSWORD — kabuステーション API パスワード（Settings.kabu_api_password）

- 任意／よく使う:
  - KABUSYS_ENV — 実行環境: development | paper_trading | live（default: development）
  - DUCKDB_PATH — DuckDB ファイルパス（default: data/kabusys.duckdb）
  - SQLITE_PATH — 監視用 SQLite（default: data/monitoring.db）
  - LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
  - KABU_API_BASE_URL — kabu station API ベース URL（default: http://localhost:18080/kabusapi）
  - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — 本番でのアラートに使用
  - KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動でクリアするか（0/1。default 0。開発時のみ 1 推奨）

- その他:
  - MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒）
  - PAPER_FILL_MODE — paper_trading 用モックの fill 動作: instant | partial | never | reject

自動 .env 読み込みの挙動
-----------------------
- 起動時に .env（プロジェクトルート）と .env.local を自動ロードします：
  - OS 環境変数 > .env.local > .env の優先度
- 自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定

安全関連・運用メモ
-------------------
- kill.flag（デフォルト data/kill.flag）:
  - エンジン起動中に kill.flag が存在すると起動拒否（KILL_FLAG_CLEAR_ON_START=1 の場合はクリアして起動）
  - 実行中に検出された場合は kill_switch が発動し全 active 注文をキャンセルする
- PID / stop flag:
  - run_execution は PID ファイル（data/execution.pid など）を書き、外部 stop フラグ stop_requested.flag を検出すると安全に停止します
- 本番環境（KABUSYS_ENV=live）では LINE トークン等の通知設定を必ず確認してください（validate_config の live ガードが警告を出します）

ディレクトリ構成（主要ファイル）
--------------------------------

（パッケージ: src/kabusys/ 以下）

- __init__.py
- config.py                 — 環境変数 / .env の読み込みと Settings クラス
- config_setup.py           — .env 対話式ウィザード
- validate_config.py        — 起動前チェック CLI（.env / config/*.yaml / パス検査）
- run_execution.py          — ExecutionEngine 起動スクリプト
- run_monitoring.py         — SystemMonitor ポーリング起動スクリプト

パッケージ: execution/
- broker_api.py             — BrokerAPI のデータモデル・Protocol・ファクトリ
- broker_factory.py         — Settings に基づくブローカーファクトリ
- kabu_client.py            — kabu station 実クライアント（HTTP + WebSocket）
- mock_client.py            — MockBrokerClient（テスト用）
- order_record.py           — 注文状態（OrderRecord）と遷移ロジック
- order_repository.py       — SQLite による永続化（orders テーブル）
- order_manager.py          — 外向き注文 API（create/send/sync/cancel）
- execution_engine.py       — セッション制御（シグナル処理・push ドレイン）
- reconciler.py             — 再起動時のリコンシリエーション
- risk_manager.py           — 3段階リスクガード

パッケージ: data/
- calendar_management.py    — マーケットカレンダー管理（DuckDB / J-Quants 統合）
- news_collector.py         — RSS ニュース収集・正規化ロジック
- (jquants_client 等の補助モジュールが存在)

パッケージ: monitoring/
- monitoring_db.py          — 監視用 SQLite テーブル初期化 / ログ機能
- system_monitor.py         — システム監視ロジック（run_monitoring で利用）

パッケージ: utils/
- logging_setup.py          — ログ初期化ヘルパ
- process_priority.py       — プロセス優先度設定ユーティリティ

（注）上記のうち一部モジュールは本 README に抜粋されていない実装ファイルを想定していますが、主要設計は上記のファイル群に含まれます。

開発者向けメモ
--------------
- ExecutionEngine はセッションベース（target_date）で動作します。テスト時は run_session の代わりに個別メソッド（_process_signals / _drain_push_queue）を呼び出してユニットテストを容易にできます。
- BrokerAPI のインターフェースは Protocol で設計されているため、Mock と実クライアントを差し替えてテストできます。
- OrderManager の send_order はクラッシュ耐性を考慮した順序で DB 更新を行っています（OrderSent 保存 → ブローカー呼出し → broker_order_id 永続化 → OrderAccepted へ遷移 など）。Reconciler による復旧設計が組み込まれています。
- config/*.yaml のスキーマ検証は PyYAML のインストールが必要です。validate_config は PyYAML 不在時に YAML 検証をスキップします。

トラブルシューティング
----------------------
- validate_config で必須環境変数が未設定と出た場合は .env を確認し、python -m kabusys.config_setup で再設定してください。
- DuckDB / SQLite のパスに指定したディレクトリが存在しない場合、validate_config は警告を出します（起動時に自動作成される場合あり）。
- KABUSYS_ENV=live は本番向けの注意が多数あります。現在 Live broker の実装は限定的／未実装箇所があるので使用時は注意してください。

ライセンス・貢献
----------------
- 本 README にライセンスは明示していません。プロジェクト配布時に LICENSE ファイルを追加してください。
- バグ報告・機能改善は Pull Request / Issue を通して歓迎します。

付録：よく使うコマンドのまとめ
------------------------------
- .env ウィザード:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict
- 実行（paper_trading / development）:
  - python -m kabusys.run_execution
- 監視:
  - python -m kabusys.run_monitoring

以上。必要であれば README に含めるサンプル .env テンプレートや、requirements.txt の候補を作成します。どれを追加しますか？