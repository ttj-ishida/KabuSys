# KabuSys

日本株自動売買システム（KabuSys）のソースコード README。  
この README はリポジトリ内の CLI、設定管理、Execution / Monitoring の起動スクリプトや主要モジュールの使い方・セットアップ手順をまとめたものです。

> 注意: このリポジトリは実際の発注を行うロジックを含みます。特に `KABUSYS_ENV=live` を使用する場合は設定・権限に十分注意してください。

---

## プロジェクト概要

KabuSys は日本株の自動売買を目的としたシステムで、主に以下の責務を持ちます。

- シグナルに基づく発注フロー（ExecutionEngine）
- 発注の永続化・状態管理（SQLite）
- ブローカークライアント（kabuステーション向けの実実装およびテスト用モック）
- リスク管理（Gate1〜Gate3：余力・重複・ポジション上限、レート制限・サーキットブレーカー、ドローダウン監視）
- 起動時のリコンシリエーション（Reconciler）
- システム監視ループ（SystemMonitor）
- データ（DuckDB）を用いたカレンダー管理やニュース収集（DataPlatform 機能）
- .env ベースの設定ウィザードおよび設定検証ツール

設計方針として、DB操作は永続化層に集約し、ビジネスロジックは純粋なモデル（OrderRecord 等）で表現されています。テストおよび開発環境向けに MockBrokerClient も提供されます。

---

## 主な機能一覧

- .env 対話的ウィザード（python -m kabusys.config_setup）
- 起動前設定検証 CLI（python -m kabusys.validate_config）
- ExecutionEngine によるシグナル読み取り → 発注フロー（run_execution）
- SystemMonitor のポーリングループ（run_monitoring）
- ブローカークライアント抽象化（BrokerAPIProtocol）と Mock 実装
- 発注状態の状態遷移管理（OrderRecord / OrderState）
- 発注永続化（SQLite を用いた OrderRepository）
- リスク管理（Rate Limit / Circuit Breaker / Drawdown）
- リコンシリエーションによる再起動後の復旧処理
- DuckDB を用いたデータ解析・カレンダー管理・ニュース収集

---

## 必要な前提ソフトウェア / Python パッケージ

推奨 Python バージョン: 3.9 以上（typing ヒント等を使用）

主な外部依存（必要に応じてインストール）:
- duckdb
- httpx
- websocket-client
- defusedxml
- PyYAML（YAML 検証を行いたい場合）
- （sqlite3 は標準ライブラリ）
- そのほかロギング関連やユーティリティが必要な場合があります

インストール例（仮想環境推奨）:
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb httpx websocket-client defusedxml PyYAML
```

※ requirements.txt がある場合はそちらを利用してください。

---

## セットアップ手順

1. リポジトリをクローンして作業ディレクトリへ移動：
   ```
   git clone <repo-url>
   cd <repo-root>
   ```

2. 仮想環境を作成して依存をインストール（上記参照）。

3. .env の作成
   - 対話式ウィザードを使う（推奨）：
     ```
     python -m kabusys.config_setup
     ```
     ウィザードは .env（デフォルト）をインタラクティブに作成・更新します。
   - あるいは .env を手動で作成します（例は下記「重要な環境変数」を参照）。

4. 設定検証（起動前チェック）:
   ```
   python -m kabusys.validate_config
   ```
   - --strict を付けると警告も FAIL 扱いで exit(1) になります：
     ```
     python -m kabusys.validate_config --strict
     ```

5. 実行/監視プロセス起動:
   - Execution（実行エンジン）:
     ```
     python -m kabusys.run_execution
     ```
     - KABUSYS_ENV が `paper_trading` の場合は MockBrokerClient が使用され、ペーパートレード専用の DB（デフォルト: data/paper_trading.db）に分離されます。
   - Monitoring（監視）:
     ```
     python -m kabusys.run_monitoring
     ```

---

## 重要な環境変数（主なもの）

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants API 用リフレッシュトークン（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）

任意 / 推奨（デフォルトを持つもの含む）:
- KABUSYS_ENV — 実行環境（development / paper_trading / live）デフォルト: development
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite（監視 DB）パス（デフォルト: data/monitoring.db）
- LOG_LEVEL — ログレベル（DEBUG / INFO / WARNING / ERROR / CRITICAL）デフォルト: INFO
- KABU_API_BASE_URL — kabuステーション API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- LINE_CHANNEL_ACCESS_TOKEN — LINE 通知トークン（本番でのアラートに必要）
- LINE_USER_ID — LINE の受信ユーザー ID（本番でのアラートに必要）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動でクリアするか（0/1、デフォルト 0）
- PAPER_FILL_MODE — paper_trading 用モックの fill モード（instant / partial / never / reject）
- PAPER_TRADING_SQLITE_PATH — paper_trading 用 SQLite（デフォルト: data/paper_trading.db）
- PID_FILE_PATH, KILL_FLAG_PATH, CPU_THRESHOLD_PCT 等（監視関連）

.env 自動ロードのルール:
- 優先度: OS 環境変数 > .env.local > .env
- 自動ロードはデフォルトで有効。自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

セキュリティ:
- .env は絶対に Git 等にコミットしないでください（config_setup の出力ヘッダにも注意喚起があります）。

---

## 使い方（主要 CLI）

- 環境設定ウィザード（.env を対話的に作成/更新）
  ```
  python -m kabusys.config_setup
  ```

- 設定検証（起動前チェック）
  ```
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- 実行エンジン起動（本番・ペーパートレード両対応）
  ```
  python -m kabusys.run_execution
  ```
  - 停止方法: プロセスを正常終了するか、リポジトリ内 `data/stop_requested.flag` を作成するとスレッドループが検知して終了します。
  - PID は data/execution.pid（デフォルト）に書き出されます。
  - 起動前に `python -m kabusys.validate_config` で設定確認することを推奨します。

- 監視ループ起動（SystemMonitor のポーリング）
  ```
  python -m kabusys.run_monitoring
  ```
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL（秒）で上書き可能（デフォルト: 60）
  - 監視は実行環境に関わらず本番用 sqlite_path を使用します（設定を確認してください）。

---

## 実装上の注意点・運用メモ

- Paper Trading: KABUSYS_ENV=paper_trading の場合は MockBrokerClient を用いて本番 DB と分離して動作します（デフォルト paper_trading の SQLite は data/paper_trading.db）。
- Reconciliation: 起動時に OrderSent の状態などを照合して自動修復を試みます（Reconciler）。
- Kill Switch:
  - `kill.flag`（デフォルト: data/kill.flag）を置くと ExecutionEngine 内で検出され kill_switch を発動します。kill_flag_clear_on_start=1 を設定していると起動時に自動クリアされます（本番では 0 を推奨）。
- ログ: 設定 LOG_LEVEL で制御されます。ログ設定は utils.logging_setup で行われます。
- WebSocket Push: kabuステーションの push 通知は WebSocket で受け、ExecutionEngine の push drain で処理されます。MockBrokerClient は stream_push を持ちません（その場合 WebSocket スレッドはスキップされます）。
- DB 初期化: orders テーブル等は init_orders_db / init_monitoring_db 等の関数で冪等に作成されます。起動先の SQLite 接続を用意しておいてください。

---

## ディレクトリ構成（主要ファイルと説明）

（抜粋: src/kabusys 以下）

- __init__.py
  - パッケージ定義（__version__ 等）

- config.py
  - 環境変数の自動読み込み（.env / .env.local）と Settings クラス
  - Settings によりアプリ全体が環境値へ簡単にアクセス可能

- config_setup.py
  - .env を対話形式で作成・更新するウィザード実装

- validate_config.py
  - 起動前に .env と config/*.yaml（存在する場合）の検証を行う CLI

- run_execution.py
  - ExecutionEngine の起動スクリプト（プロセス優先度設定、DB 接続、スレッド管理、停止フラグ検出など）

- run_monitoring.py
  - SystemMonitor のポーリング開始スクリプト（監視 DB の初期化、終了フラグ検出など）

- execution/
  - broker_api.py — Broker 用 Protocol / データモデル / 例外 / ファクトリ
  - kabu_client.py — kabuステーション向け実 HTTP クライアント（httpx）
  - mock_client.py — テスト用の MockBrokerClient
  - broker_factory.py — Settings に基づいて適切なブローカークライアントを生成
  - order_record.py — 注文状態モデルと遷移ロジック（純粋ビジネスロジック）
  - order_repository.py — SQLite を使った永続化層（orders テーブルの作成・CRUD）
  - order_manager.py — 外向け API（OrderRecord と Repository を組み合わせ、broker 呼び出しを管理）
  - execution_engine.py — シグナル読み取り、発注ループ、push ドレイン、kill switch の実装
  - reconciler.py — 再起動時の照合・復旧処理
  - risk_manager.py — Gate1/Gate2/Gate3 のリスクチェック

- data/
  - calendar_management.py — マーケットカレンダーの管理（DuckDB ベース。J-Quants 連携想定）
  - news_collector.py — RSS 収集・前処理・DB 保存ロジック（セキュリティ対策込み）

- monitoring/
  - monitoring_db.py — 監視 DB 初期化 / ログ保存（run_monitoring/run_execution から利用）
  - system_monitor.py — システム監視コンポーネント（CPU/メモリ等閾値チェック）

- utils/
  - logging_setup.py — ロギング設定ユーティリティ
  - process_priority.py — プロセス優先度設定ユーティリティ

（注）上記のうち一部ファイルはこの README に抜粋されているコード群に含まれますが、残りのユーティリティや monitoring モジュールは別ファイルとして存在します。実際のリポジトリでは完全なファイル群を確認してください。

---

## 開発・テストのヒント

- テストでは MockBrokerClient を使うと kabuステーションが不要で発注フローを検証できます。Settings の env を `paper_trading` にすると自動的に Mock が使用されます。
- OrderRecord の遷移ルールは厳密に定義されています。InvalidStateTransitionError が発生した場合は遷移設計を確認してください。
- ExecutionEngine の run_session は外部から stop() を呼ぶか、data/stop_requested.flag を配置することで安全に停止できます。
- .env の自動ロードを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定し、テスト環境でカスタム設定を注入してください。

---

## ライセンス / 責任

- 本プロジェクトにより行われる取引の結果につきましては利用者の責任です。特に live 環境での実行は十分な検証の後に行ってください。
- .env に含まれる秘密情報は厳重に管理し、リポジトリ等へ決してコミットしないでください。

---

README に含めるべき追加情報（必要であれば）:
- requirements.txt（依存の固定）
- サービスユニット（systemd）例
- 運用チェックリスト（デプロイ前の確認項目）
- テストケースや Mock の使い方例

必要なら上記の追加セクションを作成します。何か付け加える／補足してほしい点はありますか？