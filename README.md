# KabuSys

日本株自動売買システムの軽量コアライブラリ（README）。  
この README はリポジトリ内のソースコードに基づき、導入・実行方法や各コンポーネントの概要をまとめたものです。

> 注: このリポジトリはサンプル/実装例を含むため、実際の取引を行うには設定や実運用上の検討が必要です。KABUSYS_ENV=live による本番稼働は慎重に行ってください。

---

目次
- プロジェクト概要
- 主な機能
- 前提条件 / 依存関係
- セットアップ手順
- 使い方（主要コマンド）
- 環境変数一覧（必須 / 任意）
- 停止・制御方法（stop / kill）
- ディレクトリ構成

---

## プロジェクト概要

KabuSys は日本株の自動売買に必要な以下の要素を備えたシステムコアのサンプル実装です。

- 発注エンジン（ExecutionEngine）: シグナル取り込み → Gate チェック → 発注フロー
- ブローカー抽象化: 実ブローカー（kabu station）とモック実装を透過的に切替え
- 注文状態管理（OrderRecord/OrderManager）と永続化（SQLite）
- リコンシリエーション（再起動後の自動復旧）
- リスクガード（Gate1/2/3: 余力・重複・レート制限・ドローダウン等）
- 監視ループ（SystemMonitor 用の polling スクリプト）
- 設定ウィザード（.env 生成）, 設定検証ツール

設計方針は「DB にビジネスロジックを埋めず、クライアント層と永続化層を分離する」「クラッシュ・再起動時の整合性を保つ（二相永続化やリコンシリエーション）」等にあります。

---

## 主な機能

- .env 対話式ウィザード（config_setup.py）で初期設定を作成
- 起動前に環境変数・設定ファイル(config/*.yaml) を検証する CLI（validate_config.py）
- ExecutionEngine によるシグナル駆動の発注処理（run_execution.py）
- Monitoring 用のポーリングループ（run_monitoring.py）
- Broker 抽象化：MockBrokerClient（テスト用）／KabuStationClient（実接続用）
- 注文状態の状態遷移モデル（OrderRecord）と永続化（SQLite）
- リスクガード（RiskManager）: Gate1（シグナル）, Gate2（送信前）, Gate3（約定後）
- カレンダー管理（DuckDB ベース）・ニュース収集などデータ関連ユーティリティ

---

## 前提条件 / 依存関係

- Python 3.10 以上（型ヒントの構文や union 型表記などを使用）
- 必要な Python パッケージ（最低限）:
  - duckdb
  - httpx
  - websocket-client
  - defusedxml
  - PyYAML（config 検証に必須ではないが推奨）
  - その他（標準ライブラリでカバーされるものが多い）

インストール例（仮）:
```
python -m pip install duckdb httpx websocket-client defusedxml PyYAML
```

プロジェクト化されている場合は requirements.txt があればそこからインストールしてください。

---

## セットアップ手順

1. リポジトリをクローン / チェックアウトする
2. Python 仮想環境を作成して有効化
   ```
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
   ```
3. 依存パッケージをインストール
   ```
   python -m pip install --upgrade pip
   python -m pip install duckdb httpx websocket-client defusedxml PyYAML
   ```
4. .env を作成（対話式ウィザードを推奨）
   ```
   python -m kabusys.config_setup
   ```
   ウィザードは .env（デフォルト: プロジェクトルート/.env）を生成・更新します。機密値はマスクされます。

5. 設定検証
   ```
   python -m kabusys.validate_config
   python -m kabusys.validate_config --strict   # 警告も FAIL 扱い
   ```
   validate_config は .env の主要な環境変数や config/*.yaml の存在／パースをチェックします（PyYAML 未インストール時は YAML 検証をスキップして警告）。

6. DB 用ディレクトリを作成（必要に応じて）
   デフォルトで使用されるパス:
   - DuckDB: data/kabusys.duckdb
   - SQLite (monitoring): data/monitoring.db
   - Paper trading SQLite: data/paper_trading.db
   - PID / flag ファイル: data/*.pid / data/kill.flag / data/stop_requested.flag

   事前に data/ ディレクトリを作成しておくと安全です:
   ```
   mkdir -p data
   ```

---

## 使い方（主要コマンド）

- 環境設定ウィザード（.env の生成・更新）
  ```
  python -m kabusys.config_setup
  ```

- 設定検証（起動前チェック）
  ```
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- 実行エンジン起動（発注処理）
  - ペーパートレード（Mock ブローカー）で実行する例:
    ```
    export KABUSYS_ENV=paper_trading
    python -m kabusys.run_execution
    ```
    Windows Powershell / CMD では環境変数の設定方法が異なります。
  - run_execution は settings に応じて paper_trading 時は paper_trading 用 SQLite DB を使用します。

- 監視ループ起動（SystemMonitor）
  ```
  python -m kabusys.run_monitoring
  ```
  ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL（秒）で上書き可能（デフォルト 60 秒）。

- それぞれのプロセスは data/stop_requested.flag の存在を検出すると優雅に停止します（run_execution と run_monitoring で利用）。Kill スイッチ（即時全キャンセル）は data/kill.flag（settings.kill_flag_path）で管理される挙動に依存します。

---

## 環境変数一覧（主なもの）

必須（エンジン起動や API 利用に必要）
- JQUANTS_REFRESH_TOKEN — J-Quants API 用リフレッシュトークン（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）

主な任意 / 設定可能項目
- KABUSYS_ENV — 実行環境: development | paper_trading | live（デフォルト: development）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite (monitoring)（デフォルト: data/monitoring.db）
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- KABU_API_BASE_URL — kabu station API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- LINE_CHANNEL_ACCESS_TOKEN — LINE 通知用トークン（任意）
- LINE_USER_ID — LINE 通知先ユーザー ID（任意）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアする (0/1; デフォルト 0)
- PAPER_FILL_MODE — paper_trading の fill 動作: instant | partial | never | reject（default: instant）
- PAPER_TRADING_SQLITE_PATH — paper_trading 用 SQLite（デフォルト: data/paper_trading.db）
- PID_FILE_PATH, KILL_FLAG_PATH など（Settings で参照）

自動 .env ロードの挙動:
- デフォルトでプロジェクトルートの .env（および .env.local）を自動で読み込みます。OS 環境変数は優先されます。
- 自動ロードを無効化する: KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

Settings API（コード内での参照例）
- from kabusys.config import settings
- settings.jquants_refresh_token / settings.kabu_api_password / settings.duckdb_path / settings.sqlite_path / settings.env / settings.is_live / settings.paper_fill_mode など

---

## 停止・制御方法

- 優雅な停止（外部から監視スクリプトや実行エンジンに停止を通知）:
  - ファイル data/stop_requested.flag を作成すると、run_execution / run_monitoring のループが検出して終了します。

- Kill Switch（全注文キャンセル等、安全確保用）:
  - kill.flag（デフォルト data/kill.flag）を使用して kill_switch を検出します。設定によっては起動時に kill.flag が存在すると起動を拒否します（KILL_FLAG_CLEAR_ON_START により動作が変わります）。

- PID 管理:
  - 実行時に PID ファイルが書き出されます（settings.pid_file_path、デフォルト data/execution.pid）。終了時に削除されます。

---

## ディレクトリ構成（主要ファイル）

以下はリポジトリ内の主要なモジュール構成（抜粋）です。

```
.
├─ config/                          # YAML 設定ファイル（system_config.yaml 等）
├─ data/                            # デフォルト DB / フラグ / PID を置く場所
├─ src/
│  └─ kabusys/
│     ├─ __init__.py
│     ├─ config.py                  # 環境変数読み込み・Settings
│     ├─ config_setup.py            # .env 対話ウィザード
│     ├─ validate_config.py         # 起動前設定検証 CLI
│     ├─ run_execution.py           # ExecutionEngine 起動スクリプト
│     ├─ run_monitoring.py          # SystemMonitor ポーリングスクリプト
│     ├─ data/
│     │  ├─ calendar_management.py  # マーケットカレンダー管理（DuckDB）
│     │  └─ news_collector.py       # RSS ニュース収集
│     ├─ execution/
│     │  ├─ __init__.py
│     │  ├─ broker_api.py           # Broker API プロトコル・ファクトリ
│     │  ├─ kabu_client.py          # KabuStationClient（実ブローカー用）
│     │  ├─ mock_client.py          # MockBrokerClient（テスト用）
│     │  ├─ broker_factory.py       # Settings に基づくクライアント生成
│     │  ├─ order_record.py         # Order 状態モデル
│     │  ├─ order_repository.py     # SQLite 永続化
│     │  ├─ order_manager.py        # 注文管理（外部 API）
│     │  ├─ execution_engine.py     # 発注エンジンのコア
│     │  ├─ reconciler.py           # 再起動時のリコンシリエーション
│     │  └─ risk_manager.py         # Gate1/2/3 のリスク制御
│     ├─ monitoring/
│     │  └─ ...                     # 監視用 DB / SystemMonitor (省略)
│     └─ utils/
│        ├─ logging_setup.py
│        └─ process_priority.py
└─ pyproject.toml / setup.py (省略)
```

config/ 以下には以下の YAML 期待ファイルがあります（validate_config.py 参照）:
- system_config.yaml
- data_config.yaml
- strategy_config.yaml
- risk_config.yaml
- execution_config.yaml
- monitoring_config.yaml

validate_config はこれらの存在と YAML のパース可否をチェックします（PyYAML がインストールされている場合）。

---

## 運用上の注意

- 実際の売買を伴う場合は KABUSYS_ENV=live の設定や本番ブローカーの利用に際して十分な事前検証、監視、レート制御、障害対策が必要です。
- .env ファイルは機密情報を含むため、決して Git 等にコミットしないでください（config_setup.py も README コメントで注意喚起しています）。
- リコンシリエーションや OrderSent の扱いはクラッシュや部分的失敗を想定した設計になっていますが、本番運用では手動オペレーションと監査ログが重要です。
- KabuStationClient は kabuステーション® アプリがローカルで動作していることを前提とします。接続先 URL と API パスワードの設定を確認してください。

---

この README はコードベースから自動的に要点を抽出して作成しています。細かい実装や追加モジュール（monitoring の内部、SystemMonitor 実装など）はソースを参照してください。必要であれば、導入手順の具体化、Docker 化や CI/CD 用セットアップ例、運用チェックリスト等の追記も対応します。