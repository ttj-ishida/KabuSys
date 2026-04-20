# Changelog

すべての notable な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。

全般的なルール: 追加 (Added)、変更 (Changed)、修正 (Fixed)、削除 (Removed) のカテゴリを使用します。

## [0.1.0] - 2026-04-20

### Added
- 初回リリース。日本株自動売買システム「KabuSys」の基本コンポーネントを追加。
- 起動スクリプト
  - run_execution.py
    - ExecutionEngine を起動・管理する CLI ランチャーを追加。
    - KABUSYS_ENV が `paper_trading` の場合は専用のペーパートレード用 SQLite DB（デフォルト: data/paper_trading.db）を使用し、本番 DB と完全に分離。
    - 停止フラグ（data/stop_requested.flag）と PID ファイル（data/execution.pid）による外部制御をサポート。
    - バックグラウンドスレッドでエンジンを実行し、停止フラグ検知で安全に停止する仕組みを実装。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で上書き可能（デフォルト 60 秒）。
    - 監視は環境に依らず production の sqlite_path（デフォルト: data/monitoring.db）を使用。
    - 停止フラグ（data/stop_requested.flag）でループを終了。
- 設定関連
  - config.py
    - 環境変数 / .env ファイルの自動ロード機能を実装（.env, .env.local）。プロジェクトルートは .git または pyproject.toml を基準に自動検出。
    - 複数の設定プロパティを提供（J-Quants、kabuステーション、LINE、DB パス、監視閾値など）。
    - PAPER_FILL_MODE, PAPER_TRADING_SQLITE_PATH といった paper_trading 向け設定を追加。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能。
  - config_setup.py
    - 対話式ウィザードで .env を作成／更新する CLI を追加。デフォルト値表示、シークレットマスク、選択肢サポートなど。
  - validate_config.py
    - 起動前に .env と config/*.yaml の簡易検証を行う CLI を追加。必須環境変数チェック、KABUSYS_ENV 検証、パス存在チェック、YAML パース（PyYAML があれば）を実行。
    - --strict オプションで警告もエラー扱いにできる。
- ポートフォリオ構築モジュール
  - portfolio.portfolio_builder
    - select_candidates: スコア降順で候補選定。
    - calc_equal_weights / calc_score_weights: 等金額配分・スコア加重配分を実装。スコア合計が 0 の場合は等配分にフォールバック。
  - portfolio.risk_adjustment
    - apply_sector_cap: セクター集中上限チェック（max_sector_pct）に基づく候補フィルタ。
    - calc_regime_multiplier: レジーム（bull/neutral/bear）に応じた投下資金乗数を返すユーティリティ。
  - portfolio.position_sizing
    - calc_position_sizes: weight / candidates / risk ベース等の allocation_method に基づいて発注株数（単元株丸め）を計算。aggregate cap（available_cash）を超える場合のスケールダウン・端数処理も実装。
- ユーティリティ
  - utils.logging_setup
    - ルートロガーの統一的セットアップを提供。stdout 出力 + 日次ローテーションファイル（logs/<app_name>.log）を追加。ログローテーションは 30 日分保持。
    - LOG_DIR / LOG_LEVEL による上書き、ハンドラの二重登録防止、ファイル作成失敗時のフォールバック処理を実装。
  - utils.process_priority
    - set_process_priority(level): Windows / POSIX を吸収してプロセス優先度（high/normal/low）を設定。権限不足や未対応 OS は警告を出してスキップ。
    - set_cpu_affinity(cpu_count): カレントプロセスを最初の N コアにピン留めする補助関数。
- ツール
  - tools.paper_verification_report
    - ペーパートレード用検証レポート生成スクリプトを追加。system_status / trade_logs / risk_logs から稼働率・注文成功率・送信率・レイテンシ等を集計し、PASS/FAIL 判定を行う。
    - デフォルト閾値（稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200 ms）を設定。
    - 日付フィルタ（--from / --to）、DB パスの上書き（--db / 環境変数）をサポート。
- データアクセス
  - DuckDB を分析用 DB として導入（duckdb 接続を使用）。prices_daily 等のテーブル想定（research.factor_research 参照）。
- その他
  - パッケージ初期バージョンを設定: __version__ = "0.1.0"

### Changed
- （初回リリースにつき該当なし）

### Fixed
- .env パーサーの堅牢化
  - export KEY=val 形式、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメント処理、コメント判定ルールなどをサポート。これにより .env の柔軟な記述に対応。
- logging_setup: ログディレクトリ作成失敗時に StreamHandler のみで継続するフォールバックを実装（起動時にログ出力不能で落ちないように改善）。
- process_priority: 例外発生時に警告を出して続行するよう変更（権限やプラットフォーム差異の影響を吸収）。

### Removed
- （初回リリースにつき該当なし）

### Migration / 注意点
- .env 自動ロード
  - 起動時にプロジェクトルートの .env / .env.local が自動で読み込まれます。自動ロードを無効化する場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
  - OS 環境変数は保護され、.env.local の override 時も OS 環境変数は上書きされません。
- 本番/ペーパートレードの DB 分離
  - run_execution は KABUSYS_ENV=paper_trading の場合に PAPER_TRADING_SQLITE_PATH（設定名: paper_sqlite_path）を使用します。運用時に意図しない DB を上書きしないよう注意してください。
- Kill / Stop フラグ
  - 外部からプロセスを停止するためのファイルベースフラグが導入されています（data/stop_requested.flag、data/kill.flag）。本番での挙動を変更する可能性があるため設定値（KILL_FLAG_CLEAR_ON_START など）に注意してください。
- PAPER_FILL_MODE
  - paper_trading の動作（MockBrokerClient の約定挙動）を制御する PAPER_FILL_MODE（instant/partial/never/reject）を導入。無効な値は起動時に例外となります。
- ログ
  - デフォルトで logs/<app_name>.log に日次ローテーションでログが保存されます。ログディレクトリやログレベルは環境変数（LOG_DIR, LOG_LEVEL）で調整可能です。

---

今後の予定（想定）
- research.factor_research の完全実装（ファクター計算の SQL/Python 実装の続き）
- Execution / Monitoring のより詳細な稼働監視・メトリクス収集
- Strategy モジュールの追加と統合テスト

（この CHANGELOG はコードベースの内容を元に推測して作成しています。実際のリリースノートはプロジェクト運用ポリシーに従って調整してください。）