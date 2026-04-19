# KabuSys

日本株自動売買システムのコードベース（ライブラリ + 起動スクリプト群）

この README はリポジトリ内の主要モジュールから自動生成した情報を元に、開発者／運用者向けに要点を整理したドキュメントです。

---

## プロジェクト概要

KabuSys は日本株の自動売買システムです。システムは次のような責務を持つコンポーネントで構成されています。

- 戦略・ポートフォリオ構築（ファクター計算・シグナル生成・ポジションサイズ計算）
- 注文発行・リスク管理・約定管理（ExecutionEngine）
- システム監視・アラート・Kill Switch（Monitoring）
- Paper Trading（ペーパートレード）モードと実口座（live）モードの切替
- DuckDB / SQLite を使ったデータ管理・解析
- OpenAI（LLM）を使ったニュース NLP / レジーム判定（オプション）

設計上のポイント：
- 環境変数（.env）ベースで設定を管理
- 起動スクリプトはモジュール化され、`python -m kabusys.<module>` で起動可能
- Paper Trading は本番 DB と分離（専用 SQLite に記録）
- monitoring は KABUSYS_ENV にかかわらず、本番用の sqlite_path を使って監視データを記録

---

## 機能一覧

主な機能（抜粋）:

- 環境設定ウィザード（`.env` の対話式生成）
  - `python -m kabusys.config_setup`
- 設定検証ツール（.env と config/*.yaml の簡易検証）
  - `python -m kabusys.validate_config [--strict]`
- ExecutionEngine 起動スクリプト
  - `python -m kabusys.run_execution`（KABUSYS_ENV により paper_trading モードに切替）
- Monitoring 起動スクリプト（ポーリング監視ループ）
  - `python -m kabusys.run_monitoring`
  - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL`（デフォルト 60 秒）
- Paper Trading 検証レポート生成ツール
  - `python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]`
- Portfolio construction（候補選定、重み付け、ポジションサイズ算出）
- Research（ファクター計算、将来リターン、IC 計算）
- AI モジュール（ニュースセンチメント / レジーム判定） — OpenAI API 必須（オプション）
- ログ設定ユーティリティ（コンソール + 日次ローテートファイル）
- プロセス優先度 / CPU affinity のユーティリティ
- 監視 DB（SQLite）への永続化レイヤ（system_status, trade_logs, positions, risk_logs, dashboard）

---

## セットアップ手順（開発・運用向け）

前提：Python 3.9+（型ヒントでメジャー機能を使用）。必要な外部パッケージはプロジェクトで使用する機能に依存します。最低限の例：

推奨パッケージ（機能に応じて追加）:
- duckdb
- psutil
- openai（AI 機能を使う場合）
- pyyaml（validate_config の YAML 検証に必要）

例：pip でインストール
```
pip install duckdb psutil openai pyyaml
```

1. リポジトリをチェックアウト
2. Python 仮想環境を作成・有効化（任意）
3. 必要なライブラリをインストール（上記参照）
4. 初期 `.env` を作成
   - 対話式ウィザードを使う:
     ```
     python -m kabusys.config_setup
     ```
   - または `.env.example` を参照して手動作成
5. 設定の簡易検証:
   ```
   python -m kabusys.validate_config
   python -m kabusys.validate_config --strict  # 警告を許さない厳格モード
   ```
6. データディレクトリを作成（必要に応じて）
   - デフォルトの DB / ログパスは以下を参照
     - DuckDB: `data/kabusys.duckdb`
     - SQLite (monitoring): `data/monitoring.db`
     - Paper Trading SQLite: `data/paper_trading.db`
     - PID / flag / execution pid: `data/`
     - ログ: `logs/`（デフォルト）

注意: 自動 .env ロードは `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化できます（テスト時など）。

必須環境変数（主なもの）:
- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）

主な任意/上書き可能な変数:
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- LOG_LEVEL: DEBUG|INFO|WARNING|ERROR|CRITICAL（デフォルト: INFO）
- DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH
- OPENAI_API_KEY（AI 機能を使う場合）
- MONITOR_POLL_INTERVAL（監視ループの秒間隔、デフォルト 60）

---

## 使い方（起動 / コマンド例）

### 環境設定
対話式で .env を作る（推奨）
```
python -m kabusys.config_setup
```

設定検証
```
python -m kabusys.validate_config
python -m kabusys.validate_config --strict
```

### 実行（ExecutionEngine）
- 通常（`KABUSYS_ENV` に従う）:
```
python -m kabusys.run_execution
```
- ペーパートレード（MockBroker を使用、paper_trading 専用 DB に記録）
```
KABUSYS_ENV=paper_trading python -m kabusys.run_execution
```
Execution 起動時:
- プロセス優先度を "high" に設定
- Paper Trading のときは `PAPER_TRADING_SQLITE_PATH`（デフォルト `data/paper_trading.db`）に接続
- 起動前に `data/stop_requested.flag` が存在すれば起動を中止

停止手順:
- 実行中プロセスは `data/stop_requested.flag` を監視しています。ファイルを作成すると（運用側で）プロセスが検知して終了処理を行います。
- Kill Switch は `data/kill.flag` を書き込むことで ExecutionEngine に停止シグナルを送ります（Monitoring 側が発動する）。

### 監視（Monitoring）
```
python -m kabusys.run_monitoring
```
- デフォルトのポーリング間隔は 60 秒。環境変数 `MONITOR_POLL_INTERVAL` で上書き可能（例: 30 秒）
```
MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
```
- 監視は本番 sqlite（Settings.sqlite_path）を使って system_status 等を記録します（KABUSYS_ENV に依存せず本番 sqlite_path を使用する仕様）。
- 停止は `data/stop_requested.flag` を作成することで行えます。

### Paper Trading 検証レポート
Paper Trading の SQLite を指定してレポートを生成します:
```
python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
```
デフォルト DB パスは `data/paper_trading.db`。`--db` オプションまたは環境変数 `PAPER_TRADING_SQLITE_PATH` を使って変更可能。

### AI モジュール（OpenAI）
ニュース NLP / レジーム判定を使うには OpenAI API キーが必要:
```
export OPENAI_API_KEY=sk-...
```
関数はライブラリ API として提供され、DuckDB 接続と日付を渡して実行します（スクリプトから直接呼ぶユーティリティもあり）。

---

## ログ・ファイル・フラグの扱い

- ログ:
  - デフォルトは `logs/` ディレクトリに日次ローテーションで保存（ファイル名: `<app_name>.log`）。環境変数 `LOG_DIR` で変更可能。
  - ログレベルは `LOG_LEVEL` または `setup_logging(level=...)` により指定。
- PID / フラグ:
  - ExecutionEngine 用 PID: `data/execution.pid`（Settings.pid_file_path）
  - 停止要求（外部運用用）: `data/stop_requested.flag` — run_execution と run_monitoring はこの存在を監視して正常終了する
  - Kill Switch（Monitoring が書き込む）: `data/kill.flag` — ExecutionEngine はこれを検知して安全停止
  - `KILL_FLAG_CLEAR_ON_START=1` にすると ExecutionEngine 起動時に `kill.flag` を自動でクリア（注意: 本番では推奨されない）

---

## 主要ディレクトリ構成（src 以下の抜粋）

- kabusys/
  - __init__.py (バージョン等)
  - config.py (環境変数・設定管理)
  - config_setup.py (対話式 .env ウィザード)
  - validate_config.py (検証 CLI)
  - run_execution.py (ExecutionEngine 起動スクリプト)
  - run_monitoring.py (Monitoring 起動スクリプト)
  - utils/
    - logging_setup.py (統一ログ設定)
    - process_priority.py (プロセス優先度・CPU affinity)
  - execution/ (注文発行・マネージャ等: broker_factory, execution_engine, order_manager, etc.)
  - monitoring/
    - monitoring_db.py (SQLite 永続化)
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py (アラート送信)
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py (ニュースセンチメント)
    - regime_detector.py (市場レジーム判定)
  - tools/
    - paper_verification_report.py (Paper Trading の検証レポート)
  - data/ (runtime に使用される SQLite / DuckDB / flag / pid 等のファイル配置想定)
  - config/ (yaml 設定ファイル群: system_config.yaml, strategy_config.yaml, ...)

---

## 注意事項 / 運用上の留意点

- 本番（live）モードでは実際に発注されます。設定（API パスワード、チャネルトークンなど）は厳重に管理してください。
- `.env` は絶対に Git 等にコミットしないでください。
- monitoring は監視専用のロジックを持ち、KABUSYS_ENV に依存せずプロダクションの sqlite を参照します。テスト時は設定値を確認の上、パスを書き換えてください。
- OpenAI API の呼び出しにはレート制限やエラーがあるため、内部でリトライ / フェイルセーフが実装されていますが、API キー漏洩・課金リスクに注意してください。
- validate_config の YAML 検証は PyYAML がインストールされている場合のみ行われます。未インストールの場合は警告が出てスキップされます。
- 一部の機能は DuckDB のバージョンや SQLite の挙動（executemany の空リスト等）に依存するため、実稼働環境では推奨パッケージバージョンを固定してください。

---

## よく使うコマンドまとめ

- .env を作る（ウィザード）
  - python -m kabusys.config_setup
- 設定チェック
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict
- Execution 起動
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
- Monitoring 起動
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- Paper Trading レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

---

README に記載の内容はコード内の docstring / コメントを要約したものです。詳細な実装や追加の設定値は各モジュール（`src/kabusys/*`）の docstring を参照してください。必要であれば、さらに導入手順（Docker / systemd ユニットファイル等）や運用手順（Backup / restore、監視アラートの設定）についてのテンプレートも作成できます。必要なら教えてください。