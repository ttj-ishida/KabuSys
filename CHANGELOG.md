# Changelog

すべての変更は [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) の形式に準拠しています。  
このプロジェクトはセマンティックバージョニングを採用しています。

## [Unreleased]

## [0.1.0] - 2026-04-18
初回リリース。

### Added
- 基本アプリケーション骨格を追加。
  - パッケージバージョン: `kabusys.__version__ = "0.1.0"`。
- 環境変数 / 設定管理
  - .env 自動ロード機能（プロジェクトルートを .git または pyproject.toml から検出）を実装。
  - .env/.env.local の読み込みロジック（上書き制御、OS環境変数保護）。
  - .env 行パーサー（`export KEY=...`、クォートとエスケープ対応、インラインコメント処理）。
  - Settings クラスを提供（J-Quants / kabu API / DB パス / 各種監視閾値 / 環境判定等のプロパティ）。
    - PAPER_FILL_MODE の検証（有効値: "instant" / "partial" / "never" / "reject"）。
    - DB パス、PID/kill flag パス、閾値、ログレベル、環境種別判定等をプロパティで提供。
- 設定関連 CLI / ウィザード
  - 対話式環境設定ウィザード: `python -m kabusys.config_setup`（.env の初期作成・更新を支援）。
  - 設定検証 CLI: `python -m kabusys.validate_config`（必須環境変数 / config YAML / パスの検査、`--strict` オプション）。
- 実行系ランナー
  - 実行エンジン起動スクリプト: `src/kabusys/run_execution.py`
    - KABUSYS_ENV が `paper_trading` の場合は paper_trading 専用 SQLite（デフォルト: `data/paper_trading.db`）を使用し、本番 DB と完全分離。
    - BrokerClientFactory によるブローカークライアント生成を想定（Mock の利用を含む）。
    - ExecutionEngine 起動（スレッドで実行）、停止フラグ監視（`data/stop_requested.flag`）、PID ファイル指定機能。
    - RiskManager / OrderManager / Reconciler 等の組み立て処理を追加（初期設定値を含む）。
  - 監視ループ起動スクリプト: `src/kabusys/run_monitoring.py`
    - SystemMonitor の初期化とポーリングループ（デフォルト間隔 60 秒）。
    - 環境変数 `MONITOR_POLL_INTERVAL` によるポーリング間隔上書き（不正値はデフォルトにフォールバック）。
    - 監視は KABUSYS_ENV にかかわらず本番の sqlite_path を使用する設計。
    - 停止フラグファイル検知で安全にループ終了。
- モニタリング DB 初期化ユーティリティ（monitoring テーブルの冪等な作成を保証）。
- ポートフォリオ構築（純関数群）
  - `kabusys.portfolio.portfolio_builder`
    - select_candidates（スコア降順選抜）、calc_equal_weights、calc_score_weights（全スコアが 0 の場合は等配分にフォールバック）。
  - `kabusys.portfolio.risk_adjustment`
    - apply_sector_cap（セクター集中制限の適用、既存ポジションのセクター別エクスポージャ計算）、calc_regime_multiplier（レジームに応じた投入資金乗数）。
  - `kabusys.portfolio.position_sizing`
    - calc_position_sizes（複数配分方式: `risk_based`, `equal`, `score`。単元株丸め、1銘柄上限、aggregate cap によるスケーリング、cost_buffer を考慮した保守的見積り、残差処理による lot 単位の追加配分）。
- ユーティリティ
  - ログ設定ユーティリティ `kabusys.utils.logging_setup.setup_logging`
    - stdout ストリームハンドラと日次ローテートするファイルハンドラ（TimedRotatingFileHandler）をルートロガーに設定。
    - LOG_DIR / LOG_LEVEL の優先解決、ディレクトリ作成失敗時のフォールバック（コンソール出力のみ）。
  - プロセス優先度 / CPU affinity ユーティリティ `kabusys.utils.process_priority`
    - Windows / POSIX を吸収してプロセス優先度を "high"/"normal"/"low" で設定（権限不足時は警告）。
    - CPU affinity 固定機能（最初の N コアに固定）。
- Paper Trading 検証ツール
  - `kabusys.tools.paper_verification_report`：ペーパートレード DB（デフォルト: `data/paper_trading.db`）から指標（稼働率・注文成功率・送信率・レイテンシ等）を集計してレポート出力。閾値に基づく PASS/FAIL 判定を実装。
    - レポート生成時に P95 レイテンシ計算、Null 値ハンドリング、日付フィルタ（--from/--to）。
- リサーチ
  - `kabusys.research.factor_research`（ファクター計算モジュール）を追加。Momentum / Value / Volatility / Liquidity などの方針・定数を定義。（モジュールはファイル途中まで実装）

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Removed
- （初回リリースのため該当なし）

### Notes / Security
- .env は絶対にリポジトリにコミットしない旨を明示（config_setup の生成ヘッダに記載）。
- 本番運用時の注意点:
  - KABUSYS_ENV=live の場合は追加の警告チェックが行われる（LINE 通知設定、KILL_FLAG_CLEAR_ON_START の確認など）。
  - 監視プロセスは本番用 sqlite_path を常に参照する設計のため、環境に応じた DB 分離が必要な箇所（実行エンジンの paper_trading 分離とは異なる）に注意。

---

開発・運用に関する補足や既知の制約はドキュメントやコード内コメントに記載しています。追加の変更履歴や差分があればこの CHANGELOG を更新してください。