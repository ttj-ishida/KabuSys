# Changelog

すべての変更は Keep a Changelog の形式に従います。  
このプロジェクトはセマンティックバージョニングを採用しています。

## [0.1.0] - 2026-04-23

### Added
- 初回リリース。KabuSys の基本コンポーネントを追加。
- 起動スクリプト
  - run_monitoring.py
    - SystemMonitor のポーリングループを起動するスクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止はプロジェクト直下の data/stop_requested.flag ファイルの存在検知で行う。
    - Monitoring は KABUSYS_ENV にかかわらず本番用 sqlite_path を使用する設計。
  - run_execution.py
    - ExecutionEngine（発注エンジン）を起動するスクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、ペーパートレード専用 DB（デフォルト data/paper_trading.db）に記録して本番 DB と分離。
    - 停止フラグ（data/stop_requested.flag）および実行 PID ファイル管理（data/execution.pid）に対応。
- 設定管理
  - config.py
    - .env 自動読み込み（プロジェクトルートの検出: .git または pyproject.toml が基準）。
    - .env の行パーサを実装: export プレフィックス対応、クォート（シングル/ダブル）とバックスラッシュエスケープ、インラインコメント処理（適切な条件のみでコメント扱い）。
    - Settings クラスを追加し、環境変数をラップしてプロパティ経由で取得（バリデーション含む）。
    - 各種デフォルトパス（DUCKDB_PATH、SQLITE_PATH、PAPER_TRADING_SQLITE_PATH 等）およびログ・監視閾値の設定を提供。
    - PAPER_FILL_MODE のバリデーション（instant/partial/never/reject）。
- 設定ユーティリティ / CLI
  - config_setup.py
    - .env 作成・更新の対話式ウィザードを追加。シークレットはマスク表示、デフォルト値や選択肢を提示。
    - .env をテンプレート形式で書き出す機能を提供（Git にコミットしない旨のヘッダ付き）。
  - validate_config.py
    - .env および config/*.yaml の設定整合性検証 CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性確認、DB パスの親ディレクトリ存在チェック、PyYAML が有れば YAML のパース検証を実施。
    - --strict オプションで警告を FAIL 扱いにできる。
- ログ & プロセスユーティリティ
  - utils/logging_setup.py
    - ルートロガーを統一的に設定するユーティリティを追加。
    - StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション、30日分保持）を設定。
    - 既存ハンドラをクリアして二重設定を防止。
    - ログディレクトリ作成に失敗した場合はファイル出力をスキップしてコンソール出力のみで継続。
  - utils/process_priority.py
    - Windows と POSIX（Linux/Mac 等）でプロセス優先度（nice / HIGH_PRIORITY_CLASS 等）を跨いで設定するユーティリティを追加。
    - set_cpu_affinity によりプロセスを最初の N コアにピン留めする機能を提供。
    - 権限不足や未対応プラットフォームでは安全にスキップして警告ログを出す。
- ポートフォリオ構築モジュール（純粋関数、DB 参照なし）
  - portfolio/portfolio_builder.py
    - 銘柄候補選定（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）を実装。スコア全てが 0 の場合は等配分へフォールバック。
  - portfolio/risk_adjustment.py
    - セクター集中制限の適用（apply_sector_cap）と市場レジームに応じた投下資金乗数（calc_regime_multiplier）を実装。
    - 不明セクター ("unknown") はセクター上限の対象外として扱う仕様。
  - portfolio/position_sizing.py
    - 発注株数計算（calc_position_sizes）を実装。allocation_method は "risk_based" / "equal" / "score" をサポート。
    - 単元株（lot_size）で切り上げ/切り下げ、1 銘柄上限・集計上限（available_cash）を考慮したスケーリングロジックを実装。cost_buffer により手数料やスリッページを保守的に見積もる。
- 研究用モジュール（雛形）
  - research/factor_research.py
    - DuckDB を用いたモメンタム等ファクター計算の骨組みを追加（prices_daily / raw_financials を前提）。（関数が途中まで実装済）
- ツール
  - tools/paper_verification_report.py
    - Paper Trading の検証レポート生成スクリプトを追加。
    - 稼働率、注文成功率、送信率、レイテンシ（P95）等を計算し PASS/FAIL 判定（閾値はソース内で定義）。
    - 日付フィルタ（--from / --to）や DB パスの指定（--db / PAPER_TRADING_SQLITE_PATH）に対応。
- パッケージ情報
  - __init__.py にバージョン 0.1.0 を設定。

### Changed
- ロギングのデフォルト挙動
  - StreamHandler を stdout に向けることで、cron / Task Scheduler 等で stdout/stderr を一本化して扱いやすくした。
- DB 周りの起動時前処理
  - run_execution.py では監視テーブルが存在することを保証するために init_monitoring_db を呼び出す（冪等）。
- 起動スクリプトのプロセス優先度設定を起動直後に実行するよう統一（set_process_priority("high") を利用）。

### Fixed
- 環境ファイルパーサの細かな取り扱いを改善
  - export プレフィックス対応、クォート内のバックスラッシュエスケープ、インラインコメントの判定ルールを実装して .env の互換性を向上。
- run_monitoring のポーリング間隔読み取り
  - MONITOR_POLL_INTERVAL が不正（非整数や <= 0）のときにデフォルトにフォールバックし警告を出す処理を追加し、time.sleep に渡した際の ValueError を回避。

### Security
- （なし）

### Notes / Usage highlights
- .env 自動ロード
  - 起動時に OS 環境変数を優先し、プロジェクトルートの .env（未上書き）→ .env.local（上書き可）の順で自動読み込みを行う。自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- Paper Trading と Live のデータ分離
  - run_execution は paper_trading 環境時に専用 SQLite（PAPER_TRADING_SQLITE_PATH）を使用するため、本番データと分離された検証が可能です。
- ログの永続化
  - 日次ローテーション（logs/<app_name>.log）を標準で行います。ログディレクトリ作成に失敗した場合はコンソール出力のみで継続します。
- CLI
  - 設定ウィザード: python -m kabusys.config_setup
  - 設定検証: python -m kabusys.validate_config [--strict]
  - Paper 検証レポート: python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]

もしリリースノートや CHANGELOG の形式に追記したい項目（例: 既知の問題、将来の TODO、リリース日を別にしたい等）があれば指示ください。