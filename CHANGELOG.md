# Keep a Changelog
すべての重要な変更をこのファイルに記録します。  
フォーマットは Keep a Changelog に準拠しています。

## [0.1.0] - 2026-04-22

初回リリース。プロジェクトの主要コンポーネントを実装しました（環境設定、実行/監視ランナー、ポートフォリオ構築ロジック、ユーティリティ、検証/セットアップツールなど）。以下はコードベースから推測してまとめた変更点・機能説明です。

### Added
- 全体
  - パッケージ初期バージョンを追加（src/kabusys/__init__.py: __version__ = "0.1.0"）。

- 実行・監視関連スクリプト
  - run_execution: ExecutionEngine 起動スクリプトを追加
    - KABUSYS_ENV=paper_trading 時にペーパートレード用の MockBrokerClient を使用し、paper_trading 用 DB（デフォルト: data/paper_trading.db）と分離して動作。
    - プロセス優先度を高（"high"）に設定して起動。
    - PID ファイル管理（data/execution.pid）と停止フラグ（data/stop_requested.flag）に対応。
    - ExecutionEngine のために BrokerClientFactory、OrderRepository、OrderManager、RiskManager、Reconciler を組み立てる。
    - RiskManager 初期設定（デフォルト値: max_position_pct=0.20 等）を使用して起動。
  - run_monitoring: SystemMonitor 用のポーリングループ起動スクリプトを追加
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番 sqlite_path を使用して監視 DB を初期化。
    - 停止フラグ（data/stop_requested.flag）でループ終了、KeyboardInterrupt にも対応。
    - プロセス優先度を高に設定。

- 設定管理・検証ツール
  - config: 環境変数/設定管理モジュールを追加
    - プロジェクトルート自動検出（.git または pyproject.toml 基準）により .env 自動読み込みを実施（.env, .env.local）。
    - .env パースは引用符・エスケープ・インラインコメントに対応した堅牢な実装。
    - Settings クラスで設定項目をプロパティとして提供（J-Quants トークン、kabu API、DB パス、PAPER_FILL_MODE 等）。
    - KABUSYS_ENV、LOG_LEVEL 等の値検証を実施（不正値は例外）。
  - config_setup: .env 対話式ウィザードを追加
    - 対話入力、既存 .env の読み込み、シークレット値のマスク表示、確認後ファイル出力をサポート。
    - デフォルト値や選択肢（KABUSYS_ENV, LOG_LEVEL, KILL_FLAG_CLEAR_ON_START 等）を用意。
  - validate_config: 起動前検証 CLI を追加
    - 必須環境変数存在チェック、KABUSYS_ENV/LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ検査、config/*.yaml の存在・パースチェック（PyYAML がない場合はスキップ）を実施。
    - --strict オプションにより警告を失敗扱いにできる。
    - KABUSYS_ENV=live 時の特別なガード（LINE 設定の確認、KILL_FLAG_CLEAR_ON_START の警告）を実装。

- ポートフォリオ構築（純粋関数群）
  - portfolio.portfolio_builder
    - select_candidates: スコア降順 + signal_rank タイブレークで候補選定。
    - calc_equal_weights / calc_score_weights: 等配分・スコア重みの計算（スコア合計0 の場合は等配分へフォールバック）。
  - portfolio.risk_adjustment
    - apply_sector_cap: 既存保有のセクター比率に基づく新規候補の除外ロジック。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数の提供（未知レジームは 1.0 でフォールバック）。
  - portfolio.position_sizing
    - calc_position_sizes: allocation_method（"risk_based" / "equal" / "score"）に基づく発注株数計算。
    - 単元（lot_size）丸め、ポジション上限・aggregate cap（available_cash を超える場合のスケールダウン）、cost_buffer 加味、残差分配ロジック等を実装。

- ユーティリティ
  - utils.logging_setup
    - 統一的ログ設定を提供（StreamHandler を stdout へ、TimedRotatingFileHandler による日次ローテーション（30日保持））。
    - LOG_DIR / LOG_LEVEL の解決ルール、ハンドラの二重設定回避、ファイル出力失敗時のフォールバック処理を実装。
  - utils.process_priority
    - psutil を用いたクロスプラットフォームのプロセス優先度設定（Windows と POSIX の差分吸収）、CPU affinity 設定ヘルパーを追加。
    - 権限不足や未対応 OS の際は警告を出してスキップ。

- ツール
  - tools.paper_verification_report: Paper Trading 検証レポート生成スクリプトを追加
    - system_status / trade_logs / risk_logs から稼働率、注文成功率、送信率、レイテンシ（avg/max/P95）を集計してレポート出力。
    - 閾値による PASS/FAIL 判定を実装（例: 稼働率 >= 99%、P95 <= 200ms 等）。
    - --from / --to / --db オプション、環境変数 PAPER_TRADING_SQLITE_PATH をサポート。
  - tools パッケージ初期化（tools/__init__.py）。

- 研究用モジュール（部分実装）
  - research.factor_research: DuckDB を用いたファクター計算基盤の追加（モメンタム/Value/Volatility/Liquidity の設計と calc_momentum の骨格実装、詳細実装は継続）。

- パッケージエクスポート
  - portfolio パッケージの __init__ で公開 API を整理（select_candidates 等をエクスポート）。

### Changed
- なし（初回リリースのため新規導入が主体）

### Fixed
- なし（初回リリース。コード中に堅牢性向上のためのエラーハンドリングやフォールバック処理を多数含む）

### Notes / 実装上の注意事項
- .env 自動ロードはプロジェクトルート検出に成功した場合のみ行われ、OS 環境変数はデフォルトで保護されます。自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- Settings のプロパティは不正な環境変数値に対して ValueError を投げます。起動前に validate_config を実行して設定整合性を確認することを推奨します。
- run_execution は paper_trading モード向けに DB を分離しますが、本番モード（live）時は本番 sqlite_path を利用します。誤った DB を指定しないよう .env 設定に注意してください。
- ログ出力はデフォルトで logs/ ディレクトリに保存されます。ディレクトリ作成に失敗した場合はコンソール出力のみで継続します。
- position_sizing, risk_adjustment のアルゴリズムは PortfolioConstruction.md / StrategyModel.md に基づく設計メモを参照する想定です。実運用前にバックテストで挙動確認を行ってください。
- research.factor_research の実装は途中で切れている箇所があります（コード末尾が未完）。ファクター計算ロジックの完成が必要です。

### Known issues / TODO
- factor_research.calc_momentum の実装が途中（ファイル末尾が切れている）ため、研究モジュールは現状で未完成。
- position_sizing の price フォールバック（前日終値や取得原価など）に関する TODO コメントあり。価格欠損時の扱い改善が必要。
- 単元（lot_size）や銘柄別設定は将来的に拡張予定（stocks マスタからロードする等）。
- 一部モジュール（例: monitoring_db, SystemMonitor, ExecutionEngine の内部実装）は本変更ログの範囲外（別ファイル）だが、ランナーはそれらに依存しているため、併せて動作確認が必要。

---

このリリースノートはコードベースから推測して作成しています。実際の変更履歴（コミットメッセージや issue）と差異がある可能性があります。必要であれば、各モジュールごとにより詳細なリリースノートを生成します。