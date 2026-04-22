KabuSys — 日本株自動売買システム
================================

概要
----
KabuSys は日本株の自動売買を想定した小規模な取引エンジンです。  
主に以下を提供します。

- シグナルを取り込み、発注を行う ExecutionEngine
- 起動時のリコンシリエーション（Reconciler）による復旧処理
- 注文の状態管理（OrderRecord / OrderRepository / OrderManager）
- ブローカークライアントの抽象化（実装: MockBrokerClient、将来的に KabuStationClient）
- 監視用ループ（SystemMonitor / run_monitoring）
- 環境設定ウィザード（.env 作成支援）と設定検証ツール

主な設計方針は「DB による永続化」「クラッシュ耐性」「3 段階のリスクガード（Gate1/2/3）」です。

機能一覧
--------
- 環境設定ウィザード（python -m kabusys.config_setup）
  - 対話式に .env を生成／更新
- 設定検証 CLI（python -m kabusys.validate_config）
  - 必須環境変数や config/*.yaml、パス等の事前チェック
- ExecutionEngine（python -m kabusys.run_execution）
  - シグナル取得 → 発注 → push ドレイン（WebSocket） のセッション実行
  - paper_trading 環境では MockBrokerClient を使用し、本番 DB と分離
- Monitoring ループ（python -m kabusys.run_monitoring）
  - 定期的にシステム監視情報を収集・記録
- 注文永続化（SQLite）と分析用 DuckDB の使用
- リスク管理（余力・ポジション上限、レート制限・サーキットブレーカー、ドローダウン監視）
- 起動時のリコンシリエーション（OrderSent 状態の突合）

動作要件 / 推奨ライブラリ
-------------------------
（プロジェクトに requirements.txt がある場合はそちらを優先してください。以下はソースから読み取れる主な依存）

- Python 3.9+
- duckdb
- httpx
- websocket-client
- PyYAML（設定検証で YAML パースを行う場合）
- defusedxml（news RSS パース）
- その他: (標準ライブラリ: sqlite3, logging, threading, pathlib, etc.)

セットアップ手順
----------------
1. リポジトリをクローン、作業ディレクトリへ移動。

2. 仮想環境の作成（任意だが推奨）:
   - Unix/macOS:
     - python -m venv .venv
     - source .venv/bin/activate
   - Windows:
     - python -m venv .venv
     - .venv\Scripts\activate

3. 依存パッケージをインストール（最低限）:
   - pip install duckdb httpx websocket-client pyyaml defusedxml

   ※ 実際の requirements.txt がある場合:
   - pip install -r requirements.txt

4. .env の準備（対話式ウィザード推奨）:
   - python -m kabusys.config_setup
     - 対話形式で .env を生成／更新します。
   - 生成後、設定を検証:
     - python -m kabusys.validate_config
     - 警告も失敗扱いにしたい場合は --strict を付与

環境変数（主なもの）
--------------------
必須
- JQUANTS_REFRESH_TOKEN — J-Quants API 用リフレッシュトークン（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）

任意（しかし運用上推奨）
- KABUSYS_ENV — 実行環境（development / paper_trading / live）。デフォルト: development
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite DB（デフォルト: data/monitoring.db）
- LOG_LEVEL — ログレベル（DEBUG, INFO, WARNING, ...）
- KABU_API_BASE_URL — kabu station API のベース URL
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID — LINE 通知用（本番時は設定推奨）
- PAPER_FILL_MODE — paper_trading 時のモック約定モード（instant / partial / never / reject）
- PAPER_TRADING_SQLITE_PATH — paper_trading 用 SQLite（デフォルト: data/paper_trading.db）
- PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START など監視・停止制御に関する設定

.env 自動読み込み
- 設定モジュールはプロジェクトルート（.git または pyproject.toml を基準）から .env を自動読み込みします。
- 読み込み優先順位: OS 環境 > .env.local > .env
- 自動読み込みを無効化するには: KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定

使い方
------
基本的なワークフロー

1. .env を作成
   - python -m kabusys.config_setup

2. 設定検証
   - python -m kabusys.validate_config
   - --strict を付けると警告も exit(1) 扱いになります

3. 監視ループ起動（単独で常駐実行）
   - python -m kabusys.run_monitoring
   - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を変更できます（デフォルト 60 秒）

4. 発注エンジン起動
   - python -m kabusys.run_execution
   - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、paper_trading 用 DB（data/paper_trading.db）で動作します
   - 停止はプロジェクトルートの data/stop_requested.flag の作成で検知します（停止フラグ）

注意点 / 運用メモ
- kill.flag（KILL_FLAG_PATH）検出時は起動拒否または kill_switch が発動します。起動時に自動クリアしたい場合は KILL_FLAG_CLEAR_ON_START=1 を設定します（本番では推奨されません）。
- ExecutionEngine は PID ファイル（デフォルト data/execution.pid）を生成します。
- run_execution は起動時にリコンシリエーションを行い、OrderSent の突合やポジション差分を検査します。
- 本番運用（KABUSYS_ENV=live）では外部通知（LINE 等）や十分な監視設定を行ってください（コード中に live 向けの追加警告チェックあり）。

開発 / テスト
- mock クライアント: MockBrokerClient を利用することで kabu station 実環境なしに発注・約定挙動を再現できます。
- unit テストを追加する際は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を使って自動 .env ロードを抑制してください。

ディレクトリ構成（主なファイル）
-----------------------------
以下はコードベースの主なモジュール・ディレクトリ構成です（src/kabusys 以下）。

- src/kabusys/
  - __init__.py
  - config.py                   — 環境設定読み込み / Settings
  - config_setup.py             — .env 対話式ウィザード
  - validate_config.py          — 設定検証ツール（.env / config/*.yaml）
  - run_execution.py            — ExecutionEngine の起動スクリプト
  - run_monitoring.py           — Monitoring ループ起動スクリプト

  - execution/                   — 発注／注文管理関連
    - __init__.py
    - broker_api.py             — Broker API プロトコル・データモデル・ファクトリ
    - broker_factory.py         — Settings に基づくクライアント生成
    - kabu_client.py            — KabuStationClient（REST / WebSocket 実装）
    - mock_client.py            — MockBrokerClient（テスト用）
    - order_record.py           — OrderRecord（状態遷移ロジック）
    - order_repository.py       — SQLite 永続化層
    - order_manager.py          — OrderManager（外向き API）
    - execution_engine.py       — ExecutionEngine（シグナル処理 / push ドレイン）
    - reconciler.py             — 起動時リコンシリエーション
    - risk_manager.py           — Gate1/2/3 リスクガード

  - monitoring/                  — 監視関連（SystemMonitor 等）
    - monitoring_db.py
    - system_monitor.py

  - data/                        — データ取得 / カレンダー / ニュース等
    - calendar_management.py    — JPX カレンダー管理（next_trading_day 等）
    - news_collector.py         — RSS 取得 / 前処理 / raw_news 保存
    - jquants_client.py         — （外部 API のクライアント想定）

  - utils/                       — ロギング設定やプロセス優先度などユーティリティ
    - logging_setup.py
    - process_priority.py

- config/                       — 設定用 YAML テンプレート（system_config.yaml 等）
  - system_config.yaml
  - data_config.yaml
  - strategy_config.yaml
  - risk_config.yaml
  - execution_config.yaml
  - monitoring_config.yaml

- data/                         — 実行時に生成される DB やフラグ類（例: data/kabusys.duckdb, data/monitoring.db, stop_requested.flag）

補足
----
- 設定検証(validate_config) は PyYAML がインストールされている場合に config/*.yaml を YAML パースして検証します。PyYAML がないと内容検証はスキップされます（存在チェックのみ）。
- 実際の本番ブローカークライアント（kabu station）を利用する場合は KabuStationClient の使用とセキュリティ（API パスワード管理等）に十分注意してください。現在の実装では live クライアントは未実装の箇所があります（BrokerClientFactory の live 判定は NotImplementedError を投げます）。

ライセンス / 貢献
----------------
本 README はコードベースの簡易ドキュメントです。実運用に使う際は十分なテスト、コードレビュー、運用手順（systemd / コンテナ化 / ロギング / モニタリング）を整備してください。貢献・改善提案は Pull Request を歓迎します。

--- 

必要であれば README に具体的なコマンド例（systemd ユニットや Dockerfile、詳細な依存一覧、DB 初期化スクリプトなど）を追加します。どの情報を深掘りしましょうか？