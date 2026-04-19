# Changelog

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠しています。  

最新バージョン: 0.1.0

<!--
フォーマット例:
- Unreleased
- [0.1.0] - 2026-04-19
-->
## [0.1.0] - 2026-04-19

初回公開リリース。日本株自動売買システム KabuSys の基盤機能を提供します。以下はコードベースから推測してまとめた主要な追加・仕様です。

### Added
- 実行エントリ / ランナー
  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合に MockBrokerClient を使用し、paper_trading 用の専用 SQLite（デフォルト: data/paper_trading.db）へ記録して本番 DB と分離。
    - 起動時にプロセス優先度を "high" に設定。
    - 停止用フラグファイル (data/stop_requested.flag) と PID ファイル (data/execution.pid) を扱う制御ループを実装。
  - run_monitoring.py
    - SystemMonitor ポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL によりポーリング間隔を上書き可能（デフォルト: 60 秒）。
    - Monitoring は KABUSYS_ENV に依らず本番用 sqlite_path を使用（監視は一貫して本番 DB を参照）。
    - 停止フラグ検出・例外時ログ記録・接続クローズ処理を実装。

- 設定管理
  - config.py
    - 環境変数・.env ファイルの読み込み・ラッパを提供する Settings クラスを実装。
    - プロジェクトルート自動検出（.git または pyproject.toml を探索）により .env 自動読み込みを実行（環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
    - .env の行パースはクォート・エスケープやインラインコメントを考慮した堅牢な実装。
    - 各種設定プロパティ（J-Quants / kabu API / DuckDB / SQLite / Paper Trading 設定 / 監視閾値 等）を提供。
    - PAPER_FILL_MODE の検証（instant|partial|never|reject）を実装。
    - env 値の妥当性チェック（KABUSYS_ENV, LOG_LEVEL 等）を行う。

  - config_setup.py
    - 対話式ウィザードで .env を初期作成・更新する CLI を実装。
    - デフォルト値・選択肢・シークレット入力サポート・既存 .env の読み込み・最終確認後の保存機能を備える。

  - validate_config.py
    - 起動前に .env と config/*.yaml の不備を検出する CLI を実装。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性、DB パスの親ディレクトリ存在チェック、YAML の存在／パース検証（PyYAML が無い場合はスキップ）等を実行。
    - --strict オプションにより警告を失敗扱いにできる。

- ロギング・プロセス制御ユーティリティ
  - utils/logging_setup.py
    - 共通 logging 設定ユーティリティを追加。stdout 出力（StreamHandler）と日次ローテーション（TimedRotatingFileHandler）をルートロガーに設定。
    - ログディレクトリ自動作成、既存ハンドラのクリーンアップ、環境変数 LOG_DIR / LOG_LEVEL の考慮。
  - utils/process_priority.py
    - クロスプラットフォームでプロセス優先度（high/normal/low）を設定するユーティリティを追加。Windows と POSIX(nice) を吸収。
    - CPU affinity 設定関数も追加（set_cpu_affinity）。
    - 権限エラーや未サポート機能は警告ログにより安全にスキップ。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py
    - 候補選定 (select_candidates)、等金額配分 (calc_equal_weights)、スコア加重配分 (calc_score_weights) を実装。
    - スコアが全て 0 の場合は等金額にフォールバックし Warning を出力。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中を抑えるための候補フィルタリングを実装（既存ポジションのセクター比率に基づく）。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull/neutral/bear）を実装。未知レジームは警告を出して 1.0 でフォールバック。
  - portfolio/position_sizing.py
    - calc_position_sizes: 重み・候補・資金状況・現保有・価格を基に発注株数を決定。以下をサポート:
      - allocation_method: "risk_based" / "equal" / "score"
      - lot_size（単元株）丸め、max_position_pct 上限、max_utilization（投下上限）、cost_buffer（手数料スリッページ見積り）
      - aggregate cap（利用可能現金を超えた場合はスケールダウン）と端数配分ロジック
    - 価格欠損時のスキップやログ出力により堅牢化。

- モニタリング DB / DuckDB 統合
  - 複数のスクリプトで init_monitoring_db(sqlite_conn) を実行して監視テーブル存在を保証。
  - DuckDB 接続を使った分析用データベースパス管理（Settings.duckdb_path）。

- Paper Trading 検証ツール
  - tools/paper_verification_report.py
    - Paper Trading の検証レポート生成スクリプトを実装。
    - 稼働率、注文成功率（fill_rate）、送信率（send_rate）、P95 レイテンシなどを算出して PASS/FAIL を判定。デフォルトの合格閾値を定義（稼働率 99%、fill 90%、send 95%、P95 200ms）。
    - 日付範囲フィルタ（--from/--to）、DB パス指定（--db）に対応。

- リサーチ（ファクター計算；WIP）
  - research/factor_research.py
    - DuckDB 上の prices_daily / raw_financials を用いたファクター計算（Momentum, Value, Volatility, Liquidity）に着手。モメンタム計算用の関数雛形（calc_momentum）を実装中（未完成の可能性あり）。

### Changed
- 初期設計では静的だった各機能を CLI / 環境変数で柔軟に構成可能にし、実運用を想定した安全弁（stop flag / kill flag / PID ファイル / kill_flag_clear_on_start）を取り入れた。
- ログ出力を stdout とファイルの二重出力に標準化し、タスクスケジューラやコンテナ環境での取り扱いを想定。

### Fixed / Hardened
- .env パーサはクォート・エスケープ・インラインコメントの処理を厳密化し、export プレフィックスにも対応。
- logging_setup: ログディレクトリ作成に失敗してもプロセスは継続し、コンソール出力のみで動作するようフォールトトレランスを追加。
- process_priority / set_cpu_affinity: 権限不足・未サポート OS で例外になるのを抑制し警告として扱うようにした。
- 実行中に発生した例外はログに残してポーリングループやエンジン実行を継続/安全停止する仕組みを追加（監視ループの try/except、ExecutionEngine のスレッド制御）。

### Notes / Behaviour
- 環境分離
  - Monitoring は常に（KABUSYS_ENV にかかわらず）デフォルトまたは明示された sqlite_path を使用する設計。これは監視情報を一元的に扱うための意図的な仕様と思われます。
  - ExecutionEngine は paper_trading 環境時に paper_sqlite_path を使用して記録を本番 DB と分離します。
- 必須環境変数
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD は必須。validate_config でチェックされます。
- セキュリティ
  - .env ファイルは生成時に README コメントで「絶対に Git にコミットしないこと」が明記されています。
- 未完成 / TODO
  - research/factor_research.calc_momentum 等に未完の箇所が存在する可能性あり（ファイル末尾が途中で切れているように見える）。将来的な実装完了が必要。
  - position_sizing 内の price フォールバック（価格欠損時の扱い）について TODO コメントあり。

### Breaking Changes
- 初回リリースのため特段の互換性破壊はありません。導入時は .env の必須値とパス設定、KILL フラグなど運用上の注意点を確認してください。

---

今後のリリースでは以下を想定しています（例示）:
- Strategy / Execution の詳細実装、リスク管理のチューニング、テストカバレッジ拡充。
- research モジュールの完成、DuckDB を利用した高速分析パイプライン。
- CLI でのモード切替・デバッグ用オプション追加、監視アラート（LINE 通知）実装の拡張。

もし特に注記してほしい差分（例: 追加された機能や修正ポイント）や、日付・バージョン付けのポリシーがあれば指示ください。それに合わせて CHANGELOG を調整します。