# KabuSys

日本株向け自動売買システム（パッケージ化されたライブラリ + 起動スクリプト群）

このリポジトリは、シグナル生成・ポートフォリオ構築・発注（ExecutionEngine）・監視（Monitoring）・Research/AIツール群を含むモジュール構成の自動売買基盤です。各種設定は環境変数（.env）で制御します。

## 概要
- モジュール化されたコンポーネント群（portfolio, research, ai, monitoring, execution, utils 等）
- 本番 / ペーパートレードを環境変数 `KABUSYS_ENV` で切り替え可能
- SQLite（監視・発注履歴等）と DuckDB（分析用）を併用
- OpenAI を用いたニュース NLP / レジーム判定機能（任意）
- ログはコンソール出力と日次ローテーションファイル（logs/*.log）で管理

## 主な機能一覧
- ExecutionEngine（発注・OrderManager・RiskManager・Reconciler 等）
  - `run_execution.py` から起動。`KABUSYS_ENV=paper_trading` 時は MockBrokerClient を使い DB を分離。
- Monitoring（システム状態・注文の健全性・リスク監視）
  - `run_monitoring.py` からポーリング実行。Kill Switch による停止フラグ生成。
- 設定ウィザード / 検証
  - `.env` の対話式生成: `kabusys.config_setup`
  - 設定検証: `kabusys.validate_config`
- Research / ファクター計算
  - momentum / volatility / value 等のファクター計算（DuckDB ベース）
- Portfolio construction
  - 候補選定・重み計算・ポジションサイズ計算・セクターキャップ等
- AI（OpenAI）連携
  - ニュース NLP による銘柄センチメント → `ai.score_news`
  - レジーム判定（ma200 + マクロニュース） → `ai.regime_detector`
- ツール
  - Paper Trading 検証レポート生成: `kabusys.tools.paper_verification_report`

## 必須 / 推奨環境変数
必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

重要な環境変数（デフォルト含む）:
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- DUCKDB_PATH: data/kabusys.duckdb
- SQLITE_PATH: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH: data/paper_trading.db（paper_trading 用）
- LOG_LEVEL: INFO（"DEBUG"/"INFO"/"WARNING"/"ERROR"/"CRITICAL"）
- LOG_DIR: logs/
- PID_FILE_PATH: data/execution.pid
- KILL_FLAG_PATH: data/kill.flag
- KILL_FLAG_CLEAR_ON_START: 0|1（起動時に kill.flag を自動でクリアするか）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、デフォルト 60）
- OPENAI_API_KEY: OpenAI API を使う場合に必要

（細かいデフォルト値や追加設定は `kabusys.config.Settings` を参照してください）

## セットアップ手順（ローカル / 開発）
1. リポジトリをクローン、必要な Python 仮想環境を作成
2. 依存パッケージをインストール（例）
   - psutil, duckdb, openai, PyYAML（検証時に必要）、その他 requirements.txt があればそれを利用
   - 例:
     ```
     pip install psutil duckdb openai PyYAML
     ```
3. .env を生成（対話式ウィザードが便利）
   ```
   python -m kabusys.config_setup
   ```
   生成後、設定を検証:
   ```
   python -m kabusys.validate_config
   ```
   --strict を付けると警告もエラー扱いになります:
   ```
   python -m kabusys.validate_config --strict
   ```
4. ログディレクトリ・data ディレクトリなどは自動作成されますが、必要に応じて手動で作成してください。

## DB 初期化
- 監視用 SQLite（monitoring.db）は起動スクリプト内で `init_monitoring_db` により冪等的に初期化されます。基本的に手動初期化は不要です。

## 使い方（起動 / 実行例）
- ExecutionEngine（発注エンジン）を起動:
  ```
  python -m kabusys.run_execution
  ```
  - `KABUSYS_ENV=paper_trading` にすると MockBroker を使用し、`PAPER_TRADING_SQLITE_PATH`（デフォルト `data/paper_trading.db`）へ記録します。
  - 起動時に `data/stop_requested.flag` が存在すると起動を行いません。
  - 実行中は `data/execution.pid` に PID を書きます（設定で変更可）。

- Monitoring を起動（ポーリング実行）:
  ```
  python -m kabusys.run_monitoring
  ```
  - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を秒で上書き（デフォルト 60 秒）。
  - 監視は常に本番 sqlite_path（`SQLITE_PATH`）を使用します（Monitoring は環境に依らず本番 DB 参照）。
  - 停止は `data/stop_requested.flag` を作成すると検知して終了します。

- Paper Trading 検証レポート生成:
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  - DB パスは `--db` または環境変数 `PAPER_TRADING_SQLITE_PATH` で指定可能。

- AI / レジーム判定・ニューススコアリング（ライブラリ関数呼び出し）
  - OpenAI API キーを設定して、DuckDB 接続を渡し関数を呼ぶ設計です。例:
    ```py
    from kabusys.ai.news_nlp import score_news
    score_news(duckdb_conn, target_date, api_key="sk-...")
    ```
  - CLI ラッパーはありませんが、スクリプトや cron から呼び出すことを想定しています。

## 停止・Kill Switch
- 強制停止（Execution 停止指示）:
  - `KillSwitch` は条件を満たすと `data/kill.flag` を書き込みます（ExecutionEngine はこれを参照して停止処理を行います）。
  - 手動で停止指示を出す場合は `data/kill.flag` に理由を書き込みます（`KillSwitch._write_flag` と同挙動）。
- 停止フラグによる監視/実行プロセスのシャットダウン:
  - `data/stop_requested.flag` を作ることで `run_execution` / `run_monitoring` は次のループで検知して終了します。
- 起動時に `KILL_FLAG_CLEAR_ON_START=1` を設定すると起動時に kill.flag を自動クリアします（本番では 0 を推奨）。

## ログ
- ロギングは共通ユーティリティ `kabusys.utils.logging_setup.setup_logging` を通じて設定されます。
- コンソール（stdout）と日次ローテートファイル（デフォルト: logs/<app_name>.log）に出力します。
- LOG_DIR / LOG_LEVEL で挙動を制御可能。

## 注意点 / 運用上のメモ
- `KABUSYS_ENV=live` を指定すると本番モードになります。LINE通知や Kill Switch 等の設定を十分確認してください。
- Paper Trading は本番 DB と完全分離する設計です。`KABUSYS_ENV=paper_trading` の場合は `paper_sqlite_path`（デフォルト `data/paper_trading.db`）を使います。
- OpenAI を使う機能は API エラーに対して冪等・フェイルセーフな設計になっていますが、API キーやコストの管理に注意してください。
- `MONITOR_POLL_INTERVAL` に不正な値（0 以下や非整数）を設定するとデフォルト（60 秒）にフォールバックします。
- `process_priority`（優先度）は起動時に "high" に設定されるため、権限や OS 関連で設定失敗する場合は警告が出ます。

## ディレクトリ構成（主要ファイル）
（package ルートは src/kabusys を想定）

- src/kabusys/
  - __init__.py
  - config.py — 環境変数 / 設定管理（.env 自動ロード含む）
  - config_setup.py — .env 対話式ウィザード
  - validate_config.py — 起動前設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — Monitoring 起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート
  - ai/
    - news_nlp.py — ニュース NLP（OpenAI 連携）
    - regime_detector.py — 市場レジーム判定（OpenAI 連携）
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py
  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py
    - monitoring_engine.py
  - execution/  (発注関連コンポーネント: Engine, OrderManager, BrokerFactory, Reconciler, RiskManager など)
  - utils/
    - logging_setup.py
    - process_priority.py
    - __init__.py
  - data/ （実行時生成想定）
    - *.db, *.flag, *.pid など

（上記は主要ファイルの一覧です。実際の詳細実装・追加モジュールはソースを参照してください。）

## サンプル .env（参考）
以下は `kabusys.config_setup` で生成される .env の例（一部のみ）。
```
JQUANTS_REFRESH_TOKEN=your_token_here
KABU_API_PASSWORD=your_password_here
KABU_API_BASE_URL=http://localhost:18080/kabusapi

LINE_CHANNEL_ACCESS_TOKEN=
LINE_USER_ID=

DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db

KABUSYS_ENV=development
LOG_LEVEL=INFO

KILL_FLAG_CLEAR_ON_START=0
```

## 開発者向けテスト / デバッグ
- 各モジュールは関数単位でテストしやすい純粋関数（portfolio 等）や DB 接続を引数に取る構造になっています。
- MonitoringEngine は `run_once()` により単発実行で各モニタを呼び出せるためユニットテストが容易です。
- OpenAI 呼び出し部分は内部でラップしているため、テスト時はそのラッパーを patch してモック可能です（例: unittest.mock.patch）。

---

問題や追加したいドキュメントがあれば教えてください。必要に応じてサンプルコマンドや運用手順をさらに詳細化します。