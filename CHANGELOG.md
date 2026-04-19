CHANGELOG
=========

すべての重要な変更はこのファイルに記録します。

フォーマット: Keep a Changelog 準拠

Unreleased
----------

- なし

[0.1.0] - 2026-04-19
--------------------

Added
- 初回リリース: パッケージバージョンを __version__ = "0.1.0" に設定。
- 実行スクリプトを追加
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。プロセス優先度を起動時に設定し、スレッドでエンジンを実行。KABUSYS_ENV=paper_trading の場合は paper_trading 用の SQLite（data/paper_trading.db がデフォルト）を使用し、本番 DB と分離。
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可。停止フラグファイルによる安全な停止処理を実装。
- 設定関連
  - config.py: 環境変数/.env の読み込みと Settings クラスを提供。プロジェクトルート自動検出（.git または pyproject.toml 基準）、自動 .env ロード（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可）、必須値チェック helpers（_require）を実装。
  - config_setup.py: 対話式 .env 作成ウィザードを実装。既存値の再利用、シークレットマスク、保存機能を備える。
  - validate_config.py: 起動前チェック CLI を実装（--strict オプションにより警告を FAIL 扱いに可能）。必須環境変数、KABUSYS_ENV、ログレベル、DB パス、config/*.yaml の存在と YAML パース（PyYAML がある場合）などを検査。
- ポートフォリオ構築ライブラリ（純粋関数）
  - portfolio/portfolio_builder.py: 候補選定（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）を実装。スコア合計が 0 の場合は等金額配分にフォールバックして警告を出す。
  - portfolio/risk_adjustment.py: セクター集中制限を適用する apply_sector_cap、および市場レジームに基づく資金乗数 calc_regime_multiplier を実装。unknown セクターはセクター上限の対象外として扱う。
  - portfolio/position_sizing.py: 発注株数計算（risk_based / equal / score 対応）、単元株丸め、aggregate cap によるスケーリング（残差処理付き）などを実装。
  - portfolio/__init__.py: 上記関数群をパッケージとして公開。
- ユーティリティ
  - utils/logging_setup.py: 統一的なログ設定ユーティリティを追加。stdout への StreamHandler と日次ローテート（TimedRotatingFileHandler）を設定。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
  - utils/process_priority.py: Windows / POSIX（Linux/macOS/FreeBSD）差分を吸収したプロセス優先度（set_process_priority）／CPU affinity（set_cpu_affinity）設定ユーティリティを追加。権限不足や未対応 OS の場合は警告を出してスキップ。
- モニタリング DB 初期化
  - monitoring/monitoring_db.py（呼び出し実装を前提）に対する初期化を run_* スクリプトで呼び出し、監視テーブルの冪等初期化を保証。
- 実行時の安全機構
  - 停止フラグファイル（data/stop_requested.flag）と PID ファイル管理を導入。run_* スクリプトは停止フラグ検知で安全に終了/停止する。
- ツール
  - tools/paper_verification_report.py: Paper Trading 用の検証レポート生成ツールを追加。稼働率、注文成功率、送信率、P95 レイテンシなどを計算して PASS/FAIL 判定を出力。--from/--to/--db オプションをサポート。
- 研究モジュール（骨格）
  - research/factor_research.py: ファクター計算モジュールの骨格を追加（Momentum 等の要件・定数定義）。DuckDB 経由で prices_daily / raw_financials を参照する設計。注: モジュールは一部実装（calc_momentum の途中）で WIP（作業中）。

Changed
- ログ出力設計
  - stdout を標準出力に使用することで、cron / Task Scheduler などのリダイレクト運用に配慮。
  - ログレベル決定順とログディレクトリ決定順を文書化（関数引数 > 環境変数 > デフォルト）。
- 環境ファイル読み込みの挙動
  - .env のパースロジックを強化（export プレフィックス対応、クォート内のバックスラッシュエスケープ対応、行内コメントの扱い、既存 OS 環境変数の保護）。
  - 自動ロードの順序: OS 環境変数 > .env.local > .env（既存 OS 環境は上書きされない）。
- 実行環境分離
  - ExecutionEngine は paper_trading 環境時に専用 SQLite（PAPER_TRADING_SQLITE_PATH）を使うことで本番 DB と完全分離するよう設計。
  - Monitoring は環境にかかわらず運用用 sqlite_path（監視 DB）を使用する旨を明記（中央監視を意図）。
- 安全性 / 入力検証
  - MONITOR_POLL_INTERVAL の値検証を追加し、0 以下や不正な文字列の場合はデフォルト（60秒）にフォールバックして警告を出力。
  - PAPER_FILL_MODE の検証を追加（instant/partial/never/reject を有効値とする）。不正値で ValueError を送出。
  - LOG_LEVEL / KABUSYS_ENV の妥当性チェックを Settings で行い、不正値時に例外を発生させる。
- ポジションサイズ算出の堅牢化
  - calc_position_sizes: 価格が欠損・非正（<=0）の場合は対象から除外しログ出力。aggregate cap スケーリングで残差処理（lot 単位での再配分）を実装。

Fixed
- エラー耐性向上
  - run_monitoring の check_once 呼び出しで例外発生時にループを継続し、例外内容をログに残して次ポーリングへ回すように変更（監視の継続性を向上）。
  - logging_setup: ログディレクトリ作成失敗時にファイルハンドラ生成で例外が起きても、StreamHandler のみで継続して動作するように変更。
  - process_priority / set_cpu_affinity: 権限不足や未実装 API に対して例外キャッチと警告出力を追加してプロセス起動を妨げないようにした。
- calc_score_weights が全スコア 0 の場合にゼロ除算を防ぎ、等金額配分へフォールバックするよう修正。

Known issues / Notes
- research/factor_research.calc_momentum の実装が途中で終了しており、完全実装は未完（WIP）。本リリースでは骨格と定数のみ提供。
- 一部のモジュール（monitoring_db, execution.* の具体的 BrokerClient 実装 等）はこの差分で参照されているが、本 CHANGELOG 作成時点のスナップショットでは詳細実装が別ファイルに依存する場合があります。
- .env ファイルは機密情報を含むため、README 等で Git にコミットしない旨を明示しているが、リポジトリ管理時の取り扱いに注意してください。

セキュリティ
- 重要な認証情報（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD）は .env に保存する想定。Settings._require による未設定時の起動失敗保護を実装。公開リポジトリへ .env をコミットしないよう注意喚起を出している。

(以上)