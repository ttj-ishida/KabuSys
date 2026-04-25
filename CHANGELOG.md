# Changelog

すべての変更は Keep a Changelog 準拠で記載しています。  
現在のバージョン: 0.1.0 — 2026-04-25

## [0.1.0] - 2026-04-25

### Added
- 基本アプリケーション初期実装（KabuSys v0.1.0）。
- 実行スクリプト
  - run_execution.py
    - ExecutionEngine 起動用エントリポイント。
    - KABUSYS_ENV=paper_trading の場合、専用の Paper Trading DB（デフォルト: data/paper_trading.db）を使用し、本番 DB と分離。
    - ブローカークライアントは BrokerClientFactory 経由で生成。
    - エンジンはデーモンスレッドで稼働し、 data/stop_requested.flag を検知すると安全に停止。
    - 実行中 PID を data/execution.pid に保存（Engine 側の pid_file を使用）。
    - 起動時にプロセス優先度を "high" に設定。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト: 60 秒）。不正値はデフォルトへフォールバックし警告を出力。
    - 監視は KABUSYS_ENV に関わらず本番 sqlite_path（Settings.sqlite_path）を使用して監視テーブルを初期化。
    - data/stop_requested.flag を検知してループを終了。
    - 起動時にプロセス優先度を "high" に設定。
- 設定関連
  - config.py
    - .env 自動読み込み（プロジェクトルート検出: .git または pyproject.toml を基準）。
    - 自動読み込みは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - .env の読み込みは .env（上書き不可）→ .env.local（上書き可）順で実行。OS 環境変数は保護される（protected）。
    - .env パース処理はクォート、escape、コメントに対応する堅牢な実装。
    - Settings クラスを提供し、各種設定値（DB パス、API トークン、モード判定フラグ、各種閾値 等）をプロパティ経由で取得。値検証（有効な列挙値チェック、必須値チェック、数値変換など）を実装。
    - PAPER_FILL_MODE の検証（有効値: "instant", "partial", "never", "reject"）。
  - config_setup.py
    - 対話式ウィザードで .env の初期作成・更新を支援。
    - 主要設定項目（KABUSYS_ENV、JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、DB パス、LOG_LEVEL、KILL_FLAG_CLEAR_ON_START など）に対応。
    - 既存 .env 読み込み・既存値の Enter 再利用、シークレットのマスク表示、保存確認を提供。
- 設定検証ツール
  - validate_config.py
    - .env と config/*.yaml の事前検証 CLI。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性チェック、DB パス親ディレクトリ存在チェック、YAML パースチェック（PyYAML がインストールされている場合）、本番向けガード（KABUSYS_ENV=live 時の注意）などを実装。
    - --strict オプションで警告も失敗扱いにできる。
- ログ関連ユーティリティ
  - utils/logging_setup.py
    - ルートロガーに StreamHandler (stdout) と TimedRotatingFileHandler（日次、30日保持）を設定するヘルパーを実装。
    - LOG_LEVEL, LOG_DIR の解決順を実装。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソール出力のみで継続する。
    - 既存ハンドラは再設定時に一度 flush/close してから削除（多重設定防止）。
- プロセス制御ユーティリティ
  - utils/process_priority.py
    - Windows と POSIX 系（Linux, Darwin, FreeBSD）を吸収したプロセス優先度設定（high/normal/low）を実装。
    - CPU affinity 設定ユーティリティ set_cpu_affinity() を提供（N コアに固定）。
    - 権限不足や未対応環境では警告を出して安全にスキップ。
- ポートフォリオ構築ライブラリ
  - portfolio/portfolio_builder.py
    - select_candidates(): スコア降順で候補選定（同点は signal_rank でタイブレーク）。
    - calc_equal_weights(), calc_score_weights(): 等金額配分・スコア加重配分（スコア総和が 0 の場合は等分へフォールバック）。
  - portfolio/risk_adjustment.py
    - apply_sector_cap(): セクター集中制限（既存保有比で閾値超過セクターの新規候補を除外、"unknown" セクターは除外しない）。
    - calc_regime_multiplier(): 市場レジーム（bull/neutral/bear）に応じた投下資金乗数を返す（未知値は警告の上 1.0 でフォールバック）。
  - portfolio/position_sizing.py
    - calc_position_sizes(): allocation_method（"risk_based", "equal", "score"）に基づく発注株数計算。lot_size（単元株）への丸め、1銘柄上限・aggregate cap、cost_buffer を考慮したスケーリングロジックを実装。
- ツール
  - tools/paper_verification_report.py
    - Paper Trading 向け検証レポート生成スクリプト。
    - デフォルト DB: data/paper_trading.db（環境変数 PAPER_TRADING_SQLITE_PATH、--db オプションで上書き可）。
    - 指標: 稼働率（uptime）、注文成功率（fill rate）、送信率（send rate）、P95 レイテンシ 等。閾値を超えないか PASS/FAIL 判定を行う。
    - --from / --to による期間指定対応。
- 研究用モジュール（部分実装）
  - research/factor_research.py
    - DuckDB を使ったファクター計算モジュールの骨組み（モメンタム等の算出を想定）。（ファイル最後が未完で一部実装中）

### Changed
- ログ出力: 全スクリプトは共通の setup_logging を利用して統一的にログを構成。
- .env 読み込みの挙動を明確化（OS 環境変数保護、.env.local による上書きサポート）。

### Fixed
- N/A（初期リリースのため重大なバグ修正履歴はなし）。

### Notes / Migration / Breaking changes
- 監視（SystemMonitor）は KABUSYS_ENV に関わらず Settings.sqlite_path（デフォルト data/monitoring.db）を使用して監視テーブルを初期化します。これは監視データを本番監視 DB に一元化するための仕様です。必要に応じて設定を変更してください。
- Paper Trading を行う場合は KABUSYS_ENV=paper_trading を設定し、PAPER_TRADING_SQLITE_PATH（環境変数）または config_setup で指定することで監視 DB と完全に分離された data/paper_trading.db に取引ログを記録できます。
- MONITOR_POLL_INTERVAL は 0 や負の値を受け付けません。不正値が指定された場合は警告を出して既定値（60 秒）にフォールバックします。
- .env の自動読み込みは便利ですが、テストや特別な実行環境では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自動読み込みを無効化できます。
- Settings のいくつかのプロパティは値検証を行います（例: KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE）。不正な設定を入れると ValueError が発生します。起動前に validate_config を実行して確認することを推奨します。
- process_priority の設定は実行環境の権限に依存します。権限不足や未対応 OS では設定がスキップされます（警告ログあり）。

### Known issues / TODO
- research/factor_research.py は途中でファイルが切れており（未完）、ファクター計算の全実装が完了していません。今後のリリースで完成予定。
- position_sizing.calc_position_sizes:
  - price が欠損（0.0）だとエクスポージャー計算や株数算出で過小評価する可能性があり、将来的に前日終値や取得原価をフォールバックする機能を検討中（注釈あり）。
- 将来的な拡張:
  - 銘柄別単元（lot_size）の管理を stocks マスタに持たせる設計への拡張を想定。
  - logging_setup のファイルハンドラ関連のエラー処理やバックアップ戦略の追加。

---

開発者向けメモ:
- パッケージバージョンは src/kabusys/__init__.py にて __version__ = "0.1.0" として定義しています。リリース時はここを更新してください。