CHANGELOG
=========

すべての注目すべき変更はここに記録します。本ファイルは "Keep a Changelog" の形式に準拠します。
バージョンはセマンティックバージョニングに従います。

[Unreleased]
------------

- なし

[0.1.0] - 2026-04-17
--------------------

Added
- 初回リリース。KabuSys の以下の主要コンポーネントを追加。
  - 実行エンジン起動スクリプト
    - src/kabusys/run_execution.py
    - ExecutionEngine をデーモンスレッドで起動・監視する CLI ラッパ。
    - KABUSYS_ENV=paper_trading の場合は専用の paper_trading SQLite（デフォルト: data/paper_trading.db）を使用して本番 DB と分離。
    - BrokerClientFactory により環境に応じたブローカークライアントを生成。
    - OrderRepository / OrderManager / RiskManager / Reconciler を組み立て、EngineConfig(target_date=date.today()) でセッションを実行。
    - 停止フラグ (data/stop_requested.flag) と PID ファイル (data/execution.pid) を扱う。
    - RiskManager のデフォルトパラメータ（例: max_position_pct=0.20, max_utilization=0.80, rate_limit_per_sec=5, circuit_breaker_errors=10, circuit_breaker_window_sec=60, max_drawdown=0.20）を用意し、初期ポートフォリオ値に broker.get_available_cash() を使用。

  - 監視ポーリング起動スクリプト
    - src/kabusys/run_monitoring.py
    - SystemMonitor を定期実行するポーリングループを提供。
    - 環境変数 MONITOR_POLL_INTERVAL によりポーリング間隔を上書き（デフォルト 60 秒、0 以下は無視してデフォルトにフォールバック）。
    - 監視は KABUSYS_ENV にかかわらず本番用 sqlite_path（デフォルト: data/monitoring.db）を使用する仕様。
    - 停止フラグ (data/stop_requested.flag) を検知して正常終了。

  - 設定管理モジュール
    - src/kabusys/config.py
    - .env 自動読み込み（プロジェクトルートを .git または pyproject.toml から検出）を実装。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - 複数の環境変数プロパティを提供（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、KABU_API_BASE_URL、LINE_*、DUCKDB_PATH、SQLITE_PATH、PAPER_FILL_MODE、PAPER_TRADING_SQLITE_PATH、PID_FILE_PATH、KILL_FLAG_PATH、各種しきい値、KABUSYS_ENV、LOG_LEVEL 等）。
    - PAPER_FILL_MODE に対する検証（"instant" | "partial" | "never" | "reject"）を実装。
    - KABUSYS_ENV / LOG_LEVEL の検証と is_live / is_paper / is_dev のユーティリティプロパティを提供。

  - 設定検証 CLI
    - src/kabusys/validate_config.py
    - .env および config/*.yaml の存在や基本整合性をチェックするコマンドラインツール。
    - 必須環境変数の未設定チェック、プレースホルダ値の警告、KABUSYS_ENV の妥当性チェック、DB パスの親ディレクトリ存在チェック、PyYAML による YAML パース検証（インストールされていない場合は警告）など。
    - --strict を指定すると警告も失敗として exit(1) を返す。

  - 設定ウィザード CLI
    - src/kabusys/config_setup.py
    - インタラクティブに .env を作成／更新するウィザードを提供。
    - 入力項目定義（KABUSYS_ENV, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL, DUCKDB_PATH, SQLITE_PATH, LINE_* , LOG_LEVEL, KILL_FLAG_CLEAR_ON_START など）と既存 .env の読み込み・書き込み機能を実装。
    - シークレット項目は入力時にマスク表示。保存確認プロンプトあり。
    - .env を生成する際にファイル先頭に注意書きを付与（.env を Git にコミットしない旨）。

  - ポートフォリオ構築ライブラリ
    - src/kabusys/portfolio/*
    - portfolio_builder.py
      - select_candidates: BUY シグナルをスコア降順＋signal_rank タイブレークで選抜。
      - calc_equal_weights / calc_score_weights: 等金額配分とスコア配分（全スコアが 0 の場合は等金額にフォールバック）。
    - risk_adjustment.py
      - apply_sector_cap: セクター集中制限（max_sector_pct）を適用、"unknown" セクターは制限対象外。
      - calc_regime_multiplier: market_regime に基づく投下資金乗数（"bull":1.0, "neutral":0.7, "bear":0.3、未知値は警告して 1.0 にフォールバック）。
    - position_sizing.py
      - calc_position_sizes: allocation_method("risk_based" / "equal" / "score") に応じた株数算出、lot_size 単位で丸め、per-position と aggregate の上限（max_position_pct, max_utilization）を適用。
      - available_cash に対するスケールダウン処理、cost_buffer を用いた保守的なコスト見積り、残差に基づく追加配分ロジックを含む。

  - 解析／研究モジュール（DuckDB ベース）
    - src/kabusys/research/factor_research.py
    - prices_daily / raw_financials を参照してモメンタム・ボラティリティ等のファクターを計算する関数を実装（calc_momentum, calc_volatility 等）。P95 計算やウィンドウ不足時の None 戻りを考慮。

  - ユーティリティ
    - src/kabusys/utils/process_priority.py
      - set_process_priority(level): psutil を用いて Windows / POSIX に跨る優先度設定を提供。未対応 OS は警告してスキップ。
      - set_cpu_affinity(cpu_count): プロセスの CPU affinity 固定（対応 OS のみ）。例外時は警告してスキップ。

  - ツール
    - src/kabusys/tools/paper_verification_report.py
      - Paper Trading 用の検証レポート生成ツール。デフォルト DB は data/paper_trading.db。期間指定 --from / --to、--db オプション対応。
      - 稼働率、注文成功率、送信率、P95 レイテンシなどを算出し、基準値（稼働率 >=99%、成功率 >=90%、送信率 >=95%、P95 <=200ms）との比較で PASS/FAIL 判定を出力。

  - パッケージ定義
    - src/kabusys/__init__.py に __version__ = "0.1.0" を設定し、主要サブパッケージをエクスポート。

Changed
- n/a（初回リリースのため過去からの変更はなし）

Fixed
- n/a（初回リリース）

Security
- .env に関する注意喚起をドキュメント化（config_setup.py のヘッダ）。機密情報を Git にコミットしないことを明示。

Notes / Implementation Details
- .env のパースはクォート・エスケープ・インラインコメントの扱いを考慮して実装されているため、シンプルな export 形式やクォートを含む値にも対応。
- 自動ロード時に OS 環境変数は保護され、.env.local は .env より優先して上書き可能（ただし既存の OS 環境変数は上書きされない）。
- run_monitoring は例外発生時でもループを継続して次のポーリングを試みる設計（監視の頑健性を考慮）。
- run_execution/run_monitoring ともにプロセス優先度を起動時に "high" に設定する呼び出しを行う（権限不足時は警告して継続）。

将来の改善案（メモ）
- position_sizing: 銘柄ごとの lot_size を stocks マスタから取得できるよう拡張する。
- risk_adjustment.apply_sector_cap: price の欠損時のフォールバックロジック（前日終値や取得原価）を追加してエクスポージャー見積りの精度を向上させる。
- validate_config: 更に詳細な YAML スキーマ検証や、config ファイルの雛形生成オプションを追加する。
- テストカバレッジの拡充（特にファイル I/O／DB 周り、数値計算ロジック）。

----- 

注: この CHANGELOG は提供されたソースコードの内容から推測して作成しています。実際の変更履歴（コミット単位の差分や過去バージョンとの比較）はソース管理履歴（git 等）に基づいて作成することを推奨します。