# Changelog

すべての注目すべき変更点はここに記録します。  
形式は "Keep a Changelog" に準拠します。

最新: [0.1.0] - 2026-04-20

## [Unreleased]
（なし）

## [0.1.0] - 2026-04-20
初回リリース。日本株自動売買システム "KabuSys" のコアユーティリティ、ランナー、ポートフォリオ構築ロジック、設定ツールなどを追加。

### Added
- 基本パッケージ情報
  - パッケージバージョンを `__version__ = "0.1.0"` として追加。

- 起動スクリプト / ランナー
  - run_execution.py
    - ExecutionEngine の起動スクリプトを追加。
    - プロセス優先度を "high" に設定（起動時）。
    - KABUSYS_ENV が `paper_trading` の場合は専用の paper_trading 用 SQLite DB（PAPER_TRADING_SQLITE_PATH）を使用し、本番 DB と明確に分離。
    - BrokerClientFactory を用いてブローカークライアントを生成し、OrderRepository / OrderManager / RiskManager / Reconciler を組み立てて ExecutionEngine をスレッドで起動。
    - 停止制御: プロジェクトルートの `data/stop_requested.flag` を監視し、検知時にエンジンを安全に停止。
    - PID ファイルのサポート（`data/execution.pid` デフォルト）。
    - 起動時に監視テーブルの初期化を保証（冪等な init_monitoring_db 呼び出し）。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL` で上書き可能（デフォルト 60 秒）。不正値はログ警告のうえデフォルトへフォールバック。
    - Monitoring は KABUSYS_ENV にかかわらず本番用 `sqlite_path` を使用（監視データは本番 DB に記録）。

- 設定管理
  - config.py
    - .env 自動読み込み機能を実装（プロジェクトルート検出: `.git` または `pyproject.toml` を起点）。
    - `.env` / `.env.local` の読み込み順と上書きルール（OS 環境変数を保護）を実装。自動ロードを無効化するための `KABUSYS_DISABLE_AUTO_ENV_LOAD` をサポート。
    - .env パースの堅牢化（export 形式、クォート内のエスケープ、コメント処理など）。
    - Settings クラスで各種設定プロパティを提供（J-Quants / kabu API / LINE / DB / 監視閾値 / システムフラグ等）。
    - PAPER_FILL_MODE のバリデーション（有効値: "instant" / "partial" / "never" / "reject"）。
    - KABUSYS_ENV / LOG_LEVEL の妥当性チェックと is_live / is_paper / is_dev ヘルパープロパティ。
  - config_setup.py
    - 対話式ウィザードで `.env` の初期作成・更新を支援する CLI を追加。
    - 秘匿項目は表示マスク、選択肢の検証、既存 .env の読み込み・再利用、保存確認を実装。

- 設定検証ツール
  - validate_config.py
    - .env と config/*.yaml の検証 CLI を追加（--strict で警告を FAIL 扱い）。
    - 必須環境変数チェック、KABUSYS_ENV の妥当性チェック、LOG_LEVEL チェック、DB パスの親ディレクトリ存在チェック、YAML パースチェック（PyYAML 未インストール時は警告）、本番環境向けの追加ガード（LINE 通知設定や KILL_FLAG_CLEAR_ON_START）を実装。

- ロギング・プロセスユーティリティ
  - utils/logging_setup.py
    - ルートロガーに StreamHandler (stdout) と TimedRotatingFileHandler（日次・30日保持）を設定するユーティリティを追加。
    - ログレベル解決順: 引数 > 環境変数 LOG_LEVEL > デフォルト "INFO"。
    - ログディレクトリ解決順: 引数 > 環境変数 LOG_DIR > デフォルト "logs/"。ディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
    - stdout を使用することで外部スケジューラとの連携を想定。
  - utils/process_priority.py
    - Windows / POSIX を吸収するプロセス優先度設定ユーティリティを追加。
    - nice / priority_class の安全な呼び出しとアクセス権限不足時のフォールバック（警告）を実装。
    - CPU affinity を最初の N コアに固定する set_cpu_affinity を実装（権限不足時は警告してスキップ）。

- ポートフォリオ構築ライブラリ（純関数群）
  - portfolio/portfolio_builder.py
    - シグナル選定 select_candidates（score 降順、signal_rank タイブレーク）。
    - 等配分 calc_equal_weights。
    - スコア加重 calc_score_weights（全スコア0 の場合は等配分にフォールバックし WARNING）。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中上限を超える場合に新規候補を除外するロジック（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: 市場レジームに応じた投下比率乗数（bull/neutral/bear）と未知レジームのフォールバック（1.0）。
  - portfolio/position_sizing.py
    - calc_position_sizes: allocation_method ("risk_based", "equal", "score") に基づく発注株数決定ロジックを実装。
    - 単元株（lot_size）丸め、1銘柄上限（max_position_pct）、全体投下上限（available_cash による aggregate cap）、cost_buffer による保守的なコスト見積り、スケーリングと端数配分アルゴリズムを実装。
    - 価格欠損時の安全なスキップとログ出力。

- 解析 / リサーチ
  - research/factor_research.py（実装途中を含む）
    - モメンタム / MA / ATR / 出来高等のファクター計算方針と定数を定義。
    - DuckDB 接続を利用した prices_daily / raw_financials ベースの計算を想定。
    - （ファイル末尾で実装途中の箇所あり）

- Tools
  - tools/paper_verification_report.py
    - Paper Trading 用検証レポートジェネレータを追加。
    - PAPER_TRADING_SQLITE_PATH（または --db）で指定した SQLite DB からシステム稼働率、注文成功率、送信率、リスク却下数、API レイテンシ（P95 含む）を集計・表示。
    - Pass/Fail の閾値を定義（稼働率 >= 99%、注文成功率 >= 90%、送信率 >= 95%、P95 <= 200ms）。
    - 日付フィルタ（--from / --to）対応。DB 未存在やテーブル欠如時の堅牢なフォールバックを実装。

- その他
  - monitoring.monitoring_db.init_monitoring_db の呼び出しを起動シーケンスに組み込み、必要テーブルの存在を保証。
  - 停止フラグ（data/stop_requested.flag）・キルフラグ関連の設定プロパティ（kill_flag_path / kill_flag_clear_on_start）を Settings に追加。
  - デフォルトパスを明文化: DuckDB `data/kabusys.duckdb`、SQLite `data/monitoring.db`、paper trading DB `data/paper_trading.db`、ログ `logs/`。

### Changed
- 該当なし（初回リリース）

### Fixed
- 該当なし（初回リリース）

### Deprecated
- 該当なし（初回リリース）

### Removed
- 該当なし（初回リリース）

### Security
- 該当なし（初回リリース）

---

導入メモ / 注意点:
- .env は絶対にコミットしないこと（config_setup が注意喚起を出す）。
- 本番運用時は KABUSYS_ENV=live に注意（validate_config で警告が発せられる）。特に KILL_FLAG_CLEAR_ON_START は本番で `0` を推奨。
- 実行ユーザーの権限によりプロセス優先度設定や CPU affinity の適用に失敗する可能性がある（ログに警告）。
- run_execution は paper_trading と本番 DB を分離しているため、ペーパートレードの検証データが本番 DB に混在することはない。
- research/factor_research.py は実装途中の箇所があるため、利用時は注意。

（必要に応じて今後のリリースで変更履歴を更新してください。）