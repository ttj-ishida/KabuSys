# KabuSys

日本株自動売買システムのパッケージ（概要ドキュメント）

この README はリポジトリ内の主要な CLI／モジュールに基づいて、セットアップ・実行方法とディレクトリ構成を日本語でまとめたものです。

目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 使い方
  - 環境設定ウィザード（.env）
  - 設定検証
  - Execution（発注エンジン）
  - Monitoring（監視）
  - その他の注意点（停止フラグ / PID / 本番ガード 等）
- 環境変数一覧（主なもの）
- ディレクトリ構成

---

## プロジェクト概要

KabuSys は日本株向けの自動売買システムのコアライブラリ群です。  
主な機能は以下の通り：

- シグナルに基づく発注エンジン（ExecutionEngine）
- ブローカー API クライアント（kabuステーションの実装 + Mock クライアント）
- 注文状態管理（OrderRecord / OrderManager / OrderRepository）
- 起動時リコンシリエーション（Reconciler）
- リスク管理（3段階ガード: Gate1/2/3）
- DuckDB を使ったデータ分析用ストレージ、SQLite を使った監視 DB
- 監視ループ（SystemMonitor）
- .env を対話的に生成するウィザードと設定検証 CLI
- ニュース収集、マーケットカレンダー管理 等の補助モジュール

設計方針として、DB（SQLite / DuckDB）やブローカー呼び出しの分離、クラッシュ耐性（2相永続化やリコンシリエーション）を重視しています。

---

## 機能一覧

- 環境設定ウィザード（対話式）: python -m kabusys.config_setup
- 設定検証 CLI（.env / config/*.yaml の検査）: python -m kabusys.validate_config
- 発注エンジン起動スクリプト: python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading では MockBrokerClient を使用し本番 DB と分離
- 監視ループ起動スクリプト: python -m kabusys.run_monitoring
- ブローカー API 抽象（Protocol）+ 実装
  - MockBrokerClient（fill_mode 等で挙動を変えられる）
  - KabuStationClient（kabuステーション REST / WebSocket）
- 注文永続化（SQLite）とリポジトリ操作（永続化層）
- リスク管理（余力・重複・レート制限・サーキットブレーカー・ドローダウン）
- カレンダー管理（J-Quants ベース）とニュース収集（RSS → raw_news）

---

## セットアップ手順

前提:
- Python 3.10 以上を推奨（typing, dataclass, Path 等を利用）
- システムに sqlite3 は標準搭載。DuckDB は Python パッケージが必要。

1. リポジトリをクローン／展開する
2. 仮想環境を作成して有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 必要なパッケージをインストール
   - 例（プロジェクトに requirements.txt がある場合）:
     - pip install -r requirements.txt
   - ない場合の主な依存例:
     - pip install duckdb httpx websocket-client PyYAML defusedxml
   - 開発インストール:
     - pip install -e .

4. .env を作成
   - 対話ウィザードを使う: python -m kabusys.config_setup
   - 手動で作成する場合は下記の「環境変数一覧」を参照

5. 設定検証（起動前チェック）
   - python -m kabusys.validate_config
   - 警告も失敗扱いにする場合: python -m kabusys.validate_config --strict

---

## 使い方

### 環境設定ウィザード（.env の作成・更新）

- 実行:
  - python -m kabusys.config_setup
- 機能:
  - 対話式で主要な環境変数を入力し .env を生成します。
  - 既存 .env があれば読み込んで既存値を Enter で再利用可能。
  - 生成された .env は Git にコミットしないでください（機密情報を含むため）。

ウィザード完了後、README に表示される次のステップの例:
- python -m kabusys.validate_config で設定検証を実行

### 設定検証 CLI

- 実行:
  - python -m kabusys.validate_config
  - オプション: --strict で警告も失敗（exit code 1）扱い
- 検証内容:
  - 必須環境変数が設定されているか
  - KABUSYS_ENV や LOG_LEVEL の妥当性チェック
  - DB パス（DUCKDB_PATH / SQLITE_PATH）の親ディレクトリ存在チェック
  - config/*.yaml の存在チェックと（PyYAML があれば）パースチェック
  - KABUSYS_ENV=live 時の追加ガード（LINE 通知や kill flag 設定等）

### Execution（発注エンジン）

- 実行:
  - python -m kabusys.run_execution
- ポイント:
  - settings（KABUSYS_ENV）に応じてブローカークライアントを決定:
    - development / paper_trading → MockBrokerClient（paper_fill_mode に従う）
    - live → 現在は NotImplementedError（将来実装）
  - paper_trading モードでは SQLite DB は settings.paper_sqlite_path（デフォルト data/paper_trading.db）を使用して本番 DB と分離
  - 起動時に PID ファイルを data/execution.pid 等に書き込み
  - 停止は stop flag（data/stop_requested.flag）や kill.flag を利用
  - ExecutionEngine はシグナル処理フェーズ（8:50-9:10）と push ドレイン（9:10-15:30）を実行する設計

### Monitoring（監視ループ）

- 実行:
  - python -m kabusys.run_monitoring
- ポイント:
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き（デフォルト 60 秒）
  - 監視は本番 sqlite_path を使用（KABUSYS_ENV にかかわらず）
  - stop flag（data/stop_requested.flag）を検知するとループを終了

### 停止フラグ / PID / Kill Switch

- stop フラグ:
  - _STOP_FLAG = project_root / data / stop_requested.flag
  - 存在すると監視ループ・エンジンがクリーンに停止する
- kill.flag:
  - settings.kill_flag_path（デフォルト data/kill.flag）
  - 存在すると ExecutionEngine は起動を拒否（KILL_FLAG_CLEAR_ON_START=1 の場合は起動時に自動クリア可能）
  - kill_switch() の発動により全 active 注文をキャンセルする処理あり
- PID:
  - 実行時に PID をファイルへ書き込み（settings.pid_file_path）

---

## 環境変数（主なもの）

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants API のリフレッシュトークン（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）

任意 / 推奨（デフォルトあり）:
- KABUSYS_ENV — 実行環境: development / paper_trading / live（デフォルト: development）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite 監視 DB（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード専用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL、デフォルト INFO）
- KABU_API_BASE_URL — kabu station API ベース URL（デフォルト http://localhost:18080/kabusapi）
- LINE_CHANNEL_ACCESS_TOKEN — LINE 通知用アクセストークン（本番では必須推奨）
- LINE_USER_ID — LINE 通知先ユーザー ID（本番では必須推奨）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill flag を自動クリア（0/1、デフォルト 0）
- MONITOR_POLL_INTERVAL — 監視ポーリング間隔（秒、デフォルト 60）
- PID_FILE_PATH — PID ファイルパス（デフォルト data/execution.pid）

自動 .env ロード:
- プロジェクトルート（.git または pyproject.toml）を検出して .env と .env.local を自動読み込みします。
- OS 環境変数が優先され、.env.local は override=True（OS 環境変数を保護）で読み込まれます。
- 自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定

サンプル .env（ウィザード生成時の形式例）
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here
KABU_API_PASSWORD=your_kabu_api_password_here
KABU_API_BASE_URL=http://localhost:18080/kabusapi
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
KABUSYS_ENV=development
LOG_LEVEL=INFO
KILL_FLAG_CLEAR_ON_START=0
LINE_CHANNEL_ACCESS_TOKEN=
LINE_USER_ID=
```

---

## 実行時の開発上のヒント

- テスト・ローカル開発では KABUSYS_ENV=paper_trading を使うと MockBrokerClient が利用され、本番 DB へ影響を与えません。
- MockBrokerClient の fill_mode（instant / partial / never / reject）を PAPER_FILL_MODE で制御できます。（Settings.paper_fill_mode）
- validate_config は PyYAML が入っていれば config/*.yaml のパース検証も行います。未インストールでも警告を出して続行します。
- WebSocket を使った push 受信は websocket-client を使用しています。環境に応じてインストールしてください。
- DuckDB は SQL を使ってシグナルや portfolio_targets 等を参照します。初期スキーマ / データ生成スクリプトは別途用意されているはずです（docs / scripts 等を参照）。

---

## ディレクトリ構成（抜粋）

以下はリポジトリ内の主要ファイル／モジュール（src/kabusys 配下）の抜粋です。

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数読み込み & Settings クラス（自動 .env ロード, require など）
  - config_setup.py          — 対話式 .env ウィザード
  - validate_config.py       — 起動前設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリング起動スクリプト
  - execution/
    - __init__.py
    - broker_api.py          — BrokerAPI の Protocol / データモデル / ファクトリ
    - kabu_client.py         — kabu station 実装（HTTP + WebSocket）
    - mock_client.py         — MockBrokerClient（テスト用）
    - broker_factory.py      — Settings に基づいてクライアント生成
    - order_record.py        — OrderRecord（状態遷移ロジック）
    - order_repository.py    — SQLite 永続化層
    - order_manager.py       — 発注・同期・取消の外向き API
    - execution_engine.py    — ExecutionEngine（シグナル処理 + push drain）
    - reconciler.py          — 起動時のリコンシリエーション処理
    - risk_manager.py        — 3 段階リスクガード
    - ... （その他）
  - data/
    - calendar_management.py — 市場カレンダー管理（DuckDB）
    - news_collector.py      — RSS ニュース収集
    - jquants_client.py      — J-Quants 連携（参照あり）
  - monitoring/
    - monitoring_db.py       — 監視 DB の初期化・ログ
    - system_monitor.py      — 監視ロジック（run_monitoring が呼ぶ）
  - utils/
    - logging_setup.py       — ログ設定ユーティリティ
    - process_priority.py    — プロセス優先度設定ユーティリティ
  - config/
    - system_config.yaml
    - data_config.yaml
    - strategy_config.yaml
    - risk_config.yaml
    - execution_config.yaml
    - monitoring_config.yaml

（注意）config/*.yaml はプロジェクトの設定ファイルです。存在しない場合は validate_config が警告を出します。README内で参照している scripts/generate_config.py 等の補助スクリプトがプロジェクトに含まれている場合はそちらで生成してください。

---

## 最後に（運用上の注意）

- 本システムは実際に資金を動かす可能性があり、特に KABUSYS_ENV=live の設定は慎重に扱ってください。validate_config は live モードでのチェックを強化しますが、最終判断は必ず人が行ってください。
- .env や API パスワード等の機密情報は決して Git にコミットしないでください。
- 本 README はコードベースの抽出に基づくサマリです。実運用のための追加ドキュメント（インストール手順、DB 初期化スクリプト、運用 Runbook 等）を別途整備することを推奨します。

必要であれば、この README を基に「導入手順の具体化」「運用手順（起動・停止・ログ確認）」や「テスト手順」などのセクションを詳細化して作成します。どの部分を詳しく作ればよいか教えてください。