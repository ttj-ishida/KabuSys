# Changelog

すべての重大な変更はこのファイルに記載します。  
フォーマットは「Keep a Changelog」に準拠します。  

なお、本CHANGELOG はコードベースからの推測で作成しています（ドキュメント/実装の要点・挙動を要約）。

## [Unreleased]


## [0.1.0] - 2026-04-18
初回リリース

### Added
- CLI / 起動スクリプト
  - run_execution.py: 実行エンジン（ExecutionEngine）起動スクリプトを追加。KABUSYS_ENV が `paper_trading` の場合は paper 用の SQLite（data/paper_trading.db など）を使用し、本番 DB と分離する挙動を実装。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト: 60秒）。停止はプロジェクトの data/stop_requested.flag により検知。
  - kabusys.validate_config: .env および config/*.yaml を起動前に検証する CLI を追加。`--strict` オプションで警告を FAIL 扱いにできる。
  - kabusys.config_setup: 対話式ウィザードで .env を生成/更新する CLI を追加。
  - tools.paper_verification_report: Paper Trading 結果の検証レポートを生成するスクリプトを追加。期間指定や DB パス指定のオプションをサポート。

- 設定関連
  - kabusys.config.Settings: 環境変数ラッパーを実装。多くの設定（DB パス、API トークン、ログレベル、しきい値など）をプロパティ経由で取得可能に。
  - .env 自動ロード: プロジェクトルート（.git / pyproject.toml を探索）から .env と .env.local を自動読み込み（OS 環境変数は保護）。自動ロードを無効化するための KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - .env パーサ: export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント等に対応した堅牢なパーサを実装。

- データベース / 分析
  - DuckDB 統合: duckdb 接続を利用するコードが追加（多くのモジュールで DuckDB を受け取る設計）。
  - 監視用 SQLite 初期化ユーティリティ（init_monitoring_db）を起動時に呼び出すことで監視テーブルの存在を保証。

- ポートフォリオ構築（純粋関数群）
  - kabusys.portfolio.portfolio_builder: 候補選定（select_candidates）・等金額/スコア加重（calc_equal_weights / calc_score_weights）を追加。スコア合計が 0 の場合はフォールバックで等分配。
  - kabusys.portfolio.risk_adjustment: セクター集中制限（apply_sector_cap）と市場レジーム乗数（calc_regime_multiplier）を追加。未知のレジームや未知セクター時のフォールバック動作を実装。
  - kabusys.portfolio.position_sizing: 株数決定ロジック（risk_based / equal / score）を実装。単元株（lot_size）丸め、per-stock 上限、aggregate cap（利用可能現金を超えた場合のスケーリング）や cost_buffer を考慮した配分アルゴリズムを実装。端数配分は残差の大きい順に単位 lot を追加する仕組み。

- ユーティリティ
  - kabusys.utils.logging_setup: 統一的ログ設定ユーティリティを追加。コンソール出力は stdout、日次ローテート（TimedRotatingFileHandler）でログファイルを出力（デフォルト logs/、30日保持）。ログディレクトリ作成失敗時はファイル出力をスキップして stdout のみで継続。
  - kabusys.utils.process_priority: プロセス優先度（high/normal/low）と CPU affinity 設定ユーティリティを追加。Windows / POSIX の差分を吸収し、権限不足や未対応 OS の場合は警告ログでスキップ。

- モニタリング / 実行制御
  - 停止フラグ・PID ファイルの取り扱い：run_execution / run_monitoring にて data 配下のフラグファイルや PID ファイルを使用して起動制御・停止制御を実装。
  - ExecutionEngine の起動は別スレッドで行い、停止フラグ検知時に engine.stop() を呼ぶ安全な停止シーケンスを実装。

- レポート / 検証
  - Paper Trading 検証レポート（tools.paper_verification_report）: 稼働率、注文成功率、送信率、P95 レイテンシ等を計算し、しきい値に基づく PASS/FAIL 判定を出力。しきい値はソース内定数で定義（例: 稼働率 >= 99% 等）。

### Changed
- ロギング周りのデフォルト動作を明確化:
  - 標準出力は stdout を使用。ログレベルは引数→環境変数→デフォルト の順で解決。
  - 既存ハンドラがある場合は一旦 flush/close してから再設定することで二重ハンドラ登録を防止。

- 環境変数取り扱いの挙動明確化:
  - .env.local は .env より優先して上書きする（ただし OS 環境変数は保護）。
  - PAPER_TRADING_SQLITE_PATH の分離により paper_trading 環境で本番 DB を汚さない設計。

### Fixed
- 環境変数の不正値に対するフォールバック動作を明確化:
  - MONITOR_POLL_INTERVAL が整数でない、あるいは 1 未満の場合は警告を出しデフォルト（60秒）を使用。
  - PAPER_FILL_MODE に不正な値が渡された場合に ValueError を発生させるバリデーションを追加。

- 例外耐性の向上:
  - run_monitoring の監視ループ内で monitor.check_once() が例外を投げてもループを継続し、例外は logger.exception で記録するように変更（次ポーリングまで待機）。
  - run_execution/run_monitoring の finally ブロックで SQLite / DuckDB 接続を確実に閉じるようにしてリソースリークを防止。

### Security
- 機密情報を扱う項目（J-Quants トークン、API パスワード、LINE トークン）は config_setup の表示でマスク（****）するなど、対話式 UI 側での配慮を追加。

### Notes / Known limitations
- research/factor_research.py など一部リサーチモジュールは計算ロジックの骨組み（DuckDB 統合、モメンタム計算の設計）を含みますが、実装が途中（切り出し末尾で未完）になっている箇所が存在します。
- apply_sector_cap の価格欠損（price が 0.0）によりエクスポージャーが過少評価される可能性があり、将来的にフォールバック価格（前日終値等）を導入することが想定されています（TODO コメントあり）。
- process_priority / cpu_affinity の設定は権限や OS に依存するため失敗する場合があり、その際は警告ログを出力してスキップします。

---

この CHANGELOG はコードベースの実装から推測して作成しています。実際のリリースノートとして使用する場合は、変更点の正確性を開発チームで確認の上、適宜更新してください。