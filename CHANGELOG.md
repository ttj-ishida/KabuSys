# Changelog

すべての注記は Keep a Changelog 準拠の形式で記載しています。  
バージョン番号はパッケージの __version__ (0.1.0) に合わせています。

## [0.1.0] - 2026-04-23

### Added
- 全体
  - 初期リリース。KabuSys のコアモジュール・CLI・ユーティリティ群を追加。
  - 環境変数の自動読み込み機能を実装（プロジェクトルートの .env / .env.local をロード）。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - Settings クラスを追加し、環境変数から各種設定値を安全に取得する仕組みを提供（必須チェック、型変換、検証ロジックなど）。
  - .env の対話式ウィザード（config_setup）を追加。.env の初期作成・更新を支援。
  - 設定検証 CLI（validate_config）を追加。必須環境変数、KABUSYS_ENV、ログレベル、DB パス、config/*.yaml の存在とパース（PyYAML があれば内容検証）をチェック。--strict オプションで警告を FAIL 扱いにできる。

- 実行 / 監視ランナー
  - run_execution: ExecutionEngine 起動スクリプトを追加。
    - 起動時にプロセス優先度を "high" に設定。
    - KABUSYS_ENV=paper_trading 時は paper_trading 専用 SQLite（data/paper_trading.db、環境変数で上書き可）を使用して本番 DB と分離。
    - BrokerClientFactory を介したブローカークライアント作成、OrderRepository/OrderManager/RiskManager/Reconciler を組み立てて ExecutionEngine を起動。
    - 停止用フラグファイル (data/stop_requested.flag) による安全停止対応、起動時の停止フラグ検出で起動を抑止。
  - run_monitoring: SystemMonitor ポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒、無効値は警告してフォールバック）。
    - 監視用コードは環境にかかわらず本番 sqlite_path を参照して監視データを記録（意図的に本番の監視対象を使用する設計）。
    - stop_requested.flag の検出で監視ループを終了。

- ロギング / プロセス・管理ユーティリティ
  - logging_setup: 統一的なログ設定ユーティリティを追加。
    - コンソール出力は stdout（StreamHandler）を使用。
    - 日次ローテーションのファイルハンドラ（TimedRotatingFileHandler）をデフォルト logs/ に作成。LOG_DIR 環境変数で上書き可能。
    - 既存ハンドラをクリアして二重出力を防止。
  - process_priority: プラットフォーム差異を吸収したプロセス優先度設定ユーティリティを追加。
    - Windows / POSIX（Linux, macOS, FreeBSD）をサポート。nice 値や Windows の優先度定数を適用。
    - CPU affinity 設定用関数 set_cpu_affinity も提供。
    - 権限不足等で失敗した場合は警告ログを出して安全にスキップ。

- ポートフォリオ構築（純粋関数群）
  - portfolio.portfolio_builder
    - select_candidates: BUY シグナルのスコア降順選抜。
    - calc_equal_weights / calc_score_weights: 等金額配分 / スコア加重配分（スコアが全て 0 の場合は等金額配分にフォールバックし警告）。
  - portfolio.risk_adjustment
    - apply_sector_cap: セクター集中の上限チェックと候補除外（"unknown" セクターは上限除外対象外）。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた資金乗数（未知のレジームは警告して 1.0 にフォールバック）。
  - portfolio.position_sizing
    - calc_position_sizes: 発注株数計算（allocation_method: "risk_based" / "equal" / "score" をサポート）。
    - 単元株（lot_size）丸め、1銘柄上限、aggregate cap（available_cash 超過時のスケールダウン）を考慮。cost_buffer により手数料等を保守的に見積もる。

- 研究・指標計算（research）
  - research.factor_research の骨格を追加（DuckDB 接続を受け取り prices_daily / raw_financials を参照して各種ファクターを計算する方針）。（実装は一部で続く）

- ツール
  - tools.paper_verification_report: Paper Trading 向け検証レポート出力ツールを追加。
    - PAPER_TRADING_SQLITE_PATH（または --db）で指定した SQLite を読み、稼働率 / 注文成功率 / 送信率 / レイテンシなどを集計して PASS/FAIL を判定する。デフォルト基準値や P95 計算ロジックを含む。

### Changed
- 環境読み込みの挙動
  - .env の読み込みは OS 環境変数を保護（既存の OS 環境変数は上書きされない）。.env.local は .env の上書きとして扱う。
  - .env 行パーサは export プレフィックス、クォートやエスケープ、インラインコメント（一定ルール）に対応するよう強化。

- ログ出力
  - コンソール出力を stderr ではなく stdout に送るように変更（Task Scheduler / cron 等で stdout/stderr を統一して扱いやすくするため）。

### Fixed
- （該当なし: 初期リリース）

### Deprecated
- （該当なし）

### Removed
- （該当なし）

### Security
- （該当なし）

---

注記:
- 本リリースはコードベースから推測して記載した CHANGELOG です。実際のリリース文書に含めたい追加情報（既知の制約、互換性の詳細、マイグレーション手順など）があれば指示ください。