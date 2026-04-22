# KabuSys

日本株向け自動売買システムの一部（設定管理、実行/監視起動スクリプト、発注レイヤ、データユーティリティ等）の実装です。本リポジトリは実装の抜粋を含み、ローカルでの開発・ペーパートレード運用を想定しています。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は以下の主要機能を持つモジュール群で構成されています。

- 環境変数 / .env ファイルの自動読み込みと対話式ウィザードでの .env 作成（config_setup）
- 起動前設定検証 CLI（validate_config）
- 実際の注文処理を行う ExecutionEngine（run_execution）
- システム状態監視ループ（run_monitoring）
- ブローカークライアント層（kabuステーション向け実装とモック実装）
- 注文状態管理（OrderRecord / OrderManager / OrderRepository）
- リスクガード（3 段階の RiskManager）
- 再起動時のリコンシリエーション（Reconciler）
- マーケットカレンダー管理やニュース収集などのデータユーティリティ

設計方針として、DB 操作とビジネスロジックを分離し、クラッシュ時の安全性（永続化戦略や 2 相永続化など）に配慮しています。

---

## 機能一覧

- 環境設定ウィザード
  - python -m kabusys.config_setup で対話式に .env を生成／更新
  - シークレット入力（トークン等）はマスク表示
- 設定検証 CLI
  - python -m kabusys.validate_config
  - 必須環境変数未設定や config/*.yaml の存在・パースなどをチェック
  - --strict で警告も失敗扱いにできる
- 実行エンジン（ExecutionEngine）
  - シグナルプル型で発注を行う（シグナル処理フェーズ + WebSocket ドレインフェーズ）
  - kill.flag による安全停止、PID ファイル管理
  - paper_trading モードでは MockBrokerClient を使用し本番 DB と分離
- 監視ループ（SystemMonitor）
  - 定期ポーリングでシステムメトリクスや監視イベントを監視・記録
  - MONITOR_POLL_INTERVAL で間隔調整可能
- ブローカー層
  - KabuStationClient（httpx + websocket-client を使用）
  - MockBrokerClient（テスト/ペーパートレード向け）
- リスク管理
  - Gate1: シグナルレベル（余力・重複・ポジション上限）
  - Gate2: エグゼキューションレベル（レート制限 / サーキットブレーカー）
  - Gate3: メトリクス（ドローダウン監視）
- データユーティリティ
  - calendar_management（営業日判定、next_trading_day 等）
  - news_collector（RSS 収集と前処理）

---

## 必要条件 / 依存

- Python 3.10+
  - ソース中で `X | None` などの構文を使っているため Python 3.10 以上を想定しています。
- 主な外部ライブラリ
  - duckdb
  - httpx
  - websocket-client
  - defusedxml
  - PyYAML（config/*.yaml のパース検証を行う場合に必要）
- 標準ライブラリ: sqlite3, logging, threading, json, datetime など

インストール例:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install duckdb httpx websocket-client defusedxml PyYAML
```

（プロジェクトに requirements.txt があればそれを使ってください）

---

## セットアップ手順

1. リポジトリをチェックアウトし、仮想環境を作成して依存をインストールする（上記参照）。

2. .env の作成
   - 対話式ウィザードを利用:
     ```
     python -m kabusys.config_setup
     ```
     ウィザードは既存の .env を読み取り、既存値を Enter で再利用できます。作成後は .env を絶対に Git にコミットしないでください（README にも明示されています）。

   - 自動読み込み:
     - 起動時、プロジェクトルート（.git または pyproject.toml のあるディレクトリ）から `.env` と `.env.local` が自動読み込みされます。
     - OS 環境変数が優先され、`.env.local` は `.env` を上書きします。
     - 自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

3. 必須環境変数（例）
   - JQUANTS_REFRESH_TOKEN（必須）
   - KABU_API_PASSWORD（必須）

   validate_config でチェックされる項目（抜粋）:
   - 必須: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD
   - 任意/設定候補: KABUSYS_ENV (development|paper_trading|live), DUCKDB_PATH, SQLITE_PATH, LOG_LEVEL, KABU_API_BASE_URL, LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID

4. DB ファイル
   - デフォルト:
     - DuckDB: data/kabusys.duckdb
     - SQLite (監視 DB): data/monitoring.db
     - Paper trading SQLite: data/paper_trading.db
   - 実行スクリプトが起動時に必要なテーブルを作成（init_monitoring_db / init_orders_db など）します。

---

## 使い方

### 設定検証

- 基本実行:
  ```
  python -m kabusys.validate_config
  ```

- 警告を失敗扱いにする（CI 等で使用）:
  ```
  python -m kabusys.validate_config --strict
  ```

出力は INFO / WARNING / ERROR が一覧表示され、最後に OK / FAIL を返します。PyYAML が未インストールだと YAML の内容検証はスキップされます。

### 環境ウィザード

- 対話式 .env 作成:
  ```
  python -m kabusys.config_setup
  ```
  入力を完了すると指定のパスに .env を保存します（デフォルト: プロジェクトルートの .env）。

### 実行エンジン起動（注文処理）

- 実行:
  ```
  python -m kabusys.run_execution
  ```

挙動のポイント:
- KABUSYS_ENV に応じてブローカークライアントが切り替わります。
  - development / paper_trading: MockBrokerClient（PAPER_FILL_MODE を参照）
  - live: 実運用向けクライアントは未実装（Factory は NotImplementedError を投げます）
- paper_trading は本番監視 DB と分離して `PAPER_TRADING_SQLITE_PATH`（デフォルト data/paper_trading.db）へ接続します。
- 起動時に PID ファイルを書き込み、`data/stop_requested.flag` または kill.flag により安全停止します。
- kill.flag の自動クリアは環境変数 `KILL_FLAG_CLEAR_ON_START=1` で許可できます（本番では 0 推奨）。

### 監視ループ起動

- 実行:
  ```
  python -m kabusys.run_monitoring
  ```

- ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL`（秒）で変更可能（デフォルト 60 秒）。

---

## 重要な環境変数（抜粋）

- 必須
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- 推奨 / 任意
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
  - DUCKDB_PATH: DuckDB ファイルのパス（デフォルト data/kabusys.duckdb）
  - SQLITE_PATH: 監視 DB（デフォルト data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite
  - LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト INFO）
  - KABU_API_BASE_URL: kabu station のベース URL（デフォルト http://localhost:18080/kabusapi）
  - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: 本番でのアラート用
  - KILL_FLAG_CLEAR_ON_START: 0/1（起動時に kill.flag を自動クリアするか）
  - MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒）

---

## 動作ノート / 運用上の注意

- .env は絶対にリポジトリにコミットしないでください（README 生成時にも注意喚起があります）。
- KABUSYS_ENV=live の場合は特に安全策（LINE 通知設定、kill flag 設定、DB バックアップなど）を確認してください。validate_config は live での危険な設定を警告します。
- Paper trading と本番 DB は分離されています。ペーパートレードでは mock 実装を使い、本番に影響が出ないよう設計されています。
- Reconciliation（再起動時の同期）機構を備えており、OrderSent の不確定状態から復旧を試みます。
- KabuStationClient は HTTP / WebSocket を使って kabu ステーションと通信します（kabu station アプリがローカルで起動していることが前提）。

---

## ディレクトリ構成（抜粋）

プロジェクトの主要ファイルとフォルダ（src/kabusys 以下）:

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数 / .env 自動読み込みロジック、Settings クラス
  - config_setup.py           — 対話式 .env ウィザード
  - validate_config.py        — 設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor 起動スクリプト
  - execution/                — 発注関連モジュール
    - broker_api.py           — BrokerAPI の Protocol / データモデル / ファクトリ
    - kabu_client.py          — KabuStationClient（httpx / websocket）
    - mock_client.py          — MockBrokerClient（テスト用）
    - broker_factory.py       — Settings に合わせてクライアント生成
    - order_record.py         — OrderRecord（状態遷移ロジック）
    - order_repository.py     — SQLite 永続化層（orders テーブル）
    - order_manager.py        — 発注 API（OrderManager）
    - execution_engine.py     — ExecutionEngine（シグナル処理＋push ドレイン）
    - reconciler.py           — 起動時リコンシリエーション
    - risk_manager.py         — リスクガード（Gate1/2/3）
    - ...（その他関連モジュール）
  - data/                     — データ関連ユーティリティ
    - calendar_management.py  — マーケットカレンダー管理
    - news_collector.py       — RSS ニュース収集と前処理
    - jquants_client.py       — J-Quants 用クライアント（参照）
  - monitoring/               — 監視周り（monitoring_db, system_monitor 等）
  - utils/                    — ロギング設定、プロセス優先度設定等ユーティリティ
  - config/                   — YAML 設定ファイル群（system_config.yaml 等、validate でチェック対象）
  - data/                     — デフォルト DB/フラグ保存先（data/kabusys.duckdb, data/monitoring.db 等）

（上記は抜粋です。実際のツリーはリポジトリルートを参照してください）

---

## トラブルシューティング

- validate_config が YAML の検証をスキップする
  - PyYAML がインストールされていない場合、YAML の内容検証はスキップされます。インストールしてください: `pip install PyYAML`
- KABUSYS_ENV の値エラー
  - 有効値は `development`, `paper_trading`, `live` です。誤った値は例外や validate のエラーを引き起こします。
- 実行中に kill.flag を検出すると安全に停止します
  - `data/kill.flag`（または Settings で指定したパス）を利用して外部から停止指示が可能です。
- WebSocket が接続できない / トークン 401
  - kabu station の設定（API パスワード、ベース URL）と kabu ステーションアプリの起動を確認してください。401 発生時はトークンの再取得を試みます。

---

## ライセンス / コントリビューション

（ここにライセンスや貢献方法を記載してください。サンプルでは記載されていません）

---

必要であれば README に CI の組み込み手順やデプロイ手順（systemd ユニット例、監視設定例）を追加できます。どの情報を追加したいか教えてください。