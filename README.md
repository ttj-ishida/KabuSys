# KabuSys

日本株自動売買システム（ライブラリ/プロセス群）の一部実装ドキュメント。

このリポジトリは、シグナルを受けて発注を行う ExecutionEngine、監視ループ、設定読み込み/ウィザード、ブローカークライアント抽象などを含むモジュール群を提供します。実運用用ブローカー実装は未実装で、デフォルトではテスト用の MockBrokerClient を使用します。

---

## 目次
- プロジェクト概要
- 主な機能
- 動作環境 / 依存関係
- セットアップ手順
- 環境変数（必須 / 任意）
- 使い方
  - .env 設定ウィザード
  - 設定検証
  - 実行エンジンの起動
  - 監視ループの起動
- 開発・運用メモ
- ディレクトリ構成（主要ファイルの説明）

---

## プロジェクト概要
KabuSys は、J-Quants 等のデータを使ったシグナルに基づいて日本株の発注を自動化するためのコンポーネント群です。本コードベースは以下を提供します：

- 環境変数 / .env の自動読み込み・ウィザード（設定補助）
- 起動前設定検証ツール
- ExecutionEngine（シグナルを読み取って発注するエンジン）
- Order 状態管理（OrderRecord / OrderManager / OrderRepository）
- ブローカー API 抽象（BrokerAPIProtocol）と Mock 実装
- リスクガード（3 段階のリスクチェック）
- 起動時リコンシリエーション（Reconciler）
- 監視ループ（SystemMonitor をポーリングして監視 DB に記録）
- データ系ユーティリティ（マーケットカレンダー、ニュース収集など）

---

## 主な機能
- .env ウィザード（対話式）で初期設定を生成・更新
- 起動前に必須環境変数や config/*.yaml の整合性を検証
- ExecutionEngine により:
  - シグナル処理（指定時間帯に発注）
  - WebSocket push のドレイン（ブローカーからの注文更新受信）
  - Kill Switch（異常検出時に全注文をキャンセル）
- Order の状態遷移を厳格に管理（状態機械）
- MockBrokerClient によるローカルでの発注テスト（fill_mode を選択可能）
- RiskManager による Gate1/2/3 の3段階ガード（余力、重複、レート制限、サーキットブレーカー、ドローダウン）
- リコンシリエーション（起動時に OrderSent の不確定注文を照合して回復）

---

## 動作環境 / 依存関係
推奨 Python バージョン: 3.10+

主要依存（機能により任意もあり）:
- duckdb
- httpx
- websocket-client
- PyYAML（config.yaml のパース検証に使用）
- defusedxml（ニュース収集の XML パース用）
- その他：標準ライブラリの sqlite3, threading, logging など

※ requirements.txt は付随していないため、実行時に ImportError が出たモジュールを適宜インストールしてください。

例:
pip install duckdb httpx websocket-client PyYAML defusedxml

---

## セットアップ手順（ローカル開発向け）
1. リポジトリをクローン。
2. Python 仮想環境を作成・有効化。
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）
3. 必要なパッケージをインストール（上記依存を参照）。
4. データディレクトリを準備（必要に応じて）:
   - mkdir -p data
5. .env を作成（対話式ウィザードを推奨）:
   - python -m kabusys.config_setup
6. 設定を検証:
   - python -m kabusys.validate_config
   - 必要に応じて --strict を付けると警告も失敗扱い（exit 1）

---

## 環境変数（主要）
validate_config と config_setup に表記されている変数をまとめます。

必須（最低限設定が必要）:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

任意 / 推奨:
- KABUSYS_ENV: 実行環境（development / paper_trading / live）。デフォルト: development
  - paper_trading: MockBroker を使用して data/paper_trading.db に記録
  - live: 本番（注意: 本コードでは Live ブローカー実装は未実装・警告あり）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（デフォルト: data/monitoring.db）
- LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）
- KABU_API_BASE_URL: kabuステーション API ベース URL（デフォルト http://localhost:18080/kabusapi）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: 本番でのアラート通知用（任意）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（0/1。デフォルト 0）

注意:
- .env を絶対にリポジトリにコミットしないでください（シークレット含む）。
- KABUSYS_ENV=live を指定すると本番モード扱いのチェックが強化されます（LINE 通知等の必須確認）。

---

## 使い方

### 1) .env 設定ウィザード（対話式）
対話式で .env を作成・更新します。
コマンド:
python -m kabusys.config_setup

- 既存の .env を読み込めば Enter で既存値を再利用できます。
- secret フィールド（トークン等）は表示時にマスクされます。
- 最後に確認して .env を保存します。

### 2) 設定検証
.env と config/*.yaml（存在する場合）を起動前に検証します。
コマンド:
python -m kabusys.validate_config
厳密モード（警告を失敗として扱う）:
python -m kabusys.validate_config --strict

出力に INFO/WARNING/ERROR が表示され、エラーがあると exit code は 1 になります。

### 3) 実行エンジンの起動（Execution）
ExecutionEngine を起動してシグナル → 発注のフローを実行します。
コマンド:
python -m kabusys.run_execution

特徴:
- KABUSYS_ENV が paper_trading または development の場合、MockBrokerClient を使用。
- paper_trading の場合、紙上取引用 SQLite DB（data/paper_trading.db）に記録される。
- 起動直後に Reconciler が存在すればリコンシリエーションを実施。
- PID ファイル（デフォルト data/execution.pid）を書きます。
- 停止は data/stop_requested.flag を作成することで制御できます（存在検知で終了処理）。

### 4) 監視ループの起動（Monitoring）
システム監視ループを常時実行します（監視DB に定期記録）。
コマンド:
python -m kabusys.run_monitoring

特徴:
- MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）。
- monitoring は KABUSYS_ENV に依らず本番 sqlite_path を使用します（監視専用 DB に記録）。

---

## 開発・運用メモ
- Kill Switch:
  - 設定 KILL_FLAG_CLEAR_ON_START=1 にすると起動時に既存の kill.flag を自動でクリアします（本番では注意）。
  - 起動中に settings.kill_flag_path（デフォルト data/kill.flag）を検知するとキルスイッチを発動して全 active 注文をキャンセルします。
- DB 初期化:
  - orders テーブルは init_orders_db(conn) による冪等作成を想定しています（OrderRepository の init を見る）。
  - 監視 DB の初期化関数 init_monitoring_db が run_monitoring/run_execution から呼ばれます（存在確認してください）。
- MockBrokerClient:
  - fill_mode により挙動を変更（instant / partial / never / reject）。テストでの挙動制御に便利です。
- Live ブローカー:
  - KabuStationClient は実装されていますが、BrokerClientFactory は live を NotImplementedError にしてあります。実運用での利用には追加実装が必要です。

---

## 主なディレクトリ構成
（抜粋・説明つき）

- src/kabusys/
  - __init__.py
  - config.py
    - .env 自動読み込み、Settings クラス（環境変数ラッパ）
  - config_setup.py
    - .env 対話式ウィザード（python -m kabusys.config_setup）
  - validate_config.py
    - 起動前設定検証 CLI（python -m kabusys.validate_config）
  - run_execution.py
    - ExecutionEngine 起動スクリプト（python -m kabusys.run_execution）
  - run_monitoring.py
    - 監視ループ起動スクリプト（python -m kabusys.run_monitoring）
  - execution/
    - __init__.py
    - broker_api.py
      - BrokerAPIProtocol、データモデル、例外、ファクトリ
    - kabu_client.py
      - KabuStationClient（kabuステーション REST API 実装）
    - mock_client.py
      - MockBrokerClient（テスト用）
    - broker_factory.py
      - Settings に応じたクライアント生成
    - order_record.py
      - OrderRecord（状態遷移ロジック）
    - order_repository.py
      - SQLite を使った永続化層
    - order_manager.py
      - 発注フロー（OrderRecord + Repository + BrokerAPI を統合）
    - execution_engine.py
      - ExecutionEngine（シグナル処理 + push ドレイン）
    - reconciler.py
      - 起動時リコンシリエーション（OrderSent の突合）
    - risk_manager.py
      - Gate1/2/3 のリスク管理
  - data/
    - calendar_management.py
      - 市場カレンダー管理（DuckDB ベース）
    - news_collector.py
      - RSS からのニュース収集ユーティリティ
    - （その他 jquants_client など外部 API クライアントモジュールが参照される）
  - monitoring/
    - monitoring_db.py (参照されているがここでは省略)
    - system_monitor.py (参照されているがここでは省略)
  - utils/
    - logging_setup.py (参照されている)
    - process_priority.py (参照されている)

---

必要に応じて README を拡張して、実運用の手順（systemd/journald 連携、ログローテーション、データバックアップ、テスト手順、CI 設定など）を追加してください。質問や追加でほしい情報（例: サンプル .env.example、DB スキーマ、API のモックでのユニットテスト例）があれば教えてください。