# KabuSys

日本株向け自動売買システム（ライブラリ / 実行スクリプト群）

この README はリポジトリ内の実装（設定管理 / 実行エンジン / ブローカークライアント / 監視 / データ収集 等）に基づいて作成されています。簡単なセットアップ手順と主要スクリプトの使い方、ディレクトリ構成を日本語でまとめます。

---

## プロジェクト概要

KabuSys は日本株の自動売買を想定したコンポーネント群です。主な役割は以下の通りです。

- 環境変数（.env）管理と対話的セットアップウィザード
- 起動前の設定検証（必須環境変数や config/*.yaml の存在・パースなど）
- 発注エンジン（ExecutionEngine）: シグナル読み込み → リスクチェック → ブローカー発注 → リコンシリエーション
- ブローカークライアント（実ブローカー：kabuステーション用、モック：テスト／ペーパートレード用）
- 監視プロセス（SystemMonitor のポーリングループ）
- データ周りのユーティリティ（マーケットカレンダー、ニュース収集など）

設計上、DB（DuckDB / SQLite）とブローカークライアントは分離されており、ペーパートレード（モック）と本番（ライブ）を切り替え可能です。

---

## 機能一覧

- .env 対話式ウィザード（python -m kabusys.config_setup）
  - 必須 / 任意項目を対話的に入力して .env を生成
- 設定検証 CLI（python -m kabusys.validate_config）
  - 必須環境変数の確認、KABUSYS_ENV / LOG_LEVEL 検証、DB パスの親ディレクトリ確認、config/*.yaml 存在・パース確認（PyYAML があればパース検査）
  - --strict オプションで警告も失敗扱いに
- ExecutionEngine（発注エンジン）
  - シグナルを DuckDB から読み込んで発注する（時間帯：8:50〜9:10 のシグナル処理、9:10〜15:30 の push ドレイン処理）
  - 3 段階のリスクガード（Gate1: シグナルレベル、Gate2: 実行レベル、Gate3: ドローダウン監視）
  - Reconciler による起動時の自動復旧（OrderSent の照合、ポジション差分検出）
  - paper_trading モードでは MockBrokerClient を使用してデータを本番 DB と分離
- ブローカークライアント
  - KabuStationClient（httpx + websocket-client を利用）
  - MockBrokerClient（テスト用 / fill_mode 指定可能）
- 監視プロセス（run_monitoring）
  - 定期ポーリングでシステム状態を監視し、SQLite にログを記録
- データモジュール
  - マーケットカレンダー管理（DuckDB ベース）
  - ニュース収集（RSS、SSRF 対策、正規化、前処理）

---

## セットアップ手順

前提
- Python 3.10 以上を推奨（型注釈で | を使用）
- git, Python の仮想環境（venv 等）

例）ローカルセットアップ手順:

1. リポジトリをクローンし、仮想環境を作る
   - git clone <リポジトリ>
   - python -m venv .venv
   - source .venv/bin/activate (Windows は .venv\Scripts\activate)

2. 依存パッケージをインストール
   - 本リポジトリに requirements.txt がある場合:
     - pip install -r requirements.txt
   - 主要な依存の例（最低限）
     - pip install duckdb httpx websocket-client defusedxml
   - 任意（YAML の検証を行いたい場合）:
     - pip install pyyaml

3. .env を作成
   - 対話式ウィザードを使う（推奨）:
     - python -m kabusys.config_setup
     - ウィザード完了後、.env が保存されます（デフォルト: プロジェクトルート/.env）
   - 手動で作成する場合は .env.example を参考に必須項目を設定してください。

4. 設定検証
   - python -m kabusys.validate_config
   - 警告も失敗にしたい場合:
     - python -m kabusys.validate_config --strict

5. DB 初期化（必要に応じて）
   - 実行時スクリプトが SQLite / DuckDB のテーブルを初期化するコードを含むものがあります（例: init_monitoring_db, init_orders_db）。実行前に data ディレクトリを作成しておくと良いです。
   - data ディレクトリ作成:
     - mkdir -p data

注意:
- 自動で .env をロードする仕組みがあります（プロジェクトルートが特定できる場合、.env → .env.local の順に読み込む）。自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## 環境変数（主なもの）

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants API 用リフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API パスワード

推奨 / 任意:
- KABUSYS_ENV — 実行環境（development / paper_trading / live） デフォルト: development
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード専用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL） デフォルト: INFO
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — アラート通知に使用（任意）
- KILL_FLAG_CLEAR_ON_START — 起動時 kill.flag を自動クリアするか（0/1、デフォルト: 0）

関連ファイル / フラグ:
- data/kill.flag — Kill Switch（存在時は Engine の kill をトリガ）
- data/stop_requested.flag — 実行中のプロセスが外部停止要求を検知するためのフラグ
- PID ファイル: data/execution.pid（デフォルト、変更可能）

---

## 使い方（主要スクリプト）

- 環境設定ウィザード（.env を作成 / 更新）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 厳格モード（警告も失敗扱い）:
    - python -m kabusys.validate_config --strict

- 実行エンジン起動（Execution）
  - python -m kabusys.run_execution
  - 挙動:
    - KABUSYS_ENV が paper_trading の場合: MockBrokerClient を使用し paper_trading 用 SQLite（PAPER_TRADING_SQLITE_PATH）を使用
    - KABUSYS_ENV が development の場合: テスト用に Mock を利用
    - KABUSYS_ENV が live の場合: 現在は NotImplementedError（ライブブローカーは未実装。将来実装想定）

- 監視プロセス起動（Monitoring）
  - python -m kabusys.run_monitoring
  - 挙動:
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で上書き（デフォルト 60）
    - 監視は常に本番 sqlite_path（SQLITE_PATH）を使用

- 停止 / Kill フラグ
  - 実行中のプロセスは data/stop_requested.flag や data/kill.flag の存在を監視しています。外部から停止させたい場合はこれらのファイルを作成することで挙動を制御できます（運用ポリシーに依存）。

---

## 実行時の挙動（注意点）

- 発注ワークフローはクラッシュ耐性を考慮して実装されています（OrderSent 前後の永続化戦略、OrderSentPending の扱い、Reconciler による復旧）。
- ExecutionEngine はセッション制御（開始／締切／終了時刻）に基づき動きます。テストでは個別メソッドを直接呼ぶことが推奨されます。
- サーキットブレーカー / レート制限 / ドローダウン監視が組み込まれています（RiskManager）。
- 設定検証（validate_config）は PyYAML 未インストール時に YAML パースチェックをスキップします（警告が出ます）。YAML の内容確認を行う場合は PyYAML をインストールしてください。

---

## ディレクトリ構成（主要ファイル）

以下は src/kabusys 配下の主要モジュールと説明です（抜粋）。

- src/kabusys/
  - __init__.py — パッケージ定義（バージョン等）
  - config.py — 環境変数 / Settings クラス、自動 .env ロードロジック
  - config_setup.py — .env 対話式ウィザード（python -m kabusys.config_setup）
  - validate_config.py — 設定検証 CLI（python -m kabusys.validate_config）
  - run_execution.py — ExecutionEngine 起動スクリプト（python -m kabusys.run_execution）
  - run_monitoring.py — SystemMonitor 起動スクリプト（python -m kabusys.run_monitoring）
  - execution/
    - __init__.py
    - broker_api.py — ブローカー API の Protocol、データモデル、ファクトリ
    - broker_factory.py — Settings に応じたブローカー生成
    - kabu_client.py — kabuステーション向け HTTP/WebSocket クライアント
    - mock_client.py — テスト用モッククライアント
    - order_record.py — 注文状態モデルと遷移ロジック
    - order_repository.py — SQLite 永続化層
    - order_manager.py — 発注フローの外向け API
    - execution_engine.py — エンジン本体（セッション制御 / push drain 等）
    - reconciler.py — 起動時リコンシリエーション
    - risk_manager.py — 3 段階のリスクガード
  - data/
    - calendar_management.py — マーケットカレンダー周り
    - news_collector.py — RSS ニュース収集（SSRF 対策等）
    - （その他データ用モジュール）
  - monitoring/
    - monitoring_db.py — 監視用 DB 初期化・操作（参照箇所あり）
    - system_monitor.py — SystemMonitor（ポーリングループ）
  - utils/
    - logging_setup.py — ログ設定ユーティリティ
    - process_priority.py — プロセス優先度設定ユーティリティ

（上記は実装の一部を抜粋しています。リポジトリ全体のファイル構成に従って補完してください。）

---

## よくある操作例

- .env を対話式で作る:
  - python -m kabusys.config_setup
- 設定検証（警告も失敗にする）:
  - python -m kabusys.validate_config --strict
- 実エンジンを試す（テスト環境・ペーパートレード）:
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
- 監視を起動（デフォルト 60 秒ポーリング）:
  - python -m kabusys.run_monitoring

---

もし README に追加したい具体的な内容（例: 実際の .env.example、requirements.txt の内容、運用手順、Docker 化手順、単体テスト方法など）があれば教えてください。必要に応じて README を拡張します。