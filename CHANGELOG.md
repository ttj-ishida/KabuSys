# CHANGELOG

すべての変更は [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) の規約に従って記載しています。

## [Unreleased]

## [0.1.0] - 2026-04-18
初回リリース。日本株自動売買システム「KabuSys」のコアユーティリティと実行/監視周りの実装を追加しました。

### Added
- 基本パッケージメタ情報
  - パッケージバージョンを `__version__ = "0.1.0"` として追加。

- 起動スクリプト
  - run_execution.py
    - ExecutionEngine を起動する CLI スクリプトを追加。
    - KABUSYS_ENV が `paper_trading` の場合、専用の Paper Trading 用 SQLite（既定: data/paper_trading.db）を使用して本番 DB と分離。
    - ブローカークライアント生成（BrokerClientFactory）、OrderRepository、OrderManager、RiskManager、Reconciler を組み立てて ExecutionEngine を起動。エンジンはデーモンスレッドで run_session を実行。
    - 停止フラグ（data/stop_requested.flag）検知時に安全に停止処理を行う。
    - 起動時にプロセス優先度を "high" に設定（utils.process_priority を使用）。
    - PID ファイル（data/execution.pid）管理と終了時の DB クローズ処理を実装。

  - run_monitoring.py
    - SystemMonitor のポーリングループを起動するスクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値は警告を出してデフォルトにフォールバック。
    - 監視は KABUSYS_ENV に関わらず本番用の sqlite_path を使用する設計（監視 DB は環境に依存しない運用想定）。
    - 停止フラグ検知と例外発生時のロギング、SQLite/DuckDB 接続のクリーンアップを実装。

- 設定管理・検証・ウィザード
  - config.py
    - .env ファイルや環境変数から設定を読み込む Settings クラスを実装。
    - プロジェクトルート検出ロジック（.git または pyproject.toml を基準）により、自動で .env/.env.local を読み込む（無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD あり）。
    - .env のパースは以下をサポート:
      - `export KEY=val` 形式
      - シングル/ダブルクォート内のエスケープシーケンス
      - クォートなしでのインラインコメント（直前が空白/タブの場合）
    - 必須環境変数チェック用のヘルパ (`_require`) と、各種環境変数の型/妥当性検証（KABUSYS_ENV、LOG_LEVEL、PAPER_FILL_MODE など）を提供。
    - SQLite/DuckDB のデフォルトパス、PID/kill フラグパス、監視閾値（CPU/MEM/DISK）などのプロパティを定義。

  - config_setup.py
    - 対話式ウィザードで `.env` を初期作成/更新する CLI を実装。選択肢・デフォルト表示、シークレット入力のマスク、保存前の確認をサポート。
    - 生成される .env のテンプレートと書式を定義（J-Quants、kabuAPI、LINE、DB、KILL スイッチなど）。

  - validate_config.py
    - 起動前に .env および config/*.yaml の不備を検出する検証 CLI を実装。
    - 必須/任意環境変数チェック、KABUSYS_ENV の妥当性、LOG_LEVEL の妥当性、DB パスの親ディレクトリ存在チェック、YAML ファイルの存在とパース（PyYAML がインストールされている場合）を行う。
    - `--strict` オプション: 警告を FAIL 扱いにする。
    - 本番環境（KABUSYS_ENV=live）向けの追加ガード（LINE 設定未指定や KILL_FLAG_CLEAR_ON_START の危険設定等）を実装。

- ロギング・プロセス管理ユーティリティ
  - utils/logging_setup.py
    - ルートロガーに対して統一的なログ設定関数 `setup_logging(app_name, log_dir, level)` を追加。
    - stdout（StreamHandler）および日次ローテートするファイルハンドラ（TimedRotatingFileHandler、デフォルト logs/<app_name>.log、30日保持）を設定。
    - ログディレクトリ作成に失敗した場合はファイル出力をスキップしてコンソールのみで継続するフォールバックを導入。
    - 既存ハンドラの二重登録防止のためクリアしてから再設定。

  - utils/process_priority.py
    - プラットフォーム差分を吸収するプロセス優先度設定ユーティリティを追加。
    - Windows/Posix (Linux, macOS, FreeBSD) 向けに `set_process_priority(level)` を提供（"high"|"normal"|"low"）。
    - CPU 固定用 `set_cpu_affinity(cpu_count)` を追加。
    - アクセス拒否や未実装ケースはログ警告でフォールバック。

- ポートフォリオ構築・ポジションサイズ計算
  - portfolio/portfolio_builder.py
    - 候補選定関数 `select_candidates`（スコア降順、同点時は signal_rank のタイブレーク）を実装。
    - 等金額配分 `calc_equal_weights` とスコア加重配分 `calc_score_weights` を実装（スコア合計が 0 の場合は等配分にフォールバックして警告）。

  - portfolio/risk_adjustment.py
    - セクター集中制限 `apply_sector_cap` を実装。既存保有のセクター別エクスポージャーを計算し、指定比率を超えるセクターの新規候補を除外する（"unknown" セクターは除外対象外）。
    - 市場レジームに応じた投下資金乗数 `calc_regime_multiplier` を実装（"bull"=1.0, "neutral"=0.7, "bear"=0.3、未定義レジームは警告して 1.0 でフォールバック）。
    - いくつかの実装上の注意点をコメントで明示（価格欠損のフォールバック、Bear レジームの挙動説明など）。

  - portfolio/position_sizing.py
    - ポジションサイズ算出 `calc_position_sizes` を実装。以下をサポート：
      - allocation_method: "risk_based" / "equal" / "score"
      - risk_based の場合はリスク許容率（risk_pct）と stop_loss_pct に基づく株数算出
      - 等配分/スコア配分では各銘柄の割当を算出し単元株（lot_size）で丸める
      - per-position cap（portfolio_value * max_position_pct）適用
      - aggregate cap：全銘柄合計が available_cash を超える場合はスケールダウンし、端数処理を lot_size 単位で再配分するアルゴリズムを実装（残差の大小で配分）
      - cost_buffer による保守的なコスト見積もりをサポート
    - 実装中の TODO コメント（将来的な lot_size 銘柄別対応など）を追加。

  - portfolio/__init__.py
    - 上記関数群をパッケージ API として公開。

- 実行・監視データベース初期化
  - monitoring/monitoring_db.py（参照インポートあり）
    - run_* スクリプトから呼び出して監視用テーブルが存在することを保証する初期化関数を利用（冪等にテーブルを作成する想定）。

- ペーパートレーディング検証ツール
  - tools/paper_verification_report.py
    - Paper Trading の検証用レポート生成 CLI を追加。
    - 検証指標:
      - 稼働率（uptime_pct、閾値 99.0%）
      - 注文成功率（fill_rate_pct、閾値 90.0%）
      - 送信率（send_rate_pct、閾値 95.0%）
      - API レイテンシ P95（閾値 200 ms）
      - リスク却下数（risk_logs）
    - P95 計算ユーティリティ、日付フィルタリング、DB 存在チェック、SQL クエリからの指標抽出を実装。
    - コマンドラインオプション `--from`, `--to`, `--db` をサポート。環境変数 `PAPER_TRADING_SQLITE_PATH` で DB を指定可能。

- データ解析 / 研究用基盤
  - research/factor_research.py
    - ファクター計算用モジュールの骨組みを追加（Momentum, Value, Volatility, Liquidity を想定）。
    - DuckDB 接続を受け prices_daily / raw_financials テーブルから計算する設計。モメンタム計算関数 calc_momentum() の実装開始（一部実装/未完の箇所あり）。研究用途向けの設計方針（外部 API を使用しないなど）を明示。

### Changed
- なし（初回リリース）

### Fixed
- なし（初回リリース）

### Deprecated
- なし

### Removed
- なし

### Security
- なし（初回リリース）

### Notes / Known issues / TODO
- research/factor_research.py は現状実装途中（ファイル末尾が途中で終わる箇所あり）。ファクター計算ロジックは追加実装・テストが必要です。
- position_sizing.py と risk_adjustment.py 内に将来の拡張を意図した TODO コメントが残っています（銘柄別 lot_size の導入、価格欠損時のフォールバックなど）。
- .env の自動読み込みはデフォルトで有効。テスト等で自動ロードを抑止したい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- run_monitoring は監視 DB に本番 sqlite_path を使用する設計です。監視 DB を別にしたい場合は設定やコードの調整が必要です。
- process_priority / cpu_affinity の設定は権限や OS に依存するため、設定に失敗した場合はログ警告でフォールバックします。

---

以上がこのリポジトリ（v0.1.0）に含まれる主要な変更点と注意点です。必要であれば各モジュールの API ドキュメント（使用例、引数説明、返り値）や移行手順の追記、未完成箇所の一覧（TODO）を別途作成します。どの情報がさらに必要か教えてください。