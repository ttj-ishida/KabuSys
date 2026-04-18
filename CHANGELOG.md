CHANGELOG.md
=============

すべての注目すべき変更点を記録します。  
フォーマットは "Keep a Changelog" に準拠しています。

バージョン付けは SemVer を想定しています。

[Unreleased]
------------

- （なし）

[0.1.0] - 2026-04-18
--------------------

初回リリース。以下の主要機能・ユーティリティを追加しました。

Added
- コアライブラリ初期実装
  - パッケージバージョンを設定: `kabusys.__version__ = "0.1.0"`.
- 起動スクリプト
  - run_execution: 実取引/ペーパートレード双方に対応した ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV が `paper_trading` の場合は専用の SQLite（デフォルト: data/paper_trading.db）を使用し、本番 DB と分離。
    - 停止制御用ファイル（data/stop_requested.flag）と PID 管理（data/execution.pid）のサポート。
    - BrokerClientFactory によるブローカクライアント生成、OrderManager / RiskManager / Reconciler の組み立て、ExecutionEngine のバックグラウンド実行制御を実装。
  - run_monitoring: SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止フラグファイル検出で安全にループを終了。
    - 監視は環境にかかわらず本番用の sqlite_path を使用（設計方針）。
- 環境設定・検証 CLI
  - config_setup: 対話式ウィザードで .env を初期作成・更新する CLI を追加（シークレットマスク表示、デフォルト値、選択肢サポート）。
  - validate_config: .env と config/*.yaml の事前検証ツールを追加（--strict オプションで警告を失敗扱いにできる）。
- 設定管理
  - `kabusys.config.Settings` を追加。環境変数から各種設定を集約して提供。
  - .env 自動ロード機構を実装（プロジェクトルート検出: .git / pyproject.toml を基準）。優先順位: OS環境変数 > .env.local > .env。
  - .env パーサ強化:
    - `export KEY=val` 形式対応、シングル/ダブルクォート内のバックスラッシュエスケープ処理、インラインコメントの扱いを考慮。
    - 必須キー未設定時は明示的なエラーを投げる `_require()` を提供。
  - PAPER_TRADING_SQLITE_PATH / PAPER_FILL_MODE / KILL_FLAG_CLEAR_ON_START などペーパートレード向け設定を追加。
- ロギング・プロセスユーティリティ
  - `kabusys.utils.logging_setup.setup_logging` を追加:
    - stdout への StreamHandler と日次ローテート（TimedRotatingFileHandler）をルートロガーに設定。
    - ログディレクトリ作成に失敗した場合はファイル出力をスキップしてコンソールのみで継続。
    - LOG_LEVEL / LOG_DIR の環境変数対応。
  - `kabusys.utils.process_priority` を追加:
    - Windows / POSIX を透過してプロセス優先度（high/normal/low）を設定。
    - CPU affinity 設定関数 `set_cpu_affinity` を提供。
    - psutil を使ったアクセス権エラー時は警告を出して安全にスキップ。
- ポートフォリオ構築ライブラリ
  - `kabusys.portfolio.portfolio_builder`:
    - 候補選定 select_candidates（スコア降順・タイブレーク処理）。
    - 等金額配分 calc_equal_weights。
    - スコア加重配分 calc_score_weights（全スコアが 0 の場合に等金額にフォールバック）。
  - `kabusys.portfolio.risk_adjustment`:
    - セクター集中制限 apply_sector_cap（既存保有を考慮した除外ロジック）。
    - レジームに応じた投入資金乗数 calc_regime_multiplier（bull/neutral/bear とフォールバック）。
  - `kabusys.portfolio.position_sizing`:
    - 発注株数計算 calc_position_sizes（risk_based / equal / score の方式、単元株丸め、aggregate cap スケーリング、cost_buffer 考慮）。
- 研究・指標計算（スキャフォールド）
  - `kabusys.research.factor_research` を追加（DuckDB を用いたファクター計算のための実装開始。モメンタム等の計算方針と定数を定義）。
- ツール
  - tools/paper_verification_report: ペーパートレード用検証レポート生成スクリプトを追加。
    - 稼働率、注文成功率、送信率、P95 レイテンシ等を算出して PASS/FAIL 判定を行う。
    - 日付フィルタ、DB パス指定オプションをサポート。
- 監視 DB 初期化ヘルパー
  - `init_monitoring_db`（monitoring.monitoring_db）を起動スクリプトから必ず呼び出し、監視用テーブルの存在を保証（冪等）。

Changed
- ログ出力の統一:
  - すべての起動スクリプトで `setup_logging` を呼ぶ設計とし、ログの一貫性を確保。
- 起動時プロセス優先度をデフォルトで "high" に設定するフローを導入（run_execution / run_monitoring）。

Fixed / Fallbacks / Robustness
- 環境変数パース・検証の堅牢化:
  - MONITOR_POLL_INTERVAL の不正値に対するフォールバック（デフォルト 60 秒）と警告。
  - PAPER_FILL_MODE の無効値に対する ValueError。
  - calc_score_weights で全スコアが 0 の場合、等金額にフォールバックして警告ログ出力。
  - calc_regime_multiplier で未知のレジームは 1.0 にフォールバックし警告。
- ロガー・ファイルハンドラ作成失敗時の安全なフォールバック: コンソール出力のみで継続。
- 起動制御の安全化:
  - run_execution が停止フラグを検知した場合は起動を中止または実行中の Engine を停止して安全終了。
  - run_monitoring は停止フラグ検知・KeyboardInterrupt を考慮して DB 接続を確実にクローズ。

Notes / Implementation Details
- DuckDB と SQLite を併用:
  - 分析用に DuckDB（default: data/kabusys.duckdb）、監視/注文履歴用に SQLite（default: data/monitoring.db）を使用する想定。
- デフォルトパス・環境変数:
  - 多くのパスや閾値は環境変数で上書き可能（例: DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH, LOG_LEVEL, LOG_DIR 等）。
- セキュリティ/運用に関する注意:
  - .env は絶対に Git にコミットしない旨を config_setup の出力に明記。
  - validate_config は本番環境（KABUSYS_ENV=live）向けのガードチェック（LINE 通知設定、KILL_FLAG_CLEAR_ON_START の危険性）を実装。

既知の制限 / TODO
- 一部モジュール（research.factor_research など）は機能の一部がスキャフォールド状態で、さらに実装・テストが必要。
- position_sizing の lot_size は全銘柄共通としているが、将来的に銘柄別単元をサポートする拡張を検討。
- apply_sector_cap の価格欠損時の扱い（現状は 0.0 で過少見積りとなる）に対するフォールバック価格取得の実装予定。

補足
- 本 CHANGELOG はソースコードの実装内容から推測して作成しています。実際のリリースノートとして使用する場合は、開発チームによる確認・補完を推奨します。