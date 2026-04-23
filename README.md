# KabuSys

日本株自動売買システム（KabuSys）。  
発注・リスク制御・監視・カレンダー管理・ニュース収集などのコンポーネントを含む、小〜中規模の自動売買フレームワークです。本リポジトリは同期（blocking）実装を主軸にし、ペーパートレード用のモックブローカーを備えます。

注意: .env やシークレット情報は決して VCS にコミットしないでください。

---

## 概要

主な設計方針と特徴:

- Signal Queue ベースでシグナルを読み取り発注する ExecutionEngine を提供
- 発注は 3 段階のリスクガード（Gate1/2/3）で保護
- 再起動後の自動リコンシリエーション（Reconciler）を実装し、OrderSent 状態の回復を行う
- 本番/ペーパー取引の環境切替（KABUSYS_ENV）に対応。ペーパートレードでは MockBrokerClient を使用
- 監視プロセス（SystemMonitor）を別プロセスで稼働可能（run_monitoring.py）
- .env の対話的生成ウィザード（config_setup.py）と起動前検証ツール（validate_config.py）を提供
- DuckDB / SQLite を利用したデータ保存（DuckDB: 分析用、SQLite: 監視 / 注文永続化）

---

## 主な機能一覧

- 環境設定ウィザード（python -m kabusys.config_setup）
- 起動前設定検証（python -m kabusys.validate_config [--strict]）
- ExecutionEngine（発注・WebSocket ドレイン・PID 管理・kill switch）
- Broker クライアント実装
  - MockBrokerClient（ペーパートレード / テスト用）
  - KabuStationClient（実装済み、kabu station REST API 用）
- Order 管理
  - OrderRecord（状態マシン）
  - OrderRepository（SQLite 永続化）
  - OrderManager（作成・送信・同期・キャンセル）
- リスク管理（レート制限・サーキットブレーカー・ドローダウン）
- リコンシリエーション（OrderSent の突合せ・ポジション差分検出）
- データ関連
  - カレンダー管理（J-Quants 連携想定）
  - ニュース収集（RSS パーサ、SSRF/DoS 対策を考慮）
- 監視プロセス（run_monitoring.py） — SQLite を用いた監視ログ

---

## セットアップ手順

前提: Python 3.9+ を想定（typing, Path 等を利用）。システムにより微修正が必要な場合があります。

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo-root>
   ```

2. 仮想環境を作成・有効化（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

3. 必要パッケージをインストール  
   （requirements.txt が無い場合は下記の主要パッケージをインストール）
   ```
   pip install duckdb httpx websocket-client defusedxml PyYAML
   ```
   - PyYAML は validate_config の YAML パース検証に使用（未インストールでも動作するが YAML 内容検証はスキップされます）。
   - sqlite3 は標準ライブラリに含まれます。

4. data ディレクトリなどを作成（任意）
   ```
   mkdir -p data
   ```
   実行時に自動作成される場合もありますが、事前に作成しておくと権限・配置が明確になります。

5. .env を作成  
   - 対話式ウィザードを推奨（下記参照）  
   - 手動で作成する場合は .env.example を参考にしてください（リポジトリにあれば）。

環境変数の自動読み込み:
- プロジェクトルートにある `.env` と `.env.local` を自動で読み込みます（OS 環境変数が優先されます）。
- 自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト等で使用）。

必須環境変数:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

主な任意/設定変数:
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- DUCKDB_PATH, SQLITE_PATH: データベースパス（デフォルトは data/kabusys.duckdb / data/monitoring.db）
- LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID（本番での通知設定）
- KILL_FLAG_CLEAR_ON_START: 0 (推奨) / 1（起動時に kill.flag を自動クリア）

---

## 使い方

基本的なワークフロー例。

1. .env を対話式に作成
   ```
   python -m kabusys.config_setup
   ```
   - 指示に従って必要項目を入力します。
   - 保存後に `python -m kabusys.validate_config` で検証することを推奨します。

2. 起動前設定を検証
   ```
   python -m kabusys.validate_config
   python -m kabusys.validate_config --strict   # 警告も FAIL 扱い
   ```
   - 必須環境変数の未設定は ERROR（exit code 1）。
   - --strict を付けると WARNING も exit(1) で失敗扱いになります。

3. ExecutionEngine を起動（本番またはペーパー）
   - ペーパートレード / 開発:
     ```
     export KABUSYS_ENV=paper_trading
     python -m kabusys.run_execution
     ```
     ペーパートレードでは MockBrokerClient が使用され、orders は `data/paper_trading.db` に記録されます（設定で上書き可）。
   - 本番（注意: 実際に発注されます）:
     ```
     export KABUSYS_ENV=live
     python -m kabusys.run_execution
     ```

   実行時の挙動:
   - プロセス優先度を上げ、PID ファイルを作成します（デフォルト: data/execution.pid）。
   - 起動時に kill.flag が存在すると、KILL_FLAG_CLEAR_ON_START の設定に応じて起動を拒否または自動クリアします。
   - 停止は `data/stop_requested.flag` の作成でループを検出して終了します。kill.switch（全注文キャンセル）には `kill.flag` を使用。

4. 監視プロセスを起動
   ```
   python -m kabusys.run_monitoring
   ```
   - 監視は MONITOR_POLL_INTERVAL 環境変数（秒）で間隔を上書き可能（デフォルト 60s）。
   - monitoring は常に本番 sqlite_path を使用します（環境に依らず）。

5. ローカルテスト / 単体テスト
   - MockBrokerClient を使うことで kabu station を立ち上げずに発注・約定処理のテストが可能。
   - ExecutionEngine の一部メソッド（_process_signals, _drain_push_queue）を直接呼ぶことで単体テストが行えます。

停止 / 再起動の補助ファイル:
- data/stop_requested.flag — 監視・エンジンループを穏やかに停止するためのフラグ
- data/kill.flag — kill switch（強制停止 / 注文キャンセル）を管理するファイル
- PID ファイル（デフォルト: data/execution.pid） — 実行中の PID を記録

---

## ディレクトリ構成

主要なファイルと役割（src/kabusys 配下）:

- __init__.py
  - パッケージ定義・バージョン

- config.py
  - .env 読み込み / Settings クラス（環境変数アクセスのラッパ）

- config_setup.py
  - 対話式 .env 生成ウィザード

- validate_config.py
  - 起動前の設定検証 CLI（必須 env / YAML ファイル / 本番ガード等）

- run_execution.py
  - ExecutionEngine を起動するエントリポイントスクリプト

- run_monitoring.py
  - SystemMonitor を継続実行するスクリプト（監視ループ）

- execution/
  - broker_api.py — BrokerAPIProtocol、データモデル、例外、ファクトリ
  - kabu_client.py — kabu station REST API 実装（httpx/websocket）
  - mock_client.py — MockBrokerClient（テスト/ペーパー用）
  - broker_factory.py — Settings に基づくブローカー生成
  - order_record.py — 注文状態マシン
  - order_repository.py — SQLite 永続化レイヤ
  - order_manager.py — 外向き注文 API（作成・送信・同期・キャンセル）
  - execution_engine.py — Signal Queue ベースの発注エンジン
  - reconciler.py — 再起動時リコンシリエーション
  - risk_manager.py — Gate1/2/3 のリスク制御

- data/
  - （実行時に作成される / DB・フラグファイルを保存）
  - data/kabusys.duckdb — DuckDB（分析）
  - data/monitoring.db      — SQLite（監視 / orders）
  - data/paper_trading.db   — ペーパートレード専用 SQLite（KABUSYS_ENV=paper_trading）

- monitoring/
  - monitoring_db.py — 監視用 DB 初期化 / ログ書き込み
  - system_monitor.py — システムリソース監視ロジック

- data/
  - stop_requested.flag, kill.flag, *.pid 等をここに配置

- data/（その他）
  - config/*.yaml — 各種設定ファイル（system_config.yaml 等。validate_config が参照）

（上記はいくつかの抜粋です。実際のファイル構成はリポジトリを参照してください）

---

## 注意事項 / 運用メモ

- 本番（KABUSYS_ENV=live）では LINE の通知設定（LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID）を設定しておくと重要なアラートを受け取れます。validate_config は本番環境時に未設定を警告します。
- KILL_FLAG_CLEAR_ON_START=1 を本番で設定するのは危険です（kill.flag が誤ってクリアされ、残留していた停止状態が解除されます）。本番は 0 推奨。
- Order 永続化は SQLite で行われます。DB のバックアップや整合性監査を運用で検討してください。
- リコンシリエーションは OrderSent 状態の復旧を補助しますが、外部要因（証券会社側のデータ欠損等）は手動確認が必要な場合があります。
- YAML 設定ファイル（config/*.yaml）は PyYAML があると内容までパースして検証します。validate_config が見つからないファイルを警告します。疑わしい場合は scripts/generate_config.py（プロジェクトに存在する場合）で生成できます。

---

## 例: よく使うコマンド

- .env の対話作成:
  ```
  python -m kabusys.config_setup
  ```

- 起動前検証:
  ```
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- ExecutionEngine 起動:
  ```
  KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  ```

- Monitoring 起動（デフォルト 60秒間隔）:
  ```
  python -m kabusys.run_monitoring
  ```

---

必要に応じて README に追加したい内容（テスト手順、CI 設定、デプロイ手順、詳細な設定項目表など）があれば教えてください。README を拡張して含めます。