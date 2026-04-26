# Changelog

すべての注目すべき変更はこのファイルに記載します。
フォーマットは「Keep a Changelog」に準拠します。

※ この CHANGELOG は与えられたコードベースの実装内容から推測して作成しています。

## [Unreleased]

## [0.1.0] - 2026-04-26
追加（Added）
- 初期リリース: KabuSys 自動売買システムのコア機能群を追加。
- 実行スクリプト
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。  
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient（ペーパートレード）を使用し、paper_trading 用の SQLite DB（デフォルト data/paper_trading.db）に記録することで本番 DB と分離。
    - 起動時にブローカーから現金・ポジションを取得して起動時総資産を算出。
    - 実行エンジンは別スレッドで run_session を実行し、data/execution.pid に PID を管理。data/stop_requested.flag による停止検知に対応。
    - risk_config.yaml を読み込み、各パラメータの型・範囲チェック（max_position_pct 等）を実装。
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。  
    - MONITOR_POLL_INTERVAL 環境変数によるポーリング間隔上書き（デフォルト 60 秒）。不正値は警告を出してデフォルトにフォールバック。
    - 監視は環境にかかわらず本番 sqlite_path を使用して監視テーブルを初期化。
    - 停止フラグ（data/stop_requested.flag）検出による安全なループ終了、KeyboardInterrupt ハンドリングを実装。
    - 起動時にプロセス優先度を "high" に設定。
- 設定管理
  - config.py: Settings クラスを実装。環境変数から各種設定（DB パス、API トークン、閾値、環境種別など）を取得する。
    - .env 自動読み込み機能を実装（プロジェクトルート検出: .git または pyproject.toml 基準）。読み込み優先順位は OS 環境 > .env.local > .env。自動読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能。
    - .env ファイルのパースは export プレフィックス、クォート付き値、インラインコメントの扱いなどに対応。
    - paper_trading 用の PAPER_TRADING_SQLITE_PATH、PAPER_FILL_MODE（instant/partial/never/reject）対応。
    - 環境（KABUSYS_ENV）/ログレベルの検証、各種閾値プロパティを提供（CPU/MEM/DISK）。
- 設定ツール / 検証
  - config_setup.py: 対話式ウィザードを追加。.env の初期作成・更新を支援。シークレット項目はマスク表示。書き込み形式を定義して .env を生成。
  - validate_config.py: 設定検証 CLI を追加。  
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL 検証、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在と YAML パース検証（PyYAML がない場合は警告）等を実行。
    - --strict モードで警告を FAIL 扱いにできる。
- ポートフォリオ構築（Portfolio）
  - portfolio/portfolio_builder.py:
    - select_candidates: BUY シグナルをスコア降順（同点は signal_rank 昇順）で選出。
    - calc_equal_weights: 等金額配分を計算。
    - calc_score_weights: スコア加重配分を計算。全スコアが 0 の場合は等金額配分にフォールバック（警告ログ）。
  - portfolio/risk_adjustment.py:
    - apply_sector_cap: セクター集中制限を実装。既存保有のセクター比率が上限を超える場合、そのセクターの新規候補を除外（"unknown" セクターは制限対象外）。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に対する投下資金乗数を返す。未知レジームは警告のうえ 1.0 でフォールバック。
  - portfolio/position_sizing.py:
    - calc_position_sizes: 各銘柄の発注株数決定ロジックを実装（allocation_method: "risk_based" / "equal" / "score"）。  
      - リスクベース（risk_based）では risk_pct, stop_loss_pct を用いて単価あたりの株数を計算。単元株（lot_size）丸め、1銘柄上限 max_position_pct、投下資金上限 max_utilization、コストバッファ(cost_buffer) を考慮した aggregate スケールダウン／再配分ロジックを実装。
- 監視・検証ツール
  - tools/paper_verification_report.py: ペーパートレード検証レポート生成スクリプトを追加。  
    - 指標: システム稼働率（uptime）、注文成功率（fill rate）、送信率（send rate）、P95 レイテンシ等を算出し、閾値（稼働率 >= 99%、fill >= 90%、send >= 95%、P95 <= 200ms）に基づいて PASS/FAIL 判定を行う。期間指定 (--from/--to) と DB パス指定 (--db) に対応。
- ユーティリティ
  - utils/logging_setup.py: 統一的なログ設定ユーティリティを追加。  
    - StreamHandler（stdout）と TimedRotatingFileHandler（ログ日次ローテーション、30日保持）をルートロガーへ設定。既存ハンドラをクリアして二重設定を防止。ログディレクトリ作成失敗時はファイル出力をスキップして stdout のみで継続。
  - utils/process_priority.py: プロセス優先度および CPU affinity 設定ユーティリティを追加（Windows/Linux の差分を吸収）。（ファイルの一部は切り出しのため省略あり）

変更（Changed）
- なし（初回リリースのため該当なし）

修正（Fixed）
- なし（初回リリースのため該当なし）

セキュリティ（Security）
- なし（特記事項なし）

ドキュメント（Documentation）
- 各モジュールに docstring と利用例・引数説明を充実させ、挙動の説明をコード内コメントとして整備。
- config_setup による .env 生成で「.env を絶対に Git にコミットしないこと」を明示。

注記
- run_monitoring.py の挙動は監視データベース初期化を保証するために monitoring DB の初期化を必ず行う仕様になっています（環境に依らず本番 sqlite_path を使用）。
- risk_config.yaml の読み込みでは詳細なバリデーションを行い、不正な値は例外を発生させて起動を阻止する設計です。
- .env の自動ロードはプロジェクトルートの検出に依存するため、配布後や CWD と異なる場所で実行する場合でも正しく働くことを意図しています。

--- 

（必要に応じて今後の変更点を Unreleased セクションに追記してください）