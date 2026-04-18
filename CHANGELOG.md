# Changelog

すべての重要な変更をこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。

現在のリリース履歴は以下の通りです。

## [Unreleased]

（なし）

## [0.1.0] - 2026-04-18

初回公開リリース。KabuSys のコアユーティリティ、実行・監視スクリプト、ポートフォリオ構成ロジック、各種 CLI ツールを含みます。

### Added
- 全体
  - パッケージ初期バージョンを追加（kabusys.__version__ = "0.1.0"）。
  - プロジェクトルート自動検出ロジックを導入（.git または pyproject.toml を基準）により、.env 自動読み込みが CWD に依存せず動作。
  - .env 自動ロード機能を実装（.env → .env.local の順、OS 環境変数を保護）。自動ロードは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。

- 設定関連
  - Settings クラスを導入し、環境変数からアプリ設定を安全に取得（値検証付き）。
  - 必須設定チェック（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD 等）と、各種環境変数の検証ロジックを追加。
  - Paper Trading 用の専用 SQLite パス（PAPER_TRADING_SQLITE_PATH / Settings.paper_sqlite_path）をサポート。
  - PAPER_FILL_MODE（"instant" / "partial" / "never" / "reject"）をサポートし不正値時は例外を発生。

- CLI / ユーティリティ
  - 対話式 .env 作成ウィザード（kabusys.config_setup.run_wizard / python -m kabusys.config_setup）を追加。
  - 設定検証 CLI（kabusys.validate_config / python -m kabusys.validate_config）を追加。--strict フラグで警告を FAIL 扱いにできる。
  - ロギング設定ユーティリティを実装（kabusys.utils.logging_setup.setup_logging）
    - stdout ストリームハンドラと日次ローテーション（TimedRotatingFileHandler）によるファイル出力を設定。
    - LOG_DIR 環境変数、app_name 引数でログファイル場所を指定可能。ファイル出力失敗時はコンソールのみで継続。
  - プロセス優先度・CPU affinity ユーティリティ（kabusys.utils.process_priority）を追加
    - Windows / POSIX の差分を吸収して優先度（high/normal/low）を設定。
    - CPU affinity を最初の N コアに固定する機能を提供。
    - psutil による操作で失敗した場合は安全に警告を出してスキップ。

- 実行 / 監視
  - ExecutionEngine 起動スクリプト（src/kabusys/run_execution.py）を追加。
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、paper_trading 用 DB（data/paper_trading.db）へ完全に分離して記録。
    - 起動時にプロセス優先度を "high" に設定。
    - 停止フラグ（data/stop_requested.flag）と実行 PID 管理（data/execution.pid）をサポート。停止フラグ検知で安全に終了・停止。
    - ExecutionEngine の構築に必要な OrderRepository / OrderManager / RiskManager / Reconciler を組み立てる処理を実装。
    - RiskManager に初期設定（max_position_pct 等）を設定し、初期 portfolio value を broker.get_available_cash() で取得。
  - SystemMonitor 起動スクリプト（src/kabusys/run_monitoring.py）を追加。
    - 環境にかかわらず「本番」sqlite_path を使用して監視 DB を初期化（監視は本番 DB に対して動作する仕様）。
    - ポーリング間隔を環境変数 MONITOR_POLL_INTERVAL で上書き可能（デフォルト 60 秒）。不正値は警告を出してデフォルトにフォールバック。
    - 停止フラグ（data/stop_requested.flag）検知でループ終了。KeyboardInterrupt も適切に処理。
    - check_once() 実行で例外が発生してもログに出力してポーリング継続。

- データ / レポート
  - Paper Trading 検証レポート生成スクリプトを追加（src/kabusys/tools/paper_verification_report.py）
    - system_status / trade_logs / risk_logs を集計して稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）を出力。
    - デフォルト DB は data/paper_trading.db。コマンドライン引数 --db / --from / --to をサポート。
    - 合格基準（稼働率 >= 99%、成立率 >= 90%、送信率 >= 95%、P95 <= 200ms）を定義し PASS/FAIL を判定。

- ポートフォリオ構築（純粋関数群）
  - 銘柄候補選定・重み計算（src/kabusys/portfolio/portfolio_builder.py）
    - select_candidates: スコア降順・同点は signal_rank でタイブレーク。
    - calc_equal_weights / calc_score_weights（score が全て 0 の場合は等分配にフォールバック）。
  - セクター集中制限・レジーム乗数（src/kabusys/portfolio/risk_adjustment.py）
    - apply_sector_cap: 既存ポジションのセクター比率が閾値を超える場合、同セクターの新規候補を除外（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: "bull"/"neutral"/"bear" に応じた乗数を提供（未知レジームは 1.0 でフォールバックし警告）。
  - ポジションサイズ計算（src/kabusys/portfolio/position_sizing.py）
    - allocation_method に "risk_based" / "equal" / "score" をサポート。
    - 単元株（lot_size）で丸め／最大ポジション上限、aggregate cap によるスケーリングと余り配分（fractional 残差の扱い）を実装。
    - cost_buffer による手数料・スリッページ見積りを考慮。

- リサーチ
  - ファクター計算モジュール（src/kabusys/research/factor_research.py）の骨組みを追加
    - Momentum / Value / Volatility / Liquidity の設計方針、定数、calc_momentum のインターフェイスを導入（DuckDB 経由で prices_daily / raw_financials を参照する想定）。
    - P95 計算や期間バッファ等の設計が含まれる。

### Changed
- なし（初回リリースのため無し）

### Fixed
- なし（初回リリースのため無し）

### Deprecated
- なし

### Removed
- なし

### Security
- なし

### Notes / Known issues
- research/factor_research.calc_momentum の実装は途中（ファイル末尾が途中で切れているため、完全実装が必要）。
- risk_adjustment.apply_sector_cap の価格欠損（price が 0.0 の場合）に関する TODO が残る（現在は過少評価される可能性あり）。将来的に前日終値や取得原価などのフォールバックを検討。
- position_sizing の lot_size は現在グローバル固定（デフォルト 100）。将来的には銘柄別 lot_map への拡張を想定するコメントあり。
- process_priority / set_cpu_affinity は OS や権限に依存するため、psutil のアクセス拒否や未実装例外発生時は警告を出して処理をスキップする設計。ただし、実稼働環境で十分な権限が必要。

---

今後の予定（例）
- research モジュールの各ファクター実装完了
- ExecutionEngine / SystemMonitor の統合テスト追加
- ドキュメント（PortfolioConstruction.md 等）とサンプル設定ファイルの整備

（この CHANGELOG はソースコードのコメント・実装から推測して作成しています。実際のリリースノート作成時には動作確認結果やテスト結果を反映してください。）