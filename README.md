# KabuSys

KabuSys は日本株自動売買のためのシンプルでモジュール化されたフレームワークです。本リポジトリは設定読み込み、発注エンジン、リスクガード、ブローカー抽象化、監視/リコンシリエーション、データ収集（カレンダー／ニュース）などを含みます。実運用（live）・ペーパートレード（paper_trading）・開発（development）を想定した設計になっています。

---

## プロジェクト概要

- メイン用途: シグナルに基づく株式発注を行う ExecutionEngine と、それを支えるモジュール群。
- 設計方針:
  - ブローカークライアントは抽象化（Protocol）されており、Mock 実装で開発・テスト可能。
  - 発注は state machine（OrderRecord）で扱い、SQLite に永続化してクラッシュ耐性を確保。
  - 3 段階のリスクガード（Gate1: シグナル、Gate2: 実行、Gate3: ドローダウン）を備える。
  - 起動時に設定検証ツール・対話式 .env ウィザードを提供。
  - 監視ループは別プロセスとして動作し、停止フラグや監視 DB を扱う。

---

## 主な機能一覧

- 環境設定管理
  - .env / .env.local の自動読み込み（必要に応じて無効化可能）
  - 対話式ウィザードで .env を作成・更新（kabusys.config_setup）
  - 設定検証 CLI（kabusys.validate_config）

- 発注エンジン / 実行層
  - ExecutionEngine: シグナル読み込み → 発注（Signal Queue Pull 型） + WebSocket push ドレイン
  - OrderManager / OrderRepository / OrderRecord による注文の状態管理と永続化（SQLite）
  - Broker API 抽象化（BrokerAPIProtocol）とファクトリ（Mock / KabuStation）

- リスク管理
  - RiskManager: Gate1（余力・重複・ポジション上限）、Gate2（レート制限・サーキットブレーカー）、Gate3（ドローダウン監視）

- リコンシリエーション（Reconciler）
  - 起動時に OrderSent 状態の注文をブローカーと突合して同期
  - ポジション差分の検出とログ出力

- ブローカー実装
  - MockBrokerClient: テスト・開発用（fill_mode: instant/partial/never/reject）
  - KabuStationClient: kabuステーション REST API クライアント（httpx/websocket を使用）

- 監視
  - run_monitoring: SystemMonitor のポーリングループ（監視用 SQLite を使用）

- データ関連
  - カレンダー管理（J-Quants 連携想定）: 営業日・SQ判定、次営業日の計算等
  - ニュース収集（RSS から raw_news への保存。SSRF対策・XML安全対策を考慮）

---

## セットアップ手順（開発向け）

1. リポジトリをクローンして作業ディレクトリへ移動
   - 例: git clone ... && cd <repo>

2. Python 環境を用意（推奨: venv）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - requirements.txt がない場合は主要依存を手動でインストール:
     - pip install duckdb httpx websocket-client PyYAML defusedxml
   - （SQLite は標準ライブラリに含まれます）

4. .env の作成
   - 対話式ウィザードを使うのが簡単です:
     - python -m kabusys.config_setup
   - もしくはリポジトリの .env.example を参考に手動で作成してください。
   - .env は絶対に Git にコミットしないでください。

5. 設定検証
   - python -m kabusys.validate_config
   - 警告もエラー扱いにする場合:
     - python -m kabusys.validate_config --strict

6. データディレクトリ作成（必要に応じて）
   - デフォルトで使用されるパス:
     - DUCKDB_PATH: data/kabusys.duckdb
     - SQLITE_PATH: data/monitoring.db
   - これらの親ディレクトリが無ければ自動作成されますが、事前に作成しておくと便利です:
     - mkdir -p data

備考:
- 自動で .env を読み込む際、既存 OS 環境変数は保護されます。自動ロードを無効化したい場合は環境変数をセット:
  - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

---

## 必要な環境変数（主なもの）

必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

任意（よく使うもの）:
- KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
- DUCKDB_PATH — デフォルト: data/kabusys.duckdb
- SQLITE_PATH — デフォルト: data/monitoring.db
- LOG_LEVEL — DEBUG|INFO|WARNING|ERROR|CRITICAL（デフォルト: INFO）
- KABU_API_BASE_URL — kabu station の base URL（デフォルト: http://localhost:18080/kabusapi）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — 本番でのアラート用

サンプル .env（参考）
JQUANTS_REFRESH_TOKEN=your_token_here
KABU_API_PASSWORD=your_password_here
KABU_API_BASE_URL=http://localhost:18080/kabusapi
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
KABUSYS_ENV=development
LOG_LEVEL=INFO
KILL_FLAG_CLEAR_ON_START=0

---

## 使い方（主要コマンド）

- 環境設定ウィザード（.env を作成／更新）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 厳密モード（警告も失敗扱い）:
    - python -m kabusys.validate_config --strict

- 実行エンジンを起動（本番セッション想定）
  - python -m kabusys.run_execution
  - 実行時は KABUSYS_ENV に応じて mock ブローカーを使用（paper_trading / development）、
    live は未実装（例外を出します）。

- 監視ループを起動
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔秒数を上書き可能（デフォルト 60 秒）。

- 注意:
  - stop フラグ: data/stop_requested.flag を作成すると監視／実行ループが検知して停止します。
  - kill フラグ: data/kill.flag により ExecutionEngine は起動を拒否（KILL_FLAG_CLEAR_ON_START=1 の場合はクリアして起動）。

---

## 主要ファイルとディレクトリ構成

（src/kabusys 以下の主要ファイルを抜粋）

- src/kabusys/__init__.py
  - パッケージ定義。バージョン情報など。

- src/kabusys/config.py
  - 環境変数の自動読み込み、Settings クラス（アプリケーション設定）の定義。
  - .env のパースロジックを持つ。

- src/kabusys/config_setup.py
  - 対話式ウィザードで .env を生成／更新する CLI。

- src/kabusys/validate_config.py
  - 起動前に .env と config/*.yaml の基本チェックを行う CLI。

- src/kabusys/run_execution.py
  - ExecutionEngine の起動スクリプト（プロセス優先度設定、DB 接続、スレッド管理など）。

- src/kabusys/run_monitoring.py
  - SystemMonitor のポーリングループ起動スクリプト。

- src/kabusys/execution/
  - broker_api.py           — Broker API の Protocol / データモデル / ファクトリ
  - kabu_client.py          — KabuStationClient（REST + WebSocket 実装）
  - mock_client.py          — MockBrokerClient（テスト用）
  - broker_factory.py       — Settings に基づきブローカークライアントを生成
  - order_record.py         — 注文の状態遷移モデル（状態機械）
  - order_repository.py     — SQLite 永続化層（orders テーブル）
  - order_manager.py        — OrderManager（発注フロー：create/send/sync/cancel）
  - execution_engine.py     — ExecutionEngine（シグナル処理・push ドレイン）
  - reconciler.py           — 起動時のリコンシリエーション（OrderSent 照合、ポジション差分）
  - risk_manager.py         — RiskManager（Gate1/2/3）
  - order_manager.py        — 注文 API を提供する上位ラッパ
  - その他: order_record 等

- src/kabusys/monitoring/
  - monitoring_db.py        — 監視用 SQLite テーブル初期化・ログ API
  - system_monitor.py       — システムメトリクス等の収集（未記載詳細はコード参照）

- src/kabusys/data/
  - calendar_management.py  — 市場カレンダー管理、営業日計算
  - news_collector.py       — RSS からニュースを収集・前処理して保存
  - jquants_client.py       — J-Quants クライアント（参照実装、fetch/save など）

- src/kabusys/utils/
  - logging_setup.py        — ログの共通設定
  - process_priority.py     — プロセス優先度設定ユーティリティ

- config/
  - system_config.yaml, data_config.yaml, strategy_config.yaml, risk_config.yaml, execution_config.yaml, monitoring_config.yaml
  - （これらの YAML ファイルが存在すると validate_config でパース検証されます）
  - 注意: PyYAML が未インストールだと内容検証はスキップされます（validate_config の警告参照）。

---

## 運用メモ / 注意点

- .env は秘匿情報を含むため Git 管理対象から除外してください。
- KABUSYS_ENV=live の場合は本番環境扱いになります。LINE 通知等の設定漏れや KILL_FLAG_CLEAR_ON_START の設定には特に注意してください。
- ExecutionEngine の PID / stop / kill フラグは data ディレクトリ以下のファイルで制御します（PID ファイル、stop_requested.flag、kill.flag）。
- リアルブローカー接続（KabuStationClient）は実環境での扱いに注意。Mock を使って十分にテストしてください。
- config/*.yaml のテンプレート生成スクリプト（scripts/generate_config.py 等）が存在する場合はそれを使って初期ファイルを作成してください（validate_config は存在しないファイルを警告します）。

---

## 開発に関する補足

- 単体テストを追加することが推奨されます（OrderRecord の状態遷移、OrderManager のトランザクション順序、RiskManager の境界ケース等）。
- ブローカー実装を追加する場合は BrokerAPIProtocol に準拠すること。create_broker_api() を通じて切り替え可能にするのが簡便です。
- 実行フローやリコンシリエーションの運用ログは重要です。運用時は LOG_LEVEL の設定と監視周りの設定を適切に行ってください。

---

README の内容はコードベース（src/kabusys）に基づく要約です。より詳しい使い方や設定値の詳細は各モジュールの docstring を参照してください。必要であれば README にサンプル設定ファイルや運用手順（デプロイ、バックアップ、監視ダッシュボード等）を追記できます。ご希望があれば追加します。