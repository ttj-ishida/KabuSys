CHANGELOG
=========

すべての注目すべき変更点をこのファイルに記録します。  
フォーマットは "Keep a Changelog" に準拠しています（セクション: Added / Changed / Fixed / ...）。  

[Unreleased]
------------

なし

[0.1.0] - 2026-04-25
--------------------

初回リリース。自動売買フレームワーク KabuSys の基礎機能を実装しました。

### Added
- パッケージ基本情報
  - パッケージバージョンを src/kabusys/__init__.py にて v0.1.0 として公開。

- 実行用エントリスクリプト
  - run_execution.py
    - ExecutionEngine を起動するスクリプト。
    - KABUSYS_ENV=paper_trading の場合はペーパートレード用 DB（data/paper_trading.db）および MockBrokerClient を使用して本番 DB と完全に分離。
    - 起動時にプロセス優先度を High に設定する処理を実行。
    - 停止フラグ（data/stop_requested.flag）と実行 PID 管理（data/execution.pid）に対応。スレッド実行・安全停止ロジックを実装。
    - DuckDB と SQLite の接続を作成し、監視テーブルの存在を保証（init_monitoring_db を呼び出し、冪等性を確保）。

  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト。
    - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で上書き可能（デフォルト 60 秒）。不正値は警告を出してデフォルトにフォールバック。
    - 実行環境にかかわらず本番 sqlite_path（設定値）を監視 DB に使用（監視は本番 DB を参照）。
    - 停止フラグ（data/stop_requested.flag）検知でループを終了。
    - 起動時にプロセス優先度を High に設定。

- 設定管理・補助ツール
  - config.py
    - .env 自動ロード機能（プロジェクトルート検出: .git または pyproject.toml を基準）。
    - .env ファイルパースの堅牢化（export プレフィックス、クォート文字・エスケープ、行末コメント処理等に対応）。
    - 環境変数取得ヘルパ Settings クラスを提供（DB パス、PID ファイル、監視閾値、paper/trading のフラグ等）。
    - PAPER_FILL_MODE の有効値チェックや KABUSYS_ENV / LOG_LEVEL の検証を実装。
  - config_setup.py
    - 対話式 .env ウィザード。主要環境変数の初期作成・更新を支援。
    - 生成される .env に注意書き（.env をコミットしない）を付記。
  - validate_config.py
    - 起動前検証 CLI。必須環境変数、KABUSYS_ENV, LOG_LEVEL、DB パス、config/*.yaml の存在・パース（PyYAML が存在する場合）をチェック。
    - --strict モードで警告も失敗扱いにできる。

- ポートフォリオ構築ライブラリ（純粋関数群：メモリ内計算）
  - portfolio/portfolio_builder.py
    - select_candidates: スコア降順かつ signal_rank のタイブレークで候補選定。
    - calc_equal_weights: 等金額配分。
    - calc_score_weights: スコア正規化配分（全スコアが 0 の場合は等配分にフォールバック）。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中制限ロジック（既存ポジションのセクター比率が閾値を超える場合、新規候補を除外）。"unknown" セクターは制限対象外。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull/neutral/bear のマッピング。未知レジームはフォールバックで 1.0）。
  - portfolio/position_sizing.py
    - calc_position_sizes: allocation_method("risk_based" / "equal" / "score") に基づく株数算出。
    - risk_based: 許容リスク・損切り率からベース株数を算出し単元株（lot_size）に丸め。
    - equal/score: ウェイトに基づく配分、per-position と aggregate の上限および cost_buffer（手数料・スリッページ見積り）を考慮したスケーリング／端数処理を実装。

- 分析・DB 関連
  - DuckDB の接続を利用する設計を採用（設定で duckdb_path を指定、デフォルト data/kabusys.duckdb）。
  - 監視 DB（SQLite）初期化ユーティリティ（init_monitoring_db を run スクリプトから呼び出し）。

- ユーティリティ
  - utils/logging_setup.py
    - ルートロガーへ StreamHandler (stdout) と TimedRotatingFileHandler（日次ローテート、30日保持）を設定する共通セットアップ関数を実装。
    - ログディレクトリ作成失敗時はファイル出力をスキップして stdout のみで継続するフォールバックを実装。
  - utils/process_priority.py
    - psutil を利用してプロセス優先度（high/normal/low）と CPU affinity を設定するユーティリティを提供。
    - Windows と POSIX 系（Linux / Darwin / FreeBSD）で差分を吸収する実装。失敗時は警告でスキップ。

- ツール
  - tools/paper_verification_report.py
    - ペーパートレード用 SQLite DB（PAPER_TRADING_SQLITE_PATH）を参照して検証レポートを生成する CLI ツール。
    - 指標: 稼働率（uptime_pct）、注文成功率（fill_rate）、送信率（send_rate）、API レイテンシ（avg, max, P95）等。
    - デフォルトの合格閾値（例: uptime >= 99.0%、fill_rate >= 90% 等）を定義し PASS/FAIL 判定を出力。
    - 日付フィルタ（--from/--to）と DB パス指定（--db）に対応。

- 研究モジュール（進行中）
  - research/factor_research.py
    - ファクター計算（Momentum / Value / Volatility / Liquidity）の設計と一部実装。DuckDB の prices_daily / raw_financials を前提に計算する設計。
    - モメンタム計算関数 calc_momentum の骨格を実装（実装途中でファイル末尾が切れているため継続が必要）。

### Changed
- 初回リリースのため変更履歴なし

### Fixed
- 初回リリースのため修正履歴なし

Notes / 注意事項
- .env の自動ロードはデフォルトで有効。自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- PAPER_TRADING 環境では DB/ブローカーが本番と分離される設計ですが、設定ミスにより本番 DB を参照してしまうリスクがあるため .env の設定と validate_config の使用を推奨します。
- run_monitoring は監視 DB に対して本番 sqlite_path を使用する設計（監視は本番状態を想定）。
- process_priority / cpu_affinity の設定は環境（権限・OS）に依存し、失敗した場合はログに警告を出して継続します。
- research/factor_research.py は未完の箇所があり、完全実装を行う必要があります（特に calc_momentum の続き）。

今後の予定（例）
- factor_research の完成（ファクター群の完全実装と単体テスト）。
- ExecutionEngine / RiskManager / Reconciler の詳細実装およびエンドツーエンドテスト。
- CI による validate_config・静的解析の自動化。
- ドキュメント（PortfolioConstruction.md / StrategyModel.md 等）のリファレンスとコードの整合性チェック。

---