# Changelog

すべての重要な変更点を記録します。フォーマットは「Keep a Changelog」準拠です。

※ 初回公開リリース: 0.1.0

## [Unreleased]
（なし）

## [0.1.0] - 2026-04-21

### Added
- 基本アプリケーションパッケージを追加（kabusys）。
  - パッケージバージョンを `__version__ = "0.1.0"` として設定。

- 実行用スクリプト
  - run_execution.py
    - ExecutionEngine の起動スクリプトを追加。
    - KABUSYS_ENV が `paper_trading` の場合はペーパートレード専用 SQLite（デフォルト: data/paper_trading.db）を使用して本番 DB と完全分離する実装。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository/OrderManager/ RiskManager/Reconciler の組み立て、ExecutionEngine のスレッド起動を実装。
    - 停止手段として data/stop_requested.flag の存在検知および data/execution.pid を使用。
    - RiskManager のデフォルト設定（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）を定義し、初期 portfolio value は broker.get_available_cash() を基に設定。

  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト: 60秒）。不正値はログ警告後デフォルトにフォールバック。
    - 監視は環境にかかわらず本番用 sqlite_path（Settings.sqlite_path）を使用する仕様。
    - 起動時にプロセス優先度を "high" に設定。

- 設定管理
  - config.py
    - Settings クラスを実装し、環境変数経由で各種設定を取得するユーティリティを提供。
    - .env 自動読み込み機能を実装（プロジェクトルートを .git / pyproject.toml で検出）。OS 環境変数を保護して `.env` / `.env.local` を読み込む。
    - 環境変数パースロジック（クォート、エスケープ、inline コメントの扱い）を実装。
    - 各種プロパティ: J-Quants / kabu API / LINE / DB パス(duckdb/sqlite)/paper_fill_mode のバリデーション、監視閾値、PID/kill flag パス等を提供。
    - `KABUSYS_DISABLE_AUTO_ENV_LOAD` による自動ロード無効化をサポート。

  - config_setup.py
    - .env を対話的に初期作成・更新するウィザードを実装。
    - 入力補助（既存値の再利用、選択肢、シークレットマスク表示、保存確認）あり。
    - .env の書式と注意文を出力（.env を Git にコミットしない旨の注意を含む）。

  - validate_config.py
    - 起動前の設定検証 CLI を実装。
    - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性、DB パス親ディレクトリ存在確認、config/*.yaml の存在・パース確認（PyYAML がない場合はスキップ）などを行う。
    - `--strict` オプションで警告を FAIL として扱う機能を追加。

- ログ・ユーティリティ
  - utils/logging_setup.py
    - 全起動スクリプトで共通利用するログ設定ユーティリティを追加。
    - stdout 出力用 StreamHandler と 日次ローテーション（TimedRotatingFileHandler、30日保持）のファイル出力を設定。
    - 環境変数 `LOG_LEVEL` / `LOG_DIR` を考慮した解決順、既存ハンドラの二重設定防止処理を実装。
    - ログ出力ディレクトリ作成に失敗した場合はファイルハンドラをスキップしてコンソール出力のみで継続。

  - utils/process_priority.py
    - クロスプラットフォームのプロセス優先度設定ユーティリティを追加（Windows / POSIX を吸収）。
    - set_process_priority(level: "high"|"normal"|"low") と set_cpu_affinity(cpu_count) を提供。
    - psutil を使用し、権限不足や未対応環境では警告を出して無効化。

- ポートフォリオ構築（純関数群・メモリ内計算）
  - portfolio/portfolio_builder.py
    - 候補選定 (select_candidates)、等金額重み(calc_equal_weights)、スコア加重(calc_score_weights) を実装。
    - スコア合計が 0 の場合に等金額にフォールバックする挙動を実装（警告ログあり）。

  - portfolio/risk_adjustment.py
    - セクター集中制限 apply_sector_cap を実装（既存保有のセクター別時価を計算し上限超過セクターの新規候補を除外）。
    - 市場レジームに応じた投下資金乗数 calc_regime_multiplier を実装（"bull"=1.0, "neutral"=0.7, "bear"=0.3、未定義は警告とともに 1.0 フォールバック）。

  - portfolio/position_sizing.py
    - 発注株数計算 calc_position_sizes を実装。
    - allocation_method として "risk_based" / "equal" / "score" をサポート。
    - 単元株（lot_size）丸め、per-position 上限、aggregate cap（available_cash 超過時のスケーリング）を含む保守的な資金配分ロジックを実装。
    - cost_buffer による手数料/スリッページ見積りを考慮した計算、残余キャッシュを用いた端数配分ロジックを実装。

- データベース/分析関連
  - utils: duckdb への接続を起動スクリプトで確立（duckdb_conn を実行コンポーネントに渡す）。
  - monitoring.monitoring_db.init_monitoring_db を起動時に呼び出して監視テーブルの存在を保証（冪等）。

- ツール
  - tools/paper_verification_report.py
    - ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）から集計を行い検証レポートを生成する CLI を追加。
    - 指標: 稼働率(uptime)、注文成功率(fill rate)、送信率(send rate)、リスク却下数、API レイテンシ（avg/max/P95）などを算出。
    - 基準値（閾値）を定義して PASS/FAIL 判定を行う（稼働率 >= 99% など）。
    - --from/--to/--db オプションで期間と DB パス指定が可能。

- research
  - research/factor_research.py
    - ファクター計算モジュールの骨格を追加（モメンタム/MA/ATR/VOL/Liquidity に関する定数とドキュメント）。
    - calc_momentum のドキュメントと定数が用意され、DuckDB 接続経由で prices_daily を参照する設計を採用（関数本体は今後の実装を想定した骨組み）。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Deprecated
- （該当なし）

### Removed
- （該当なし）

### Security
- 環境変数の取り扱いについてシークレットは .env に保存すること、.env を Git に含めない旨の注意をドキュメント/ウィザードに追加。

## 注記 / 使用上の重要ポイント
- run_monitoring は監視用 SQLite を「環境にかかわらず」 Settings.sqlite_path（デフォルト data/monitoring.db）で使用します。開発中に誤って本番 DB を上書きしないよう注意してください。
- run_execution はペーパートレード時に paper_trading 専用 DB（PAPER_TRADING_SQLITE_PATH）を使用することで本番 DB と分離します。KABUSYS_ENV を適切に設定してください。
- .env の自動ロードはデフォルトで有効。テスト環境などで無効化したい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- PAPER_FILL_MODE の有効値は "instant" | "partial" | "never" | "reject" です。無効な値は Settings.paper_fill_mode により例外となります。
- ログ設定は既存ハンドラの二重追加を防ぐよう実装されていますが、外部から直接ルートロガーにハンドラを設定している場合は期待通りにならない可能性があります。
- process_priority / cpu_affinity の設定は権限やプラットフォームに依存します。権限不足時は警告ログを出してスキップします。

もし追加で CHANGELOG に含めたい細かい実装詳細や、特定ファイルごとの責務・既知の制限（TODO や未実装箇所）を明記したければ教えてください。必要に応じて Unreleased セクションや将来のマイルストーンも追記します。