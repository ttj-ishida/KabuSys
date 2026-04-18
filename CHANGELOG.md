# CHANGELOG

すべての重要な変更点は Keep a Changelog の形式に従って記載します。  
初期リリースおよびコードベースから推測できる主要な機能・修正点をまとめています。

注: 日付はコード解析時点（2026-04-18）を基準にしています。実際のリリース日・バージョン運用に合わせて調整してください。

## [Unreleased]

- なし

## [0.1.0] - 2026-04-18

### 追加 (Added)
- 基本パッケージ公開
  - パッケージメタ情報として `__version__ = "0.1.0"` を設定。
- 実行コンポーネント
  - run_execution: ExecutionEngine 起動スクリプトを追加。
    - プロセス優先度を高く設定して実行。
    - 環境に応じて本番/ペーパートレード用の SQLite を切り替え（KABUSYS_ENV=paper_trading の場合は `data/paper_trading.db` を使用）。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立てと ExecutionEngine の起動・停止ロジックを実装。
    - 停止用フラグ（data/stop_requested.flag）および PID ファイル（data/execution.pid）に対応。
  - run_monitoring: SystemMonitor ポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を指定可能（デフォルト 60 秒）。
    - 監視は環境に関わらず本番 sqlite_path を使用して監視データを記録。
    - 停止フラグ検知でループを終了。例外時にもログを出力して継続。
- 設定管理
  - config.py: 環境変数読み込み・設定取得用の Settings クラスを実装。
    - 自動 .env ロード（プロジェクトルートを .git または pyproject.toml を基準に検出）。
    - 必須変数取得時の検査・未設定時の ValueError 投出。
    - 各種設定（DB パス、Paper Trading 設定、監視閾値、PID/kill flag パスなど）をプロパティとして提供。
    - PAPER_FILL_MODE 等の妥当性チェックを実装。
  - config_setup.py: 対話式 .env 生成ウィザードを実装。
    - 既存 .env 読み込み、秘密値マスク表示、確認後に .env を保存。
    - デフォルト値や選択肢を用意。
  - validate_config.py: 起動前の設定検証 CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL 検証、DB パスの親ディレクトリチェック、config/*.yaml の存在および YAML パース検証（PyYAML があれば実施）。
    - --strict オプションで警告を FAIL 扱いに可能。
- ポートフォリオ構築ライブラリ (pure functions)
  - portfolio.portfolio_builder
    - select_candidates: シグナルのスコア降順選定（同点時は signal_rank でタイブレーク）。
    - calc_equal_weights / calc_score_weights: 等配分・スコア加重配分を実装。全スコアが 0 の場合は等配分にフォールバックして警告。
  - portfolio.risk_adjustment
    - apply_sector_cap: セクター集中上限（max_sector_pct）を適用して候補を除外。
    - calc_regime_multiplier: market regime に応じた投下資金乗数（bull/neutral/bear）を提供。未知レジームは警告してフォールバック。
  - portfolio.position_sizing
    - calc_position_sizes: allocation_method (= "risk_based" / "equal" / "score") に基づく株数計算を実装。
    - 単元株（lot_size）丸め、1銘柄上限、aggregate cap（available_cash）に基づくスケーリング、cost_buffer を考慮した保守的見積りを実装。
- ユーティリティ
  - utils.logging_setup: 統一ログ設定ユーティリティを追加。
    - stdout に StreamHandler、日次ローテーションの TimedRotatingFileHandler（デフォルト logs/<app_name>.log）を設定。
    - ログディレクトリを自動作成。失敗時はファイル出力をスキップしてコンソールログのみ実行。
    - デフォルトで 30 日分のログを保持。
    - コンソール出力を stderr ではなく stdout に出す設計。
  - utils.process_priority: プロセス優先度・CPU affinity 設定を追加。
    - Windows と POSIX（Linux/Mac/FreeBSD）差分を吸収して nice / priority を設定。
    - set_cpu_affinity により最初の N コアにプロセスを固定する機能を提供。
    - 権限不足等のケースは警告してスキップ。
- ツール群
  - tools.paper_verification_report: Paper Trading の検証レポート生成スクリプトを追加。
    - 稼働率・注文成功率・送信率・レイテンシ（P95）などを計算して PASS/FAIL 判定。
    - デフォルト DB パスは data/paper_trading.db。--db / 環境変数で上書き可能。
    - P95 計算、平均/最大レイテンシ、リスク却下数の集計を実装。
- 研究モジュール（骨格）
  - research.factor_research: ファクター計算モジュールの骨格を追加（momemtum 等の指標計算を想定）。
    - DuckDB 接続を受け取り prices_daily / raw_financials を参照して計算する設計。
    - モメンタム指標（1M/3M/6M、MA200乖離）、ATR、流動性指標などを想定（実装途中の関数あり）。

### 変更 (Changed)
- 監視・実行プロセスの優先度設定箇所を統一
  - run_monitoring および run_execution の起動時に set_process_priority("high") を呼び出すようにしてプロセス優先度を高く設定。
- DB 関連
  - monitoring の初期化は起動時に idempotent に init_monitoring_db を呼び出して監視テーブルの存在を保証。
  - paper_trading 実行時は本番 DB と完全に分離された専用 SQLite パスを使用する設計（データ混在防止）。

### 修正 (Fixed)
- .env パーサーの堅牢化
  - export KEY=val 形式、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメントの扱いなどを正しくパースする実装を導入。
  - 値の不正（数値等）に対して明確な警告・例外を出すように調整。
- MONITOR_POLL_INTERVAL の安全化
  - 指定が 0 以下や不正な文字列の場合はデフォルト（60 秒）にフォールバックする処理を追加。
- ロギング周りのフォールバック強化
  - ログディレクトリ作成やファイルハンドラ生成に失敗した場合でもコンソールログのみで継続可能にした（起動失敗を回避）。
- ExecutionEngine 起動ロジックの堅牢化
  - 起動時に既に停止フラグが立っている場合は起動を中止する保護を追加。
  - スレッド終了待ちや強制停止手順（engine.stop()）を実装して安全にシャットダウンするようにした。
- Paper verification の集計処理でデータ欠損（テーブル不存在／カラム欠損）を安全に扱うための例外ハンドリングを追加。

### ドキュメント (Documentation)
- 各 CLI スクリプト（config_setup, validate_config, tools.paper_verification_report）に使い方とオプションの説明を docstring と argparse のヘルプとして追加。
- portfolio / risk / sizing の各関数に詳細な docstring を追加し、設計注釈（PortfolioConstruction.md / StrategyModel.md に基づく旨）を明示。

### 既知の問題 (Known issues)
- research.factor_research の実装が途中で終わっている関数が存在する（calc_momentum 実装途中）。完全実装は今後のタスク。
- price の欠損 (0.0/None) によってセクターエクスポージャーやポジション計算が過少評価される可能性があるため、フォールバック価格（前日終値等）を使う拡張が TODO に残されている。
- OS 権限や環境依存（psutil の一部定数や CPU affinity）が原因で process priority / affinity の設定が失敗する場合は警告が出るのみで継続する設計。期待する振る舞いが得られない環境があり得る。

---

この CHANGELOG はコードベースから推測して作成したものであり、実際のリリースノートや設計仕様書とは差異がある可能性があります。必要に応じて日付・バージョン・項目の修正・追記を行ってください。