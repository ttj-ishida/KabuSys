# KabuSys

日本株自動売買フレームワーク（プロトタイプ）

このリポジトリは日本株の自動売買／監視を目的とした軽量フレームワークです。発注フロー、リスクガード、再起動時のリコンシリエーション、監視ループ、mock ブローカーなどを備え、ローカルでの開発・ペーパートレード運用に焦点を当てています。

バージョン: 0.1.0

---

## 概要

KabuSys は以下の関心事を分離して実装しています。

- 環境設定管理（.env 自動読み込み / 対話式ウィザード）
- 設定検証ツール（起動前に .env と config/*.yaml をチェック）
- ExecutionEngine：シグナルに基づく発注フロー（Signal Pull + WebSocket push ドレイン）
- Order 管理：OrderRecord（状態遷移）、OrderRepository（SQLite）、OrderManager（API 呼び出し含む）
- Broker クライアント：MockBrokerClient（テスト用）、KabuStationClient（kabuステーション API 実装）
- リスク管理：Gate1/2/3 の 3 段階リスクガード（余力・重複・ポジション上限、レート制限／サーキットブレーカー、ドローダウン）
- Reconciler：起動時の OrderSent 照合とポジション差分検出
- 監視ループ：SystemMonitor を定期実行して監視データを収集

設計は「DB と API 呼び出しの責務を明確に分離」「クラッシュに耐える永続化シーケンス」「テスト可能な mock 実装」を重視しています。

---

## 主な機能一覧

- .env 対話式ウィザード（python -m kabusys.config_setup）
- 起動前設定検証 CLI（python -m kabusys.validate_config）
  - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性、DBパスや config/*.yaml の存在・パース確認（PyYAML があればパース）
  - --strict で警告も FAIL 扱い
- ExecutionEngine（run_execution）
  - シグナル処理（発注窓口）、WebSocket push ドレイン、PID/kill flag 管理、kill_switch 実装
- Broker 抽象化（Protocol）
  - MockBrokerClient（paper_trading / development 用、fill_mode の振舞い切替）
  - KabuStationClient（kabuステーション向け REST/WebSocket 実装）
- Order の永続化（SQLite）と状態遷移ロジック（OrderRecord）
- Reconciler（再起動時の自動復旧）
- RiskManager（Gate1/2/3）とサーキットブレーカ、レートトークンバケツ
- データ系ユーティリティ
  - JPX カレンダー管理（DuckDB）
  - ニュース収集（RSS → raw_news）※セキュリティ対策（SSRF対策、defusedxml 等）を組み込み

---

## 必要条件・依存関係

- Python 3.10+
- 標準ライブラリ: sqlite3, threading, logging, pathlib, time, datetime など
- 推奨 pip パッケージ:
  - duckdb
  - httpx
  - websocket-client
  - defusedxml
  - pyyaml（config/*.yaml のパース検証に必要）
- （開発用）pytest 等

インストール例:

```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb httpx websocket-client defusedxml pyyaml
```

---

## セットアップ手順

1. リポジトリをクローンして作業ディレクトリへ移動

   ```bash
   git clone <repo-url>
   cd <repo-root>
   ```

2. 仮想環境を作成して依存パッケージをインストール（上記を参照）

3. .env を作成する
   - 対話式ウィザード実行（推奨）

     ```bash
     python -m kabusys.config_setup
     ```

     wizard に従って必要な値（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD 等）を入力します。
   - 既存の .env を手動で用意する場合はルートに `.env` を置いてください（.env は Git にコミットしないでください）。

4. 設定の検証

   ```bash
   python -m kabusys.validate_config
   # 警告を FAIL 扱いにする場合:
   python -m kabusys.validate_config --strict
   ```

   - 必須環境変数が未設定、または config/*.yaml に問題がある場合に検出されます。
   - config/*.yaml は config ディレクトリ下の YAML を想定。欠けている場合は警告になります（生成スクリプトがある場合: python scripts/generate_config.py を参照してください）。

5. DB ディレクトリ作成（必要に応じて）
   - デフォルトでは data/ 以下に duckdb / sqlite ファイルを置きます。親ディレクトリがない場合は起動時に自動作成される場合がありますが、手動で作成しておくと安全です。

---

## 使い方

- 設定ウィザード

  ```bash
  python -m kabusys.config_setup
  ```

- 設定検証

  ```bash
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- 実行エンジン（運用・ペーパートレード）

  環境変数で運用モードを切り替えます:
  - KABUSYS_ENV=development または paper_trading: MockBrokerClient を使用（実発注なし）
  - KABUSYS_ENV=live: 本番（ただし Live broker client は未実装の箇所あり）

  起動例（ペーパートレード）:

  ```bash
  export KABUSYS_ENV=paper_trading
  python -m kabusys.run_execution
  ```

  実行時の挙動:
  - PID ファイル（data/execution.pid 等）を書き込み
  - stop flag（data/stop_requested.flag）による終了
  - kill flag（デフォルト: data/kill.flag）による起動拒否や強制停止
  - paper_trading は paper_sqlite_path（デフォルト data/paper_trading.db）を使用し本番 DB と分離

- 監視プロセス

  ```bash
  python -m kabusys.run_monitoring
  ```

  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書きできます（デフォルト 60）
  - 監視は本番 sqlite_path を使用（KABUSYS_ENV に依らず本番 DB パスを利用）

- 環境変数の例（主なもの）
  - 必須:
    - JQUANTS_REFRESH_TOKEN
    - KABU_API_PASSWORD
  - 推奨 / 任意:
    - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
    - DUCKDB_PATH（デフォルト data/kabusys.duckdb）
    - SQLITE_PATH（デフォルト data/monitoring.db）
    - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB）
    - LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL）
    - KABU_API_BASE_URL（kabu station API）
    - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID（本番での通知）
    - KILL_FLAG_CLEAR_ON_START（起動時に kill.flag を自動クリアするか）

---

## 既知の注意点 / 制限

- Live 用の KabuStationClient は REST/WebSocket 実装が存在しますが、BrokerClientFactory は live を NotImplementedError として扱う箇所があります（将来的な本番対応は要確認）。
- config/*.yaml の生成スクリプト（scripts/generate_config.py）についてはリポジトリの該当スクリプトを参照してください。存在しない場合は手動で config 配下にファイルを配置してください。
- .env の自動読み込みは起動時に行われますが、テストなどで自動ロードを無効化したい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- Python 3.10 以上を推奨（型記法や union operator に依存）。

---

## ディレクトリ構成（主要ファイル）

ルート: src/kabusys 以下にパッケージが配置されています。主要ファイルの簡単な説明:

- __init__.py
  - パッケージ定義とバージョン

- config.py
  - 環境変数の自動ロード（.env / .env.local）
  - Settings クラス（環境変数をプロパティで取得、妥当性チェック含む）
  - _require() による必須 env チェック

- config_setup.py
  - .env 対話式ウィザード（run_wizard / main）

- validate_config.py
  - 起動前の設定検証 CLI（必須 env、KABUSYS_ENV, LOG_LEVEL, DB パス、config/*.yaml、live ガード等）

- run_execution.py
  - ExecutionEngine 起動スクリプト
  - PID / stop flag 管理、DB 接続、スレッドでエンジンを実行

- run_monitoring.py
  - 監視（SystemMonitor）ポーリングループ起動スクリプト

- execution/
  - broker_api.py — BrokerAPIProtocol、データモデル、例外、ファクトリ
  - broker_factory.py — Settings に基づくブローカーファクトリ
  - kabu_client.py — KabuStationClient（HTTP + WebSocket 実装）
  - mock_client.py — MockBrokerClient（テスト用）
  - order_record.py — Order の状態遷移モデル
  - order_repository.py — SQLite 永続化層（init_orders_db あり）
  - order_manager.py — Order 作成/送信/同期/キャンセルの外向き API
  - execution_engine.py — ExecutionEngine（シグナル処理・WebSocket ドレイン・kill_switch 等）
  - reconciler.py — 起動時リコンシリエーション
  - risk_manager.py — Gate1/2/3 のリスク制御

- data/
  - calendar_management.py — JPX カレンダー管理（DuckDB を利用）
  - news_collector.py — RSS 収集・前処理（セキュリティ考慮済み）
  - （その他データ関連モジュール）

- monitoring/
  - monitoring_db.py（監視用 SQLite 初期化 / ログ機能） — 実装あり（参照）
  - system_monitor.py（SystemMonitor 実装） — 実装あり（参照）

- utils/
  - logging_setup.py — ロギング設定ユーティリティ
  - process_priority.py — プロセス優先度設定ユーティリティ

- config/（設定 YAML 想定ディレクトリ）
  - system_config.yaml
  - data_config.yaml
  - strategy_config.yaml
  - risk_config.yaml
  - execution_config.yaml
  - monitoring_config.yaml

- data/（ランタイムで使用するファイル群）
  - *.duckdb
  - monitoring.db / paper_trading.db
  - execution.pid / stop_requested.flag / kill.flag

---

## 推奨ワークフロー（ローカル開発・ペーパートレード）

1. 仮想環境を作成して依存をインストール
2. python -m kabusys.config_setup で .env を作成（KABUSYS_ENV=paper_trading を選択）
3. python -m kabusys.validate_config で検証
4. python -m kabusys.run_execution を実行して発注フローをテスト
5. python -m kabusys.run_monitoring を別プロセスで起動して監視を確認

---

## 補足

- テスト・デバッグ時は MockBrokerClient（PAPER_FILL_MODE や available_cash の調整）を利用してください。
- 本番運用時は LINE 通知等の設定を必ず確認し、KABUSYS_ENV=live の警告に注意してください。
- README に書かれていない内部実装や詳細については各モジュールの docstring を参照してください（src/kabusys 以下の各ファイルに詳細な説明があります）。

---

貢献・報告
- バグ報告や提案は Issue を立ててください。重大な仕様変更や live ブローカー実装は事前に設計協議をお願いします。