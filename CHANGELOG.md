# CHANGELOG

すべての変更は Keep a Changelog の形式に準拠します。セマンティックバージョニングを採用しています。

## [Unreleased]

## [0.1.0] - 2026-04-19
初回リリース。日本株自動売買システム KabuSys のコアユーティリティ、起動スクリプト、ポートフォリオ構築ロジック、設定管理・検証ツール、およびいくつかの運用ツールを収録。

### Added
- 起動スクリプト
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は KABUSYS_ENV にかかわらず本番用 sqlite_path を使用。停止フラグファイル検知で優雅に終了。
  - run_execution.py: ExecutionEngine の起動スクリプトを追加。KABUSYS_ENV=paper_trading 時は MockBrokerClient を使用し、paper_trading 用の SQLite（data/paper_trading.db）に完全分離して記録。起動時に stop flag を確認し、PID ファイルを利用してプロセス管理。
- 環境設定・検証ツール
  - config_setup.py: .env の初期作成・更新を対話式に支援するウィザードを追加。複数の設定項目をガイド付きで入力し .env を書き出し。
  - validate_config.py: .env および config/*.yaml の起動前検証 CLI を追加。必須環境変数のチェック、KABUSYS_ENV/LOG_LEVEL の妥当性確認、DB パスの親ディレクトリ存在チェック、YAML パース検証（PyYAML 利用可の場合）。--strict オプションで警告を失敗扱いにできる。
- 設定管理
  - config.py: Settings クラスを導入。環境変数の読み取り、デフォルト値、妥当性チェック（KABUSYS_ENV, LOG_LEVEL 等）、Paper Trading 用パスや各種閾値をプロパティで提供。プロジェクトルート検出により .env 自動ロードを実施（無効化可能）。
  - .env パーサの改善: export プレフィックス対応、引用符付き値のエスケープ処理、インラインコメントや空白周りの扱いを実装。
- ロギング / プロセス管理ユーティリティ
  - utils/logging_setup.py: 統一的なログ設定ユーティリティを追加。コンソール(stdout) と TimedRotatingFileHandler（日次・30日保持）をルートロガーへ設定。ログディレクトリ作成失敗時はファイルハンドラをスキップしてコンソールのみで継続。
  - utils/process_priority.py: Windows / POSIX の差分を吸収するプロセス優先度設定ユーティリティを追加。set_process_priority(level) と set_cpu_affinity(n) を提供し、権限不足や未対応プラットフォーム時は安全にフォールバック。
- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py: 候補選定（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）を実装。スコア全0時のフォールバック挙動を定義。
  - portfolio/risk_adjustment.py: セクター集中防止の apply_sector_cap、マーケットレジームに応じた投下資金乗数 calc_regime_multiplier を実装。未知レジームはフォールバック値を使用。
  - portfolio/position_sizing.py: 発注株数計算ロジック（risk_based / equal / score）を実装。単元株（lot_size）丸め、1銘柄上限・集計上限（aggregate cap）およびコストバッファを考慮したスケーリングを行う。価格欠損時の扱い、残余配分アルゴリズムを含む。
  - portfolio/__init__.py にて API をエクスポート。
- 研究用モジュール
  - research/factor_research.py: DuckDB を利用したファクター計算モジュール（モメンタム・移動平均乖離・ATR 等）の骨組みを追加。prices_daily / raw_financials テーブルのみ参照する設計思想を採用。
- 運用ツール
  - tools/paper_verification_report.py: Paper Trading 用 SQLite から検証レポートを生成する CLI を追加。稼働率、注文成功率、送信率、P95 レイテンシ等を集計して PASS/FAIL 判定を出力。--from/--to/--db オプションをサポート。

### Changed
- 起動時のプロセス優先度設定を標準化
  - run_monitoring と run_execution の両方で起動直後に set_process_priority("high") を呼び出すようにして、重要プロセスの優先度を高める動作を採用。
- DB 接続の扱い
  - 監視（monitoring）は KABUSYS_ENV にかかわらず production 用 sqlite_path を利用する設計（監視 DB と実行 DB の分離方針を明確化）。
  - run_execution は Paper Trading 時に paper_sqlite_path を使用して本番 DB と完全分離する挙動を採用。
- ログ出力
  - logging_setup により、全起動スクリプトで統一されたフォーマットとファイルローテーションを使用。ログディレクトリ作成失敗時に安全にフォールバックするため、運用時の堅牢性が向上。

### Fixed
- 環境変数パースの堅牢化
  - config._parse_env_line にて引用符付き値のバックスラッシュエスケープや export プレフィックス、インラインコメントの扱いを改善。不正な行を無視して自動ロード中のクラッシュを防止。
- 無効な MONITOR_POLL_INTERVAL の扱い
  - run_monitoring._get_poll_interval で不正な値（数字以外・0 以下）が与えられた場合に警告を出しデフォルトにフォールバックするように改良（time.sleep の ValueError 回避）。
- 権限不足や未対応環境での process priority / cpu affinity の失敗を安全にハンドル（警告出力でスキップ）。

### Security
- .env ファイル生成ウィザードで生成されるファイルに関する注意喚起を追加：.env を絶対に Git にコミットしない旨のヘッダを記載。

### Documentation
- 各モジュールに docstring と使用例を追加し、意図や設計方針、引数・戻り値の説明を明記。
- CLI スクリプトにヘルプ文や usage コメントを追加（python -m での実行例を明示）。

### Notes / Known limitations
- research/factor_research.py は一部実装が続き（ファイル末尾で未完の可能性）になっているため、用途に応じて追加実装が必要。
- position_sizing や apply_sector_cap は価格データ欠損時に conservative な挙動（スキップ又は 0 として扱う）をとるが、将来的にフォールバック価格や銘柄別単元情報の導入を検討する旨の TODO コメントあり。
- ログディレクトリ作成やファイルハンドラ作成で失敗した場合はコンソール出力のみとなるため、運用環境でファイル書き込み権限があることを確認すること。

---

以上。リリースにあたってさらに詳細な変更箇所や設計資料（PortfolioConstruction.md 等）を参照することで、各関数・CLI の利用方法やパラメータ調整のガイドが得られます。必要であれば各ファイルごとの変更要約や具体的な使用例を追加で作成します。