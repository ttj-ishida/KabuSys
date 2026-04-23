# KabuSys

日本株向け自動売買システム（モジュール群）  
この README は与えられたコードベースの概要・セットアップ・使い方をまとめたものです。

> ※ 本ドキュメントはリポジトリの現時点のソースコード（src/kabusys 以下）に基づいています。実運用前に必ず内容を確認してください。

---

## プロジェクト概要

KabuSys は、kabu ステーション（またはモック実装）を用いた日本株自動売買向けのコンポーネント群です。  
主な機能としては：

- シグナルに基づく発注エンジン（ExecutionEngine）
- 注文状態管理（OrderRecord / OrderManager / OrderRepository）
- ブローカー API 抽象化（KabuStationClient / MockBrokerClient）
- リスク管理（3段階ガード: Gate1/2/3）
- 起動時のリコンシリエーション（Reconciler）
- 監視プロセス（SystemMonitor を使ったポーリングループ）
- 環境設定ウィザードと設定検証 CLI
- データ処理（マーケットカレンダー、ニュース収集等）

設計は、DB（SQLite, DuckDB）とブローカー API を切り離したモジュール化・クラッシュ耐性を重視しています。

---

## 主な機能一覧

- 環境設定ウィザード（.env の生成 / 更新）
  - python -m kabusys.config_setup
- 設定内容の事前検証（.env / config/*.yaml のチェック）
  - python -m kabusys.validate_config [--strict]
- 発注エンジン
  - ExecutionEngine: シグナルの読み込み → Gate1/2 を経て発注、push ドレイン
  - 発注の永続化は SQLite（orders テーブル）
- ブローカー層
  - KabuStationClient: kabu ステーション REST API 実装（httpx）
  - MockBrokerClient: テスト/開発用のモック。PAPER_FILL_MODE により振る舞いを変更可能
- リスク管理
  - RiskManager: 3 層のガード（シグナル・エグゼキューション・メトリクス監視）
  - サーキットブレーカー、レート制限、ポジション/利用率チェック、ドローダウン監視
- リコンシリエーション
  - 再起動時に OrderSent 状態をブローカーと突合して自動復旧
- データ関連
  - カレンダー管理（DuckDB を使用）
  - ニュース収集（RSS パーシング、前処理、安全性対策あり）
- 監視プロセス
  - run_monitoring: SystemMonitor のポーリングループ、監視 DB に記録

---

## セットアップ手順（ローカル開発向け）

1. Python と仮想環境の準備
   - 推奨: Python 3.9+
   - 仮想環境作成例:
     - python -m venv .venv
     - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージのインストール  
   （requirements.txt が無い場合は以下を目安にインストールしてください）
   - pip install duckdb httpx websocket-client defusedxml PyYAML
   - もし monitoring やその他で追加依存があれば適宜追加してください。

   例:
   - pip install duckdb httpx websocket-client defusedxml PyYAML

3. .env の作成
   - 対話式ウィザードで作成:
     - python -m kabusys.config_setup
   - 生成された .env を絶対に Git にコミットしないでください（README 内にも警告あり）。

4. 設定の事前検証
   - python -m kabusys.validate_config
   - --strict を付けると警告も FAIL 扱いで exit(1) になります。

5. データベース（初期化）
   - 実行スクリプトが起動時に必要に応じて DB テーブルを初期化します（orders 等）。
   - DuckDB と SQLite のデフォルトパス:
     - DUCKDB_PATH: data/kabusys.duckdb
     - SQLITE_PATH: data/monitoring.db
   - .env で上書き可能（環境変数優先）。

6. 実行
   - 発注エンジン（Execution）
     - python -m kabusys.run_execution
     - paper_trading 環境では MockBrokerClient を使用し、paper_trading 用の SQLite に記録されます。
   - 監視ループ（Monitoring）
     - python -m kabusys.run_monitoring
     - ポーリング間隔を環境変数 MONITOR_POLL_INTERVAL（秒）で上書き可能（デフォルト 60 秒）。

---

## 使い方（CLI / 実行例）

- 環境設定ウィザード
  - python -m kabusys.config_setup
  - オプション: --env-file を指定して別パスへ保存可能

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- 発注エンジン起動
  - python -m kabusys.run_execution
  - 注意:
    - KILL_FLAG（data/kill.flag 等）や stop flag の状態により起動／停止が決まります。
    - KABUSYS_ENV=paper_trading または development は MockBrokerClient を使用。
    - KABUSYS_ENV=live は現状未実装（BrokerClientFactory が NotImplementedError を投げます）。

- 監視ループ起動
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を設定可能。

---

## 重要な環境変数（主なもの）

必須（validate_config / Settings._require で確認されるもの）
- JQUANTS_REFRESH_TOKEN — J-Quants API 用リフレッシュトークン
- KABU_API_PASSWORD — kabu ステーション API パスワード

任意 / 推奨
- KABUSYS_ENV — 実行環境 (development | paper_trading | live)
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH — 監視 DB（デフォルト data/monitoring.db）
- LOG_LEVEL — ログレベル（DEBUG, INFO, WARNING, ERROR, CRITICAL）
- KABU_API_BASE_URL — kabu station base URL（デフォルト http://localhost:18080/kabusapi）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID — 本番アラート用

その他
- PAPER_FILL_MODE — paper_trading 時のモックの振る舞い（instant | partial | never | reject）
- MONITOR_POLL_INTERVAL — 監視ポーリング間隔（秒）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアする（0/1）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 自動 .env 読み込みを無効化（値が設定されていれば読み込みしない）

設定の自動ロード順序:
- OS 環境変数 > .env.local > .env
- プロジェクトルートは __file__ を基準に .git または pyproject.toml から特定

注意:
- .env には機密情報が含まれるため絶対にリポジトリにコミットしないでください。

---

## 実装のポイント / 注意事項

- 発注の堅牢性
  - OrderManager.send_order は「OrderSent を DB に保存 → ブローカー呼び出し → broker_order_id を保存 → OrderAccepted」など、クラッシュ耐性を意識した2相的な永続化を行っています。
  - OrderSent 状態のままクラッシュした場合に備え、Reconciler による復旧処理があります。

- リスク管理
  - Gate1: シグナル単位の余力・重複・ポジション上限
  - Gate2: API レート制限（トークンバケツ）とサーキットブレーカー
  - Gate3: 約定後のドローダウン監視（初期資産評価を基準）

- MockBrokerClient
  - テスト用に fill_mode を変更して即時約定・部分約定・保留・拒否の振る舞いを確認可能（PAPER_FILL_MODE）。

- DB/ファイルのパス
  - いくつかのプロセスは起動前に親ディレクトリが存在するかを検査し、存在しない場合は警告を出します（自動作成される場合あり）。

---

## ディレクトリ構成（主要ファイル）

以下は src/kabusys 以下の主なファイル/モジュール構成（抜粋）です。

- src/kabusys/
  - __init__.py
  - config.py               — 環境変数読み込み / Settings クラス
  - config_setup.py         — .env 対話式ウィザード
  - validate_config.py      — 起動前設定検証 CLI
  - run_execution.py        — ExecutionEngine 起動スクリプト
  - run_monitoring.py       — SystemMonitor ポーリング起動スクリプト
  - execution/               — 発注関連（パッケージ）
    - __init__.py
    - broker_api.py         — ブローカー API Protocol / データモデル / ファクトリ
    - kabu_client.py        — kabu station 実装（httpx）
    - mock_client.py        — モックブローカー（テスト用）
    - broker_factory.py     — Settings に基づくクライアント生成
    - order_record.py       — OrderRecord（状態遷移ロジック）
    - order_repository.py   — SQLite 永続化層（orders テーブル）
    - order_manager.py      — OrderManager（外向き API）
    - execution_engine.py   — ExecutionEngine（主要制御フロー）
    - reconciler.py         — 起動時リコンシリエーション
    - risk_manager.py       — RiskManager（Gate1/2/3）
    - ... (その他)
  - data/
    - calendar_management.py — マーケットカレンダー管理（DuckDB）
    - news_collector.py      — RSS ニュース収集（defusedxml など安全対策）
    - jquants_client.py      — （参照あり、実装別途）
  - monitoring/              — 監視関連（MonitoringDB, SystemMonitor 等）
  - utils/                   — logging_setup, process_priority 等ユーティリティ（参照あり）

（※ 上はスナップショットの抜粋であり、実際のリポジトリではさらにファイルやサブパッケージが存在する可能性があります。）

---

## 開発・運用上のヒント

- .env 管理は慎重に
  - config_setup は便利だが、.env を漏洩しないように注意してください。
- 本番（live）環境
  - KABUSYS_ENV=live は慎重に扱ってください。validate_config は live の場合に追加チェック（LINE 設定、Kill Flag など）を行います。
  - BrokerClientFactory は現状 live 実装を未提供（NotImplementedError）なので、実際の本番運用には追加実装が必要です。
- テスト
  - MockBrokerClient で単体／統合テストを行えます。PAPER_FILL_MODE で挙動を切り替え可能。
- ロギング
  - setup_logging が利用され、LOG_LEVEL で制御できます。

---

## よくあるトラブルと対処

- validate_config で必須環境変数エラー
  - JQUANTS_REFRESH_TOKEN / KABU_API_PASSWORD が未設定。.env を作成して値を入れてください。
- 起動時に kill.flag のため起動拒否
  - data/kill.flag を確認。KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時にクリアされますが、本番では推奨されません。
- duckdb/sqlite のパスの親ディレクトリが無い
  - validate_config は警告を出します。手動でディレクトリを作成するか、起動時に自動作成される場合もあります。

---

## 参考コマンドまとめ

- 仮想環境作成
  - python -m venv .venv
  - source .venv/bin/activate

- 依存インストール（例）
  - pip install duckdb httpx websocket-client defusedxml PyYAML

- 環境設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- 実行
  - python -m kabusys.run_execution
  - python -m kabusys.run_monitoring

---

ご不明点や README に追加したい具体的な内容（例: サンプル .env、requirements.txt の中身、CI の設定など）があればお知らせください。補足ドキュメントを追記します。