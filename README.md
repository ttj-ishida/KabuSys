# KabuSys

日本株自動売買システムの部分実装（ライブラリ + 実行スクリプト群）

このリポジトリは、発注エンジン（ExecutionEngine）・監視プロセス・設定管理・データ周りユーティリティを含むモジュール群です。開発 / ペーパートレード環境向けに Mock ブローカーを用意しており、実運用（live）のブローカー実装は現時点では未実装です。

バージョン: 0.1.0

---

## プロジェクト概要

- 発注フロー、状態遷移（OrderRecord / OrderManager）、永続化（SQLite）、発注用 API クライアント層（kabu station 用実装 + モック）、リスクガード（3 段階）、リコンシリエーション機能を含む実行基盤。
- 設定ウィザード（.env を対話的に作成）・起動前設定検証ツール・監視ループ用スクリプトを提供。
- DuckDB を使ったシグナル/カレンダーデータ・ニュース収集などの Data レイヤー補助コードを含む。

主要な設計ポイント:
- 設定は環境変数（または .env / .env.local）で管理。Settings クラスで安全に取得。
- ExecutionEngine はシグナルプル型 + WebSocket push ドレインで発注を行う（セッション時間帯で動作を切り分け）。
- RiskManager による Gate1/2/3（シグナル検査 / 実行前レート制限＋CB / 約定後ドローダウン監視）。
- 発注の堅牢性のために二相的永続化（OrderSent の扱い）と起動時の Reconciler による自動復旧。

---

## 機能一覧

- 設定管理
  - .env/.env.local 自動読み込み（プロジェクトルートは .git または pyproject.toml で検出）
  - Settings クラスで型・妥当性チェック（KABUSYS_ENV / LOG_LEVEL 等）
  - 対話式設定ウィザード（python -m kabusys.config_setup）

- 設定検証
  - .env と config/*.yaml の存在・基本妥当性を検査（PyYAML があれば YAML パースも実施）
  - 必須 env チェック、値のプレースホルダ検出など（python -m kabusys.validate_config）

- 発注実行 (Execution)
  - ExecutionEngine：シグナルの読み込み・Gate チェック・発注・push ドレイン
  - OrderRecord（状態遷移）、OrderRepository（SQLite 永続化）、OrderManager（発注 API 呼び出しの安全化）
  - Broker クライアント:
    - MockBrokerClient（テスト/開発用、fill_mode を選択可能）
    - KabuStationClient（kabu station REST API 実装）
  - RiskManager（Gate1/2/3）・Reconciler（起動時の同期）
  - run_execution スクリプト（python -m kabusys.run_execution）

- 監視
  - SystemMonitor ベースのポーリングループ（run_monitoring）
  - MONITOR_POLL_INTERVAL によるポーリング間隔指定（デフォルト 60 秒）

- データユーティリティ
  - calendar_management（営業日判定、next/prev_trading_day 等）
  - news_collector（RSS 収集、正規化、SSRF 対策）
  - jquants_client（J-Quants 連携は別モジュール参照）

---

## セットアップ手順（開発向け）

1. Python 環境を用意（3.9+ 推奨）
2. 依存パッケージをインストール（プロジェクトに requirements.txt がある場合はそちらを使用）  
   最低限必要になりそうなパッケージ例:
   - duckdb
   - httpx
   - websocket-client
   - defusedxml
   - PyYAML（config YAML 検証を行う場合）
   例:
   pip install duckdb httpx websocket-client defusedxml pyyaml

3. プロジェクトルートに移動（.git または pyproject.toml があるディレクトリ）
4. 対話式で .env を作成:
   python -m kabusys.config_setup
   - ウィザードが対話形式で .env を生成します。保存後、validate_config を実行して検証してください。
5. 設定検証:
   python -m kabusys.validate_config
   - --strict を付けると警告も失敗（exit code 1）扱いになります。

注意:
- 自動 .env ロードは Settings モジュール起動時に行われます（.env → .env.local、OS 環境変数は保護）。自動ロードを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- プロジェクトルートの検出は __file__ を基準に親ディレクトリへ遡り .git または pyproject.toml を探します。配布後の環境では注意してください。

---

## 環境変数（主要）

必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

任意（デフォルト値あり／または機能に応じて使用）:
- KABUSYS_ENV   : development | paper_trading | live  （デフォルト: development）
- DUCKDB_PATH   : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH   : 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH : ペーパートレード専用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL     : DEBUG | INFO | WARNING | ERROR | CRITICAL（デフォルト: INFO）
- KABU_API_BASE_URL : kabu station API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID : 本番アラート用（live 環境では設定推奨）
- KILL_FLAG_CLEAR_ON_START : 0|1（本番では 0 推奨）
- MONITOR_POLL_INTERVAL : 監視ポーリング間隔（秒、デフォルト 60）

Settings クラスで多くの値を取得・妥当性チェックしています。PAPER_FILL_MODE（paper_trading 用）等、その他プロパティも存在します（詳しくは kabusys.config.Settings を参照）。

---

## 使い方（主要スクリプト）

- 環境セットアップ（対話式）:
  python -m kabusys.config_setup

- 設定検証（起動前チェック）:
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict

- 実行エンジン起動（発注プロセス）:
  python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading または development では MockBrokerClient が使われます（paper_trading は sqlite DB を分離して記録）。
  - KABUSYS_ENV=live の場合は現時点でライブブローカーは未実装（BrokerClientFactory が NotImplementedError を投げます）。

- 監視プロセス起動:
  python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更できます（デフォルト 60 秒）。

運用上のフラグ:
- 停止フラグ: project_root/data/stop_requested.flag を作成するとループが穏やかに終了します（スクリプトがこのファイルを監視）。
- kill.flag: settings.kill_flag_path（デフォルト data/kill.flag）を配置すると ExecutionEngine が起動を拒否または実行中に kill_switch を発動します。KILL_FLAG_CLEAR_ON_START=1 のときは起動時に自動クリアされます（本番では推奨しません）。
- PID ファイル: 起動時に data/<...>.pid を書き出します（設定で変更可）。

ログ:
- setup_logging が利用され、LOG_LEVEL で制御します。

---

## 実装上の注意点／設計メモ

- 発注の堅牢性:
  - OrderManager.send_order は OrderSent を先に永続化 → ブローカー送信 → broker_order_id を先に保存 → 状態更新、という二相的永続化を行い、クラッシュ復旧のための Reconciler に配慮した設計になっています。
  - OrderSentPendingError（broker 側で order_id は発行されたが約定がない/保留）は broker_order_id を保存した上で再スローし、後続の reconciler/監視で回収可能にします。

- RiskManager:
  - Gate1: 余力・重複・1銘柄上限・総利用率上限
  - Gate2: トークンバケツによるレート制限 + サーキットブレーカー（OPEN/HALF_OPEN）
  - Gate3: ドローダウン監視（初期ポートフォリオ評価額に対する閾値）

- データ分離:
  - paper_trading 環境では SQLite を paper_trading 用に分け、本番データと分離します（settings.paper_sqlite_path）。

- モジュール分割:
  - 発注ロジック・DB 層・API クライアントは明確に分離しており、テストやモック差し替えが容易です（create_broker_api(factory) を利用）。

---

## ディレクトリ構成（抜粋）

(src/kabusys をルートとした主要ファイル/ディレクトリ)

- src/
  - kabusys/
    - __init__.py
    - config.py                # 環境変数読み込み・Settings
    - config_setup.py          # .env 対話ウィザード
    - validate_config.py       # 起動前設定検証 CLI
    - run_execution.py         # ExecutionEngine 起動スクリプト
    - run_monitoring.py        # SystemMonitor 起動スクリプト
    - execution/               # 発注コンポーネント群
      - __init__.py
      - broker_api.py
      - kabu_client.py
      - mock_client.py
      - broker_factory.py
      - order_record.py
      - order_repository.py
      - order_manager.py
      - execution_engine.py
      - reconciler.py
      - risk_manager.py
      - ...                    # その他補助モジュール
    - data/
      - calendar_management.py
      - news_collector.py
      - jquants_client.py (参照)
    - monitoring/
      - monitoring_db.py
      - system_monitor.py
    - utils/
      - logging_setup.py
      - process_priority.py
    - strategy/                 # 戦略関連（エクスポート領域）
    - ...                       # その他

---

## よくある操作例

1. 初期設定
   - python -m kabusys.config_setup
   - python -m kabusys.validate_config --strict

2. ペーパートレードでエンジン起動（同一端末でテストしたい場合）
   - KABUSYS_ENV=paper_trading python -m kabusys.run_execution

3. 監視プロセスを別プロセスで起動
   - python -m kabusys.run_monitoring

4. 停止（優雅な停止）
   - touch data/stop_requested.flag

---

## 依存関係（参考）

- 標準ライブラリ: os, sys, sqlite3, threading, logging, time, datetime, pathlib, json 等
- サードパーティ（機能により）:
  - duckdb
  - httpx
  - websocket-client
  - defusedxml
  - PyYAML（config の YAML 検証）
  - その他（必要に応じて requirements.txt を用意してください）

---

README はここまでです。さらに詳しい API 仕様（OrderRequest/OrderResponse/OrderStatus のフィールドなど）やテスト手順、CI 設定、デプロイ手順が必要であればお知らせください。