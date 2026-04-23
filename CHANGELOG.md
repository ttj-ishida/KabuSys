# CHANGELOG

すべての注目すべき変更をここに記録します。  
フォーマットは「Keep a Changelog」に準拠します。

## [Unreleased]

## [0.1.0] - 2026-04-23
初回リリース。KabuSys のコア機能群（設定管理、起動スクリプト、実行エンジン連携、監視、ポートフォリオ構築ユーティリティ、各種 CLI/ツール、ユーティリティ）が含まれます。

### Added
- 全体
  - パッケージバージョンを `__version__ = "0.1.0"` として公開。
  - デフォルトのデータ・ログ格納パスを含む設定・起動用スクリプト群を追加。

- 設定管理
  - `kabusys.config.Settings`：環境変数ベースの設定ラッパーを実装。J-Quants / kabu API / DB パス / 監視閾値 / ログ関連の設定プロパティを提供。
  - 自動 .env 読み込み機能：プロジェクトルート（.git または pyproject.toml）を探索して `.env` / `.env.local` を読み込み。OS 環境変数を保護する仕組みを実装（上書き制御）。
  - `.env` のパースは `export KEY=val` 形式、クォート文字内のエスケープ、行内コメントの扱い等に対応。
  - 環境変数自動ロードを無効化するためのフラグ `KABUSYS_DISABLE_AUTO_ENV_LOAD` をサポート。

- コンフィグ関連 CLI
  - `kabusys.config_setup`：対話式ウィザードで `.env` を作成／更新する CLI を追加。複数項目（KABUSYS_ENV、JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、DB パス、LOG_LEVEL、KILL_FLAG_CLEAR_ON_START など）をサポート。
  - `kabusys.validate_config`：起動前に設定不備を検出する検証ツールを追加。必須環境変数チェック、KABUSYS_ENV の妥当性、LOG_LEVEL の妥当性、DB パスの親ディレクトリ存在確認、config/*.yaml の存在・パースチェック、KABUSYS_ENV=live 時の追加ガード等を実装。`--strict` フラグで警告を FAIL 扱いにできる。

- 起動スクリプト / 実行基盤
  - `run_execution.py`：ExecutionEngine を起動するスクリプトを追加。
    - 起動時にプロセス優先度を "high" に設定。
    - `Settings` に基づき SQLite / DuckDB 接続を確立。
    - 環境に応じて paper_trading 用 DB（`PAPER_TRADING_SQLITE_PATH`）を使用し、本番 DB と完全分離（KABUSYS_ENV=paper_trading 時）。
    - `BrokerClientFactory` によるブローカークライアント生成（paper_trading 時は MockBrokerClient を使う想定）。
    - OrderRepository / OrderManager / RiskManager / Reconciler を組み立て、ExecutionEngine をバックグラウンドスレッドで実行。停止はプロジェクトの data/stop_requested.flag を検出して行う。PID ファイル管理あり。
  - `run_monitoring.py`：SystemMonitor のポーリングループ起動スクリプトを追加。
    - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL` で上書き可能（デフォルト 60 秒、不正値は警告してデフォルトにフォールバック）。
    - 監視用 DB 初期化（monitoring テーブル群）を保証し、Monitoring は環境にかかわらず本番 sqlite_path を使用する（監視データは本番 DB に保存する仕様）。
    - 起動時にプロセス優先度を "high" に設定し、停止フラグ（data/stop_requested.flag）検知でループ終了。

- モニタリング / DB
  - `monitoring.monitoring_db.init_monitoring_db`（参照として使用）により監視系テーブルの初期化を行う設計を採用（冪等）。
  - DuckDB と SQLite の両方を利用する設計（分析用に DuckDB、運用ログや監視に SQLite）。

- ポートフォリオ構築（純粋関数群）
  - `kabusys.portfolio.portfolio_builder`
    - select_candidates：BUY シグナルをスコア降順＆タイブレークでソートし上位 N を選択。
    - calc_equal_weights：等金額配分を計算。
    - calc_score_weights：スコア加重配分を計算（全スコア 0 の場合は等分にフォールバックし WARNING を出力）。
  - `kabusys.portfolio.risk_adjustment`
    - apply_sector_cap：セクター集中を防ぐため、既存保有のセクター比率が閾値（max_sector_pct）を超える場合に当該セクターの新規候補を除外。
    - calc_regime_multiplier：市場レジーム（bull/neutral/bear）に応じた投下資金乗数を返す（未知レジームは 1.0 でフォールバック）。
  - `kabusys.portfolio.position_sizing`
    - calc_position_sizes：等配分/スコア配分/リスクベース配分をサポート。単元株（lot_size）丸め、1 銘柄上限、aggregate cap に基づくスケーリング（余りの分配ロジック含む）、cost_buffer（手数料・スリッページ見積り）を考慮する。

- ユーティリティ
  - `kabusys.utils.logging_setup.setup_logging`：
    - ルートロガーへの統一的な設定。コンソール（stdout）ストリームハンドラと TimedRotatingFileHandler（毎日ローテート、30 日保持）を追加。
    - ログレベル解決順：引数 > LOG_LEVEL 環境変数 > デフォルト INFO。
    - ログディレクトリは引数 > LOG_DIR 環境変数 > デフォルト logs/。ディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
  - `kabusys.utils.process_priority`：
    - set_process_priority(level)：Windows/Linux/Mac の差分を吸収して優先度（high/normal/low）を設定。権限不足や未対応 OS の場合は警告を出してスキップ。
    - set_cpu_affinity(cpu_count)：プロセスを最初の N コアにピン留め（可能な環境のみ）。不正引数は ValueError。
    - psutil に依存するが、例外時は安全に警告して継続する実装。

- ツール / レポート
  - `kabusys.tools.paper_verification_report`：ペーパートレーディング用検証レポート生成スクリプトを追加。
    - SQLite の paper_trading DB（デフォルト data/paper_trading.db）を読み、システム稼働率（system_status）、注文成功率（trade_logs）、リスク却下数（risk_logs）、API レイテンシ（trade_logs.latency_ms）等の指標を集計・出力。
    - P95 レイテンシ計算、閾値に基づく PASS/FAIL 判定（稼働率 >=99%、成立率 >=90%、送信率 >=95%、P95 <=200 ms）。
    - CLI で期間指定（--from/--to）や DB パス指定（--db）をサポート。

- リサーチ / ファクター計算（骨組み）
  - `kabusys.research.factor_research`：DuckDB を用いたファクター計算モジュールの骨格を追加（Momentum / Value / Volatility / Liquidity 等を想定）。calc_momentum 関数など、prices_daily/raw_financials を参照して日付・銘柄ごとのファクターを返す設計。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Removed
- （初回リリースのため該当なし）

### Security
- 環境変数や機密情報は .env に保存される想定だが、README 等で .env の Git 管理禁止を明記する（config_setup に警告ヘッダを含む）。

---

注記:
- 実装は例示的な安全弁（ファイル作成失敗時のフォールバック、例外キャッチ・ログ出力、停止フラグ検知）を多用しており、本番運用での堅牢性を考慮した設計になっています。
- 実際の振る舞い（ブローカークライアントの具体実装、SystemMonitor の詳細、ExecutionEngine の振る舞い等）は本 CHANGELOG の範囲外のモジュール実装に依存します。必要であればそれらのモジュールの差分や詳細な使用法、既知の制限を別途まとめます。