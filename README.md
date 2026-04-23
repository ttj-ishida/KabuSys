# KabuSys

日本株向けの自動売買システム（プロジェクト骨格）。  
このリポジトリは、環境設定管理、発注エンジン、リスクガード、リコンシリエーション、監視ループ、ニュース収集やマーケットカレンダー管理などの主要コンポーネントを含む構成になっています。

> 注: ここに含まれるコードはプロダクション用途の設計思想を持ちますが、実行環境・証券会社 API の扱いには十分注意してください。特に KABUSYS_ENV=live のときは慎重に設定・確認を行ってください。

---

## 主な機能

- 環境変数の自動読み込み（`.env` / `.env.local`）
- 対話式の `.env` 生成ウィザード（`config_setup`）
- 設定検証 CLI（`.env` と `config/*.yaml` の基本チェック）
- ExecutionEngine（シグナル読み取り → 発注フロー）
  - OrderRecord / OrderRepository による状態管理と永続化（SQLite）
  - OrderManager による送信・同期・キャンセルロジック
  - RiskManager による 3 段階リスクガード（Gate1/2/3）
  - Reconciler による再起動後の自動復旧
- ブローカークライアント
  - MockBrokerClient（開発 / ペーパートレード用）
  - KabuStationClient（kabuステーション REST API 実装）
- 監視ループ（SystemMonitor 起動スクリプト）
- データ系ユーティリティ
  - マーケットカレンダー管理（J-Quants 経由）
  - ニュース収集（RSS → 正規化 → DB 保存）

---

## 前提（Requirements）

- Python 3.10+（typing, dataclass, match 等の言語機能に依存）
- 推奨パッケージ（最低限、以下は必要/便利）:
  - duckdb
  - httpx
  - websocket-client
  - PyYAML（config YAML 検証用、任意）
  - defusedxml（RSS パース用）
- SQLite（標準ライブラリに含まれます）
- （kabu station を使う場合）kabuステーションがローカルで起動していること

インストール例（仮）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb httpx websocket-client PyYAML defusedxml
# または requirements.txt があれば: pip install -r requirements.txt
```

---

## セットアップ手順（クイックスタート）

1. リポジトリをクローンし、仮想環境を作る
2. 必要なパッケージをインストール（上記参照）
3. .env を準備する（2 通りの方法）
   - 対話式ウィザードで作成:
     ```bash
     python -m kabusys.config_setup
     ```
     ウィザード終了後、`.env` に保存されます（保存時に `python -m kabusys.validate_config` で検証する旨のメッセージが出ます）。
   - 手動で `.env` を作成: 必須変数は下記参照
4. 設定検証を実行:
   ```bash
   python -m kabusys.validate_config
   # 警告をエラー扱いにする場合:
   python -m kabusys.validate_config --strict
   ```
5. 実行（例）
   - 監視ループ:
     ```bash
     python -m kabusys.run_monitoring
     ```
   - 実行エンジン:
     ```bash
     python -m kabusys.run_execution
     ```
   - どちらも `KABUSYS_ENV` に応じて動作（`development` / `paper_trading` / `live`）

---

## 環境変数（主要）

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants API 用
- KABU_API_PASSWORD — kabuステーション API パスワード

任意 / 推奨:
- KABUSYS_ENV — 実行環境（development / paper_trading / live）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- LOG_LEVEL — ログレベル（DEBUG / INFO / WARNING / ERROR / CRITICAL）
- KABU_API_BASE_URL — kabuステーションのベース URL（デフォルト: http://localhost:18080/kabusapi）
- LINE_CHANNEL_ACCESS_TOKEN — LINE 通知用（本番では設定推奨）
- LINE_USER_ID — 通知先ユーザー ID（本番では設定推奨）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動でクリアする（0/1、デフォルト 0）
- MONITOR_POLL_INTERVAL — 監視ポーリング間隔（秒、デフォルト 60）

備考:
- `.env` / `.env.local` は自動で読み込まれます（OS 環境変数が優先）。
- 自動ロードを無効化するには: `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。
- `.env` は絶対にバージョン管理にコミットしないでください（README 内で繰り返し警告）。

---

## 使い方（主要 CLI）

- 環境設定ウィザード（対話式）
  ```bash
  python -m kabusys.config_setup
  ```

- 設定検証（起動前チェック）
  ```bash
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict   # 警告も FAIL 扱い
  ```

- 監視ループ起動（SystemMonitor）
  ```bash
  python -m kabusys.run_monitoring
  ```
  - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を秒単位で上書き可能（デフォルト 60）

- 実行エンジン起動（ExecutionEngine）
  ```bash
  python -m kabusys.run_execution
  ```
  - `KABUSYS_ENV=paper_trading` のときは MockBrokerClient を使用し、paper_trading 専用の SQLite（`PAPER_TRADING_SQLITE_PATH`）に記録します。
  - 起動時に `data/execution.pid`（デフォルト）へ PID を書き、`data/kill.flag` の存在で停止などのガードが入ります。
  - 停止フラグ: リポジトリの data/stop_requested.flag で各ループを安全に停止できます（スクリプトが監視するフラグ）。

---

## 運用上の注意（重要）

- KABUSYS_ENV=live を設定すると本番モードになります。LINE 通知などの設定が不十分だとアラートが届かないため、validate_config の警告を必ず確認してください。
- kill.flag（デフォルト: data/kill.flag）や KILL_FLAG_CLEAR_ON_START の設定により、誤操作でプロセスが起動しないようになっています。運用方針を決めてから運用してください。
- 本番での証券会社 API 利用時はネットワーク、認証、資金管理に細心の注意を払ってください。実際にマネーを扱う前にテスト（paper_trading / mock）で十分に動作確認を行ってください。

---

## ディレクトリ構成（抜粋）

以下は主要ファイル・モジュール群の概観（src/kabusys 配下）です。

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数読み込みと Settings クラス（アプリ設定）
  - config_setup.py          — 対話式 .env ウィザード
  - validate_config.py       — .env / config/*.yaml の起動前検証ツール
  - run_execution.py         — ExecutionEngine 起動スクリプト（エントリポイント）
  - run_monitoring.py        — SystemMonitor ポーリングループ起動スクリプト
  - execution/
    - broker_api.py          — Broker API の Protocol / データモデル / 例外 / ファクトリ
    - broker_factory.py      — Settings に基づくブローカーファクトリ
    - kabu_client.py         — kabuステーション REST クライアント（HTTP/WebSocket）
    - mock_client.py         — MockBrokerClient（テスト用）
    - order_record.py        — OrderRecord（状態遷移ロジック）
    - order_repository.py    — SQLite 永続化層（orders テーブル）
    - order_manager.py       — 発注ロジック（Send/Sync/Cancel）
    - execution_engine.py    — ExecutionEngine（シグナル処理＋push ドレイン）
    - reconciler.py          — リコンシリエーション（再起動復旧）
    - risk_manager.py        — 3 段階のリスクガード
  - data/
    - calendar_management.py — マーケットカレンダー管理
    - news_collector.py      — RSS ニュース収集
    - (その他: jquants_client 等が想定)
  - monitoring/               — 監視関連（monitoring_db, system_monitor 等）
  - utils/
    - logging_setup.py       — ロギング初期化ユーティリティ（参照あり）
    - process_priority.py    — プロセス優先度設定ユーティリティ（参照あり）
  - config/                   — 設定用 YAML ファイル群（例: system_config.yaml 等）

（上記はコードベースの主要ファイルを抜粋したものです。実際のリポジトリにはさらに補助スクリプトやドキュメントがある場合があります。）

---

## 参考コマンド例（実践）

- .env を作る（ウィザード）
  ```bash
  python -m kabusys.config_setup
  ```

- 設定を検証
  ```bash
  python -m kabusys.validate_config --strict
  ```

- ペーパートレードで実行エンジンを起動
  ```bash
  export KABUSYS_ENV=paper_trading
  python -m kabusys.run_execution
  ```

- 監視ループをデフォルト間隔で起動
  ```bash
  python -m kabusys.run_monitoring
  # ポーリング間隔を 30 秒にしたい場合:
  export MONITOR_POLL_INTERVAL=30
  python -m kabusys.run_monitoring
  ```

---

## その他

- .env / 認証情報は絶対に Git にコミットしないこと。
- `validate_config` は起動前に必ず実行するワークフローを推奨します（--strict モードで CI に組み込むのが安全です）。
- paper_trading / development では MockBrokerClient を使って安全に動作確認できます。live 実装は慎重に導入してください。

---

もし README に追記してほしい内容（例: CI 設定例、詳細な DB スキーマ、API シーケンス図、開発用テスト手順など）があれば教えてください。必要に応じてドキュメントを拡張します。