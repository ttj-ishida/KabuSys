# KabuSys

日本株自動売買システムの軽量コアライブラリ（README 日本語版）

## 概要
KabuSys は日本株向けの自動売買エンジンのコア部分を実装した Python パッケージです。  
主に以下の要素を含み、実取引（kabuステーション）やペーパートレードの両方を想定した設計になっています。

- シグナルに基づく発注フロー（ExecutionEngine）
- ブローカー API 抽象（BrokerAPIProtocol）と Mock クライアント
- 注文状態管理（OrderRecord / OrderManager / OrderRepository）
- リスクガード（3段階の Gate）
- 起動時のリコンシリエーション（Reconciler）
- 監視ループ（SystemMonitor 起動スクリプト）
- 環境設定ウィザード / 設定検証ツール（.env 管理）

このリポジトリはライブラリ/実行スクリプト群を備え、ローカル開発やペーパートレードでの検証が容易になるよう設計されています。

## 主な機能
- 環境設定ウィザード（.env の対話式生成）: python -m kabusys.config_setup
- 設定検証 CLI（.env と config/*.yaml のチェック）: python -m kabusys.validate_config
- ExecutionEngine: シグナルの Pull 型発注と WebSocket push ドレインループ
- Order 管理:
  - OrderRecord（状態遷移と検証）
  - OrderRepository（SQLite ベースの永続化）
  - OrderManager（作成・送信・同期・キャンセル）
- Broker 抽象化:
  - BrokerAPIProtocol
  - MockBrokerClient（fill_mode: instant / partial / never / reject）
  - KabuStationClient（kabuステーション REST / WebSocket 実装）
- リスク管理（RiskManager）: Gate1/2/3（シグナル・実行・メトリクス）
- 起動時リコンシリエーション（Reconciler）
- Data モジュール:
  - マーケットカレンダー管理（calendar_management）
  - ニュース収集ユーティリティ（news_collector）
- 監視ループ起動スクリプト（run_monitoring.py）

## 要件
- Python 3.10+
- 推奨パッケージ（開発／実行時に必要となるもの）
  - duckdb
  - httpx
  - websocket-client
  - defusedxml
  - PyYAML（config/*.yaml をパースして検証する場合に必要）
- SQLite は標準ライブラリで利用

（プロジェクトに requirements.txt がない場合は上記をインストールしてください）

例:
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb httpx websocket-client defusedxml pyyaml
```

## セットアップ手順（ローカル開発／検証向け）
1. リポジトリをクローンしてチェックアウト
2. Python 仮想環境を用意して依存パッケージをインストール（上記参照）
3. .env を作成
   - 対話式で生成: python -m kabusys.config_setup
   - 手動作成: プロジェクトルートに `.env` を配置
   - 自動読み込みの挙動:
     - デフォルトで自動ロードされる（OS環境変数 > .env.local > .env の優先順）
     - 自動ロードを無効化する場合: 環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`
4. 設定検証:
   - python -m kabusys.validate_config
   - 警告もエラー扱いにする場合: python -m kabusys.validate_config --strict
5. Execution / Monitoring の起動（下記「使い方」参照）

## 環境変数（主要）
必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

オプション（主要なもの）:
- KABUSYS_ENV: execution モード。development / paper_trading / live（デフォルト: development）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite DB（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL（デフォルト: INFO）
- KABU_API_BASE_URL: kabu station API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: 本番アラート用（任意）
- KILL_FLAG_PATH: kill.flag のパス（デフォルト: data/kill.flag）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill flag を自動クリア（0/1、デフォルト: 0）
- MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、デフォルト: 60）

注意:
- config/*.yaml の検証には PyYAML が必要（なければ内容検証はスキップされ、警告になる）
- KABUSYS_ENV=live の場合は本番向けの追加警告やチェックが走ります（LINE 通知設定など）

## 使い方（主要コマンド）
- 環境設定ウィザード（.env 作成）
  ```
  python -m kabusys.config_setup
  ```
- 設定検証（起動前チェック）
  ```
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```
- 実行エンジン起動（デフォルトは settings に従う）
  ```
  python -m kabusys.run_execution
  ```
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient が使われ、ペーパートレード用 DB（PAPER_TRADING_SQLITE_PATH）に記録されます。
- 監視ループ起動
  ```
  python -m kabusys.run_monitoring
  ```
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（秒、デフォルト 60）。
  - Monitoring は KABUSYS_ENV に関わらず本番 sqlite_path を使用します（設定ファイルに注意）。

実運用の運用フロー（概略）:
1. .env を作成・確認
2. python -m kabusys.validate_config で設定確認
3. 必要な DB 初期化（run_execution / run_monitoring の起動時に各 init_* が呼ばれる）
4. python -m kabusys.run_execution をデーモン / systemd 等で起動
5. 監視は python -m kabusys.run_monitoring で別プロセスとして起動

## 開発者向けメモ（設計ポイント）
- Order の状態機械（OrderRecord / OrderState）により一貫した遷移が保証される。InvalidStateTransitionError が投げられる。
- OrderManager.send_order は 2相永続化を採用（OrderSent を先に DB に persist → ブローカー呼び出し → broker_order_id 保存 → OrderAccepted へ遷移）。クラッシュ耐性を考慮しています。
- Reconciler は起動時に OrderSent の不確定注文をブローカーと突合して自動復旧します。
- RiskManager は Gate1/2/3 の 3 層防御を提供（余力・重複・ポジション上限 / レート制限・サーキットブレーカー / ドローダウン監視）。
- Broker クライアントは Protocol で抽象化されており、MockBrokerClient により実装の検証が容易です。

MockBrokerClient の fill_mode:
- instant: 即時全量約定（テスト向け）
- partial: 半量約定（部分約定シナリオ）
- never: 注文番号は発行するが約定しない（OrderSentPendingError を発生）
- reject: 発注を拒否（OrderRejectedError）

## ディレクトリ構成（抜粋）
以下は主要ファイルのツリー（src/kabusys 以下を抜粋）です:

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / Settings
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py       — SystemMonitor ポーリングループ起動スクリプト
  - execution/
    - __init__.py
    - broker_api.py          — Broker API 抽象（Protocol / データモデル / ファクトリ）
    - broker_factory.py      — Settings に基づくブローカーファクトリ
    - kabu_client.py         — kabu station 実装（REST / WebSocket）
    - mock_client.py         — テスト用モック
    - order_record.py        — 注文状態モデルと遷移ロジック
    - order_repository.py    — SQLite 永続化
    - order_manager.py       — 上位 API（作成/送信/同期/キャンセル）
    - execution_engine.py    — 発注エンジン本体
    - reconciler.py          — 起動時リコンシリエーション
    - risk_manager.py        — 3段階リスクガード
  - data/
    - calendar_management.py — マーケットカレンダー管理（DuckDB）
    - news_collector.py      — RSS ニュース収集
    - jquants_client.py      — J-Quants API クライアント（想定）
  - monitoring/
    - monitoring_db.py      — 監視 DB 初期化・履歴ロギング（想定）
    - system_monitor.py     — システム状態ポーリング（想定）
  - utils/
    - logging_setup.py      — ロギング初期化ユーティリティ（想定）
    - process_priority.py   — プロセス優先度設定ユーティリティ（想定）

（上記の "想定" は抜粋に含まれない実装ファイルがあることを示します。リポジトリ全体を参照してください）

## 注意事項 / 運用上のヒント
- .env は機密情報（API トークン・パスワード等）を含むため、絶対に Git にコミットしないでください。
- KABUSYS_ENV=live の場合は本番動作になります。LINE 通知などの設定を忘れずに行ってください。
- kill.flag により外部から安全に稼働中のプロセスを停止できます。KILL_FLAG_CLEAR_ON_START を 1 にすると起動時に既存の kill.flag を自動クリアしますが、本番では 0 を推奨します。
- 実ブローカー接続（KabuStationClient）を使用する場合はローカルで kabuステーション® が起動している必要があります（API の挙動に依存）。

---

問題や拡張の提案があれば、リポジトリの該当箇所（execution / reconciler / risk_manager 等）を参照のうえご相談ください。README の追記やサンプル .env のテンプレート生成なども対応できます。