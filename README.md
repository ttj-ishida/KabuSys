KabuSys — 日本株自動売買システム (README)
======================================

概要
----
KabuSys は日本株向けの自動売買システムのコア実装です。  
本リポジトリには設定管理、実行エンジン、注文永続化、ブローカークライアント（実装 & モック）、リスクガード、リコンシリエーション、マーケットカレンダー・ニュース収集などの主要コンポーネントが含まれます。  
設計方針としては、DB と API 呼び出しの責務を明確に分離し、再起動やクラッシュ時の安全性（2相永続化・リコンシリエーション）、テスト容易性（MockBroker）を重視しています。

主な機能
-------
- 環境設定ウィザード（.env 作成／更新）: kabusys.config_setup
- 設定検証 CLI（.env と config/*.yaml の存在・基本整合性チェック）: kabusys.validate_config
- 実行エンジン（Signal Queue Pull 型）: ExecutionEngine（発注フロー、WebSocket push ドレイン、kill-switch）
- 発注管理（OrderManager / OrderRecord / OrderRepository）: 注文状態遷移・永続化・同期
- ブローカークライアント群:
  - MockBrokerClient（テスト・開発用、複数の fill_mode をサポート）
  - KabuStationClient（kabu station REST API 実装）
  - Broker API ファクトリ create_broker_api
- リスク管理（3段階ガード: Gate1/2/3）: RiskManager
- リコンシリエーション（起動時の自動復旧）: Reconciler
- 監視ポーリングループ（SystemMonitor 起動）: run_monitoring
- データ関連:
  - マーケットカレンダー管理（J-Quants ベース）: calendar_management
  - ニュース収集（RSS）: news_collector
- ロギング、プロセス優先度制御、PID/Kill フラグ管理など運用支援

セットアップ手順
--------------
前提:
- Python 3.9+（コードは型ヒントに Path | None 等を使っています）
- DuckDB, sqlite3 はランタイムで使用します（duckdb は Python パッケージとして必要）

1. リポジトリをクローン
   - git clone ... （プロジェクトルートが .git や pyproject.toml を持つことを想定）

2. 仮想環境を用意（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   - pip install duckdb httpx websocket-client defusedxml
   - 任意（YAML 検証を行いたい場合）: pip install pyyaml
   - 追加のユーティリティがあれば requirements.txt を用意していれば pip install -r requirements.txt

4. data ディレクトリなどの作成（自動生成される場合もありますが、事前に作ると安心）
   - mkdir -p data

5. 初期設定ファイルの作成
   - python -m kabusys.config_setup
     - 対話式ウィザードで .env を生成／更新します（.env は絶対に Git にコミットしないでください）

6. 設定検証
   - python -m kabusys.validate_config
   - 必要なら厳格モード: python -m kabusys.validate_config --strict

使い方
-----
共通:
- 環境変数は .env / .env.local / OS 環境変数の順で読まれます（OS 環境変数が最優先）。自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可。

主要コマンド:
- 設定ウィザード（.env 作成）:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config
  - --strict を付けると警告も失敗扱いで exit(1)
- 実行エンジン起動（本番相当のセッション実行）:
  - python -m kabusys.run_execution
  - KABUSYS_ENV が paper_trading または development の場合は MockBroker を使用します。live は未実装（NotImplementedError）。
- 監視ループ起動:
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL（秒）でポーリング間隔を変更可（デフォルト 60）

必須／主な環境変数:
- 必須:
  - JQUANTS_REFRESH_TOKEN — J-Quants API 用リフレッシュトークン
  - KABU_API_PASSWORD — kabuステーション API パスワード
- 任意（デフォルト値ありまたは空許容）:
  - KABUSYS_ENV — execution/monitoring の環境（development / paper_trading / live）
  - DUCKDB_PATH — DuckDB ファイルパス（default: data/kabusys.duckdb）
  - SQLITE_PATH — 監視 DB（default: data/monitoring.db）
  - LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
  - KABU_API_BASE_URL — kabu station base URL
  - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — 通知設定
  - KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアする（0/1）

. env の注意:
- .env はプロジェクトルートに置きます。config_setup で生成されたテンプレートに従ってください。
- 自動ロードは OS 環境変数 > .env.local > .env の優先順です。
- .env をコミットしないこと（秘密情報含む）。

挙動上の重要点（運用メモ）:
- ExecutionEngine はセッション時間に基づく挙動（デフォルト: シグナル処理 8:50-9:10、マーケットクローズ 15:30）で動作します。
- kill.flag（Settings.kill_flag_path）で外部停止を制御。KILL_FLAG_CLEAR_ON_START=1 に注意（本番では推奨されない）。
- OrderManager は二相永続化を用い、クラッシュ時に OrderSent の不確実状態を残してリコンシリエーションで回復できる設計です。
- Reconciler は起動時に OrderSent を突合し、ポジション差分を検出します。

ディレクトリ構成（主要ファイル）
------------------------------
以下は src/kabusys 以下の主なファイルと役割（抜粋）です。

- src/kabusys/
  - __init__.py — パッケージ定義、バージョン
  - config.py — 環境変数読み込み・Settings クラス（.env 自動ロードなど）
  - config_setup.py — .env 対話式ウィザード（python -m kabusys.config_setup）
  - validate_config.py — 起動前設定検証 CLI（python -m kabusys.validate_config）
  - run_execution.py — ExecutionEngine 起動スクリプト（python -m kabusys.run_execution）
  - run_monitoring.py — SystemMonitor ポーリング起動（python -m kabusys.run_monitoring）
  - execution/  — 発注関連（クライアント・エンジン・リスク等）
    - broker_api.py — Broker API のデータモデル・Protocol・ファクトリ
    - kabu_client.py — kabu station REST クライアント（httpx）
    - mock_client.py — MockBrokerClient（テスト用）
    - broker_factory.py — Settings に基づくクライアント生成
    - order_record.py — 注文状態モデルと遷移ロジック
    - order_repository.py — SQLite ベースの永続化
    - order_manager.py — 発注 API（作成→送信→同期→キャンセル）
    - execution_engine.py — セッション制御・シグナル処理・push ドレイン
    - reconciler.py — 起動時の自動復旧処理
    - risk_manager.py — Gate1/2/3 のリスク統制
  - data/  — データ系モジュール
    - calendar_management.py — マーケットカレンダー管理（DuckDB）
    - news_collector.py — RSS ニュース収集、前処理、安全性対策
    - jquants_client.py — （参照されるがここでは省略／J-Quants API のクライアント想定）
  - monitoring/ — 監視 DB / SystemMonitor 等（ファイルは省略されている場合あり）
  - utils/ — ロギングセットアップやプロセス優先度制御等ユーティリティ（ファイルは省略されている場合あり）
  - config/ — config/*.yaml（system_config.yaml 等をプロジェクト直下の config に置く想定）

config ディレクトリに期待されるファイル（validate_config 参照）
- system_config.yaml
- data_config.yaml
- strategy_config.yaml
- risk_config.yaml
- execution_config.yaml
- monitoring_config.yaml

その他の注意点
--------------
- live 環境（KABUSYS_ENV=live）は実装の一部（特に Broker の live 実装）で未対応です。paper_trading / development（MockBroker）での動作検証を想定しています。
- YAML の内容検証は PyYAML がインストールされている場合に行われます。未インストール時は警告のみ出力してスキップされます。
- news_collector は SSRF 対策、受信最大サイズ制限、XML パーサの安全化（defusedxml）などを意識して実装されています。

付録: よく使うコマンド一覧
-----------------------
- .env ウィザード:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict
- 実行エンジン起動:
  - python -m kabusys.run_execution
- 監視ポーリング起動:
  - python -m kabusys.run_monitoring

フィードバック / 開発
-------------------
設計や実装の拡張（例: live ブローカー実装、非同期化、追加ログやメトリクス出力、テストカバレッジ強化など）は歓迎です。PR や issue を通じて提案してください。

以上。README の追記／修正希望があれば、どの部分を詳しく書くか教えてください。