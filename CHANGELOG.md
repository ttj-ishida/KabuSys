# Changelog

すべての注目すべき変更点を記録します。フォーマットは「Keep a Changelog」に準拠しています。  

現在のリリース履歴:

## [0.1.0] - 2026-04-18

### 追加 (Added)
- プロジェクト初回公開リリース。以下の主要機能・モジュールを実装・追加しました。
- コマンドライン / 起動スクリプト
  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。起動時にプロセス優先度を "high" に設定します。
    - KABUSYS_ENV が `paper_trading` の場合、専用の Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）を使用し、本番 DB と完全に分離します。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て、ExecutionEngine のバックグラウンドスレッド実行および停止フラグ（data/stop_requested.flag）への対応を実装。
    - エンジンの PID ファイル出力（data/execution.pid）に対応。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数（デフォルト 60 秒）でポーリング間隔を上書き可能。
    - 監視は環境にかかわらず本番用 sqlite_path を使用して監視データベースを初期化します（init_monitoring_db）。
    - 停止フラグ（data/stop_requested.flag）検知でループ終了、KeyboardInterrupt による終了処理を実装。
- 設定管理
  - config.py
    - .env 自動読み込み機能を実装（プロジェクトルートの検出: .git または pyproject.toml）。
    - .env/.env.local の読み込み順序とオーバーライド挙動（OS 環境変数の保護）を実装。
    - 複数の設定プロパティを型付プロパティとして提供（J-Quants、kabuステーション、DB パス、PAPER_FILL_MODE 等）。
    - 環境値の検証（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE の有効値チェック）を実装。
    - settings = Settings() グローバルインスタンスを公開。
- 設定支援ツール
  - config_setup.py
    - 対話式ウィザードで .env の初期作成・更新を支援。選択肢・デフォルト値の提示、シークレット項目はマスクして表示、保存前の確認を実装。
  - validate_config.py
    - 起動前に .env と config/*.yaml の設定不備を検出する CLI を追加。必須環境変数の存在チェック、パス存在チェック、YAML パース検証（PyYAML があれば）や本番環境向けのガードを実装。--strict オプションで警告を失敗扱いにできます。
- ツール
  - tools/paper_verification_report.py
    - Paper Trading 用 SQLite ログから検証レポートを生成するスクリプトを追加（期間指定可）。稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）、リスク却下数などを集計し PASS/FAIL を判定する基準を実装。
- ポートフォリオ構築ライブラリ (純粋関数群)
  - portfolio/portfolio_builder.py
    - 銘柄選定（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）を実装。スコアが全て 0 の場合のフォールバックも実装。
  - portfolio/risk_adjustment.py
    - セクター集中上限チェック（apply_sector_cap）を実装。既存保有のセクター別時価を考慮して新規候補を除外するロジックを提供。
    - 市場レジームに応じた投下資金乗数（calc_regime_multiplier）を実装（bull/neutral/bear のマッピング、未知レジームはフォールバック）。
  - portfolio/position_sizing.py
    - 各銘柄の発注株数計算ロジックを実装（allocation_method: "risk_based" / "equal" / "score"）。リスクベースのサイズ算出、単元株丸め（lot_size）、per-position および aggregate の上限処理、available_cash によるスケールダウンロジック、cost_buffer（手数料/スリッページ見積）を実装。
  - portfolio/__init__.py で上記関数群を公開。
- ユーティリティ
  - utils/logging_setup.py
    - ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（日次・30日保持）を設定する共通ロギング初期化関数 setup_logging() を実装。ログディレクトリ作成失敗時はファイル出力をスキップして stdout のみで継続。
  - utils/process_priority.py
    - Windows/Linux/macOS の差分を吸収してカレントプロセスの優先度（high/normal/low）を設定する set_process_priority() を実装。CPU affinity 設定関数 set_cpu_affinity() も提供。権限不足や未対応環境では警告を出してスキップ。
- モジュール初期化等
  - __init__.py にバージョン __version__ = "0.1.0" を設定。
- 研究用モジュール（計算ロジックの骨格）
  - research/factor_research.py
    - モメンタムや移動平均、ATR、流動性指標などを計算するための関数群の設計と一部実装を追加（DuckDB 接続を受けて prices_daily / raw_financials を参照する設計）。（注: ファイルは一部実装の段階）

### 変更 (Changed)
- N/A（初回リリースのため既存からの変更はありません）

### 修正 (Fixed)
- N/A（初回リリース）

### 注意事項 / 実装上の重要点
- 設定の自動ロードはプロジェクトルートが検出できない場合はスキップされます（配布後の環境で意図せぬ読み込みを防止）。
- run_monitoring は監視 DB として settings.sqlite_path を常に使用します（KABUSYS_ENV に関わらず本番 DB を監視する想定）。run_execution は paper_trading 時に paper_sqlite_path を使用し DB を分離します。
- PAPER_FILL_MODE は "instant" | "partial" | "never" | "reject" のいずれかである必要があります。無効値は例外になります。
- logging はデフォルトで stdout を使用するように設定されています（cron / タスクスケジューラからの運用を想定）。
- process_priority / cpu_affinity の設定は権限がない環境では失敗するため、呼び出し側で例外は捕捉しログ警告の上で継続します。
- portfolio の各関数は副作用のない純粋関数設計を意識しており、外部 DB を参照しない（呼び出し側で必要なマップ・データを渡す想定）。

### 既知の制限 / TODO
- research/factor_research.py はモメンタム計算などの骨格はあるものの、未完の箇所（ソース中で途中の実装）が存在します。今後のリリースで完成させる予定です。
- position_sizing の lot_size は現状グローバル単一値（デフォルト 100）。将来的には銘柄毎の lot_size を外部マスタで扱えるように拡張予定。
- apply_sector_cap は price_map に 0.0 が入るとエクスポージャーの過小評価を招く可能性があり、フォールバック価格の導入を検討しています。

---

作業やバグ報告、改善提案は issue を立ててください。次のリリースでは research モジュールの完成、ExecutionEngine / Broker 周りの堅牢化やテスト整備を予定しています。