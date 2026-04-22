# KabuSys

日本株自動売買システムの軽量コア。  
このリポジトリは発注エンジン、モニタ、設定管理、データ処理の主要コンポーネントを含むモジュール群を提供します。

> バージョン: 0.1.0（src/kabusys/__init__.py の __version__ を参照）

---

## プロジェクト概要

KabuSys は以下の責務を持つモジュールで構成される自動売買基盤のコアです。

- 環境変数 / .env 管理（自動ロード・ウィザード）
- 起動前設定検証 CLI
- 発注エンジン（ExecutionEngine） — シグナル駆動の発注フロー、リスクガード、リコンシリエーション
- ブローカー API 抽象（KabuStation 実装 & Mock クライアント）
- 注文永続化（SQLite）
- 監視（SystemMonitor 用ループ）
- データ関連ユーティリティ（カレンダー管理、ニュース収集など）

設計方針として、DB 操作とビジネスロジックを分離し、クラッシュ安全性（段階的永続化）や各種リスクガード（3段階）を組み込んでいます。

---

## 主な機能一覧

- .env ウィザード（対話式で .env を作成・更新）
  - `python -m kabusys.config_setup`
- 設定検証 CLI（.env と config/*.yaml の存在・妥当性チェック）
  - `python -m kabusys.validate_config [--strict]`
- 実行エンジン実行スクリプト
  - `python -m kabusys.run_execution`
  - KABUSYS_ENV に応じて MockBrokerClient を使用（paper_trading / development）、live は未実装
- 監視ループ実行スクリプト
  - `python -m kabusys.run_monitoring`
  - ポーリング間隔は MONITOR_POLL_INTERVAL で上書き可能（デフォルト 60 秒）
- Broker API 抽象と実装
  - `kabu_client.py`（kabu station REST）
  - `mock_client.py`（テスト用）
- 注文状態管理（OrderRecord）、状態遷移の検証
- 注文永続化（SQLite）：orders テーブル定義・インデックス、ユニーク制約
- リスク管理（Gate 1/2/3）：
  - Gate1: シグナルレベル（余力 / 重複 / ポジション上限）
  - Gate2: エグゼキューション（レートリミット / サーキットブレーカー）
  - Gate3: ドローダウン監視（約定後）
- リコンシリエーション（起動時の OrderSent 状態照合・ポジション差分検出）
- データユーティリティ（マーケットカレンダー管理、RSS ニュース収集など）

---

## セットアップ手順

1. Python 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate (Windows: .venv\Scripts\activate)

2. 依存パッケージのインストール（例）
   - pip install duckdb httpx websocket-client PyYAML defusedxml

   ※ 他に logging 等標準ライブラリを使用。必要に応じてパッケージを追加してください。

3. プロジェクトルートに `.env` を作成するか、ウィザードを使って生成します（推奨）
   - python -m kabusys.config_setup
   - ウィザードは既存の .env を読み込めます。生成後は .env を Git にコミットしないでください。

4. 設定の検証
   - python -m kabusys.validate_config
   - 警告もエラー扱いにする場合:
     - python -m kabusys.validate_config --strict

5. データディレクトリの準備
   - デフォルトの DB パスは `data/kabusys.duckdb`（DuckDB） と `data/monitoring.db`（SQLite）
   - 必要なら .env で `DUCKDB_PATH` / `SQLITE_PATH` を指定してください

---

## 環境変数（重要なキー）

必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

よく使う任意 / デフォルト:
- KABUSYS_ENV (development / paper_trading / live) — デフォルト: development
  - paper_trading: MockBrokerClient を使う（実際の発注は行わない）
  - live: 本番（注意: Live broker client は未実装の箇所があります）
- DUCKDB_PATH (default: data/kabusys.duckdb)
- SQLITE_PATH (default: data/monitoring.db)
- LOG_LEVEL (DEBUG / INFO / WARNING / ERROR / CRITICAL) — default INFO
- KABU_API_BASE_URL (default: http://localhost:18080/kabusapi)
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（通知設定）
- KILL_FLAG_CLEAR_ON_START (0/1) — 起動時の kill.flag 自動クリア（本番は 0 推奨）
- MONITOR_POLL_INTERVAL（監視ポーリング間隔、秒。run_monitoring 用）

自動ロード:
- プロジェクトルート（.git または pyproject.toml があるディレクトリ）を検出し、優先順に:
  1. OS 環境変数
  2. .env.local （存在すれば上書き）
  3. .env
- 自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト用）。

注意:
- .env は機密情報を含むため、絶対に Git にコミットしないでください。

---

## 使い方（主要コマンド）

- 環境設定ウィザード（対話式）
  - python -m kabusys.config_setup
  - 保存後に `python -m kabusys.validate_config` を推奨

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告も失敗と扱い exit(1) で終了

- 発注エンジン起動（本番セッション用）
  - python -m kabusys.run_execution
  - 注意: 実際のブローカー連携は KABUSYS_ENV に依存（paper_trading/development は Mock）

- 監視ループ起動
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可能

停止・フラグ:
- 停止要求はプロジェクトルートの `data/stop_requested.flag` ファイルの作成で検出されます（run_execution / run_monitoring が確認）。
- kill スイッチは `KILL_FLAG_PATH`（デフォルト `data/kill.flag`）で管理されます。起動時に kill.flag が存在すると原則起動を拒否します（KILL_FLAG_CLEAR_ON_START=1 の場合は自動クリアして起動）。

ログ:
- 各スクリプトは logging の設定を行います（app_name による識別）。LOG_LEVEL で制御可能。

Paper trading 動作（開発用）:
- KABUSYS_ENV=paper_trading の場合、MockBrokerClient を利用し DB は `PAPER_TRADING_SQLITE_PATH`（デフォルト: data/paper_trading.db）に分離されます。

---

## ディレクトリ構成（主要ファイル）

（以下は src/kabusys 以下の主なファイル／モジュール）

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数自動ロード / Settings クラス
  - config_setup.py           — .env 対話式ウィザード
  - validate_config.py        — 起動前設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — SystemMonitor ポーリング起動スクリプト
  - execution/                — 発注関連モジュール
    - __init__.py
    - broker_api.py           — Broker API の Protocol / データモデル / ファクトリ
    - kabu_client.py          — kabu station REST API 実装
    - mock_client.py          — テスト用 MockBrokerClient
    - broker_factory.py       — Settings に基づくクライアント生成
    - order_record.py         — OrderRecord（状態遷移ロジック）
    - order_repository.py     — SQLite 永続化層（orders テーブル）
    - order_manager.py        — 発注フロー（create/send/sync/cancel）
    - execution_engine.py     — ExecutionEngine（シグナル処理 + push drain）
    - reconciler.py           — リコンシリエーション（OrderSent 照合・ポジション差分）
    - risk_manager.py         — 3段階リスクガード
  - data/                     — データ処理関連（calendar/news など）
    - calendar_management.py  — マーケットカレンダー管理（DuckDB）
    - news_collector.py       — RSS ニュース収集（安全対策あり）
    - jquants_client.py       — （参照される想定）
  - monitoring/               — 監視関連（監視DB 初期化、SystemMonitor 等）
    - monitoring_db.py       — 監視 DB 初期化 / ログ
    - system_monitor.py      — SystemMonitor 実装
  - utils/                    — ユーティリティ（logging_setup, process_priority 等）
    - logging_setup.py
    - process_priority.py

※ 実際のファイル構成はリポジトリの完全なツリーを参照してください。上記は主要モジュールの一覧です。

---

## .env の例（抜粋）

以下は .env の一部例（ウィザードで生成される内容に準拠）:

JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here
KABU_API_PASSWORD=your_kabu_api_password_here
KABU_API_BASE_URL=http://localhost:18080/kabusapi
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
KABUSYS_ENV=development
LOG_LEVEL=INFO
KILL_FLAG_CLEAR_ON_START=0

必須値は JQUANTS_REFRESH_TOKEN と KABU_API_PASSWORD です。validate_config で未設定を検出します。

---

## 運用上の注意・ベストプラクティス

- .env に秘密情報を含めるため、絶対に VCS にコミットしないでください（config_setup.py も同様に注意喚起あり）。
- 本番運用（KABUSYS_ENV=live）に切り替える際は警告が多く出ます。LINE 通知等のアラート設定が必須に近いです。
- live クライアントの実装状態を確認してください（broker_factory.py は live を NotImplementedError にしている箇所があります）。
- DB パスの親ディレクトリが存在しない場合は起動時に自動作成される場合がありますが、権限等に注意してください。
- 停止は `data/stop_requested.flag` を作成する方法などで行えます。kill.flag の残留がある場合は起動が拒否されます（KILL_FLAG_CLEAR_ON_START の設定で挙動を変更可能）。

---

## 開発者向けメモ

- Order のクラッシュ耐性を考慮して、OrderSent に遷移してから broker 呼び出しを行う等の 2 相永続化パターンを採用しています（OrderManager の send_order を参照）。
- リコンシリエーションは起動時に未決注文を broker と照合して状態回復を行います（Reconciler）。
- カレンダー関連は DuckDB を利用し、DB が不足する場合は曜日ベースのフォールバックを行います。
- news_collector は SSRF や XML パース攻撃対策（defusedxml 等）を組み込んでいます。

---

問題報告・貢献
- バグや改善提案は issue を立ててください。Pull Request は歓迎します。
- 大きな設計変更（特に本番ブローカークライアント周り）は事前に Issue で議論してください。

---

以上。必要であれば README に追加したい「設定例テンプレート」や「運用チェックリスト」などを追記します。どの情報を詳細化しますか？