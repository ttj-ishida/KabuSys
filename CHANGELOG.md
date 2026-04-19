# Changelog

すべての非互換な変更はメジャーバージョンを上げ、後方互換のない変更は明示します。  
フォーマットは「Keep a Changelog」に準拠します。

- 発行日の日付はコードから推測したスナップショット日（この CHANGELOG 作成日）を使用しています。

## [Unreleased]
- （現時点で未リリースの差分はありません）

## [0.1.0] - 2026-04-19
初回公開リリース。本リポジトリは日本株自動売買システム「KabuSys」のコアユーティリティ群と起動スクリプト、ポートフォリオ構築ロジック、検証ツール等を含みます。

### Added
- 起動スクリプト
  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV が `paper_trading` の場合は paper 用 SQLite（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）を使用し、本番 DB と完全分離する設計。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て。
    - 実行用 PID ファイル（data/execution.pid）管理、停止フラグ（data/stop_requested.flag）対応。
    - プロセス優先度を High に設定して起動。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング周期を上書き可能（デフォルト 60 秒）。不正値（0 以下や非整数）はデフォルトにフォールバックして警告を出力。
    - Monitoring は環境に関係なく本番用 sqlite_path を使用（監視データの一元化）。
    - stop flag 検知によるループ終了、KeyboardInterrupt ハンドリング、例外発生時のロギング継続。

- 設定 / 環境管理
  - config.py
    - Settings クラスで環境変数アクセスをラップ（各種必須値や検証付き）。
    - .env 自動ロード機能を実装（プロジェクトルート自動検出: .git または pyproject.toml を起点）。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - .env のパースを堅牢化（export プレフィックス対応、クォート内のエスケープ処理、インラインコメント処理ルール）。
    - 各種設定プロパティ（DUCKDB_PATH / SQLITE_PATH / PAPER_FILL_MODE / PAPER_TRADING_SQLITE_PATH / PID_FILE_PATH / 各種閾値など）を追加。
    - KABUSYS_ENV / LOG_LEVEL の値検証を実装。

  - validate_config.py
    - 起動前に .env と config/*.yaml の検証を行う CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV の妥当性チェック、ログレベルチェック、DB パスの親ディレクトリ存在確認、YAML パース（PyYAML がない場合はスキップして警告）、本番（live）向け追加ガードなど。
    - --strict オプションで警告を Fail 扱いにできる。

  - config_setup.py
    - 対話式ウィザードで .env を初期作成 / 更新する CLI を追加。
    - シークレット入力のマスク表示、デフォルト値・選択肢の提示、入力キャンセル・確認処理、ファイル書き込みフォーマットを提供。

- ロギング / 実行環境ユーティリティ
  - utils/logging_setup.py
    - ルートロガーの統一設定ユーティリティを追加。
    - stdout への StreamHandler（stdout を利用）と日次ローテーション（TimedRotatingFileHandler）を組み合わせて設定。
    - LOG_LEVEL / LOG_DIR / 引数での上書き対応。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
  - utils/process_priority.py
    - クロスプラットフォームでプロセス優先度（および CPU affinity）を設定するユーティリティを追加。
    - Windows（psutil の PRIORITY_CLASS）と POSIX（nice 値）を吸収。権限不足や未対応 OS は警告でスキップ。
    - set_cpu_affinity によるコアピンニング機能を提供。

- ポートフォリオ構築ロジック（純関数群、DB 非依存）
  - portfolio/portfolio_builder.py
    - select_candidates: BUY シグナルのスコア降順選定（タイブレークは signal_rank）。
    - calc_equal_weights, calc_score_weights: 等金額配分、スコア加重配分（全スコア 0 の場合は等分へフォールバック）。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中上限チェック（max_sector_pct）および候補除外のロジック。売却予定銘柄をエクスポージャーから除外可能。
    - calc_regime_multiplier: market レジームに応じた投下資金乗数（bull/neutral/bear）と未知レジームのフォールバック。
  - portfolio/position_sizing.py
    - calc_position_sizes: allocation_method（"risk_based" / "equal" / "score"）に基づく発注株数決定。
    - 単元株（lot_size）丸め、1 銘柄上限・aggregate 上限の適用、cost_buffer（スリッページ・手数料考慮）、可用現金を超える場合のスケールダウンと残差配分ロジックを実装。

- データベース / 分析連携
  - DuckDB と SQLite を併用する設計（duckdb_path / sqlite_path の設定）。
  - monitoring_db.init_monitoring_db 呼び出しにより監視用テーブルの冪等初期化を保障（monitoring モジュール側の初期化関数を利用）。

- ツール
  - tools/paper_verification_report.py
    - Paper Trading 用の検証レポート生成ツールを追加。
    - システム稼働率、注文成功率（fill_rate）、送信率（send_rate）、リスク却下数、API レイテンシ（avg/max/P95）を集計し、閾値（稼働率 99% 等）に基づく PASS/FAIL 判定を行う。
    - --from / --to / --db オプションで期間・DB を指定可能。PAPER_TRADING_SQLITE_PATH 環境変数に対応。

- リサーチ（ファクター計算）
  - research/factor_research.py
    - Momentum 等のファクター計算モジュール（DuckDB 経由で prices_daily / raw_financials を参照）。設計方針と定数を導入。
    - calc_momentum 関数の実装開始（ファイル末尾で実装途中の痕跡あり）。（注意: 断片的実装のため将来的な完成が必要）

### Changed
- パッケージ初期化
  - __init__.py に初期バージョン文字列 __version__ = "0.1.0" を設定し、主要サブパッケージを __all__ で公開。

### Fixed
- （初回リリースのため特定のバグ修正エントリはなし。実装上の注意点は下記を参照）

### Security
- 機密情報（J-Quants トークン、kabu API パスワード、LINE トークン等）は .env に保存する設計。config_setup の README 注記で .env をリポジトリにコミットしないよう明示。

### Notes / Known issues / TODO
- research/factor_research.calc_momentum の実装がファイル末尾で途中のように見えるため、完全実装が必要。
- position_sizing の price 欠損（価格 0.0）時は現状スキップする実装になっており、将来的に前日終値や取得原価でのフォールバックが必要（TODO コメントあり）。
- apply_sector_cap では sector_map にないコードを "unknown" 扱いしているが、"unknown" セクターは上限適用外になる点に注意（設計仕様）。
- ログディレクトリ作成やプロセス優先度設定は権限や環境依存で失敗する可能性があるため、呼び出し側での運用監視を推奨。

---

参考:
- 環境変数や設定ファイル (.env / config/*.yaml) の検証には validate_config.py を使用してください。
- .env の対話的作成・更新は python -m kabusys.config_setup を参照してください。
- Paper Trading レポートは python -m kabusys.tools.paper_verification_report で生成できます。