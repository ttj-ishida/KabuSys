# CHANGELOG

すべての変更は [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) の方針に準拠して記載しています。  
日付はコードベースの現在日付（2026-04-25）で記載しています。バージョンはパッケージの __version__（0.1.0）に合わせています。

## [Unreleased]
- （現時点の差分はありません）

## [0.1.0] - 2026-04-25

### Added
- 起動スクリプトを追加
  - run_execution: ExecutionEngine を起動するエントリポイントを追加。paper_trading 環境時は MockBrokerClient を利用し、paper_trading 専用 SQLite（data/paper_trading.db）を使用する分離を実装。
  - run_monitoring: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数によるポーリング間隔の上書き対応（デフォルト 60 秒）。停止フラグファイル検出で安全に終了。

- 環境/設定関連ツールを追加
  - config_setup: 対話式の .env 作成・更新ウィザードを追加。既存 .env の読み込み・既存値再利用・シークレットマスク表示等に対応。
  - validate_config: .env と config/*.yaml の事前検証 CLI を追加。必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性、DB パスや YAML のパース検証、live 環境向けのガード（LINE 設定や Kill Switch の注意）を実装。

- 設定管理を強化（kabusys.config）
  - プロジェクトルート自動検出（.git / pyproject.toml を探索）に基づく .env 自動読み込み機構を追加。OS 環境変数の保護（上書き禁止）や .env.local の優先ロードに対応。自動ロードを無効にする KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - .env パーサ実装を改善し、`export KEY=val` 形式、シングル/ダブルクォート内のエスケープ、インラインコメントの扱いを考慮。
  - 各種設定プロパティを追加・整備（DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH, PAPER_FILL_MODE の検証など）。

- ロギング / プロセス制御ユーティリティを追加（kabusys.utils）
  - logging_setup: stdout 出力用 StreamHandler と 日次ローテートする TimedRotatingFileHandler をルートロガーに統一的に設定するユーティリティを追加。LOG_DIR/LOG_LEVEL の解決順と、ハンドラ二重設定防止ロジックを搭載。
  - process_priority: Windows / POSIX の差分を吸収してプロセス優先度（high/normal/low）を設定するユーティリティを追加。CPU affinity 設定機能も提供。

- ポートフォリオ構築関連モジュールを追加（kabusys.portfolio）
  - portfolio_builder: 候補選定（スコア降順）、等配分・スコア加重による重み算出を実装。
  - risk_adjustment: セクター集中制限（apply_sector_cap）と市場レジームに応じた投下資金乗数（calc_regime_multiplier）を実装。
  - position_sizing: risk_based / equal / score に基づく発注株数算出ロジックを実装。単元株（lot_size）丸め、単銘柄上限、aggregate cap によるスケールダウン、cost_buffer（手数料・スリッページ見積り）対応。

- Paper Trading 検証ツールを追加（kabusys.tools.paper_verification_report）
  - Paper Trading 用 SQLite から稼働率、注文成功率、送信率、レイテンシ（avg, max, P95）等を集計し、閾値判定（PASS/FAIL）を出力するレポート生成スクリプトを追加。期間指定（--from / --to）や DB パス指定（--db）に対応。

- DuckDB 統合
  - 分析用に DuckDB 接続（duckdb）を各種エンジンで使用可能にし、duckdb_path の設定を追加。

### Changed
- 実行時の振る舞い・安全性向上
  - ExecutionEngine 起動時に停止フラグを検知したら起動を回避する仕組みを導入。起動後も停止フラグ検出でエンジン停止を試みる。
  - run_monitoring は KABUSYS_ENV に関わらず本番 sqlite_path を使用して監視データを保存する設計（監視データを本番DBと統一して扱う想定）。
  - ログ出力は stdout を基準にし、cron/Task Scheduler での運用を考慮して stderr ではなく stdout を使用。

- 設定値の検証強化
  - PAPER_FILL_MODE の許容値検証を実装（instant/partial/never/reject）。
  - KABUSYS_ENV と LOG_LEVEL の値検証を validate_config と Settings で重複確認して堅牢化。

- DB 初期化の冪等性
  - init_monitoring_db 呼び出しを実行時に行い、監視テーブルが存在することを保証（既に存在する場合も問題にならない）。

### Fixed
- 環境変数入力の堅牢性向上
  - _get_poll_interval（run_monitoring）で MONITOR_POLL_INTERVAL の不正値（非整数・0 以下）を検知してデフォルトにフォールバックするよう修正。time.sleep に不正値が渡るのを防止。
  - logging_setup: ログディレクトリ作成失敗時にファイルハンドラ作成をスキップし、コンソール出力のみで継続するようにして起動失敗を回避。
  - process_priority / set_cpu_affinity: 権限不足や未対応 OS の際に例外を握りつぶしてログ警告に留めることで、非致命的に運用可能に。

- レポート/集計の堅牢化
  - paper_verification_report: データ不足やテーブル未存在時に sqlite3.OperationalError を捕捉して個別にデフォルト値を扱うことで、レポート生成が途中で失敗しないように修正。
  - P95 計算ロジックを安全に扱い、空データ時は None を返してレポートに N/A を表示。

### Documentation / Other
- パッケージメタ情報
  - __version__ を 0.1.0 に設定。
  - package-level __all__ を定義して主要モジュール（data, strategy, execution, monitoring）を公開。

- コードコメント・設計メモを充実
  - PortfolioConstruction.md / StrategyModel.md 等のドキュメント参照をコメント中で明記し、各関数の仕様（引数・戻り値・フォールバック方針）を詳細に注釈。

---

注:
- 上記は提供されたコードベースの内容から推測された変更・機能一覧です。実際のコミット履歴やリリースノートが存在する場合はそれに従ってください。