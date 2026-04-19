# Changelog

すべての重要な変更点をこのファイルに記載します。フォーマットは「Keep a Changelog」に準拠し、セマンティックバージョニングを採用しています。

配布バージョン:
- 現在のパッケージバージョン: 0.1.0 (src/kabusys/__init__.py)

## [Unreleased]
### Added
- 開発・運用に必要なコマンドライン起動スクリプトを追加
  - run_execution: ExecutionEngine を起動するエントリポイント。プロセス優先度設定、DB接続、Broker クライアント生成、ExecutionEngine の起動/停止ループを実装。
  - run_monitoring: SystemMonitor のポーリングループ起動スクリプト。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能。
- 環境設定関連のユーティリティを追加
  - config: .env 自動読み込み（.env / .env.local）、プロジェクトルート探索、環境変数パースロジック、Settings クラス（環境変数をプロパティ経由で取得、型変換・バリデーションを実施）。
  - config_setup: 対話式ウィザードで .env を初期作成 / 更新する CLI。既存値の読み込み・シークレット表示・保存をサポート。
  - validate_config: 起動前の設定検証 CLI。.env と config/*.yaml の基本チェック、--strict オプションで警告を失敗扱いにできる。
- ロギング・プロセス制御ユーティリティを追加
  - utils/logging_setup: stdout StreamHandler と 日次ローテーションの TimedRotatingFileHandler をルートロガーに設定する共通ユーティリティ。LOG_DIR/LOG_LEVEL の解決、既存ハンドラのクリアなどを実装。
  - utils/process_priority: Windows / POSIX を吸収するプロセス優先度設定、CPU affinity 設定ユーティリティ。権限不足などの失敗は警告でスキップ。
- ポートフォリオ構築・ポジション決定ロジック（純粋関数群）
  - portfolio/portfolio_builder: シグナルの選別 (select_candidates)、等金額配分 (calc_equal_weights)、スコア加重配分 (calc_score_weights) を実装。
  - portfolio/risk_adjustment: セクター上限適用 (apply_sector_cap)、市場レジームに応じた投下資金乗数 (calc_regime_multiplier) を実装。
  - portfolio/position_sizing: 各種配分方式（risk_based / equal / score）に基づく発注株数計算、単元株丸め、aggregate cap によるスケーリング、cost_buffer による保守的見積りを実装。
- Paper Trading 検証用ツール
  - tools/paper_verification_report: Paper Trading 用 SQLite (data/paper_trading.db 想定) を読み、稼働率・注文成功率・送信率・レイテンシ (平均/最大/P95) などを集計して PASS/FAIL 判定するレポート生成スクリプト。期間指定オプション (--from/--to)、DB パスオーバーライド (--db) をサポート。
- DuckDB / SQLite の運用補助
  - 複数スクリプトで duckdb と sqlite コネクションを利用する設計（run_execution/run_monitoring で両方接続）。
  - 監視テーブル初期化ユーティリティ (monitoring.monitoring_db.init_monitoring_db) を起動時に呼び出して冪等に監視テーブルを準備（モジュール参照箇所あり）。
- 研究・ファクター計算の下地
  - research/factor_research: Momentum 等のファクター計算モジュールの骨組み（DuckDB 接続を受け prices_daily / raw_financials を参照して計算する方針、各種窓長定数を定義）。（実装は一部継続中）

### Changed
- 設定読み込みのデフォルト方針
  - OS 環境変数 > .env.local > .env の優先読み込みを採用。自動読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
- run_execution/run_monitoring の DB 分離方針
  - run_execution は KABUSYS_ENV=paper_trading の場合に paper_sqlite_path（デフォルト data/paper_trading.db）を使用し、本番の monitoring DB と完全に分離する設計。
  - run_monitoring は環境にかかわらず production（settings.sqlite_path）を使用する旨が明示されている（監視は実運用 DB を参照）。

### Fixed
- 環境変数パースの強化
  - export プレフィックス、クォート内のバックスラッシュエスケープ、行内コメント判定（クォート無の '#' は直前がスペース/タブでない限りコメントとしない）などの挙動に対応。
- ロギングディレクトリ作成失敗時のフォールバック
  - ログディレクトリの作成に失敗した場合はファイルハンドラをスキップし、コンソール出力のみで継続するように改善。

---

## [0.1.0] - 2026-04-19
最初の公開リリース。上記「Added / Changed / Fixed」の内容を含む初期版リリース。

### Added
- パッケージ初期公開（KabuSys - 日本株自動売買システム）
- 実行用スクリプト: run_execution, run_monitoring
- 設定管理・ウィザード・検証: config, config_setup, validate_config
- ロギング/プロセス制御ユーティリティ: utils.logging_setup, utils.process_priority
- ポートフォリオ構築: portfolio.*（候補選定、重み計算、リスク制御、ポジションサイズ計算）
- Paper Trading 検証ツール: tools/paper_verification_report
- 研究用: research.factor_research（ファクター計算の基礎）
- その他ユーティリティ・初期の DB 初期化フック

### Changed
- (初期リリースのため該当なし)

### Fixed
- (初期リリースのため該当なし)

---

注意事項 / 既知の制約
- research/factor_research の実装は一部が継続中（ファイル末尾で計算ロジックが途中で切れている可能性あり）。研究用途で利用する際は未完成箇所に注意してください。
- process_priority / set_cpu_affinity は権限やプラットフォーム依存のため、実行環境によっては期待通り動作しない場合があります（失敗時は警告でスキップします）。
- .env ファイルは機密情報を含むため、絶対に VCS にコミットしないでください（config_setup のヘッダにも警告あり）。

もしさらに細かい変更履歴（ファイル単位の差分や開発履歴）を推測して盛り込みたい場合は、追加のコンテキスト（対象とする過去バージョンやコミット要約など）を教えてください。