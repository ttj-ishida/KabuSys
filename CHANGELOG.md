# CHANGELOG

すべての変更は Keep a Changelog の形式に準拠します。  
このファイルはリポジトリのコードから推測して作成した初期リリース向けの変更履歴です。

## [Unreleased]

（現時点で未リリースの変更はありません）

## [0.1.0] - 2026-04-18

初期リリース。KabuSys の基本コンポーネントを追加。

### Added
- 全体
  - パッケージ初期化とバージョン定義を追加（kabusys.__version__ = "0.1.0"）。
  - 環境変数・設定管理モジュールを追加（kabusys.config）。
    - .env / .env.local の自動読み込み（プロジェクトルート検出：.git または pyproject.toml）。
    - .env パーサは export 構文、クォート内のエスケープ、インラインコメント処理に対応。
    - 必須環境変数取得ヘルパー（_require）と Settings クラスを提供。多くの設定プロパティ（DB パス、API トークン、監視閾値、実行環境フラグ等）を環境変数から取得。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD で自動読み込みを無効化可能。

- CLI / ツール
  - 環境設定ウィザード（kabusys.config_setup）
    - .env の対話的作成・更新を支援するウィザード。シークレット入力、選択肢、既存値再利用に対応。
    - 出力フォーマットは .env ファイル（機密情報を含むため Git へコミットしないよう注意書きあり）。
  - 設定検証ツール（kabusys.validate_config）
    - .env と config/*.yaml の存在・基本整合性を検証。
    - --strict オプションで警告を失敗扱いにして exit(1) にする。
    - 本番環境（KABUSYS_ENV=live）向けの追加ガードチェックを実装（LINE 通知設定、KILL_FLAG_CLEAR_ON_START の危険性等）。
  - Paper Trading 検証レポート生成ツール（kabusys.tools.paper_verification_report）
    - paper_trading 用 SQLite（デフォルト: data/paper_trading.db）から集計し、稼働率・注文成功率・送信率・レイテンシ（平均/最大/P95）などを出力。
    - デフォルト閾値（稼働率 99.0%、注文成功率 90%、送信率 95%、P95 レイテンシ 200ms）に基づく PASS/FAIL 判定を実装。
    - --from / --to / --db オプションで期間や DB を指定可能。

- 実行/監視ランナー
  - 実行エンジン起動スクリプト（kabusys.run_execution）
    - プロセス優先度を最初に "high" に設定。
    - KABUSYS_ENV=paper_trading の場合は paper_sqlite_path（デフォルト: data/paper_trading.db）を使用し、本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント生成（paper_trading 時は Mock を想定）。
    - OrderRepository / OrderManager / RiskManager / Reconciler を組み立て、ExecutionEngine をスレッドで起動。
    - 停止フラグ (data/stop_requested.flag) の存在チェックで安全に停止。実行用 pid ファイルパスをサポート。
  - 監視ループ起動スクリプト（kabusys.run_monitoring）
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はデフォルトにフォールバックして警告。
    - 監視は環境にかかわらず本番 sqlite_path を使用して監視テーブルを初期化。
    - SystemMonitor.check_once() を定期実行し、例外はログに出力して次ポーリングへフォールバック。
    - 停止フラグ (data/stop_requested.flag) の検出でループを終了。
    - プロセス優先度を起動直後に "high" に設定。

- ポートフォリオ構築（kabusys.portfolio）
  - portfolio_builder
    - select_candidates: BUY シグナルをスコア降順（タイブレークは signal_rank）でソートし上位 N を返す。
    - calc_equal_weights / calc_score_weights: 等金額配分とスコア加重配分（全スコアが 0 の場合は等金額にフォールバック）を実装。
  - risk_adjustment
    - apply_sector_cap: セクター集中制限を適用し、上限超過セクターの新規候補を除外（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: レジーム（bull/neutral/bear）に応じた投下資金乗数を返す（未定義レジームは 1.0 にフォールバック）。
  - position_sizing
    - calc_position_sizes: allocation_method（"risk_based" / "equal" / "score"）に基づき、単元株（lot_size）丸め、1銘柄上限、aggregate cap（available_cash 超過時のスケーリング）、cost_buffer（スリッページ・手数料見積）を考慮して発注株数を計算。
    - risk_based ではポジションごとのリスク＋損切り率からベース株数を算出。
    - aggregate cap の際はスケールダウンと端数補填ロジックを実装。

- 分析/リサーチ
  - research.factor_research（初期実装の一部を追加）
    - DuckDB 接続を受け取り、prices_daily / raw_financials を参照してモメンタム、MA200 乖離、ATR、ボリューム関連などのファクター計算を行う設計（関数 calc_momentum の雛形あり）。
    - 日付範囲やスキャンバッファの定数を設定。

- ユーティリティ
  - ログ設定ユーティリティ（kabusys.utils.logging_setup）
    - ルートロガーに stdout 用 StreamHandler と日次ローテートされる TimedRotatingFileHandler（logs/<app_name>.log、30 日保持）を設定。
    - 既存ハンドラをクリアして二重設定を防止。ログディレクトリ作成に失敗した場合はファイルロギングをスキップして stdout のみで継続。
    - LOG_LEVEL / LOG_DIR / app_name / 引数 level/log_dir を解決するロジックを実装。
  - プロセス優先度ユーティリティ（kabusys.utils.process_priority）
    - Windows / POSIX（Linux, Darwin, FreeBSD）を吸収してプロセス優先度（high/normal/low）を設定。
    - CPU affinity を最初の N コアへ固定する set_cpu_affinity を実装（権限エラーや未対応 OS は警告でスキップ）。
    - 権限不足などで設定に失敗した場合は警告をログに出す。

### Changed
- （初期リリースにつき該当なし）

### Fixed
- （初期リリースにつき該当なし）

### Removed
- （初期リリースにつき該当なし）

### Notes / その他重要事項
- 環境分離
  - 実行エンジンは paper_trading モード時に paper_trading 用 SQLite を使用して本番データと完全分離する設計。監視（monitoring）は意図的に本番 sqlite_path を使用する実装が含まれています（設計上の理由に注意が必要）。
- 停止制御
  - 両ランナーはプロジェクトの data/stop_requested.flag を監視して安全停止する仕組みを持つ。実運用ではこのファイルの管理に注意してください。
- ログ
  - ログはデフォルトで logs/ 配下に保存されます。ログディレクトリ作成に失敗した場合でもコンソールログは有効のまま動作します。
- .env の安全性
  - .env には機密情報（API トークン等）を保存するため、リポジトリへのコミットは厳禁です（config_setup のヘッダにも明記）。

今後の予定（想定）
- research.factor_research の完全実装（Momentum, Value, Volatility, Liquidity の各計算）。
- ExecutionEngine / BrokerClient の詳細実装・テスト、MockBroker の振る舞い検証。
- さらなる CLI/運用ツール（ログ集約、メトリクス可視化など）。

------------------------------
参照: この CHANGELOG はソースコードの内容から推測して作成しています。実際のコミット履歴や設計ドキュメントに基づく正式な履歴とは差異がある可能性があります。