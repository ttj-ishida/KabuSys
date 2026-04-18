# CHANGELOG

すべての重要な変更を記録します。フォーマットは Keep a Changelog に準拠します。

## [0.1.0] - 2026-04-18

リリース初版。KabuSys のコア機能（設定管理、起動スクリプト、監視/実行ループ、ポートフォリオ構築ユーティリティ、各種ユーティリティ、検証・ウィザード・レポートツール）を追加しました。

### Added
- 一般
  - パッケージバージョンを設定（kabusys.__version__ = "0.1.0"）。
  - Keep a Changelog 準拠のログを出力するための基礎を提供。

- 設定管理
  - Settings クラス（kabusys.config）を追加。環境変数から各種設定（J-Quants / kabu API / DB パス / ログレベル / 環境種類 など）を取得するプロパティを実装。
  - .env 自動読み込み機能を実装（プロジェクトルート検出: .git または pyproject.toml を基準）。.env と .env.local の読み込み順序と、OS 環境変数を保護する動作をサポート。
  - .env パース機能を強化（export プレフィックス対応、シングル/ダブルクォート中のエスケープ対応、インラインコメント処理）。

- 設定支援ツール
  - 対話式設定ウィザード（kabusys.config_setup）を追加。対話的に .env を作成・更新する run_wizard を実装。機密値はマスク表示、保存前の確認プロンプトを実装。
  - バリデーション CLI（kabusys.validate_config）を追加。必須環境変数や KABUSYS_ENV/LOG_LEVEL の妥当性、DB パスの親ディレクトリ存在確認、config/*.yaml の存在と（PyYAML があれば）パース検証を行う。--strict オプションで警告を FAIL 扱いにできる。

- 起動スクリプト / 実行基盤
  - 実行エンジン起動スクリプト（kabusys.run_execution）を追加。
    - プロセス優先度を起動時に設定（high）。
    - paper_trading 環境では paper 専用 SQLite（PAPER_TRADING_SQLITE_PATH、デフォルト data/paper_trading.db）を使用し、本番 DB と分離。
    - BrokerClientFactory を介してブローカークライアントを生成（KABUSYS_ENV に応じて Mock/実ブローカーを切り替え想定）。
    - OrderRepository、OrderManager、RiskManager、Reconciler、ExecutionEngine を組み立て、ExecutionEngine をスレッドで実行。stop フラグ（data/stop_requested.flag）で安全に停止可能。
    - RiskManager の初期パラメータ（max_position_pct、max_utilization、rate_limit_per_sec、circuit_breaker 等）と、initial_portfolio_value を Broker から取得して初期化する挙動を導入。

  - 監視ポーリング起動スクリプト（kabusys.run_monitoring）を追加。
    - MONITOR_POLL_INTERVAL 環境変数（秒）でポーリング間隔を上書き可能（デフォルト: 60 秒）。不正値（0 以下や非整数）はデフォルトにフォールバックし、警告ログを出す。
    - 監視は環境（KABUSYS_ENV）にかかわらず本番 sqlite_path を使用する仕様（監視データは本番 DB を見に行く）。
    - SystemMonitor.check_once() の例外を捕捉してログ出力後に次ポーリングへ継続する堅牢化。
    - 停止フラグ（data/stop_requested.flag）検知でループを抜けてクリーンアップする。

- 監視・データベース
  - init_monitoring_db を用いて必要な監視テーブルの存在を保証する初期化処理を導入（冪等）。

- ロギング / プロセス制御ユーティリティ
  - 統一ロギング設定ユーティリティ（kabusys.utils.logging_setup）を追加。
    - ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション、30 日保持）を設定。
    - ログレベルとログディレクトリの解決順（引数 > 環境変数 > デフォルト）を実装。
    - ログディレクトリ作成に失敗した場合はファイルハンドラをスキップしてコンソール出力のみで継続する安全策を実装。
  - プロセス優先度 / CPU affinity ユーティリティ（kabusys.utils.process_priority）を追加。
    - Windows / POSIX を吸収した nice/priority 設定を実装。アクセス権限や未対応 OS 時は警告を出してスキップ。
    - set_cpu_affinity により最初の N コアにピン留めする機能を提供。

- ポートフォリオ構築（純粋関数群）
  - portfolio_builder:
    - select_candidates: スコア降順（同点時 signal_rank でタイブレーク）で上位 N を選択。
    - calc_equal_weights / calc_score_weights: 等金額配分とスコア加重配分（全スコアが 0 の場合は等金額にフォールバック）を実装。
  - risk_adjustment:
    - apply_sector_cap: 既存保有のセクター・エクスポージャーに基づいて新規候補を除外するロジック。sell_codes（当日売却予定）をエクスポージャー計算から除外可能。unknown セクターは制限対象外。
    - calc_regime_multiplier: market レジーム（bull/neutral/bear）に基づく投下資金乗数を実装（デフォルトフォールバックと警告を含む）。
  - position_sizing:
    - calc_position_sizes: allocation_method（risk_based / equal / score）に基づく発注株数計算。
      - 単元株（lot_size）で丸め、1 銘柄上限、aggregate cap（available_cash）を考慮したスケーリング、cost_buffer（手数料/スリッページ見積り）を組み込んだ保守的評価、残余キャッシュでの端数配分ロジックなどを実装。

- 解析 / リサーチ
  - research/factor_research モジュールを追加（Momentum / Value / Volatility / Liquidity 計算の方針を実装）。DuckDB 接続を受け取り prices_daily / raw_financials を参照して各ファクターを計算する設計（モジュール内の関数 calc_momentum 等を含む、詳細実装は進行中）。

- ツール
  - Paper Trading 検証レポート生成ツール（kabusys.tools.paper_verification_report）を追加。
    - PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）を参照して、system_status / trade_logs / risk_logs から稼働率・注文成功率・送信率・レイテンシ等を集計。
    - P95 の計算、閾値（稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200 ms）に基づく PASS/FAIL 判定を実装。
    - コマンドライン引数 --from / --to / --db をサポート。

### Changed
- なし（初版のため変更履歴はありません）。

### Fixed
- ロギング設定
  - ログディレクトリが作成できない環境でも起動を継続するように修正（ファイル出力を無効化してコンソール出力のみで継続）。
- 監視ループ
  - MONITOR_POLL_INTERVAL の不正値（0 以下・非整数）で time.sleep が ValueError を投げるケースに対処。警告を出力してデフォルト値にフォールバックする実装を追加。
  - SystemMonitor.check_once() 内で例外が発生しても監視ループ全体が停止しないよう例外を捕捉してログ出力し、次回ポーリングへ継続する堅牢化を実施。
- 実行エンジン
  - 起動時に停止フラグが既に立っている場合はエンジンを起動せず終了する安全チェックを追加。

### Deprecated
- なし

### Removed
- なし

### Security
- なし

Notes:
- .env ファイルは機密情報を含むため、config_setup により生成された .env を絶対にリポジトリにコミットしない旨の注意書きを含めています。
- Paper Trading と本番 DB は分離して運用する設計（paper_trading 環境では paper_sqlite_path を使用）になっています。運用時は環境変数設定にご注意ください。