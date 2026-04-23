# KabuSys

日本株自動売買システムの一部コードベース（ライブラリ & 実行スクリプト）の README です。  
この README はソース内のモジュール・コメントを元に作成しています。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株の自動売買を目的としたシステムのコア部分です。主な責務は次のとおりです。

- シグナルに基づく発注フロー（ExecutionEngine）
- 発注状態管理（OrderRecord / OrderManager）
- ブローカークライアント抽象化（実機: KabuStationClient / モック: MockBrokerClient）
- リスク制御（3段階のゲート: Gate1/2/3）
- 起動時のリコンシリエーション（Reconciler）
- 監視用ポーリングループ（run_monitoring）
- 環境設定ウィザードおよび設定検証 CLI（config_setup / validate_config）
- マーケットカレンダーやニュース収集などのデータ処理ユーティリティ

設計上、ビジネスロジック（OrderRecord 等）と永続化層（OrderRepository : SQLite）は分離されています。Paper Trading（テスト）用に MockBrokerClient が用意され、本番（live）用の実装もクライアント層に存在しますが、ファクトリでは live の自動生成は制限されています。

---

## 機能一覧

- 環境設定ウィザード（.env の対話式作成 / 更新）
- 設定検証 CLI（.env と config/*.yaml の事前チェック、--strict オプション）
- ExecutionEngine
  - シグナル読み取り（DuckDB）→ 発注（OrderManager）→ push ドレイン（WebSocket）
  - 発注ループと push ドレインの時間帯管理（例: 8:50-9:10 シグナル処理、9:10-15:30 ドレイン）
  - PID / kill flag 管理
- Order 管理
  - OrderRecord（状態遷移の検証）
  - OrderRepository（SQLite を用いた永続化）
  - OrderManager（発注のライフサイクル: create / send / sync / cancel）
- リスク管理（RiskManager）
  - Gate 1: シグナルレベル（余力・重複・ポジション上限）
  - Gate 2: エグゼキューション（レート制限・サーキットブレーカー）
  - Gate 3: 約定後メトリクス（ドローダウン監視、kill switch）
- Reconciler（起動時の OrderSent 照合、ポジション差分検出）
- ブローカークライアント
  - MockBrokerClient（テスト用）
  - KabuStationClient（kabuステーション REST API クライアント）
- データユーティリティ
  - マーケットカレンダー管理（DuckDB を使用）
  - ニュース収集モジュール（RSS 収集、正規化、SSRF 対策等）
- 監視ループ（run_monitoring）: SQLite / DuckDB を利用して定期的にシステム状態を記録

---

## 必要な環境変数（主なもの）

必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

任意・設定可能な主要項目（デフォルトや役割は下記参照）:
- KABUSYS_ENV (development / paper_trading / live) — default: development
- DUCKDB_PATH — default: data/kabusys.duckdb
- SQLITE_PATH — default: data/monitoring.db
- LOG_LEVEL — default: INFO
- KABU_API_BASE_URL — default: http://localhost:18080/kabusapi
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID — LINE 通知設定（任意）
- KILL_FLAG_CLEAR_ON_START — 起動時 kill.flag 自動クリア（0/1）

注意: Settings クラスにより一部変数は検証・変換されます（例: PAPER_FILL_MODE 固定値チェック等）。

---

## セットアップ手順（ローカル開発向け）

1. ソースを取得し、プロジェクトルートへ移動
   - この README は `src/kabusys` を想定しています（パッケージ構成に合わせてください）。

2. Python 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - Windows: .venv\Scripts\activate
   - macOS/Linux: source .venv/bin/activate

3. 必要パッケージをインストール
   - 以下はコードから推測される主要依存パッケージです。プロジェクトに requirements.txt がある場合はそちらを使用してください。
     - duckdb
     - httpx
     - websocket-client
     - PyYAML (設定検証で YAML パースをする場合)
     - defusedxml
   - 例:
     - pip install duckdb httpx websocket-client PyYAML defusedxml

   標準ライブラリでカバーされるもの:
   - sqlite3, logging, threading, json, datetime など

4. .env を用意する
   - 対話式ウィザードを使うのが簡単です（次項参照）。
   - あるいはプロジェクトルートに直接 `.env` ファイルを置くこともできます。
   - 自動読み込み: Settings モジュールはプロジェクトルート（.git または pyproject.toml）を探索して `.env` / `.env.local` を自動ロードします。テスト時は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化できます。

---

## .env 作成（対話ウィザード）

対話式で .env を作成 / 更新できます:

- 実行:
  - python -m kabusys.config_setup

- 例:
  - python -m kabusys.config_setup --env-file .env

ウィザードの説明やデフォルト値が表示され、秘密情報項目は表示がマスクされます。ウィザード実行後、保存確認があり `.env` に書き出されます。

ウィザード完了後は設定検証を実行してください。

---

## 設定検証

起動前に環境変数や config/*.yaml を検査できます。

- 実行:
  - python -m kabusys.validate_config
  - 厳格モード（警告も失敗扱い）:
    - python -m kabusys.validate_config --strict

出力は INFO / WARNING / ERROR に分類され、exit code は検出結果により 0/1 を返します。PyYAML が無い場合は YAML 内容検証をスキップし警告が出ます。

---

## 実行方法（主要スクリプト）

- 監視ループ（SystemMonitor ポーリング）
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書き可能（デフォルト 60）。

- 発注エンジン（ExecutionEngine）
  - python -m kabusys.run_execution
  - KABUSYS_ENV により動作モードが変わります:
    - development / paper_trading → MockBrokerClient を使用（create_broker_api で mock=True）
    - live → 現状ファクトリ経由では NotImplementedError（本番クライアントの取り扱いに注意）

注意:
- 実行中はプロセス優先度を設定し、PID ファイル / kill flag を利用して制御します（デフォルトパスは Settings により定義）。
- ExecutionEngine はシグナル処理・push ドレイン・kill switch・リコンシリエーション等のフローを内包します。

---

## 使い方（簡単なワークフロー）

1. 仮想環境を作成し依存ライブラリをインストール
2. python -m kabusys.config_setup で .env を作成
3. python -m kabusys.validate_config で設定確認（--strict 推奨）
4. paper_trading モードで試す場合は KABUSYS_ENV=paper_trading を .env に設定
   - 必要であれば PAPER_FILL_MODE を設定（instant / partial / never / reject）
5. 実行:
   - 監視のみ: python -m kabusys.run_monitoring
   - 発注実行: python -m kabusys.run_execution

開発時は MockBrokerClient を使い、duckdb / sqlite のファイルはデフォルトで `data/` 以下に作成されます（親ディレクトリが無くても起動時に自動作成される場合がありますが、権限やパスに注意してください）。

---

## ディレクトリ構成（主要ファイル / モジュール）

以下は `src/kabusys` を起点とした主要なファイル群です（抜粋）。

- kabusys/
  - __init__.py
  - config.py                    — 環境変数読み込み / Settings
  - config_setup.py              — .env 対話式ウィザード CLI
  - validate_config.py           — 設定検証 CLI
  - run_execution.py             — ExecutionEngine 起動スクリプト
  - run_monitoring.py            — Monitoring 起動スクリプト
  - execution/                    — 発注 / ブローカー周り
    - __init__.py
    - broker_api.py              — Protocol / データモデル / ファクトリ
    - broker_factory.py          — Settings に基づくクライアント生成
    - kabu_client.py             — kabuステーション REST クライアント
    - mock_client.py             — MockBrokerClient（テスト用）
    - order_record.py            — Order 状態遷移モデル
    - order_repository.py        — SQLite 永続化
    - order_manager.py           — 外向け注文 API（create/send/sync/cancel）
    - execution_engine.py        — ExecutionEngine（シグナル処理・pushドレイン）
    - reconciler.py              — 起動時リコンシリエーション
    - risk_manager.py            — 3段階リスクガード
    - ...（他に order_manager などの補助モジュール）
  - data/
    - calendar_management.py     — マーケットカレンダー管理（DuckDB）
    - news_collector.py          — RSS ニュース収集
    - jquants_client.py          — J-Quants API クライアント（参照あり）
  - monitoring/
    - monitoring_db.py           — 監視用 DB 初期化・ログ機能（参照あり）
    - system_monitor.py          — 実際の監視ロジック（参照あり）
  - utils/
    - logging_setup.py           — ロギングのセットアップ
    - process_priority.py        — プロセス優先度の調整
  - config/                      — YAML 設定ファイルを想定（system_config.yaml 等）

config/ 配下の想定ファイル:
- system_config.yaml
- data_config.yaml
- strategy_config.yaml
- risk_config.yaml
- execution_config.yaml
- monitoring_config.yaml

（validate_config.py がこれらの存在 / YAML パースをチェックします）

---

## 主要設計上のポイント・注意点

- 発注の永続化は SQLite（orders テーブル）で行われ、OrderSent 状態でクラッシュすると list_uncertain() に残る設計。Reconciler が再起動時に照合して回復を試みる。
- ExecutionEngine は時間帯で処理を分ける（シグナル処理 → push ドレイン）。テストではこれらメソッドを直接呼び出して検証可能。
- RiskManager はトークンバケツ（レート制限）とサーキットブレーカーを実装。API エラーの連続でサーキットブレーカーが OPEN になり発注停止する。
- MockBrokerClient は paper_trading / development 環境でのテストを容易にする。PAPER_FILL_MODE により挙動（instant/partial/never/reject）を切り替えられる。
- .env は機密情報を含むため、Git 等にコミットしないことを README とウィザードでも強調しています。

---

## トラブルシューティング / よくある確認点

- validate_config が警告やエラーを出す場合はまず .env の必須変数（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD）を確認してください。
- PyYAML が未インストールだと YAML 内容検証がスキップされます（警告）。必要なら pip install PyYAML。
- DuckDB や websocket-client が無いと実行スクリプトの一部機能が動作しません。エラーメッセージに従って missing package をインストールしてください。
- run_execution/run_monitoring の停止はプロジェクトルートの data/stop_requested.flag を作成するか、プロセスを割り込む（Ctrl+C）して終了できます。
- kill.flag が存在すると ExecutionEngine の起動が拒否されます（KILL_FLAG_CLEAR_ON_START=1 の場合は自動クリア可）。

---

## 最後に

この README はソースの docstring / コメントを元に要点をまとめたものです。実際の運用前には必ず:
- .env の内容を正しく設定・保護すること
- validate_config で検証すること
- 本番環境では十分な監視と手動確認のプロセスを準備すること

必要であれば README に追記したい項目（依存関係の正確なリスト、起動用 systemd / サービスユニットの例、DB 初期化スクリプト など）を教えてください。