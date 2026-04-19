# Changelog

すべての変更は Keep a Changelog の形式に準拠して記載しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

## [Unreleased]

※ 現時点では未リリースの変更はありません。

## [0.1.0] - 2026-04-19

初回リリース。KabuSys のコアユーティリティ、起動スクリプト、ポートフォリオ構築ロジック、設定管理ツール、検証ツール、およびペーパートレード検証用レポート生成ツールを追加しました。

### Added
- 起動スクリプト
  - run_execution.py
    - ExecutionEngine を起動するメインスクリプトを追加。
    - KABUSYS_ENV が `paper_trading` の場合は専用の paper_trading DB（デフォルト: data/paper_trading.db）を使用し、本番 DB と完全分離。
    - BrokerClientFactory を利用して環境に応じたブローカークライアントを生成。
    - エンジンはデーモンスレッドで run_session を実行し、data/stop_requested.flag による停止制御、PID ファイル管理を実施。
    - RiskManager のデフォルト設定（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）を組み立て、initial_portfolio_value はブローカーから取得した利用可能現金を使用。
  - run_monitoring.py
    - SystemMonitor をポーリングで回す監視プロセス起動スクリプトを追加。
    - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で上書き可能（デフォルト 60 秒）、不正値は警告してデフォルトにフォールバック。
    - 監視は環境にかかわらず本番用 sqlite_path を使用する仕様（監視 DB の一元化）。
    - 停止フラグ（data/stop_requested.flag）の検出で安全にループ終了。

- 設定管理・検証ツール
  - config.py
    - プロジェクトルートの自動検出（.git または pyproject.toml を探索）に基づく .env 自動読み込み。
    - .env のパース機能を実装（export プレフィックス対応、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントの扱いなど）。
    - 設定値をプロパティで提供する Settings クラスを追加（DB パス、Paper Trading 設定、監視閾値、ログレベル、環境判定ユーティリティ等）。
    - PAPER_FILL_MODE の入力検証（instant/partial/never/reject）。
  - config_setup.py
    - 対話式ウィザードで .env を初期作成・更新する CLI を追加。
    - シークレット項目はマスク表示、既存 .env 取り込み、保存前確認を実装。
  - validate_config.py
    - .env と config/*.yaml の起動前チェック CLI を追加。
    - 必須環境変数の未設定チェック、KABUSYS_ENV や LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在チェック、YAML ファイルの存在およびパース検証（PyYAML がない場合は警告）を実装。
    - --strict オプションで警告を FAIL 扱いにできる。

- ロギング／プロセス管理ユーティリティ
  - utils/logging_setup.py
    - ルートロガーに StreamHandler (stdout) と TimedRotatingFileHandler（日次ローテーション、30 日保持）を設定する共通ユーティリティを追加。
    - 既存ハンドラの二重登録防止のためクリア処理を実施。ログディレクトリ作成に失敗した場合はファイル出力をスキップしてコンソールのみで継続。
    - ログレベル・ログディレクトリの解決順を明確化（引数 > 環境変数 > デフォルト）。
  - utils/process_priority.py
    - クロスプラットフォームでプロセス優先度（high/normal/low）と CPU affinity を設定するユーティリティを追加（psutil を使用）。
    - Windows と POSIX (Linux/Mac/FreeBSD) の差分吸収と、権限不足や未対応プラットフォーム時のフォールバックログを実装。

- ポートフォリオ構築およびリスク調整ロジック（純粋関数群）
  - portfolio/portfolio_builder.py
    - BUY シグナルのソート・候補選定（スコア降順、score 同値時は signal_rank 昇順）select_candidates を追加。
    - 等金額配分 calc_equal_weights とスコア加重配分 calc_score_weights（全スコア 0 の場合は等配分へフォールバック）を追加。
  - portfolio/risk_adjustment.py
    - セクター集中制限 apply_sector_cap（既存ポジションのセクター曝露を計算し、上限を越えるセクターの候補を除外）を追加。unknown セクターは制限の対象外。
    - 市場レジームに応じた乗数 calc_regime_multiplier（bull/neutral/bear をマップ、未知レジームは 1.0 にフォールバック）を追加。
  - portfolio/position_sizing.py
    - allocation_method（risk_based / equal / score）に基づき発注株数を算出する calc_position_sizes を実装。
    - 単元株（lot_size）丸め、銘柄毎上限（max_position_pct）、aggregate cap（available_cash を超える場合のスケールダウン）、cost_buffer による保守的見積り、端数配分ロジック（lot 単位で残差が大きい順に配分）を実装。

- Paper Trading 検証ツール
  - tools/paper_verification_report.py
    - ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）から検証指標を集計し、人間向けレポートを出力するスクリプトを追加。
    - 指標: 稼働率（uptime）、注文成功率（fill rate）、送信率（send rate）、リスク却下数、API レイテンシ（avg/max/P95）。
    - P95 計算、期間フィルタ（--from, --to）、データ存在チェック、しきい値（稼働率 >= 99%、fill_rate >= 90%、send_rate >= 95%、P95 <= 200ms）に基づく PASS/FAIL 判定を実装。

- 研究用ファクター計算（部分実装）
  - research/factor_research.py
    - Momentum、Value、Volatility、Liquidity といったファクター計算の設計と一部実装開始。DuckDB 接続を受けて prices_daily / raw_financials を参照する設計。

### Changed
- ログ出力の標準ストリームを stderr ではなく stdout に統一（cron などで stdout/stderr をリダイレクトしやすくするため）。
- .env 自動読み込みの優先順を OS 環境 > .env.local > .env に設定（.env.local は上書き可・OS 環境は保護）。
- run_monitoring と run_execution で起動時にプロセス優先度を最初に "high" に設定するように統一。

### Fixed
- Settings.paper_fill_mode の不正値検出を追加し、無効値で ValueError を投げることで誤設定の早期発見に対応。
- config_setup の .env 読み書きでシークレットをマスクして表示する挙動を実装（誤ってシークレットを露出しないように保護）。
- validate_config: PyYAML 未インストール時に YAML 検証をスキップして警告することで、検証スクリプトのクラッシュを防止。

### Known issues / Notes
- research/factor_research.py は設計に基づく実装を開始していますが、現状で完全実装されていない箇所があります（今後の実装で各ファクター計算の SQL 実装等を追加予定）。
- apply_sector_cap のエクスポージャー計算は price_map に price が欠損（0.0）があると過少見積になる可能性があり、将来的に前日終値や取得原価等のフォールバック価格の導入を検討する旨の TODO コメントがあります。
- process_priority.set_process_priority / set_cpu_affinity は権限不足や未対応 OS の場合は警告ログを出して処理をスキップします（動作はプラットフォームに依存）。

---

## 参考
- パッケージバージョンは src/kabusys/__init__.py の __version__ (= 0.1.0) に対応しています。