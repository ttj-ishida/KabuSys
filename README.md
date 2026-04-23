# KabuSys

バージョン: 0.1.0

日本株自動売買システムのコア実装（モジュール群）。このリポジトリには、環境設定ウィザード、設定検証ツール、発注エンジン、監視ループ、データ処理ユーティリティなどが含まれます。

---

## 概要

KabuSys は以下の目的をもつモジュール群です。

- シグナルに基づく発注（ExecutionEngine）
- ブローカー API 抽象化（KabuStation 実装 + Mock 実装）
- 注文状態管理と永続化（SQLite）
- リコンシリエーション（クラッシュ後の自動復旧）
- 3段階のリスクガード（Gate1/2/3）
- マーケットカレンダー管理 / ニュース収集などのデータ処理
- 起動前の設定検証 / 対話式 .env 生成ウィザード
- 監視プロセス（SystemMonitor）

設計方針として、DB 操作とビジネスロジックを明確に分離し、テスト容易性を重視しています。paper_trading モードでは MockBrokerClient を用いて本番 DB と完全に分離して動作します。

---

## 主な機能一覧

- .env 対話式作成ウィザード（python -m kabusys.config_setup）
- 起動前設定検証 CLI（python -m kabusys.validate_config）
  - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL 検証、DB パス確認、config/*.yaml 存在・YAML パースチェック、live 環境の追加ガード等
  - --strict フラグで警告も失敗扱いにできます（CI 用）
- ExecutionEngine（run_execution.py）
  - シグナル読み込み → Gate1/2 のリスクチェック → 発注 → WebSocket push ドレイン → Gate3 ドローダウン監視
  - paper_trading では MockBrokerClient を使用し、paper DB に分離
- Broker クライアント
  - KabuStationClient（httpx + websocket）
  - MockBrokerClient（テスト用、fill_mode 制御）
  - 共通インターフェース（BrokerAPIProtocol）
- 注文管理
  - OrderRecord（状態遷移ロジック）
  - OrderRepository（SQLite 永続化）
  - OrderManager（送信/同期/キャンセル）
  - Reconciler（起動時の OrderSent 照合とポジション差分検出）
- RiskManager（レート制限・サーキットブレーカー・ポジション制御・ドローダウン判定）
- データ関連
  - calendar_management（営業日判定、next_trading_day 等）
  - news_collector（RSS 収集）
- 監視ループ（run_monitoring.py）
  - SystemMonitor による定期ポーリング（MONITOR_POLL_INTERVAL で変更可能）
  - 監視は常に本番 sqlite_path を参照

---

## セットアップ

1. Python 環境を用意（推奨: 3.10+）

2. 仮想環境作成（例）
   ```bash
   python -m venv .venv
   source .venv/bin/activate   # macOS/Linux
   .venv\Scripts\activate      # Windows
   ```

3. 依存パッケージをインストール（要件ファイルがある場合はそちらを使用）
   例: 必要な主要パッケージ
   ```bash
   pip install duckdb httpx websocket-client pyyaml defusedxml
   ```
   - PyYAML は config/*.yaml の内容検証に使用されます（任意）。未インストールでも動作しますが、YAML 検証はスキップされます。
   - sqlite3 は標準ライブラリです。

4. リポジトリルートに移動して環境ファイルを作成します（下記参照）。

注意:
- .env は絶対に Git にコミットしないでください（README 内にも警告あり）。
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動で .env を読み込む処理を無効化できます（テスト用途など）。

---

## 環境変数（.env）

本システムは環境変数から設定を読み込みます（自動でプロジェクトルートの `.env` → `.env.local` を読みます。OS 環境変数が優先されます）。

- 必須:
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD

- 任意（しばしば設定する）:
  - KABUSYS_ENV : development | paper_trading | live（デフォルト: development）
  - DUCKDB_PATH : デフォルト data/kabusys.duckdb
  - SQLITE_PATH : 監視 DB（デフォルト data/monitoring.db）
  - LOG_LEVEL : DEBUG | INFO | WARNING | ERROR | CRITICAL（デフォルト: INFO）
  - KABU_API_BASE_URL : kabu station の base URL（デフォルト: http://localhost:18080/kabusapi）
  - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID : 本番アラート用（任意）
  - KILL_FLAG_CLEAR_ON_START : 0（デフォルト） or 1（起動時に kill.flag をクリア）
  - PAPER_FILL_MODE（instant | partial | never | reject）: paper_trading 動作制御
  - PAPER_TRADING_SQLITE_PATH : paper_trading 用 SQLite（デフォルト data/paper_trading.db）
  - PID_FILE_PATH, KILL_FLAG_PATH, CPU_THRESHOLD_PCT など監視関連パラメータも存在します（Settings クラス参照）

.env の自動読み込みルール:
- OS 環境 > .env.local > .env の順で解釈されます。
- 自動読み込みを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

サンプル（.env の一部）:
```
JQUANTS_REFRESH_TOKEN=your_token_here
KABU_API_PASSWORD=your_kabu_password_here
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
LOG_LEVEL=INFO
```

---

## 使い方

1. .env を対話式に作成する（推奨）
   ```bash
   python -m kabusys.config_setup
   ```
   - 既存 .env を読み込んで Enter で再利用できます。
   - 作成後、validate_config の案内が表示されます。

2. 設定検証
   ```bash
   python -m kabusys.validate_config
   python -m kabusys.validate_config --strict  # 警告も FAIL 扱い
   ```
   - .env と config/*.yaml の存在・基本的整合性を検査します。
   - PyYAML がインストールされていれば YAML のパース検証も行います。

3. 監視デーモンを起動
   ```bash
   python -m kabusys.run_monitoring
   ```
   - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒単位で上書き可能（デフォルト 60）。
   - 監視は常に本番 sqlite_path を参照します（paper_trading でも本番パスを参照）。

4. エンジン（発注プロセス）を起動
   ```bash
   python -m kabusys.run_execution
   ```
   - KABUSYS_ENV が `paper_trading` の場合は MockBrokerClient が使用され、paper_trading 用 SQLite（PAPER_TRADING_SQLITE_PATH）に記録します。
   - 起動時に data/stop_requested.flag が存在すると起動しません。
   - 実行中に data/stop_requested.flag を作成すると安全停止処理が走ります。
   - ExecutionEngine は PID ファイルを書き込みます（デフォルト: data/execution.pid）。

5. 開発／テスト用ユーティリティ
   - MockBrokerClient を用いることで外部依存なしに発注フローをテストできます。
   - Reconciler は起動時の OrderSent 注文をブローカー側と突合し、状態を回復します。

---

## 重要なファイル / 動作フロー（簡易）

- 起動前:
  - .env を作成し（config_setup）、validate_config で検証
- run_execution:
  - Settings 読み込み → DB 初期化（監視テーブル）→ Broker クライアント生成 → ExecutionEngine 起動
  - ExecutionEngine: シグナル処理（8:50-9:10）、Push ドレイン（9:10-15:30）
- run_monitoring:
  - SystemMonitor を定期実行してメトリクスや稼働状況を記録

---

## ディレクトリ構成（主要ファイル）

以下はパッケージ内部の主要ファイル／モジュール構成の抜粋です（src/kabusys 以下）。

- src/kabusys/
  - __init__.py (バージョン等)
  - config.py (Settings クラス、.env 自動読み込みロジック)
  - config_setup.py (対話式 .env ウィザード)
  - validate_config.py (起動前設定検証 CLI)
  - run_execution.py (ExecutionEngine 起動スクリプト)
  - run_monitoring.py (SystemMonitor ポーリングループ起動スクリプト)
  - execution/
    - broker_api.py (データモデル、Protocol、ファクトリ)
    - kabu_client.py (kabu station 実装)
    - mock_client.py (テスト用モック)
    - broker_factory.py (Settings に基づくクライアント生成)
    - order_record.py (注文状態遷移モデル)
    - order_repository.py (SQLite 永続化)
    - order_manager.py (外向け注文 API)
    - execution_engine.py (発注エンジン)
    - reconciler.py (リコンシリエーション)
    - risk_manager.py (3段階リスクガード)
  - data/
    - calendar_management.py (営業日ロジック)
    - news_collector.py (RSS 収集)
    - jquants_client.py (J-Quants API クライアント — 実装参照)
  - monitoring/
    - monitoring_db.py (監視DB初期化／操作)
    - system_monitor.py (監視ロジック)
  - utils/
    - logging_setup.py
    - process_priority.py

（注）上記の一部ファイルは本 README の元コード一覧に含まれています。実際のリポジトリではさらにファイルやサブモジュールが存在する可能性があります。

---

## 運用・トラブルシューティング

- .env を決してリポジトリに含めないでください（認証情報が含まれます）。
- 起動前に必ず:
  1. python -m kabusys.config_setup で .env を整備
  2. python -m kabusys.validate_config で検証
- 本番環境（KABUSYS_ENV=live）では LINE の通知設定（LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID）を必ず確認してください（validate_config は live で警告を出します）。
- PID / flag ファイル:
  - data/execution.pid 等の PID ファイルは起動時に作成され、終了時に削除されます。
  - data/stop_requested.flag を作成すると実行中プロセスに安全停止指示を出せます。
  - data/kill.flag が存在すると ExecutionEngine は起動を拒否します（KILL_FLAG_CLEAR_ON_START=1 の場合は起動時にクリアされる挙動があります）。
- デバッグや CI では validate_config の --strict を有効にして、警告も失敗として扱うのが推奨です。

---

## 開発メモ / 拡張ポイント

- Live ブローカー（KabuStationClient）の完全運用対応や認証フローの詳細設定は将来的に拡張可能です（BrokerClientFactory は現在 paper_trading / development を mock に割り当てます）。
- YAML 設定ファイル（config/*.yaml）の生成スクリプトはリポジトリ内に存在する可能性があります（validate_config の警告参照: python scripts/generate_config.py）。
- WebSocket の受信や再接続、トークン更新ロジックは KabuStationClient に実装されていますが、実環境でのストレステストが重要です。

---

この README はリポジトリ内のコードを基に要点をまとめたものです。詳細な使用法や API の仕様は各モジュールの docstring を参照してください。質問や追加のドキュメントが必要であれば教えてください。