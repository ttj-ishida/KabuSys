# Changelog

すべての注目すべき変更点はこのファイルに記録します。フォーマットは「Keep a Changelog」仕様に準拠しています。

## [0.1.0] - 2026-04-18

### Added
- 全体
  - 初期版リリース。パッケージ名: KabuSys (日本株自動売買システム)。
  - バージョン定義: `__version__ = "0.1.0"`。

- 起動スクリプト / デーモン
  - run_monitoring
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` によるポーリング間隔上書き（デフォルト 60 秒）。不正値は警告を出してデフォルトへフォールバック。
    - 監視は KABUSYS_ENV にかかわらず本番用の `sqlite_path` を使用する設計。
    - 停止制御: プロジェクト内 `data/stop_requested.flag` を監視し、存在でループを終了。
    - 起動時にプロセス優先度を "high" に設定。
    - SQLite / DuckDB 接続の初期化とクローズを実装。

  - run_execution
    - ExecutionEngine 起動スクリプトを追加。
    - `KABUSYS_ENV=paper_trading` の場合は Mock ブローカーを使用し、paper_trading 専用 DB (`PAPER_TRADING_SQLITE_PATH` / デフォルト `data/paper_trading.db`) に記録して本番 DB と完全分離。
    - 停止フラグ (`data/stop_requested.flag`) を検知して安全停止、PID ファイル (`data/execution.pid`) の扱いを実装。
    - 起動時にプロセス優先度を "high" に設定。
    - ブローカークライアントの生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て、ExecutionEngine の起動を行う。

- 設定管理
  - config
    - 環境変数読み込みユーティリティを提供。
    - プロジェクトルート自動検出ロジック（`.git` または `pyproject.toml` を基準）により `.env` / `.env.local` を自動で読み込む（`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能）。
    - `.env` のパースはクォートやエスケープ、インラインコメント等に対応。
    - Settings クラスでアプリ設定をプロパティ経由で取得:
      - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD（必須）
      - KABUSYS_ENV（`development`/`paper_trading`/`live` 検証）
      - DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH
      - PID / kill flag パス、しきい値（CPU/Memory/Disk）
      - PAPER_FILL_MODE（`instant`/`partial`/`never`/`reject` 検証）
      - その他ログレベル判定、is_live/is_paper/is_dev ユーティリティ

  - config_setup
    - 対話式ウィザードで `.env` を初期作成・更新する CLI を追加。
    - J-Quants / kabuステーション / データベース / LINE 通知 / ログ設定 / Kill Switch の主要項目を対話入力で設定可能。
    - 既存 `.env` の読み込み・マスク表示・デフォルト利用・確認プロンプトを実装。
    - `.env` 書き込みフォーマットと注意書きを出力（Git にコミットしない旨）。

  - validate_config
    - 起動前の設定検証 CLI を追加。
    - 必須環境変数の有無チェック、KABUSYS_ENV 値チェック、LOG_LEVEL の検証、DB パスの親ディレクトリ存在チェック、`config/*.yaml` の存在・パースチェック（PyYAML 有無で挙動切替）、本番時の追加ガード（LINE 未設定や KILL_FLAG_CLEAR_ON_START の危険設定の警告）を実装。
    - `--strict` オプションで警告も失敗扱いにできる。

- ログ / プロセス管理ユーティリティ
  - logging_setup
    - ルートロガーに対して stdout 出力用 StreamHandler と日次ローテートの TimedRotatingFileHandler を設定するユーティリティを追加。
    - ログディレクトリ自動作成（失敗時はファイル出力をスキップして stdout のみ継続）。
    - ログローテーション: 日次、30世代保存。
    - ログレベル解決順: 引数 > 環境変数 LOG_LEVEL > デフォルト。
    - ログディレクトリ解決順: 引数 > 環境変数 LOG_DIR > デフォルト "logs/"。
    - ハンドラの二重登録防止（既存ハンドラをクリア）。

  - process_priority
    - Windows / POSIX（Linux, macOS, FreeBSD 等）差分を吸収してプロセス優先度（nice / Windows priority class）や CPU affinity を設定するユーティリティを追加。
    - set_process_priority("high"|"normal"|"low") により優先度を設定。権限不足や未対応 OS の場合は警告を出してスキップ。
    - set_cpu_affinity(cpu_count) でプロセスを最初の N コアに固定（権限不足時は警告を出してスキップ）。

- ポートフォリオ構築ライブラリ（純粋関数群、DB 非依存）
  - portfolio.portfolio_builder
    - select_candidates: スコア降順・タイブレークに signal_rank を用いた候補選定。
    - calc_equal_weights: 等金額配分。
    - calc_score_weights: スコア正規化配分（全スコアが 0 の場合は等金額へフォールバックし警告）。

  - portfolio.risk_adjustment
    - apply_sector_cap: セクター別エクスポージャーが上限を超える場合に当該セクターの新規候補を除外（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: 市場レジーム ("bull"/"neutral"/"bear") に基づく投下資金乗数を返す。未知のレジームは 1.0 にフォールバック（警告）。

  - portfolio.position_sizing
    - calc_position_sizes: 重み・候補・リスクパラメータに基づき発注株数を算出する純粋関数。
      - allocation_method: "risk_based" / "equal" / "score" をサポート。
      - risk_based: リスク % と損切り率からポジションサイズを算出。
      - 等分配系: weight に基づく算出。単元株（lot_size）で丸め。
      - per-position 上限（max_position_pct）と aggregate cap（available_cash）を考慮し、必要に応じてスケーリングと残余の優先配分ロジック（fractional remainder）を実装。
      - cost_buffer により手数料・スリッページを保守的に見積もる。

- 解析 / ツール
  - tools.paper_verification_report
    - ペーパートレード結果を SQLite DB（デフォルト `data/paper_trading.db`）から集計して検証レポートを生成する CLI を追加。
    - 指標: 稼働率 (uptime)、注文成功率 (fill rate)、送信率 (send rate)、P95 レイテンシ、リスク却下数 など。
    - 基準値による PASS/FAIL 判定（デフォルト閾値をソース内で定義。例: 稼働率 >= 99%、Fill >= 90%、Send >= 95%、P95 <= 200 ms）。
    - 日付フィルタ（--from / --to）、DB パス指定（--db または環境変数 PAPER_TRADING_SQLITE_PATH）をサポート。
    - P95 は単純パーセンタイル計算で実装。データ不足時は N/A を表示。

- リサーチ / ファクター計算
  - research.factor_research（計算フレームワーク）
    - DuckDB 接続を受け prices_daily / raw_financials を利用して各種ファクター（Momentum / Value / Volatility / Liquidity）を計算する設計。モメンタム計算のインターフェースおよび定数を導入（例: 1M/3M/6M、MA200、ATR20 等）。
    - 設計方針として外部 API に依存せず DuckDB + SQL/Python で完結することを明記。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- 環境変数取り扱い上の注意をドキュメント内に明記（.env を絶対にリポジトリにコミットしない等）。

---

注記:
- stop_flag / kill_flag / PID ファイルのパスや起動オプションは Settings および各スクリプトで環境変数経由でカスタマイズ可能です（例: PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START）。
- Paper Trading と Live の DB は明確に分離される設計（paper_trading は専用 SQLite を使用）で、安全にオフライン検証が行えるようになっています。
- 本 CHANGELOG はコード構成とコメント/実装から推測して作成しています。運用ルールや README の記載内容に合わせて適宜編集してください。