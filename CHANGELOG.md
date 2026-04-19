# CHANGELOG

すべての注目すべき変更をこのファイルに記載します。  
フォーマットは「Keep a Changelog」に準拠しています。  

注：以下の変更点はリポジトリ内のソースコードから推測してまとめた内容です。

## [Unreleased]
- （なし）

## [0.1.0] - 2026-04-19
初回リリース。

### Added
- 基本ランタイム/起動スクリプトを追加
  - run_monitoring.py
    - SystemMonitor のポーリングループを起動するスクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト: 60秒）。
    - 監視は環境にかかわらず本番用 sqlite_path を使用する挙動。
    - 停止フラグ（data/stop_requested.flag）検知で安全にループを終了。
  - run_execution.py
    - ExecutionEngine（注文実行エンジン）を起動するスクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は専用の paper_trading SQLite DB を利用（本番 DB と分離）。
    - 停止フラグ・PID ファイル管理・スレッドライフサイクル管理を実装。

- 設定・環境関連
  - config.py
    - Settings クラスを追加し、環境変数経由で設定を取得する統一インタフェースを提供。
    - .env 自動ロード機能（プロジェクトルートを検出して .env / .env.local を読み込む）。自動ロード無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
    - 各種設定プロパティ（DB パス、PID/kill フラグパス、しきい値、環境判定メソッド等）を実装。
    - PAPER_FILL_MODE の検証・PAPER_TRADING_SQLITE_PATH の設定を提供。
  - config_setup.py
    - 対話式ウィザードにより .env の初期作成/更新を支援する CLI を追加。
    - J-Quants / kabu-api / DB パス / LINE 設定等の選択肢・説明・デフォルトを提供。

- 検証ツール
  - validate_config.py
    - .env と config/*.yaml の設定不備を起動前に検出する CLI を追加。
    - 必須/任意の環境変数チェック、KABUSYS_ENV と LOG_LEVEL の妥当性チェック、DB パス確認、YAML ファイルの存在/パース検査を実装。
    - --strict オプションで警告も失敗扱いにできる。

- ロギング・プロセスユーティリティ
  - utils/logging_setup.py
    - 統一的なログセットアップ関数 setup_logging を追加。
    - コンソール出力（stdout）用 StreamHandler と日次ローテート（TimedRotatingFileHandler、30日保持）をデフォルトで設定。
    - LOG_DIR / LOG_LEVEL による上書き、ハンドラ重複防止、ディレクトリ作成失敗時のフォールバック動作を実装。
  - utils/process_priority.py
    - クロスプラットフォームでプロセス優先度（high/normal/low）を設定するユーティリティを追加（psutil を利用）。
    - CPU affinity を最初の N コアに固定する set_cpu_affinity を実装。
    - Windows と POSIX の違いを吸収する実装とエラーハンドリングを含む。

- ポートフォリオ構築ライブラリ
  - portfolio/portfolio_builder.py
    - 候補選定（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）を追加。
    - スコアがすべて 0 の場合は等金額配分にフォールバックする警告を出す。
  - portfolio/risk_adjustment.py
    - セクター集中上限チェック（apply_sector_cap）を追加。sell コードの除外、"unknown" セクターの扱い、既存ポジションのエクスポージャ計算を実装。
    - 市場レジームに応じた投下資金乗数 calc_regime_multiplier を追加（bull/neutral/bear をマップし、未知レジームはフォールバック）。
  - portfolio/position_sizing.py
    - 各銘柄の発注数を計算する calc_position_sizes を追加。allocation_method（risk_based/equal/score）をサポート。
    - 単元株（lot_size）丸め、1銘柄上限、aggregate cap（available_cash を超えた場合のスケールダウン）、手数料・スリッページ考慮の cost_buffer を実装。
    - price 欠損時の警告ログや安全弁としての上限チェックを実装。

- 取引検証・レポート
  - tools/paper_verification_report.py
    - Paper Trading 用の検証レポート生成スクリプトを追加。
    - system_status / trade_logs / risk_logs から稼働率、注文成功率、送信率、リスク却下数、平均/MAX/P95 レイテンシを集計。
    - PASS/FAIL 判定基準（稼働率、成功率、送信率、P95 レイテンシの閾値）を実装。
    - コマンドライン引数 --from/--to/--db をサポート。

- 研究用モジュール（骨格）
  - research/factor_research.py
    - ファクター計算モジュールを追加（Momentum/Value/Volatility/Liquidity を想定）。
    - DuckDB 接続を受け取り prices_daily / raw_financials から計算する設計。
    - モメンタム計算（calc_momentum）などの実装開始（関数の骨格が含まれる）。  

- パッケージ初期化
  - __init__.py にバージョン情報 __version__ = "0.1.0" を追加し、主要なサブパッケージ名を __all__ にエクスポート。

- DB 初期化ヘルパー呼び出し
  - run_* スクリプト内で monitoring 用のテーブル作成を行う init_monitoring_db(sqlite_conn) 呼び出しを導入し、監視テーブル存在保証（冪等）を実施。

### Changed
- （初回リリースにつき、既存からの変更はなし）

### Fixed
- （初回リリースにつき、既知の修正点はなし）

### Notes / Implementation details
- .env パーサーはクォートやエスケープ、export プレフィクス、行内コメントの扱いを考慮した堅牢な実装になっているため、複雑な .env 形式にもある程度対応可能。
- ロギングは標準出力を stdout に向ける設計で、cron やスケジューラでの扱いを想定。
- process_priority や CPU affinity の設定はアクセス権限や OS によって失敗する可能性があるため、例外時には警告を出してスキップする安全設計。
- position_sizing の aggregate スケーリングは lot_size 単位で丸めつつ、残余キャッシュを用いて残差の大きい銘柄順に追加配分する再現可能なアルゴリズムを採用。

### Known limitations / TODO
- research/factor_research.py は計算ロジックの続きを実装する必要がある（ファイル末尾が途中で切れている／関数の完全実装が必要）。
- price 欠損時（0.0）のエクスポージャ過少見積りに関する注記が残っており、将来的に前日終値やその他フォールバック価格を使う拡張を検討。
- lot_size を銘柄ごとに持たせる拡張（stocks マスタを使う等）を将来検討。

---

この CHANGELOG はソースコードの内容から推測して作成しています。実際のリリースノート作成時は、コミット／PR のログやリリース方針に合わせて調整してください。