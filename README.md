# KabuSys

日本株自動売買システムのコアライブラリ（リードミー）

このリポジトリは、シグナルを受け取って発注を行う ExecutionEngine、起動時のリコンシリエーション、監視ループ、環境設定ウィザード／検証などを含む自動売買の基本コンポーネントを提供します。実運用（live）は未実装の部分がありますが、開発・ペーパートレード用途で動作する設計です。

---

## プロジェクト概要

主な目的：
- シグナルに基づく発注フロー（ExecutionEngine）
- 発注状態管理（OrderRecord / OrderRepository / OrderManager）
- ブローカー抽象（BrokerAPIProtocol）とモック実装（MockBrokerClient）
- 起動時リコンシリエーション（Reconciler）
- 3段階リスクガード（RiskManager）
- マーケットカレンダー管理、ニュース収集などのデータ処理ユーティリティ
- 環境設定ウィザード（.env 作成）および設定検証 CLI
- 監視プロセス（SystemMonitor）を常駐する run_monitoring スクリプト

設計方針：
- DB（SQLite / DuckDB）を利用して永続化・解析を分離
- Broker クライアントは Protocol を通して差し替え可能（テストは Mock を使用）
- 再起動後の安全性（OrderSent の二相永続化、Reconciliation）に配慮

---

## 機能一覧

- 環境設定ウィザード（python -m kabusys.config_setup）
  - 対話式で .env を生成／更新
- 設定検証（python -m kabusys.validate_config）
  - 必須環境変数、YAML 設定ファイル、パスなどの事前チェック
  - --strict で警告も FAIL 扱い
- 実行エンジン起動（python -m kabusys.run_execution）
  - ExecutionEngine によりシグナル読み込み→発注→push ドレインを実行
  - KABUSYS_ENV により mock ブローカーを使用（paper_trading/dev）
- 監視ループ起動（python -m kabusys.run_monitoring）
  - SystemMonitor をポーリングして監視ログを記録
- ブローカー抽象と実装
  - BrokerAPIProtocol（インターフェース）
  - MockBrokerClient（テスト用）
  - KabuStationClient（kabu station REST API 実装）
- 注文永続化・状態遷移管理
  - OrderRepository（SQLite）
  - OrderRecord / OrderState（状態遷移検証）
- リスク管理
  - RiskManager（Gate1/2/3：シグナル、実行、メトリクス）
  - サーキットブレーカー／レート制限など
- データユーティリティ
  - calendar_management（営業日判定・カレンダー更新ジョブ）
  - news_collector（RSS 収集・前処理）

---

## セットアップ手順

前提：
- Python 3.9+（型注釈の使用に伴う互換性）
- システムに duckdb、httpx、websocket-client 等をインストールすることを推奨

推奨パッケージ（最低限）:
- duckdb
- httpx
- websocket-client
- PyYAML（設定検証で YAML パースを行う場合に必要）
- defusedxml（news_collector で使用）
- その他：requests 相当や標準ライブラリのみで動く機能もあります

例（pip）:
pip install duckdb httpx websocket-client pyyaml defusedxml

リポジトリの配置想定：
- プロジェクトルートに `.env` / `.env.local` を配置するか、環境変数で設定します。
- 自動ロード：プロジェクトルートは .git または pyproject.toml を基準に自動判定されます。
  - 自動ロード無効化：環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`

初期設定手順：
1. .env を作る（対話式ウィザード推奨）
   - python -m kabusys.config_setup
2. 設定検証
   - python -m kabusys.validate_config
   - 問題があれば .env を修正して再検証
3. 実行（ペーパートレード）
   - KABUSYS_ENV=paper_trading に設定の上、python -m kabusys.run_execution
4. 監視起動（任意）
   - python -m kabusys.run_monitoring

注意：
- `.env` は絶対に Git にコミットしないでください（config_setup のヘッダにも明記しています）。
- デフォルト DB パスはプロジェクト内の `data/` に作られます（存在しない親ディレクトリは起動時に作成される場合があります）。

---

## 環境変数（主な項目）

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants API 用
- KABU_API_PASSWORD — kabuステーション API パスワード

主な任意／デフォルト:
- KABUSYS_ENV — 実行環境（development / paper_trading / live）※ live では注意喚起あり
  - デフォルト: development
- DUCKDB_PATH — DuckDB のパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite（監視 DB）パス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード時の専用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）（デフォルト: INFO）
- KABU_API_BASE_URL — kabu station のベース URL（デフォルト: http://localhost:18080/kabusapi）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — 本番での通知用（任意）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（0/1、デフォルト: 0）
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング秒数（デフォルト: 60）

自動ロード：
- プロジェクトルートの `.env` → `.env.local`（優先）を自動で読み込みます。OS 環境変数は上書きされません（例外: .env.local で override=True。ただし既存の OS 環境変数は protected）。

設定検証：
- python -m kabusys.validate_config
  - --strict を付けると警告もエラー扱いで exit(1)

---

## 使い方（主要コマンド）

1. 環境設定ウィザード（.env 作成／更新）
   - python -m kabusys.config_setup
   - 対話式で主要な環境変数を入力します。シークレット値はマスク表示されます。
   - 保存後に `python -m kabusys.validate_config` で検証することを推奨。

2. 設定検証
   - python -m kabusys.validate_config
   - 出力に INFO / WARNING / ERROR が表示されます。
   - --strict を付けると WARNING があると exit code 1 になります。

3. 実行エンジン（セッション実行）
   - python -m kabusys.run_execution
   - KABUSYS_ENV が `paper_trading` または `development` の場合は MockBrokerClient を使用します（paper_trading は専用 SQLite を使用して本番 DB と分離）。
   - run_execution は PID ファイルを書き、stop フラグ（data/stop_requested.flag）を検出すると安全終了します。
   - 実行中に `data/kill.flag` の存在によって起動拒否や kill_switch が発動します（KILL_FLAG_CLEAR_ON_START の値に依存）。

4. 監視ループ
   - python -m kabusys.run_monitoring
   - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更可能（デフォルト 60 秒）。
   - 監視は常に本番の sqlite_path を使用します（環境に関係なく）。

注意点：
- ペーパートレードでは発注は仮想的に処理され、`PAPER_TRADING_SQLITE_PATH` に履歴が記録されます。
- live 実装は未完成の箇所があります（BrokerClientFactory は live で NotImplementedError を投げます）。

---

## 初期 DB の作成（補足）

- orders テーブル等は run_execution 内で init_monitoring_db / init_orders_db が呼ばれて作成されます（冪等）。
- 個別に初期化したい場合は Python REPL 等で以下を実行できます（例）:

from kabusys.config import Settings
import sqlite3, duckdb
from kabusys.execution.order_repository import init_orders_db
from kabusys.monitoring.monitoring_db import init_monitoring_db  # monitoring_db モジュールを参照

settings = Settings()
sqlite_conn = sqlite3.connect(str(settings.sqlite_path))
init_monitoring_db(sqlite_conn)
init_orders_db(sqlite_conn)  # orders テーブルを作りたい場合
duckdb_conn = duckdb.connect(str(settings.duckdb_path))

---

## 主要コンポーネント（簡易説明）

- config.py / Settings
  - 環境変数読み込みとアクセス API。プロジェクトルートの .env を自動ロードします。
- config_setup.py
  - .env の生成・更新ウィザード。
- validate_config.py
  - .env と config/*.yaml（存在する場合）を事前検証。
- execution/
  - broker_api.py — ブローカー API の Protocol／データモデル／ファクトリ
  - kabu_client.py — kabu station 実装（HTTP + WebSocket）
  - mock_client.py — テスト用モック（fill_mode 等を指定可能）
  - broker_factory.py — Settings を基にブローカークライアントを生成
  - order_record.py, order_repository.py, order_manager.py — 注文状態遷移・SQLite 永続化・外向き API
  - execution_engine.py — シグナル処理と push ドレインを行うエンジン
  - risk_manager.py — Gate1/2/3 のリスク検査
  - reconciler.py — 起動時の自動復旧・リコンシリエーション
- data/
  - calendar_management.py — 営業日管理・J-Quants 連携（カレンダー更新ジョブ）
  - news_collector.py — RSS 収集と前処理（SSRF 対策等を実装）
- monitoring/
  - monitoring_db.py, system_monitor.py — 監視 DB とモニタリング処理（run_monitoring で使用）
- utils/
  - logging_setup.py, process_priority.py — ログ設定、プロセス優先度設定ユーティリティ

（上記は主なファイル・モジュールの一覧です。詳細は該当ソースを参照してください。）

---

## ディレクトリ構成（主要ファイル）

リポジトリの主要なツリー（抜粋）:

- src/
  - kabusys/
    - __init__.py
    - config.py
    - config_setup.py
    - validate_config.py
    - run_execution.py
    - run_monitoring.py
    - execution/
      - __init__.py
      - broker_api.py
      - broker_factory.py
      - kabu_client.py
      - mock_client.py
      - order_record.py
      - order_repository.py
      - order_manager.py
      - execution_engine.py
      - reconciler.py
      - risk_manager.py
      - ...（その他関連モジュール）
    - data/
      - calendar_management.py
      - news_collector.py
      - jquants_client.py (参照あり)
      - ...
    - monitoring/
      - monitoring_db.py
      - system_monitor.py
      - ...
    - utils/
      - logging_setup.py
      - process_priority.py
      - ...

---

## 補足・運用上の注意

- 本番運用（KABUSYS_ENV=live）は慎重に。validate_config は live 設定時に多数の警告を出します（LINE 通知設定等）。
- kill.flag / stop_requested.flag / PID ファイルを用いたプロセス制御に対応しています。運用スクリプトでの管理を推奨します。
- .env の自動ロードは便利ですが、CI / テスト環境では `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定して無効化してください。
- 設定ファイル（config/*.yaml）が必要な場合、validate_config は PyYAML が無いと内容検証をスキップします。必要であれば pyyaml をインストールしてください。
- ロギングは utils/logging_setup.py で設定します。ログレベルは LOG_LEVEL 環境変数で制御してください。

---

必要であれば、この README をベースにインストール手順（requirements.txt / Dockerfile / systemd ユニットファイル）のテンプレートや、より詳しい運用手順を追加できます。どの情報を優先して追記しますか？