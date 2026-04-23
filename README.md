# KabuSys — 日本株自動売買システム

このリポジトリは日本株向けの自動売買システム「KabuSys」の実装を含みます。  
主要コンポーネントは発注エンジン（ExecutionEngine）、ブローカークライアント（kabu station / Mock）、リスクガード、監視（Monitoring）、データ処理（カレンダー・ニュース収集）などです。

注意: .env に機密情報（API トークン・パスワード等）を保存しないように、また .env を Git にコミットしないでください。

## 概要（Project overview）
- 本プロジェクトは、kabuステーション等のブローカー API と連携して株式の自動発注を行うためのシステム基盤を提供します。
- 発注フローは Signal Queue をプルして発注を行う設計（ExecutionEngine）。
- 本番（live） / ペーパートレード（paper_trading） / 開発（development）を環境変数で切り替え可能。
- 再起動時の自動復旧（Reconciler）や、3段階のリスクガード（Gate1/2/3）を備え安全性を高めています。
- テスト用にブローカーのモック（MockBrokerClient）を提供し、kabuステーション無しでのローカル検証が可能。

## 機能一覧（Features）
- 環境設定ウィザード（.env 作成）: python -m kabusys.config_setup
- 設定検証 CLI（.env と config/*.yaml の事前検査）: python -m kabusys.validate_config
- 発注エンジン起動スクリプト: python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading 時は MockBroker を使用し、本番 DB と分離して記録
- 監視プロセス起動スクリプト（SystemMonitor のポーリングループ）: python -m kabusys.run_monitoring
- ブローカー API 層
  - KabuStationClient（kabuステーション REST API 実装）
  - MockBrokerClient（テスト用）
  - create_broker_api ファクトリ
- 注文ライフサイクル管理
  - OrderRecord（状態遷移ロジック）
  - OrderRepository（SQLite 永続化）
  - OrderManager（外向き API、send/cancel/sync）
  - Reconciler（起動時の自動照合）
- リスク管理（RiskManager）
  - Gate1: シグナルレベル（余力・重複・ポジション上限）
  - Gate2: エグゼキューション（レート制限・サーキットブレーカー）
  - Gate3: ドローダウン監視（約定後）
- データ処理
  - マーケットカレンダー管理（DuckDB を利用）
  - ニュース収集（RSS → raw_news、SSRF/XML 脆弱性対策あり）
- 監視 DB（SQLite）および DuckDB を用いた分析データ管理
- PID / stop flag / kill flag によるプロセス制御と安全停止

## 前提（Prerequisites）
- Python 3.10 以上（型ヒントに PEP 604 の "|" を使用）
- 推奨パッケージ（代表例）
  - duckdb
  - httpx
  - websocket-client
  - PyYAML（YAML 検証用。無ければ検証をスキップ）
  - defusedxml
- SQLite は標準ライブラリで利用可能

例（最小インストール）:
```bash
python -m pip install "duckdb" "httpx" "websocket-client" "PyYAML" "defusedxml"
```
（requirements.txt がある場合は `pip install -r requirements.txt` を使用してください）

## セットアップ手順（Setup）
1. リポジトリをクローン
2. Python 仮想環境を作成して有効化
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
   ```
3. 依存パッケージをインストール
   ```bash
   pip install -r requirements.txt  # あれば
   # ない場合は個別にインストール
   pip install duckdb httpx websocket-client PyYAML defusedxml
   ```
4. .env を作成（ウィザード推奨）
   ```bash
   python -m kabusys.config_setup
   ```
   ウィザードでは J-Quants トークンや kabu API パスワード等を対話的に設定できます。完了後 `.env` が生成されます。
5. 設定検証（起動前に推奨）
   ```bash
   python -m kabusys.validate_config
   # 警告も失敗扱いにする場合
   python -m kabusys.validate_config --strict
   ```

注意:
- OS 環境変数は .env の自動ロード時に保護されます（既存の OS 環境変数は上書きされません）。
- 自動ロードを無効化する場合:
  ```bash
  export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  ```

## 環境変数（主なもの）
必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

任意 / 推奨:
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- DUCKDB_PATH: DuckDB ファイル（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 DB（デフォルト: data/paper_trading.db）
- LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL（デフォルト: INFO）
- KABU_API_BASE_URL: kabu station のベース URL（デフォルト: http://localhost:18080/kabusapi）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: 通知設定（本番で必須推奨）
- KILL_FLAG_CLEAR_ON_START: 1 なら起動時に kill.flag を自動クリア（開発用、デフォルト 0）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）

PAPER_FILL_MODE（paper_trading 用）:
- instant | partial | never | reject

## 使い方（Usage）
基本的なコマンド:

- 環境設定ウィザード（.env 作成・更新）
  ```bash
  python -m kabusys.config_setup
  ```

- 設定検証（起動前確認）
  ```bash
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict  # 警告を FAIL 扱い
  ```

- 発注エンジン起動
  ```bash
  python -m kabusys.run_execution
  ```
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を用いて発注をシミュレートします。
  - 起動時に data/stop_requested.flag の存在を確認し、あれば起動を中止します。
  - PID ファイルはデフォルトで data/execution.pid に保存（設定で変更可）。

- 監視プロセス起動
  ```bash
  python -m kabusys.run_monitoring
  ```
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を調整できます（秒、デフォルト 60）。

開発 / テストのポイント:
- paper_trading で動かせば実ブローカーへ発注しないため安心してテストできます。
- MockBrokerClient には fill_mode を指定でき、即時約定 / 部分約定 / 未約定 / 拒否 の動作を切り替えられます。
- Reconciler により、OrderSent 状態の不確定注文をブローカと突合して起動復旧が可能です。

安全関連:
- kill.flag（settings.kill_flag_path）や stop_requested.flag を用いて、外部から安全にプロセスを停止できます。
- サーキットブレーカーやドローダウン監視により、大きな損失リスクに対する自動停止が組み込まれています。

## ディレクトリ構成（Directory structure）
主要なファイル/モジュール構成（src/kabusys）:

- src/kabusys/
  - __init__.py
  - config.py                    — 環境変数 / Settings
  - config_setup.py              — .env ウィザード（対話型）
  - validate_config.py           — 起動前設定検証 CLI
  - run_execution.py             — ExecutionEngine 起動スクリプト
  - run_monitoring.py            — Monitoring 起動スクリプト
  - execution/                   — 発注関連コンポーネント
    - broker_api.py              — ブローカー API の Protocol / データモデル / ファクトリ
    - kabu_client.py             — kabu station REST 実装
    - mock_client.py             — テスト用モック実装
    - broker_factory.py          — Settings に基づくクライアント生成
    - execution_engine.py        — ExecutionEngine（シグナル処理＋push ドレイン）
    - order_record.py            — 注文状態遷移のドメインモデル
    - order_repository.py        — SQLite 永続化層（orders テーブル）
    - order_manager.py           — 発注フロー（create/send/sync/cancel）
    - reconciler.py              — 起動時リコンシリエーション
    - risk_manager.py            — Gate1/2/3 リスクガード
  - data/                        — データ関連
    - calendar_management.py     — マーケットカレンダー管理（DuckDB）
    - news_collector.py          — RSS ニュース収集（defusedxml, SSRF 対策等）
    - jquants_client.py          — （参照される想定の J-Quants クライアント）
  - monitoring/                  — 監視関連（DB 初期化や SystemMonitor 実装）
    - monitoring_db.py
    - system_monitor.py
  - utils/
    - logging_setup.py
    - process_priority.py
  - config/                      — YAML 設定ファイル群（system_config.yaml 等。生成スクリプトあり）
  - data/                        — 実行時データ格納（DuckDB/SQLite/pid/flag 等）

（上記のうち一部ファイルはリスト内の説明に準拠します。実際のリポジトリに存在しないスクリプトは README 上で参照されている場合があります。）

例: config/*.yaml（期待されるファイル）
- config/system_config.yaml
- config/data_config.yaml
- config/strategy_config.yaml
- config/risk_config.yaml
- config/execution_config.yaml
- config/monitoring_config.yaml

validate_config はこれらの存在と YAML パースの検証を行います（PyYAML がインストールされていない場合はパース検証をスキップして警告出力）。

## 開発・拡張メモ
- Broker クライアントは Protocol に基づいて実装されるため、新しいブローカーを追加する場合は BrokerAPIProtocol を実装し、create_broker_api を拡張してください。
- ExecutionEngine は push 通知を WebSocket 経由で受け取り _push_queue に入れて処理します。non-blocking な設計で、テストでは _process_signals / _drain_push_queue を直接呼ぶことが可能です。
- DuckDB は分析用ストアとして使用され、signals / portfolio_targets / market_calendar などを含みます。calendar_update_job で J-Quants API からカレンダーを更新します。
- セキュリティ: news_collector では defusedxml、SSRF 対策、受信バイト制限を導入しています。

## トラブルシューティング
- 設定検証でエラーが出る場合は .env（および OS 環境変数）を確認してください。必須変数が未設定の場合は起動時に例外を送出します。
- run_execution の起動前に data/stop_requested.flag が存在すると起動を中止します。開発時に停止フラグを削除してください。
- KABUSYS_ENV=live を設定すると本番モードになります。LINE 通知や監視設定など、本番向けの追加チェックが行われます。設定不備があると警告またはエラーになります。

---

必要ならば README の英語版、詳細な設定例（.env.example）、system_config.yaml のテンプレート、運用手順（デプロイ / サービス化 systemd 例）なども作成できます。どの追加情報が欲しいか教えてください。