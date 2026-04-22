# KabuSys

日本株自動売買システムの軽量プロトタイプ。  
このリポジトリは、シグナルに基づく発注エンジン、ブローカークライアント（Mock/KabuStation）ラッパー、リスク管理、起動時リコンシリエーション、監視ループ、環境設定ウィザード／検証ツールなどを含みます。

注意: 本実装では本番ブローカークライアント（KabuStationClient）は簡易的に実装されています。実稼働前には十分な検証と本番ブローカ連携の実装が必要です。

---

## 主な機能

- 環境設定ウィザード（.env の対話式作成 / 更新）
- 設定検証 CLI（.env と config/*.yaml の事前検査）
- 実行エンジン（ExecutionEngine）
  - Signal Queue からの発注処理（発注時間帯の制御）
  - 発注のクラッシュ安全化（OrderSent の二相永続化等）
  - リスク管理（Gate1/2/3：余力、重複、ポジション上限、レート制限、サーキットブレーカー、ドローダウン監視）
  - WebSocket（kabu push）ドレイン処理
  - 起動時リコンシリエーション（OrderSent の突合、ポジション差分検出）
- 監視ループ（SystemMonitor を定期実行、監視 DB へ記録）
- ブローカーファクトリ（MockBrokerClient を用いた paper_trading / development 環境サポート）
- データ処理ユーティリティ（マーケットカレンダー管理、RSS ニュース収集など）
- SQLite / DuckDB を用いた永続化・分析基盤

---

## 必要条件（依存パッケージ）

主な外部依存（例）:

- Python 3.8+
- duckdb
- httpx
- websocket-client
- PyYAML（config 検証を行う場合に必要）
- defusedxml

インストール例:

```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb httpx websocket-client PyYAML defusedxml
```

※ 実際の運用では requirements.txt / poetry / pip-tools 等で依存管理してください。

---

## セットアップ手順

1. リポジトリをクローンしてワークディレクトリへ移動。

2. 仮想環境を作成して依存パッケージをインストール（上記参照）。

3. .env を作成する
   - 対話式ウィザードを使う（推奨）:
     ```bash
     python -m kabusys.config_setup
     ```
   - 手動で作る場合は .env.example を参考にプロジェクトルートに `.env` を配置してください。

4. 設定検証（必須環境変数が設定されているか、config/*.yaml が存在・パース可能かをチェック）:
   ```bash
   python -m kabusys.validate_config
   # strict モード: 警告も失敗扱い
   python -m kabusys.validate_config --strict
   ```

5. 実行・監視プロセスを起動
   - Execution（発注エンジン）
     ```bash
     python -m kabusys.run_execution
     ```
     - KABUSYS_ENV が `paper_trading` の場合、MockBrokerClient を使い paper_trading 用 SQLite（デフォルト: data/paper_trading.db）に記録します。
   - Monitoring（システム監視）
     ```bash
     python -m kabusys.run_monitoring
     ```
     - 監視は環境にかかわらず本番 sqlite（デフォルト: data/monitoring.db）を使用します。

---

## 環境変数（主なもの）

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants API 用リフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API パスワード

任意 / 推奨:
- KABUSYS_ENV — 実行環境: development / paper_trading / live（デフォルト: development）
  - live を使う場合は追加の注意（LINE 通知や kill flag 等）があります
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — paper_trading 用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- KABU_API_BASE_URL — kabu API の base URL
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — アラート用 LINE 設定
- KILL_FLAG_CLEAR_ON_START — 起動時に kill flag を自動クリアするか（0/1、デフォルト 0）
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、デフォルト 60）

.env の自動ロード:
- ランタイム起動時、Settings モジュールはプロジェクトルート（.git または pyproject.toml を探索）を起点に `.env` を自動読み込みします。
- 読込順: OS 環境変数 > .env > .env.local（.env.local は既存を上書き）
- 自動ロードを無効化する場合: KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定

検証ツール:
- `python -m kabusys.validate_config` は必須 env の未設定やプレースホルダ値、config/*.yaml の存在・パースエラーなどを報告します。

---

## 使い方・運用メモ

- .env 作成:
  - 対話式: python -m kabusys.config_setup
  - ウィザード後に .env を保存すると次のステップとして validate_config を推奨（ウィザードにメッセージあり）

- 設定検証:
  - python -m kabusys.validate_config
  - --strict を付けると警告も失敗（exit code 1）として扱う

- 実行フロー:
  - run_execution:
    - プロセス優先度を "high" に設定（内部ユーティリティ）
    - SQLite / DuckDB に接続し、監視テーブル（init_monitoring_db）や orders テーブル（init_orders_db）などを冪等に初期化
    - BrokerClientFactory により環境に合わせたブローカークライアントを生成（dev/paper_trading → Mock）
    - ExecutionEngine を起動し、シグナル処理（8:50-9:10）と push ドレイン（9:10-15:30）を実行
    - stop フラグ / kill.flag に対応（data/kill.flag の存在を監視）。起動時に kill.flag があり、KILL_FLAG_CLEAR_ON_START=0 の場合は起動を拒否します
  - run_monitoring:
    - SystemMonitor をポーリング（デフォルト 60 秒）。MONITOR_POLL_INTERVAL で上書き可
    - 監視は常に本番 sqlite_path を使用（環境に依らず）

- kill / stop の仕組み:
  - 停止用フラグ: data/stop_requested.flag（スクリプト内で検出）
  - Kill Switch（致命的なリスク違反で全注文をキャンセル）や kill.flag の存在による起動拒否など保護機構が実装されています

- DB とファイル:
  - デフォルトのファイルは `data/` 配下に作られます。親ディレクトリが存在しない場合は起動時に自動作成される箇所もありますが、権限等に注意してください。

---

## 開発メモ（主要コンポーネント説明）

- kabusys.config
  - .env 自動読み込みロジック、Settings クラス（環境変数をプロパティとしてラップ）
  - 設定取得時にバリデーション（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE 等）

- kabusys.config_setup
  - .env を対話的に生成・更新する CLI ウィザード

- kabusys.validate_config
  - .env と config/*.yaml の存在・値チェック。--strict オプションあり

- kabusys.run_execution
  - ExecutionEngine の起動スクリプト。ExecutionEngine は発注・WebSocket ドレイン・リコンシリエーション等を管理

- kabusys.execution
  - broker_api: データモデル、Protocol、ファクトリ
  - kabu_client: kabuステーション REST / WebSocket 実装
  - mock_client: テスト用 MockBrokerClient（fill_mode サポート）
  - order_record / order_repository / order_manager: 注文状態管理と SQLite 永続化
  - execution_engine: 発注ループと push ドレイン
  - reconciler: OrderSent の自動照合とローカル/ブローカー間のポジション差分検出
  - risk_manager: Gate1/2/3 のリスクチェックとサーキットブレーカー等

- kabusys.monitoring
  - 監視DB初期化、SystemMonitor（ソース内に実装ファイルあり）

- kabusys.data
  - calendar_management: マーケットカレンダーの管理（DuckDB と J-Quants 連携）
  - news_collector: RSS 取得と記事整形・保存（セキュリティ対策済）

---

## ディレクトリ構成（主要ファイル）

（プロジェクトルートの src/kabusys を基準）

- src/kabusys/
  - __init__.py
  - config.py                     — 環境変数読み込み / Settings
  - config_setup.py               — .env 対話式ウィザード
  - validate_config.py            — 設定検証 CLI
  - run_execution.py              — 発注エンジン起動スクリプト
  - run_monitoring.py             — 監視ループ起動スクリプト
  - execution/
    - __init__.py
    - broker_api.py               — Protocol / データモデル / ファクトリ
    - kabu_client.py              — kabuステーション REST / WebSocket 実装
    - mock_client.py              — テスト用モック
    - broker_factory.py           — 設定からクライアントを生成
    - order_record.py             — 注文状態モデル・遷移
    - order_repository.py         — SQLite 永続化
    - order_manager.py            — 注文 API（外向け）
    - execution_engine.py         — セッション管理 / 発注ロジック
    - reconciler.py               — 起動時リコンシリエーション
    - risk_manager.py             — 3段階リスクガード
  - data/
    - calendar_management.py      — マーケットカレンダー管理（DuckDB）
    - news_collector.py           — RSS 取得・正規化
    - (その他データ関連モジュール)
  - monitoring/
    - monitoring_db.py            — 監視DB初期化・書き込みユーティリティ
    - system_monitor.py           — SystemMonitor（ポーリング実装）
  - utils/
    - logging_setup.py            — ロギング設定ユーティリティ
    - process_priority.py         — プロセス優先度設定ユーティリティ
  - config/
    - *.yaml                      — 各種設定ファイル（system/data/strategy/risk/...）

---

## よくある質問・注意点

- config/*.yaml が無い場合:
  - validate_config は警告を出します（generate_config.py などで生成可能とメッセージが出ます）
  - 一部のコンポーネントは YAML を参照するため、実行時に必要なファイルは用意してください

- 本番運用の注意:
  - KABUSYS_ENV=live のときは追加の警告・ガードがあります。LINE 通知等を有効にし、KILL_FLAG_CLEAR_ON_START は慎重に扱ってください
  - KabuStationClient の実装は実運用での挙動確認が必須です（API レスポンスの差分やエラーハンドリング）

---

この README はコードベースの主要機能と運用上のポイントをまとめたものです。詳細な API 仕様やデプロイ手順、運用手順は別途ドキュメント（運用マニュアルや DataPlatform.md）を参照してください。必要があれば README を拡張して具体的な例（.env.example、SQL 初期化スクリプト、docker-compose など）を追加できます。