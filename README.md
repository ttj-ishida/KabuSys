# KabuSys

日本株自動売買システム（パーツ群）。このリポジトリは発注エンジン、監視ループ、環境設定ウィザード、設定検証ツールなどを含む軽量な自動売買フレームワークです。

## プロジェクト概要
- 発注フロー（ExecutionEngine）: シグナルに基づく発注、Order 状態管理、Reconciliation（再同期）を実装。
- ブローカー抽象化: 実運用用（kabuステーション）クライアントとテスト用モック（MockBrokerClient）を提供。
- リスク管理: Gate1〜3 による多段階リスクガード（余力、ポジション上限、レート制限、サーキットブレーカー、ドローダウン）。
- 監視（Monitoring）: プロセス監視ループと監視用 DB へのログ収集。
- 開発支援: .env 対話式生成ウィザード、起動前設定検証 CLI。

## 主な機能一覧
- 環境設定ウィザード（対話式）: `.env` を作成 / 更新する `python -m kabusys.config_setup`
- 設定検証 CLI: `.env` と `config/*.yaml` のチェック（PyYAML 利用時は YAML のパース検証）`python -m kabusys.validate_config [--strict]`
- ExecutionEngine:
  - シグナル読み込み（DuckDB）→ 発注 → push（WebSocket）処理のドレイン
  - kill_flag による安全停止、PID 管理、発注リコンシリエーション
- Mock ブローカ: paper_trading / development 向けのモッククライアント（fill_mode により挙動を切替）
- RiskManager: 発注前チェック（Gate1）、エグゼキューション制御（Gate2）、約定後ドローダウン監視（Gate3）
- Calendar / Data utilities: JPX 営業日の管理（DuckDB を使用）

## 必要条件（目安）
- Python 3.9+（コードの型注釈等から想定）
- 推奨ライブラリ（機能に応じて必要）:
  - duckdb
  - httpx
  - websocket-client
  - defusedxml
  - PyYAML（validate_config で YAML を検証する場合）
- （プロジェクトルートに requirements.txt がある場合）pip install -r requirements.txt を使用

※実際の運用では kabuステーション® アプリ（ローカルの REST/WS エンドポイント）が必要です。本リポジトリでは paper_trading / development 向けに MockBrokerClient を用意しています（live は未実装で NotImplementedError を投げます）。

## セットアップ手順（ローカル開発向け）
1. リポジトリをクローン
   - git clone ...
2. 仮想環境を作成して有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 依存パッケージをインストール
   - pip install -r requirements.txt
   - 必要に応じて: pip install duckdb httpx websocket-client defusedxml PyYAML
4. 環境変数の初期化（対話式ウィザード推奨）
   - python -m kabusys.config_setup
     - `.env` を作成・更新します。J-Quants トークンや kabu API パスワード等を入力します。
5. 設定検証（起動前チェック）
   - python -m kabusys.validate_config
   - 警告も失敗扱いにしたい場合:
     - python -m kabusys.validate_config --strict

## 使い方（実行コマンド）
- 環境設定ウィザード（.env 作成）
  - python -m kabusys.config_setup
- 設定検証（.env & config/*.yaml）
  - python -m kabusys.validate_config [--strict]
- ExecutionEngine 起動（本番 / ペーパートレードのセッション実行）
  - python -m kabusys.run_execution
  - 注意: `KABUSYS_ENV` が `paper_trading` または `development` のときは MockBrokerClient を使い動作します。`live` は未実装。
- Monitoring loop 起動（システム監視）
  - python -m kabusys.run_monitoring
  - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL` で秒数を指定（デフォルト 60 秒）。

## 主要な環境変数
必須:
- JQUANTS_REFRESH_TOKEN — J-Quants API 用リフレッシュトークン（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）

オプション:
- KABUSYS_ENV — 実行環境: development / paper_trading / live（既定: development）
- DUCKDB_PATH — DuckDB ファイルパス（既定: data/kabusys.duckdb）
- SQLITE_PATH — 監視 SQLite ファイルパス（既定: data/monitoring.db）
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- KABU_API_BASE_URL — kabu station base URL（既定: http://localhost:18080/kabusapi）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID — LINE 通知設定（本番アラート用）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（0/1、既定: 0）
- PAPER_FILL_MODE — paper_trading の fill 動作（instant / partial / never / reject）
- PID_FILE_PATH, KILL_FLAG_PATH, その他監視閾値（CPU/MEM/DISK）

.env の自動ロード
- Settings モジュールはプロジェクトルート（.git または pyproject.toml がある箇所）を検出して `.env`、`.env.local` を自動読み込みします。
- OS 環境変数が優先され、`.env.local` は上書き（override=True）されますが OS 環境と同名キーは保護されます。
- 自動ロードを無効化する場合: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

簡単な .env 例
JQUANTS_REFRESH_TOKEN=your_token_here
KABU_API_PASSWORD=your_password_here
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
LOG_LEVEL=INFO
PAPER_FILL_MODE=instant

（実運用では `.env` を絶対に Git にコミットしないでください）

## 実行時の挙動・注意点
- PID / stop フラグ:
  - 起動時に PID ファイルを書き、停止は `data/stop_requested.flag`（stop_requested.flag の検出でループを安全に終了）や `kill.flag` による動作停止が行われます。
  - `KILL_FLAG_CLEAR_ON_START=1` を設定すると起動時に既存の kill.flag を自動で削除して起動します（本番では非推奨）。
- Paper trading:
  - `KABUSYS_ENV=paper_trading` のときは MockBrokerClient を用い、SQLite は `PAPER_TRADING_SQLITE_PATH`（既定: data/paper_trading.db）に分離保存されます。
  - `PAPER_FILL_MODE` によってモックの約定動作を制御できます。
- Reconciliation:
  - 再起動時に OrderSent の不確定注文をブローカーと照合して状態を回復する Reconciler を実行します。
- 設定検証:
  - `python -m kabusys.validate_config` は必須環境変数の未設定、プレースホルダ値、KABUSYS_ENV の妥当性、LOG_LEVEL、DB パスの親ディレクトリ存在可否、config/*.yaml の存在と（PyYAML があれば）パース可否をチェックします。

## ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py — パッケージ定義、バージョン
  - config.py — 環境変数読み込み / Settings クラス、自動 .env ロードロジック
  - config_setup.py — .env 対話式ウィザード
  - validate_config.py — 起動前設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト（セッション制御 / PID / stop flag）
  - run_monitoring.py — システム監視ループ起動スクリプト
  - execution/
    - broker_api.py — BrokerAPI の Protocol、データモデル、例外、ファクトリ
    - kabu_client.py — kabuステーション REST/WS クライアント（httpx, websocket）
    - mock_client.py — MockBrokerClient（テスト用）
    - broker_factory.py — Settings を元に適切な Broker クライアントを返す
    - order_record.py — Order の状態遷移ロジック（状態機械）
    - order_repository.py — SQLite による永続化層（orders テーブル）
    - order_manager.py — 外向き API（create/send/sync/cancel）
    - execution_engine.py — ExecutionEngine（シグナル処理、push ドレイン、kill）
    - reconciler.py — 起動時リコンシリエーション
    - risk_manager.py — Gate1〜3 を実装するリスクガード
  - monitoring/ (監視関連)
    - monitoring_db.py — 監視用 DB 初期化・ログ関係（参照）
    - system_monitor.py — システム監視ロジック（参照）
  - data/
    - calendar_management.py — マーケットカレンダー管理（DuckDB）
    - news_collector.py — RSS ニュース収集（防御的 XML パース等）
  - utils/
    - logging_setup.py — ロギング初期化（参照）
    - process_priority.py — プロセス優先度設定（参照）

（注）config/ 以下の YAML ファイル:
- config/system_config.yaml
- config/data_config.yaml
- config/strategy_config.yaml
- config/risk_config.yaml
- config/execution_config.yaml
- config/monitoring_config.yaml
validate_config はこれらの存在を確認し、PyYAML がある場合はパース検証を行います。存在しない場合は警告を出します。`python scripts/generate_config.py`（存在するなら）で生成できる旨のメッセージが表示されます。

## トラブルシューティング / よくある注意
- PyYAML が未インストールだと YAML の内容検証をスキップします（validate_config は警告を出します）。
- `KABUSYS_ENV=live` を設定した場合、実際のブローカークライアントが未実装だと起動時に警告または NotImplementedError になります。開発・テストは `development` / `paper_trading` を使用してください。
- stop / kill フラグや PID ファイルの取り扱いに注意してください。特に本番で kill_flag を誤って残すと起動拒否されます（KILL_FLAG_CLEAR_ON_START により挙動を変更可能）。

---

その他の詳細は各モジュールのドキュメント文字列（docstring）を参照してください。必要であれば README を拡張して CI/デプロイ手順やテストの説明も追加します。