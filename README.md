# KabuSys

日本株自動売買システムの一部を実装した Python パッケージ。  
このリポジトリには、環境設定ウィザード、設定検証ツール、発注エンジンやモニタリング用のランナー、ブローカークライアント、注文状態管理、リコンシリエーション、リスクガード、マーケットカレンダーやニュース収集などの主要コンポーネントが含まれます。

---

## 概要

KabuSys は以下のような機能を持つ自動売買プラットフォームの基盤です。

- 環境変数 / .env による設定管理（自動ロード機能あり）
- 対話式の .env 作成ウィザード（config_setup）
- 起動前に環境設定を検証する CLI（validate_config）
- 実際のセッションを回す ExecutionEngine（run_execution）
- システム監視ループ（run_monitoring）
- ブローカークライアント抽象（実装: MockBrokerClient / KabuStationClient）
- 注文の状態遷移を扱う純粋モデル（OrderRecord）
- SQLite による注文永続化（OrderRepository）
- OrderManager による発注フロー（作成 → 送信 → 同期 → 取消）
- 起動時のリコンシリエーション（Reconciler）
- 3段階のリスクガード（RiskManager）
- DuckDB ベースのマーケットカレンダー管理 / シグナル読み込み
- RSS ニュース収集（news_collector）

設計上、DB 操作とビジネスロジックは分離され、各コンポーネントはテストしやすい形で実装されています。

---

## 主な機能一覧

- .env ウィザード（python -m kabusys.config_setup）
- 設定検証（python -m kabusys.validate_config）
  - 必須環境変数チェック、KABUSYS_ENV の妥当性、YAML 設定ファイルの存在・パース（PyYAML 必須）
  - --strict: 警告も失敗扱いに
- 実行エンジン（python -m kabusys.run_execution）
  - paper_trading モードでは Mock ブローカーを使用し本番 DB とは分離
  - kill.flag / PID 管理・Kill Switch 機構
- 監視ループ（python -m kabusys.run_monitoring）
  - SQLite / DuckDB に接続して定期的にシステム状態を記録
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更可能（デフォルト 60 秒）
- ブローカークライアント
  - MockBrokerClient（テスト用、fill_mode 等で挙動を切替）
  - KabuStationClient（kabuステーションの REST / WebSocket 実装）
- 注文管理（OrderManager / OrderRepository / OrderRecord）
  - 二相永続化やクラッシュ耐性を意識したフロー実装
- リスク管理（Gate1/Gate2/Gate3）
  - 余力、重複、ポジション上限、レート制限、サーキットブレーカー、ドローダウン監視
- データ処理ヘルパー
  - マーケットカレンダー（DuckDB, J-Quants 経由の更新ジョブ）
  - ニュース RSS 収集と前処理（SSRF 対策、トラッキング除去、defusedxml 使用）

---

## 要件

- Python 3.10+
- SQLite（標準ライブラリに同梱）
- 推奨 / 必要な Python パッケージ（用途に応じて）:
  - duckdb
  - httpx
  - websocket-client
  - PyYAML（YAML の検証を行う場合）
  - defusedxml（RSS パース）
- 上記パッケージは次のコマンドでインストールできます（任意）:
  - pip install duckdb httpx websocket-client PyYAML defusedxml

※ requirements.txt は本リポジトリに含まれていない場合があるため、用途に応じて必要なパッケージをインストールしてください。

---

## セットアップ手順

1. リポジトリをクローン / チェックアウト
   - git clone ...

2. Python 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - pip install duckdb httpx websocket-client PyYAML defusedxml

4. .env を作成する（推奨）
   - 対話式ウィザードを使う:
     - python -m kabusys.config_setup
   - もしくは手動でプロジェクトルートに .env を作成して必要な環境変数を設定する。

5. 設定を検証する
   - python -m kabusys.validate_config
   - 警告も失敗扱いにしたい場合:
     - python -m kabusys.validate_config --strict

---

## 環境変数（主要）

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants API のリフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API パスワード

任意・デフォルトあり:
- KABUSYS_ENV — 実行環境（development / paper_trading / live）。デフォルト: development
- DUCKDB_PATH — DuckDB DB のパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- LOG_LEVEL — ログレベル（DEBUG / INFO / WARNING / ERROR / CRITICAL）。デフォルト: INFO
- KABU_API_BASE_URL — kabu station API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID — 通知用（任意）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（0/1、デフォルト 0）
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、デフォルト 60）

自動ロード:
- プロジェクトルートに .env / .env.local がある場合、起動時に自動で読み込まれます（OS環境変数が優先されます）。
- 自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

簡単な .env の例:
JQUANTS_REFRESH_TOKEN=your_jquants_token_here
KABU_API_PASSWORD=your_kabu_password_here
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
LOG_LEVEL=INFO

---

## 使い方

- .env の作成（推奨）:
  - python -m kabusys.config_setup

- 設定検証:
  - python -m kabusys.validate_config
  - --strict を付けると警告もエラー扱いで exit code 1

- 実行エンジン（本番 / ペーパー）:
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient が利用され、paper_trading 用の SQLite（PAPER_TRADING_SQLITE_PATH）を使用します。
  - 実行中は data/execution.pid に PID が書き出され、data/stop_requested.flag の存在で停止します。
  - kill.flag の存在は起動拒否（ただし KILL_FLAG_CLEAR_ON_START=1 の場合は自動クリアして起動）

- モニタリング:
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更できます（デフォルト 60 秒）。
  - 監視は常に本番用の sqlite_path を参照します（環境にかかわらず）。

- プログラムから設定を使う:
  - from kabusys.config import settings
  - settings.jquants_refresh_token や settings.duckdb_path などでアクセス可能

---

## 注意点 / 運用メモ

- 本番（KABUSYS_ENV=live）では特に LINE 通知設定や KILL_FLAG_CLEAR_ON_START の設定を慎重に行ってください。validate_config は live の場合に追加チェックを行います。
- YAML 設定ファイル（config/*.yaml）は PyYAML がインストールされている場合にパース検証を行います。インストールがない場合は検証をスキップします。
- Execution の設計はクラッシュ耐性（OrderSent 状態の扱い、2相永続化の考慮）と起動時リコンシリエーションを重視しています。
- MockBrokerClient はユニットテスト・開発で便利です。fill_mode によって挙動を変えられます（instant / partial / never / reject）。

---

## ディレクトリ構成（抜粋）

プロジェクトの主なファイル / ディレクトリ構成（src/kabusys 以下）:

- src/kabusys/
  - __init__.py
  - config.py                    — 環境変数 / .env 読み込みと Settings クラス
  - config_setup.py              — 対話式 .env ウィザード
  - validate_config.py           — 起動前設定検証 CLI
  - run_execution.py             — ExecutionEngine 起動スクリプト
  - run_monitoring.py            — SystemMonitor ポーリングループ起動スクリプト

  - execution/
    - __init__.py
    - broker_api.py              — BrokerAPI の Protocol / データモデル / ファクトリ
    - broker_factory.py          — Settings に基づくクライアント生成
    - kabu_client.py             — kabuステーション REST / WebSocket 実装
    - mock_client.py             — テスト用 MockBrokerClient
    - order_record.py            — OrderRecord（状態遷移ロジック）
    - order_repository.py        — SQLite 永続化層（orders テーブル）
    - order_manager.py           — 上位の発注フロー（create/send/sync/cancel）
    - execution_engine.py        — セッション駆動の ExecutionEngine
    - reconciler.py              — 起動時のリコンシリエーション（OrderSent 照合）
    - risk_manager.py            — Gate1/2/3 の実装（レート制限・CB・ドローダウン等）
    - ...（他に order_* / risk* など）

  - data/
    - calendar_management.py     — マーケットカレンダー管理（DuckDB / J-Quants 連携）
    - news_collector.py          — RSS ニュース収集（defusedxml, SSRF 対策 等）
    - ...（jquants_client などが参照される）

  - monitoring/ （監視関連モジュール、例: monitoring_db.py, system_monitor.py）

- config/
  - system_config.yaml
  - data_config.yaml
  - strategy_config.yaml
  - risk_config.yaml
  - execution_config.yaml
  - monitoring_config.yaml
  （上記 YAML は config_setup / validate_config で期待される。存在しない場合は警告）

- data/
  - （デフォルトで DUCKDB / SQLite / PID / flag ファイルがここに作られる想定）

---

## 開発 / テストに関するヒント

- unit テストを書く際は MockBrokerClient を活用すると kabuステーションが不要でテスト可能です。
- Settings の自動 .env 読み込みを無効化したいテストでは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- SQLite / DuckDB はファイルベースなので CI では一時ディレクトリを使用するとクリーンです。

---

## ライセンス / バージョン

パッケージバージョン: 0.1.0（src/kabusys/__init__.py）  
ライセンス情報はリポジトリのルートに配置してください（本 README には含めていません）。

---

以上。必要であれば README に含める具体的な .env のテンプレート、requirements.txt の候補、実行例（ログ出力例や典型的なワークフロー）を追加で生成できます。どの情報を拡張しますか？