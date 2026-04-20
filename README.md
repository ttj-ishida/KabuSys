# KabuSys

日本株向け自動売買システム（ライブラリ＋起動スクリプト群）

このリポジトリは、シグナル生成・ポートフォリオ構築・発注エンジン・監視機構・研究用ユーティリティを含む日本株自動売買システムのコア実装です。OpenAI を用いたニュース・マクロ判定、DuckDB を使った分析、SQLite による監視ログ永続化などを備えています。

---

## 概要

主な役割コンポーネント：

- 設定管理（.env 自動ロード、Settings クラス）
- 起動スクリプト
  - `run_execution.py`：ExecutionEngine（発注エンジン）を起動
  - `run_monitoring.py`：SystemMonitor のポーリングループを起動
- 監視（Monitoring）
  - system / trade / risk の各 Monitor、Kill Switch、アラート統合
  - SQLite ベースの監視 DB（`monitoring_db.py`）
- ポートフォリオ構築（選定・重み付け・ポジションサイズ計算・セクター制限）
- リサーチ（ファクター計算、特徴量探索、IC 等）
- AI モジュール（OpenAI を用いたニュースセンチメント、レジーム判定）
- ツール（Paper Trading 検証レポート生成 等）
- ユーティリティ（ログ設定、プロセス優先度設定 等）

---

## 主な機能一覧

- 環境設定ウィザード（対話式 .env 生成）: `kabusys.config_setup`
- 設定検証 CLI（.env / config/*.yaml の事前チェック）: `kabusys.validate_config`
- 起動スクリプト
  - Execution エンジン起動（本番/ペーパートレード切替）: `kabusys.run_execution`
  - Monitoring ポーリングループ: `kabusys.run_monitoring`
- 監視機能
  - システム状態（CPU/Mem/Disk、Execution プロセス生存確認、データの鮮度）
  - 取引監視（滞留注文、約定異常等）
  - リスク監視（ドローダウン、ポジション上限）
  - Kill Switch（条件に応じて `data/kill.flag` を作成して ExecutionEngine を停止）
- ポートフォリオ構築
  - 候補選定、等金額／スコア加重の重み算出、ポジションサイズ計算（LOT 単位対応）
  - セクター上限フィルタ、レジームに基づく乗数
- 研究用関数
  - モメンタム／ボラティリティ／バリュー等のファクター計算（DuckDB 接続受け取り）
  - 将来リターン、IC（Spearman）計算、統計サマリー
- AI（OpenAI）連携
  - ニュースセンチメント（銘柄毎）および市場レジーム判定（gpt-4o-mini 想定）
  - 再試行・バリデーション・部分書き込みによる堅牢な実装
- ツール
  - ペーパートレード検証レポート生成（注文成功率、レイテンシ、稼働率等）

---

## 要件（主な依存）

- Python 3.9+
- ランタイムライブラリ（例）
  - duckdb
  - psutil
  - openai
  - PyYAML（任意：config YAML の検証に使用）
- 標準ライブラリ：sqlite3 等

（実行環境に合わせて virtualenv を推奨します）

例（pip）:
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai PyYAML
```

---

## セットアップ手順

1. リポジトリをクローン／展開
2. 仮想環境を作成して依存パッケージをインストール（上記参照）
3. 初期設定（.env 作成）
   - 対話式ウィザードを利用:
     ```
     python -m kabusys.config_setup
     ```
   - 生成された `.env` は絶対に Git に含めないでください。
4. 設定検証:
   ```
   python -m kabusys.validate_config
   ```
   - `--strict` を付けると警告も失敗扱いになります。
5. データディレクトリ（`data/`）やログディレクトリ（`logs/`）は自動作成されますが、権限など注意してください。

---

## 環境変数（主なもの）

必須（アプリにより参照される）:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

推奨／オプション:
- KABUSYS_ENV: 実行環境（development / paper_trading / live）
  - `paper_trading` の場合は MockBrokerClient を使用し、`data/paper_trading.db` に記録します（本番 DB と分離）。
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: SQLite 監視 DB（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: ペーパートレードでの約定モード（instant/partial/never/reject）
- OPENAI_API_KEY: OpenAI API キー（AI モジュールで使用）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: アラート通知（任意）
- LOG_LEVEL, LOG_DIR: ログ設定
- PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）

注意: Settings クラスが環境変数から多くの設定を参照します。`.env.example`（存在する場合）を参照してください。

---

## 起動・使い方

基本的なコマンド例：

- 環境ウィザード（.env 作成）
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  ```

- ExecutionEngine 起動
  - 本番／開発：Settings.KABUSYS_ENV を設定してから実行
  ```
  python -m kabusys.run_execution
  ```
  - 起動時に `data/stop_requested.flag` が存在すると起動をスキップします。
  - `paper_trading` 環境では paper_trading 用 DB に記録します。

- Monitoring 起動（ポーリング）
  ```
  python -m kabusys.run_monitoring
  ```
  - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を秒で上書き可能（デフォルト 60 秒）。
  - 監視は Settings.env にかかわらず本番用 `sqlite_path` を使用します（監視 DB は単一の監視ファイルで管理）。

- Paper Trading 検証レポート生成
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  - `--db` オプションでペーパートレード DB を明示可能。環境変数 `PAPER_TRADING_SQLITE_PATH` も利用可。

- ライブラリ利用（例: 研究用関数）
  Python スクリプト／REPL 内で DuckDB 接続を作成して使用できます:
  ```py
  import duckdb
  from kabusys.research import calc_momentum

  conn = duckdb.connect("data/kabusys.duckdb")
  records = calc_momentum(conn, target_date=date(2026, 4, 10))
  ```

---

## ログ・データ・フラグ

- ログ
  - デフォルト出力先: `logs/<app_name>.log`（`kabusys.utils.logging_setup.setup_logging` で管理）
  - 日次ローテーション・30日保持
- データディレクトリ（デフォルト）
  - SQLite: `data/monitoring.db`
  - DuckDB: `data/kabusys.duckdb`
  - ペーパートレード DB: `data/paper_trading.db`
- フラグファイル
  - `data/kill.flag`: Kill Switch（ExecutionEngine へ停止指示）
  - `data/stop_requested.flag`: スクリプトを終了させるための停止フラグ（run_* が参照）
  - PID ファイル: `data/execution.pid`（ExecutionEngine が使用）

---

## ディレクトリ構成（概要）

リポジトリの主要なファイル・ディレクトリ構成（src 配下を中心に）:

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / Settings
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — Monitoring 起動スクリプト
  - tools/
    - paper_verification_report.py
  - ai/
    - news_nlp.py            — ニュース NLP（OpenAI）
    - regime_detector.py     — 市場レジーム判定（OpenAI + MA）
  - research/
    - factor_research.py
    - feature_exploration.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - monitoring_engine.py
    - kill_switch.py
    - alert_manager.py
  - execution/                — 発注関連（Engine, BrokerFactory, OrderManager など）
  - utils/
    - logging_setup.py
    - process_priority.py

プロジェクトルート:
- config/                    — YAML テンプレート（system_config.yaml 等）
- data/                      — 生成される DB / フラグ
- logs/                      — ログ出力先（デフォルト）

---

## 重要ノート / 運用上の注意

- .env は機密情報を含みます。決して VCS にコミットしないでください。
- 本番環境（KABUSYS_ENV=live）では特に Kill Switch / LINE 通知設定を確認してください。
- OpenAI を利用する機能は API キーが必要です。呼び出し回数やコストに注意してください。
- run_monitoring は監視 DB（SQLite）を参照します。監視は本番 DB を参照する仕様になっているため、環境設定に注意してください。
- process priority 設定や CPU affinity の設定は権限により失敗することがあります（警告ログのみ）。

---

README は以上です。必要であれば以下の追加情報を作成します：
- 具体的な .env 例（.env.example 形式）
- systemd / supervisor 用の起動スクリプト例
- 実装ごとの API ドキュメント（関数シグネチャ詳細）