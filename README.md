KabuSys — 日本株自動売買システム（README）
======================================

概要
----
KabuSys は日本株向けの自動売買システムのコアライブラリです。  
本リポジトリは以下の主要機能を提供します。

- シグナルに基づく発注エンジン（ExecutionEngine）
- ブローカー API 抽象化（kabu station 実装 / モック実装）
- 安全設計のリスクガード（3段階: Gate1/2/3）
- 注文状態管理（永続化・リコンシリエーション）
- 監視プロセス（SystemMonitor のポーリングループ）
- データ処理ユーティリティ（マーケットカレンダー・ニュース収集等）
- 環境設定ウィザード (.env 作成) と設定検証 CLI

機能一覧
--------
主要機能の概要：

- 環境設定
  - 対話式ウィザードで .env を生成・更新（kabusys.config_setup）
  - validate_config で .env と config/*.yaml の簡易検証
- Execution（発注）
  - ExecutionEngine: DuckDB のシグナルから発注を行うセッション実行
  - OrderManager / OrderRecord: 注文状態遷移のビジネスロジック
  - OrderRepository: SQLite による永続化
  - Broker クライアントファクトリ: Mock / 本番クライアントの切替
  - Reconciler: 再起動時の自動復旧（OrderSent の突合・ポジション差分検出）
  - RiskManager: Gate1（余力/重複/ポジション上限） / Gate2（レート制限・CB） / Gate3（ドローダウン）
- Monitoring（監視）
  - run_monitoring: SystemMonitor のポーリングループ（SQLite / DuckDB を使用）
- ブローカークライアント
  - KabuStationClient: kabu-station REST / WebSocket 実装（httpx, websocket-client）
  - MockBrokerClient: テスト／ペーパートレード用のモック（fill_mode 等を設定可能）
- データ関連ユーティリティ
  - calendar_management: JPX カレンダーの取得・営業日判定
  - news_collector: RSS から記事収集（SSRF 対策・正規化）

セットアップ手順
----------------

前提
- Python 3.10+（タイプアノテーション等を利用）
- Git clone したレポジトリのルートに移動

推奨パッケージ（例）
- duckdb
- httpx
- websocket-client
- defusedxml
- PyYAML（config YAML の解析を行う場合）
- その他: sqlite3 は標準ライブラリで提供

インストール例（仮の requirements がない場合の例）
- 仮想環境作成・有効化（任意）
  - python -m venv .venv
  - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
- 必要パッケージを pip でインストール
  - pip install duckdb httpx websocket-client defusedxml pyyaml

.env の作成
- 対話式ウィザードで .env を生成・更新:
  - python -m kabusys.config_setup
  - 途中で入力をキャンセルした場合は変更は保存されません
- 手動で .env を作る場合はリポジトリの .env.example を参考にする（存在する場合）

設定検証
- .env と config/*.yaml を起動前に検証:
  - python -m kabusys.validate_config
  - 警告もエラー扱いにする: python -m kabusys.validate_config --strict

実行（ローカル開発 / ペーパートレード）
- Execution（発注エンジン）を起動:
  - python -m kabusys.run_execution
  - KABUSYS_ENV が paper_trading / development の場合、MockBrokerClient が使われ、本番 DB と分離して paper_trading 用 SQLite（PAPER_TRADING_SQLITE_PATH）に記録されます
- Monitoring（監視）を起動:
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL（秒）でポーリング間隔を変更可能（デフォルト 60 秒）

使い方（主要コマンド）
--------------------

- 環境ウィザード
  - python -m kabusys.config_setup
  - フロー: 既存 .env 読込 → 各項目入力 → 保存確認 → .env 書き込み
- 設定検証
  - python -m kabusys.validate_config [--strict]
  - 必須環境変数未設定や YAML のパース失敗を検出
  - 必須環境変数: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD
  - 許容される KABUSYS_ENV: development, paper_trading, live
- ExecutionEngine（本番相当のセッション実行）
  - python -m kabusys.run_execution
  - 動作のポイント:
    - 起動時にプロセス優先度を上げる処理が入る（utils/process_priority）
    - DB: paper_trading 環境では paper_sqlite_path（デフォルト data/paper_trading.db）、それ以外は sqlite_path（監視 DB）を利用
    - DuckDB はシグナル取得や分析用に使用（DUCKDB_PATH）
    - kill.flag（KILL_FLAG_PATH）検査と kill_switch による安全停止
    - 発注は 8:50–9:10 のシグナル処理と 9:10–15:30 の push ドレインループで運用設計
- Monitoring
  - python -m kabusys.run_monitoring
  - 監視 DB (sqlite) と DuckDB に接続して SystemMonitor を定期実行

重要な環境変数
----------------
（validate_config と Settings クラスで参照される主要項目）

必須（実行に必要）
- JQUANTS_REFRESH_TOKEN — J-Quants API 用リフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API パスワード

任意（デフォルトあり / オプション）
- KABUSYS_ENV — 実行環境: development / paper_trading / live（デフォルト: development）
- DUCKDB_PATH — DuckDB のファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- KABU_API_BASE_URL — kabu station の base URL（デフォルト http://localhost:18080/kabusapi）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID — 本番アラート用（任意）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアする（0/1、デフォルト 0）
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング秒数（デフォルト 60）

注意事項
---------
- 本番（KABUSYS_ENV=live）では設定ミスが致命的となる可能性があります。validate_config で確認し、LINE の通知設定なども忘れずに行ってください。
- KabuStationClient（本番接続）は kabuステーションアプリがローカルで起動していることを前提としています。本番ブローカー実装は将来的に拡張される設計です。
- .env は絶対にリポジトリにコミットしないでください（config_setup のヘッダにも注意書きあり）。
- 自動 .env 読み込みを無効化する場合: KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると config モジュールの自動ロードをスキップします（テスト等で使用）。

ディレクトリ構成
-----------------
（リポジトリの src/kabusys 以下を抜粋）

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数 / .env 読み込みロジック、Settings
  - config_setup.py           — .env 対話式ウィザード
  - validate_config.py        — 設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト（セッション実行）
  - run_monitoring.py         — SystemMonitor ポーリングループ起動スクリプト
  - execution/
    - __init__.py
    - broker_api.py           — Broker API のデータモデル・Protocol・ファクトリ
    - broker_factory.py       — Settings に基づくクライアント生成
    - kabu_client.py          — kabu station 実装（REST / WebSocket）
    - mock_client.py          — モックブローカー（テスト/ペーパー用）
    - order_record.py         — OrderRecord（状態遷移ロジック）
    - order_repository.py     — SQLite 永続化層
    - order_manager.py        — 発注フロー（作成・送信・同期・取消）
    - execution_engine.py     — ExecutionEngine（シグナル処理・push ドレイン）
    - reconciler.py           — 起動時リコンシリエーション・ポジション照合
    - risk_manager.py         — 3段階リスクガード
  - monitoring/
    - monitoring_db.py        — 監視 DB 初期化・ログ用の API（参照あり）
    - system_monitor.py       — SystemMonitor 実装（参照あり）
  - data/
    - calendar_management.py  — 市場カレンダー管理
    - news_collector.py       — RSS ニュース収集
    - jquants_client.py       — J-Quants API クライアント（参照あり）
  - utils/
    - logging_setup.py        — ロギング設定ユーティリティ（参照あり）
    - process_priority.py     — プロセス優先度設定ユーティリティ（参照あり）

（注）上記は主なファイル群の抜粋です。各モジュールはさらに細かい責務に分離されています。

開発者向けメモ
---------------
- 自動 .env 読込は config._find_project_root() で .git または pyproject.toml を基準に行うため、パッケージ配布後も安定して動作します。テストや CI では KABUSYS_DISABLE_AUTO_ENV_LOAD を使うと便利です。
- ExecutionEngine.run_session() は実運用時間帯（8:50–15:30）に合わせた処理フローを備えていますが、テストでは _process_signals() と _drain_push_queue() を直接呼ぶことで時間依存を回避できます。
- Order のクラッシュ安全性は設計済み（OrderSent の二相永続化、broker_order_id 保持、Reconciler による復旧）。

トラブルシューティング
---------------------
- 設定検証で PyYAML 未インストール警告が出る場合、config/*.yaml の内容検証はスキップされます。YAML 検証を有効にするには PyYAML をインストールしてください。
- KABUSYS_ENV=live での実行は設定ミスが重大な損失につながるため、まず paper_trading / development で十分に検証してください。
- WebSocket 接続は kabu station のトークン認証を行い、接続断時にリトライします。ローカルの kabu station アプリと通信できることを確認してください。

最後に
------
この README はソースの主要モジュールに基づく概要と運用手順をまとめたものです。詳細な挙動や追加のユーティリティは各モジュールのドキュメント（ソース内 docstring）を参照してください。質問やドキュメント追加の要望があれば教えてください。