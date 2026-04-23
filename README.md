KabuSys — 日本株自動売買システム（README）
====================================

概要
----
KabuSys は日本株向けの自動売買システムのコアライブラリです。  
設定（.env / config/*.yaml）管理、発注エンジン（ExecutionEngine）、注文状態管理、リスク管理、ブローカークライアント（kabu station 実装／モック）、監視ループ、マーケットカレンダーやニュース収集などの機能を提供します。  
設計は「DB とビジネスロジックの分離」「再起動時のリコンサイル」「本番（live）／ペーパー（paper_trading）／開発（development）環境の分離」を重視しています。

主な機能
---------
- 環境設定の自動ロード／ウィザード（.env の生成・更新）
- 起動前設定検証ツール（環境変数・config/*.yaml の簡易チェック）
- ExecutionEngine：シグナルプル型発注ループ + WebSocket プッシュ処理
- 注文状態管理（OrderRecord、状態遷移の検証、DB 永続化）
- ブローカークライアント層（KabuStationClient 実装、MockBrokerClient）
- リスク管理（Gate1〜3：余力・重複・ポジション上限、レート制限、ドローダウン）
- 起動時リコンシリエーション（Reconciler）と不確定注文の回復処理
- 監視ループ（SystemMonitor を定期実行、SQLite に記録）
- データ系ユーティリティ（マーケットカレンダー管理、ニュース収集）
- テスト用モック（MockBrokerClient）によるオフライン動作可能

セットアップ手順
----------------
前提
- Python 3.10 以降（型記法で | を使用）
- SQLite（標準ライブラリ）、DuckDB ライブラリ

推奨手順（仮想環境）
1. 仮想環境作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   - 必須：duckdb, httpx, websocket-client, defusedxml
   - 任意（YAML 検証）：PyYAML
   例:
     pip install duckdb httpx websocket-client defusedxml
     pip install PyYAML   # YAML 検証を行いたい場合

   （プロジェクトに requirements.txt があればそれを使用してください）
   - pip install -r requirements.txt

3. プロジェクトルートで .env を準備
   - 対話式ウィザードを使う:
     python -m kabusys.config_setup
   - あるいは手動で .env を作成（.env.example を参考にしてください）

環境変数（主なもの）
- 必須:
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- 任意 / 推奨:
  - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
  - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH（監視DB、デフォルト: data/monitoring.db）
  - LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL）
  - KABU_API_BASE_URL（kabu station のベース URL）
  - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（本番アラート用）

- テスト用フラグ:
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動 .env ロードを無効化

使い方（主要コマンド）
---------------------
1. 環境設定ウィザード（.env 作成）
   - python -m kabusys.config_setup
   ウィザードは既存の .env を読み込み、対話的に入力して保存します。

2. 設定検証（起動前チェック）
   - python -m kabusys.validate_config
   - 厳密モード（警告も失敗扱い）:
     python -m kabusys.validate_config --strict
   .env と config/*.yaml の存在や基本的な値の妥当性をチェックします。
   PyYAML が無い場合は YAML パース検証をスキップして警告を出します。

3. 実行エンジン起動（発注）
   - python -m kabusys.run_execution
   KABUSYS_ENV に応じて MockBrokerClient（paper_trading / development）または実装済みクライアントを使用します。paper_trading は paper_trading 用 SQLite（PAPER_TRADING_SQLITE_PATH）にデータを分離します。起動時にデータディレクトリの kill.flag を検査します。

4. 監視ループ起動（SystemMonitor）
   - python -m kabusys.run_monitoring
   MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書き可能。監視は本番の sqlite_path を使用します（環境に関わらず）。

注意点 / 運用メモ
- PID やフラグファイル:
  - PID ファイルや kill.flag、stop_requested.flag 等は data/ 下に作成されます。PID は起動時に書き出され、終了時に削除されます。
- 本番環境（KABUSYS_ENV=live）では LINE 通知の設定や KILL_FLAG_CLEAR_ON_START 等を慎重に設定してください。validate_config は live 時に追加ガードをチェックします。
- 自動 .env ロード:
  - プロジェクトルート（.git または pyproject.toml）から .env を自動読み込みします。自動読み込みを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。
- YAML 設定:
  - config/*.yaml（system_config.yaml, data_config.yaml, strategy_config.yaml, risk_config.yaml, execution_config.yaml, monitoring_config.yaml）が想定されています。見つからない場合は警告が出ます。generate_config スクリプト（scripts/generate_config.py）がある場合はそれで生成できます。

ディレクトリ構成（主要ファイル）
--------------------------------
src/kabusys/
- __init__.py                 — パッケージ情報（バージョン等）
- config.py                   — 環境変数読み込み／Settings クラス（アプリ設定の取得）
- config_setup.py             — .env 対話ウィザード
- validate_config.py          — 起動前設定検証 CLI
- run_execution.py            — ExecutionEngine 起動スクリプト
- run_monitoring.py           — 監視ループ起動スクリプト

src/kabusys/execution/
- broker_api.py               — Broker API の Protocol / データモデル / ファクトリ
- kabu_client.py              — kabu station REST クライアント実装
- mock_client.py              — テスト用モッククライアント（MockBrokerClient）
- broker_factory.py           — Settings に基づくクライアント生成ファクトリ
- execution_engine.py         — ExecutionEngine 本体（シグナル処理 / push 処理 / kill）
- order_record.py             — 注文状態モデルと遷移ロジック（純粋ロジック）
- order_repository.py         — SQLite ベースの永続化層
- order_manager.py            — 外向きの注文管理（作成／送信／同期／キャンセル）
- reconciler.py               — 起動時のリコンシリエーション（OrderSent の突合）
- risk_manager.py             — Gate1〜3 のリスク制御

src/kabusys/data/
- calendar_management.py      — マーケットカレンダー管理（J-Quants 連携）
- news_collector.py           — RSS ニュース収集と前処理

src/kabusys/monitoring/
- monitoring_db.py            — 監視用 SQLite テーブル初期化 / ログ関数
- system_monitor.py           — 監視ロジック（別プロセスで定期実行）

src/kabusys/utils/
- logging_setup.py            — ログ設定ユーティリティ
- process_priority.py         — プロセス優先度設定ユーティリティ

（上は主要なファイル・モジュール一覧です。実際のリポジトリでは更に補助スクリプトや tests 等が存在する可能性があります）

開発・テスト
-------------
- MockBrokerClient により kabu station が無くてもローカルでエンジンを動かして挙動検証が可能です（paper_trading / development）。
- Settings や .env の自動ロードを無効化して単体テストを実行できます:
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 pytest ...

ライセンス / 保守
-----------------
- このリポジトリ内のコメントやドキュメントを参照して運用してください。.env は機密情報を含むため絶対にリポジトリにコミットしないでください。

問題／提案
---------
問題点や追加要望がある場合は Issue を立ててください。運用上の注意（本番設定、セキュリティ、LINE トークン管理等）については慎重に扱ってください。

以上です。開始手順の推奨フロー:
1) python -m kabusys.config_setup
2) python -m kabusys.validate_config
3) python -m kabusys.run_monitoring （監視開始）
4) python -m kabusys.run_execution （発注エンジン起動）