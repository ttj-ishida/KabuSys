# Changelog

すべての注目すべき変更はこのファイルに記録します。フォーマットは Keep a Changelog に準拠しています。

## [Unreleased]


## [0.1.0] - 2026-04-19
初回リリース。

### Added
- パッケージ初期実装を追加（__version__ = 0.1.0）。
- 実行用エントリスクリプト
  - run_execution.py
    - ExecutionEngine を起動するランチャーを追加。
    - KABUSYS_ENV=paper_trading の場合は本番 DB と分離して PAPER_TRADING_SQLITE_PATH（デフォルト: data/paper_trading.db）を使用し、MockBrokerClient 相当の振る舞いでペーパートレード運用が可能。
    - 起動時にプロセス優先度を "high" に設定（utils.process_priority.set_process_priority を利用）。
    - 停止制御用 stop flag（data/stop_requested.flag）および実行 PID ファイル（data/execution.pid）を利用。
    - duckdb 接続をサポート（analytics 用 duckdb_path）。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL によるポーリング間隔の上書きをサポート（デフォルト 60 秒）。無効値はデフォルトにフォールバックし警告ログを出力。
    - 監視は環境にかかわらず本番用 sqlite_path を使用して監視テーブルを初期化（init_monitoring_db）。
    - 停止フラグ（data/stop_requested.flag）検出で安全にループ終了。
- 設定管理
  - config.py
    - .env 自動読み込み機能を実装（プロジェクトルート検出: .git または pyproject.toml を探索）。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動読み込みを無効化可能。
    - .env の読み込み優先度: OS 環境変数 > .env.local > .env。既存 OS 環境変数は保護され上書きされない。
    - 強力な .env パーサ実装（export 形式、シングル/ダブルクォート内のエスケープ、行末コメントの取り扱いなどに対応）。
    - Settings クラスを導入して環境変数をラップ（J-Quants、kabu API、LINE、DBパス、監視閾値、システムフラグなど）。
    - paper_fill_mode の検証（instant/partial/never/reject のみ有効）。
    - KABUSYS_ENV / LOG_LEVEL 等のバリデーションを行い不正値で ValueError を送出。
    - settings インスタンスをモジュールレベルでエクスポート。
- 設定ユーティリティと CLI
  - config_setup.py
    - 対話式 .env 作成/更新ウィザードを追加。
    - デフォルト値提示、シークレットマスク表示、選択肢サポート、.env ファイルへの安全な書き込みを提供。
    - 生成後に validate_config の実行を推奨するメッセージを表示。
  - validate_config.py
    - 起動前チェック用 CLI を追加（必須環境変数の存在確認、KABUSYS_ENV/LOG_LEVEL の妥当性、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在確認と YAML パースチェック）。
    - --strict モードをサポート（警告を FAIL 扱いにする）。
    - PyYAML 未インストール時は YAML チェックをスキップして警告を出力。
- ログ・プロセスユーティリティ
  - utils/logging_setup.py
    - 統一ロギング設定ユーティリティを追加。
    - StreamHandler を stdout に出力し、TimedRotatingFileHandler（日次ローテーション、30日保持）を併用。
    - ログディレクトリ作成失敗時にファイル出力をスキップするフォールトトレラントな実装。
    - ログレベル・ログディレクトリの解決順をサポート（引数 > 環境変数 > デフォルト）。
  - utils/process_priority.py
    - クロスプラットフォーム（Windows / POSIX）でのプロセス優先度設定を実装（psutil を使用）。
    - CPU affinity 設定関数を追加（set_cpu_affinity）。
    - アクセス権限不足や未対応 OS では安全にスキップして警告を出力。
- ポートフォリオ構築ライブラリ（純粋関数群）
  - portfolio/portfolio_builder.py
    - select_candidates: スコア基準で上位 N を選択（タイブレーク: signal_rank）。
    - calc_equal_weights / calc_score_weights: 等金額配分・スコア加重配分を実装。全スコア 0 の場合は等配分にフォールバック。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター別集中上限（max_sector_pct）により新規候補を除外するロジックを実装。既存保有のエクスポージャ計算、売却予定銘柄の除外をサポート。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数を実装（未知レジームは 1.0 にフォールバック）。
  - portfolio/position_sizing.py
    - calc_position_sizes: risk_based / equal / score の各配分方式に対応した株数算出ロジックを実装。
    - 単元株（lot_size）で丸め、1銘柄上限・全体利用上限（max_utilization）やコストバッファを考慮した aggregate cap スケーリングを実装。
    - 価格未取得時のスキップやログ出力、将来の拡張ポイント（銘柄別 lot_size 等）を明記。
- 研究（research）モジュール
  - research/factor_research.py（骨組み実装）
    - DuckDB 接続を受け取り、prices_daily / raw_financials を参照してモメンタム・Value・Volatility・Liquidity 等のファクターを計算する設計を追加。
    - calc_momentum のインターフェースと設計注記（MA200、1M/3M/6M リターン、データ不足時は None を返す等）を実装（実装途中の箇所あり）。
- ツール
  - tools/paper_verification_report.py
    - ペーパートレード検証レポート生成 CLI を追加。
    - 指標: 稼働率（uptime）、注文成功率（fill_rate）、送信率（send_rate）、API レイテンシ（avg/max/P95）などを集計。
    - デフォルト閾値（例: uptime >= 99.0%、fill_rate >= 90% 等）を定義し PASS/FAIL 判定を行う。
    - --from / --to / --db オプションをサポートし、PAPER_TRADING_SQLITE_PATH 環境変数からの DB パス指定も可能。
    - DB 存在チェックやテーブル欠如時のフォールトトレラントな扱いを実装。
- パッケージエクスポート
  - portfolio モジュールをトップレベルでまとめてエクスポート（select_candidates 等を再公開）。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- （初回リリースのため該当なし）

---

注: 上記はコードベースから推測した主な機能・設計上の変更点と挙動の要約です。実際のリリースノートはコミット履歴／リポジトリの変更履歴と照合して作成してください。