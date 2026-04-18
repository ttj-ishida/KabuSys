# Keep a Changelog

すべての注目すべき変更をこのファイルに記録します。  
フォーマットは Keep a Changelog (https://keepachangelog.com/ja/1.0.0/) に準拠します。

## [0.1.0] - 2026-04-18

### Added
- 初回リリース。KabuSys のコア機能群を追加。
- 実行用スクリプト
  - run_execution.py — ExecutionEngine 起動スクリプトを追加。KABUSYS_ENV によってペーパートレード用の MockBrokerClient を使用し、ペーパートレード時は専用の SQLite DB（data/paper_trading.db または PAPER_TRADING_SQLITE_PATH）を使用する。
  - run_monitoring.py — SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL によるポーリング間隔上書き対応および停止フラグファイルによるシャットダウン制御を実装。
- 設定管理・導入支援
  - config.py — 環境変数/ .env ファイルからの設定読み込み、Settings クラスを提供。自動 .env ロード（.env, .env.local）の挙動と無効化フラグ（KABUSYS_DISABLE_AUTO_ENV_LOAD）を実装。
  - config_setup.py — 対話式ウィザードで .env の初期作成・更新を支援する CLI を追加。シークレットのマスク表示や保存テンプレートを提供。
  - validate_config.py — 起動前に .env や config/*.yaml の問題を検出する検証 CLI を追加（--strict オプションあり）。PyYAML の有無に応じて YAML 検証をスキップ可能。
- ロギング・プロセス制御
  - utils/logging_setup.py — 統一的なロギング設定ユーティリティを追加。stdout 出力と日次ローテーション（TimedRotatingFileHandler）をルートロガーに設定。ログディレクトリの自動作成と失敗時のフォールバックを実装。
  - utils/process_priority.py — Windows/Linux（POSIX）差分を吸収したプロセス優先度設定と CPU affinity 設定ユーティリティを追加。呼び出し元はプラットフォームを意識せずに利用可能。
- ポートフォリオ構築モジュール（純関数）
  - portfolio/portfolio_builder.py — 候補選定（select_candidates）、等配分・スコア配分（calc_equal_weights, calc_score_weights）。
  - portfolio/position_sizing.py — ポジションサイズ計算（risk_based / equal / score）、単元株丸め、aggregate cap（総投下資金に応じたスケーリング）を実装。
  - portfolio/risk_adjustment.py — セクター集中制限（apply_sector_cap）および市場レジーム乗数（calc_regime_multiplier）。
  - portfolio/__init__.py で API をエクスポート。
- 研究用モジュール（骨組み）
  - research/factor_research.py — Momentum 等のファクター計算モジュールの実装（DuckDB 接続を受け取り prices_daily / raw_financials を参照して計算）。
- 運用ツール
  - tools/paper_verification_report.py — Paper Trading 検証レポート生成スクリプトを追加。稼働率、注文成功率、送信率、レイテンシ（P95）などを集計して PASS/FAIL を判定。日付フィルタや DB パス指定オプションあり。
- 監視 DB 初期化ユーティリティ
  - monitoring.monitoring_db.init_monitoring_db を使用して起動時に監視テーブルを冪等に初期化。

### Changed
- run_monitoring の挙動
  - Monitoring は KABUSYS_ENV にかかわらず「本番」sqlite_path を使用する設計に変更（監視データの一貫性保持のため）。
  - プロセス優先度を最初に「high」に設定してから他リソースを初期化するフローを採用。
- .env 読み込みの優先度
  - OS 環境変数 > .env.local > .env の順で読み込む挙動を明確化。OS 環境変数は保護（上書き禁止）される。
- ロギング
  - 既にハンドラが設定されている場合は一度クリアしてから再設定することで多重登録を防止。
  - stdout を StreamHandler に使用（stderr ではなく）し、cron 等でのリダイレクト運用を想定。
- Execution エンジン起動フロー
  - 停止フラグ（data/stop_requested.flag）を検知するとエンジンを起動せず終了する安全措置を追加。起動後も同フラグ検知でエンジン.stop() を呼び安全終了するループを実装。
- validate_config の検証内容を整理
  - 必須環境変数チェック、KABUSYS_ENV の妥当性、LOG_LEVEL、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在・YAML パースチェック（PyYAML があれば実行）、本番環境向けの追加ガード（LINE 設定確認、KILL_FLAG_CLEAR_ON_START の危険性警告）を実装。

### Fixed
- 環境変数パースの堅牢化
  - config._parse_env_line で以下をサポート／改善:
    - "export KEY=val" 形式の対応
    - シングル/ダブルクォート内部のバックスラッシュエスケープ処理
    - クォートなし値におけるインラインコメント判定（'#' の前が空白/タブのときのみコメント扱い）
    - 無効行のスキップ
- MONITOR_POLL_INTERVAL の検証強化
  - run_monitoring._get_poll_interval で環境変数値を int にパースし、0 以下や不正値はデフォルト（60 秒）にフォールバックし、警告ログを出力することで time.sleep の例外発生を防止。
- ログ出力先ディレクトリ作成失敗時のフォールバック
  - logging_setup.setup_logging でログディレクトリ作成に失敗しても stdout のみで動作を継続するようにし、例外でプロセスを止めないようにした。
- process_priority / cpu_affinity の例外安全化
  - 権限不足や未実装 API による例外を捕捉して警告ログを出力し、処理をスキップするようにして起動の堅牢性を向上。

### Security
- .env の取り扱いに関する注意書きを config_setup._write_env のヘッダに明示（.env を絶対に Git にコミットしない旨）。

### Notes / Known limitations
- research/factor_research.py はファクター計算ロジックの主要設計を含むが、外部データ（DuckDB テーブル）に依存しており、実稼働環境でのテストが必要。
- position_sizing の lot_size は現状全銘柄共通（将来的に銘柄別の lot_map へ拡張予定）。
- apply_sector_cap の価格欠損時の挙動に関する TODO コメントあり（価格が欠損すると過少見積りされ除外が外れる可能性があるため、フォールバック価格導入を検討）。

---

このリリースは主要な初期機能（実行エンジン、監視、設定管理、ポートフォリオ構築、運用ツール、ロギング/プロセス制御）を含みます。各モジュールの詳細な使い方は該当するモジュールのドキュメンテーションと CLI のヘルプを参照してください。