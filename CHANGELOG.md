CHANGELOG
=========

フォーマットは "Keep a Changelog" に準拠しています。  
主にソースコードから推測できる追加機能、動作、既知の制約や注意点を記載しています。

Unreleased
----------

- なし（現時点ではリリース済みの状態を想定しています）。

0.1.0 - 2026-04-11
------------------

Added
- 基本パッケージとバージョン情報を追加
  - kabusys パッケージ初期リリース（__version__ = "0.1.0"）。
- 実行エントリポイント
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。プロセス優先度設定、Paper Trading 用 DB 分離（PAPER_TRADING_SQLITE_PATH / settings.is_paper）、BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て、スレッドでのエンジン実行と停止フラグ処理、PID ファイル管理を実装。
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数によるポーリング間隔上書き、停止フラグ検出、監視用 SQLite/ DuckDB 接続、例外時のログ保護を実装。監視は環境に関係なく本番用 sqlite_path を使用する仕様。
- 設定関連
  - config.py: 環境変数読み込み・ラッパー（Settings クラス）を実装。自動 .env/.env.local の読み込み（プロジェクトルート検出）、保護された OS 環境変数の扱い、各種設定プロパティ（DB パス、API トークン、Paper Trading 設定、監視閾値等）を実装。PAPER_FILL_MODE の検証、KABUSYS_ENV / LOG_LEVEL の検証を含む。
  - config_setup.py: 対話式 .env 作成/更新ウィザードを実装。既存 .env の読み込み、入力のマスク（秘密値）、検証とファイル書き出しをサポート。
  - validate_config.py: 起動前の設定検証 CLI を追加（必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL/DB パス、config/*.yaml の存在と YAML パース検証等）。--strict オプションで警告をエラー扱いにできる。
- ポートフォリオ構築（Portfolio construction）
  - portfolio/portfolio_builder.py: 候補選定（select_candidates）、等分配（calc_equal_weights）、スコア加重配分（calc_score_weights）を実装。スコア全ゼロ時は等分配へフォールバック。
  - portfolio/risk_adjustment.py: セクター集中上限適用（apply_sector_cap）、市場レジームに応じた投下資金乗数（calc_regime_multiplier）を実装。未知レジームは警告を出して 1.0 でフォールバック。
  - portfolio/position_sizing.py: 発注株数計算（calc_position_sizes）を実装。allocation_method（"risk_based" / "equal" / "score"）の対応、単元株切り捨て、ポジション上限・集計上限（aggregate cap）でのスケーリング、手数料/スリッページ考慮の cost_buffer、lot_size 対応、既存保有考慮を実装。
- ユーティリティ
  - utils/logging_setup.py: 統一的なログ設定ユーティリティを追加。stdout への StreamHandler と日次ローテーションの TimedRotatingFileHandler（logs/<app>.log）を設定。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
  - utils/process_priority.py: クロスプラットフォームのプロセス優先度設定（Windows / POSIX 対応）と CPU affinity 設定ユーティリティを追加。権限不足時は警告を出してスキップ。
- ツール・スクリプト
  - tools/paper_verification_report.py: Paper Trading の検証レポート生成スクリプトを追加。稼働率、注文成功率、送信率、P95 レイテンシなどを集計し PASS/FAIL 判定を行う。DB パスは引数/環境変数で指定可能。
- 分析・リサーチ基盤（初期）
  - research/factor_research.py: ファクター計算の骨子（モメンタム、移動平均、ATR、流動性等）を実装するモジュールを追加（DuckDB 経由で prices_daily/raw_financials を参照する設計）。（注: ファイル末尾に一部実装が途切れているため、完全実装は今後の作業。）
- モニタリング DB 初期化/SystemMonitor との連携を行うためのモジュール参照が追加（init_monitoring_db / SystemMonitor は別モジュールとして使用）。

Changed
- 環境変数読み込みの挙動
  - 自動ロードは OS 環境変数を優先し、.env を既定でロードする一方、KABUSYS_DISABLE_AUTO_ENV_LOAD により無効化可能に。
  - .env 読み込み時に export プレフィックスやクォート、インラインコメントの扱いに対応するパーサを実装し堅牢化。
- ログ設定
  - setup_logging() は既存ハンドラのクリア処理を行い、二重ハンドラ設定を防止。ログレベル・ログディレクトリの解決順序を明確化。

Fixed
- env ファイルパーサの堅牢化により、引用符・エスケープやコメント混在ケースでの誤読を防止。
- run_monitoring.py / run_execution.py で例外発生時にも DB 接続を確実にクローズするよう finally ブロックを使用。

Known issues / Notes
- research/factor_research.py の一部（calc_momentum の先頭以降）は実装途中でファイルが切れているため、ファクター計算の完全実装は未完。今後のリリースで補完予定。
- portfolio/risk_adjustment.apply_sector_cap 内の価格欠損（price が 0.0）の取り扱いに TODO コメントあり。現状だと欠損価格はゼロ換算され、エクスポージャーが過少評価される可能性があるため注意が必要。
- process_priority.set_cpu_affinity / nice の設定は実行環境（権限）に依存し、権限不足や未対応 OS では警告が出て設定はスキップされる。
- run_monitoring は監視データ用 sqlite_path を常に本番パスで開く仕様（環境に依存しない）。テスト環境で分離したい場合は設定やコードの調整が必要。
- Paper Trading（KABUSYS_ENV=paper_trading）は本番 DB と分離して data/paper_trading.db を使用する設計。ただし、Monitoring テーブル初期化は両実行スクリプトで呼んでいるため、環境に応じた DB 運用は運用方針に従ってください。

Security
- .env ファイルは生成時に Git にコミットしないよう注意喚起を .env ヘッダに記載。

Acknowledgements / Notes for maintainers
- 今後の改善候補:
  - research モジュールの完全実装（ファクター計算と正規化パイプライン）。
  - portfolio の lot_size を銘柄ごとに管理する拡張（stocks マスタとの連携）。
  - Monitoring と Execution のより細かい分離（テスト用 DB スイッチなど）。
  - 単体テストの追加（特に position_sizing のスケールダウンロジック、config のパース）。
  - エラー時の自動アラート（LINE 経由）を validate_config のチェックと連携させる案。

-----  
この CHANGELOG はソースコード中の設計コメント・関数名・処理フローから推測して作成しています。実際のリリースノート作成時はコミット履歴・JIRA/タスク管理の情報を参照して差分/担当者情報を補完してください。