# Changelog

すべての注目すべき変更点を記録します。  
このファイルは Keep a Changelog の形式に準拠しています。  

フォーマット:
- Unreleased: 未リリースの変更点（将来の変更はこちらに追加してください）
- 各リリースは日付付きで記載します。

## [Unreleased]

（現時点ではありません）

## [0.1.0] - 2026-04-20

### Added
- 全体
  - 初期リリース。システム全体の主要コンポーネント、CLI、およびユーティリティを実装。
  - パッケージバージョンを `kabusys.__version__ = "0.1.0"` として設定。

- 起動スクリプト / 実行
  - run_execution:
    - ExecutionEngine 起動スクリプトを実装。プロセス優先度設定・ログ設定を行い、ExecutionEngine を別スレッドで実行。
    - KABUSYS_ENV が `paper_trading` の場合は Paper Trading 用の専用 SQLite DB（既定: `data/paper_trading.db`）を使用して本番 DB と分離。
    - 停止フラグファイル（`data/stop_requested.flag`）の存在を監視し、検知時にエンジン停止・シャットダウンする仕組みを搭載。
    - 実行用 PID ファイルサポート（既定: `data/execution.pid`）。

  - run_monitoring:
    - SystemMonitor ポーリングループ起動スクリプトを実装。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - Monitoring は環境にかかわらず本番の sqlite_path を使用する設計。
    - 停止フラグファイルを検出してループを終了する安全な終了処理を含む。

- 設定管理 / CLI
  - config:
    - 環境変数 / .env 読み込み・管理用クラス `Settings` を実装。
    - プロジェクトルート自動検出（.git または pyproject.toml）に基づく .env 自動読み込み（優先順位: OS 環境 > .env.local > .env）。自動読み込みを無効化するための `KABUSYS_DISABLE_AUTO_ENV_LOAD` をサポート。
    - .env 解析はクォート、エスケープ、コメント、`export KEY=...` 形式に対応する堅牢なパーサを実装。
    - 多数の設定プロパティを提供（J-Quants / kabu API / LINE / DB パス / 監視閾値 / 実行環境など）。バリデーション（例えば KABUSYS_ENV、LOG_LEVEL、PAPER_FILL_MODE の許容値チェック）を内蔵。

  - config_setup:
    - 対話式ウィザード `python -m kabusys.config_setup` を実装し、.env の初期作成・更新を支援。
    - シークレットをマスク表示、選択肢サポート、既存 .env の読み込みと Enter での再利用、保存確認を提供。
    - .env の書き出しテンプレートを生成（保存時に注意書きコメントを付与）。

  - validate_config:
    - 設定検証 CLI `python -m kabusys.validate_config` を実装。
    - 必須/任意環境変数のチェック、KABUSYS_ENV / LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在確認と（PyYAML があれば）パースチェックを実施。
    - `--strict` オプションで警告も失敗扱いにできる。

- ポートフォリオ構築ライブラリ（pure function）
  - portfolio.portfolio_builder:
    - 候補選定 `select_candidates`（スコア降順・同点は signal_rank でタイブレーク）。
    - 等分配 `calc_equal_weights` とスコア加重 `calc_score_weights`（全スコアが 0 の場合は等分配にフォールバックし WARNING を出力）。

  - portfolio.risk_adjustment:
    - セクター集中上限適用 `apply_sector_cap`（既存保有比率が所定の閾値を超えるセクターの新規候補を除外、"unknown" セクターは除外対象外）。
    - レジーム乗数 `calc_regime_multiplier`（"bull"=1.0, "neutral"=0.7, "bear"=0.3、未知レジームは 1.0 にフォールバックして警告）。

  - portfolio.position_sizing:
    - 株数決定 `calc_position_sizes` を実装。
    - allocation_method による分岐（"risk_based" / "equal" / "score"）をサポート。
    - per-stock 上限（max_position_pct）、aggregate cap（available_cash）を考慮したスケーリング、単元株（lot_size）丸め、cost_buffer による保守的コスト推定、残余キャッシュを用いた端数の配分ロジックを備える。
    - 価格欠損時のスキップやログ出力の考慮。

- ユーティリティ
  - utils.logging_setup:
    - 統一ログ設定関数 `setup_logging(app_name, log_dir, level)` を実装。
    - stdout への StreamHandler と日次ローテートされる TimedRotatingFileHandler（デフォルト logs/<app_name>.log、30日保持）をルートロガーに設定。既存ハンドラのクリーンアップを行う。
    - ログディレクトリ作成に失敗した場合はファイル出力をスキップして stdout のみで継続するフォールバックを実装。
    - LOG_LEVEL/LOG_DIR の環境変数に対応。

  - utils.process_priority:
    - クロスプラットフォーム（Windows / POSIX）でのプロセス優先度設定 `set_process_priority` を実装（psutil を使用、許容レベル: high/normal/low）。
    - CPU affinity 設定 `set_cpu_affinity` を実装（最初の N コアに固定、権限や未対応環境では警告を出してスキップ）。

- モニタリング / レポート
  - monitoring（run_monitoring を含む）:
    - SQLite / DuckDB 接続の初期化、監視 DB テーブル初期化（init_monitoring_db 呼び出し）。
    - 例外隔離（check_once 内での例外はループを止めずにログ化して次ポーリングへ）。

  - tools.paper_verification_report:
    - Paper Trading 用検証レポート生成ツールを実装（コマンドライン引数 --from / --to / --db をサポート）。
    - 指標: 稼働率(uptime)、注文成功率(fill rate)、送信率(send rate)、P95 レイテンシ等を計算。
    - デフォルト閾値を定義（稼働率 >= 99%、成立率 >= 90%、送信率 >= 95%、P95 <= 200 ms）と Pass/Fail 判定ロジックを提供。
    - 日付フィルタのタイムスタンプ化（ISO8601 UTC）を実装し、DB 存在チェックとエラーハンドリングを備える。

- 研究用モジュール（research）
  - research.factor_research:
    - DuckDB を用いてモメンタム / MA200 / ATR / 出来高等のファクター計算を実装する設計を追加（関数インターフェースと定数群を定義、実装途中のファイルあり）。

### Changed
- デフォルトと安全性
  - run_monitoring と run_execution でプロセス起動直後にプロセス優先度を "high" に設定するよう統一（set_process_priority を最初に呼ぶ）。
  - run_execution/run_monitoring が使用する DB 接続方法を明確化（sqlite3 / duckdb の両方を使用）。

- ログの取り扱い
  - logging_setup は既存ハンドラを全て flush/close してから入れ替えることで二重出力を防止。

### Fixed
- 考慮済みの堅牢化・フォールバック
  - .env 解析で引用符・エスケープ・インラインコメントの扱いを改善し、さまざまな .env 表現に対応。
  - process_priority の実行で権限不足や未対応環境（psutil の定数未定義等）に対して例外を握り潰し、警告でスキップするようにして起動失敗を防止。
  - logging_setup でログディレクトリ作成に失敗した場合もコンソール出力を確保するよう修正。

### Security
- シークレット管理
  - config_setup ウィザードはシークレット項目（J-Quants / KABU API パスワード等）を入力時にマスク表示し、.env の Git 管理禁止をドキュメント化。

---

備考:
- 本 CHANGELOG はソースコードから推測して作成しています。実装の細部や外部モジュール（例: ExecutionEngine, SystemMonitor, BrokerClientFactory 等）の振る舞いに依存する点は、実行時の挙動や追加リリースで変わる可能性があります。必要であれば、各モジュールの詳細実装を元により精密な変更履歴を作成します。