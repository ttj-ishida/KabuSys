# CHANGELOG

すべての変更は Keep a Changelog の形式に従います。  
バージョン番号は src/kabusys/__init__.py の __version__ に対応します。

## [0.1.0] - 2026-04-23

### 追加
- 初回リリース: KabuSys 日本株自動売買システムのベース機能群を追加。
- 起動スクリプト
  - run_execution.py: ExecutionEngine を起動するエントリポイントを追加。
    - KABUSYS_ENV=paper_trading 時はペーパートレード用 DB と MockBrokerClient を利用（data/paper_trading.db で完全分離）。
    - 実行中の停止フラグ（data/stop_requested.flag）検知、PID ファイル管理、スレッド起動/停止ロジックを実装。
    - プロセス優先度を起動時に "high" に設定する処理を実行。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で上書き可能（デフォルト 60 秒）。
    - 監視は常に本番用 sqlite_path を使用する（環境に依存しない）。
    - 停止フラグ検知でループ終了、例外はログ出力して次のポーリングへフォールバック。
- 設定関連
  - config.py: Settings クラスを追加。環境変数から各種設定を取得するユーティリティを提供。
    - DB パス（DUCKDB/SQLite）、KABUSYS_ENV、LOG_LEVEL、paper_trading 関連設定（PAPER_FILL_MODE、PAPER_TRADING_SQLITE_PATH）、閾値や PID / kill flag パス等。
    - プロジェクトルート自動検出（.git または pyproject.toml を基準）と .env 自動読み込み（.env/.env.local、OS 環境変数保護）。
  - config_setup.py: 対話式 .env ウィザードを実装。既存 .env の読み込み／更新、シークレットマスク表示、保存機能を提供。
  - validate_config.py: 起動前検証 CLI を追加。必須環境変数・KABUSYS_ENV・DB パス・config/*.yaml の存在と YAML パース（PyYAML があれば）等を検査。--strict オプションで警告を失敗扱いにできる。
- ポートフォリオ構築関連（純粋関数群）
  - portfolio.portfolio_builder: 候補選定 (select_candidates)、等金額配分 (calc_equal_weights)、スコア加重配分 (calc_score_weights) を追加。
  - portfolio.risk_adjustment: セクター集中制限を行う apply_sector_cap、マーケットレジームに基づく投下資金乗数 calc_regime_multiplier を追加。
  - portfolio.position_sizing: 各銘柄の発注株数計算 calc_position_sizes を追加。allocation_method（risk_based / equal / score）、lot_size での丸め、aggregate cap によるスケーリング、cost_buffer 考慮などのロジックを含む。
- ユーティリティ
  - utils/logging_setup.py: 統一的なログ設定関数 setup_logging を実装。コンソール（stdout）出力と日次ローテーションファイル出力（TimedRotatingFileHandler）を設定。ログディレクトリ自動作成（失敗時はファイル出力をスキップ）。
  - utils/process_priority.py: プラットフォーム差分を吸収するプロセス優先度設定（set_process_priority）と CPU affinity 設定（set_cpu_affinity）を実装（psutil 利用）。
- ツール
  - tools/paper_verification_report.py: ペーパートレード DB から検証レポートを生成する CLI を追加。稼働率、注文成功率・送信率、リスク却下数、API レイテンシ（平均/最大/P95）などを集約し PASS/FAIL 判定を出力。日付フィルタ（--from / --to）や DB パス指定オプションをサポート。
- 研究モジュール
  - research/factor_research.py: ファクター計算モジュールを追加（モメンタムや移動平均・ATR 等を計画）。DuckDB 接続を受けて prices_daily / raw_financials を参照する設計。

### 変更
- ログ出力の標準出力先を stderr ではなく stdout に変更（utils.logging_setup）。cron / タスクスケジューラからのリダイレクトを考慮。
- run_execution/run_monitoring の起動時にプロセス優先度を自動で "high" に設定するように統一。

### 修正
- .env パーサの強化（config._parse_env_line）
  - export プレフィックス対応。
  - シングル/ダブルクォートされた値のエスケープ処理に対応（バックスラッシュによるエスケープを正しく処理）。
  - クォートなしの場合のインラインコメント認識ルールを明確化（'#' の直前がスペース/タブのときのみコメントとして扱う）。
  - ファイル読み込み時に既存の OS 環境変数を保護する仕組みを追加（protected set により上書きを抑制）。
- position_sizing の集約制約ロジックの改善
  - cost_buffer を導入してスリッページ/手数料分を保守的に見積もる。
  - スケーリング後の残差処理で lot_size 単位で再分配するアルゴリズムを実装し、可決可能な配分を最大化。
- monitoring / execution の DB 初期化で監視テーブルが存在することを冪等に保証（init_monitoring_db 呼び出しを追加）。

### ドキュメント（コード内コメント・docstring）
- 各モジュールに利用方法、設計方針、引数・戻り値の説明を含む詳細な docstring と注釈を追加。
- PortfolioConstruction.md / StrategyModel.md など外部設計ドキュメント参照を明記（コード内コメント）。

### 既知の制限 / 注意点
- research/factor_research.py は継続実装中の箇所があり（ファイル末尾が途中で切れている）、完全なファクター計算実装は今後の作業。
- apply_sector_cap は price_map に価格欠損（0.0）がある場合にエクスポージャーが過小に見積もられる可能性がある旨の TODO コメントあり。将来的にフォールバック価格の採用を検討予定。
- process_priority および set_cpu_affinity は権限不足や未対応プラットフォームでスキップされる可能性がある（警告ログ出力で通知）。

### セキュリティ
- シークレット情報（J-Quants トークン、kabu API パスワード、LINE トークン等）は .env に保存する設計だが、config_setup の README コメントで .env を絶対に Git にコミットしないよう注意喚起を追加。

---

今後の計画（抜粋）
- research モジュールの完成（全ファクター実装・正規化ユーティリティ統合）
- ExecutionEngine / BrokerClient の詳細実装とペーパートレード／本番クライアントのテスト強化
- 監視・アラート（LINE 連携）機能の拡充と運用ドキュメント整備

もし特定ファイルや機能について CHANGELOG にさらに詳しい記載（例: 関数単位の変更点、既知のバグ一覧）を希望される場合は、対象箇所を指定してください。