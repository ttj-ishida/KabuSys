# KabuSys

日本株自動売買システムのコアモジュール群。発注エンジン、リスクガード、監視、データ処理（マーケットカレンダー・ニュース収集）などを含む軽量フレームワークです。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は kabu ステーションや外部 API（例: J-Quants）を用いた日本株自動売買のための内部ライブラリと起動スクリプト群を提供します。設計は以下を重視しています。

- 発注フローのクラッシュ耐性（2相永続化・リコンシリエーション）
- 3段階のリスクガード（Gate1/2/3）
- ペーパートレード向けのモックブローカーを標準装備
- 起動前チェック（.env / config/*.yaml の検証）と対話式設定ウィザード
- DuckDB（分析） / SQLite（監視・注文永続化）を利用したデータ管理

---

## 主な機能一覧

- .env 対話式ウィザード（config_setup.py）で初期設定を作成・更新
- 起動前設定検証 CLI（validate_config.py）で必須環境変数・YAML ファイルなどをチェック
- ExecutionEngine（run_execution.py）: シグナル駆動の発注エンジン
  - Signal の読み込み → Gate1/2 を通して発注 → push（WebSocket）をドレイン
  - Paper trading / development 環境では MockBrokerClient を使用
- Order 管理層
  - OrderRecord（状態遷移ロジック）
  - OrderRepository（SQLite 永続化）
  - OrderManager（発注フロー、send/cancel/sync）
  - Reconciler（再起動時の同期・ポジション照合）
- RiskManager：3 段階リスクガード（余力・重複・ポジション上限 / レート制限・CB / ドローダウン）
- ブローカークライアント群
  - KabuStationClient（kabu station REST / WebSocket 実装）
  - MockBrokerClient（テスト用）
  - create_broker_api() ファクトリ
- 監視プロセス（run_monitoring.py）：SystemMonitor のポーリングループ（SQLite / DuckDB 使用）
- データ処理モジュール（例）
  - calendar_management：JPX カレンダー管理、営業日判定、calendar_update_job
  - news_collector：RSS 取得・前処理・保存ロジック（SSRF 防御など）

---

## 前提条件

- Python 3.10 以上（PEP604 の型記法や型合成を使用）
- 推奨ライブラリ（用途に応じて必要）
  - duckdb
  - httpx
  - websocket-client
  - pyyaml（config/*.yaml のパース検証を行う場合）
  - defusedxml（RSS パースの安全化）
  - その他（用途により sqlite3 は標準ライブラリ、requests の代わりに httpx を使用）

requirements.txt がない場合は手動でインストールしてください。例:

Linux/macOS:
  python -m venv .venv
  source .venv/bin/activate
  pip install --upgrade pip
  pip install duckdb httpx websocket-client pyyaml defusedxml

Windows (PowerShell):
  python -m venv .venv
  .\.venv\Scripts\Activate.ps1
  pip install --upgrade pip
  pip install duckdb httpx websocket-client pyyaml defusedxml

---

## セットアップ手順

1. リポジトリをクローン
   git clone <repo-url>
   cd <repo-root>

2. 仮想環境の作成と依存パッケージのインストール（上記参照）

3. .env の作成（対話式ウィザード）
   python -m kabusys.config_setup
   - 対話に従って .env を生成します。
   - 生成後、python -m kabusys.validate_config で検証してください。

4. （任意）config/*.yaml のテンプレート生成スクリプトがある場合は実行して YAML を用意してください（README に付属スクリプトがある想定）。見つからない場合は config ディレクトリと YAML を手動で配置します。

---

## 環境変数（主なもの）

必須
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

任意 / 推奨
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- DUCKDB_PATH: 分析用 DuckDB パス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（デフォルト data/monitoring.db）
- LOG_LEVEL: DEBUG|INFO|WARNING|ERROR|CRITICAL
- KABU_API_BASE_URL: kabu station API ベース URL
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: 本番アラート用

注意:
- KABUSYS_ENV=live の場合、本番向けの追加チェック（LINE 設定、KILL_FLAG_CLEAR_ON_START 等）があります。
- KILL_FLAG_CLEAR_ON_START=1 は起動時に kill.flag を自動クリアするため本番では注意が必要です。

---

## 使い方（主要コマンド）

- 環境設定ウィザード（.env 作成・更新）
  python -m kabusys.config_setup
  オプション:
    --env-file <path> で .env の保存先を指定可能

- 設定検証 CLI（起動前チェック）
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict  # 警告も失敗扱いで exit(1)

  検証内容:
  - 必須環境変数の有無・プレースホルダ判定
  - KABUSYS_ENV / LOG_LEVEL の妥当性
  - DB パスの親ディレクトリ存在確認
  - config/*.yaml の存在・（PyYAML がインストールされていれば）パース検証
  - KABUSYS_ENV=live 時の追加ガード（LINE 設定、KILL_FLAG 等）

- 実行エンジン（Execution）
  python -m kabusys.run_execution

  説明:
  - settings に基づき SQLite / DuckDB に接続
  - KABUSYS_ENV が development/paper_trading の場合は MockBrokerClient を使用
  - paper_trading は専用の paper_sqlite_path（デフォルト data/paper_trading.db）を使用して本番 DB と分離
  - 停止フラグ: project_root/data/stop_requested.flag を作成すると優雅に停止
  - PID ファイル: data/execution.pid（設定で変更可能）

- 監視ループ（Monitoring）
  python -m kabusys.run_monitoring

  説明:
  - SystemMonitor のポーリングループを起動
  - 環境変数 MONITOR_POLL_INTERVAL で秒数を上書き可能（デフォルト 60）
  - Monitoring は環境にかかわらず本番 sqlite_path を使用

- 直接ライブラリ利用（アプリケーションから）
  from kabusys.config import settings
  token = settings.jquants_refresh_token

---

## 動作上の注意 / 運用メモ

- PID / stop フラグ
  - 実行時には PID ファイルが書き出されます（設定参照）
  - 停止は data/stop_requested.flag の作成で検知します
  - kill.flag を用いた緊急停止（kill_switch）が設計に組み込まれています

- 発注のクラッシュ耐性
  - OrderManager は「OrderSent」に遷移して DB にコミットしてからブローカー API 呼び出しを行う流れを採用（クラッシュで不確定状態が残る場合は Reconciler で復旧可能）
  - OrderSentPendingError（ブローカーが注文番号は返すが約定しない場合）を上手く扱う設計

- 本番環境（KABUSYS_ENV=live）は運用・テストが必要
  - 現状 Live broker client の未実装箇所があり、paper_trading/development を推奨しています

- YAML パース検証は PyYAML に依存。未インストールでも警告を出してスキップします。

---

## ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py
- config.py                  — 環境変数/設定管理（自動 .env ロード、Settings クラス）
- config_setup.py            — .env 対話式ウィザード
- validate_config.py         — 起動前設定検証 CLI
- run_execution.py           — ExecutionEngine 起動スクリプト（メイン）
- run_monitoring.py          — SystemMonitor 起動スクリプト
- data/
  - calendar_management.py   — マーケットカレンダー管理
  - news_collector.py        — RSS ニュース収集
  - jquants_client.py        — （別ファイル想定）J-Quants API クライアント
- execution/
  - __init__.py
  - broker_api.py            — Broker API データモデル / Protocol / ファクトリ
  - kabu_client.py           — kabu station 実装（HTTP + WebSocket）
  - mock_client.py           — MockBrokerClient（開発/テスト用）
  - broker_factory.py        — Settings に基づくクライアント生成
  - order_record.py          — Order の状態遷移ロジック
  - order_repository.py      — SQLite 永続化
  - order_manager.py         — 発注フロー管理
  - execution_engine.py      — 発注エンジン（シグナル処理 / push ドレイン）
  - reconciler.py            — 再起動時リコンシリエーション
  - risk_manager.py          — 3 段リスクガード
- monitoring/
  - monitoring_db.py         — 監視 DB 初期化 / ログ保存（想定）
  - system_monitor.py        — システム監視ロジック（想定）
- utils/
  - logging_setup.py         — ロギング初期化ユーティリティ（想定）
  - process_priority.py      — プロセス優先度設定ユーティリティ（想定）
- config/                    — YAML 設定ファイル群（system_config.yaml 等を想定）
- data/                      — 実行時 DB / フラグファイル / PID などを格納するローカルディレクトリ（デフォルト）

主要な config/*.yaml（参照）
- system_config.yaml
- data_config.yaml
- strategy_config.yaml
- risk_config.yaml
- execution_config.yaml
- monitoring_config.yaml

---

## トラブルシューティング

- validate_config で PyYAML がないと YAML の内容検証をスキップします。YAML 検証を行いたい場合は pyyaml をインストールしてください。
- KABUSYS_ENV の値が不正だと起動前検証でエラーになります。許容値: development, paper_trading, live
- DB パスの親ディレクトリが存在しない場合は警告が出ます（起動時に自動作成されることがあるため必ずしも致命的ではありません）。
- 実行中の停止は data/stop_requested.flag を作成することで行えます。

---

## 開発・貢献

- コードはモジュール単位で分割されており、MockBrokerClient によりローカルでの単体テストが可能です。
- リコンシリエーション・リスク周りは特にクリティカルな箇所のためユニットテストを充実させてください。
- Pull Request の際は機能追加に伴う設定ファイル・ドキュメントの更新をお願いします。

---

必要に応じて README の補足（例: 実行フロー図、DB スキーマ詳細、設定ファイルテンプレート）を作成できます。追加したい項目があれば教えてください。