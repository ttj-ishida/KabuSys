# Changelog

すべての重要な変更はこのファイルに記録します。  
フォーマットは "Keep a Changelog" に準拠します。

現在のリリース:
- [0.1.0] - 2026-04-21

## [0.1.0] - 2026-04-21

### Added
- 初期リリースを追加（パッケージバージョン: 0.1.0）。
- 設定・環境変数管理
  - Settings クラスを追加し、アプリケーション設定を環境変数から取得する実装を提供。
  - .env ファイルの自動読み込み機能を追加（優先順位: OS 環境変数 > .env.local > .env）。自動ロードは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
  - .env パーサは `export KEY=val` 形式、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントを考慮した堅牢な実装。
  - 必須環境変数存在チェック用のユーティリティ（_require）を追加。
- 設定関連 CLI
  - `kabusys.config_setup`：対話式ウィザードで `.env` を初期作成 / 更新する機能を追加。シークレット項目のマスク表示、デフォルト値/選択肢のサポート、保存確認を実装。
  - `kabusys.validate_config`：起動前検証 CLI を追加。必須環境変数、KABUSYS_ENV の妥当性、ログレベル、DB パス、config/*.yaml の存在と YAML パース（PyYAML 利用可能時）等のチェックを実施。`--strict` オプションで警告を失敗扱いにできる。
- 実行/監視スクリプト
  - `run_execution.py` を追加: ExecutionEngine を起動するエントリポイント。プロセス優先度を高く設定し、DB 接続、ブローカークライアント生成、OrderManager / RiskManager / Reconciler の組立て、バックグラウンドスレッドでセッション実行を行う。`KABUSYS_ENV=paper_trading` の場合は専用の Paper Trading 用 SQLite（`PAPER_TRADING_SQLITE_PATH` / デフォルト `data/paper_trading.db`）を使用し、本番 DB と分離する設計。
  - `run_monitoring.py` を追加: SystemMonitor を定期ポーリングで実行する監視ループ。`MONITOR_POLL_INTERVAL` 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は環境にかかわらず本番の `SQLITE_PATH` を使用する点に注意。
  - 停止制御用のフラグファイル（`data/stop_requested.flag`）や PID ファイルを用いた起動／停止挙動を実装。
- ブローカー / 実行関連
  - `BrokerClientFactory`（実装参照）を利用して実行時に適切なブローカークライアントを生成（Paper Trading 時は Mock に切り替え想定）。
  - RiskManager のデフォルト設定（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker, max_drawdown など）を含む初期構成を追加。
- ロギング / プロセス制御ユーティリティ
  - `utils.logging_setup.setup_logging` を追加。ルートロガーに stdout 向け StreamHandler と日次ローテートする TimedRotatingFileHandler を設定。ログディレクトリの自動作成、既存ハンドラのクリアによる二重設定防止、環境変数/引数によるログレベル・ログディレクトリ解決を行う。ファイル出力の失敗時はコンソール出力へフォールバック。
  - `utils.process_priority` を追加。Windows / POSIX(Linux/Mac/FreeBSD) を吸収してプロセス優先度（high/normal/low）の設定を行う。CPU affinity 設定 (`set_cpu_affinity`) も提供。権限不足等のエラーは警告ログにフォールバック。
- ポートフォリオ構成モジュール
  - `portfolio.portfolio_builder` を追加:
    - select_candidates: BUY シグナルをスコア降順（同スコアは signal_rank 昇順）で並べ上位 N を選出。
    - calc_equal_weights / calc_score_weights: 等金額配分およびスコア加重配分を提供。スコア合計が 0 の場合は等分配にフォールバック（警告出力）。
  - `portfolio.risk_adjustment` を追加:
    - apply_sector_cap: セクター集中を監視し、既存保有のセクター比率が上限を超える場合に新規候補を除外するロジックを実装（"unknown" セクターはチェック対象外）。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投入資金乗数を返す（未知のレジームは 1.0 でフォールバック）。
  - `portfolio.position_sizing` を追加:
    - calc_position_sizes: allocation_method に応じた発注株数計算（"risk_based", "equal", "score" をサポート）。単元株（lot_size）で丸め、per-position 上限・aggregate cap（available_cash に合わせてスケールダウン）や cost_buffer（手数料・スリッページ見積り）を考慮する。価格欠損時のスキップ、スケールダウン時の端数処理（割合の大きい順に単元を追加）などを実装。
  - 上記モジュールは純粋関数としてメモリ内計算のみを行い、DB 参照を行わない設計。
- 分析 / ツール
  - `tools.paper_verification_report` を追加: Paper Trading の検証レポート生成スクリプト。稼働率、注文成功率（Fill Rate）、送信率、P95 レイテンシ等を算出し PASS/FAIL 判定を出力。P95 計算、日付フィルタ（--from/--to）、DB パス解決（引数 > 環境変数 > デフォルト）を実装。デフォルト閾値は稼働率 99%、Fill Rate 90%、Send Rate 95%、P95 200 ms。
- リサーチ / ファクター計算（着手）
  - `research.factor_research` を追加（モメンタム等のファクター計算実装開始）。DuckDB 接続を受け取り prices_daily / raw_financials を用いてモメンタム、MA200乖離、ATR、流動性指標などを計算する設計方針を反映（実装は続きあり）。

### Changed
- （初期リリースのため該当なし）

### Fixed
- （初期リリースのため該当なし）

### Deprecated
- （初期リリースのため該当なし）

### Removed
- （初期リリースのため該当なし）

### Security
- （該当なし）

---

注記:
- run_monitoring は明示的に本番用の sqlite_path を使用する設計になっているため、開発やペーパートレード用 DB と分離したい場合は運用上の配慮が必要です。
- `.env` は機密情報を含むため、生成された `.env` を Git 等にコミットしないようドキュメントにも明記済みです（config_setup のヘッダ参照）。