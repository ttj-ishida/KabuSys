# CHANGELOG

すべての変更は Keep a Changelog の形式に準拠しています。主にコードベースの初期機能実装を反映したリリースノートです。

## [Unreleased]

## [0.1.0] - 2026-04-22

### Added
- パッケージ基本情報
  - パッケージバージョンを `__version__ = "0.1.0"` として追加。

- 起動スクリプト / ランタイム
  - run_execution.py
    - ExecutionEngine 起動用スクリプトを追加。
    - 起動時にプロセス優先度を "high" に設定。
    - KABUSYS_ENV が `paper_trading` の場合は専用の Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）を使用し、本番 DB と分離。
    - BrokerClientFactory を使ったブローカークライアントの生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て、ExecutionEngine のスレッド起動、停止フラグ（data/stop_requested.flag）による安全停止をサポート。
    - PID ファイル（data/execution.pid）管理の仕組みを組み込み。

  - run_monitoring.py
    - SystemMonitor ポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` によりポーリング間隔を上書き可能（デフォルト: 60秒）。不正値はデフォルトにフォールバック。
    - Monitoring は KABUSYS_ENV にかかわらず本番用 sqlite_path を使用する（監視データは一元管理）。
    - 停止フラグ検知でループを終了。KeyboardInterrupt に対応。
    - SQLite / DuckDB 接続の初期化とクローズ処理を実装。

- 設定管理 / CLI
  - config.py
    - Settings クラスを実装し、環境変数から各種設定を安全に取得・検証する機能を提供。
    - .env 自動読み込み（プロジェクトルートの `.env` と `.env.local`、OS 環境変数を保護）を実装。自動ロードは `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
    - .env の行パーサーは `export` プレフィックス、クォート、エスケープ、インラインコメント（限定的）に対応。
    - 各プロパティで型変換と妥当性検査を行う（例: `PAPER_FILL_MODE` の有効値チェック、`KABUSYS_ENV`、`LOG_LEVEL` の検証）。
    - DB パス、PID/kill flag パスや監視閾値等のデフォルト値を提供。

  - config_setup.py
    - 対話式ウィザードで .env を生成・更新する CLI を追加。
    - 各設定項目の説明、既存値のマスク表示（シークレット）とデフォルト提示、書き込み機能を提供。

  - validate_config.py
    - 起動前の設定検証 CLI を追加。
    - 必須環境変数のチェック、KABUSYS_ENV/LOG_LEVEL の妥当性、DB パスの親ディレクトリ存在確認、config/*.yaml の存在と（PyYAML があれば）パース検証を実施。
    - `--strict` オプションで警告も失敗扱いにできる。
    - 本番環境向けの注意喚起（LINE 通知設定未設定、KILL_FLAG_CLEAR_ON_START の危険性）を追加。

- ポートフォリオ構築ライブラリ（pure functions）
  - portfolio/portfolio_builder.py
    - 候補選定: select_candidates（スコア降順、同点時 signal_rank によるタイブレーク）。
    - 重み計算: calc_equal_weights、calc_score_weights（スコア合計が 0 の場合は等配分にフォールバック）。

  - portfolio/risk_adjustment.py
    - セクター集中制限: apply_sector_cap（既存保有を考慮したセクター別エクスポージャ計算と候補除外）。unknown セクターは制限を適用しない。
    - レジーム乗数: calc_regime_multiplier（"bull"/"neutral"/"bear" に応じた乗数。未知のレジームは警告を出して 1.0 にフォールバック）。

  - portfolio/position_sizing.py
    - 株数決定ロジック: calc_position_sizes を実装。
    - risk_based / equal / score の allocation_method をサポート。
    - 単元株（lot_size）丸め、1 銘柄上限（max_position_pct）、aggregate cap（available_cash を超える場合のスケーリング）を実装。
    - cost_buffer によるコスト保守見積り、スケールダウン時の端数配分ロジックを実装。
    - 現状は全銘柄共通 lot_size を想定。将来的拡張のための TODO を残す。

  - portfolio/__init__.py
    - 上記関数群をパッケージとして公開。

- ユーティリティ
  - utils/logging_setup.py
    - 共通ログ設定ユーティリティを追加。ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（日次、30日保持）を設定。
    - ログディレクトリ作成に失敗した場合はファイル出力をスキップし、コンソール出力のみで継続するフォールバックを実装。
    - ログレベル / ログディレクトリの解決ルールを実装。

  - utils/process_priority.py
    - psutil を用いたプロセス優先度設定ユーティリティを追加（Windows / POSIX の差分吸収）。
    - CPU affinity 設定関数 set_cpu_affinity を追加（利用可能コア数を超える場合の挙動制御、権限不足時に警告）。
    - 設定失敗時に警告を出して安全にスキップする実装。

- ツール
  - tools/paper_verification_report.py
    - Paper Trading 用 SQLite（PAPER_TRADING_SQLITE_PATH）を解析し、検証レポートを出力するスクリプトを追加。
    - 指標: 稼働率（uptime）、注文成功率（fill_rate）、送信率（send_rate）、API レイテンシ（avg / max / P95）、リスク却下数。
    - パス／期間フィルタ（--from / --to / --db）に対応。基準値を用いた PASS/FAIL 判定を出力。

- 研究用モジュール（開始実装）
  - research/factor_research.py
    - ファクター計算モジュールの骨組みを追加（Momentum / Value / Volatility / Liquidity の設計方針、定数定義、calc_momentum の開始実装）。
    - DuckDB を用いた prices_daily / raw_financials 参照設計。まだ未完の箇所あり（実装途中）。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Deprecated
- （現在なし）

### Security
- （今回の変更における既知のセキュリティ懸念はなし）

---

### 重要なデフォルト動作・注意点
- .env 自動ロード
  - プロジェクトルート（.git または pyproject.toml を基準）から `.env` / `.env.local` を自動で読み込みます。OS 環境変数は保護され、`.env.local` は既存値を上書きします。自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

- DB 分離
  - Paper Trading（KABUSYS_ENV=paper_trading）では paper_sqlite_path（デフォルト: data/paper_trading.db）が使用され、本番監視 DB（data/monitoring.db）とは分離されます。
  - Monitoring は常に settings.sqlite_path（デフォルト: data/monitoring.db）を使用します（環境に依存せず監視データは一元管理される設計）。

- ログ
  - デフォルトログディレクトリは `logs/`、ログは日次ローテート・30日分保持。ディレクトリ作成失敗時はファイル出力を行わず stdout のみで稼働。

- プロセス優先度
  - 起動スクリプトは最初にプロセス優先度を "high" に設定します。権限不足や未対応 OS の場合は警告を出してスキップします。

- 環境変数/設定の検証
  - `validate_config.py` により起動前に必須設定や構成ファイルの検証が可能。特に本番（KABUSYS_ENV=live）では LINE 通知設定や kill-flag の設定を確認することを推奨。

### 既知の課題・TODO
- research/factor_research.py の実装が途中（ファイル末尾が未完）。momentum 等の計算ロジックは今後完成予定。
- portfolio/risk_adjustment.apply_sector_cap:
  - price が欠損（0.0）の場合、エクスポージャが過少見積りされる可能性あり。将来的に前日終値や取得原価等のフォールバックを検討する旨の TODO を残しています。
- portfolio/position_sizing:
  - 現状は全銘柄共通の lot_size を想定。将来的に銘柄別 lot_size をサポートする拡張予定（stocks マスタに lot_size を持たせる等）。
- process_priority / set_cpu_affinity:
  - 権限やプラットフォームによっては設定できないケースがあるため、失敗時は単に警告を出してスキップします。
- .env のパーサーは多くのケースを扱いますが、複雑な構文やすべての shell 互換性（複数行クォート、ヒアドキュメント等）はサポートしていません。

---

必要であれば、セクションの補足（例: 各 CLI の使い方例、環境変数一覧やデフォルト値の表）を追記します。どの項目を詳述したいか教えてください。