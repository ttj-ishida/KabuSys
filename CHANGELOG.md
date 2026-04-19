# Changelog

すべての変更は Keep a Changelog のフォーマットに準拠し、セマンティック バージョニングを使用します。  
日付はリリース日（YYYY-MM-DD）です。

## [Unreleased]

## [0.1.0] - 2026-04-19
初回公開リリース。

### Added
- 起動スクリプト
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止フラグファイル (data/stop_requested.flag) による安全停止対応。
    - 監視は環境にかかわらず本番用の sqlite_path を使用して DB に接続。
  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合はペーパートレード専用 DB（data/paper_trading.db）を使用し、MockBrokerClient を利用して本番 DB と完全分離。
    - 実行中の PID ファイル管理（data/execution.pid）と停止フラグによる安全停止対応。
    - ExecutionEngine をスレッドで実行し、停止フラグで安全に停止可能。

- 設定関連
  - config.py
    - 環境変数読み込みと Settings クラスを実装。
    - .env 自動ロード（プロジェクトルート検出：.git または pyproject.toml）。
    - .env のパースは export 形式・引用符・インラインコメント等に対応。
    - 必須環境変数取得ヘルパー、自動フォールバック値、環境種別チェック（development / paper_trading / live）を提供。
    - 各種パス（DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH 等）、Paper Trading の fill モード、閾値などをプロパティで提供。
  - config_setup.py
    - 対話式の .env 作成/更新ウィザードを追加。
    - 初期テンプレート、既存 .env 読み込み、秘密値のマスク表示、保存確認、.env 書き出し機能を提供。
    - .env を絶対に Git にコミットしない旨のヘッダを出力。
  - validate_config.py
    - .env および config/*.yaml の起動前検証 CLI を追加。
    - 必須環境変数の未設定チェック、KABUSYS_ENV / LOG_LEVEL の妥当性、DB パスの親ディレクトリチェックを実装。
    - PyYAML がインストールされていれば config/*.yaml のパース検証を実行（未インストール時は警告）。
    - --strict オプションで警告をエラー扱いにできる。

- ポートフォリオ構築ライブラリ（純粋関数群）
  - portfolio.portfolio_builder
    - 候補選定（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）を実装。
  - portfolio.risk_adjustment
    - セクター集中の上限適用（apply_sector_cap）、市場レジームに応じた投下資金乗数（calc_regime_multiplier）を実装。
    - 未知レジームでのフォールバックとログ警告を実装。
  - portfolio.position_sizing
    - 各銘柄の発注株数決定ロジック（risk_based / equal / score）を実装。
    - 単元株（lot_size）丸め、per-position と aggregate の上限、コストバッファを考慮したスケールダウンと端数分配を実装。
  - portfolio パッケージのエクスポート（select_candidates 等の公開 API を提供）。

- ユーティリティ
  - utils.logging_setup
    - ルートロガー設定ユーティリティを追加（StreamHandler: stdout、TimedRotatingFileHandler: 日次ローテーション）。
    - ログレベル解決（引数 > 環境変数 > デフォルト）、ログディレクトリ解決、既存ハンドラのクリア、ファイルハンドラの作成失敗時のフォールバックを実装。
    - 日次ローテーション、30 日分保持。
  - utils.process_priority
    - プロセス優先度（high/normal/low）および CPU affinity 設定ユーティリティを追加。
    - Windows/Linux/その他の差分を吸収（psutil を利用）。権限不足や未対応 OS の場合は警告を出してスキップ。

- ツール
  - tools.paper_verification_report
    - ペーパートレード用 SQLite DB から検証レポートを生成する CLI を追加。
    - システム稼働率（uptime）、注文成功率（fill rate）、送信率（send rate）、P95 レイテンシなどを集計し PASS/FAIL を判定。
    - 日付レンジ指定オプション --from / --to、DB パス指定 --db、環境変数 PAPER_TRADING_SQLITE_PATH に対応。
    - P95 計算、欠損データの扱い、しきい値は定数化（README 風の説明あり）。

- リサーチ（作業中）
  - research.factor_research
    - ファクター計算の基盤（モメンタム、MA200、ATR、出来高系など）を開始。DuckDB を用いた prices_daily / raw_financials 参照を想定。
    - 設計ドキュメント参照の上で関数群を実装中（未完の箇所あり）。

- パッケージ初期化
  - __init__.py にバージョン情報 (__version__ = "0.1.0") を追加。

### Changed
- （新規リリースのため該当なし）

### Fixed
- （新規リリースのため該当なし）

### Removed
- （新規リリースのため該当なし）

### Security
- .env に API トークン等の秘密情報を保存しないよう注意喚起を追加（config_setup のヘッダ）。
- config_setup / logging_setup 等にてシークレット値は表示時にマスクする実装を導入。

### Notes / Implementation details / Known issues
- .env 自動読み込みはプロジェクトルートを .git または pyproject.toml で検出するため、配布後も CWD に依存せず動作することを意図している。ただしルートが見つからない場合は自動ロードをスキップする。
- .env パーサは export 形式や引用符、エスケープ、インラインコメント等に対応しているが、特殊ケースですべての .env 文法をカバーするわけではない。
- Paper Trading は本番 DB から完全分離されるように paper_sqlite_path を導入。PAPER_FILL_MODE の有効値は instant / partial / never / reject で、不正な値の場合は起動時に例外を出す。
- process_priority と set_cpu_affinity は psutil に依存する。権限不足や未対応 OS の場合は警告を出し、処理をスキップする。
- logging_setup はログディレクトリ作成に失敗した場合、ファイルハンドラを作成せずコンソール出力のみで継続する。
- portfolio.position_sizing 内に将来の拡張（銘柄別 lot_size サポートなど）に関する TODO コメントあり。
- risk_adjustment.apply_sector_cap は price_map に欠損（0.0 等）があるとエクスポージャーを過少評価する可能性があり、将来的にフォールバック価格導入を検討する TODO が残っている。
- validate_config は PyYAML が無い環境でも動作するが、YAML 検証はスキップされるため config ファイルのミスを見逃す可能性がある。
- research.factor_research は一部実装が未完（ファイル末尾で途切れている部分あり）。今後のリリースで完成予定。

---

将来的なリリースでは、以下を予定しています:
- research.factor_research の完成とユニットテスト追加
- ExecutionEngine / SystemMonitor 周りの E2E テストとドキュメント強化
- 銘柄別単元株（lot_size）や価格フォールバックのサポート
- 監視 / アラート機能（LINE 通知等）の拡張

Contributing, バグ報告、改善提案はプルリクエストまたは Issue を通じてお願いします。