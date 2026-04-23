# Changelog

すべての重要な変更点をここに記録します。本ファイルは「Keep a Changelog」記法に準拠します。バージョン番号はパッケージの __version__（src/kabusys/__init__.py）に合わせています。

## [Unreleased]

- なし

## [0.1.0] - 2026-04-23

初回公開リリース。以下の主要機能とユーティリティを実装しています。

### Added
- 実行・監視用エントリポイントスクリプトを追加
  - src/kabusys/run_execution.py
    - ExecutionEngine を起動するランチャー。
    - KABUSYS_ENV=paper_trading の場合は専用の Paper Trading 用 SQLite（data/paper_trading.db など）を使用して本番 DB と完全に分離。
    - 停止を指示するファイル（data/stop_requested.flag）と PID ファイル（data/execution.pid）に対応。
    - 起動時にプロセス優先度を "high" に設定。
    - DuckDB と SQLite（監視用テーブル保証のため init_monitoring_db を呼ぶ）を接続。
    - スレッドで ExecutionEngine.run_session をデーモン実行し、stop flag 検知で安全に停止するループを実装。
  - src/kabusys/run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒、無効値は警告してデフォルトにフォールバック）。
    - 監視は環境にかかわらず本番 sqlite_path を使用する（監視データは監視 DB に保存）。
    - 停止フラグ検知でループを終了。

- 設定管理・自動読み込み
  - src/kabusys/config.py
    - .env 自動読み込み機能を実装（プロジェクトルートを .git または pyproject.toml から探索）。
    - .env と .env.local を読み込み（OS 環境変数は保護）、export プレフィックスやクォート付き値、インラインコメント等を考慮したパーサを実装。
    - 各種設定をプロパティとして提供（J-Quants、kabu API、LINE、DuckDB/SQLite パス、PID/kill flag、閾値、環境判定など）。
    - PAPER_FILL_MODE の検証（instant/partial/never/reject）や KABUSYS_ENV / LOG_LEVEL の検証を実施。

- 設定ウィザード CLI
  - src/kabusys/config_setup.py
    - 対話式ウィザードで .env の初期作成・更新を支援。
    - シークレット項目はマスク表示、選択肢/デフォルト表示、既存 .env 読み込み・利用が可能。
    - 最終確認の上で .env を書き出す helper を提供。

- 設定検証 CLI
  - src/kabusys/validate_config.py
    - 起動前に .env と config/*.yaml の設定不備を検出する CLI。
    - 必須環境変数チェック、KABUSYS_ENV と LOG_LEVEL の妥当性確認、DB パス親ディレクトリ存在チェック、config/*.yaml の存在確認および PyYAML があればパース検証を行う。
    - --strict オプションで警告を FAIL 扱いにできる。
    - 本番（live）環境向けの追加ガード（LINE トークン未設定や KILL_FLAG_CLEAR_ON_START の危険設定の警告）を実装。

- ロギング・プロセスユーティリティ
  - src/kabusys/utils/logging_setup.py
    - ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（日次・30 日保持）を設定するユーティリティ。
    - ログレベル・ログディレクトリの解決順を実装。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソール出力のみで継続。
  - src/kabusys/utils/process_priority.py
    - Windows / POSIX を吸収したプロセス優先度設定（psutil を使用）。
    - cpu_affinity 設定ユーティリティを提供。
    - アクセス拒否や未サポート API に対しては警告を出して安全にフォールバック。

- ポートフォリオ構築ライブラリ
  - src/kabusys/portfolio/portfolio_builder.py
    - 候補選定（スコア降順、signal_rank を tie-breaker）select_candidates。
    - 等金額配分 calc_equal_weights、スコア加重配分 calc_score_weights（全スコアが 0 の場合は等金額へフォールバック）。
  - src/kabusys/portfolio/position_sizing.py
    - 各銘柄の発注株数計算を実装（risk_based / equal / score の割当方式対応）。
    - 単元株（lot_size）丸め、1 銘柄上限・aggregate cap、cost_buffer（手数料・スリッページ見積り）を考慮したスケーリングロジックを実装。
  - src/kabusys/portfolio/risk_adjustment.py
    - セクター集中上限チェック apply_sector_cap（既存保有のセクター別エクスポージャ計算と新規候補の除外）。
    - 市場レジームに応じた投下資金乗数 calc_regime_multiplier（bull/neutral/bear に対応、未知レジームはフォールバックして警告）。

- Paper Trading 検証ツール
  - src/kabusys/tools/paper_verification_report.py
    - Paper Trading 用 SQLite を解析して検証レポートを生成するスクリプト。
    - 稼働率（uptime）、注文成功率、送信率、リスク却下数、API レイテンシ（avg/max/P95）等を集計。
    - P95（95パーセンタイル）計算、しきい値による PASS/FAIL 判定を実装。
    - コマンドライン引数 --from/--to/--db をサポート。

- 分析・リサーチ基盤（初期）
  - src/kabusys/research/factor_research.py
    - モメンタム等のファクター計算方針と定数を追加。DuckDB を用いた prices_daily / raw_financials 参照を想定した設計。
    - 主要定数（モメンタム窓、MA200、ATR、volume window 等）と calc_momentum の骨組みを実装開始（詳細計算は続きあり）。

- パッケージ情報
  - src/kabusys/__init__.py にて __version__ = "0.1.0" を設定。

### Changed
- なし（初回リリース）

### Fixed
- なし（初回リリース）

### Notes / Implementation details
- .env パーサは export プレフィックス、クォート（シングル/ダブル）とバックスラッシュエスケープ、インラインコメント判定（非クォート時に # の直前がスペース/タブの場合）を考慮した堅牢な実装になっています。
- logging_setup は標準出力を stdout に向ける設計（cron 等で stdout/stderr を一本化する運用を想定）。
- process_priority はプラットフォーム差異を吸収するために psutil の定数や nice 値を利用し、失敗時は警告して続行します。
- run_monitoring は監視用 DB に対して冪等にテーブル初期化（init_monitoring_db）を行うことで監視テーブルの存在を保証します。
- Paper Trading（is_paper）時の DB 分離や MockBrokerClient の採用は本番データと完全に分離する運用を意図しています。

---

この CHANGELOG は、提供されたコードから推測される実装・動作に基づいて作成しています。実際のリリースノート作成時はリポジトリのコミット履歴・リリース方針に合わせて適宜調整してください。