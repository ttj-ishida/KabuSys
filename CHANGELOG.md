# CHANGELOG

すべての変更は Keep a Changelog の形式に準拠します。主要なリリース履歴をコードベースから推測して日本語でまとめています。

全体方針: 初回リリースとして、環境設定・検証・起動スクリプト、ログ/プロセスユーティリティ、ポートフォリオ構築（純粋関数群）、ポジションサイズ計算、ペーパートレーディング検証ツール、リサーチ用ファクター計算の基盤等を実装しています。

## [Unreleased]
- （なし）

## [0.1.0] - 2026-04-19
初回リリース。システム全体の基盤機能を実装。

### Added
- 環境設定 / 管理
  - kabusys.config
    - .env 自動読み込み機能（プロジェクトルート検出: .git または pyproject.toml を基準）。
    - .env/.env.local の読み込み順序と OS 環境変数保護（上書き制御）。
    - 行パーサーは export 形式、引用文字列、インラインコメント、エスケープを考慮して堅牢に解析。
    - Settings クラスを提供し、各種環境変数へのアクセス（J-Quants、kabuAPI、DB パス、監視閾値、実行環境フラグ等）をプロパティで取得。
    - PAPER_FILL_MODE の検証（instant/partial/never/reject）と各種閾値のデフォルト設定。
  - kabusys.config_setup
    - 対話式 .env ウィザード。既存 .env 読み込み、入力プロンプト、シークレットマスク表示、.env ファイル書き出し機能。
    - 提供項目例: KABUSYS_ENV, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DUCKDB_PATH, SQLITE_PATH, LINE トークン等。

- 設定検証ツール
  - kabusys.validate_config
    - CLI による事前チェック。必須環境変数、KABUSYS_ENV/LOG_LEVEL の妥当性、DB パスの存在確認（親ディレクトリ）、config/*.yaml の存在・パース検証（PyYAML があればパースを実行）など。
    - --strict オプションで警告を FAIL 扱いにできる。

- 起動スクリプト / ランタイム
  - run_execution (kabusys.run_execution)
    - ExecutionEngine 起動スクリプト。
    - KABUSYS_ENV=paper_trading の場合、Paper 用の専用 SQLite（デフォルト: data/paper_trading.db）を使用して本番 DB とは分離。
    - BrokerClientFactory を用いたブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て、ExecutionEngine の起動・停止ループ（停止フラグ監視）。
    - プロセス優先度を高に設定して起動（set_process_priority("high")）。
    - PID ファイル管理と停止フラグ検出による安全停止。
  - run_monitoring (kabusys.run_monitoring)
    - SystemMonitor ポーリングループ起動スクリプト。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値は警告してデフォルトにフォールバック。
    - 監視 DB 初期化（monitoring_db.init_monitoring_db）を実行。Monitoring は環境に関わらず本番 sqlite_path を使用する設計。
    - duckdb 接続を併用、プロセス優先度設定、停止フラグ検知でループ終了。例外はログ出力して次のポーリングへ継続。

- ポートフォリオ構築（純粋関数群、DB 未参照）
  - kabusys.portfolio.portfolio_builder
    - select_candidates: BUY シグナルのスコア降順ソート（同点時に signal_rank）で上位 N を選択。
    - calc_equal_weights: 等金額配分の重み計算。
    - calc_score_weights: スコア加重配分。全スコアが 0 の場合は等金額配分にフォールバック（警告）。
  - kabusys.portfolio.risk_adjustment
    - apply_sector_cap: セクター毎の既存エクスポージャー計算と上限超過セクターの除外（unknown セクターは除外対象外）。sell_codes を除外して計算。
    - calc_regime_multiplier: market regime に応じた投下資金乗数（bull:1.0, neutral:0.7, bear:0.3）。未知レジームは警告して 1.0 にフォールバック。
  - kabusys.portfolio.position_sizing
    - calc_position_sizes: allocation_method ("risk_based" / "equal" / "score") に基づく株数算出。
    - risk_based: risk_pct / stop_loss_pct に基づくリスクベース算出。
    - equal/score: ウェイトに基づく資金配分、個別上限(max_position_pct)考慮。
    - lot_size（単元）で丸め、aggregate cap（available_cash）超過時にはスケールダウンし、余剰キャッシュで端数調整する再配分ロジックを実装。
    - cost_buffer による保守的コスト推定をサポート。
    - 価格欠損時はスキップする挙動（ログ出力）。

- ロギング / プロセスユーティリティ
  - kabusys.utils.logging_setup
    - setup_logging(): ルートロガーに StreamHandler (stdout) と TimedRotatingFileHandler（日次ローテート、30日保持）を設定。LOG_DIR / LOG_LEVEL の解決順を実装。既存ハンドラはリセット。
    - ファイルハンドラ作成失敗時はコンソールのみで継続。
  - kabusys.utils.process_priority
    - set_process_priority(level): Windows と POSIX の差分を吸収して優先度 / nice 値を設定。失敗時は警告してスキップ。
    - set_cpu_affinity(cpu_count): カレントプロセスの CPU affinity を最初の N コアに固定。失敗時は警告してスキップ。

- 監視・モニタリング基盤（起動スクリプトが利用）
  - monitoring_db 初期化呼び出し場所の追加（起動時に監視テーブルを冪等に初期化）。

- ツール
  - kabusys.tools.paper_verification_report
    - Paper Trading の検証レポート生成 CLI。
    - 日付範囲指定 (--from/--to) と DB パス指定 (--db / PAPER_TRADING_SQLITE_PATH)。
    - 指標: 稼働率（uptime_pct）、注文成功率（fill_rate）、送信率（send_rate）、P95 レイテンシ、リスク却下数等を集計。
    - 判定基準（デフォルト）: 稼働率 >= 99%、成立率 >= 90%、送信率 >= 95%、P95 <= 200 ms。結果を PASS/FAIL で出力。
    - sqlite のテーブル欠如に対しては安全に N/A を返す実装。

- リサーチ基盤（ファクター）
  - kabusys.research.factor_research（基盤実装）
    - モメンタム、MA200、ATR、出来高などのファクター計算方針と各種定数を定義。
    - DuckDB 接続を受け取り prices_daily / raw_financials を参照して計算する設計（外部 API にはアクセスしない）。
    - （calc_momentum の実装開始が見られる。完全実装は継続の可能性あり）

### Changed
- N/A（初回リリース）

### Fixed
- N/A（初回リリース）

### Notes / Known limitations
- apply_sector_cap の価格欠損（price_map が 0.0）によりエクスポージャーが過少見積りされる可能性がある旨を TODO コメントで記載。将来、前日終値や取得原価などのフォールバックを検討。
- position_sizing: 現状 lot_size はグローバル固定（例: 100）。将来は銘柄別 lot_size を扱う拡張が予定。
- factor_research の一部関数（例: calc_momentum）がファイル末尾で途切れており、完全実装が必要な箇所が存在する可能性あり。
- monitoring の実装は起動スクリプトで参照されるが、SystemMonitor の詳細な挙動・テーブル定義は別モジュールに依存（ここでは起動/初期化フローのみ記載）。

---

作成された CHANGELOG はコードベースの公開時に README と合わせて配布してください。将来の変更はこの形式で追記してください。