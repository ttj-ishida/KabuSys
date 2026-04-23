# KabuSys

日本株向け自動売買基盤（部分実装）。  
本リポジトリは、シグナルに基づく発注エンジン、監視プロセス、設定ウィザードと検証ツール、ブローカークライアント（Mock / kabu station）などを含むモジュール群を提供します。

## 概要
KabuSys は、local 開発 / ペーパートレード / 将来的な本番（live）を想定した自動売買フレームワークです。  
主な設計方針は次のとおりです。

- 発注ロジックと永続化（SQLite）を分離した堅牢な Order State Machine
- 実行前・実行中の多段階リスクガード（Gate1/2/3）
- 再起動時のリコンシリエーション（OrderSent の突合作業）
- duckdb を用いたシグナル / ポートフォリオ管理（分析向け）
- .env ベースの設定管理と対話式ウィザード、起動前検証 CLI

## 主な機能一覧
- 環境設定ウィザード（python -m kabusys.config_setup）
- 設定検証ツール（python -m kabusys.validate_config）
  - .env と config/*.yaml の基本チェック（PyYAML があれば YAML のパース検査も実施）
  - --strict オプションで警告も失敗扱い
- ExecutionEngine（発注エンジン）
  - Signal を読み取り Gate1/2 を経てブローカーへ発注
  - WebSocket push のドレイン処理、Gate3（ドローダウン）監視
  - Paper trading / development 環境では MockBrokerClient を使用（本番クライアント未実装）
- Monitoring（SystemMonitor）ポーリングループ
  - 監視用 SQLite にログを書く（監視は本番 DB を使用）
  - MONITOR_POLL_INTERVAL でポーリング間隔を制御
- Broker クライアント
  - MockBrokerClient（テスト用）
  - KabuStationClient（kabu station REST API 実装、HTTP/WebSocket）
- Order の永続化（SQLite）・Repository・Manager・Record（状態遷移の検証）
- Reconciler（再起動時の自動復旧）
- Data モジュール例：マーケットカレンダー管理、ニュース収集（RSS）等

## セットアップ手順（開発者向け）
前提: Python 3.9+ を想定（型ヒント・標準ライブラリ利用を踏まえて）。環境に応じて適宜読み替えてください。

1. リポジトリをクローン／チェックアウト
   - ルートに `.git` または `pyproject.toml` がある想定です（config 自動ロードに使用）。

2. 依存パッケージをインストール
   - requirements.txt があればそれを使ってください（本コードベースには同梱されていません）。
   - 最低限の推奨パッケージ:
     - duckdb
     - httpx
     - websocket-client
     - PyYAML（config YAML 検証を有効にする場合）
     - defusedxml（ニュース収集）
   - 例:
     ```
     pip install duckdb httpx websocket-client PyYAML defusedxml
     ```

3. .env を作成
   - 対話式ウィザードを使う:
     ```
     python -m kabusys.config_setup
     ```
     ウィザードは .env を生成／更新します（秘密値は入力時にマスク表示）。
   - 手動作成する場合は後述のサンプルを参考にしてください。

4. 設定検証（起動前確認）
   ```
   python -m kabusys.validate_config
   # 警告も FAIL としたい場合:
   python -m kabusys.validate_config --strict
   ```

5. 実行
   - ExecutionEngine（発注エンジン）:
     ```
     python -m kabusys.run_execution
     ```
     KABUSYS_ENV が `paper_trading` の場合、paper_trading 用の SQLite（PAPER_TRADING_SQLITE_PATH）を使用します。`live` は未実装（NotImplementedError）。
   - Monitoring:
     ```
     python -m kabusys.run_monitoring
     ```
     MONITOR_POLL_INTERVAL 環境変数でポーリング秒数を変更可能（デフォルト 60 秒）。

注意:
- .env は絶対にリポジトリにコミットしないでください（ウィザードの出力ヘッダにも明記されています）。
- 自動で .env をロードする仕組みがあります（プロジェクトルートに基づいて .env / .env.local を読み込み）。自動ロードを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

## 必須 / 推奨の環境変数
（config ウィザードや validate_config がチェックする主なもの）

必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

任意 / 推奨（デフォルト値あり）:
- KABUSYS_ENV (development | paper_trading | live) — default: development
- DUCKDB_PATH — default: data/kabusys.duckdb
- SQLITE_PATH — default: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH — default: data/paper_trading.db
- LOG_LEVEL — default: INFO
- KABU_API_BASE_URL — default: http://localhost:18080/kabusapi
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID — 本番での通知に必要
- KILL_FLAG_CLEAR_ON_START — default: 0（本番では 0 推奨）
- MONITOR_POLL_INTERVAL — 監視プロセスのポーリング秒数（実行時に参照）

設定の自動読み込み挙動:
- ロード順: OS 環境変数 > .env.local > .env
- .env.local があると .env の値を上書きします（.env.local はローカル専用）
- OS 側に既にあるキーは保護され、自動ロードでは上書きされません
- 自動ロード無効化: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

簡易 .env サンプル:
```
# --- J-Quants API ---
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here

# --- kabuステーション API ---
KABU_API_PASSWORD=your_kabu_api_password_here
KABU_API_BASE_URL=http://localhost:18080/kabusapi

# --- データベース ---
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db

# --- 環境 ---
KABUSYS_ENV=development
LOG_LEVEL=INFO

# --- Kill Switch ---
KILL_FLAG_CLEAR_ON_START=0
```

## 使い方（主要コマンド）
- 環境ウィザード（.env を生成）
  ```
  python -m kabusys.config_setup
  ```

- 設定検証（起動前チェック）
  ```
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- 実行（発注エンジン）
  ```
  python -m kabusys.run_execution
  ```
  - 起動前に .env を整え、validate_config で問題がないことを確認してください。
  - 起動中の停止は `data/stop_requested.flag` を作成することで要求できます。
  - PID ファイルはデフォルトで `data/execution.pid`（設定で変更可）。

- 監視（SystemMonitor ポーリング）
  ```
  python -m kabusys.run_monitoring
  ```
  - MONITOR_POLL_INTERVAL 環境変数で周期（秒）を指定できます。

注意点:
- Paper トレード: KABUSYS_ENV=paper_trading により MockBrokerClient が利用され、発注情報は paper_trading 用 SQLite に分離されます（PAPER_FILL_MODE 等で約定挙動を変更可能）。
- Live 環境サポートは一部未実装です（BrokerFactory は live を拒否します）。

停止 / リスタート関連:
- 停止要求: プロジェクトルートの `data/stop_requested.flag` を作成すると監視／実行ループが検知して終了します。
- kill switch: `data/kill.flag` による強制停止 / 注文キャンセル処理が組み込まれています。起動時に `KILL_FLAG_CLEAR_ON_START=1` を設定すると既存の kill.flag を自動でクリアして起動します（本番では推奨されません）。

## ディレクトリ構成（抜粋）
以下は src/kabusys 以下の主要ファイル／モジュール構成（本 README 作成時点の内容に基づく抜粋）:

```
src/kabusys/
├── __init__.py
├── config.py                 # 環境変数ロード・Settings
├── config_setup.py           # .env 対話ウィザード
├── validate_config.py        # 設定検証 CLI
├── run_execution.py          # ExecutionEngine 起動スクリプト
├── run_monitoring.py         # Monitoring 起動スクリプト
├── execution/
│   ├── __init__.py
│   ├── broker_api.py         # Broker API の Protocol / データモデル / ファクトリ
│   ├── broker_factory.py     # Settings に基づくブローカーファクトリ
│   ├── kabu_client.py        # kabu station 実装（HTTP/WebSocket）
│   ├── mock_client.py        # MockBrokerClient（テスト用）
│   ├── order_record.py       # Order の状態遷移ロジック（純粋モデル）
│   ├── order_repository.py   # SQLite 永続化層
│   ├── order_manager.py      # 外向き API（発注／キャンセル／同期）
│   ├── execution_engine.py   # ExecutionEngine（シグナル処理・WebSocket）
│   ├── reconciler.py         # 再起動時リコンシリエーション
│   └── risk_manager.py       # Gate1/2/3 のリスク統制
├── monitoring/
│   ├── monitoring_db.py      # 監視用 DB 初期化・アクセス
│   └── system_monitor.py     # システムリソース監視（CPU/MEM/DISK 等）
├── data/
│   ├── calendar_management.py  # マーケットカレンダー管理
│   └── news_collector.py       # RSS ニュース収集
└── utils/
    ├── logging_setup.py      # ロギング設定ユーティリティ
    └── process_priority.py   # プロセス優先度設定ユーティリティ
```

（実際のリポジトリにはさらに補助スクリプトやテスト、ドキュメントが存在する可能性があります）

## 補足 / 注意事項
- 本番環境（KABUSYS_ENV=live）を有効にする際は、必ず設定検証（validate_config）や通知設定（LINE トークン等）を確認してください。validate_config は live 時に追加の警告（LINE 設定、KILL_FLAG_CLEAR_ON_START 等）を出します。
- ブローカー API のエラーや再接続処理、WebSocket の受信処理は実装済みですが、外部サービス（kabu station）の設定やネットワーク環境に依存します。
- DB スキーマ初期化（orders / monitoring 等）は起動時に自動で行われる箇所があります（init_orders_db / init_monitoring_db）。ただし初期データやバックフィル処理は運用スクリプトで実行する想定です。

---
より詳しいドキュメントや運用手順、CI/CD の設定、テスト手順は別途ドキュメントにまとめることを推奨します。README の内容はコードベースの主要点をまとめたものであり、実運用前には十分なテストとレビューを行ってください。