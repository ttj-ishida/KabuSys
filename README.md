# KabuSys

日本株向け自動売買システム（ミニマム実装）  
このリポジトリは、発注エンジン、監視・リコンシリエーション、データ処理ユーティリティを含むモジュール群を提供します。実際の証券会社接続はモックで動作可能な設計になっており、ペーパートレード／本番切替や各種安全ガードが組み込まれています。

## 主な特徴
- 環境変数ベースの設定管理（`.env`, `.env.local` 自動ロード）
- 対話式の環境設定ウィザード（`.env` 自動生成）
- 起動前に設定を検証する CLI（警告・エラー検出）
- ExecutionEngine：シグナルプル型の発注エンジン（発注／キャンセル／リコンシリエーション）
- Mock ブローカー（ペーパートレード／テスト用）
- RiskManager による 3 段階リスクガード（Gate1/2/3、サーキットブレーカー、レート制限、ドローダウン監視）
- SystemMonitor ベースの監視プロセス（定期ポーリング）
- データ処理機能（マーケットカレンダー管理、ニュース収集 etc.）

## 主要コマンド・スクリプト
- 環境ウィザード（.env 作成）
  - `python -m kabusys.config_setup`
- 設定検証
  - `python -m kabusys.validate_config`  
    - `--strict` を付けると警告も FAIL 扱いして exit code 1 を返します
- 監視プロセス起動
  - `python -m kabusys.run_monitoring`
    - 環境変数 `MONITOR_POLL_INTERVAL`（秒）でポーリング間隔を上書き可（デフォルト 60）
- エンジン起動（実行）
  - `python -m kabusys.run_execution`
    - `KABUSYS_ENV=paper_trading` で Mock ブローカーを使用し、paper_trading 用 SQLite に結果を保存

## セットアップ手順（ローカル開発向け）
前提：Python 3.10+（型注釈の構文を使用）、pip

1. リポジトリをクローンし、作業ディレクトリに移動
2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate もしくは .venv\Scripts\activate
3. 依存パッケージをインストール（代表例）
   - pip install duckdb httpx websocket-client defusedxml
   - PyYAML があると YAML 構成ファイルのパース検証が有効になります：pip install pyyaml
   - 実行環境によっては追加のパッケージが必要です（例: sqlite3 は標準ライブラリ）
4. .env を作成
   - 対話式ウィザード：`python -m kabusys.config_setup`
   - もしくは `.env.example` を参考に `.env` を作成
5. 設定検証（起動前チェック）
   - `python -m kabusys.validate_config`
   - 問題があればログに WARNING/ERROR が出力されます
6. 実行
   - 監視: `python -m kabusys.run_monitoring`
   - エンジン: `python -m kabusys.run_execution`

注意：自動で `.env` を読み込む仕組みが組み込まれており、優先順位は OS 環境変数 > `.env.local` > `.env` です。自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

## 環境変数（主なもの）
必須（起動前に設定必須）
- JQUANTS_REFRESH_TOKEN — J-Quants API 用リフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API パスワード

任意 / 推奨
- KABUSYS_ENV — 実行環境。`development` / `paper_trading` / `live`（デフォルト: development）
  - `paper_trading`：Mock ブローカーを用いたペーパートレード
  - `live`：本番（設定に注意）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視 DB（デフォルト: data/monitoring.db）
- LOG_LEVEL — `DEBUG`/`INFO`/`WARNING`/`ERROR`/`CRITICAL`（デフォルト: INFO）
- KABU_API_BASE_URL — kabu station のベース URL（デフォルト: http://localhost:18080/kabusapi）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID — 本番通知用（任意）
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング秒数（デフォルト 60）

.env 自動読み込みの仕様
- プロジェクトルート（.git または pyproject.toml があるディレクトリ）を探し、`.env` と `.env.local` をロードします
- OS 環境変数は保護（上書き不可）、`.env.local` は `.env` を上書きできます
- 自動ロードを無効にする: `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`

サンプル (.env の一部)
```
JQUANTS_REFRESH_TOKEN=your_jquants_token_here
KABU_API_PASSWORD=your_kabu_password_here
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
LOG_LEVEL=INFO
KILL_FLAG_CLEAR_ON_START=0
LINE_CHANNEL_ACCESS_TOKEN=
LINE_USER_ID=
```

## 使い方（ワークフロー例）
1. .env を生成（対話式）
   - `python -m kabusys.config_setup`
2. 設定検証
   - `python -m kabusys.validate_config`
   - 問題がある場合は修正して再検証。CI 等では `--strict` を使うと警告も失敗扱いになります。
3. 監視プロセスを別プロセスで起動（常駐）
   - `python -m kabusys.run_monitoring`
4. 発注エンジンを起動
   - `python -m kabusys.run_execution`
   - `KABUSYS_ENV=paper_trading`（または development）で Mock ブローカーが使われます

運用上の注意
- 本番（KABUSYS_ENV=live）では LINE 通知設定や KILL_SWITCH 設定等を必ず確認してください。validate_config は `live` 時に追加の警告を表示します。
- 起動時に `kill.flag` が存在すると起動を拒否します（`KILL_FLAG_CLEAR_ON_START=1` の場合は自動クリアして起動）。

## ディレクトリ構成（主要ファイル）
（src/kabusys 以下を想定）

- src/
  - kabusys/
    - __init__.py
    - config.py — 環境変数読み込み / Settings クラス
    - config_setup.py — 対話式 .env 作成ウィザード
    - validate_config.py — 起動前の設定検証 CLI
    - run_execution.py — ExecutionEngine 起動スクリプト
    - run_monitoring.py — SystemMonitor ポーリング起動スクリプト
    - execution/
      - broker_api.py — Broker API の Protocol／データモデル／ファクトリ
      - kabu_client.py — kabu station REST クライアント実装（未実装の部分あり）
      - mock_client.py — テスト／ペーパートレード用モック
      - broker_factory.py — Settings に応じたブローカー作成ファクトリ
      - order_record.py — 注文状態モデル / 状態遷移
      - order_repository.py — SQLite 永続化層
      - order_manager.py — 発注ワークフロー（create/send/sync/cancel）
      - execution_engine.py — 発注エンジンのメインロジック
      - reconciler.py — 起動時の注文・ポジション照合（リコンシリエーション）
      - risk_manager.py — Gate1/2/3 を実装するリスク管理
      - ...（他の execution 関連モジュール）
    - data/
      - calendar_management.py — マーケットカレンダー管理
      - news_collector.py — RSS ニュース収集（SSRF 対策等を実装）
      - jquants_client.py (想定) — J-Quants API クライアント（参照あり）
    - monitoring/
      - monitoring_db.py — 監視 DB 初期化 / ログ記録（参照あり）
      - system_monitor.py — システムリソースのポーリング監視（参照あり）
    - utils/
      - logging_setup.py — ログ設定
      - process_priority.py — プロセス優先度設定ユーティリティ
    - config/（リポジトリルート）
      - system_config.yaml
      - data_config.yaml
      - strategy_config.yaml
      - risk_config.yaml
      - execution_config.yaml
      - monitoring_config.yaml
      - ...（YAML 設定ファイル。validate_config で存在・パース検証する）

注: 一部モジュール（例: jquants_client, monitoring_db, system_monitor, utils/*）は README の説明中で参照されています。完全な実行にはそれらの実装と依存パッケージが必要です。

## 開発・テストのヒント
- MockBrokerClient により、kabuステーションを起動せずに発注・約定フローをテストできます（`KABUSYS_ENV=paper_trading`）。
- Reconciler は再起動時の OrderSent レコードを突合して状態を回復するため、発注処理のクラッシュ耐性テストに有用です。
- news_collector.py は SSRF や XML 攻撃対策（defusedxml、ホスト判定、最大受信バイト数）を含んでいるため、外部フィード連携のユースケースに適しています。

----------------------------------------------------
この README はコードベース（src/kabusys 内のドキュメント文字列）を基に作成しています。実際に運用する場合は、環境ごとの設定（DB パス、KABUSYS_ENV、通知設定等）を必ず確認し、まずはペーパートレード環境で十分に検証してください。