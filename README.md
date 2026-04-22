# KabuSys

日本株自動売買システム KabuSys のリポジトリ用 README

---

## プロジェクト概要

KabuSys は日本株向けの自動売買フレームワークです。  
主に以下を提供します：

- シグナルに基づく発注エンジン（ExecutionEngine）
- ブローカークライアントの抽象化（kabuステーション API / モック）
- 注文状態管理・永続化（SQLite）
- 起動時のリコンシリエーション（再同期）
- システム監視用プロセス（監視データは SQLite / DuckDB に記録）
- .env ベースの環境設定ウィザード・検証ツール

開発/ペーパートレード環境向けに MockBrokerClient を用意しており、kabuステーションがなくてもローカルで動作確認できます。

---

## 主な機能

- 環境設定ウィザード（.env を対話的に生成 / 更新）
- 起動前の設定検証ツール（env / config/*.yaml の存在・基本整合性チェック）
- 実際の発注フロー（OrderManager / ExecutionEngine）
  - 発注→永続化→ブローカー送信→状態同期（クラッシュ安全性を考慮した2相的な更新）
  - 3段階のリスクガード（Gate1: シグナル、Gate2: レート/CB、Gate3: ドローダウン監視）
- リコンシリエーション（OrderSent の不確定注文をブローカーと突合）
- モニタリング用ポーリングプロセス（SystemMonitor：定期ログ・メトリクス収集）
- DuckDB を用いたシグナル / カレンダー / ニュース等のデータ処理
- テスト・開発用モック（MockBrokerClient）で即座に挙動確認可能

---

## 前提 / 必要な依存関係

推奨 Python バージョン: 3.9+

主な依存パッケージ（抜粋）:

- duckdb
- httpx
- websocket-client
- defusedxml
- PyYAML（config 検証を有効にしたい場合）
- （標準モジュール）sqlite3, logging, threading, etc.

インストールは仮想環境を作成してから行ってください。

例（requirements.txt がある場合）:
```
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

requirements.txt がない場合は最低限:
```
pip install duckdb httpx websocket-client defusedxml PyYAML
```

---

## セットアップ手順

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo-root>
   ```

2. 仮想環境作成・有効化（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate
   ```

3. 依存ライブラリをインストール
   ```
   pip install duckdb httpx websocket-client defusedxml PyYAML
   ```

4. .env を作成（対話式ウィザードを推奨）
   ```
   python -m kabusys.config_setup
   ```
   ウィザードは J-Quants トークンや kabu API パスワード等の重要な値を入力して .env を生成します。

5. 設定検証
   ```
   python -m kabusys.validate_config
   # 警告もエラーとして扱う（厳密モード）
   python -m kabusys.validate_config --strict
   ```

---

## 環境変数（主要）

必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

主な任意 / その他:
- KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
- DUCKDB_PATH — デフォルト: data/kabusys.duckdb
- SQLITE_PATH — デフォルト: data/monitoring.db
- LOG_LEVEL — DEBUG | INFO | WARNING | ERROR | CRITICAL（デフォルト: INFO）
- KABU_API_BASE_URL — kabuステーションのベース URL（開発時に変更する）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID — 本番のアラート通知に使用
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒）

注意:
- .env と .env.local は自動でロードされます（OS 環境変数が優先）。
- 自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

サンプル（.env の主要項目）
```
JQUANTS_REFRESH_TOKEN=your_refresh_token_here
KABU_API_PASSWORD=your_kabu_password_here
KABU_API_BASE_URL=http://localhost:18080/kabusapi
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
KABUSYS_ENV=development
LOG_LEVEL=INFO
KILL_FLAG_CLEAR_ON_START=0
```

---

## 使い方（ランタイムの主要コマンド）

- 環境設定ウィザード（.env を作る）
  ```
  python -m kabusys.config_setup
  ```

- 設定検証（起動前チェック）
  ```
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```
  exit code:
  - 0: OK（エラーなし、警告なしまたは許容）
  - 1: エラーあり、または --strict で警告がある場合

- 実行エンジン（発注プロセス）を起動
  ```
  python -m kabusys.run_execution
  ```
  - KABUSYS_ENV が `paper_trading` の場合、MockBrokerClient を使用し、paper_trading 用 SQLite（PAPER_TRADING_SQLITE_PATH）に記録します。
  - 起動中に `data/stop_requested.flag` を作成すると安全に停止します。
  - PID は data/execution.pid（デフォルト）に書き出されます。
  - kill.flag（settings.kill_flag_path）により起動拒否や即時 Kill Switch が動作します。

- 監視プロセスを起動（SystemMonitor ポーリング）
  ```
  python -m kabusys.run_monitoring
  ```
  - デフォルトのポーリング間隔は 60 秒。環境変数 MONITOR_POLL_INTERVAL で上書き可能。
  - 監視は KABUSYS_ENV にかかわらず本番 sqlite_path を使用します（監視データは統一されます）。

---

## 動作上の注意点 / 運用メモ

- 本番モード（KABUSYS_ENV=live）を使う場合は LINE 通知や各種キーの設定を必ず確認してください。validate_config の live 用ガードも参照。
- kill.flag（KILL_FLAG_CLEAR_ON_START） の挙動:
  - 起動時に kill.flag が存在する場合、KILL_FLAG_CLEAR_ON_START=1 ならクリアして起動、0 なら起動拒否します。
- 発注フローはクラッシュ安全性を考慮しており、OrderSent の途中でクラッシュした場合でもリコンシリエーションで復旧できるよう設計されています。
- Paper trading と本番 DB は分離されます（paper_trading 用 SQLite を使用）。

---

## ディレクトリ構成（主要ファイル）

リポジトリの主要なディレクトリ / ファイル（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数読み込み / Settings クラス
  - config_setup.py          — .env 対話ウィザード
  - validate_config.py       — 起動前設定検証 CLI
  - run_execution.py         — 発注エンジン起動スクリプト
  - run_monitoring.py        — 監視プロセス起動スクリプト
  - execution/
    - broker_api.py          — Broker API の Protocol / データモデル / ファクトリ
    - broker_factory.py      — Settings に応じたクライアント作成
    - kabu_client.py         — KabuStation REST クライアント
    - mock_client.py         — テスト用 MockBrokerClient
    - order_record.py        — 注文状態モデルと状態遷移
    - order_repository.py    — SQLite 永続化レイヤー（orders テーブル）
    - order_manager.py       — 発注の上位 API（作成・送信・同期・キャンセル）
    - reconciler.py          — 起動時リコンシリエーション
    - execution_engine.py    — ExecutionEngine（シグナル処理・WS ドレイン等）
    - risk_manager.py        — 3段階リスクガード
  - data/
    - calendar_management.py — マーケットカレンダー管理（DuckDB）
    - news_collector.py      — RSS ニュース取得・前処理
  - monitoring/
    - monitoring_db.py       — 監視DB 初期化・ログ書き込み
    - system_monitor.py      — システム監視ロジック
  - utils/
    - logging_setup.py       — ロギング初期化
    - process_priority.py    — プロセス優先度設定

（上記は抜粋です。細かい実装は各モジュールを参照してください。）

---

## 開発者向けメモ

- 設定ファイル（config/*.yaml）が必要な場合、validate_config は PyYAML がインストールされていればパースして検証します。存在しないファイルは警告となり、scripts/generate_config.py の利用を案内します（プロジェクト内にある場合）。
- ブローカークライアントは Protocol によって抽象化されているため、実装の差し替えが容易です。create_broker_api(mock=True|False) を使用して切替えます。
- ExecutionEngine の挙動テストはモッククライアント（MockBrokerClient）を使うと安全です。
- DB 初期化関数（init_orders_db / init_monitoring_db 等）を起動前に呼び出してスキーマを作成してください（run_* スクリプト内でも冪等に初期化しています）。

---

## 参考 / 次のステップ

- .env を作成したらまず `python -m kabusys.validate_config` で検証してください。
- 開発時は KABUSYS_ENV=development または paper_trading を使用してください（live は注意深く）。
- 実運用時は監視・アラート（LINE 等）を十分に設定し、kill flag の運用手順を明確にしてください。

---

ライセンスや貢献ガイドライン等がある場合はリポジトリのルートにある LICENSE / CONTRIBUTING を参照してください。

何か追加したい節（例: デプロイ手順、CI 設定、より詳しい設定例など）があれば教えてください。README を拡張して反映します。