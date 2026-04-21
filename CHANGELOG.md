KEEP A CHANGELOG
すべての重要な変更をこのファイルに記載します。
このプロジェクトは Keep a Changelog の規約に準拠します。
（訳注: 以下はソースコードから推測して作成した初期リリースの変更履歴です）

Unreleased
- （なし）

[0.1.0] - 2026-04-21
Added
- 初回リリース: KabuSys 日本株自動売買システムの基本コンポーネントを追加。
  - 実行/監視
    - run_execution.py: ExecutionEngine を起動するエントリポイント。KABUSYS_ENV=paper_trading の場合は MockBroker を使用して paper_trading 用 DB に記録し、本番 DB と分離して動作。
    - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプト。MONITOR_POLL_INTERVAL 環境変数で間隔を上書き可能（デフォルト 60 秒）。監視は環境にかかわらず本番 sqlite_path を使用する設計。
    - 停止制御: プロジェクト内 data/stop_requested.flag を監視して安全にシャットダウン。
    - PID 管理: execution 用の pid ファイル (data/execution.pid) をサポート。
  - 設定・環境管理
    - config.py: 環境変数・設定のラッパー（Settings クラス）を提供。デフォルト値、バリデーション（KABUSYS_ENV、LOG_LEVEL、PAPER_FILL_MODE など）を実装。
      - デフォルトパス: DUCKDB_PATH=data/kabusys.duckdb、SQLITE_PATH=data/monitoring.db、PAPER_TRADING_SQLITE_PATH=data/paper_trading.db。
      - 自動 .env ロード: プロジェクトルート（.git / pyproject.toml を基準）から .env と .env.local を自動読み込み。KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化対応。
      - .env パース: export 形式、引用符付き文字列（バックスラッシュエスケープ含む）、インラインコメントの扱い等に対応。
    - config_setup.py: 対話式ウィザードで .env を生成/更新。機密項目はマスク表示、デフォルト値/選択肢を提示。
    - validate_config.py: 起動前検証 CLI。必須環境変数や config/*.yaml の有無、ファイルパスの親ディレクトリ存在チェック、--strict オプションで警告をエラー扱いにできる。
  - ポートフォリオ構築
    - portfolio モジュールを提供（純粋関数群、DB 非依存、メモリ内計算）
      - portfolio_builder.py
        - select_candidates: BUY シグナルをスコア降順で選定。タイブレークは signal_rank を用いる。
        - calc_equal_weights / calc_score_weights: 等金額・スコア加重の重み計算。全スコアが 0 の場合は等分配へフォールバック。
      - risk_adjustment.py
        - apply_sector_cap: セクター集中抑制ロジック。既存保有を基にセクター別露出を計算し、上限（max_sector_pct）を超えるセクターの新規候補を除外（"unknown" セクターは除外対象外）。
        - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数を返す（デフォルトマップ: bull=1.0, neutral=0.7, bear=0.3）。未知レジームは 1.0 にフォールバック。
      - position_sizing.py
        - calc_position_sizes: 等配分・スコア配分・リスクベース配分をサポート。単元株（lot_size）で丸め、ポートフォリオおよび per-stock の上限を考慮。合計投資が利用可能現金を超える場合はスケーリングを行い、残余キャッシュで端数を lot 単位で配分するロジックを実装。cost_buffer により手数料・スリッページを保守的に見積もる。
  - 実行関連コンポーネント（概要）
    - execution パッケージ内に BrokerClientFactory、ExecutionEngine、OrderManager、OrderRepository、Reconciler、RiskManager 等の依存コンポーネントを組み合わせて ExecutionEngine を立ち上げる設計を導入。RiskManager には初期設定（例: max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）を使用。
  - 監視・分析
    - monitoring.monitoring_db: 監視用 DB 初期化ユーティリティ（init_monitoring_db）。run_execution/run_monitoring から冪等に呼び出してテーブル存在を保証。
    - tools/paper_verification_report.py: ペーパートレード結果の検証レポート生成スクリプトを追加。稼働率、注文成功率、送信率、P95 レイテンシなどの指標を算出し、PASS/FAIL を判定する閾値を定義（稼働率 99%、成立率 90% など）。--from/--to/--db オプションに対応。
  - データ分析基盤
    - DuckDB を利用する設計（duckdb_path を Settings で扱う）。research モジュール（factor_research.py）により prices_daily/raw_financials を使ったファクター計算を想定（モメンタム/バリュー/ボラティリティ/流動性など）。
  - ユーティリティ
    - utils/logging_setup.py: 共通のログ設定関数 setup_logging を提供。StreamHandler（stdout）と TimedRotatingFileHandler（デイリーローテート、30 日分保持）を設定。LOG_DIR 環境変数・引数でログ出力先を指定可能。既存ハンドラは上書き（重複防止）。
    - utils/process_priority.py: クロスプラットフォームでプロセス優先度（high/normal/low）および CPU affinity を設定するユーティリティ。Windows/Linux/macOS 等の差分を吸収し、権限不足などは警告でスキップ。
  - パッケージ情報
    - パッケージバージョンを __version__ = "0.1.0" として設定。

Changed
- （初回リリースのため該当なし）

Fixed
- ログ出力周りでディレクトリ作成に失敗した場合、ファイルハンドラの作成をスキップしてコンソール出力のみで継続するようフォールバックを実装。
- monitoring と execution 起動時に監視 DB 初期化を冪等に行う（init_monitoring_db を呼ぶことでテーブル存在を保証）。

Deprecated
- （初回リリースのため該当なし）

Removed
- （初回リリースのため該当なし）

Security
- config_setup にて .env を生成する際、機密情報のマスク表示を行い、.env を Git にコミットしないよう注意書きを追加。

Notes / 備考
- run_monitoring は監視 DB を環境に依らず本番 sqlite_path を使用する仕様になっているため、paper_trading と本番データの分離が必要な運用では注意が必要です（ExecutionEngine は KABUSYS_ENV に応じて paper_sqlite_path を使い分けます）。
- .env の自動ロードはプロジェクトルートが特定できない場合はスキップされます。必要に応じて KABUSYS_DISABLE_AUTO_ENV_LOAD で自動ロードを無効化できます。
- 一部モジュール（research 等）は DuckDB テーブル（prices_daily, raw_financials 等）を前提としており、適切なデータ投入が必要です。

--- 
（この CHANGELOG はソースコードの内容から推測して作成しています。実際の変更履歴やリリース日付はプロジェクトの管理記録に従って調整してください。）