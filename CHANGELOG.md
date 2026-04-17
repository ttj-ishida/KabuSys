CHANGELOG
=========

すべての重要な変更を記録します。フォーマットは "Keep a Changelog" に準拠しています。

[0.1.0] - 2026-04-17
--------------------

Added
- 初期リリース（バージョン情報: __version__ = "0.1.0"）。
- 実行用スクリプトを追加:
  - run_execution.py: ExecutionEngine を起動するエントリポイントを実装。KABUSYS_ENV=paper_trading の場合は paper_trading 用の SQLite を分離して使用し、BrokerClientFactory を用いてブローカークライアントを生成、ExecutionEngine をスレッドで実行・停止制御する。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを実装。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能。監視は環境にかかわらず本番 sqlite_path を使用し、監視 DB の初期化を行う。
- 環境設定関連 CLI を追加:
  - config_setup.py: .env ファイルの対話式ウィザード（作成・更新）を実装。デフォルト/既存値の再利用、シークレットマスク表示、.env 出力テンプレートを提供。
  - validate_config.py: 起動前の設定検証ツールを実装。必須環境変数 / KABUSYS_ENV / LOG_LEVEL / DB パス / config/*.yaml の基本チェック、--strict オプションで警告を失敗扱いにできる。
- 設定管理モジュールを追加:
  - config.py: .env の自動読み込み（.env, .env.local）・カレントに依存しないプロジェクトルート検出(.git または pyproject.toml)・高度な .env パーサ（export プレフィックス、クォート + エスケープ、インラインコメントの扱い）・Settings クラス（各種環境変数の取得と検証）を実装。
  - Settings にて PAPER_FILL_MODE の検証、paper_sqlite_path / pid_path / kill_flag 関連設定、各種閾値設定（CPU/MEM/DISK）などを提供。
- ポートフォリオ構築関連（純粋関数群）を追加:
  - portfolio_builder.py: シグナル選定 (select_candidates)、等金額重み (calc_equal_weights)、スコア重み (calc_score_weights)。
  - risk_adjustment.py: セクター集中制限の適用 (apply_sector_cap)、市場レジームに基づく投下資金乗数 (calc_regime_multiplier)。
  - position_sizing.py: 各銘柄の株数算出 (calc_position_sizes)。risk_based / equal / score の配分方式、単元株丸め、per-stock 上限、aggregate cap（スケーリングと端数処理）を実装。
  - portfolio/__init__.py でパブリック API をエクスポート。
- ユーティリティを追加:
  - utils/process_priority.py: プロセス優先度設定と CPU affinity 設定ユーティリティ。Windows（psutil の priority constants）と POSIX 系（nice 値）を吸収し、未対応 OS や権限不足時は警告を出して安全にスキップする。
- リサーチモジュールを追加:
  - research/factor_research.py: DuckDB を使ったファクター計算（Momentum, Volatility/ATR, 流動性等）の実装。各種ウィンドウ長・スキャン範囲の定義と SQL 実装を提供。
- 検証ツールを追加:
  - tools/paper_verification_report.py: ペーパートレード用 SQLite を解析して稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）等を集計し、基準値との比較で PASS/FAIL を出力するレポート機能を実装。P95 計算および日付フィルタリングをサポート。
- 監視 DB 初期化呼び出し (monitoring_db.init_monitoring_db) を run_execution/run_monitoring の起動フローに組み込み（冪等に存在確認・テーブル生成を保証）。

Changed
- ログ・起動挙動:
  - run_execution/run_monitoring の起動時にプロセス優先度を "high" に設定する呼び出しを追加（set_process_priority("high")）。
  - run_monitoring では例外発生時にループを継続する（check_once() の例外捕捉と logger.exception）。
- DB パスの取り扱い:
  - run_execution は paper_trading 環境時に paper_sqlite_path を優先して使用するよう変更（本番 DB と完全分離）。
  - duckdb を分析用 DB として統合し、各処理で接続を確立してクローズするように統一。

Fixed
- .env 読み込みの堅牢化:
  - config._parse_env_line で export プレフィックス、クォート内バックスラッシュエスケープ、クォートなし時のインラインコメント判定（先行の空白/タブがある場合のみ）を正しく処理するよう改善。これにより .env の多様な記法に対応。
- position_sizing の端数処理と aggregate cap のロジックを堅牢化。残余キャッシュを利用して lot_size 単位で追加配分するアルゴリズムを採用し、再現性のためソートを安定化。

Security
- .env の取り扱いで注意喚起を追加（config_setup にて .env を絶対に Git にコミットしない旨を明記）。

Notes / Implementation details
- validate_config は PyYAML の有無を検出し、未インストール時は YAML 内容検証をスキップして警告を出す。
- run_monitoring/run_execution はプロセス停止制御のためプロジェクト下 data/stop_requested.flag を監視する（停止フラグ検出で安全に終了）。
- run_execution は ExecutionEngine をデーモン化したスレッドで実行し、停止フラグ検出時に engine.stop() を呼んでシャットダウンする。
- calc_regime_multiplier は未知のレジーム値に対してデフォルト 1.0 でフォールバックし警告を出す。
- process_priority と set_cpu_affinity は権限不足や未対応 API の例外を安全にハンドリングし、操作に失敗した場合は警告を出して続行する。

今後の改善案（未実装 / TODO）
- position_sizing: 銘柄ごとの lot_size を stocks マスタに持たせる拡張（現在は全銘柄共通の lot_size）。
- risk_adjustment.apply_sector_cap: price 欠損時のフォールバック価格（前日終値や取得原価）を使う改善。
- factor_research: 追加ファクターや正規化ユーティリティの統合（kabusys.data.stats などとの連携）。
- より細かいユニットテストとエンドツーエンドの検証スイート整備。

--- 

過去のリリースは存在しません（初期公開）。