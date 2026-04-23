# KabuSys

日本株自動売買システム（軽量プロトタイプ）

このリポジトリは、kabuステーションや J-Quants を利用する日本株向け自動売買の主要コンポーネント群を含むプロジェクトの一部です。主にローカル開発 / ペーパートレード環境で動作するように設計されています。

バージョン: 0.1.0

---

## 概要

KabuSys は次の役割を持つコンポーネントを含みます:

- 環境設定管理 (.env 自動読み込み / 設定ウィザード)
- 設定検証 CLI（.env と config/*.yaml の検査）
- 発注ロジック（ExecutionEngine、OrderManager、OrderRepository、OrderRecord）
- ブローカークライアント実装
  - MockBrokerClient（テスト / ペーパートレード用）
  - KabuStationClient（kabuステーション REST API 実装）
- リスク管理（3段階ガード）
- リコンシリエーション（再起動時の状態整合）
- 監視サービス（SystemMonitor ポーリング）
- データ処理（カレンダー管理、ニュース収集等）

設計方針として、ビジネスロジックと永続化（SQLite）を分離し、クラッシュ時の整合性・リカバリ（2相永続化、reconciliation）を重視しています。

---

## 主な機能一覧

- .env ウィザード（対話式で .env を作成 / 更新）: python -m kabusys.config_setup
- 設定検証 CLI（必須環境変数や config/*.yaml の存在・パース検査）:
  - python -m kabusys.validate_config
  - --strict をつけると警告もエラー扱いで終了コード 1 を返す
- 発注エンジン（ExecutionEngine）
  - シグナル取得（DuckDB）→ Gate1/Gate2 リスクチェック → 発注 → push ドレイン
  - paper_trading / development では MockBrokerClient を利用
- ブローカークライアント
  - KabuStationClient: kabuステーション REST API 実装（httpx）
  - MockBrokerClient: fill_mode により instant/partial/never/reject を模擬
- 注文永続化（SQLite）
  - orders テーブル、ユニーク制約で同一 signal の重複防止
- リスク管理
  - Gate1: 余力 / 重複 / ポジション上限
  - Gate2: レート制限 / サーキットブレーカー
  - Gate3: ドローダウン監視（kill switch）
- リコンシリエーション（起動時の OrderSent の照合・ポジション差分検出）
- 監視ループ（SystemMonitor）: MONITOR_POLL_INTERVAL でポーリング間隔を制御

---

## 必須 / 推奨環境変数

必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

任意（但し多くは設定推奨）:
- KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
- DUCKDB_PATH — デフォルト: data/kabusys.duckdb
- SQLITE_PATH — デフォルト: data/monitoring.db
- LOG_LEVEL — DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト INFO）
- KABU_API_BASE_URL — kabuステーションのベース URL（デフォルト http://localhost:18080/kabusapi）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID — 本番のアラート通知用
- MONITOR_POLL_INTERVAL — 監視ポーリング間隔（秒、デフォルト 60）

注意:
- 自動で .env を読み込む（.env → .env.local の優先順）。自動読み込みを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- .env の初期作成は対話式ウィザードを推奨します（python -m kabusys.config_setup）。

---

## 依存パッケージ（代表例）

プロジェクト全体の requirements.txt はここに含まれていませんが、次のライブラリが必要/推奨されます:

- duckdb
- httpx
- websocket-client
- defusedxml
- PyYAML（validate_config で YAML 構文検査を行う場合に必要）
- （標準ライブラリ）sqlite3, logging, threading 等

環境によっては追加のパッケージが必要です。pip でインストールしてください。

---

## セットアップ手順（開発向け）

1. Python 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  （Windows は .venv\Scripts\activate）

2. 必要パッケージをインストール
   - pip install duckdb httpx websocket-client defusedxml PyYAML
   - （実際のプロジェクトでは requirements.txt を用意し、pip install -r requirements.txt を実行）

3. プロジェクトルートに data ディレクトリを作成
   - mkdir -p data

4. .env を作成
   - 対話式ウィザード: python -m kabusys.config_setup
   - 手動で作成する場合は .env.example（存在する場合）を参照して .env を作る

5. 設定検証を実行
   - python -m kabusys.validate_config
   - 警告を厳密に扱いたい場合: python -m kabusys.validate_config --strict

6. DB の初期化（必要に応じて）
   - Execution や Monitoring 起動時に必要テーブルが初期化される関数（例: init_monitoring_db, init_orders_db）があり、起動時に冪等に作成されます。

---

## 使い方（主要スクリプト）

- 設定ウィザード
  - python -m kabusys.config_setup
    - .env の作成 / 更新を対話式で行います。

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告も失敗扱い（終了コード 1）

- 発注エンジン（Execution）
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、paper_trading 用 SQLite（デフォルト data/paper_trading.db）に記録します。
  - 起動前に data/kill.flag が存在すると起動を拒否します。KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に自動クリアします。

- 監視ループ（Monitoring）
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL でポーリング間隔（秒）を変更可能（デフォルト 60）。
  - 監視は常に本番用 sqlite_path を使います（環境に関わらず）。

実運用では systemd / PM2 / コンテナ等を用いて起動管理することを想定しています。停止はファイルベースのフラグ（data/stop_requested.flag など）／PID ファイルを介して行います。

---

## 主要ファイル・ディレクトリ構成

以下は src/kabusys 以下の代表的な構成（抜粋）です:

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数読み込み・Settings 定義（自動 .env ロード）
  - config_setup.py           — 対話式 .env ウィザード
  - validate_config.py        — 起動前設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor 起動スクリプト
  - execution/
    - __init__.py
    - broker_api.py           — BrokerAPI の Protocol・データモデル・ファクトリ
    - kabu_client.py          — kabuステーション REST API 実装
    - mock_client.py          — MockBrokerClient（テスト用）
    - broker_factory.py       — Settings ベースのクライアント生成
    - order_record.py         — 注文状態モデルと遷移ロジック
    - order_repository.py     — SQLite 永続化層（orders テーブル）
    - order_manager.py        — 外向きの注文 API（create/send/sync/cancel）
    - execution_engine.py     — ExecutionEngine（シグナル読取・発注ループ）
    - reconciler.py           — 起動時リコンシリエーション
    - risk_manager.py         — 3段階リスクガード
  - data/
    - calendar_management.py  — マーケットカレンダー管理（DuckDB）
    - news_collector.py       — RSS ニュース収集（defusedxml 等を使用）
  - monitoring/
    - monitoring_db.py        — 監視用 DB 初期化・ログ関数（参照）
    - system_monitor.py       — SystemMonitor（ポーリングループ） — 実装参照
  - utils/
    - logging_setup.py        — ロギング設定ユーティリティ（参照）
    - process_priority.py     — プロセス優先度設定ユーティリティ（参照）

補足:
- config/*.yaml（system_config.yaml 等）は設定ファイル群。validate_config はこれらの存在と YAML パース（PyYAML 必須）をチェックします。
- data/ 配下に PID やフラグファイル（execution.pid, kill.flag, stop_requested.flag）を作成して制御します。

---

## 注意事項 / トラブルシューティング

- validate_config は PyYAML がない場合、YAML 内容の検証をスキップします（警告）。
- .env にプレースホルダ（末尾が `_here` や `your_value`）が残っていると警告が出ます。
- KABUSYS_ENV の `live` モードでは多くの注意喚起（LINE 通知設定や Kill Flag）を行いますが、現状 Live ブローカークライアント実装は未完成で NotImplementedError を投げる場合があります（設定を確認してください）。
- orders の同一 signal_id に対する重複はデータベース側で一件に制限しています。DuplicateOrderError が発生した場合は重複の可能性があります。
- ExecutionEngine は時刻ベースで動作します（シグナル送信開始・終了時間）。テスト時は該当メソッドを直接呼び出すことを検討してください。

---

## 制限事項 / 将来の実装予定

- Live 環境向けの本番ブローカークライアント（KabuStationClient の本格運用検証・追加実装）がまだ完全ではない箇所があります。
- 運用向けの監視・アラート（LINE 連携）の設定はユーザ側で行う必要があります。
- requirements.txt / Dockerfile / systemd ユニットは本 README に含まれていません。運用環境に合わせて追加してください。

---

README に記載のコマンドや設定は本コードベースの主要ワークフローを素早く開始するための要点をまとめたものです。詳細はソースコード内の docstring コメント（各モジュール頭部）を参照してください。必要であれば、README を拡張してセットアップスクリプトや Docker 化手順、CI 設定などを追記できます。