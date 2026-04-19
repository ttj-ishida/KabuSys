CHANGELOG
=========

すべての変更は Keep a Changelog の形式に準拠しています。
http://keepachangelog.com/ja/1.0.0/

Unreleased
----------

（なし）

0.1.0 - 2026-04-19
------------------

Added
- 初回リリース: KabuSys v0.1.0 を追加。
- 起動スクリプト / CLI
  - run_execution: ExecutionEngine 起動スクリプト（KABUSYS_ENV により本番/ペーパートレードを切替、ペーパートレード時は専用 DB を使用）。
  - run_monitoring: SystemMonitor ポーリングループ起動スクリプト（MONITOR_POLL_INTERVAL で間隔上書き可能、停止フラグ監視）。
  - validate_config: 設定検証 CLI（必須環境変数・パス・YAML パース・本番時ガード等のチェック、--strict オプション）。
  - config_setup: 対話式 .env 作成/更新ウィザード（シークレット入力マスク、既存 .env の読み込み・再利用）。
  - tools.paper_verification_report: ペーパートレード検証レポート生成スクリプト（期間指定・P95 等の指標算出、合否判定基準付き）。
- 設定管理
  - Settings クラス: 環境変数 / .env 自動読み込み（プロジェクトルート探索、.env / .env.local の読み込み順、KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化）。
  - .env パーサーの強化: export プレフィックス、シングル/ダブルクォート、エスケープ、インラインコメントの取り扱いに対応。
  - 各種設定プロパティ（DB パス、PID/kill フラグパス、閾値、PAPER_FILL_MODE 等）を提供。
- 実行・監視基盤
  - SQLite / DuckDB の組合せによるデータ保存（monitoring 用 SQLite、分析用 DuckDB）。
  - ペーパートレード時の DB 分離（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）。
  - 停止フラグ（data/stop_requested.flag 等）と PID ファイルを用いた安全な起動・停止制御。
  - run_monitoring: 例外ハンドリングでポーリングループ継続（check_once 内の例外をログ出力しリトライ）。
- ポートフォリオ構築（純粋関数群、DB 参照なし）
  - portfolio_builder: buy シグナルの候補選定（スコア降順、signal_rank によるタイブレーク）、等金額／スコア加重の重み計算（全スコア 0 の場合は等金額へフォールバック）。
  - risk_adjustment: セクター集中制限（apply_sector_cap）、市場レジームに応じた資金乗数（calc_regime_multiplier、'bull'/'neutral'/'bear' マッピング）を実装。
  - position_sizing: 複数配分方式（"risk_based","equal","score"）対応、単元株（lot_size）丸め、per-position 上限・aggregate cap によるスケーリング、コストバッファ考慮。
- ユーティリティ
  - logging_setup: ルートロガーを統一的に設定（stdout StreamHandler + 日次ローテートの TimedRotatingFileHandler、LOG_DIR/LOG_LEVEL に依存）。
  - process_priority: Windows/Linux/Mac の差を吸収したプロセス優先度設定（nice / HIGH_PRIORITY_CLASS 等を使用、失敗時は警告でスキップ）。CPU affinity 設定補助も提供。
- 解析・リサーチ
  - research.factor_research: DuckDB を用いた定量ファクター計算（モメンタム、MA200 乖離、ATR、出来高等の計算設計。prices_daily/raw_financials を参照）。
- 監視／検証関連
  - monitoring DB 初期化ユーティリティを導入（init_monitoring_db を経由して監視テーブルの冪等初期化）。
  - paper_verification_report による自動判定基準（稼働率・成立率・送信率・P95 レイテンシ）を実装。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Removed
- （初回リリースのため該当なし）

Security
- .env は絶対にリポジトリにコミットしないよう config_setup のヘッダとドキュメントで明示。
- 設定検証で本番環境（KABUSYS_ENV=live）時の注意喚起を追加（LINE 通知設定や KILL_FLAG_CLEAR_ON_START の危険性を警告）。

Notes / Known limitations
- apply_sector_cap 内で価格が欠損（0.0）の場合にエクスポージャーが過小評価される可能性あり（コード内に TODO コメントあり）。将来的には前日終値や取得原価でのフォールバックを検討。
- position_sizing の lot_size は現状全銘柄共通で固定。将来的に銘柄別単元 (lot_map) を受け取る拡張を想定している。
- logging_setup はログディレクトリ作成に失敗した場合、ファイル出力をスキップしてコンソールのみで動作する設計。
- factor_research は DuckDB のテーブル構造（prices_daily, raw_financials）を前提としているため、実行前に該当テーブル／データの準備が必要。

開発者向け備考
- バージョン情報はパッケージ top-level の __version__ = "0.1.0" に格納。
- 自動 .env 読み込みはプロジェクトルート（.git または pyproject.toml）を起点に行うため、パッケージ配布後も適切に動作する想定。必要に応じて KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。