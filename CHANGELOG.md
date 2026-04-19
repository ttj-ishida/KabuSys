# CHANGELOG

すべての変更は Keep a Changelog の形式に従っています。  
慣例: 追加 (Added), 変更 (Changed), 修正 (Fixed), 非推奨 (Deprecated), 削除 (Removed)、セキュリティ (Security)。

<!-- 参照: Keep a Changelog (https://keepachangelog.com/ja/1.0.0/) -->

## [Unreleased]
- 小さな改善・ドキュメント補足など（次回リリースにまとめます）。

## [0.1.0] - 2026-04-19
最初の公開リリース。自動売買システム KabuSys のコア機能群を実装。

### Added
- 基本設定・環境読み込み
  - .env 自動ロード機能を実装（プロジェクトルートの検出: .git または pyproject.toml）。環境変数の読み込み優先順位は OS 環境変数 > .env.local > .env。自動ロードは `KABUSYS_DISABLE_AUTO_ENV_LOAD` で無効化可能。
  - .env ファイルのパース機能を強化（export プレフィックス、シングル/ダブルクォート、インラインコメント、エスケープ処理に対応）。
  - Settings クラスを実装し、各種設定値（J-Quants / kabu API / DB パス / Paper Trading 設定 / 監視閾値 / 実行環境フラグ等）をプロパティ経由で取得できるようにした。環境変数の妥当性チェック（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE 等）を内蔵。

- 起動スクリプト
  - run_execution: ExecutionEngine 起動用スクリプトを追加。
    - `KABUSYS_ENV=paper_trading` 時は paper_trading 専用の SQLite（デフォルト: data/paper_trading.db）を使用し、本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler 組み立て、ExecutionEngine の起動・停止制御（stop flag / PID ファイルの利用）を実装。
    - デフォルトでプロセス優先度を "high" に設定。
  - run_monitoring: SystemMonitor ポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒、無効値は警告してデフォルトにフォールバック）。
    - 監視 DB 初期化（init_monitoring_db）、duckdb 接続、SystemMonitor の単回チェック実行ループ、停止フラグの検出処理を実装。
    - Monitoring は環境にかかわらず本番の sqlite_path を参照する設計。

- ロギング・プロセス管理ユーティリティ
  - logging_setup: 統一的なロギング設定ユーティリティを追加。
    - stdout へ出力する StreamHandler と、日次ローテーションする TimedRotatingFileHandler（既定 logs/ ディレクトリ、30 日分保持）をルートロガーに設定。
    - 既存ハンドラのクリアやログディレクトリ作成失敗時のフォールバック動作を実装。
  - process_priority: プロセス優先度（Windows / POSIX）や CPU affinity 設定ユーティリティを追加。
    - Windows の優先度クラスや POSIX の nice 値を環境に合わせて設定。失敗時は警告してスキップ。

- 設定支援・検証ツール
  - config_setup: 対話式 .env 作成ウィザードを追加。主要な環境変数を対話的に入力・保存可能。
  - validate_config: 起動前検証 CLI を追加。必須環境変数のチェック、KABUSYS_ENV / LOG_LEVEL の妥当性、DB パスや config/*.yaml の存在（および PyYAML があればパース検証）、本番時のガード（LINE 通知・KILL_FLAG_CLEAR_ON_START など）を行う。`--strict` で警告を失敗扱いにできる。

- Portfolio モジュール（純粋関数群）
  - portfolio_builder:
    - 候補選定 (select_candidates) — スコア降順かつタイブレークで signal_rank を使用。
    - 等金額配分 (calc_equal_weights) / スコア加重配分 (calc_score_weights) を実装。全スコアが 0 の場合は等金額配分にフォールバックして警告を出す。
  - risk_adjustment:
    - apply_sector_cap: セクター集中制限ロジックを実装（既存保有のセクター別露出を計算し、閾値超過セクターの新規候補を除外）。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数を返す。未知レジームはフォールバックで 1.0。
  - position_sizing:
    - calc_position_sizes: allocation_method（risk_based / equal / score）に基づく発注株数決定ロジックを実装。
    - lot_size（単元）での丸め、per-position 上限、aggregate cap（利用可能現金を超える場合のスケーリング）や cost_buffer を用いた保守的見積り、残差処理（fractional remainder による追加配分）などを実装。

- ツール類
  - tools/paper_verification_report: Paper Trading の検証レポート生成スクリプトを追加。
    - システム稼働率、注文成功率（fill_rate）、送信率（send_rate）、リスク却下数、API レイテンシ（avg/max/P95）を計算・出力。
    - P95 の算出、期間フィルタリング、閾値判定（稼働率 >= 99%、fill_rate >= 90% など）を提供。
    - DB パスはコマンドライン引数または環境変数（PAPER_TRADING_SQLITE_PATH）で指定可能。

- データ分析準備
  - research/factor_research: ファクター計算モジュールの骨組みを追加（モメンタム / MA / ATR / 出来高等の定数定義と calc_momentum のインターフェース設計）。DuckDB 接続を受け取り prices_daily / raw_financials を参照して計算する設計。

- パッケージメタ
  - パッケージ初期化: __version__ = "0.1.0" を設定。主要サブパッケージを __all__ でエクスポート。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- 環境変数内のシークレット表示はウィザード・確認画面でマスク表示（****）。

### Notes / Implementation Details
- DB 周り:
  - 監視用テーブル確保のため init_monitoring_db を各起動スクリプトで呼び出し、冪等に初期化することを想定。
  - DuckDB は分析用に利用（duckdb_path）。
- 実行制御:
  - 停止フラグファイル（data/stop_requested.flag 等）や PID ファイルで外部からプロセス制御できる設計。
- エラーハンドリング:
  - モニターループや ExecutionEngine スレッド監視で、例外発生時にログ出力しループ継続する堅牢性を確保。
- ログ:
  - ログディレクトリ作成に失敗した場合はファイルロギングをスキップしてコンソール出力のみ継続するフォールバックを採用。

---

今後の予定（例）
- factor_research の完全実装（Momentum / Value / Volatility / Liquidity の SQL 実装）。
- Strategy/Execution の統合テスト、具体的な BrokerClient 実装（本番接続）と Mock の充実。
- 単体テストの追加・CI 統合、パッケージ化・リリースプロセス整備。

（この CHANGELOG はコードベースの内容から推測して作成しています。実際のリリース記録と差異がある場合は適宜調整してください。）