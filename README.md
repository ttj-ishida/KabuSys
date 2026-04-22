# KabuSys

日本株自動売買システム（KabuSys）の軽量実装。  
シグナルに基づく発注エンジン、ブローカークライアント（mock / kabu station）、リスクガード、発注履歴永続化、起動時のリコンシリエーション、監視ループなどを含みます。

バージョン: 0.1.0

---

## 概要

KabuSys は以下を目的としたモジュール群を提供します。

- シグナルを取り込み発注を行う ExecutionEngine
- 発注状態（OrderRecord）と永続化（SQLite）を分離した堅牢な発注ワークフロー
- 3段階のリスクガード（Gate1: シグナルレベル、Gate2: 実行レベル、Gate3: メトリクス）
- 起動時のリコンシリエーション（OrderSent 状態の復旧・照合）
- モニタリング用ループ（システム負荷や監視 DB へのログ）
- 開発／テスト用の MockBrokerClient による紙/ローカル検証
- .env 対話ウィザードと起動前設定検証ツール

---

## 主な機能一覧

- 環境変数ベースの設定管理（自動 .env 読み込み）
- 対話式 .env 設定ウィザード（python -m kabusys.config_setup）
- 起動前設定検証 CLI（python -m kabusys.validate_config）
- ExecutionEngine（シグナル処理・WebSocket push ドレイン）
- OrderManager / OrderRecord（状態遷移を検証する注文管理）
- OrderRepository（SQLite による永続化、競合対策の unique index）
- Reconciler（再起動時の自動復旧・ポジション差分検出）
- RiskManager（rate limit / circuit-breaker / drawdown 等）
- Broker クライアントファクトリ（Mock / KabuStationClient）
- Monitoring loop（監視用 sqlite と DuckDB 接続）
- Data モジュール（カレンダー管理、ニュース収集等）

---

## 前提（Requirements）

- Python 3.10 以上（型注釈に `X | Y` を使用）
- 推奨パッケージ（用途に応じて必要）:
  - duckdb
  - httpx
  - websocket-client
  - pyyaml （config/*.yaml のパース検証時に必要）
  - defusedxml （ニュース収集で利用）
- SQLite 標準ライブラリは不要（組み込み）

（プロジェクト配下に requirements.txt は含まれていないため、必要な依存だけインストールしてください）

例:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb httpx websocket-client pyyaml defusedxml
# 追加の依存がある場合は必要に応じてインストール
```

---

## セットアップ手順

1. リポジトリをクローンして作業ディレクトリへ移動
2. 仮想環境を作成して有効化
3. 必要なパッケージをインストール（上記参照）
4. .env（環境変数ファイル）を作成
   - 対話式ウィザードを使う:
     ```bash
     python -m kabusys.config_setup
     ```
     これによりプロジェクトルートの `.env` を作成／更新できます。
   - 手動で作る場合は .env に以下の必須キーを設定してください（例）:
     - JQUANTS_REFRESH_TOKEN=...
     - KABU_API_PASSWORD=...
     - その他任意の設定は下記「環境変数一覧」を参照
5. 設定検証（起動前）
   ```bash
   # WARNING を FAIL（exit 1）扱いにする場合は --strict
   python -m kabusys.validate_config
   python -m kabusys.validate_config --strict
   ```
6. 実行
   - 実行エンジン（発注ループ）
     ```bash
     python -m kabusys.run_execution
     ```
   - 監視ループ
     ```bash
     python -m kabusys.run_monitoring
     ```

起動スクリプトは内部で DB 初期化関数を呼びます（monitoring は sqlite を、全体で duckdb を使用）。初回実行時にデータディレクトリ（デフォルトは `data/`）を自動作成することが期待されますが、権限等に注意してください。

---

## 環境変数一覧（主要）

必須:
- JQUANTS_REFRESH_TOKEN  
  - J-Quants API 用リフレッシュトークン（必須）
- KABU_API_PASSWORD  
  - kabuステーション API パスワード（必須）

任意 / デフォルト値:
- KABUSYS_ENV (development | paper_trading | live)  
  - デフォルト: development
  - paper_trading では MockBrokerClient を使用し、paper_trading 用 SQLite（data/paper_trading.db）を使います
  - live は本番（注意: 本コードでは Live broker client 実装に制約があり NotImplementedError になる箇所あり）
- DUCKDB_PATH  
  - デフォルト: data/kabusys.duckdb
- SQLITE_PATH  
  - デフォルト: data/monitoring.db
- LOG_LEVEL  
  - デフォルト: INFO
- KABU_API_BASE_URL  
  - デフォルト: http://localhost:18080/kabusapi
- LINE_CHANNEL_ACCESS_TOKEN  
  - 任意（本番環境ではアラート用に必要）
- LINE_USER_ID  
  - 任意（本番環境ではアラート送信先として必要）
- KILL_FLAG_CLEAR_ON_START  
  - 0（デフォルト）/ 1（起動時に kill.flag をクリア）
- MONITOR_POLL_INTERVAL  
  - 監視ループのポーリング間隔（秒）。デフォルト 60

注意:
- .env の自動読み込みは標準で有効です。テスト等で自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- 設定検証ツール（validate_config）は .env と config/*.yaml の存在や基本的な値検証を行います（PyYAML がない場合は YAML 内容検証をスキップします）。

---

## 使い方（コマンド）

- 環境設定ウィザード（.env を作成／更新）
  ```bash
  python -m kabusys.config_setup
  ```

- 設定を検証（起動前に実行）
  ```bash
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict  # 警告も FAIL 扱い
  ```

- 実行エンジン（発注処理）
  ```bash
  python -m kabusys.run_execution
  ```
  - KABUSYS_ENV=paper_trading なら MockBrokerClient を使用（本番 DB と分離）
  - PID ファイル、kill.flag による外部制御あり（`data/execution.pid` 等）

- 監視ループ（System monitoring）
  ```bash
  python -m kabusys.run_monitoring
  ```
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更可能
  - 停止フラグ: data/stop_requested.flag を配置するとループが終了します

開発／テスト:
- MockBrokerClient を直接利用してユニットテストや統合テストが可能です（create_broker_api(mock=True)）。
- ExecutionEngine の run_session を直接呼んでテスト用の挙動を検証できます。

停止・運用:
- 実行中に停止したい場合はプロセスに対応する stop フラグファイルを作る（プロジェクトでは stop_requested.flag / kill.flag の管理があります）。
- 本番運用時は KABUSYS_ENV=live に注意（設定の慎重な確認、LINE 通知設定等）。

---

## ディレクトリ構成（抜粋）

プロジェクトの主要ファイル・ディレクトリ（src/kabusys 以下）:

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数読み込み / Settings
  - config_setup.py          — .env 対話ウィザード CLI
  - validate_config.py       — 起動前設定検証 CLI
  - run_execution.py         — Execution エントリポイント
  - run_monitoring.py        — Monitoring エントリポイント
  - data/
    - calendar_management.py — マーケットカレンダー（DuckDB を利用）
    - news_collector.py      — RSS ニュース収集（defusedxml 使用）
    - jquants_client.py      — J-Quants API クライアント（参照）
  - execution/
    - broker_api.py          — Broker API の Protocol、モデル、ファクトリ
    - kabu_client.py         — KabuStation REST + WebSocket クライアント
    - mock_client.py         — MockBrokerClient（テスト用）
    - broker_factory.py      — Settings を見て適切なクライアントを返す
    - order_record.py        — 注文状態モデルと遷移ロジック
    - order_repository.py    — SQLite を使った永続化層
    - order_manager.py       — 発注フロー（作成・送信・同期・取消）
    - execution_engine.py    — ExecutionEngine（シグナル処理・push ドレイン）
    - reconciler.py          — 起動時のリコンシリエーション
    - risk_manager.py        — 3段階リスクガード実装
  - monitoring/
    - monitoring_db.py      — 監視用 DB 初期化 / ログ機能（参照）
  - utils/
    - logging_setup.py      — ロギングの初期化
    - process_priority.py   — プロセス優先度設定ユーティリティ

（上記はリポジトリ内の主要ファイルを抜粋しています）

---

## 運用上の注意 / ベストプラクティス

- 本番（live）モードでは外部通知（LINE）等を確実に設定してください。validate_config は live 時に注意喚起を行います。
- kill_flag（KILL_FLAG_CLEAR_ON_START）や PID ファイルの扱いは安全性に重要です。運用時はデフォルト（クリアしない）を推奨します。
- DB（DuckDB / SQLite）のバックアップやアクセス権限を適切に設定してください。
- KabuStationClient はローカルで kabuステーション® アプリが動作している想定です。ネットワーク構成や API パスは `KABU_API_BASE_URL` で調整できます。
- live 実行は慎重に。MockBrokerClient を使った入念な検証を推奨します。

---

## 開発者向けメモ

- OrderRecord は状態遷移の検証を内部で行い、不正遷移は例外を投げます（InvalidStateTransitionError）。
- OrderRepository は `idx_orders_unique_active_signal` により同一 signal_id の重複発注を DB レベルでも防いでいます。
- ExecutionEngine はシグナル時間帯（デフォルト 8:50–9:10）と push ドレイン（9:10–15:30）を想定したフローを持ちます。テスト時はメソッド単位で呼び出して検証してください。
- Reconciler は再起動時の OrderSent レコードを broker と照合し、ローカルと broker のポジション差分を検知します。

---

この README はコードベース（src/kabusys）から抽出した情報に基づいて作成しています。実際の運用・デプロイ前に必ずローカルで動作確認と十分なテストを行ってください。