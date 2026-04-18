# Changelog

すべての重要な変更をここに記録します。フォーマットは「Keep a Changelog」に準拠しています。

現在のリリース: 0.1.0

## [Unreleased]

（なし）

## [0.1.0] - 2026-04-18

初回リリース。日本株自動売買フレームワーク「KabuSys」の基本機能を実装しました。以下は主な追加点・仕様です。

### Added（追加）

- パッケージ全体
  - パッケージバージョンを `__version__ = "0.1.0"` として公開。
  - コアモジュール群（execution / monitoring / portfolio / utils / research / tools 等）を追加。

- 起動スクリプト
  - run_execution.py
    - ExecutionEngine を起動するエントリポイントを追加。
    - KABUSYS_ENV が `paper_trading` の場合、専用の Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）を使用し、本番 DB と分離。
    - 実行中の停止制御: プロジェクトの data/stop_requested.flag の検出で安全に停止。PID ファイル管理（data/execution.pid）をサポート。
    - brokerFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler 組み立てを行う。
    - RiskConfig のデフォルトを設定（例: max_position_pct=0.20, max_utilization=0.80, rate_limit_per_sec=5 など）。
  - run_monitoring.py
    - SystemMonitor のポーリングループを起動するエントリポイントを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は常に（環境にかかわらず）本番 sqlite_path を使用して監視テーブルを初期化。
    - 停止制御: data/stop_requested.flag の検出でループ終了。

- 設定管理 / ユーティリティ
  - config.py
    - 環境変数と .env ファイルの読み込みを実装（自動ロード: .env → .env.local、OS 環境変数を保護）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能。
    - .env パース機能を強化（export 形式、シングル/ダブルクォート、エスケープシーケンス、インラインコメント対応）。
    - Settings クラスを実装し、J-Quants / kabuAPI / DB パス / 監視閾値 / 環境判定（is_live/is_paper/is_dev）等をプロパティで提供。
    - PAPER_FILL_MODE（`instant`|`partial`|`never`|`reject`）や PAPER_TRADING_SQLITE_PATH をサポート。
  - config_setup.py
    - 対話式ウィザードで .env を初期作成・更新する CLI を追加（各項目の説明・デフォルト値・秘密入力対応）。
  - validate_config.py
    - 起動前の設定検証 CLI を追加。必須環境変数チェック、KABUSYS_ENV 検証、DB パスの親ディレクトリチェック、config/*.yaml の存在/パース確認（PyYAML 未インストール時は警告）。
    - `--strict` モードで警告も失敗扱いにできる。
    - exit コードを用いた自動化に対応（エラー時は exit(1)）。
  - utils/logging_setup.py
    - 統一的なログ設定ユーティリティを追加。
    - stdout への StreamHandler（stderr ではなく stdout）と、日次ローテート（TimedRotatingFileHandler）でのファイル出力（デフォルト logs/<app_name>.log）を設定。ファイルは 30 日分保持。
    - ログディレクトリ作成に失敗した場合はファイル出力をスキップしてコンソールのみで継続。
    - ログレベル決定順: 引数 > 環境変数 LOG_LEVEL > デフォルト INFO。
  - utils/process_priority.py
    - クロスプラットフォームでプロセス優先度（high/normal/low）を設定するユーティリティを追加。
    - CPU affinity 設定関数も提供（最初の N コアへピンニング）。
    - 権限不足や未対応 OS の場合は警告を出してスキップする安全設計。
  - tools/paper_verification_report.py
    - Paper Trading 用検証レポート生成スクリプトを追加。
    - Paper Trading DB（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）から稼働率、注文成功率、送信率、レイテンシ（P95 等）を集計して標準出力にレポートを出力。
    - CLI 引数で期間指定（--from / --to）や DB パス指定（--db）に対応。
    - 合否判定の閾値（稼働率99%、注文成功率90%、送信率95%、P95レイテンシ200ms）を定義。

- ポートフォリオ構築（純関数群）
  - portfolio/portfolio_builder.py
    - 候補選定（select_candidates）: スコア降順、同点は signal_rank 昇順でタイブレーク。
    - 等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）。全スコアが 0 の場合は等金額にフォールバックして警告。
  - portfolio/risk_adjustment.py
    - セクター上限適用（apply_sector_cap）: 既存保有のセクターエクスポージャーが閾値を超える場合に同セクターの新規候補を除外（"unknown" セクターは除外対象外）。
    - レジーム乗数（calc_regime_multiplier）: "bull"/"neutral"/"bear" に応じた投下資金乗数を提供（未定義レジームは警告して 1.0 でフォールバック）。
  - portfolio/position_sizing.py
    - 銘柄ごとの発注株数計算（calc_position_sizes）を実装。
    - allocation_method に応じて risk_based / equal / score の各方式をサポート。
    - 単元（lot_size）丸め、1銘柄上限（max_position_pct）、aggregate cap（利用可能現金を超えた場合のスケーリング）、cost_buffer（手数料・スリッページ見積）を考慮。
    - スケーリング時は残差の大きい順に lot 単位で再配分するロジックを実装。

- 研究用モジュール（ドラフト）
  - research/factor_research.py
    - モメンタム等のファクター計算を行うための基盤を追加（DuckDB 接続を受け取り prices_daily / raw_financials を参照する設計）。
    - モメンタム期間等の定数を定義（1M/3M/6M、MA200、ATR20 等）。
    - （ファイル末尾で実装途中の箇所あり）

### Changed（変更）

- 監視 / 実行の挙動
  - 監視・実行プロセスは起動直後に process priority を "high" に設定するように変更（set_process_priority 呼び出しを追加）。
  - 実行時に監視テーブルの初期化（init_monitoring_db）を実行して冪等的にテーブルを用意するようにした。

- .env 読み込みロジック
  - OS 環境変数は保護され、.env.local の値は既存 OS 環境変数を上書きしない（protected 機構）。
  - パースの堅牢化（export プレフィックス、クォート・エスケープ、インラインコメントの扱いなど）。

- ロギング
  - StreamHandler は stdout を使用（cron 等で stdout/stderr を一元管理しやすくするため）。
  - 既存ハンドラがある場合は一旦 flush/close してから再設定し、二重登録を防止。

### Fixed（修正）

- process_priority と logging 設定において、権限不足やファイル作成失敗など環境依存の失敗を警告に留め安全にフォールバックするように調整（クラッシュさせない設計）。
- config.validator の検証出力を整理し、PyYAML 未インストール時は YAML の内容検証をスキップして警告を出すようにした。

### Notes（備考・使用上のポイント）

- 環境変数（代表）
  - KABUSYS_ENV: development | paper_trading | live（必須ではないが正しい値を推奨）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD: 1 を設定すると .env の自動読み込みを無効化。
  - JQUANTS_REFRESH_TOKEN / KABU_API_PASSWORD: 必須（validate_config でチェック）。
  - DUCKDB_PATH / SQLITE_PATH / PAPER_TRADING_SQLITE_PATH: データベースファイルのパス。デフォルトは data/ ディレクトリ下。
  - MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒）。正の整数で、デフォルト 60。
  - PAPER_FILL_MODE: paper_trading 時の約定モード（instant/partial/never/reject）。不正値は ValueError。
  - LOG_LEVEL / LOG_DIR: ログレベル・ログディレクトリ設定。
  - PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START: 実行制御用のパスやフラグ。

- Paper Trading と本番 DB の分離
  - paper_trading 環境では paper_trading 用 SQLite が使用され、本番監視 DB（monitoring.db）とは分離されています。

- 停止制御
  - 実行・監視ともに data/stop_requested.flag の有無で安全に停止できます（CI/運用上の Kill Switch）。

- レポートと閾値
  - Paper Trading レポートはデフォルト閾値により PASS/FAIL 判定を行います。閾値はツール内で定義されており、必要に応じて調整してください。

- 研究モジュールは DuckDB を前提に設計されています。prices_daily / raw_financials テーブルのスキーマに依存します。

### Deprecated / Removed / Security

- なし

---

今後の予定（例）
- factor_research の完全実装（Momentum / Value / Volatility / Liquidity 等の出力整形）。
- ExecutionEngine / Broker クライアントの詳細なテスト、PaperTrade のシミュレーション強化。
- 単体テスト・統合テストの追加と CI パイプライン整備。