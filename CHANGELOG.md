# Changelog

すべての変更は Keep a Changelog の形式に従います。  
このファイルはコードベース（src/ 以下）の実装内容から推測して作成しています。

全般的なバージョニング方針: メジャー.マイナー.パッチ（このリリースは初期公開相当の 0.1.0 と想定）。

## [Unreleased]

- 現在未リリースの変更はありません。

## [0.1.0] - 2026-04-24

### Added
- コアランタイム
  - 実行スクリプトを追加:
    - run_execution.py: ExecutionEngine を起動するエントリポイントを実装。Broker クライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て、スレッドでのエンジン実行、停止フラグ監視、PID ファイル管理を行う。
    - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを実装。MONITOR_POLL_INTERVAL 環境変数によるポーリング間隔指定、停止フラグ検知での安全停止、monitoring DB 初期化を行う。
  - Settings（config.py）: 環境変数／.env 読み込みと各種設定プロパティを実装。KABUSYS_ENV（development/paper_trading/live）、ログレベル、DB パス、paper trading 用設定、各種しきい値などを提供。
  - 自動 .env ロード機能: プロジェクトルート（.git または pyproject.toml を基準）を探索して .env/.env.local を自動読み込み（OS 環境変数を保護）。KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能。
  - 設定検証 CLI:
    - validate_config.py: 必須環境変数、KABUSYS_ENV, LOG_LEVEL, DB パス、config/*.yaml の存在とパース検証、本番時のガードチェック等を行う。--strict オプションで警告を失敗扱いにできる。
  - 設定ウィザード CLI:
    - config_setup.py: 対話式に .env を初期作成・更新するウィザードを実装。既存 .env 読み込み・マスク表示・保存機能を提供。
- ポートフォリオ構築（portfolio モジュール）
  - portfolio_builder: シグナルのソート（select_candidates）、等分配（calc_equal_weights）、スコア重み付け（calc_score_weights）を実装。スコアが全て 0 の場合は等分配にフォールバック。
  - risk_adjustment: セクター集中制限（apply_sector_cap）とレジーム乗数（calc_regime_multiplier）を実装。未知レジームはフォールバックで 1.0 を返す。
  - position_sizing: 発注株数計算（calc_position_sizes）を実装。risk_based / equal / score の配分方式をサポートし、単元株（lot_size）丸め、1銘柄上限・集計上限（aggregate cap）・コストバッファを考慮したスケーリング処理を行う。
- 監視・モニタリング
  - monitoring 側の DB 初期化（init_monitoring_db を呼び出し）を実装して監視テーブルの存在を保証（冪等）。
  - run_monitoring では本番 sqlite_path を使用する設計（環境にかかわらず監視 DB は共通の本番 DB を参照するポリシー）。
- ユーティリティ
  - logging_setup: ルートロガーに StreamHandler (stdout) と TimedRotatingFileHandler（日次ローテーション、30日保持）を統一的に設定するユーティリティを追加。LOG_DIR/LOG_LEVEL の解決順などを定義。ログディレクトリ作成失敗時はファイル出力を自動的にスキップ。
  - process_priority: psutil を用いたプロセス優先度設定ユーティリティを追加（Windows / POSIX の差分吸収）。CPU affinity を最初の N コアに固定する helper も提供。
- Paper Trading / 検証ツール
  - tools/paper_verification_report.py: Paper Trading 用 SQLite（デフォルト data/paper_trading.db）から稼働率、注文成功率、送信率、API レイテンシ（平均/最大/P95）やリスク却下数を集計して検証レポートを生成する CLI を追加。閾値判定に基づく PASS/FAIL を出力。期間フィルタ（--from / --to）と DB パス指定（--db）をサポート。テーブルが存在しない場合は例外を吸収して「データなし」扱いにフォールバックする。
- research/factor_research.py（骨格）
  - DuckDB を用いたファクター計算モジュールの骨格を追加（モメンタム等の定義・定数を含む）。（実装途中の記述あり）

### Changed
- データベース取り扱い
  - run_execution は KABUSYS_ENV=paper_trading 時に paper_sqlite_path（デフォルト data/paper_trading.db）を使用して本番 DB と完全に分離するよう実装。
  - DuckDB 接続（duckdb.connect）を複数箇所で使用する設計に変更し、分析用 DB を明確化（Settings.duckdb_path）。
- ログ動作
  - stdout を標準出力に使うことで cron/タスクスケジューラからのリダイレクト運用を想定。
  - 既存のハンドラをクリアしてから再設定することで二重登録を回避。
- 環境変数パース
  - .env の行パーサを充実化（export プレフィックス対応、クォート文字内のバックスラッシュエスケープ対応、インラインコメントの取り扱い、無効行の無視など）。
  - .env.local を .env より優先して読み込む（ただし OS 環境変数は保護）。
- ジョブ起動時の振る舞い
  - 起動時にプロセス優先度を "high" に設定する呼び出しを run_execution/run_monitoring の最初に配置。
  - 実行時の停止制御を data/stop_requested.flag および data/execution.pid（PID 管理）で行う設計を採用。

### Fixed
- エラー耐性の向上
  - run_monitoring のポーリングループで monitor.check_once() が例外を投げてもループを継続し、例外をログに残して次回に備えるようにした。
  - logging_setup でログディレクトリ作成やファイルハンドラ作成に失敗した場合に、コンソール出力のみで継続する安全なフォールバックを追加。
  - .env 読み込みでファイルオープンに失敗した場合は警告を出して処理を継続するようにした。

### Removed
- 特になし

### Known issues / TODOs
- portfolio/risk_adjustment.apply_sector_cap:
  - price_map に price が欠損（0.0）の場合、エクスポージャーが過少見積りされる可能性がある（コード中に TODO があり、前日終値や取得原価などのフォールバックを検討中）。
- portfolio/position_sizing:
  - 将来的には銘柄ごとの lot_size をサポートする設計への拡張（現在は全銘柄共通の lot_size）。
- research/factor_research.py:
  - ファイル末尾で実装途中（calc_momentum の開始のみ）が見られる。ファクター計算ロジックは今後整備が必要。
- 本番運用ガード:
  - validate_config によるチェックを推奨（特に KABUSYS_ENV=live の場合は LINE 通知設定や KILL_FLAG_CLEAR_ON_START の値に注意すること）。

---

配布／導入手順（推奨）
- .env を作成して必須変数（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD 等）を設定する。
- python -m kabusys.config_setup で初期セットアップ、python -m kabusys.validate_config で検証を実行する。
- run_execution.py/run_monitoring.py を適切なユーザ権限で起動する（プロセス優先度設定や PID ファイル利用のため）。
- Paper Trading の検証には tools/paper_verification_report.py を利用する。

（注）本 CHANGELOG はコード内容からの推測に基づいています。実際のリリースノート作成時にはコミット履歴や PR の説明を参照して正確な差分を反映してください。