KabuSys — 日本株自動売買システム
================================

概要
----
KabuSys は日本株向けの自動売買フレームワーク（PoC / 開発用実装）です。  
主に以下の役割を持ちます：

- シグナルを取り込み、発注フロー（Order 管理 / 永続化 / リスクガード）を実行
- ブローカー API の抽象化（実環境用クライアントとテスト用のモックを切替）
- 起動時の設定ウィザード（.env）と事前検証ツール
- 監視ループ（システムメトリクスや監視DBのロギング）
- 市場カレンダー管理、ニュース収集などのデータ処理ユーティリティ

バージョン: 0.1.0

主な機能
--------
- .env 対話式ウィザード（kabusys.config_setup）による環境変数作成/更新
- 設定検証 CLI（kabusys.validate_config）: .env と config/*.yaml の整合性チェック
- ExecutionEngine（run_execution）: シグナル読み取り → 発注 → 状態管理（永続化は SQLite）
- Monitoring Loop（run_monitoring）: システム監視データの定期記録
- ブローカー抽象化: 実ブローカー（KabuStationClient）と Mock（MockBrokerClient）の切替
- 安全機構: 3段階リスクガード（Gate1/2/3）、サーキットブレーカー、kill switch、リコンシリエーション
- データユーティリティ: マーケットカレンダー管理、ニュース収集、DuckDB を用いた分析データ処理

前提・依存関係
--------------
推奨環境:
- Python 3.10 以上

主な Python パッケージ（プロジェクト配布で requirements.txt がある場合はそれを使用してください）:
- duckdb
- httpx
- websocket-client
- PyYAML（YAML 検証のため、なければ警告を出してスキップします）
- defusedxml

標準ライブラリ: sqlite3, threading, logging, pathlib など

セットアップ手順
----------------
1. リポジトリをクローン
   - git clone <リポジトリ URL>

2. 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - pip install -r requirements.txt
   （requirements.txt がない場合）
   - pip install duckdb httpx websocket-client PyYAML defusedxml

4. .env の初期設定
   - python -m kabusys.config_setup
     - 対話形式で必要な環境変数を入力します。
     - 生成された .env は Git にコミットしないでください（README 内に注意書きも出力されます）。

5. 設定を検証
   - python -m kabusys.validate_config
   - 厳格モード（警告も失敗扱い）:
     - python -m kabusys.validate_config --strict

基本的な使い方
--------------
.env 作成・更新
- python -m kabusys.config_setup
  - 対話形式で KABUSYS_ENV、JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD などを設定します。

設定の事前検証
- python -m kabusys.validate_config
  - .env と config/*.yaml の存在と基本整合性をチェックします。
  - --strict を使うと警告も exit code 1 として扱います。

ExecutionEngine を起動
- 本番/検証相当のセッションを実行（PID / kill flag を data/ に出力します）
- python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading または development の場合は MockBrokerClient を使用。
  - KABUSYS_ENV=live は現在未実装（BrokerFactory で NotImplementedError を送出）。

Monitoring を起動
- python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL（秒）でポーリング間隔を上書き（デフォルト 60 秒）。

主な環境変数（抜粋）
- 必須:
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- 推奨/任意:
  - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
  - DUCKDB_PATH — データ解析用 DuckDB の保存先（デフォルト data/kabusys.duckdb）
  - SQLITE_PATH — 監視 DB（デフォルト data/monitoring.db）
  - LOG_LEVEL — DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト INFO）
  - KABU_API_BASE_URL — kabu station API の base URL
  - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID — 本番通知用
  - KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（0/1、デフォルト 0）

安全・運用に関する注意
- KABUSYS_ENV=live を設定する場合は全設定を慎重に確認してください（validate_config は live の場合に追加警告を出します）。
- kill.flag を用いた安全停止機構があり、KILL_FLAG_CLEAR_ON_START=1 は本番で危険です（デフォルト 0）。
- ExecutionEngine は起動時に PID ファイルを書き、kill.flag 存在時の振る舞いが設定で制御されます。
- MockBrokerClient（paper_trading/development）を使えば実ブローカーなしで動作確認できます。

ディレクトリ構成（主要部分）
---------------------------
プロジェクトルート（抜粋）:
- src/kabusys/
  - __init__.py
  - config.py                  — 環境変数 / Settings 管理（自動 .env ロード含む）
  - config_setup.py            — .env 対話式ウィザード CLI
  - validate_config.py         — 起動前設定検証 CLI
  - run_execution.py           — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — Monitoring 起動スクリプト
  - execution/
    - __init__.py
    - broker_api.py            — Broker API Protocol / データモデル / ファクトリ
    - broker_factory.py        — Settings に基づくクライアント生成
    - kabu_client.py           — 実ブローカー (KabuStation) クライアント実装
    - mock_client.py           — モック実装（テスト用）
    - order_record.py          — 注文状態マシン（純粋ロジック）
    - order_repository.py      — SQLite 永続化層（orders テーブル定義等）
    - order_manager.py         — 外向き注文 API（作成・送信・同期・キャンセル）
    - reconciler.py            — 起動時リコンシリエーション / 自動復旧
    - execution_engine.py      — 発注エンジン（シグナル処理・push ドレイン）
    - risk_manager.py          — 3段階リスクガード（Gate1/2/3）
  - data/
    - calendar_management.py   — JPX カレンダー管理（DuckDB）
    - news_collector.py        — RSS ニュース収集 / 前処理
  - monitoring/
    - monitoring_db.py         — 監視 DB 初期化 / ログ書き込み（参照）
  - utils/
    - logging_setup.py         — ロギング初期化（参照）
    - process_priority.py      — プロセス優先度設定（参照）
- config/
  - system_config.yaml        — 想定される設定ファイル（存在しない場合は警告）
  - data_config.yaml
  - strategy_config.yaml
  - risk_config.yaml
  - execution_config.yaml
  - monitoring_config.yaml

データ / ランタイム用ファイル（デフォルト）
- data/kabusys.duckdb
- data/monitoring.db
- data/execution.pid
- data/kill.flag
- data/stop_requested.flag

開発時のヒント
--------------
- テストや開発では KABUSYS_ENV=paper_trading を利用すると MockBrokerClient による安全な動作確認が可能です。
- 設定検証ツール（validate_config）は PyYAML 未インストール時に YAML パース検証をスキップします。YAML の検証を行いたい場合は PyYAML をインストールしてください。
- ExecutionEngine の主要ルーチン:
  - _process_signals(): シグナル読み取り→Gate1/2→発注
  - _drain_push_queue(): push 通知処理（sync_order 等）
  - kill_switch(): 全 active 注文のキャンセルとループ停止
- 起動・運用時は監視 DB や PID / kill flag の扱いに注意してください。

ライセンス・貢献
----------------
（ここにライセンス情報や貢献の手順を追加してください。）

お問い合わせ
------------
不明点や改善提案はリポジトリの issue にて報告してください。