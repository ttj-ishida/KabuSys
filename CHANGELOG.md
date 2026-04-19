# CHANGELOG

すべての重要な変更をここに記録します。フォーマットは Keep a Changelog に準拠しています。  

最新リリース: 0.1.0

## [Unreleased]
（なし）

## [0.1.0] - 2026-04-19
初回公開リリース

### Added
- 基本パッケージ情報
  - パッケージバージョンを `__version__ = "0.1.0"` として追加（src/kabusys/__init__.py）。

- 実行スクリプト
  - 実行エンジン起動スクリプトを追加（src/kabusys/run_execution.py）。
    - KABUSYS_ENV が `paper_trading` の場合は MockBrokerClient を使用し、paper_trading 用の SQLite（data/paper_trading.db をデフォルト）に記録して本番 DB と分離。
    - エンジンはスレッドで起動し、data/stop_requested.flag により停止可能。実行時に実行 PID を data/execution.pid に記録。
  - 監視ループ起動スクリプトを追加（src/kabusys/run_monitoring.py）。
    - デフォルトポーリング間隔は 60 秒。環境変数 `MONITOR_POLL_INTERVAL` で上書き可能（不正値はデフォルトにフォールバックして警告出力）。
    - Monitoring は環境にかかわらず本番用の sqlite_path を使用する（監視専用 DB へ接続）。
    - 停止フラグ（data/stop_requested.flag）検知でループを終了。

- 設定管理
  - 環境変数 / .env 読み込み・管理モジュールを追加（src/kabusys/config.py）。
    - プロジェクトルートの自動検出（.git または pyproject.toml を探索）に基づく .env 自動読み込み機能。
    - .env 自動ロードは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD`=1 で無効化可能。
    - 必須/任意の設定取得用プロパティとバリデーション（J-Quants, kabuAPI, DB パス, PAPER_FILL_MODE の有効値チェック等）。
    - 環境判別プロパティ（is_live / is_paper / is_dev）。
  - 対話式環境設定ウィザードを追加（src/kabusys/config_setup.py）。
    - .env の初期作成・更新を対話式に行う。秘密値のマスク表示、デフォルト値、説明文付き。
    - 書き込み時のテンプレート（.env ヘッダ）を含む。

- 設定検証 CLI
  - 起動前検証ツールを追加（src/kabusys/validate_config.py）。
    - 必須環境変数のチェック、KABUSYS_ENV / LOG_LEVEL の妥当性、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在と（PyYAML があれば）パース検証、live 環境向け追加警告など。
    - `--strict` オプションで警告を失敗扱い（exit 1）にできる。
    - CLI から実行可能（python -m kabusys.validate_config）。

- 監視・検証ツール
  - Paper Trading 検証レポート生成スクリプトを追加（src/kabusys/tools/paper_verification_report.py）。
    - Paper Trading 用 SQLite（環境変数 `PAPER_TRADING_SQLITE_PATH` または --db で指定）から各種指標を集計してレポート出力。
    - 指標: 稼働率（uptime）、注文成功率（fill_rate）、送信率（send_rate）、レイテンシ（平均/最大/P95）等。
    - デフォルトの判定閾値を定義（稼働率 99%、注文成功率 90%、送信率 95%、P95 レイテンシ 200ms）。
    - 日付フィルタ（--from / --to）に対応。

- ポートフォリオ構築（純粋関数群）
  - 銘柄選定・重み計算（src/kabusys/portfolio/portfolio_builder.py）
    - select_candidates: スコア降順かつ signal_rank でタイブレークし上位 N を選択。
    - calc_equal_weights / calc_score_weights: 等配分・スコア加重（全スコアが 0 の場合は等配分にフォールバックして警告）。
  - セクター集中制限・レジーム乗数（src/kabusys/portfolio/risk_adjustment.py）
    - apply_sector_cap: 既存保有のセクター別エクスポージャーを計算し、上限超過セクターの新規候補を除外。`unknown` セクターは上限適用対象外。
    - calc_regime_multiplier: market regime に応じた投下資金乗数（bull=1.0, neutral=0.7, bear=0.3）。未知レジームは 1.0 にフォールバックして警告。
  - 株数決定・リスク制限・単元丸め（src/kabusys/portfolio/position_sizing.py）
    - calc_position_sizes: allocation_method (`risk_based`, `equal`, `score`) に対応。
    - risk_based: risk_pct・stop_loss_pct を用いたポジションサイズ計算。
    - equal/score: 各銘柄の重みに基づく配分。lot_size（デフォルト 100）で丸め、単銘柄上限および aggregate cap（利用可能現金）を考慮してスケーリング。cost_buffer（手数料/スリッページ見積り）により保守的に試算。
    - aggregate cap 超過時はスケールダウンし、残余資金で小数点端数を lot 単位で順次配分するアルゴリズムを実装。

- ユーティリティ
  - ロギング設定ユーティリティを追加（src/kabusys/utils/logging_setup.py）。
    - StreamHandler（stdout） + TimedRotatingFileHandler（日次ローテーション、30日保持）をルートロガーに設定。
    - ログレベル・ログディレクトリは引数 / 環境変数で解決。ディレクトリ作成に失敗した場合はファイル出力をスキップしてコンソール出力のみで継続。
  - プロセス優先度 / CPU affinity 設定ユーティリティを追加（src/kabusys/utils/process_priority.py）。
    - Windows / POSIX の差分を吸収して引数により優先度（high/normal/low）を設定。CPU affinity を N コアに固定する機能も提供。
    - 権限不足や未対応 OS の場合は警告を出して安全にスキップ。

- 研究用ファクター計算（初期実装）
  - DuckDB を用いたファクター計算モジュールを追加（src/kabusys/research/factor_research.py）。
    - Momentum / MA200 / ATR / Volume 系の計算方針と関数インターフェースを定義。DuckDB 接続を受け取って prices_daily / raw_financials を参照する設計。
    - （ソース末尾で関数実装が途中の箇所あり — 今後拡張予定）

- パッケージエクスポート
  - portfolio パッケージの __all__ を整備して関連関数を公開（src/kabusys/portfolio/__init__.py）。
  - tools パッケージを作成（src/kabusys/tools/__init__.py）。

### Changed
- （初版のため該当なし）

### Fixed
- （初版のため該当なし）

### Deprecated
- （初版のため該当なし）

### Removed
- （初版のため該当なし）

### Security
- （初版のため該当なし）

---

補足 / 注意事項
- 環境変数とデフォルトパス
  - DuckDB: デフォルト data/kabusys.duckdb（Settings.duckdb_path）
  - 監視 SQLite: data/monitoring.db（Settings.sqlite_path）
  - Paper Trading SQLite: data/paper_trading.db（Settings.paper_sqlite_path または PAPER_TRADING_SQLITE_PATH）
- モード依存の振る舞い
  - run_execution は KABUSYS_ENV=paper_trading のとき DB を分離し（paper_trading DB を使用）、MockBroker を使用する設計。
  - run_monitoring は環境にかかわらず本番の sqlite_path を使用して監視データの一貫性を保つ。
- CLI 例
  - 設定ウィザード: python -m kabusys.config_setup
  - 設定検証: python -m kabusys.validate_config [--strict]
  - Paper 検証レポート: python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
- ロギング
  - stdout を StreamHandler に使用（cron 等で stdout/stderr を一本化する運用を考慮）。
  - ログファイルはデフォルト logs/<app_name>.log に日次ローテーションで出力。
- 未実装 / 既知の改善点
  - factor_research の一部実装が未完（ソース末尾の calc_momentum 等の続き）。将来的に完全実装予定。
  - position_sizing の price 欠損時のフォールバックに関する TODO（前日終値や取得原価でのフォールバック検討）。
  - .env 読み込みロジックは複雑なクォート・エスケープやインラインコメントを考慮しているが、稀なケースで挙動が異なる可能性あり。

もし特定機能について CHANGELOG 上の表現や詳細を修正したい場合は、その機能名を指定して指示してください。