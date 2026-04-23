# CHANGELOG

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠しています。  

- リリースの重要度は慣習に従い Added / Changed / Fixed / Deprecated / Removed / Security に分類しています。
- 日付・内容はソースコードの実装・コメントから推測して作成しています。

## [Unreleased]

### Added
- 起動スクリプトを追加 / 整備
  - run_execution.py: ExecutionEngine 起動スクリプトを提供。KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使い、paper_trading 用 DB（data/paper_trading.db）に記録する。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを提供。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は環境に関係なく本番 sqlite_path を使用する旨を明示。
- 設定関連ユーティリティ
  - config.py: 環境変数読み込みと Settings クラスを導入。.env ファイル自動ロード（.env, .env.local）を行い、KABUSYS_DISABLE_AUTO_ENV_LOAD により無効化可能。クォートや export プレフィックス、インラインコメントを考慮した .env パーサを実装。
  - config_setup.py: 対話式 .env 作成ウィザードを追加。デフォルトや選択肢、シークレット入力、保存前確認をサポート。
  - validate_config.py: 起動前検証 CLI を追加。必須環境変数やパス、config/*.yaml の存在や YAML パースを検査。--strict オプションで警告を FAIL 扱いにできる。
- ポートフォリオ構築関連（純粋関数群）
  - portfolio/portfolio_builder.py: 候補選定（select_candidates）、等分配（calc_equal_weights）、スコア加重（calc_score_weights）を実装。スコアが全て 0 の場合は等分配にフォールバックして警告を出す。
  - portfolio/risk_adjustment.py: セクター集中制限を行う apply_sector_cap、マーケットレジームに応じた投下資金乗数を返す calc_regime_multiplier を実装（regime によるマップとフォールバック動作を含む）。
  - portfolio/position_sizing.py: 株数算出ロジックを実装。allocation_method として "risk_based" / "equal" / "score" をサポートし、単元株丸め（lot_size）、1銘柄上限（max_position_pct）、全体の aggregate cap、および cost_buffer を考慮したスケーリングロジックを備える。
  - portfolio パッケージの __init__ によるエクスポートを整備。
- ユーティリティ
  - utils/logging_setup.py: 統一的なロギング設定ユーティリティを追加。stdout への StreamHandler と日次ローテーションのファイルハンドラ（TimedRotatingFileHandler）をルートロガーに設定。既存ハンドラのクリア、ログディレクトリ作成失敗時のフォールバック、LOG_LEVEL / LOG_DIR の解決ルールを実装。
  - utils/process_priority.py: クロスプラットフォームなプロセス優先度設定（および set_cpu_affinity）を実装。Windows と POSIX の差分を吸収し、psutil の制約や権限不足を警告してスキップする安全設計。
- ツール
  - tools/paper_verification_report.py: Paper Trading 用検証レポート生成スクリプトを追加。稼働率・注文成功率・送信率・レイテンシ（P95）等を集計し、PASS/FAIL 判定を出力する。CLI 引数 (--from / --to / --db) をサポート。
- 監視 DB 初期化
  - monitoring.monitoring_db の初期化呼び出しを run_execution/run_monitoring から行い、監視テーブルの存在を起動時に保証（冪等に初期化する意図）。

### Changed
- 起動時のプロセス優先度を default で "high" に設定するように全起動スクリプトで呼び出すようにした（set_process_priority を利用）。
- run_execution と run_monitoring で SQLite / DuckDB の接続を明示的に確立し、終了時に確実にクローズされるよう構成。
- .env の自動読込順序を OS 環境 > .env.local > .env に明確化し、OS 環境変数を保護するための protected 動作を実装。
- logging_setup で既に設定されているハンドラを一度 flush / close してから削除することで、複数回のセットアップによる二重出力を防止。

### Fixed
- MONITOR_POLL_INTERVAL のパースと検証を強化。非整数または 0 以下の値が指定された場合にデフォルト 60 秒へフォールバックし、警告を出す。
- .env 読み込みの堅牢化：
  - export プレフィックス、シングル/ダブルクォート内のバックスラッシュエスケープ、行内コメントの扱いなどをサポート。
  - ファイル読み込み失敗時に警告を発し処理を継続。
- process_priority / set_cpu_affinity 周りで権限不足や未実装プラットフォームでも安全にスキップするよう例外処理を追加。
- position_sizing の aggregate cap スケーリングで残余資金を使って端数の lot 単位を再配分するロジックを導入し、より保守的かつ再現性のある配分を実現。

### Documentation / Developer experience
- モジュールおよび関数に日本語の docstring を充実させ、設計意図や使用上の注意（例: データ参照の制約、フォールバック動作、将来の TODO）を明記。
- validate_config と config_setup により初期セットアップ・検証プロセスを整備し、運用上のミスを減らす支援を追加。

## [0.1.0] - 2026-04-11

(This is the initial inferred release based on the current codebase.)

### Added
- プロジェクト初期実装を追加:
  - コアモジュール: config, settings (Settings クラスと settings インスタンス)
  - 起動スクリプト: run_execution, run_monitoring
  - ポートフォリオ関連: portfolio_builder, risk_adjustment, position_sizing
  - 監視関連: monitoring DB 初期化フック（init_monitoring_db の呼び出し箇所）
  - ユーティリティ: logging_setup, process_priority
  - 開発・運用支援ツール: config_setup (対話ウィザード), validate_config (起動前検証), tools/paper_verification_report
  - research/factor_research の下地（モメンタム等の計算ロジックの開始。注: ファイルは途中まで実装）

### Changed
- パッケージメタ: __version__ を設定 (0.1.0)。
- ログ出力の統一設定とローテーションを導入。

### Fixed
- N/A（初期リリースのため特別な修正履歴は無し）

---

注記:
- 日付はコード内コメントやツールのサンプル引数（2026-04-01 など）から推測した暫定値です。正確なリリース日や履歴は実際のリポジトリのコミット履歴に基づいて更新してください。
- この CHANGELOG はコードの構成・コメントから推測して作成したものです。実際の変更履歴（コミットや PR の一覧）と照合して必要に応じて調整してください。