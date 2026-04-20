# Changelog

すべての重要な変更履歴を here に記載します。本ファイルは Keep a Changelog 準拠の形式で日本語で記載しています。  

フォーマット:
- 追加 (Added)
- 変更 (Changed)
- 修正 (Fixed)
- 非推奨 (Deprecated)
- 削除 (Removed)
- セキュリティ (Security)

最新リリースが初期リリースのため、主に「何が追加されたか」を中心にまとめています。

## [Unreleased]

## [0.1.0] - 2026-04-20
初期リリース。以下の主要機能とユーティリティを追加しました。

### Added
- 実行/監視の起動スクリプト
  - run_execution.py: ExecutionEngine を起動するスクリプトを追加。BrokerClientFactory を用いたブローカー抽象化、OrderRepository/OrderManager/RiskManager/Reconciler の組立て、実行スレッド管理、停止フラグ（data/stop_requested.flag）と PID ファイルの取り扱いを実装。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数によるポーリング間隔上書き、停止フラグ検知、監視 DB 初期化 (init_monitoring_db) を実装。Monitoring は環境に関わらず本番 sqlite_path を使用。

- 環境設定・検証ツール
  - config_setup.py: .env の対話式ウィザードを追加。既存値の読み込み、シークレット項目のマスク表示、.env の書き出し機能を提供。
  - validate_config.py: 起動前に .env と config/*.yaml を検証する CLI を追加。--strict オプションによる警告の FAIL 扱いサポート、PyYAML 未インストール時は YAML 検証をスキップして警告表示。

- 設定管理
  - config.py: 環境変数・.env 自動ロード機能を実装（プロジェクトルート検出: .git / pyproject.toml）、.env パースの強化（export 対応、クォート内バックスラッシュエスケープ、インラインコメント処理）、Settings クラスによるプロパティアクセス（各種パス、閾値、環境種別、PAPER_FILL_MODE 検証等）を追加。

- ポートフォリオ構築関連（純粋関数モジュール）
  - portfolio.portfolio_builder: シグナル候補選択 (select_candidates)、等金額/スコア加重配分 (calc_equal_weights / calc_score_weights) を追加。
  - portfolio.position_sizing: position size 計算ロジックを追加。risk_based / equal / score の割付方法、lot_size 単位丸め、aggregate cap によるスケーリング、cost_buffer 考慮を実装。
  - portfolio.risk_adjustment: セクター集中制限の適用 (apply_sector_cap)、市場レジームに応じた乗数 (calc_regime_multiplier) を追加。

- ロギング / プロセス制御ユーティリティ
  - utils.logging_setup: 統一的なログ設定関数を追加。stdout 出力と日次ローテーションファイル出力 (TimedRotatingFileHandler) を設定。LOG_DIR の自動作成と作成失敗時のフォールバック（コンソールのみ）を実装。
  - utils.process_priority: プラットフォーム差分を吸収したプロセス優先度設定（Windows の priority class / POSIX の nice）、および CPU affinity 設定を追加。アクセス権限がない環境での安全にスキップする設計。

- Paper Trading 支援ツール
  - tools.paper_verification_report: Paper Trading の SQLite データを解析して検証レポートを生成するユーティリティを追加。稼働率／注文成功率／送信率／レイテンシ（P95）などを算出し、閾値に基づく PASS/FAIL 判定を行う。コマンドラインで日付範囲指定や DB パス指定が可能。

- データアクセス
  - DuckDB 連携: run_* スクリプトや research モジュールで DuckDB 接続を使用する設計を導入（Settings.duckdb_path により指定）。
  - monitoring DB 初期化ヘルパー呼び出し: init_monitoring_db を起動スクリプトから呼び出して監視テーブルの存在を保証（冪等）する実装。

- パッケージメタ情報
  - kabusys.__init__ にてバージョン __version__ = "0.1.0" を設定。

### Changed
- （初期リリースのため「変更」は特になし）

### Fixed
- .env パース挙動の堅牢化:
  - export プレフィックス対応、クォート内でのバックスラッシュエスケープ処理、クォートなし時のインラインコメント判定ルールを改善して現実的な .env 記述に耐えるようにしました。
- logging_setup の堅牢化:
  - ログディレクトリ作成に失敗した際のフォールバック（ファイルハンドラを設定せず StreamHandler のみで継続）と、その際の警告出力を追加しました。
- process_priority のフォールバック:
  - 未対応 OS や権限不足時に警告を出し安全にスキップするようにしました。

### Security
- config_setup で生成される .env ファイルに関する注意を明記:
  - .env は絶対に Git にコミットしないようにする警告ヘッダを出力する実装。
- secret 項目（J-Quants トークン、kabu API パスワード、LINE トークン等）は対話ウィザードでマスク表示され、.env に平文で保存される旨をユーザに分かりやすく提示しています（運用上の注意）。

### Notes / Usage tips
- Paper Trading と本番 DB は分離:
  - run_execution.py は KABUSYS_ENV=paper_trading の場合、Settings.paper_sqlite_path（デフォルト data/paper_trading.db）を使用して本番 DB と完全分離する設計になっています。
- 監視ループ（run_monitoring.py）は MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更可能。無効な値（0 や非数）を設定した場合はデフォルト 60 秒にフォールバックします。
- 停止制御はファイルフラグ方式:
  - data/stop_requested.flag や data/execution.pid 等のファイルにより起動/停止管理を行います。KILL フラグ等の挙動は Settings の kill_flag_* プロパティで制御できます。
- ログは既定で logs/ に日次ローテーションで出力されます（LOG_DIR/LOG_LEVEL で上書き可能）。ログ出力に失敗した場合はコンソール出力のみで継続します。
- validate_config.py により、起動前に必要な環境変数や YAML ファイルの有無をチェックできます。--strict をつけると警告もエラー扱いになります。

### Known limitations / TODO
- 一部モジュール（例: research.factor_research）は設計に沿った実装を進めていますが、外部依存（DuckDB テーブルの存在等）や未実装箇所がある可能性があります。実運用前に validate_config と簡易テストを推奨します。
- position_sizing の lot_size は現状全銘柄共通の固定値（デフォルト 100）を想定しており、将来的に銘柄別 lot_map への拡張を想定しています（TODO コメントあり）。
- apply_sector_cap は price_map が欠損（0.0）だとエクスポージャーが過少見積もられる可能性があり、将来的にはフォールバック価格の導入を検討する旨がコメントされています。

---

（注）この CHANGELOG は提供されたコードベースを解析して推測により作成しています。実際のコミット履歴や開発ノートに基づく正式な変更履歴は、Git のコミットログ等を参照して作成してください。