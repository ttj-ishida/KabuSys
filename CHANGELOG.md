CHANGELOG
=========

すべての重要な変更点は Keep a Changelog の形式に準拠して記載しています。

Unreleased
----------


0.1.0 - 2026-04-17
------------------

Added
- 初期リリース。KabuSys の基盤となる機能群を追加。
- 実行系 / 監視
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV が paper_trading の場合は paper 用 DB（data/paper_trading.db をデフォルト）および MockBrokerClient を使用（本番 DB から完全分離）。
    - 起動時にプロセス優先度を "high" に設定するフローを追加。
    - 実行中は data/stop_requested.flag を監視し、検知時は安全に停止する挙動を実装。
    - 実行用 PID ファイル（data/execution.pid）への対応。
  - run_monitoring.py: システム監視ポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正な値は警告してデフォルトにフォールバック。
    - 監視は KABUSYS_ENV にかかわらず本番用 sqlite_path を使用する仕様。
    - 停止フラグ（data/stop_requested.flag）によるループ停止、例外時のログ保護、KeyboardInterrupt ハンドリングを含む。
- 設定・環境変数関連
  - config.py: Settings クラスを追加。環境変数を集約して提供。
    - .env 自動読み込み（プロジェクトルート検出: .git または pyproject.toml を基準）。
    - 自動読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - 必須／オプションの設定、既定値、型変換（Path、float 等）、バリデーション（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE など）を実装。
    - Paper Trading 用 DB パス（PAPER_TRADING_SQLITE_PATH）/ PID / kill flag /閾値設定等を提供。
  - config_setup.py: .env を対話式に作成・更新するウィザード CLI を追加。
    - 複数項目（KABUSYS_ENV, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DUCKDB_PATH, SQLITE_PATH, LOG_LEVEL, KILL_FLAG_CLEAR_ON_START など）に対応。シークレット項目はマスク表示。
  - validate_config.py: 起動前に .env と config/*.yaml の設定不備を検出する検証ツールを追加。
    - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性、DB パスの親ディレクトリ確認、YAML パース（PyYAML があれば内容検証）を実行。
    - --strict オプションで警告も失敗扱い可能。
    - 本番環境向けの追加ガード（LINE トークン未設定や KILL_FLAG_CLEAR_ON_START の危険設定を警告）。
- ポートフォリオ構築（純粋関数群）
  - portfolio.portfolio_builder
    - select_candidates: スコア降順ソートと上位 N 抽出（同点は signal_rank でブレーク）。
    - calc_equal_weights / calc_score_weights: 重み計算。スコアが全て 0 の場合は等金額配分にフォールバック（警告）。
  - portfolio.risk_adjustment
    - apply_sector_cap: セクター集中上限チェックにより候補を除外するロジック（売却予定銘柄をエクスポージャー計算から除外可）。"unknown" セクターはカウントしない。
    - calc_regime_multiplier: 市場レジーム ("bull","neutral","bear") に応じた乗数（フォールバック挙動あり）。
  - portfolio.position_sizing
    - calc_position_sizes: 各銘柄の発注株数計算（risk_based / equal / score の allocation_method に対応）、単元株丸め、per-position と aggregate のキャップ適用、cost_buffer（手数料・スリッページ見積り）考慮、スケールダウン時の端数再配分ロジックを実装。
    - 将来的な拡張点（銘柄別 lot_size のサポート等）をコメントで明示。
- 研究・ファクター計算
  - research.factor_research
    - calc_momentum: 1M/3M/6M リターン、200 日移動平均乖離率などを DuckDB の prices_daily から計算。
    - calc_volatility: ATR / 平均売買代金 / 出来高比などを計算（DuckDB を利用）。（ファイル途中までの実装が含まれる）
    - 全関数は DuckDB 接続を受け取り純粋関数的に動作する設計。
- ユーティリティ
  - utils.process_priority: プロセス優先度（Windows/Linux 対応）と CPU affinity 設定ユーティリティを追加（psutil 使用）。
    - set_process_priority("high"|"normal"|"low")、set_cpu_affinity(n) を実装。権限不足や未対応 OS では警告してスキップ。
- モニタリング / DB 初期化
  - monitoring.monitoring_db の初期化処理（init_monitoring_db）の呼び出しを実行スクリプト側で行うことでテーブル存在を保証（冪等）。
  - DuckDB と SQLite の併用（分析用は DuckDB、運用ログは SQLite）。
- ペーパートレード検証ツール
  - tools.paper_verification_report: Paper Trading 用 SQLite を解析して稼働率 / 注文成功率 / 送信率 / レイテンシ（P95 など）を算出し、PASS/FAIL 判定を行う CLI を追加。
    - デフォルトおよび --db オプション、日付フィルタに対応。
    - 判定閾値（稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200ms）を設定。

Changed
- 初回リリースのため該当なし。

Fixed
- 初回リリースのため該当なし。

Removed
- 初回リリースのため該当なし。

Security
- 環境変数ファイル (.env) は生成スクリプトで Git へのコミット禁止を明記（.env の取扱注意喚起）。
- シークレットは対話式ウィザードでマスクして表示。

Notes / Known limitations
- run_monitoring は明示的に本番用 sqlite_path を使用する設計。開発時に監視データを分離したい場合は環境や実装に注意が必要。
- 一部の機能は外部ライブラリ（psutil, duckdb, PyYAML 等）に依存。validate_config は PyYAML がない場合に YAML 内容チェックをスキップして警告する。
- position_sizing や apply_sector_cap は価格が欠損（0 や None）だと過少評価やスキップが発生する旨の TODO コメントあり。将来的にフォールバック価格の導入を検討。
- process priority / cpu affinity の設定は権限や OS により失敗する場合がある（警告して継続）。
- research.factor_research の一部は DuckDB と prices_daily/raw_financials テーブルを前提としており、入力データが不足すると None を返す設計。
- PAPER_FILL_MODE は "instant" / "partial" / "never" / "reject" のみ有効。不正値は起動時に例外を送出する。

Version
- 現在のパッケージバージョン: 0.1.0（src/kabusys/__init__.py に定義）

貢献・フィードバック
- バグ報告・提案は issue にてお願いします。今後のリリースではテストカバレッジ、エラーハンドリング強化、個別銘柄単元対応、価格フォールバック等の改善を予定しています。