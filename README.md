# KabuSys

日本株向けの自動売買システム（ミニマム実装）。  
このリポジトリは、発注エンジン、リスク管理、ブローカークライアントの抽象化、監視ループ、データ処理ユーティリティなどを含む構成になっています。

> 注意: この README はソース内の docstring とコードから生成しています。実行前に必ず設定検証を行ってください。

---

## 概要

KabuSys は次の要素を備えた自動売買プラットフォームのコア部分です。

- 発注エンジン（ExecutionEngine）：シグナルに基づく発注フロー、WebSocket push ドレイン
- 注文管理（OrderManager / OrderRepository / OrderRecord）：注文状態遷移と SQLite 永続化
- ブローカー抽象（BrokerAPIProtocol）：実際の kabu station クライアント / Mock クライアントの切替
- リスク管理（RiskManager）：Gate1〜3（シグナル検査、レート制限／サーキットブレーカー、ドローダウン監視）
- リコンシリエーション（Reconciler）：クラッシュ後の自動同期処理
- 監視ループ（SystemMonitor 起動スクリプト）：監視用 DB へのログ保存
- データユーティリティ（マーケットカレンダー、ニュース収集等）
- 環境設定ウィザード & 設定検証 CLI

本プロジェクトは開発／ペーパートレード／本番環境を区別して動作します（KABUSYS_ENV）。

---

## 主な機能一覧

- .env / .env.local 自動読み込み（実行時、OS 環境変数を保護）
- 対話式 .env 作成ウィザード（python -m kabusys.config_setup）
- 設定検証ツール（python -m kabusys.validate_config）
  - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性、DB パス、config/*.yaml の存在・パースチェック（PyYAML があれば検証）
  - --strict で警告も失敗扱いにできる
- MockBrokerClient によるペーパートレード（PAPER_FILL_MODE により即時約定／部分約定／拒否等を模擬）
- 発注の冪等性（client_order_id は UUID、signal_id による部分ユニーク制約）
- 起動時リコンシリエーション（OrderSent の突合・ポジション差分検出）
- 監視 DB（SQLite）と分析 DB（DuckDB）を分離して使用
- WebSocket push ハンドリング（kabu station の push を受け取り同期）

---

## 事前準備（依存関係）

最低限必要な Python パッケージ（代表例）:

- python >= 3.9
- duckdb
- httpx
- websocket-client
- defusedxml
- PyYAML（config/*.yaml の内容検証を行う場合）
- （標準ライブラリ: sqlite3 等は組み込み）

インストール例（仮）:

pip install duckdb httpx websocket-client defusedxml PyYAML

プロジェクトを editable インストールする場合:

pip install -e .

（実際の要件はプロジェクトの requirements ファイルや pyproject.toml を参照してください）

---

## セットアップ手順

1. リポジトリをクローン / チェックアウト
2. 必要な Python パッケージをインストール
3. 対話式ウィザードで .env を作成（推奨）
   - python -m kabusys.config_setup
   - ウィザードは既存の .env を読み込み、Enter で既存値を流用できます
4. 設定検証を実行
   - python -m kabusys.validate_config
   - 警告を FAIL としたい場合は --strict を付ける
5. DB 用ディレクトリ（data/ 等）がなければ作成（多くは起動時に自動作成されますが事前に用意しておいてもよい）

---

## 環境変数（主要）

必須:

- JQUANTS_REFRESH_TOKEN — J-Quants API 用リフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API パスワード

任意・デフォルトあり:

- KABUSYS_ENV — 実行環境（development / paper_trading / live）。デフォルト: development
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視 DB（デフォルト: data/monitoring.db）
- PID_FILE_PATH, KILL_FLAG_PATH など（Settings 参照）
- LOG_LEVEL — DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）
- KABU_API_BASE_URL — kabu station のベース URL（デフォルト: http://localhost:18080/kabusapi）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — 本番でのアラート送信に使用
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（0/1、デフォルト 0）
- PAPER_FILL_MODE — ペーパートレード時の fill 動作（instant / partial / never / reject）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード専用 SQLite（デフォルト: data/paper_trading.db）

.env 自動読み込み:
- プロジェクトルートの .env と .env.local が自動的に読み込まれます（OS 環境変数が優先されます）。
- 自動読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## 設定管理（.env）

- 対話式ウィザード: python -m kabusys.config_setup
  - 既存の .env を読み込んで更新できます
  - 作成後、python -m kabusys.validate_config で検証を推奨

- validate_config の使い方:
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict  （警告も失敗扱い）

---

## 実行方法（主なエントリポイント）

- 監視ループ開始（SystemMonitor ポーリング）
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書きできます（デフォルト 60 秒）
  - 監視は常に sqlite_path（本番パス）を使用します

- 発注エンジン起動（ExecutionEngine）
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用して data/paper_trading.db に分離して記録します
  - 起動時に data/execution.pid に PID が書き出され、停止フラグ data/stop_requested.flag の検出でループを終了します
  - settings.kill_flag_path（デフォルト data/kill.flag）で kill_switch の判定を行います

- 設定検証
  - python -m kabusys.validate_config

- 環境設定ウィザード
  - python -m kabusys.config_setup

---

## 実行時の注意点（本番向け）

- KABUSYS_ENV=live を設定する場合は特に注意:
  - LINE 通知設定が未設定だとアラートが届きません（validate_config が警告を出します）
  - KILL_FLAG_CLEAR_ON_START=1 は本番では危険（kill flag が自動でクリアされます）
- PID / kill / stop フラグの運用方法を運用ドキュメントで厳密に定義してください
- DB 周り（特に本番 duckdb/sqlite ファイルパス）はバックアップと権限管理を行ってください

---

## 主要な設計ポイント（簡易）

- 発注は 2 相永続化（OrderSent を先に保存 → ブローカー API 呼び出し → broker_order_id を保存 → OrderAccepted など）でクラッシュ耐性を強化
- OrderSent のままクラッシュしたレコードは Reconciler で復旧可能
- RiskManager は 3 つのゲートで安全性を担保（シグナル→実行→メトリクス）
- MockBrokerClient によりローカルで本番相当のフローをテスト可能

---

## ディレクトリ構成

（代表的なファイルのみ抜粋）

src/kabusys/
- __init__.py — パッケージ定義、バージョン
- config.py — Settings クラス（環境変数読み込み・バリデーション）、.env 自動ロード
- config_setup.py — .env 作成用対話式ウィザード
- validate_config.py — 起動前設定検証 CLI
- run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト
- run_execution.py — ExecutionEngine 起動スクリプト
- execution/
  - __init__.py — execution 層の公開 API
  - broker_api.py — BrokerAPIProtocol、データモデル、ファクトリ
  - kabu_client.py — kabu station REST クライアント（httpx）
  - mock_client.py — MockBrokerClient（テスト用）
  - broker_factory.py — Settings を基にブローカークライアントを選択する
  - order_record.py — OrderRecord と状態遷移（純粋ロジック）
  - order_repository.py — SQLite 永続化層（orders テーブル定義 + CRUD）
  - order_manager.py — 外向き注文 API（create/send/sync/cancel）
  - execution_engine.py — セッション実行ロジック（シグナル処理・push ドレイン）
  - reconciler.py — 起動時リコンシリエーション
  - risk_manager.py — Gate1/2/3 のリスク制御
- data/
  - calendar_management.py — マーケットカレンダー管理（DuckDB）
  - news_collector.py — RSS ニュース収集
  - (jquants_client など他データクライアントが存在)
- monitoring/
  - monitoring_db.py — 監視用 DB 初期化・ログ関数（参照のみ）
  - system_monitor.py — システム監視ロジック（参照のみ）
- utils/
  - logging_setup.py — ロギング設定ユーティリティ
  - process_priority.py — プロセス優先度設定ユーティリティ

data/（実行時生成されるファイルの例）
- data/kabusys.duckdb — DuckDB（分析 / シグナル / calendar 等）
- data/monitoring.db — 監視用 SQLite
- data/paper_trading.db — ペーパートレード専用 SQLite（paper_trading 環境）
- data/execution.pid — ExecutionEngine の PID（起動時に作成）
- data/kill.flag — Kill フラグ（手動で立てる）
- data/stop_requested.flag — 外部停止フラグ

config/
- system_config.yaml
- data_config.yaml
- strategy_config.yaml
- risk_config.yaml
- execution_config.yaml
- monitoring_config.yaml

（config/*.yaml はプロジェクト固有の設定を保持。PyYAML 未インストール時は内容検証をスキップします）

---

## 例: よく使うコマンド

- .env を作成:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict
- 監視ループ起動:
  - python -m kabusys.run_monitoring
- 発注エンジン起動:
  - python -m kabusys.run_execution

---

## トラブルシューティング（簡易）

- validate_config で必須変数エラーが出た場合:
  - .env の該当キーを設定するか、OS 環境変数に追加してください
- config/*.yaml が無い・パースエラー:
  - python scripts/generate_config.py がある場合はそれで生成できます（validate_config の警告メッセージ参照）
  - PyYAML がない場合は pip install PyYAML
- ペーパートレードで DB を分離したい:
  - KABUSYS_ENV=paper_trading を設定すると paper_sqlite_path（デフォルト data/paper_trading.db）を使用します

---

## 最後に

この README はコードに埋められた説明を基に作成しています。運用前には必ず下記の点を確認してください:

- .env の必須変数が設定されていること
- validate_config を実行してエラー／警告を確認すること
- 本番環境（KABUSYS_ENV=live）では KILL フラグや通知設定（LINE）を十分に整備すること

必要があれば、運用ガイドやデプロイ手順、詳細なアーキテクチャ図を別途作成してください。