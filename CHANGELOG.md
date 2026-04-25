# CHANGELOG

すべての変更は Keep a Changelog の形式に準拠して記載しています。重要な動作や外部インタフェース（環境変数・ファイル・CLI 等）の変更点は明記しています。

全般: 初回リリース（v0.1.0）

## [0.1.0] - 2026-04-25

### Added
- 実行用スクリプトを追加
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。停止はプロジェクトの data/stop_requested.flag ファイルで制御。例外発生時はログを出して次回ポーリングに続行する実装。ファイル: src/kabusys/run_monitoring.py
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。KABUSYS_ENV=paper_trading の場合は専用のペーパートレード用 SQLite（data/paper_trading.db がデフォルト）を使用し、本番 DB と分離。停止フラグと実行 PID ファイルに対応。ファイル: src/kabusys/run_execution.py

- 設定・環境管理
  - Settings クラス（src/kabusys/config.py）を追加。環境変数に基づく設定取得を統一（DB パス、ログレベル、環境種別、ペーパートレード設定等）。KABUSYS_ENV の値検証（development/paper_trading/live）や PAPER_FILL_MODE の有効値チェックなどを提供。
  - .env 自動ロード機能を実装（プロジェクトルート判定は .git または pyproject.toml）。自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を使用可能。

- 設定補助ツール
  - config_setup.py: 対話式ウィザードで .env を作成・更新する CLI を追加。既存 .env の読み込みとマスク表示、項目ごとの説明・デフォルト値を提供。ファイル出力テンプレート（.env）を生成。ファイル: src/kabusys/config_setup.py
  - validate_config.py: 起動前チェック用 CLI を追加。.env および config/*.yaml の存在・基本整合性を検証。--strict オプションで警告を失敗扱いにできる。PyYAML 未インストール時は YAML 検証をスキップして警告を表示。ファイル: src/kabusys/validate_config.py

- ロギング・プロセス制御ユーティリティ
  - setup_logging（src/kabusys/utils/logging_setup.py）:
    - ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（日次、30日保持）を設定するユーティリティを追加。
    - ログディレクトリの自動作成、作成失敗時はファイル出力をスキップしてコンソールのみで継続。
    - ログレベル解決順（引数 > LOG_LEVEL 環境変数 > デフォルト）。
  - process_priority（src/kabusys/utils/process_priority.py）:
    - Windows と POSIX（Linux/Mac 等）両対応のプロセス優先度設定を提供（high/normal/low）。CPU affinity を最初の N コアに固定する関数も追加。

- ポートフォリオ構築（純粋関数群）
  - portfolio_builder（src/kabusys/portfolio/portfolio_builder.py）:
    - select_candidates: BUY シグナルのスコア降順選定（同点時は signal_rank でブレーク）を実装。
    - calc_equal_weights / calc_score_weights: 等金額・スコア加重の重み計算を実装。全銘柄のスコアが 0 の場合は等金額配分にフォールバック。
  - risk_adjustment（src/kabusys/portfolio/risk_adjustment.py）:
    - apply_sector_cap: セクターごとの既存エクスポージャが閾値を超える場合にそのセクターの新規候補を除外する機能。
    - calc_regime_multiplier: マーケットレジーム（bull/neutral/bear）に応じた投下資金乗数を返す関数を実装（未知レジームは 1.0 にフォールバックして警告）。
  - position_sizing（src/kabusys/portfolio/position_sizing.py）:
    - calc_position_sizes: allocation_method（risk_based/equal/score）に応じた発注株数計算を実装。単元株（lot_size）で丸め、1 銘柄上限・aggregate cap（利用可能現金）に基づくスケーリング、cost_buffer を用いた保守的見積り、スケールダウン時の端数配分ロジックなどを搭載。

- Paper Trading 検証ツール
  - tools/paper_verification_report.py: ペーパートレード用 SQLite を読み取り、稼働率、注文成功率、送信率、レイテンシ（avg/max/P95）などを集計し、PASS/FAIL 判定を行うレポート生成スクリプトを追加（閾値はソースで定義: 稼働率 99% 等）。P95 計算、日付フィルタ、DB 存在チェックに対応。ファイル: src/kabusys/tools/paper_verification_report.py

- research/factor_research.py（計算骨格）
  - DuckDB を用いたファクター計算の骨格と定数群を追加（モメンタム / MA / ATR / 流動性等を想定）。（実装は続きが必要な箇所あり）

- パッケージ初期化
  - __init__.py にバージョン定義 __version__ = "0.1.0" を追加。パッケージ公開用の __all__ を設定。

### Changed
- DB/監視の挙動
  - run_monitoring は KABUSYS_ENV に関わらず本番用 sqlite_path を使用する旨を明示（監視データは本番 DB パスに集約）。ファイル: src/kabusys/run_monitoring.py
  - run_execution は paper_trading 環境時にペーパートレード専用 SQLite を使用して本番 DB とログを完全に分離する設計に変更。ファイル: src/kabusys/run_execution.py

- .env 読み込みの挙動改善
  - .env 行のパーサーで export KEY=val 形式やシングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメントの扱いを強化（src/kabusys/config.py）。
  - .env の読み込み順は OS 環境変数 > .env.local > .env。OS 側の既存環境変数は保護される（protected set）。自動読み込みを無効化するための KABUSYS_DISABLE_AUTO_ENV_LOAD を追加。

- ログ出力先
  - ログのコンソール出力を stderr ではなく stdout に出力するように明示（cron や外部リダイレクト運用を想定）。ファイル: src/kabusys/utils/logging_setup.py

- 例外処理・耐障害性
  - run_monitoring のループで monitor.check_once() が例外を投げてもループ継続するように logger.exception によるログ出力後に次ポーリングへ移行する実装に変更（耐障害性向上）。ファイル: src/kabusys/run_monitoring.py
  - DB ハンドラ生成やログディレクトリ作成に失敗した場合でもアプリケーションが継続するようフォールバック（ファイルログ無効化してコンソール出力のみ）するように改善。

### Fixed
- .env パーサーの改善により、クォート付き値内のエスケープ（バックスラッシュ）やコメントの誤解析を修正（src/kabusys/config.py）。
- process_priority.set_process_priority でサポート外 OS の場合に落ちないように警告を出してスキップすることで未対応環境でのクラッシュを回避（src/kabusys/utils/process_priority.py）。

### Notes / Implementation details
- DuckDB と SQLite の併用
  - 分析・集計用途は DuckDB（設定: DUCKDB_PATH）、監視・トレードログ等は SQLite（SQLITE_PATH / PAPER_TRADING_SQLITE_PATH）を使い分ける設計。多くのコンポーネントで両接続を受け取る実装になっています。

- PID/停止フラグ / Kill Switch
  - 実行制御は data ディレクトリ内のフラグファイル（stop_requested.flag / execution.pid / kill.flag）を用いる設計。Settings で各種パスが取得可能。

- 将来の拡張に関するTODO
  - position_sizing における銘柄ごとの lot_size を stocks マスタへ持たせるなどの拡張を想定した設計注記あり。
  - research/factor_research.py はファクター計算の骨格を実装済みだが、完全実装には続きが必要（ファイル末尾で途切れている箇所あり）。

### Removed
- なし

### Security
- 特に無し（ただし .env の扱いについて「決して Git にコミットしない」旨を README/テンプレートに記載）。

---

このリリースは初期実装群のまとめです。各モジュールはユニットテストと統合テストにより追加検証を推奨します。運用時は .env と kill/stop フラグの取り扱い、KABUSYS_ENV と PAPER_TRADING_SQLITE_PATH の設定に注意してください。