# Changelog

すべての重要な変更を記録します。フォーマットは「Keep a Changelog」に準拠します。  

注: エントリはソースコードの内容から推測して作成しています。

## [Unreleased]

### Added
- run_monitoring 起動スクリプトを追加（src/kabusys/run_monitoring.py）。
  - SystemMonitor のポーリングループを開始するエントリポイント。MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。
  - 停止フラグファイル（data/stop_requested.flag）による安全停止、logging/duckdb/sqlite の初期化、プロセス優先度設定を実装。
- run_execution 起動スクリプトを追加（src/kabusys/run_execution.py）。
  - ExecutionEngine を起動するエントリポイント。プロセス優先度設定、stop flag/ pid ファイル管理、スレッド実行制御を実装。
  - KABUSYS_ENV=paper_trading の際は paper_trading 用 SQLite（data/paper_trading.db 既定）を使用し、本番 DB と分離。MockBroker を利用する設計を想定。
- 環境設定管理クラス Settings を追加（src/kabusys/config.py）。
  - .env の自動読み込み（プロジェクトルート検出）と環境変数アクセサ（DB パス、API トークン、閾値など）を提供。
  - PAPER_FILL_MODE の検証、env 判定（development/paper_trading/live）などを実装。
- 設定検証 CLI を追加（src/kabusys/validate_config.py）。
  - 必須環境変数や config/*.yaml、パスなど起動前チェックを行う。--strict オプションで警告をエラー扱いにできる。
- 環境設定ウィザード CLI を追加（src/kabusys/config_setup.py）。
  - 対話式で .env を作成/更新するウィザード。デフォルト/既存値の利用、シークレット項目のマスク表示、保存確認を実装。
- Paper Trading 向け検証レポートツールを追加（src/kabusys/tools/paper_verification_report.py）。
  - ペーパートレード DB を解析して稼働率、注文成功率、送信率、レイテンシ（P95 など）を出力し、PASS/FAIL 判定を行う。
  - CLI 引数 --from/--to/--db に対応。
- ポートフォリオ構築 / リスク調整 / ポジションサイジング機能を追加（src/kabusys/portfolio/*）。
  - 銘柄選定（select_candidates）、等重/スコア重み（calc_equal_weights / calc_score_weights）。
  - セクター上限適用（apply_sector_cap）、レジーム乗数（calc_regime_multiplier）。
  - ポジション株数算出ロジック（calc_position_sizes） — risk_based / equal / score 配分、lot_size・コストバッファ・aggregate cap の処理を含む。
- logging ユーティリティを追加（src/kabusys/utils/logging_setup.py）。
  - stdout への StreamHandler と日次ローテーションのファイルハンドラ（TimedRotatingFileHandler）をルートロガーに設定。ログディレクトリ作成失敗時はファイル出力をスキップするなど堅牢化。
- プロセス優先度 / CPU affinity ユーティリティを追加（src/kabusys/utils/process_priority.py）。
  - Windows と POSIX を吸収した優先度設定（high/normal/low）と set_cpu_affinity を実装。権限不足等の例外は警告で無視する。
- research モジュール（factor_research）を追加（src/kabusys/research/factor_research.py）。
  - モメンタム等ファクター算出の骨子（DuckDB 接続を受けて prices_daily/raw_financials を参照する設計）を導入。

### Changed
- .env 自動読み込みの優先順位を明確化（OS 環境 > .env.local > .env）。自動読み込みを無効化する KABUSYS_DISABLE_AUTO_ENV_LOAD を追加（src/kabusys/config.py）。
- ログの既定動作を統一（stdout を用いる、ログレベル解決順の明確化など）（src/kabusys/utils/logging_setup.py）。
- run_monitoring/run_execution 起動時に最初にプロセス優先度を "high" に設定するよう変更。

### Fixed
- .env パーサーの改善（src/kabusys/config.py）
  - export KEY=val 形式のサポート、シングル/ダブルクォート内のバックスラッシュエスケープ処理、インラインコメントの解釈ルールを強化。
  - 無効行のスキップ処理と保護された OS 環境変数を上書きしないオプションを追加。
- ポジションサイジングでのスケールダウンロジックの細かな安全弁（lot 単位での丸め、残余キャッシュによる追加配分、max_per_stock 上限の考慮）を実装（src/kabusys/portfolio/position_sizing.py）。
- process_priority の例外処理を強化し、未対応 OS の場合は警告を出してスキップするように修正（src/kabusys/utils/process_priority.py）。
- logging_setup においてログディレクトリ作成失敗時に適切な警告出力とファイルハンドラスキップを行うよう修正。

### Security
- 必須シークレットは Settings 経由で取得し、未設定時は ValueError を発生させる（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD）（src/kabusys/config.py）。

## [0.1.0] - 2026-04-19

初回公開リリース（推定） — 上記の機能群をパッケージ化。

### Added
- パッケージ初期バージョン。以下を含む主要コンポーネントを実装:
  - 起動スクリプト: run_execution, run_monitoring
  - 環境管理/ウィザード/検証: config.py, config_setup.py, validate_config.py
  - ロギング・プロセス管理ユーティリティ: utils/logging_setup.py, utils/process_priority.py
  - ポートフォリオ構築ライブラリ: portfolio/*
  - Paper Trading 検証ツール: tools/paper_verification_report.py
  - 研究用ファクターモジュール: research/factor_research.py

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

---

注意事項・補足
- run_monitoring は「監視用途の SQLite（monitoring.db）を本番設定にかかわらず使用する」仕様がソース中に明示されています。運用時はデータ分離の方針に注意してください。
- run_execution は KABUSYS_ENV によって paper_trading 用 DB を切り替える設計です（PAPER_TRADING_SQLITE_PATH 環境変数で上書き可能）。
- .env の読み込み / パース挙動は実装の細部（クォート、コメント、エクスポート形式）に依存するため、.env の作成には config_setup を利用することを推奨します。

（以上）