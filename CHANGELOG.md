# CHANGELOG

すべての notable な変更点はこのファイルに記載します。フォーマットは「Keep a Changelog」に準拠しています。

全般方針: バージョンはパッケージ内の __version__ に合わせています。

## [0.1.0] - 2026-04-21

### Added
- 初回公開リリース。
- 起動/運用用スクリプトを追加:
  - run_execution.py: ExecutionEngine の起動スクリプト（スレッド実行、停止フラグ検知、PID ファイル管理）。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプト（監視用 stop フラグ、MONITOR_POLL_INTERVAL によるポーリング間隔上書き対応）。
- 設定関連 CLI を追加:
  - config_setup.py: 対話式 .env 作成/更新ウィザード（シークレット入力のマスク表示、選択肢・デフォルト対応、.env 出力）。
  - validate_config.py: 起動前チェック CLI（必須環境変数、KABUSYS_ENV 検証、ログレベル、DB パス、config/*.yaml の存在とパース確認、--strict モード追加）。
- Paper Trading 用解析ツール:
  - tools/paper_verification_report.py: ペーパートレード DB から稼働率・注文成功率・レイテンシ等を集計してレポート出力（P95 計算、閾値による PASS/FAIL 判定、--from/--to/--db オプション）。
- ポートフォリオ構築モジュール（純関数群）を追加:
  - portfolio/portfolio_builder.py: シグナル選定 (select_candidates)、等分配・スコア加重 (calc_equal_weights / calc_score_weights)。
  - portfolio/position_sizing.py: 発注株数計算（risk_based / equal / score）、単元株（lot_size）丸め、aggregate cap によるスケーリングと残余配分ロジック、コストバッファ考慮。
  - portfolio/risk_adjustment.py: セクター集中制限の適用 (apply_sector_cap)、市場レジームによる投下資金乗数 (calc_regime_multiplier)。
  - portfolio/__init__.py: 上記 API のエクスポート。
- 共通ユーティリティを追加/改善:
  - utils/logging_setup.py: 全スクリプト共通のロギング初期化（stdout を用いる StreamHandler、日次ローテーションの TimedRotatingFileHandler、ログディレクトリ自動作成、LOG_LEVEL/LOG_DIR の解決順）。
  - utils/process_priority.py: Windows/Linux/Mac の差分を吸収するプロセス優先度設定（`set_process_priority`）と CPU affinity 設定（`set_cpu_affinity`）。psutil の制約に応じたフォールバックと警告出力。
- 設定読み込み/管理:
  - config.py:
    - .env 自動ロード機能（プロジェクトルート検出: .git または pyproject.toml を基準）。
    - .env / .env.local の読み込み順序（OS 環境変数は保護される）。KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化対応。
    - 洗練された .env パーサ（export プレフィックス対応、シングル/ダブルクォートのエスケープ処理、インラインコメントの取り扱い）。
    - 各種設定プロパティ（DB パス、paper_trading 用 DB パス、pid/kill flag パス、閾値設定、PAPER_FILL_MODE 検証など）を getter にて提供。
    - settings = Settings() による単一インスタンス提供。
- データリサーチ基盤:
  - research/factor_research.py: DuckDB 接続を受け取る形でモメンタム等のファクター計算枠組み（モジュール設計と定数、calc_momentum の実装方針と一部実装）。Pandas ではなく DuckDB/SQL と Python の混合で計算する方針。

### Changed
- Database / 環境分離:
  - run_execution.py: KABUSYS_ENV=paper_trading の場合、paper_sqlite_path（デフォルト data/paper_trading.db）を使用して本番 DB と分離。monitoring テーブルの初期化 (init_monitoring_db) を冪等に実行。
  - run_monitoring.py: Monitoring は環境にかかわらず本番 sqlite_path を使用する旨を明確化（監視は production DB を参照する設計判断）。
- ログ出力の統一:
  - logging_setup で stdout を StreamHandler に使用（stderr ではなく stdout）。ログディレクトリ作成に失敗した場合はファイルハンドラをスキップしてコンソールのみで継続。
- プロセス管理:
  - 起動直後に set_process_priority("high") を呼び出す運用に変更（run_execution/run_monitoring 共通）。
- run_execution のエンジン実行モデル:
  - ExecutionEngine を別スレッドで実行し、メインループで停止フラグ検知→ engine.stop() を呼ぶ（安全に中止できるように設計）。
- 設定検証:
  - validate_config.py にて PyYAML 未インストール時に YAML 検証をスキップする旨を WARN として通知。config/*.yaml に対する存在チェックと YAML パースの試行を実装。
- Paper 検証レポート:
  - レポートの閾値や出力フォーマットを明文化（稼働率、注文成功率、送信率、P95 レイテンシ等）。DB パス解決順を明確化（--db > 環境変数 > デフォルト）。

### Fixed
- 環境変数パーサの堅牢性向上:
  - クォート内のバックスラッシュエスケープ処理、export プレフィックス対応、インラインコメントの扱いを改善し、.env の多様な記法に対応。
- ポジションサイズ計算の合計キャッシュ超過時のスケーリングロジックを実装（小数点から lot_size 単位への再配分を行い、残余キャッシュで端数調整）。
- calc_score_weights: 全スコアが 0 の場合に等金額配分へフォールバックしログ WARNING を出力するよう修正。
- process_priority / set_cpu_affinity: psutil に依存する箇所で AccessDenied などの例外を捕捉し、失敗時は警告を出してスキップするように改善。

### Security
- .env を生成する config_setup.py において「.env は絶対に Git にコミットしないこと」を明示するヘッダを出力（ユーザー通知）。

### Known issues / Notes
- research/factor_research.py の一部（calc_momentum の実装の続き）が未完（ファイル末尾が途中で切れている様子）。今後のリリースで続きを実装予定。
- 一部 TODO コメントあり（例: position_sizing で銘柄別 lot_size を将来的に拡張する旨、risk_adjustment の price 欠損時のフォールバック戦略など）。
- run_monitoring の MONITOR_POLL_INTERVAL は環境変数で上書き可能だが、不正値（0 / 負数 / 非整数）はデフォルト（60秒）へフォールバックし警告を出力する。

---

今後の予定（概略）
- factor_research の完成（ファクター計算の SQL 実装完了）。
- テストカバレッジの追加（特に position sizing と sector cap の境界ケース）。
- ExecutionEngine / BrokerClient 周りの統合テストおよび paper_trading の検証強化。