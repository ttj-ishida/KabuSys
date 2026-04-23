# Changelog

すべての重要な変更点を記録します。本ファイルは Keep a Changelog の形式に従います。

全般的な注意
- 本リリースはパッケージの初期公開（バージョン 0.1.0）に相当すると想定して作成しています（src/kabusys/__init__.py の __version__ に基づく）。
- 記載はコードベースから推測した機能・動作を元にしています。

## [Unreleased]
（今後の変更をここに記載）

---

## [0.1.0] - 2026-04-23

### Added
- コア機能・モジュール
  - portfolio: 銘柄選定・配分・サイズ算出・リスク調整用の純粋関数群を追加。
    - portfolio_builder.select_candidates: スコア降順、同点は signal_rank でタイブレークして上位 N を選定。
    - portfolio_builder.calc_equal_weights / calc_score_weights: 等金額配分・スコア加重配分（スコア全て0なら等金額配分にフォールバックし警告）。
    - risk_adjustment.apply_sector_cap: セクター集中上限（max_sector_pct）を超える場合に新規候補を除外。売却予定銘柄を除外可能。unknown セクターは上限適用除外。
    - risk_adjustment.calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull/neutral/bear をマッピング、未知レジームは警告して 1.0 でフォールバック）。
    - position_sizing.calc_position_sizes: allocation 方法（"risk_based","equal","score"）に対応した株数計算。単元株（lot_size）丸め、1銘柄上限・aggregate cap、cost_buffer を考慮したスケーリングと残差処理を実装。
  - research: factor_research モジュール（DuckDB でのファクター計算設計・一部実装）。モメンタム・ボラティリティ等の計算方針と定数を定義。
  - execution: ExecutionEngine 起動スクリプト（run_execution.py）を追加。
    - KABUSYS_ENV=paper_trading 時は専用の Paper Trading SQLite を使用して本番 DB と完全分離（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）。
    - ブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て、スレッドで ExecutionEngine を実行、停止フラグ（data/stop_requested.flag）検知によるシャットダウンを実装。
    - 起動時にプロセス優先度を "high" に設定。
    - 実行中の PID を data/execution.pid に記録（設定に依存）。
  - monitoring: SystemMonitor 起動スクリプト（run_monitoring.py）を追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値や 0 以下はデフォルトにフォールバックして警告。
    - 監視は環境にかかわらず本番の sqlite_path を使用して監視データを保存。
    - 停止フラグ（data/stop_requested.flag）検知でループ終了。
  - tools:
    - paper_verification_report: ペーパートレード検証レポート生成スクリプトを追加。稼働率、注文成功率、送信率、P95 レイテンシなどを算出して PASS/FAIL 判定を行う。閾値はソース内で定義（例: 稼働率 >= 99%、注文成功率 >= 90% 等）。
  - config:
    - config_setup.py: .env 初期作成/対話式更新ウィザードを追加。各種環境変数の雛形と説明を提供し .env を生成。
    - validate_config.py: .env と config/*.yaml の設定の事前検証 CLI を追加。--strict で警告を FAIL 扱いにできる。PyYAML が利用可能な場合は YAML の構文検証も実施。
  - config.Settings: 環境変数ラッパークラスを追加。多くの設定（DB パス、ログレベル、KABUSYS_ENV 判定、paper_trading 判定、各種閾値、PAPER_FILL_MODE の妥当性チェック等）をプロパティで提供。settings オブジェクトをモジュールレベルでエクスポート。
  - utils:
    - logging_setup.setup_logging: ルートロガー設定ユーティリティを追加。stdout への StreamHandler と日次ローテーションのファイルハンドラ（TimedRotatingFileHandler、30日保持）を設定。ログディレクトリ作成に失敗した場合はファイル出力をスキップして stdout のみで継続。
    - process_priority.set_process_priority / set_cpu_affinity: Windows/Linux の差を吸収してプロセス優先度や CPU affinity を設定するユーティリティを追加。権限不足などで失敗した場合は警告して継続。
  - monitoring DB 初期化: init_monitoring_db を呼び出して監視テーブルが存在することを保証（冪等）。

### Changed / Design decisions
- .env 自動読み込み:
  - プロジェクトルート（.git または pyproject.toml）を基準に .env/.env.local を自動読み込みする実装を導入。OS 環境変数は保護され（上書き禁止）、.env.local は .env より優先して上書きできる。
  - 自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD を設定することで無効化可能（テスト等で利用）。
- .env パーサーの振る舞い:
  - export KEY=val 形式に対応。シングル/ダブルクォート内のバックスラッシュエスケープ処理や、クォートなし値内のコメント扱い（# の前にスペース/タブがある場合のみコメントとして扱う）など、実用的なパースを実装。
- ログ:
  - スクリプトからのログ設定は一元化（setup_logging）。コンソールは stdout を使用（cron 等で stdout/stderr を一本化しやすくするため）。
- DB の使い分け:
  - monitoring は環境にかかわらず監視用 sqlite_path（デフォルト data/monitoring.db）を使用。
  - execution は paper_trading 時に paper 用 SQLite を使用して本番 DB とデータを分離。
- Execution 起動フロー:
  - 起動時に優先度を上げる（set_process_priority("high")）。停止フラグがある場合は起動を行わず終了する。

### Fixed / Robustness
- 環境変数の検証やフォールバックの強化:
  - MONITOR_POLL_INTERVAL の不正値や 0 以下を検出してデフォルト値にフォールバックし警告するようにした。
  - PAPER_FILL_MODE の有効値を検証し、不正な値は ValueError を発生させる（事前検証の助けとなる）。
  - KABUSYS_ENV / LOG_LEVEL などの値検証を導入し、不正値はエラーを出すようにした。
- ログファイルディレクトリ作成失敗時のフォールバック:
  - logging_setup でログディレクトリ作成に失敗した場合、ファイルハンドラ作成をスキップしてコンソール出力のみで継続する（起動失敗を避ける）。
- process_priority / cpu_affinity:
  - 権限不足・未対応 OS などで例外が出てもワーニングにとどめ稼働を継続する（堅牢性向上）。
- DB クエリの例外耐性（tools.paper_verification_report）:
  - 該当テーブルが存在しない場合に備えて sqlite3.OperationalError を捕捉してデフォルト値を使用するようにした（レポート生成時のクラッシュ回避）。

### Documentation / CLI
- 実行可能スクリプトと CLI の説明コメントを各ファイルに追加（run_execution.py, run_monitoring.py, config_setup.py, validate_config.py, tools.paper_verification_report.py）。使い方・環境変数・例などをソース内ドキュメントとして明記。
- config_setup による .env 生成テンプレートを実装。生成される .env に対する注意書き（絶対に Git にコミットしない等）を出力。

---

開発者向けメモ（コードからの推測）
- 複数のモジュールは「純粋関数」として設計されており、ユニットテストが書きやすい（DB に依存しない）。position_sizing や risk_adjustment は将来的な拡張（銘柄別 lot_size、価格フォールバック等）を意識した TODO コメントがある。
- DuckDB を分析用に利用（duckdb_path 設定）し、研究処理（factor_research）での SQL/Python ハイブリッド実装が想定されている。
- 実運用向けの安全設計（kill/stop フラグ、PID ファイル、ログのローテーション、環境検証 CLI）が充実しているため、本番移行の土台が整っている。

（以上）