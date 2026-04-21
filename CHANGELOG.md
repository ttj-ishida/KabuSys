# CHANGELOG

すべての重要な変更は Keep a Changelog の形式に従って記載します。
リリースバージョンはパッケージの __version__ に基づきます。

なお、本 CHANGELOG はソースコードから推測して作成しています。実際のリリースノートやユーザー向けドキュメントとして利用する場合は、必要に応じて加筆・修正してください。

## [Unreleased]
- なし

## [0.1.0] - 2026-04-21
初回公開リリース。

### Added
- 全体
  - KabuSys パッケージ初期版を追加。自動売買システムのコアユーティリティ群、起動スクリプト、設定管理、検証ツール、ポートフォリオ構築ロジックなどを含む。
  - パッケージバージョンを `__version__ = "0.1.0"` として定義。

- 起動スクリプト / デーモン
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` によるポーリング間隔上書きをサポート（デフォルト: 60 秒）。不正な値は警告を出してデフォルトにフォールバック。
    - 監視は環境に関わらず本番の `sqlite_path` を使用して接続・初期化する設計。
    - 停止フラグ（data/stop_requested.flag）検出による安全停止をサポート。
  - run_execution.py
    - ExecutionEngine を起動するスクリプトを追加。
    - `KABUSYS_ENV=paper_trading` の場合はペーパートレード用の専用 SQLite（`PAPER_TRADING_SQLITE_PATH` / デフォルト: data/paper_trading.db）を使用し、本番 DB と分離。
    - BrokerClient のファクトリを用いて本番／モックブローカーを切り替え可能（paper_trading 用 MockBrokerClient を想定）。
    - デーモンはスレッドでエンジンを起動し、停止フラグ（data/stop_requested.flag）により安全に停止できる。PID ファイル出力をサポート。

- 設定管理
  - config.py
    - プロジェクトルート自動検出（.git または pyproject.toml）に基づく .env 自動ロード機能を実装（`.env` → `.env.local`、OS 環境変数を保護して上書き制御）。
    - 複雑な .env 行パースを実装（コメント、export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ対応）。
    - Settings クラスを提供し、環境変数のアクセスとバリデーションを集中管理（J-Quants, kabuAPI, DuckDB/SQLite パス, 各しきい値, KABUSYS_ENV/LOG_LEVEL の検証等）。
    - `paper_fill_mode`（ペーパートレードの約定モード）を厳密にバリデーション（"instant" / "partial" / "never" / "reject" のみ許容）。

- 設定ユーティリティ／CLI
  - config_setup.py
    - 対話式ウィザードで .env を初期作成／更新するツールを実装。
    - シークレット項目は入力時にマスクして表示。既存 .env の読み込みと Enter による既存値再利用をサポート。
    - 出力時に .env を上書きするための確認プロンプト付き。`.env` をコミットしない旨のヘッダを出力。
  - validate_config.py
    - 起動前に .env と config/*.yaml の整合性・必須設定をチェックする CLI を実装。
    - 必須環境変数（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD 等）の未設定検出、KABUSYS_ENV / LOG_LEVEL の妥当性チェック、DUCKDB/SQLITE のパス親ディレクトリ検査を実装。
    - PyYAML が未インストールの場合は YAML のパース検証をスキップして警告を出力。`--strict` オプションで警告を失敗扱いにできる。
    - KABUSYS_ENV=live の場合の追加ガード（LINE 通知未設定や KILL_FLAG_CLEAR_ON_START の危険設定の警告）を実装。

- ロギング・プロセス制御ユーティリティ
  - utils/logging_setup.py
    - アプリケーション共通のロギング初期化関数 `setup_logging(app_name, log_dir, level)` を提供。
    - stdout への StreamHandler と日次ローテート（TimedRotatingFileHandler）を組み合わせてルートロガーを設定。ログディレクトリ作成に失敗した場合はファイル出力をスキップしてコンソールのみで継続。
    - ログレベル、ログディレクトリ解決の優先度（引数 > 環境変数 > デフォルト）を実装。
    - ログファイルは `<log_dir>/<app_name>.log`、ローテーション保存日数は 30 日。
  - utils/process_priority.py
    - プラットフォーム差分を吸収する `set_process_priority(level)` を実装（Windows：HIGH_PRIORITY_CLASS 等、POSIX：nice 値で設定）。
    - `set_cpu_affinity(cpu_count)` を提供し、最初の N コアに固定する機能を実装。権限不足や未対応環境では警告を出して安全にスキップ。

- ポートフォリオ構築（純関数群）
  - portfolio/portfolio_builder.py
    - シグナル選定・重み算出ユーティリティを提供。
    - select_candidates: スコア降順（同点は signal_rank）で候補を絞る。
    - calc_equal_weights / calc_score_weights: 等金額配分／スコア加重配分を実装。スコア合計が 0 の場合は等配分にフォールバックして警告。
  - portfolio/risk_adjustment.py
    - セクター集中制限 apply_sector_cap を実装（既存保有のセクター比率が閾値を超える場合に新規候補を除外）。
    - 市場レジームに応じた投下資金乗数 calc_regime_multiplier を実装（"bull":1.0, "neutral":0.7, "bear":0.3、未知値は 1.0 でフォールバックして警告）。
  - portfolio/position_sizing.py
    - position sizing ロジックを実装（allocation_method: "risk_based", "equal", "score"）。
    - 単元株（lot_size）丸め、1 銘柄上限、aggregate cap、cost_buffer（手数料・スリッページ見積り）を考慮したスケーリングと残差処理（rasion に基づく追加配分）を実装。
    - 価格データ欠如時のスキップ、負値ハンドリング、available_cash によるスケールダウン等を実装。

- 取引・検証ツール
  - tools/paper_verification_report.py
    - ペーパートレード検証レポート生成スクリプトを追加。期間指定（--from/--to）や DB パス指定（--db / 環境変数 PAPER_TRADING_SQLITE_PATH）に対応。
    - system_status / trade_logs / risk_logs を参照して稼働率、注文成功率、送信率、リスク却下数、レイテンシ（平均/最大/P95）を算出し、定義済み閾値と比較して PASS/FAIL を判定。
    - P95 の計算、データ不足時の N/A 表示、DB ファイル存在チェックのエラーメッセージを実装。

- 研究モジュール（下位）
  - research/factor_research.py（ファクター計算モジュールの実装開始）
    - モメンタム、移動平均乖離、ATR、流動性等の計算を行う設計で、DuckDB の prices_daily / raw_financials を参照する構成を採用。モジュールの冒頭部分を追加（計算窓・関数の定義開始）。※ファイルは途中で切れているため、完全実装は今後。

### Changed
- なし（初回リリース）

### Fixed
- なし（初回リリース）

### Deprecated
- なし

### Removed
- なし

### Security
- config_setup.py の出力ヘッダに「.env は絶対に Git にコミットしないこと」と明示。シークレット（API トークン等）は .env に格納する設計だが、.env の扱いに注意する旨を記載。

---

補足メモ（実装上の注意点・設計上の挙動）
- .env 自動読み込みはプロジェクトルートの検出に成功した場合にのみ行われる。テスト等で自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定する。
- run_monitoring は監視 DB として Settings.sqlite_path を使用する設計であり、環境変数 KABUSYS_ENV に関わらず本番用 path を使う点に注意（運用時の DB 分離ポリシーに応じて運用者が調整してください）。
- process priority / CPU affinity やログディレクトリ作成は権限不足や未対応プラットフォームで安全にスキップするように実装されている（警告ログ出力）。
- position sizing / sector cap 等のロジックは多くのパラメータを受け取る純関数実装で、単体テストしやすい設計となっている。实际運用前にパラメータ（risk_pct, stop_loss_pct, max_position_pct, lot_size, cost_buffer 等）のチューニングが必要。

以上。必要であれば、各ファイルごとの詳細な変更点や使用例、運用手順（起動コマンド例、環境変数の推奨値など）を追記します。どの程度の詳細が必要か教えてください。