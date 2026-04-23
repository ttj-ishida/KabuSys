KabuSys — 日本株自動売買システム
================================

概要
----
KabuSys は日本株の自動売買を目的とした内部ミドル層ライブラリ／実行フレームワークです。本プロジェクトは以下を目的とします。

- シグナルを受けて発注を行う ExecutionEngine
- 発注状態の永続化（SQLite）
- 発注・約定のリコンシリエーション（復旧）
- 3段階のリスクガード（Gate1/2/3）
- モニタリング（監視ループ）
- 開発用に kabuステーションを模した Mock broker を提供

主な特徴
--------
- ExecutionEngine：シグナルの取り込み → 発注 → WebSocket Push ドレインの実装
- OrderManager / OrderRecord：注文状態遷移の厳密な管理（状態機械）
- OrderRepository：SQLite による永続化（orders テーブル・インデックスを冪等作成）
- Broker クライアント：
  - KabuStationClient：kabuステーション REST API（httpx）実装
  - MockBrokerClient：テスト／開発用のモック（fill_mode 切替可能）
- RiskManager：Gate1（シグナル） / Gate2（実行） / Gate3（メトリクス）を提供
- Reconciler：再起動時に OrderSent の注文をブローカーと突合して同期
- 環境設定ウィザード（config_setup）と設定検証ツール（validate_config）
- データ処理：マーケットカレンダー管理、ニュース収集など（data パッケージ）

セットアップ
------------
推奨：仮想環境（venv / venvwrapper / poetry 等）を使用してください。

例（venv + pip）:
1. 仮想環境作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   - pip install duckdb httpx websocket-client defusedxml
   - PyYAML は設定検証（config/*.yaml のパース）で任意に使用：pip install PyYAML

（プロジェクトに requirements.txt / pyproject.toml がある場合はそれに従ってください）

環境変数（主なもの）
-------------------
必須:
- JQUANTS_REFRESH_TOKEN — J-Quants API のリフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API パスワード

任意・設定推奨:
- KABUSYS_ENV — 実行環境（development, paper_trading, live）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視 DB の SQLite パス（デフォルト: data/monitoring.db）
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- KABU_API_BASE_URL — kabu station のベース URL
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — 本番通知用（任意）
- PAPER_FILL_MODE — paper_trading 用のモック約定モード（instant/partial/never/reject）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動でクリアするか（0/1）

.env の自動読み込み
- 起動時にプロジェクトルート（.git または pyproject.toml を基準）を探して .env を自動読み込みします。
- 読み込み順序: OS 環境 > .env > .env.local (.env.local は上書き)
- 自動ロードを無効にする場合: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

使い方（主要 CLI / スクリプト）
--------------------------------

1) 初期 .env 作成（対話式ウィザード）
- python -m kabusys.config_setup
  - 対話式で .env を作成・更新します（デフォルトはプロジェクトルートの .env）。
  - シークレット値は入力時にマスク表示されます。

2) 設定検証
- python -m kabusys.validate_config
  - .env と config/*.yaml の存在・簡易チェックを行います。
  - --strict を付けると警告も FAIL として exit(1) を返します。
  - PyYAML がインストールされていれば YAML のパース検証も行います。

3) 実行エンジン（本番・テストの起動）
- python -m kabusys.run_execution
  - ExecutionEngine を起動します。
  - KABUSYS_ENV が paper_trading の場合、MockBrokerClient を使用して data/paper_trading.db に記録します。
  - 起動時に PID ファイルを書き込み（デフォルト: data/execution.pid）。停止は data/stop_requested.flag を作成するか kill.flag を使用。

4) モニタリングループ起動
- python -m kabusys.run_monitoring
  - SystemMonitor のポーリングループを開始します（デフォルト 60 秒間隔）。
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能。
  - モニタリングは KABUSYS_ENV にかかわらず本番用 sqlite_path を使用。

停止・Kill スイッチ
- stop: プロジェクトルート/data/stop_requested.flag を作成すると、実行中の run_execution/run_monitoring が検知して安全に停止します。
- kill flag: 設定で指定された KILL_FLAG_PATH（デフォルト data/kill.flag）が存在すると起動拒否または kill_switch 発動の対象になります。
- KILL_FLAG_CLEAR_ON_START=1 を設定すると、起動時に kill.flag を自動クリアします（本番での自動クリアは推奨されません）。

主要コンポーネント（簡単な説明）
--------------------------------
- ExecutionEngine
  - シグナル取り込み（DuckDB）→ Gate1/2 のリスク検査 → 発注 → push ドレインループ
  - run_session() がセッションのライフサイクルを管理（時刻ベースの処理区分あり）
- OrderRecord / OrderState
  - 注文状態のデータモデルと状態遷移の検証
- OrderRepository
  - SQLite を用いた orders テーブルの永続化（init_orders_db でスキーマ作成）
- OrderManager
  - OrderRecord と OrderRepository、Broker API を組み合わせて発注フローを管理
  - send_order() の2相永続化などクラッシュ安全性を意識した設計
- Broker クライアント
  - KabuStationClient：kabuステーション REST API 実装（httpx）
  - MockBrokerClient：テスト用。PAPER_FILL_MODE により挙動変更（instant/partial/never/reject）
  - create_broker_api() で適切な実装を取得
- RiskManager
  - Gate1（シグナル検査：余力・重複・ポジション上限）
  - Gate2（レート制限、サーキットブレーカー）
  - Gate3（ドローダウン監視）
- Reconciler
  - 起動時に OrderSent の注文をブローカーと照合して状態を回復
- data パッケージ
  - calendar_management（営業日計算、J-Quants 連携）
  - news_collector（RSS 収集、前処理、SSRF 対策等）
- monitoring
  - 監視用 DB と SystemMonitor（run_monitoring が使用）

ディレクトリ構成（主要ファイル）
-------------------------------
src/kabusys/
- __init__.py
- config.py                — 環境変数読み込み・Settings
- config_setup.py          — .env 作成ウィザード
- validate_config.py       — 設定検証 CLI
- run_execution.py         — ExecutionEngine 起動スクリプト
- run_monitoring.py        — Monitoring 起動スクリプト

src/kabusys/execution/
- __init__.py
- broker_api.py            — Broker API の型定義・ファクトリ
- mock_client.py           — MockBrokerClient（テスト用）
- kabu_client.py           — KabuStationClient（httpx ベース）
- broker_factory.py        — Settings に基づくクライアント生成
- execution_engine.py      — ExecutionEngine の実装
- order_record.py          — 注文状態モデルと遷移ロジック
- order_repository.py      — SQLite 永続化層（orders テーブル）
- order_manager.py         — 発注フロー（OrderManager）
- reconciler.py            — リコンシリエーション
- risk_manager.py          — リスク管理

src/kabusys/data/
- calendar_management.py   — マーケットカレンダー管理（JPX/J-Quants ベース）
- news_collector.py        — RSS ニュース収集

src/kabusys/monitoring/
- (監視関連のモジュール: monitoring_db, system_monitor など)

その他:
- config/*.yaml            — 設定ファイル（存在が期待される。validate_config が検出）
- .env, .env.local         — 環境変数定義ファイル（.env を絶対に Git にコミットしないこと）

設定ファイル（config/*.yaml）
----------------------------
- validate_config は以下ファイルの存在をチェックします（パース可能ならパースも行う）:
  - system_config.yaml
  - data_config.yaml
  - strategy_config.yaml
  - risk_config.yaml
  - execution_config.yaml
  - monitoring_config.yaml

- これらが存在しない場合、validate_config は警告を出します（生成スクリプトがある場合はそれを利用してください）。PyYAML 未インストール時はパース検証をスキップします。

動作上の注意
------------
- 本番環境（KABUSYS_ENV=live）は慎重に扱ってください。validate_config は live の場合に複数の注意（LINE 通知設定未設定、KILL_FLAG_CLEAR_ON_START の危険設定等）を出します。
- PID ファイル・kill.flag 等は実行環境の運用ルールに従って管理してください。
- .env を絶対にリポジトリにコミットしないでください（README ヘッダ注記や config_setup の出力も同じ警告を出します）。

トラブルシューティング
--------------------
- YAML パース検証がスキップされる／PyYAML を要求された場合: pip install PyYAML
- DuckDB 接続エラー: DUCKDB_PATH の親ディレクトリが存在するか確認してください（validate_config で親ディレクトリの存在を警告します）。
- API 通信系のエラーはログ（LOG_LEVEL を DEBUG にすると詳細）を確認してください。

ライセンス・貢献
----------------
- このリポジトリに LICENSE が含まれている場合はそれに従ってください。コントリビューションは通常の Fork & Pull Request フローを推奨します。

以上が本プロジェクトの主要な README 内容です。必要があればインストール用の requirements.txt や起動スクリプトの systemd ユニット例、より詳細な運用手順（本番移行チェックリスト等）を追記します。どの情報を優先して追加しますか？