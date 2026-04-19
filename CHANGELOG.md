CHANGELOG
=========

すべての重要な変更はこのファイルに記録します。
フォーマットは「Keep a Changelog」準拠です。
ソースツリーの内容から推測して作成しています（実装・挙動の要約）。

Unreleased
----------

### Added
- 起動スクリプトを追加 / 整備
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。KABUSYS_ENV に応じて paper_trading 用の専用 SQLite を使用する（デフォルト: data/paper_trading.db）。起動時にプロセス優先度を設定し、stop フラグ / pid ファイルの取り扱いを行う。
  - run_monitoring.py: SystemMonitor のポーリングループを起動するスクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視用 DB は環境に依らず本番 sqlite_path を使用する。

- 設定・環境変数周りのユーティリティ追加
  - config.py: .env 自動ロード機能を実装（.env, .env.local の読み込み順; OS 環境変数優先）。.env のパースはクォート、export プレフィックス、インラインコメント等に対応。Settings クラスを導入し、各種設定（DB パス、ログレベル、環境種別、Paper Trading 用設定等）をプロパティ経由で取得。値検証（有効な KABUSYS_ENV / LOG_LEVEL / PAPER_FILL_MODE 等）を実施。
  - config_setup.py: .env を対話式に生成・更新するウィザードを追加。秘密値はマスク表示、保存フォーマットを整備。
  - validate_config.py: 起動前に .env と config/*.yaml を検査する CLI を追加。必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL 検証、DB パスや YAML ファイルの存在・パース検査、KABUSYS_ENV=live 時の追加警告等を実施。--strict オプションで警告を失敗扱いにできる。

- ポートフォリオ構築関連モジュール追加
  - portfolio/portfolio_builder.py: 候補選定 (select_candidates)、等配分 (calc_equal_weights)、スコア加重配分 (calc_score_weights)。
  - portfolio/risk_adjustment.py: セクター集中制限の適用 (apply_sector_cap)、市場レジームに応じた投下資金乗数 (calc_regime_multiplier)。
  - portfolio/position_sizing.py: 各銘柄の発注株数計算ロジック (calc_position_sizes)。リスクベース算出、等配分/スコア配分、単元（lot）丸め、aggregate cap に基づくスケーリング、cost_buffer の考慮等を実装。
  - portfolio/__init__.py にエクスポートをまとめる。

- ユーティリティ
  - utils/logging_setup.py: ルートロガーの統一設定ユーティリティを追加。stdout への StreamHandler と日次ローテートのファイルハンドラ（TimedRotatingFileHandler）を設定。ログディレクトリやログレベルの解決ルールを定義し、ディレクトリ作成失敗時はファイル出力をスキップして stdout のみで継続する。
  - utils/process_priority.py: プロセス優先度（high/normal/low）と CPU affinity 設定ユーティリティを追加。Windows と POSIX 系を抽象化し psutil を利用。権限不足等で失敗しても警告を出してスキップする実装。

- Paper Trading 検証ツール
  - tools/paper_verification_report.py: Paper Trading 用 SQLite（デフォルト data/paper_trading.db）から統計を集計して検証レポートを出力する CLI を追加。稼働率、注文成功率（fill）、送信率（send）、P95 レイテンシなどを算出し、閾値（デフォルト値）に基づいて PASS/FAIL を判定。日付フィルタ（--from/--to）や DB パス指定をサポート。

- 研究用モジュール（部分実装）
  - research/factor_research.py: DuckDB の prices_daily/raw_financials を用いたファクター計算用モジュールの骨組みを追加（モメンタム、MA、ATR、出来高等の指標を計算する方針を実装）。（ファイル末尾に未完了の部分あり）

### Changed
- DB/環境分離の強化
  - 実行エンジンは paper_trading モード時に本番監視 DB と分離された paper_trading 用 SQLite を使用するよう明示的に実装（設定プロパティ paper_sqlite_path）。
  - 監視（run_monitoring）は環境にかかわらず監視用 sqlite_path（本番監視 DB）を使用する旨を明文化。

- ログ出力の標準化
  - 各起動スクリプトは setup_logging を呼び出してログ出力を統一。ログディレクトリの生成失敗時も安全にフォールバックする。

- 起動時のプロセス優先度設定
  - run_execution/run_monitoring は起動時に set_process_priority("high") を呼び出すようにし、重要プロセスの優先度を上げる。

### Fixed
- 環境変数パースの堅牢化
  - .env の parser はクォート内のバックスラッシュエスケープやインラインコメントの取り扱い、export プレフィックスの許容などに対応して不正なパースを防止。

- ポジション算出の安全弁
  - calc_position_sizes では price が欠損・0 の場合にログを出してスキップし、aggregate cap のスケーリング処理で lot_size 単位の端数処理を安定して行うよう改善。

### Security
- .env の取り扱いに関する注意喚起を config_setup で明示（.env を絶対に Git にコミットしない旨のヘッダを出力）。

0.1.0 - 2026-04-19
------------------
初期リリース（ソースから推測）

### Added
- 基本機能群（自動売買システムのコア/ユーティリティ）
  - 起動スクリプト: run_execution, run_monitoring
  - 設定管理: config.py（Settings）、自動 .env 読込
  - 対話式セットアップ: config_setup.py（.env ウィザード）
  - 設定検証: validate_config.py（CLI, --strict）
  - ロギングユーティリティ: utils/logging_setup.py
  - プロセス制御ユーティリティ: utils/process_priority.py
  - ポートフォリオ構築: portfolio モジュール（候補選定、重み付け、ポジションサイズ計算、セクターキャップ、レジーム乗数）
  - Paper Trading 検証ツール: tools/paper_verification_report.py
  - 研究用ファクター計算の骨組み: research/factor_research.py

### Changed / Fixed
- 起動・監視の運用面整備（stop フラグ、pid ファイル、優先度設定、ログローテーション）
- .env パースの堅牢化、PAPER_FILL_MODE 等設定値の検証ロジックを実装
- Paper Trading と本番 DB を明確に分離

Notes
-----
- ここに記載した変更・振る舞いは、提供されたソースコードの内容から推測してまとめたものです。実際の振る舞い・パラメータは実行環境や追加の実装（未掲載のモジュール）に依存します。
- 将来的な変更や bugfix は Unreleased に追記してください。