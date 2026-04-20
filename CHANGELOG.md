# CHANGELOG

すべての変更は [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) に準拠します。  
このプロジェクトのバージョンは `src/kabusys/__init__.py` の `__version__` に従います。

## [0.1.0] - 2026-04-20

### Added
- 初回リリース。
- 実行用スクリプト / CLI を追加:
  - run_monitoring (src/kabusys/run_monitoring.py)
    - SystemMonitor のポーリングループ起動スクリプト。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止はプロジェクトの data/stop_requested.flag ファイルで検知。
    - Monitoring は KABUSYS_ENV にかかわらず本番用の `sqlite_path` を使用する設計。
  - run_execution (src/kabusys/run_execution.py)
    - ExecutionEngine 起動スクリプト。
    - `KABUSYS_ENV=paper_trading` の場合、MockBrokerClient（Factory経由）を使用し、Paper Trading 用 DB（`data/paper_trading.db` または `PAPER_TRADING_SQLITE_PATH`）に記録して本番 DB と分離。
    - 実行中の PID 管理・停止フラグ検知をサポート。
  - validate_config (src/kabusys/validate_config.py)
    - .env と config/*.yaml の起動前チェックツール。`--strict` オプションで警告を失敗扱いにできる。
    - 必須環境変数、KABUSYS_ENV の妥当性、ログレベル、DB パス、YAML ファイルの存在とパース（PyYAML がない場合は警告）などを検査。
    - live 環境向けの追加ガード（LINE 通知設定や Kill Switch の設定確認）。
  - config_setup (src/kabusys/config_setup.py)
    - 対話式ウィザードで .env を初期生成 / 更新するユーティリティ。
    - 選択肢、デフォルト、シークレット入力、既存値の取り込み、確認プロンプト、ファイル書き出しをサポート。
  - tools.paper_verification_report (src/kabusys/tools/paper_verification_report.py)
    - Paper Trading データベースから検証レポートを生成する CLI。
    - 稼働率、注文成功率、送信率、リスク却下数、レイテンシ (avg/max/P95) を算出し、PASS/FAIL 判定を行う。期間フィルタと DB ファイル指定オプションをサポート。
- 環境・設定管理:
  - Settings クラス (src/kabusys/config.py)
    - .env 自動ロード機構（プロジェクトルートの検出: .git / pyproject.toml を基準）。
    - .env の読み込み順序: OS 環境 > .env.local > .env。`KABUSYS_DISABLE_AUTO_ENV_LOAD` で無効化可能。
    - .env パース機能が改良され、`export KEY=...`、クォート文字列、インラインコメントの扱いをサポート。
    - 各種プロパティ追加 / 検証:
      - `paper_fill_mode`（PAPER_FILL_MODE、値検証: instant|partial|never|reject）
      - `paper_sqlite_path`（PAPER_TRADING_SQLITE_PATH）
      - 監視関連設定（pid_file_path, kill_flag_path, kill_flag_clear_on_start など）
      - CPU/Memory/Disk の閾値プロパティ
      - `env` / `log_level` の検証
- ポートフォリオ構築ユーティリティ (src/kabusys/portfolio/*)
  - portfolio_builder
    - select_candidates: スコア降順 + signal_rank タイブレークで候補選定
    - calc_equal_weights / calc_score_weights: 等金額配分、スコアによる配分（全スコア0の時は等配分へフォールバック）
  - risk_adjustment
    - apply_sector_cap: セクター集中上限チェック（既存保有のセクター比率を計算して超過セクターの候補除外。unknown セクターは適用除外）
    - calc_regime_multiplier: レジーム（bull/neutral/bear）に応じた資金乗数の算出（未知レジームは警告のうえ 1.0 でフォールバック）
  - position_sizing
    - calc_position_sizes: allocation_method = "risk_based" / "equal" / "score" をサポート
    - 単元株（lot_size）、max_position_pct、max_utilization、cost_buffer（手数料・スリッページ見積り）、aggregate cap によるスケーリング、端数分配ロジックなどを実装
- ユーティリティ:
  - logging_setup (src/kabusys/utils/logging_setup.py)
    - ルートロガーに StreamHandler (stdout) と TimedRotatingFileHandler（日次、30日保持）を設定する共通設定関数 `setup_logging` を提供。
    - ログディレクトリ作成失敗時はファイル出力をスキップし、標準出力のみで継続するフォールバックあり。
  - process_priority (src/kabusys/utils/process_priority.py)
    - `set_process_priority(level)`：Windows / POSIX を吸収してプロセス優先度（high/normal/low）を設定。アクセス権限がない場合は警告でスキップ。
    - `set_cpu_affinity(cpu_count)`：最初の N コアにプロセスを制限する機能。未対応 OS/権限不足時は警告でスキップ。
- research/factor_research (初期実装)
  - DuckDB 接続を受け取り、Momentum / Value / Volatility / Liquidity 等のファクター算出を行う設計。モメンタム計算の実装が開始（ファイル末尾は未完の状態）。

### Changed
- ログ出力の標準ストリームを stderr ではなく stdout に統一（cron/Task Scheduler でのリダイレクトを想定）。
- run_monitoring: モニタは常に本番用 SQLite パスを使用する明示的な設計に（監視データの分離方針）。
- run_execution: Paper Trading 時は専用 SQLite を使い、本番データと完全分離する設計。
- .env 読み込み挙動:
  - `.env.local` が `.env` を上書きする形で読み込まれる。
  - OS 環境変数は保護され、.env の上書きを防ぐ仕組みを導入。

### Fixed / Robustness improvements
- .env パーサの堅牢化:
  - クォート内のバックスラッシュエスケープを正しく扱うように改善。
  - `export KEY=val` 形式、インラインコメントの取り扱い、空行/コメント行スキップをサポート。
- logging_setup: ログディレクトリ作成失敗時にプロセスが停止しないようにフォールバック処理を追加。
- process_priority / set_cpu_affinity: 異なるプラットフォーム・権限不足に対して安全にフォールバックするよう例外処理を強化。
- paper_verification_report: DB テーブルが存在しない / カラム不足な場合でも sqlite3.OperationalError をハンドリングしてレポート生成が停止しないようにした。

### Notes / Known limitations
- research/factor_research のファイルは未完の箇所があり、モメンタム等のファクター計算は引き続き実装を進める必要があります。
- position_sizing の lot_size は現状グローバル共通（デフォルト 100）で、将来的に銘柄別単元対応へ拡張予定（TODO コメントあり）。
- apply_sector_cap は price_map に価格がない場合に露出が過少見積もられる可能性がある旨の注意書き（将来的にフォールバック価格を導入予定）。

## 開発者向け補足
- 重要な環境変数:
  - JQUANTS_REFRESH_TOKEN (必須)
  - KABU_API_PASSWORD (必須)
  - KABUSYS_ENV (development | paper_trading | live)
  - PAPER_FILL_MODE (instant | partial | never | reject)
  - PAPER_TRADING_SQLITE_PATH（Paper Trading 用 DB パス）
  - MONITOR_POLL_INTERVAL（run_monitoring のポーリング間隔上書き）
  - LOG_DIR / LOG_LEVEL
  - KILL_FLAG_CLEAR_ON_START（本番で 1 にするべきではない旨の警告あり）
- 起動コマンド例:
  - 監視: python -m kabusys.run_monitoring
  - 実行エンジン: python -m kabusys.run_execution
  - 設定検証: python -m kabusys.validate_config
  - .env ウィザード: python -m kabusys.config_setup
  - Paper Trading レポート: python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

--- 

今後のリリースではファクター計算の完成、銘柄別単元対応、より厳密なエラーハンドリングとテストカバレッジの拡充を予定しています。