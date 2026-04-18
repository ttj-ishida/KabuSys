# Changelog

すべての重要な変更点を Keep a Changelog 準拠で日本語で記載します。

フォーマット
- 重要な変更はセクションごとに分類しています: Added / Changed / Fixed / Deprecated / Removed / Security
- バージョン 0.1.0 を初回リリースとして記載しています（開発中の変更は Unreleased に集約）

## [Unreleased]
（現在の差分 — 特にリリース前の作業があればここに記載してください）

---

## [0.1.0] - 2026-04-18
初期リリース

### Added
- プロジェクト全体の初期実装を追加
  - パッケージメタ情報
    - `kabusys.__version__ = "0.1.0"`

- 実行スクリプト
  - `src/kabusys/run_monitoring.py`
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` によりポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止はプロジェクトの `data/stop_requested.flag` ファイルの存在で検知。
    - 監視は環境にかかわらず「本番」用の sqlite パスを使用して接続する仕様。
    - 起動時にプロセス優先度を "high" に設定（`set_process_priority` を呼出し）。

  - `src/kabusys/run_execution.py`
    - ExecutionEngine を起動するスクリプトを追加。
    - `KABUSYS_ENV=paper_trading` の場合はペーパートレード用のモックブローカを用い、専用 DB (`data/paper_trading.db` など) を使用して本番 DB と分離。
    - エンジンはスレッドで実行され、`data/stop_requested.flag` で停止をトリガーできる。
    - 起動時にプロセス優先度を "high" に設定。

- 設定管理
  - `src/kabusys/config.py`
    - .env ファイル（`.env`, `.env.local`）と環境変数の読み込みロジックを実装。
    - 自動ロードを無効化する環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD` に対応。
    - プロジェクトルート検出は `.git` または `pyproject.toml` を探索して判定（CWD に依存しない）。
    - .env の行パースはクォートやエスケープ、コメント処理に対応。
    - 各種設定プロパティを `Settings` クラスとして提供（DB パス、API トークン、PID ファイル等）。
    - Paper Trading 用の挙動（`paper_sqlite_path`, `paper_fill_mode`）をサポート。
    - 環境種別検証（`development` / `paper_trading` / `live`）とログレベル検証を実装。

  - `src/kabusys/config_setup.py`
    - 対話式ウィザードで `.env` を初期作成・更新する CLI を追加。
    - 値の入力補助、既存値の読み込み、シークレット扱い（表示マスク）、デフォルト提示、確認・保存機能を提供。

  - `src/kabusys/validate_config.py`
    - 起動前に .env や config/*.yaml の基本チェックを行う CLI を追加。
    - 必須環境変数のチェック（`JQUANTS_REFRESH_TOKEN`, `KABU_API_PASSWORD` 等）。
    - DB パス、YAML ファイル存在チェック、`KABUSYS_ENV=live` 時の追加ガード（LINE 通知設定や Kill Switch 設定の警告）。
    - `--strict` オプションで警告も失敗（exit 1）扱いにできる。

- ログ・ユーティリティ
  - `src/kabusys/utils/logging_setup.py`
    - 全アプリケーションで使う共通のログ設定ユーティリティを追加。
    - stdout 出力用 StreamHandler と日次ローテーション（TimedRotatingFileHandler）を root ロガーに設定。
    - ログディレクトリ自動作成、ファイルハンドラ作成失敗時のフォールバック対応。
    - ログレベルとログディレクトリの優先解決ルールを実装。

  - `src/kabusys/utils/process_priority.py`
    - Windows / POSIX の差分を吸収するプロセス優先度設定ユーティリティを追加。
    - set_process_priority(level) により "high" / "normal" / "low" を設定（psutil 利用）。アクセス不可時は警告でスキップ。
    - set_cpu_affinity(cpu_count) によりプロセスを最初の N コアにピン固定可能（未指定なら何もしない）。

- Portfolio（ポートフォリオ構築）
  - `src/kabusys/portfolio/portfolio_builder.py`
    - 候補選定（select_candidates：スコア降順 / 同点時は signal_rank ブレーク）を実装。
    - 等配分（calc_equal_weights）およびスコア加重（calc_score_weights、スコアゼロ時は等配分にフォールバック）を実装。

  - `src/kabusys/portfolio/risk_adjustment.py`
    - セクター集中制限（apply_sector_cap）：既存保有のセクター比率が閾値を超える場合に新規候補を除外する処理を実装。
    - レジームに応じた投下資金乗数（calc_regime_multiplier）を実装（bull/neutral/bear とフォールバック挙動を定義）。

  - `src/kabusys/portfolio/position_sizing.py`
    - 各銘柄の発注株数算出ロジック（calc_position_sizes）を実装。
    - risk_based / equal / score の割当方式に対応。
    - 単元株（lot_size）丸め、1銘柄上限および全体の aggregate cap（available_cash）によるスケールダウン、cost_buffer（手数料・スリッページ見積り）を考慮した配分調整を実装。
    - 価格欠損時のスキップやデバッグログなどを備える。

  - `src/kabusys/portfolio/__init__.py` で上記機能を公開。

- Research（研究用）
  - `src/kabusys/research/factor_research.py`
    - モメンタム・ボラティリティ・バリュー等のファクター計算モジュールのスケルトンを追加。
    - DuckDB 接続に対して prices_daily / raw_financials を参照してファクターを算出する設計（calc_momentum を含む一連の定義と定数）。
    - （注）ファイル末尾で実装が途中の箇所あり（calc_momentum の実装断片が存在）。

- Tools
  - `src/kabusys/tools/paper_verification_report.py`
    - Paper Trading の検証レポート生成スクリプトを追加。
    - 指標: 稼働率 (uptime)、注文成功率（fill rate）、送信率（send rate）、API レイテンシ (avg/max/P95) 等を算出。
    - デフォルト DB: `data/paper_trading.db`（環境変数 `PAPER_TRADING_SQLITE_PATH` または `--db` で指定可能）。
    - チェック基準（閾値）を定義（例: uptime >= 99%、fill_rate >= 90%、P95 <= 200 ms）して PASS/FAIL を判定。

- データベース初期化
  - `monitoring_db.init_monitoring_db` を用い、実行／監視スクリプト起動時に監視テーブルが存在することを冪等的に保証。

### Changed
- （なし — 初期リリース）

### Fixed
- （なし — 初期リリース）

### Deprecated
- （なし）

### Removed
- （なし）

### Security
- 機密情報（API トークン等）は .env に格納することを想定。`.env` の Git 管理は行わない旨を `config_setup` のヘッダで明示。

---

注意事項 / 補足
- 環境変数やファイルパスのデフォルト:
  - DUCKDB_PATH: data/kabusys.duckdb
  - SQLITE_PATH: data/monitoring.db
  - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
  - LOG_DIR: logs/
  - MONITOR_POLL_INTERVAL: 60（秒）
- run_monitoring は監視用 DB 接続に sqlite3／duckdb を使用、run_execution は環境に応じて paper_trading 用 DB を切替えます。
- process_priority の設定は OS に依存する操作を含むため、権限不足等で失敗する場合はワーニングでスキップされます。
- research/factor_research.py は設計方針・定数が整備されていますが、実装途中の箇所があるため使用時は確認してください。

もしリリースノートの文言を英語化したい、日付を変更したい、あるいは各変更に対する影響度（breaking / minor / patch）を付けたい場合は知らせてください。