# KabuSys

日本株向け自動売買システム（KabuSys）リポジトリの README（日本語）。

このドキュメントは、提供されたソースコードに基づきプロジェクト概要・機能・セットアップ・使い方・ディレクトリ構成をまとめたものです。

---

## プロジェクト概要

KabuSys は、kabuステーション（またはモック）を用いて日本株の自動売買を行うための基盤ライブラリ／実行スクリプト群です。設計上は下記の点を重視しています。

- 安全性（複数のリスクゲート、キルスイッチ、サーキットブレーカー）
- クラッシュ耐性（永続化とリコンシリエーション）
- 開発と本番の分離（paper_trading 用 DB、モックブローカー）
- 運用支援（環境設定ウィザード、設定検証 CLI、監視プロセス）

主要コンポーネント：
- ExecutionEngine：シグナルに基づく発注エンジン
- RiskManager：Gate1〜3 による多段リスクガード
- Broker クライアント：実運用向けの KabuStationClient とテスト用 MockBrokerClient
- Reconciler：再起動後の注文照合／ポジション差分検出
- 設定ユーティリティ：.env ウィザード / 検証
- Data モジュール：マーケットカレンダー、ニュース収集など
- Monitoring：システム監視プロセス

---

## 機能一覧

- 環境設定ウィザード（python -m kabusys.config_setup）
  - 対話式に .env を作成・更新
- 設定検証 CLI（python -m kabusys.validate_config）
  - 必須環境変数、config/*.yaml、パス、環境値の検査
  - --strict オプションで警告をエラー扱いに可能
- 実行エンジン（python -m kabusys.run_execution）
  - シグナル読み取り → Gate1/2 を経て発注
  - WebSocket push ドレイン（broker の push を受信）
  - kill.flag による安全停止と全注文キャンセル
  - paper_trading モードでは MockBroker を使用し DB を分離
- 監視ループ（python -m kabusys.run_monitoring）
  - システムリソース監視、監視DBへのログ記録
  - MONITOR_POLL_INTERVAL で間隔変更可能
- Broker クライアント
  - KabuStationClient（kabuステーション REST + WebSocket）
  - MockBrokerClient（fill_mode による即時/部分/拒否/保留挙動）
- 注文永続化（SQLite）
  - OrderRepository / orders テーブル（冪等性・部分ユニークインデックス等）
- リコンシリエーション（再起動時の OrderSent 照合、ポジション差分検出）
- RiskManager：余力・重複・ポジション上限・レート制限・サーキットブレーカー・ドローダウン監視
- Data モジュール
  - マーケットカレンダー管理（DuckDB）
  - ニュース収集（RSS、正規化、SSRF/XML 防御）

---

## セットアップ手順（ローカル）

前提
- Python 3.10+ 推奨（型ヒントに PEP 604（X|Y）を使用）
- Git, pip 等

1. リポジトリをクローン
   - git clone <repository-url>
   - cd <repository-root>

2. 仮想環境を作成・有効化（任意）
   - python -m venv .venv
   - source .venv/bin/activate  # Unix/macOS
   - .venv\Scripts\activate     # Windows

3. 必要パッケージをインストール
   - 代表的な依存例:
     - duckdb
     - httpx
     - websocket-client
     - defusedxml
     - pyyaml（YAML 検証を使う場合、任意）
   - 例:
     - pip install duckdb httpx websocket-client defusedxml pyyaml

   注: sqlite3 は標準ライブラリに含まれます。

4. データディレクトリの作成（デフォルトの DB パス確保）
   - mkdir -p data

5. .env の作成（推奨: ウィザードを使用）
   - python -m kabusys.config_setup
   - ウィザードは JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD 等の入力を促します。

   手動作成の場合はプロジェクトルートに `.env` を配置してください。自動読み込みはデフォルトで有効（.env → .env.local の順で読み込む）。自動読み込みを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

必須環境変数（最低限）
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

主な任意/追加環境変数（例）
- KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
- DUCKDB_PATH — デフォルト: data/kabusys.duckdb
- SQLITE_PATH — デフォルト: data/monitoring.db
- LOG_LEVEL — DEBUG|INFO|WARNING|ERROR|CRITICAL
- KABU_API_BASE_URL — kabu station のベース URL
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — 通知設定
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（0/1）

config ディレクトリの YAML ファイル:
- config/system_config.yaml
- config/data_config.yaml
- config/strategy_config.yaml
- config/risk_config.yaml
- config/execution_config.yaml
- config/monitoring_config.yaml

validate_config はこれらの存在／パースをチェックします（PyYAML が無い場合は YAML 内容チェックをスキップして警告を出す）。

---

## 使い方（主要コマンド）

- 環境設定ウィザード（.env 作成・更新）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 警告も失敗扱いにする: python -m kabusys.validate_config --strict
  - 戻り値:
    - エラーがあれば exit code 1
    - 警告のみで --strict 未指定なら成功（exit 0）

- 実行エンジン起動（本番/ペーパー両対応）
  - python -m kabusys.run_execution
  - 注意:
    - KABUSYS_ENV=paper_trading または development の場合、MockBrokerClient を使用します。
    - paper_trading モードでは PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に分離して記録されます。
    - 起動時に data/execution.pid 等の PID ファイルを作成します。
    - 起動前に data/stop_requested.flag が存在する場合は起動せず終了します。

- 監視ループ起動
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL（秒）で間隔を変更可能（デフォルト 60）
  - Monitoring は環境にかかわらず本番 sqlite_path を使用します（設定に注意）

- ログ設定・プロセス優先度
  - run_* スクリプトは内部でログを初期化し、set_process_priority("high") を呼びます。

- デバッグ/テスト
  - MockBrokerClient は fill_mode によりテスト挙動を制御できます（instant/partial/never/reject）。
  - ExecutionEngine はテスト時に内部メソッド（_process_signals / _drain_push_queue）を直接呼び出して検査可能です。

---

## 運用メモ／トラブルシュート

- .env の自動読み込み
  - Settings モジュールはプロジェクトルート（.git または pyproject.toml）を起点に .env と .env.local を自動読み込みします。
  - OS の環境変数は上書きされません（.env.local は override=True だが protected により OS 環境は保護されます）。

- validate_config の挙動
  - PyYAML が無い場合は YAML のパース検証をスキップし警告を出します。YAML 構文チェックを有効にしたい場合は pyyaml をインストールしてください。

- 本番運用（KABUSYS_ENV=live）
  - KABUSYS_ENV=live は注意喚起の警告が出ます（validate_config も警告）。
  - 本番では LINE 通知や KILL_FLAG_CLEAR_ON_START 等の設定を慎重に行ってください。KILL_FLAG_CLEAR_ON_START=1 は本番で危険です（自動で kill flag をクリアしてしまうため）。

- DB 初期化
  - 多くの run スクリプトは必要なテーブルを起動時に冪等に作成します（init_monitoring_db, init_orders_db 等）。
  - DuckDB/SQLite のデフォルトパスは .env で変更可能です。

---

## ディレクトリ構成（主要ファイル）

（プロジェクトルート下に `src/kabusys` がある想定）

- src/kabusys/
  - __init__.py
  - config.py
    - Settings クラス（環境変数読み込み・検証・プロパティ）
    - .env 自動ロードロジック
  - config_setup.py
    - .env 対話式ウィザード
  - validate_config.py
    - 起動前チェック CLI（必須 env / config YAML / パス等）
  - run_execution.py
    - ExecutionEngine の起動スクリプト
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト
  - execution/ (発注関連)
    - broker_api.py — データモデル・Protocol・ファクトリ・例外定義
    - kabu_client.py — kabuステーション実装（HTTP + WebSocket）
    - mock_client.py — テスト用モック実装
    - broker_factory.py — Settings に基づくクライアント生成
    - execution_engine.py — ExecutionEngine（セッション管理・シグナル処理・WebSocket ドレイン）
    - order_record.py — OrderRecord の状態遷移ロジック（状態機械）
    - order_repository.py — SQLite 永続化層（orders テーブル）
    - order_manager.py — 外向け注文 API（create/send/sync/cancel）
    - reconciler.py — リコンシリエーション（OrderSent 照合、ポジション差分）
    - risk_manager.py — Gate1/2/3 のリスク管理
  - data/ (データ関連)
    - calendar_management.py — マーケットカレンダーと営業日ロジック
    - news_collector.py — RSS ニュース収集・前処理・保存ロジック
    - (jquants_client 等の補助モジュールが想定)
  - monitoring/
    - monitoring_db.py — 監視 DB 初期化・ログ関数（init_monitoring_db など）
    - system_monitor.py — システムリソース監視ロジック
  - utils/
    - logging_setup.py — ログ初期化ユーティリティ
    - process_priority.py — プロセス優先度設定ユーティリティ
  - config/ (設定用 YAML)
    - system_config.yaml
    - data_config.yaml
    - strategy_config.yaml
    - risk_config.yaml
    - execution_config.yaml
    - monitoring_config.yaml

---

## 参考（よく使うコマンドまとめ）

- .env ウィザード:
  - python -m kabusys.config_setup

- 設定検証:
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- 実行エンジン起動:
  - python -m kabusys.run_execution

- 監視起動:
  - python -m kabusys.run_monitoring

---

以上。必要であれば README.md をプロジェクト構造に合わせて調整したり、サンプル .env.example の雛形や requirements.txt を追加するドキュメントを作成します。どの形式（短い要約版 / 詳細手順 / 追加サンプル .env）を優先しますか？