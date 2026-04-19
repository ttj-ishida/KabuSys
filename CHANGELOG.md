# CHANGELOG

すべての変更は Keep a Changelog のフォーマットに準拠しています。  
日付はコードベースの現在時点（2026-04-19）を基準に推測しています。コード内の実装・ドキュメントから機能追加・振る舞いを推測して記載しています。

## [Unreleased]
- 今後のリリースで追記予定

## [0.1.0] - 2026-04-19
初回公開リリース（推測）。以下の主要機能・CLI・ライブラリを実装。

### Added
- 全体
  - パッケージ初期化とバージョン情報を追加（kabusys.__version__ = "0.1.0"）。
  - 環境変数・設定管理モジュール（kabusys.config）
    - プロジェクトルート自動検出（.git または pyproject.toml 基準）による .env 自動読み込み機能を追加。
    - .env 読み込みロジックは export 形式やシングル/ダブルクォート、行内コメント等に対応。
    - 必須/任意の設定値取得プロパティを提供（J-Quants / kabuステーション / DB パス / PID / Kill Flag 等）。
    - PAPER_FILL_MODE のバリデーション（instant/partial/never/reject）や KABUSYS_ENV の許容値チェックを実装。
    - paper_trading 用 DB パス（PAPER_TRADING_SQLITE_PATH）や monitoring 用 sqlite_path の分離をサポート。

- CLI ツール
  - 環境設定ウィザード（kabusys.config_setup）
    - 対話式で .env を作成・更新するウィザードを実装。
    - J-Quants トークンや kabu API パスワード等のシークレット入力、選択肢・デフォルト値のサポート、既存値の再利用機能を提供。
    - .env のテンプレート出力（書式と注意書き含む）。
  - 設定検証ツール（kabusys.validate_config）
    - 起動前に .env と config/*.yaml の存在・基本整合性を検証する CLI を実装。
    - 必須環境変数チェック、KABUSYS_ENV 値チェック、ログレベルチェック、DB パスの親ディレクトリ検査、YAML パース（PyYAML が利用可能な場合）を行う。
    - --strict オプションで警告をエラー扱いにできる。
  - Paper Trading 検証レポート生成（kabusys.tools.paper_verification_report）
    - paper_trading 用 SQLite DB（デフォルト: data/paper_trading.db）から指標を集計してレポート出力するスクリプトを追加。
    - 指標: 稼働率(uptime)、注文成功率(fill rate)、送信率(send rate)、P95 レイテンシ、リスク却下数 等。
    - デフォルト閾値 (稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200ms) に基づく PASS/FAIL 判定を実装。
    - 日付フィルタ (--from / --to) と DB パスの引数/環境変数オーバーライドをサポート。

- 実行・監視ランナー
  - 実行エンジン起動スクリプト（kabusys.run_execution）
    - ExecutionEngine の起動ロジックを実装。BrokerClientFactory を用いたブローカークライアント生成を含む。
    - paper_trading 環境では専用の SQLite（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）を使用し本番 DB と完全分離。
    - リスクマネージャ設定（RiskConfig のデフォルト値）や Reconciler/OrderManager/OrderRepository の組み立て、スレッドでのセッション実行、停止フラグ（data/stop_requested.flag）検出による安全停止をサポート。
    - PID ファイル出力と stop フラグチェックに対応。
  - 監視ループ起動スクリプト（kabusys.run_monitoring）
    - SystemMonitor をポーリングするデーモンループ実装。ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で上書き可能（デフォルト 60 秒）。
    - 監視用 DB 初期化（init_monitoring_db）、duckdb 接続を用いた分析用 DB 連携。
    - 停止フラグ（data/stop_requested.flag）検知でループを終了、KeyboardInterrupt による終了処理を実装。
    - Monitoring は環境に関わらず本番 sqlite_path を使用する設計。

- ポートフォリオ構築ライブラリ（kabusys.portfolio）
  - portfolio_builder
    - select_candidates: BUY シグナルのスコア降順選択（タイブレークは signal_rank）。
    - calc_equal_weights / calc_score_weights: 等金額配分 / スコア加重配分（スコア合計が 0 の場合は等分にフォールバック）。
  - risk_adjustment
    - apply_sector_cap: セクター集中上限チェック（既存保有のセクター露出を計算して新規候補を除外）。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数を提供（未知レジームは 1.0 でフォールバック）。
  - position_sizing
    - calc_position_sizes: allocation_method（risk_based / equal / score）に基づき発注株数を計算。
    - 単元株（lot_size）丸め、ポジション上限（max_position_pct）、利用可能資金による aggregate cap、cost_buffer（手数料・スリッページ見積り）を考慮したスケーリングを実装。
    - price 欠損時のスキップやログ出力、スケールダウン時の端数配分ロジックを実装。

- ユーティリティ
  - ロギング設定ユーティリティ（kabusys.utils.logging_setup）
    - StreamHandler（stdout）と TimedRotatingFileHandler（日次・30日分保持）をルートロガーに設定する共通初期化機能を追加。
    - LOG_DIR / LOG_LEVEL 解決順序の実装と、ファイル出力に失敗した場合のフォールバック（コンソールのみ）をサポート。
  - プロセス優先度・CPU affinity 設定ユーティリティ（kabusys.utils.process_priority）
    - Windows と POSIX（Linux/Mac/FreeBSD）を吸収する set_process_priority と set_cpu_affinity を追加。
    - psutil を利用し、権限不足や未対応 OS の場合は警告を出して安全にスキップ。

- 研究用ファクタ計算（kabusys.research.factor_research）
  - DuckDB を用いたモメンタム/ボラティリティ/流動性/バリュー等のファクター計算を意図したモジュールを追加（関数 calc_momentum 等、設計ドキュメントコメントと定数を含む）。（注: ファイル末尾で計算処理が途中まで含まれているため、以降の実装は未完の可能性あり）

### Changed
- （初版のため特記すべき既存からの変更はなし）

### Fixed
- （初版のため特記すべき修正はなし）

### Deprecated
- なし

### Removed
- なし

### Security
- 環境変数を .env から自動読み込みする際、OS 環境変数（既存の環境）を保護する仕組みを実装（protected set）し、テスト用途に KABUSYS_DISABLE_AUTO_ENV_LOAD で自動読み込みを無効化可能。

---

注記:
- 上記はリポジトリ内のソース・ドキュメント文字列から振る舞いを推測してまとめた CHANGELOG です。実際のコミット履歴や意図したリリースノートとの差異がある場合があります。必要であれば、実際の git 履歴や開発者コメントを元に追補・修正します。