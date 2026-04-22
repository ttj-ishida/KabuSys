KabuSys — 日本株自動売買システム (README)
========================================

プロジェクト概要
----------------
KabuSys は日本株向けの自動売買システムの基盤ライブラリです。  
主な目的は以下のとおりです。

- シグナルに基づく発注の実行（ExecutionEngine）
- ブローカークライアント抽象化（kabuステーション実装 / モック実装）
- 注文永続化・状態管理（SQLite）
- 起動時リコンシリエーション（再起動後の整合性回復）
- 監視プロセス（SystemMonitor のポーリング）
- 環境設定ウィザードおよび設定検証ユーティリティ
- マーケットカレンダー管理やニュース収集などのデータ処理ユーティリティ

安全性・運用性を重視した設計（kill switch、サーキットブレーカー、3段階リスクガード、発注の2相永続化など）を備えています。

機能一覧
--------
- 環境設定ウィザード（python -m kabusys.config_setup）で .env を対話的に生成・更新
- 起動前の設定検証ツール（python -m kabusys.validate_config、--strict オプション）
- ExecutionEngine：シグナルプル型の発注ループ（発注ウィンドウ管理、WebSocket push ドレイン）
- Broker クライアント層：
  - KabuStationClient（kabuステーション REST / WebSocket 実装）
  - MockBrokerClient（開発・テスト用のモック、PAPER_FILL_MODE による挙動）
  - BrokerClientFactory で環境（development / paper_trading / live）に応じた生成
- 注文管理：
  - OrderRecord（状態遷移ロジック）
  - OrderRepository（SQLite 永続化）
  - OrderManager（発注フロー、送信・同期・キャンセル処理）
- リスク管理（RiskManager）：Gate1/2/3（シグナルチェック、レート制限・CB、ドローダウン監視）
- Reconciler：再起動時に OrderSent 状態をブローカーと突合し同期、ポジション差分検出
- 監視プロセス（run_monitoring）：定期ポーリングでシステム状況を記録
- データユーティリティ：
  - calendar_management（営業日判定 / カレンダー更新ジョブ）
  - news_collector（RSS ニュース収集・前処理）
- 設定・パス管理（Settings クラス）：.env 自動ロード（OS 環境 > .env.local > .env）

セットアップ手順
----------------
前提
- Python 3.9+ を想定（typing / Path / dataclass 等を使用）
- SQLite は標準ライブラリで利用可
- DuckDB を使用（duckdb パッケージ）
- HTTP/WebSocket クライアント：httpx, websocket-client
- optional: PyYAML（config/*.yaml の内容検証用）、defusedxml（ニュース収集）

推奨インストール例（仮の requirements）
1. 仮想環境の作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージのインストール
   - pip install duckdb httpx websocket-client defusedxml
   - 任意: pip install pyyaml

3. プロジェクトルートで .env を作成（次節参照）

環境変数・設定
--------------
必須環境変数
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

推奨 / 任意
- KABUSYS_ENV: 実行環境（development / paper_trading / live）※ live は一部未実装（後述）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（デフォルト data/monitoring.db）
- LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL
- KABU_API_BASE_URL: kabu station base URL（デフォルト http://localhost:18080/kabusapi）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: 通知用（任意）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（0/1）

.env は OS 環境変数より下位で、.env.local が .env を上書きできます。自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。

使い方（主要コマンド）
--------------------

1) 環境設定ウィザード（.env を生成／更新）
- 実行:
  - python -m kabusys.config_setup
- 対話形式で必要項目（J-Quants token、kabu API password、DB パス等）を入力できます。
- 完了後 .env に保存されます（.env を Git にコミットしないでください）。

2) 設定検証
- 実行:
  - python -m kabusys.validate_config
  - 厳密モード（警告も失敗扱い）: python -m kabusys.validate_config --strict
- .env と config/*.yaml の存在・基本的な内容（PyYAML がインストールされていればパース）をチェックします。

3) 実行エンジン起動（発注）
- 実行:
  - python -m kabusys.run_execution
- 挙動:
  - KABUSYS_ENV が paper_trading または development の場合は MockBrokerClient を使用（本番発注は行わない）。
  - paper_trading の場合、デフォルトで PAPER_TRADING_SQLITE_PATH（data/paper_trading.db）に記録して本番 DB と分離します。
  - 起動時に kill.flag の存在を確認。KILL_FLAG_CLEAR_ON_START=1 の場合はクリアして起動できます（注意）。
  - PID ファイル（data/execution.pid 等）を作成します。停止は data/stop_requested.flag の作成で行えます。

4) 監視プロセス起動
- 実行:
  - python -m kabusys.run_monitoring
- MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を設定可能（デフォルト 60 秒）。
- 監視は常に本番 sqlite_path を使用（環境にかかわらず）。

主要な運用ファイル・フラグ
- data/kill.flag            — Kill Switch（存在すると発注停止等のトリガ）
- data/stop_requested.flag  — 外部からの停止リクエスト（監視・実行ループの終了トリガ）
- data/execution.pid        — ExecutionEngine の PID（起動時に書き出し）

PAPER / MOCK の挙動
- PAPER_FILL_MODE 環境変数（instant / partial / never / reject）で Mock の約定挙動を制御できます。
  - instant: 即座に全量約定
  - partial: 一部約定（テスト用に fill_order で全量約定可能）
  - never: 注文は約定せず Pending（order_id 発行のみ）
  - reject: 発注を拒否する

注意: live 環境（KABUSYS_ENV=live）は現状で Live broker client が未実装のため利用できません。将来の実装を予定しています。

ディレクトリ構成
----------------
以下は主要モジュールとその役割（抜粋）です。実コードは src/kabusys 以下に配置されています。

- src/kabusys/
  - __init__.py                — パッケージ定義
  - config.py                  — Settings クラス、.env 自動ロード、環境変数取得ユーティリティ
  - config_setup.py            — .env を対話形式で作成するウィザード CLI
  - validate_config.py         — 起動前設定検証 CLI
  - run_execution.py           — ExecutionEngine 起動スクリプト（発注エントリポイント）
  - run_monitoring.py          — SystemMonitor ポーリングループ起動スクリプト
  - execution/
    - broker_api.py            — BrokerAPI のデータモデル・Protocol・ファクトリ・例外定義
    - kabu_client.py           — kabu station REST / WebSocket 実装
    - mock_client.py           — テスト用 MockBrokerClient
    - broker_factory.py        — Settings に基づく Broker クライアント生成
    - order_record.py          — OrderRecord（状態遷移ロジック）
    - order_repository.py      — SQLite を用いた永続化層（orders テーブルの初期化含む）
    - order_manager.py         — 発注フローの高レベル API（create/send/sync/cancel）
    - execution_engine.py      — 発注エンジン本体（シグナル処理／push ドレイン／kill switch）
    - reconciler.py            — 起動時リコンシリエーション（OrderSent 突合・ポジション差分検出）
    - risk_manager.py          — 3段階リスクガード（Gate1/2/3）
  - data/
    - calendar_management.py   — マーケットカレンダー管理（営業日判定／更新ジョブ）
    - news_collector.py        — RSS ニュース収集・前処理
    - (jquants_client 等の補助モジュールが想定される)
  - monitoring/
    - monitoring_db.py         — 監視用 DB 初期化 / 書き込み（参照のみ）
    - system_monitor.py        — システム監視ロジック（参照）
  - utils/
    - logging_setup.py         — ログ設定ユーティリティ（参照）
    - process_priority.py      — プロセス優先度設定ユーティリティ（参照）
  - config/                    — 設定ファイル yaml（system_config.yaml などを想定）
  - scripts/
    - generate_config.py       — config/*.yaml を生成する補助スクリプト（参照）

備考 / 運用上の注意
-------------------
- .env を絶対にバージョン管理 (Git) にコミットしないこと。config_setup は生成時にその旨を注意書きします。
- validate_config は PyYAML がインストールされていれば config/*.yaml をパースして検証します。未インストール時は YAML 内容検証をスキップします。
- ExecutionEngine の kill-switch / PID / stop flag の挙動は運用上重要です。運用前に README の該当箇所と validate_config の警告を確認してください。
- 設定ミスや未設定環境変数は validate_config で検出できます。--strict を CI に組み込むと警告も失敗にできます。
- live 環境は現状で Live broker client が未実装です。実運用をする場合は実装状況とテストを確認してください。

問題報告 / 貢献
----------------
- バグや改善提案は Issue を利用してください。プルリクエスト歓迎です。

以上が本リポジトリの概要と基本的な使い方です。セットアップや実行で不明点があれば、具体的なエラーや状況を教えてください。