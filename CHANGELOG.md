CHANGELOG
=========

すべての重要な変更は Keep a Changelog (https://keepachangelog.com/ja/1.0.0/) のフォーマットに従って記載しています。

Unreleased
----------
- （現時点の作業ブランチに未リリースの変更はありません）

0.1.0 - 2026-04-18
------------------

Added
-----
- 初回公開リリースを追加。
- 起動スクリプト:
  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。プロセス優先度を上げ、SQLite / DuckDB に接続してエンジンをデーモンスレッドで実行する。
    - KABUSYS_ENV=paper_trading のときは paper_trading 用の専用 SQLite（デフォルト: data/paper_trading.db）を使用し、本番 DB と分離する。
    - 起動前に停止フラグ (data/stop_requested.flag) をチェックし、既に立っていれば起動を中止する。
    - 実行中は停止フラグ検知で安全にエンジン停止を試みる。
  - run_monitoring.py
    - SystemMonitor をポーリングする監視ループスクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番 sqlite_path を使用する設計。
    - 停止フラグ (data/stop_requested.flag) による終了処理を実装。
- 設定・環境管理:
  - config.py
    - .env 自動読み込み機構を実装（プロジェクトルートを .git または pyproject.toml から検出）。
    - .env パーサーは export プレフィックス・クォート・エスケープ・インラインコメントなどに対応。
    - Settings クラスを提供し、主要な設定項目（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、DUCKDB_PATH、SQLITE_PATH、PAPER_TRADING_SQLITE_PATH、PAPER_FILL_MODE、KABUSYS_ENV、LOG_LEVEL 等）をプロパティ経由で取得できるようにした。
    - 環境値のバリデーション（PAPER_FILL_MODE の有効値チェック、KABUSYS_ENV/LOG_LEVEL の検証など）を組み込んだ。
  - config_setup.py
    - .env 作成/更新の対話式ウィザードを追加。既存 .env の読み込みと既存値の再利用、秘密値のマスク表示に対応。
  - validate_config.py
    - 起動前チェック用 CLI を追加。必須環境変数やファイルパス、config/*.yaml の存在・YAML パース（PyYAML があれば）を検査。--strict オプションで警告も失敗扱いにできる。
- ポートフォリオ構築（純粋関数群）:
  - portfolio/portfolio_builder.py
    - 候補選定 (select_candidates)、等重み (calc_equal_weights)、スコア重み (calc_score_weights) を追加。score が全て 0 の場合は等重みへフォールバック。
  - portfolio/risk_adjustment.py
    - セクター集中制限を適用する apply_sector_cap と、市場レジームに応じた投下資金乗数 calc_regime_multiplier を追加。未知レジーム時は 1.0 にフォールバックし警告を出力する。
  - portfolio/position_sizing.py
    - ポジションサイズ計算 calc_position_sizes を追加。risk_based / equal / score の allocation_method に対応し、lot_size 切り上げ/切り捨て、aggregate cap によるスケールダウン、cost_buffer を用いた保守的見積り、残差分の追加配分ロジックを実装。
- ユーティリティ:
  - utils/logging_setup.py
    - 共通ロギング初期化関数 setup_logging を追加。stdout への StreamHandler と日次ローテーションの TimedRotatingFileHandler（logs/<app_name>.log、30日保持）を設定。LOG_LEVEL/LOG_DIR 環境変数を尊重。
  - utils/process_priority.py
    - プロセス優先度設定（set_process_priority）と CPU affinity 設定（set_cpu_affinity）を追加。Windows と POSIX (Linux, macOS, FreeBSD) を吸収する実装。権限不足等のケースは警告を出してスキップ。
- ツール:
  - tools/paper_verification_report.py
    - ペーパートレード結果の検証レポート生成ツールを追加。system_status / trade_logs / risk_logs を集計し、稼働率・注文成功率・送信率・P95 レイテンシ等を計算して PASS/FAIL を判定する。
    - デフォルト閾値: 稼働率>=99%、注文成功率>=90%、送信率>=95%、P95<=200 ms。
    - 日付フィルタ (--from, --to) と DB パス (--db) をサポート。
- 研究用:
  - research/factor_research.py（部分実装）
    - DuckDB 接続を受け、価格データからモメンタム等のファクターを計算する設計を追加（calc_momentum 等の骨組み）。
- パッケージメタ:
  - __init__.py にバージョン __version__ = "0.1.0" を追加。

Changed
-------
- （初回リリースのため、過去バージョンからの変更点はありません）

Fixed
-----
- （初回リリースのため既知の修正履歴はありません）
  - ただし実行時にファイル/ディレクトリ作成に失敗した場合（ログディレクトリなど）はフォールバックして継続する設計になっています。

Notes / 使用上の注意
-------------------
- 環境変数自動ロード:
  - デフォルトでプロジェクトルートの .env（および .env.local）を自動でロードします。自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
  - .env の上書き挙動: OS 環境変数は保護され、.env.local は .env を上書きします（ただし既存の OS 環境変数は保護されます）。
- 重要な環境変数:
  - JQUANTS_REFRESH_TOKEN（必須）
  - KABU_API_PASSWORD（必須）
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
  - PAPER_FILL_MODE: instant | partial | never | reject（paper_trading 用、デフォルト: instant）
  - DUCKDB_PATH / SQLITE_PATH / PAPER_TRADING_SQLITE_PATH（DB ファイルパス）
  - LOG_LEVEL / LOG_DIR
  - MONITOR_POLL_INTERVAL（監視ポーリング秒数、デフォルト 60）
  - KILL_FLAG_CLEAR_ON_START（本番運用時の注意フラグ）
- Paper trading と本番 DB の分離:
  - paper_trading モードでは paper_sqlite_path（デフォルト data/paper_trading.db）を使用し、本番の monitoring DB とデータを隔離します。
- 停止制御:
  - 起動スクリプトは data/stop_requested.flag（プロジェクトルート下）を監視して安全に停止します。ExecutionEngine 用に data/execution.pid など PID ファイルを管理しています。
- ロギング:
  - stdout とファイル（logs/<app>.log）へ統一的に出力。ログディレクトリ作成に失敗した場合はコンソールのみで継続します。
- 設定検証:
  - validate_config.py で起動前に環境/設定ファイルの問題を検出できます。--strict を使うと警告もエラー扱いとなります。

将来の改善候補（未実装/TODO）
----------------------------
- position_sizing: 銘柄ごとの lot_size を stocks マスタから取得する拡張（現在は全銘柄共通 lot_size）。
- apply_sector_cap: 価格欠損時のフォールバック価格（前日終値や取得原価等）への対応。
- research/factor_research: calc_momentum 等の完全実装（現状一部実装/骨組み）。
- より詳細なエラーメトリクスの収集と運用向けドキュメント追加。

ライセンス / 著作権
------------------
- 本リポジトリのライセンス・著作権情報はリポジトリの LICENSE ファイルを参照してください。