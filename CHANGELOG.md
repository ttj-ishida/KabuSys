# CHANGELOG

すべての変更は Keep a Changelog の形式に準拠して記載しています。  
日付は本ファイル生成日です（2026-04-18）。

## [0.1.0] - 2026-04-18

### Added
- 起動スクリプトを追加／実装
  - run_execution.py：ExecutionEngine 起動スクリプトを実装。KABUSYS_ENV に応じて paper_trading 用 DB を分離して使用する（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）。起動時にプロセス優先度を High に設定し、停止フラグ（data/stop_requested.flag）で安全に停止可能。エンジンはデーモンスレッドで実行され、停止検知で engine.stop() を呼び出す。
  - run_monitoring.py：SystemMonitor ポーリングループ起動スクリプトを実装。MONITOR_POLL_INTERVAL 環境変数によるポーリング間隔の上書きをサポート（デフォルト: 60 秒）。監視は環境に依らず production の sqlite_path を使用。停止フラグ検出と例外ハンドリングを含む。

- 環境設定・検証ツール
  - config_setup.py：対話式 .env ウィザードを実装。代表的な環境変数項目を並べ、既存 .env を読み込み・更新して .env を書き出す機能を提供。
  - validate_config.py：起動前に .env と config/*.yaml の設定を検証する CLI を実装。必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性、DB パスの親ディレクトリ存在チェック、YAML パースチェック（PyYAML 利用可の場合）などを行い、errors/warnings/infos を出力。--strict オプションで警告を失敗扱いにできる。

- 設定管理
  - config.py：.env の自動読み込みロジックを実装（プロジェクトルート検出、.env/.env.local の読み込み順）。.env パースは export プレフィックス、クォート、エスケープ、インラインコメントの取り扱いに対応。Settings クラスを提供し、各種環境変数をプロパティ経由で取得（値検証・デフォルト設定を含む）。PAPER_FILL_MODE の有効値検証、KABUSYS_ENV/LOG_LEVEL の検証、paper_sqlite_path などを実装。自動読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。

- ロギング・プロセス優先度ユーティリティ
  - utils/logging_setup.py：統一的なログ設定ユーティリティを実装。stdout へ StreamHandler、ファイルへ TimedRotatingFileHandler（日次・30 日保持）をルートロガーに設定。LOG_LEVEL / LOG_DIR の解決順や、ログディレクトリ作成失敗時のフォールバック（ファイル出力無効化）を考慮。
  - utils/process_priority.py：プラットフォーム非依存のプロセス優先度設定ユーティリティ（set_process_priority）および CPU affinity 設定（set_cpu_affinity）を実装。Windows と POSIX の差分を吸収し、例外発生時は警告を出してスキップする。

- ポートフォリオ構築・リスク調整・サイズ計算
  - portfolio/portfolio_builder.py：候補選定（select_candidates）、等配分（calc_equal_weights）、スコア加重（calc_score_weights）を実装。スコアが全て 0 の場合は等配分へフォールバック。
  - portfolio/risk_adjustment.py：セクター集中制限の適用（apply_sector_cap）、市場レジームに応じた投下資金乗数の算出（calc_regime_multiplier）を実装。unknown セクターの扱いやレジーム不明時のフォールバックを明示。
  - portfolio/position_sizing.py：複数の配分方式（risk_based / equal / score）に基づく発注株数算出ロジックを実装。単元株（lot_size）丸め、per-position / aggregate cap、cost_buffer による保守的見積り、スケールダウンと残差処理（fractional remainder に基づく追加配分）を含む。

- Paper Trading 検証ツール
  - tools/paper_verification_report.py：ペーパートレード用の検証レポート生成スクリプトを実装。システム稼働率、注文成功率（Filled/Created）、送信率（Sent/Created）、リスク却下数、レイテンシ（avg/max/P95）などを集計し、PASS/FAIL 判定（しきい値はソース内定義）を行う。DB が存在しない場合やテーブル欠如時のフォールバック処理を実装。P95 計算ロジックを提供。

- research/factor_research.py：DuckDB 上で動作するファクター計算モジュール（モメンタム／MA200乖離／ATR 等）をベースにした実装の開始。API の設計方針やスキャン期間定義を含む（calc_momentum を含むが実装途中の断片あり）。

- パッケージメタ情報
  - __init__.py にてパッケージバージョン __version__ = "0.1.0" を設定。

### Changed
- 全体設計の意図・動作を明確化するため、各モジュールに詳細な docstring/注釈を追加（起動スクリプトの挙動、環境依存仕様、各アルゴリズムのフォールバック方針等）。
- ログ設定は stdout を採用（cron/Task Scheduler におけるリダイレクト想定）し、既存ハンドラのクリーンアップ処理を追加。

### Fixed
- .env パーサーの改善（config._parse_env_line）
  - export プレフィックス対応、クォートされた値のエスケープ処理、インラインコメントの取り扱い、無効行のスキップ等を正しく処理するよう強化。
- process_priority と CPU affinity の例外処理を堅牢化：アクセス権不足や未サポート環境でも起動を継続できるよう警告でフォールバック。

### Security
- .env の書き出しウィザード（config_setup.py）で .env を生成する旨の注意書きを挿入（.env を Git にコミットしないことを明示）。

### Notes / Internal
- ExecutionEngine の RiskManager 初期化で initial_portfolio_value = broker.get_available_cash() を利用する設計になっており、ブローカークライアント実装に依存する。
- run_monitoring と run_execution は sqlite3 / duckdb の接続を確実に close() するよう finally ブロックで閉じる実装。
- config の自動読み込みはプロジェクトルート探索により .env を読み込むため、パッケージ配布後も CWD に依存しない設計。自動読み込みは無効化可能（KABUSYS_DISABLE_AUTO_ENV_LOAD）。
- research/factor_research.py はファクター計算の方針と一部関数を含むが、実装は継続中（calc_momentum の途中でソース断片が存在）。

---

変更点はコードから推測した実装・設計意図に基づき記載しています。必要であれば、各変更項目に対応するファイル・関数名や具体的なコード行の抜粋を追加して詳細化できます。どの程度の粒度で CHANGELOG を整備するかご指定ください。