CHANGELOG
=========

すべての変更は Keep a Changelog の形式に準拠して記載しています。
リリース日はリポジトリ内の __version__ とコードの状態に基づき推定しています。

[Unreleased]
------------

- (なし)

0.1.0 - 2026-04-18
------------------

Added
- 基本機能・CLI
  - 初期リリース（0.1.0）。自動売買システム KabuSys のコア機能を追加。
  - 実行エントリスクリプト:
    - run_execution.py: ExecutionEngine を起動するスクリプトを追加。KABUSYS_ENV=paper_trading の場合は paper_trading 用の専用 SQLite（data/paper_trading.db を想定）を使用して本番 DB と分離し、MockBrokerClient を利用する設計をサポート。プロセス起動時に優先度を "high" に設定し、停止フラグ（data/stop_requested.flag）と PID ファイル（data/execution.pid）を扱う。
    - run_monitoring.py: SystemMonitor のポーリングループを起動するスクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。Monitoring は環境にかかわらず本番 sqlite_path を使用する点に注意。
  - 設定関連 CLI:
    - config_setup.py: .env の対話式ウィザードを実装。主要な環境変数（KABUSYS_ENV、JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、DUCKDB_PATH、SQLITE_PATH など）を対話で作成・更新可能。
    - validate_config.py: 起動前チェック用 CLI を追加。必須環境変数・KABUSYS_ENV の妥当性、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在および PyYAML によるパース確認、ライブ環境向けの追加ガードなどを実行。--strict オプションで警告を FAIL 扱いにできる。
  - ツール:
    - tools/paper_verification_report.py: Paper Trading 用の検証レポート生成スクリプトを追加。期間指定オプション (--from / --to) と DB パス指定 (--db) をサポート。システム安定性（稼働率）、注文成功率、送信率、リスク却下数、API レイテンシ（avg/max/P95）を集計し PASS/FAIL 判定を出力する。既定の合格基準（稼働率 >= 99%、成立率 >= 90%、送信率 >= 95%、P95 レイテンシ <= 200 ms）を定義。
- 設定管理
  - config.py:
    - .env 自動ロード機能を実装（プロジェクトルートの検出に .git または pyproject.toml を使用）。OS 環境変数を保護する仕組み（protected set）により上書きを制御。
    - .env のパース関数は export プレフィックス、クォート文字列、エスケープ、インラインコメントなどに対応する堅牢な実装を採用。
    - 各種設定プロパティを提供（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、DUCKDB_PATH、SQLITE_PATH、PAPER_FILL_MODE（有効値検証）、PAPER_TRADING_SQLITE_PATH、PID/KILL フラグパス、閾値設定、環境（KABUSYS_ENV）/ログレベル検証等）。
- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py:
    - select_candidates: BUY シグナルをスコア降順で選別し上位 N 件を返す（同点は signal_rank でタイブレーク）。
    - calc_equal_weights, calc_score_weights: 等金額配分とスコア加重配分を実装。全スコアが 0 の場合は警告を出して等金額にフォールバック。
  - portfolio/risk_adjustment.py:
    - apply_sector_cap: 既存保有のセクター比率に基づくセクター集中制限を実装（unknown セクターは除外しない仕様）。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数を提供（未定義レジームは警告を出して 1.0 にフォールバック）。
  - portfolio/position_sizing.py:
    - calc_position_sizes: allocation_method（"risk_based" / "equal" / "score"）に基づく株数計算を実装。単元 (lot_size) 丸め、per-position 上限、aggregate cap（利用可能現金を超えた場合のスケールダウンと remainder による再配分）を考慮。cost_buffer を用いた保守的なコスト見積りに対応。
  - portfolio/__init__.py で上記関数を公開。
- 研究/ファクター計算（骨格）
  - research/factor_research.py: DuckDB を使ったファクター計算モジュールの骨格を追加（モメンタム、MA200、ATR、出来高指標等を想定）。関数インターフェースと定数が定義されている（実装途中を示唆する記述あり）。
- ユーティリティ
  - utils/logging_setup.py:
    - 統一的なログ設定ユーティリティを提供。stdout ベースの StreamHandler（stdout を使用）と TimedRotatingFileHandler（日次、30日バックアップ）をルートロガーに設定。ログディレクトリの自動作成と失敗時のフォールバック処理を実装。ログレベルは引数 > 環境変数 > デフォルト の順で決定。
  - utils/process_priority.py:
    - psutil を利用してクロスプラットフォームでプロセス優先度設定（Windows と POSIX 系での差分吸収）と CPU affinity のユーティリティを提供。権限不足や未対応 OS では警告を出して安全にスキップ。
- その他
  - パッケージ初期化: __init__.py にバージョンを追加（__version__ = "0.1.0"）と主要サブパッケージのエクスポート定義。
  - logging の実行時統一、プロセス優先度のデフォルト変更（起動時に high をセットするフローが run_execution/run_monitoring に組み込まれている）。

Changed
- (このリリースは初期追加のため大きな変更履歴はなし)

Fixed
- (このリリースは初期追加のため修正履歴はなし)

Notes / Known limitations
- config.py / .env パーサは多くのケースに対応しているが、非常に複雑な .env のエッジケースは未検証。自動読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
- position_sizing.calc_position_sizes:
  - price が欠損（0.0）の場合の扱いに TODO コメントあり（将来的に前日終値や取得原価でフォールバックする可能性を想定）。
  - lot_size は現状グローバル共通。将来的に銘柄別単元対応を予定。
- research/factor_research.py はファクター計算の骨格とインターフェースを備えるが、一部実装が未完（ファイル末尾に断片があるため継続実装が必要）。
- run_monitoring.py は監視用 DB 接続に本番 sqlite_path を使用するため、テスト・paper_trading 時の監視データ分離に注意が必要。
- paper trading（KABUSYS_ENV=paper_trading）では MockBrokerClient と別 DB を利用する設計だが、Mock の挙動やフィルモード（PAPER_FILL_MODE）の詳細実装は別モジュールに依存。

Security
- 環境変数や .env の扱いに注意。config_setup により生成される .env は絶対に Git にコミットしないことを README ヘッダに明記している。

Contact
- バグ報告・改善要望はリポジトリの Issue にお願いします。