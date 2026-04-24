# CHANGELOG

すべての重要な変更点を記録します。フォーマットは Keep a Changelog に準拠します。

最新の変更は常に最上部に記載します。

## [Unreleased]

（なし）

## [0.1.0] - 2026-04-24

初回リリース。KabuSys のコア機能（設定管理、起動スクリプト、監視、実行エンジン起動補助、ポートフォリオ構築ロジック、ユーティリティ、Paper Trading 向け検証ツール等）を実装・公開しました。

### Added
- 起動スクリプト
  - run_monitoring.py
    - SystemMonitor を初期化してポーリングループを実行する起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL によるポーリング間隔上書き対応（デフォルト 60 秒）。
    - 停止フラグファイル（data/stop_requested.flag）検知により安全にループ終了。
    - 監視 DB は実行環境に依らず本番 sqlite_path を使用する設計。
  - run_execution.py
    - ExecutionEngine を組み立ててセッションを別スレッドで実行する起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用 SQLite（data/paper_trading.db 等）を使用して本番 DB と完全分離。
    - 起動前に停止フラグ検知があれば起動せず終了。実行中に停止フラグ検知で Engine.stop() を呼び停止。
    - 実行用 PID ファイルを書き込む仕組み（data/execution.pid）に対応。
- 設定管理
  - config.py
    - .env 自動読み込み機能を追加（プロジェクトルート検出: .git または pyproject.toml）。
    - .env / .env.local の読み込み順序と上書きルールを実装（OS 環境変数保護対応）。
    - .env パーサは `export KEY=value`、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント（クォート無しのとき）などを適切に扱う。
    - Settings クラスを導入し、J-Quants / kabuステーション / DB パス / 監視閾値 / 環境種別 等のプロパティを提供。入力値のバリデーションを行う。
    - PAPER_FILL_MODE（paper_trading の MockBroker fill モード）の検証（instant/partial/never/reject）を追加。
- 設定ユーティリティ CLI
  - config_setup.py
    - 対話式ウィザードで .env を初期作成・更新する機能を追加（各設定項目の説明、既存値のマスク表示、保存確認など）。
  - validate_config.py
    - .env および config/*.yaml の起動前検証ツールを追加。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性、DB パスの親ディレクトリ確認、YAML のパース検証（PyYAML が存在する場合）、本番向けガード（LINE 通知設定や KILL_FLAG_CLEAR_ON_START の警告）などを実装。
    - --strict オプションで警告も失敗扱いにできる。
- Paper Trading 検証ツール
  - tools/paper_verification_report.py
    - Paper Trading 用 SQLite（PAPER_TRADING_SQLITE_PATH）から稼働率、注文成功率、送信率、API レイテンシ（P95 等）を集計してレポート出力する CLI を追加。
    - デフォルト基準値（稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200ms）を使用して PASS/FAIL を判定。
- ポートフォリオ構築ロジック（純粋関数群）
  - portfolio/portfolio_builder.py
    - シグナル選定（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）を実装。
    - スコアが全て 0 の場合は等金額配分にフォールバックして警告を出す。
  - portfolio/risk_adjustment.py
    - セクター集中制限を適用する apply_sector_cap を実装（既存保有のセクター暴露を計算して新規候補を除外）。
    - レジームに応じた投下資金乗数 calc_regime_multiplier を実装（bull=1.0 / neutral=0.7 / bear=0.3、未知レジームは 1.0 でフォールバック）。
  - portfolio/position_sizing.py
    - 発注株数算出ロジック calc_position_sizes を実装（allocation_method: "risk_based" / "equal" / "score"）。
    - 単元株（lot_size）丸め、per-stock 上限、aggregate cap（available_cash 超過時のスケーリング）、cost_buffer（手数料・スリッページ想定）対応。
    - risk_based モードで stop_loss_pct / risk_pct を用いたポジション算出を実装。
- ユーティリティ
  - utils/logging_setup.py
    - 統一的なロギング設定ユーティリティを実装（コンソール stdout と TimedRotatingFileHandler（日次・30世代）を設定）。
    - LOG_DIR / LOG_LEVEL の解決、ログディレクトリ作成失敗時のフォールバック動作を実装。
  - utils/process_priority.py
    - psutil を利用したプロセス優先度設定（Windows と POSIX の差分吸収）と CPU affinity 設定用ユーティリティを追加。権限不足などは警告を出してスキップ。
- パッケージ情報
  - __init__.py にてパッケージバージョンを 0.1.0 として追加。

### Changed
- ログ出力の統一
  - 全起動スクリプト・CLI から setup_logging() を呼び、ログ設定を統一するように設計変更。
- DB 初期化
  - 監視用テーブルの初期化関数 init_monitoring_db() を run_monitoring/run_execution 起動時に呼び出して存在を保証（冪等）。

### Fixed
- .env 読み込み/書き出しの細かい取り扱いを改善
  - export プレフィックス、クォートのエスケープ、行末コメントの扱いをサポートし、より実用的な .env パーサに改善。
- run_execution の paper_trading 分離
  - paper_trading 環境時には paper_sqlite_path を使用するようにして本番 DB からのデータ汚染を防止。

### Removed
- （なし）

### Deprecated
- （なし）

### Security
- 環境変数記載ファイル（.env）に関して
  - config_setup が .env を生成する際に「.env を Git にコミットしない」旨の注記を明記。

### Notes / Known issues / TODO
- position_sizing.calc_position_sizes:
  - 銘柄別の単元（lot_size）を将来的に stocks マスタなどで管理する案を TODO コメントとして残しています。
- risk_adjustment.apply_sector_cap:
  - price_map に価格が欠損（0.0）だった場合のエクスポージャー過少見積りについて FIXME コメントあり。前日終値等でのフォールバックを将来検討予定。
- research/factor_research.py はモメンタム等のファクター計算を実装中（ファイル末尾が途中で切れている状態）。今後のリリースで完全実装予定。
- run_monitoring は monitoring 用 DB に常に本番 sqlite_path を使用する仕様のため、意図しないデータ書き込みを避けるため環境変数設定には注意してください。
- Settings のプロパティは不正な値（例: KABUSYS_ENV、PAPER_FILL_MODE、LOG_LEVEL）で ValueError を送出します。起動前に validate_config で検証することを推奨します。

---

以上がリリース 0.1.0 の主な変更点です。将来的なリリースでは research モジュールの完成、より詳細なテストカバレッジ、個別銘柄単元管理や価格フォールバックの改善などを予定しています。