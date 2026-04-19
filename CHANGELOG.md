CHANGELOG
=========

すべての注目すべき変更はこのファイルに記録します。
フォーマットは「Keep a Changelog」に準拠します。

[Unreleased]
-------------

- 今のところ保留中の変更はありません。

[0.1.0] - 2026-04-19
-------------------

初回リリース。日本株自動売買システム「KabuSys」の基本コンポーネントを実装しました。
主な追加点、挙動および注意点は以下の通りです。

Added
- 基本パッケージ
  - kabusys パッケージ初期バージョンを追加。バージョンは src/kabusys/__init__.py にて __version__ = "0.1.0"。
- 実行/監視用エントリポイント
  - run_execution.py: ExecutionEngine を起動する CLI スクリプトを追加。
    - KABUSYS_ENV=paper_trading 時は paper 用の SQLite（data/paper_trading.db、環境変数で上書き可）を使用し、MockBrokerClient を利用する想定（BrokerClientFactory 経由）。
    - エンジンは別スレッドで run_session を起動し、data/stop_requested.flag（プロジェクトルート/data）を監視して安全停止。
    - 起動前に実行中判定用の PID ファイル (data/execution.pid) を扱う。
    - RiskManager に渡す設定（RiskConfig）に initial_portfolio_value を broker.get_available_cash() で参照。
  - run_monitoring.py: SystemMonitor をポーリングする監視スクリプトを追加。
    - ポーリング間隔を MONITOR_POLL_INTERVAL 環境変数で上書き可能（デフォルト 60 秒）。不正な値は警告の上デフォルトへフォールバック。
    - 停止はプロジェクト直下の data/stop_requested.flag により行う。
    - 監視は KABUSYS_ENV に関わらず本番の sqlite_path を使用（設計上の注意点）。
- 設定管理
  - config.py: .env 自動読み込み機能、.env 行パーサー（クォート対応、export 形式対応）、Settings クラスを実装。
    - 自動ロード順: OS 環境 > .env.local > .env（プロジェクトルートの探索は .git または pyproject.toml を起点）。
    - 必須環境変数は _require() によって未設定時に ValueError を発生させる。
    - 各種プロパティ（duckdb_path, sqlite_path, paper_sqlite_path, pid_file_path, kill_flag_path, CPU/MEM/DISK 閾値など）を提供。
    - PAPER_FILL_MODE、KABUSYS_ENV、LOG_LEVEL の値検証を実装。
- 設定補助 CLI
  - config_setup.py: 対話式 .env 作成/更新ウィザードを追加（既存値の読み取り、シークレットマスク、保存確認を実装）。
  - validate_config.py: 起動前チェック用 CLI を追加（必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL 検証、DB パス / config/*.yaml 存在チェック、live 環境向けガードなど）。
    - --strict オプションで警告も失敗扱い（exit 1）にできる。
- ロギング / プロセス管理ユーティリティ
  - utils/logging_setup.py:
    - ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（日次・30日保持）を設定するユーティリティを追加。
    - ログディレクトリ作成に失敗した場合はファイル出力をスキップしてコンソール出力のみで継続する。
    - ログレベルは引数 > 環境変数 LOG_LEVEL > デフォルト "INFO" の順で解決。
  - utils/process_priority.py:
    - psutil を用いたプロセス優先度（Windows の priority class / POSIX の nice）と CPU affinity 設定関数を追加。
    - 権限不足や未対応 OS の場合は警告を出してスキップする安全実装。
- ポートフォリオ構築（純粋関数）
  - portfolio/portfolio_builder.py:
    - select_candidates, calc_equal_weights, calc_score_weights を追加（スコア加重時に全銘柄スコアが 0 のときは等配分にフォールバック）。
  - portfolio/risk_adjustment.py:
    - apply_sector_cap（セクター集中上限による候補除外）を追加。unknown セクターは除外対象外にする挙動。
    - calc_regime_multiplier（市場レジームに応じた投下資金乗数）を追加。既知のレジームに対する値を定義し、未知レジームは 1.0 でフォールバックして警告を出す。
    - apply_sector_cap 内に将来的な価格フォールバックについての TODO コメントを残しています（価格欠損時の過少見積もりに注意）。
  - portfolio/position_sizing.py:
    - calc_position_sizes を追加（risk_based / equal / score の割当方式をサポート）。
    - 単元株（lot_size）で丸め、per-position 上限・全体利用可能現金によるスケールダウン、cost_buffer による保守的見積り、残差分を fractional remainder に基づき追加配分するアルゴリズムを実装。
    - 価格欠損時は該当銘柄をスキップする挙動。
- 解析・研究ユーティリティ
  - research/factor_research.py: ファクター計算モジュールの骨格を追加（Momentum, Value, Volatility, Liquidity 設計方針、calc_momentum の実装開始を含む）。DuckDB を想定した設計。
- Paper Trading 検証ツール
  - tools/paper_verification_report.py:
    - Paper Trading 用 SQLite（PAPER_TRADING_SQLITE_PATH 指定可）から各種指標（稼働率、注文成功率、送信率、レイテンシ P95 等）を集計してレポートを出力するツールを追加。
    - デフォルトの閾値（稼働率 99%、注文成功率 90%、送信率 95%、P95 レイテンシ 200ms）を設定し、PASS/FAIL 判定を行う。
    - 日付フィルタ（--from/--to）に対応し、P95 は独自関数で計算。
- DB 初期化・監視テーブル
  - monitoring/monitoring_db:init_monitoring_db を起動スクリプトから呼び出して監視テーブル存在を保証（冪等）。
- duckdb 統合
  - run_execution/run_monitoring や research 等で DuckDB を利用するための接続処理を追加（設定は Settings.duckdb_path）。

Changed
- N/A（初回リリースのため改修履歴なし）。

Fixed
- ログディレクトリ作成や .env 読み込み失敗時にプロセスが致命的に停止しないよう、安全にフォールバックする処理を追加。
- process_priority / set_cpu_affinity は権限やプラットフォームの違いを捕捉して警告を出し、処理を継続するように変更（実装当初からの安全設計）。

Security
- .env の取り扱いに関して注意書きを config_setup.py に追加（.env を絶対に Git にコミットしない旨）。

Notes / Known limitations
- run_monitoring は「監視は KABUSYS_ENV に関わらず本番 sqlite_path を使用する」仕様です。テスト環境で分離が必要な場合は設定や実行方法に注意してください。
- apply_sector_cap は price_map に価格が欠損（0.0）するとエクスポージャーが過少見積もりになり得る点がコメントで明示されています（将来的にフォールバック価格実装を検討）。
- process_priority の変更は OS 権限に依存します。権限不足時は設定がスキップされます（警告出力）。
- research/factor_research.py の実装はモジュール設計を含む段階で、一部未完の関数が存在します（今後の拡張予定）。

Files (主な追加ファイル)
- src/kabusys/__init__.py
- src/kabusys/config.py
- src/kabusys/config_setup.py
- src/kabusys/validate_config.py
- src/kabusys/run_execution.py
- src/kabusys/run_monitoring.py
- src/kabusys/utils/logging_setup.py
- src/kabusys/utils/process_priority.py
- src/kabusys/portfolio/*.py
- src/kabusys/research/factor_research.py
- src/kabusys/tools/paper_verification_report.py

貢献・報告
- バグ・改善要望・セキュリティ問題は issue を作成してください。
- 設計上の注意点や TODO は各ソース内コメントにも記載しています（将来的な改善点の手掛かりとして参照してください）。