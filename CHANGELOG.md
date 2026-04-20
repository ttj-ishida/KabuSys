# Changelog

すべての重要な変更は Keep a Changelog の慣例に従って記載しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

## [0.1.0] - 2026-04-20
初回公開リリース。以下の主要機能・ユーティリティを含みます。

### 追加 (Added)
- 基本アプリケーション情報
  - パッケージバージョンを `__version__ = "0.1.0"` として追加。

- 環境/設定管理
  - Settings クラスを実装し、環境変数経由でアプリケーション設定を提供（KABUSYS_ENV / LOG_LEVEL / 各種 DB パス等）。
  - 自動 .env 読み込み機能を実装（プロジェクトルートの `.env` と `.env.local` を自動ロード、OS 環境変数を保護）。`KABUSYS_DISABLE_AUTO_ENV_LOAD` で無効化可能。
  - `.env` ファイルの高度なパーサを実装（`export` プレフィックス、シングル/ダブルクォート内のエスケープ、インラインコメントの考慮等をサポート）。

- 起動支援 CLI / ツール
  - `kabusys.config_setup`：対話式ウィザードで `.env` を生成・更新する CLI を追加（デフォルト値、シークレットマスク表示、保存確認など）。
  - `kabusys.validate_config`：起動前に .env と config/*.yaml を検証する CLI を追加。`--strict` オプションで警告を失敗扱いに可能。
  - `kabusys.tools.paper_verification_report`：Paper Trading 用 SQLite データベースから検証レポートを生成するツールを追加。稼働率、注文成功率、送信率、レイテンシ（P95）等を算出し PASS/FAIL 判定を行う。

- 実行系 / 監視
  - `run_execution.py`：ExecutionEngine 起動スクリプトを追加。  
    - `KABUSYS_ENV=paper_trading` の場合、ペーパートレード用の専用 SQLite DB (`PAPER_TRADING_SQLITE_PATH`) を使用し、本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント抽象化（MockBroker の利用を想定）。
    - ExecutionEngine を別スレッドで実行し、`data/stop_requested.flag` による停止制御、実行中 PID ファイル管理を行う。
    - リスク管理のデフォルト設定（max_position_pct / max_utilization / rate_limit_per_sec / circuit_breaker 等）を組み込み。
  - `run_monitoring.py`：SystemMonitor ポーリングループ起動スクリプトを追加。
    - 環境にかかわらず監視は本番用の sqlite_path を使用（監視データを本番 DB に集約）。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。不正な値はデフォルトにフォールバック。
    - 停止フラグ `data/stop_requested.flag` の検知でループを終了。

- ロギング / プロセス制御ユーティリティ
  - `kabusys.utils.logging_setup.setup_logging`：全アプリで共通利用できるログ初期化関数を実装。
    - stdout への StreamHandler と日次ローテーション (`TimedRotatingFileHandler`) の両対応。
    - `LOG_LEVEL` / `LOG_DIR` の解決順を実装し、既存ハンドラをクリアして重複出力を防止。
  - `kabusys.utils.process_priority`：プロセス優先度（Windows の High/Nomal/Low、POSIX の nice 値）と CPU affinity 設定ユーティリティを実装。権限不足や未対応 OS の場合は警告を出してスキップ。

- ポートフォリオ構築（純粋関数群）
  - `portfolio.portfolio_builder`：シグナル選定と重み計算（候補選択、等分配、スコア加重）を実装。スコアが全て 0 の場合は等分配にフォールバックして警告を出す。
  - `portfolio.risk_adjustment`：セクター集中制限（apply_sector_cap）と市場レジームに応じた乗数（calc_regime_multiplier）を実装。未知レジームでは 1.0 でフォールバック。
  - `portfolio.position_sizing`：株数決定ロジックを実装（risk_based / equal / score）。単元株（lot_size）で丸め、集計投下上限を超える場合はスケーリングして端数をロット単位で補正するロジックを実装。

- リサーチ / ファクター計算（骨組み）
  - `research.factor_research`：DuckDB を入力に取るモジュールを追加（モメンタム / MA200 / ATR / 流動性等の計算方針を実装予定。モジュール冒頭と一部関数を実装中）。

### 変更 (Changed)
- DB 初期化
  - `init_monitoring_db` を実行して監視テーブルの存在を保証（冪等に DB 準備を行う）。`run_execution` と `run_monitoring` の起動時に呼び出すようにしている。

- ログ出力先・レベル決定ロジックの統一
  - 全スクリプトで `setup_logging(app_name=...)` を利用することを想定し、ログの一貫性を確保。

- .env 読み込みポリシー
  - OS 環境変数を保護しつつ `.env` / `.env.local` をロードする仕組みに変更。`.env.local` は `.env` 上書き（ただし OS 環境変数は保護）。

### 修正 (Fixed)
- 健全性向上・堅牢化
  - `MONITOR_POLL_INTERVAL` のパースで不正値（0 以下・非数）を検出した際にフォールバックし、警告ログを出すようにした（time.sleep の ValueError を回避）。
  - `paper_verification_report` で対象テーブルが存在しない場合に発生する sqlite3.OperationalError をキャッチしてレポート処理を継続可能にした（データ不足時は N/A として扱う）。
  - ログディレクトリ作成に失敗した場合でもコンソール出力のみで動作を継続するようにし、例外による起動停止を防止。
  - process_priority / set_cpu_affinity は権限エラーや未対応 API を安全にハンドリングし、失敗時に警告を出してスキップするように改良。

### ドキュメント（補足）
- 各モジュールに簡易的な docstring と使用例を追加してコードの用途を明示（config_setup, validate_config, logging_setup, run_* スクリプト等）。
- PortfolioConstruction.md / StrategyModel.md 等の外部設計文書への参照コメントをソース内に記載。

### セキュリティ (Security)
- `.env` ファイル生成ウィザードにおいてシークレット項目（トークン・パスワード）は画面表示をマスクして扱う（ファイル生成自体はローカルで行うことを想定。`.env` を Git にコミットしない旨を明記）。

---

注記:
- 本 CHANGELOG はソースコードから推測可能な変更点・仕様に基づいて作成しています。実際の変更履歴やリリースノートはコミット履歴やリリースドキュメントを参照してください。