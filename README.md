# KabuSys

日本株自動売買システム（ミニマル実装）

このリポジトリは、KabuStation（ローカル REST/WebSocket サーバ）や J-Quants などを組み合わせた、自動売買のための小規模なフレームワークです。発注フロー、リスクガード、リコンシリエーション、監視、データ収集（カレンダー／ニュース）などの主要コンポーネントを含みます。

---

## 目次

- プロジェクト概要
- 機能一覧
- セットアップ手順
- 使い方
  - .env 作成ウィザード
  - 設定検証
  - 監視プロセス起動
  - 実行エンジン起動
- 主要設定項目（環境変数）
- ディレクトリ構成

---

## プロジェクト概要

KabuSys は以下の責務を持つコンポーネント群で構成されています。

- 発注エンジン（ExecutionEngine）: DuckDB からシグナルを読み、OrderManager を介してブローカー API に発注する。
- ブローカークライアント: 実ブラウザ接続用の KabuStationClient と、テスト用の MockBrokerClient を提供。
- 注文永続化（SQLite）: OrderRepository が注文状態を保持し、クラッシュ耐性のための永続化ロジックを備える。
- リスク管理（RiskManager）: Gate1/2/3 による多段階ガード（余力・重複・レート制限・サーキットブレーカー・ドローダウン）。
- リコンシリエーション（Reconciler）: 起動時に OrderSent 状態の注文をブローカーと突合して状態を回復する。
- 監視（SystemMonitor 用スクリプト）: 稼働状況を定期的に記録するポーリングループ。
- データモジュール: 市場カレンダー管理、ニュース収集など。

---

## 機能一覧

- .env 対話式ウィザードで初期設定を作成/更新（kabu/ J-Quants / DBパス / LINE 通知など）
- .env および config/*.yaml の事前検証ツール（警告／エラー判定、--strict モードあり）
- ExecutionEngine によるシグナル取得 → Gate1/2 チェック → 発注フロー（発注の2相永続化等）
- Mock ブローカーでのペーパートレード（fill_mode: instant / partial / never / reject）
- 起動時リコンシリエーション（OrderSent の照合、ポジション差分検出）
- RiskManager によるトークンバケツ型レート制限とサーキットブレーカー
- DuckDB を利用したシグナル / カレンダー管理、SQLite による監視・注文履歴保存
- ニュース収集（RSS）、URL 正規化、SSRF対策、XML データ保護（defusedxml）

---

## セットアップ手順

1. Python 3.8+ を用意します（型アノテーション・pathlib 等を利用）。
2. 仮想環境を作成・有効化（任意）:
   - python -m venv .venv
   - source .venv/bin/activate (Unix) / .venv\Scripts\activate (Windows)
3. 依存パッケージをインストールします（例）:
   - pip install duckdb httpx websocket-client defusedxml
   - PyYAML は config 検証を有効化するために推奨: pip install pyyaml
   - （必要に応じて他の依存を追加してください）
4. プロジェクトルートに移動し、.env を作成します（下記参照）。自動ロード機能が有効であれば `.env` / `.env.local` が自動的に読み込まれます。

注意:
- SQLite は Python 標準ライブラリの sqlite3 を使用するため追加インストール不要です。
- duckdb は外部パッケージです。インストールを忘れないでください。

---

## 使い方

基本的なワークフローは次の通りです: .env 作成 → 設定検証 → 実行/監視起動

1. .env 作成（対話式ウィザード）
   - 実行:
     - python -m kabusys.config_setup
   - 画面に従って必須値（J-Quants リフレッシュトークン、kabu API パスワードなど）を入力します。
   - ウィザードは既存の .env を読み込み、Enter で既存値を再利用できます。

2. 設定検証
   - 実行:
     - python -m kabusys.validate_config
     - 厳格モード（警告も失敗扱い）: python -m kabusys.validate_config --strict
   - .env の必須環境変数未設定や config/*.yaml の不整合を起動前に検出します。
   - PyYAML がインストールされていない場合は YAML のパース検証をスキップします（警告表示）。

3. 監視プロセス起動
   - 実行:
     - python -m kabusys.run_monitoring
   - 監視ループは SQLite（settings.sqlite_path）と DuckDB（settings.duckdb_path）へ接続します。
   - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で上書き可能（デフォルト 60 秒）。
   - 停止フラグファイル data/stop_requested.flag を作成するとループを終了します。

4. 実行エンジン起動（発注）
   - 実行:
     - python -m kabusys.run_execution
   - KABUSYS_ENV に応じて MockBrokerClient（paper_trading / development）か実ブローカーを使用します。
   - execution は PID ファイルを書き込み、data/execution.pid（デフォルト）を利用します。
   - 実行前に stop flag / kill.flag の状態や KILL_FLAG_CLEAR_ON_START を確認します。

実行中の停止:
- データディレクトリの data/stop_requested.flag を作成すると run_monitoring と run_execution は安全に停止します。
- kill.flag（settings.kill_flag_path）を利用すると ExecutionEngine は全 active 注文をキャンセルして停止します。

---

## 主要設定項目（環境変数）

validate_config と Settings クラスで利用される主要な環境変数（概要）:

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants API 用リフレッシュトークン（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）

任意 / 推奨:
- KABUSYS_ENV — 実行環境: development | paper_trading | live（デフォルト: development）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト: data/monitoring.db）
- LOG_LEVEL — ログレベル（DEBUG / INFO / WARNING / ERROR / CRITICAL、デフォルト: INFO）
- KABU_API_BASE_URL — kabuステーション API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- LINE_CHANNEL_ACCESS_TOKEN — LINE 通知用（本番では設定推奨）
- LINE_USER_ID — LINE 通知先ユーザー ID（本番では設定推奨）
- PAPER_FILL_MODE — ペーパートレード時の fill モード（instant|partial|never|reject、設定は Settings.paper_fill_mode）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード専用 SQLite（デフォルト: data/paper_trading.db）
- PID_FILE_PATH — PID ファイル（default: data/execution.pid）
- KILL_FLAG_PATH — kill flag のパス（default: data/kill.flag）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（0/1、デフォルト: 0）
- MONITOR_POLL_INTERVAL — 監視ループのポーリング間隔（秒、デフォルト 60）

自動 .env ロードの抑止:
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると、config モジュールの自動 .env 読み込みを無効化します（テスト等で利用）。

config ディレクトリの YAML ファイル（検証対象）:
- system_config.yaml
- data_config.yaml
- strategy_config.yaml
- risk_config.yaml
- execution_config.yaml
- monitoring_config.yaml

（これらは validate_config で存在とパースをチェックします。PyYAML が必要です）

---

## ディレクトリ構成

リポジトリの主なファイル・ディレクトリ構成（抜粋）:

- config/                             — YAML 設定ファイル（system/data/strategy/...）
  - system_config.yaml
  - data_config.yaml
  - strategy_config.yaml
  - risk_config.yaml
  - execution_config.yaml
  - monitoring_config.yaml
- data/                               — 実行時データ（DB・フラグ・PID）
  - stop_requested.flag
  - kill.flag
  - kabusys.duckdb (デフォルト path)
  - monitoring.db (デフォルト SQLite)
  - paper_trading.db (ペーパートレード用)
- scripts/                            — （存在する場合）ユーティリティスクリプト（例: generate_config.py）
- src/kabusys/
  - __init__.py
  - config.py                         — 環境変数読み込み・Settings 定義（自動 .env 読み込み）
  - config_setup.py                   — .env 対話式ウィザード
  - validate_config.py                — 起動前の設定検証 CLI
  - run_execution.py                  — ExecutionEngine 起動スクリプト
  - run_monitoring.py                 — SystemMonitor ポーリングループ起動スクリプト
  - execution/
    - broker_api.py                   — BrokerAPIProtocol, データモデル, ファクトリ
    - kabu_client.py                  — KabuStationClient（実 API 実装）
    - mock_client.py                  — MockBrokerClient（テスト用）
    - broker_factory.py               — Settings に基づくクライアント生成
    - order_record.py                 — OrderRecord（状態遷移ロジック）
    - order_repository.py             — SQLite 永続化層
    - order_manager.py                — Order 管理（作成・送信・同期・キャンセル）
    - execution_engine.py             — ExecutionEngine（シグナル処理・push ドレイン）
    - reconciler.py                   — 起動時リコンシリエーション
    - risk_manager.py                 — RiskManager（Gate1/2/3）
  - monitoring/                        — 監視 DB 初期化や SystemMonitor（別ファイル群）
  - data/                              — data 関連（calendar_management.py, news_collector.py, ...）
    - calendar_management.py
    - news_collector.py
  - utils/                             — ロギング・プロセス優先度等ユーティリティ

---

## 追加メモ / 運用上の注意

- 本番環境（KABUSYS_ENV=live）を使用する際は validate_config が追加チェックを行い、LINE 通知設定や kill flag に関する警告を出します。live は慎重に使用してください。
- ExecutionEngine は PID ファイルを作成し、kill.flag による自動クリア設定（KILL_FLAG_CLEAR_ON_START）をサポートしていますが、デフォルトではクリアしません。
- 発注フローはクラッシュ耐性を考慮した設計（OrderSent の 2相永続化、reconciliation による回復）となっています。
- MockBrokerClient により、ネットワークや実ブローカーなしで平常系/異常系テスト（instant/partial/never/reject）が可能です。
- config/*.yaml の雛形を生成するスクリプト（scripts/generate_config.py）への参照がコード内にあります。必要ならこのスクリプトを用いて生成してください。

---

問題や改善提案があれば README を更新します。必要であれば「導入手順（docker / systemd サービス化）」「設定例の .env.example」「テスト手順（ユニットテスト、統合テスト）」の追記も行えます。どの内容を追加したいか教えてください。