# KabuSys

日本株自動売買システム（KabuSys）のリポジトリ向け README。  
このドキュメントは本コードベースに含まれる主要な機能、セットアップ手順、使い方、ディレクトリ構成をまとめたものです。

---

## プロジェクト概要

KabuSys は日本株の自動売買を想定したモジュール群です。  
主な目的は次のとおりです。

- シグナルに基づく発注エンジン（ExecutionEngine）
- 発注の永続化と状態管理（SQLite）
- ブローカー API 抽象化（実運用向け KabuStationClient / テスト用 MockBrokerClient）
- リスク管理（3段階のガード：Gate1/2/3）
- 起動時リコンシリエーション（Reconciler）
- 監視プロセス（SystemMonitor 用の polling loop）
- 環境設定ウィザード（.env の生成）および設定検証 CLI

設計方針として、API クライアント層と永続化層 / ビジネスロジック層を明確に分離しています。テストやローカル実行向けに MockBrokerClient が用意され、本番（live）環境用クライアントは将来的な実装を想定しています。

---

## 主な機能一覧

- 環境設定ウィザード（python -m kabusys.config_setup）
  - 対話形式で `.env` を生成・更新
- 設定検証 CLI（python -m kabusys.validate_config）
  - .env と config/*.yaml の存在や基本的な値チェック
  - `--strict` オプションで警告も失敗扱い
- ExecutionEngine（run_execution.py）
  - シグナル処理ループ（発注）と WebSocket push のドレイン処理
  - OrderManager / OrderRepository による注文ライフサイクル管理
- Broker クライアント群
  - KabuStationClient（kabu station REST API 実装）
  - MockBrokerClient（テスト・開発用）
  - create_broker_api ファクトリで切替可能
- RiskManager（3段階のガード）
  - Gate1: シグナルレベル（余力・重複・ポジション上限）
  - Gate2: 実行レベル（レート制限・サーキットブレーカー）
  - Gate3: メトリクス（ドローダウン）
- Reconciler（起動時の自動復旧）
  - OrderSent の突合 → ポジション差分検出
- 監視ループ（run_monitoring.py）
  - SystemMonitor の定期実行（MONITOR_POLL_INTERVAL で調整可能）
- データパイプラインの一部
  - マーケットカレンダー管理（data/calendar_management.py）
  - ニュース収集（data/news_collector.py）

---

## 必須 / 推奨環境変数

必須（最低限設定が必要）
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

任意（設定すると便利）
- KABUSYS_ENV (development | paper_trading | live)
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (デフォルト: data/monitoring.db)
- LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL)
- KABU_API_BASE_URL
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID
- KILL_FLAG_CLEAR_ON_START (0/1)
- PAPER_FILL_MODE (paper_trading 用: instant | partial | never | reject)

注意:
- 自動で .env を読み込む仕組みがあり、プロジェクトルートの `.env` と `.env.local` がロードされます。自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。
- `KABUSYS_ENV=live` は本番モードですが、Broker のライブクライアント（KabuStationClient）や本番運用における設定は注意して扱ってください（コード内で live の実装制限や警告があります）。

---

## 必要な依存パッケージ（例）

最低限（使用する機能によって追加が必要）
- python >= 3.10（型注釈等を前提）
- duckdb
- httpx
- websocket-client
- defusedxml
- PyYAML（config/*.yaml のパース検証を行う場合）
- そのほか標準ライブラリ（sqlite3 等）

インストール例:
```
pip install duckdb httpx websocket-client defusedxml pyyaml
```

---

## セットアップ手順

1. リポジトリをクローンして作業ディレクトリをプロジェクトルートに移動します。

2. 必要なパッケージをインストールします（上記参照）。

3. 対話式ウィザードで .env を作成：
```
python -m kabusys.config_setup
```
- 既存の .env を読み取り、Enter で値を保持できます。
- 作成後に `.env` を保存すると README の案内の通り validate を実行することを推奨します。

4. 設定検証を実行：
```
python -m kabusys.validate_config
# 警告も失敗扱いにする場合:
python -m kabusys.validate_config --strict
```
- 必須環境変数や config/*.yaml のパース、KABUSYS_ENV の妥当性などをチェックします。
- PyYAML がインストールされていない場合、YAML 検証はスキップされ警告が出ます。

5. データディレクトリの準備（必要なら）：
- デフォルトの DB パス（data/ 以下）を使用する場合、親ディレクトリが存在しないと警告が出ます。必要に応じて手動でディレクトリを作成してください。
```
mkdir -p data
```

---

## 使い方（実行例）

- ExecutionEngine（発注実行）を起動：
```
python -m kabusys.run_execution
```
- Monitoring（監視）を起動（ポーリング間隔は MONITOR_POLL_INTERVAL で秒数を指定）：
```
MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
```
- 設定ウィザード：
```
python -m kabusys.config_setup
```
- 設定検証：
```
python -m kabusys.validate_config [--strict]
```

運用上の注意:
- 実行中の停止フラグは project_root/data/kill.flag（デフォルト）で検知されます。`KILL_FLAG_CLEAR_ON_START=1` を設定すると起動時に既存の kill.flag を自動でクリアして起動します（本番では推奨されません）。
- PID ファイルはデフォルトで data/execution.pid 等に書き込まれます（config で変更可能）。

---

## よく使う設定項目（抜粋）

- KABUSYS_ENV: 実行モード
  - development：ローカル開発・テスト（デフォルト）
  - paper_trading：ペーパートレード（MockBroker を使用）
  - live：本番（実際に発注） — live 用ブローカークライアントは注意
- PAPER_FILL_MODE（paper_trading 時の挙動）
  - instant / partial / never / reject
- DUCKDB_PATH / SQLITE_PATH：データベースファイルパス
- LOG_LEVEL：ログ出力レベル
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID：LINE 通知設定（本番で要）

---

## ディレクトリ構成（主要ファイルと役割）

- src/kabusys/
  - __init__.py
    - パッケージ定義（__version__ 等）
  - config.py
    - 環境変数 / .env 読み込みロジック、Settings クラス
    - 自動 .env 読込（.env / .env.local）と保護機能
  - config_setup.py
    - 対話式ウィザードで .env を生成 / 更新
  - validate_config.py
    - 起動前の設定検証 CLI
  - run_execution.py
    - ExecutionEngine 起動スクリプト（メイン実行フロー）
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト
  - execution/
    - broker_api.py
      - BrokerAPIProtocol、データモデル、例外、ファクトリ
    - broker_factory.py
      - Settings に基づきブローカークライアントを生成
    - kabu_client.py
      - kabu station REST API 実装（HTTP & WebSocket）
    - mock_client.py
      - MockBrokerClient（テスト用）
    - order_record.py
      - 注文状態と状態遷移の純粋ロジック（DB 非依存）
    - order_repository.py
      - SQLite を使った永続化層（orders テーブル定義と CRUD）
    - order_manager.py
      - 外向き API（シグナルを受け発注／同期／キャンセル等）
    - execution_engine.py
      - ExecutionEngine（セッション管理、シグナル処理、push ドレイン）
    - reconciler.py
      - 起動時の OrderSent 突合 / ポジション差分検出
    - risk_manager.py
      - 3段階のリスクガード実装
  - data/
    - calendar_management.py
      - カレンダー（営業日）管理、next/prev_trading_day など
    - news_collector.py
      - RSS ニュース収集と前処理
    - jquants_client (参照されるが省略されている可能性あり)
  - monitoring/
    - monitoring_db.py (参照あり。監視 DB 初期化・ログなど)
    - system_monitor.py (参照あり。監視ロジック)
  - utils/
    - logging_setup.py (ロギング初期化ユーティリティ)
    - process_priority.py (プロセス優先度設定)
  - scripts/
    - generate_config.py (README 内で言及されるがリポジトリに存在する場合あり)
- data/
  - デフォルトの DB/フラグ/PID ファイルが置かれる想定ディレクトリ（例: data/monitoring.db, data/kabusys.duckdb, data/kill.flag）

（※ 上記はコード内参照から抽出した主要ファイル・モジュールの一覧です。リポジトリの実際のファイル構成に合わせて補完してください）

---

## 運用上の注意事項

- 本番環境（KABUSYS_ENV=live）は慎重に扱ってください。validate_config は live 設定時に追加の警告を出します。
- 起動前に必ず `python -m kabusys.validate_config` で設定を確認することを推奨します（`--strict` で警告も失敗扱いにできます）。
- .env は絶対にバージョン管理（Git）にコミットしないでください（config_setup.py の出力にも注記あり）。
- Kill Switch（kill.flag）や PID ファイルの管理で予期せぬ起動停止や再起動の振る舞いが変わるため運用手順を明確にしてください。
- 本コードでは MockBrokerClient を用いた試験が可能です。paper_trading / development 環境では自動で Mock が使用されます。

---

## 問い合わせ / 貢献

コードの拡張やバグ修正、ドキュメント改善はプルリクエスト歓迎です。Issue を立てる際は再現手順やログ、.env のどの項目が影響するか等をできるだけ明確に記載してください。

---

この README はコードベース中の docstrings とモジュール間の参照に基づいて作成しています。実際の運用や追加スクリプト（例: scripts/generate_config.py）が存在する場合はそちらも併せて確認してください。