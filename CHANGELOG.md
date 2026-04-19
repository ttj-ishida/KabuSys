# Changelog

すべての重要な変更をこのファイルに記録します。  
このファイルは Keep a Changelog の形式に準拠しています。  
リリース日はコードベースから推測して付与しています。

※ 内容は提供されたソースコードから推測して作成しています。

## [0.1.0] - 2026-04-19

### Added
- プロジェクト初期実装
  - パッケージ識別子を含むパッケージ初期化 (src/kabusys/__init__.py, __version__ = 0.1.0)。
- 実行系・監視系起動スクリプトを追加
  - run_execution.py
    - ExecutionEngine 起動スクリプトを実装。
    - KABUSYS_ENV=paper_trading 時は paper_trading 用の SQLite (デフォルト: data/paper_trading.db) を使用する分離設計。
    - プロセス優先度を High に設定し、PID ファイル操作、停止フラグ (data/stop_requested.flag) を監視して安全に停止可能。
    - BrokerClientFactory を用いたブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組立てを実装。
  - run_monitoring.py
    - SystemMonitor ポーリングループ起動スクリプトを実装。
    - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で上書き可能（デフォルト 60 秒、無効値はデフォルトにフォールバック）。
    - 監視は環境に関わらず本番 sqlite_path を利用して監視テーブルを初期化。
    - 停止フラグ検出でループを終了、KeyboardInterrupt に対応。
- 環境設定/検証用 CLI を追加
  - config_setup.py
    - 対話式ウィザードで .env を初期作成 / 更新できるツール。
    - 複数の設定項目 (KABUSYS_ENV, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DUCKDB_PATH, SQLITE_PATH, LINE 等) を対話で入力。
    - 既存 .env の読み込みとマスク表示（シークレット）に対応。
  - validate_config.py
    - .env と config/*.yaml の構成検証スクリプトを実装。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性チェック、DB パスや YAML ファイルの存在/パース検証を実施。
    - --strict オプションにより警告も失敗扱いにできる。
- 環境変数読み込みの強化
  - config.py
    - プロジェクトルート検出ロジックを実装（.git / pyproject.toml を探索）。これにより CWD に依存しない .env 自動読み込みを実現。
    - .env/.env.local の読み込み順 (OS 環境変数 > .env.local > .env)、.env のパースで以下に対応:
      - export キーワード、クォート付き値（エスケープ処理含む）、インラインコメント処理（クォート無し時の条件付きコメント認識）。
    - protected オプションを用いた既存 OS 環境変数の保護（上書き防止）。
    - Settings クラスで各種設定値（パス、閾値、モードなど）をプロパティとして提供。PAPER_FILL_MODE 等の入力検証を実施。
- ロギング / プロセス制御ユーティリティを追加
  - utils/logging_setup.py
    - ルートロガーに StreamHandler (stdout) と TimedRotatingFileHandler（日次、30 日保持）を設定する共通セットアップ関数を実装。
    - LOG_DIR 作成失敗時も安全にコンソール出力へフォールバック。
    - ログレベル/ログディレクトリの解決順を明示。
  - utils/process_priority.py
    - プロセス優先度（high/normal/low）を Windows / POSIX 間で吸収するユーティリティを実装（psutil ベース）。
    - CPU affinity を最初の N コアに固定する set_cpu_affinity を提供。
    - アクセス権限不足や未対応プラットフォーム時に警告を出してスキップする堅牢性を確保。
- ポートフォリオ構築関連の純粋関数群を追加（DB 参照なし）
  - portfolio/portfolio_builder.py
    - select_candidates: BUY シグナルをスコア降順で選択（同点時は signal_rank でブレーク）。
    - calc_equal_weights: 等金額配分。
    - calc_score_weights: スコア加重配分（全て 0 の場合は等金額にフォールバックして警告）。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中制限。既存保有を考慮して超過セクターの候補除外を実装（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull/neutral/bear、未知値は警告して 1.0 にフォールバック）。
  - portfolio/position_sizing.py
    - calc_position_sizes: 複数配分方法 (risk_based / equal / score) に対応した発注株数計算。
    - 単元株（lot_size）丸め、per-position 上限・aggregate キャップ、コストバッファ (slippage/commission を見込む) に基づくスケーリングを実装。
    - aggregate cap 超過時のスケールダウンと残余キャッシュを活用した端数配分ロジックを実装。
- Paper Trading 検証ツールを追加
  - tools/paper_verification_report.py
    - paper_trading SQLite DB からシステム稼働率、注文成功率、送信率、レイテンシ指標 (avg/max/P95) を集計し、基準値（稼働率 99%、成功率 90% など）に基づく PASS/FAIL レポートを出力。
    - CLI オプション: --from/--to（期間指定）、--db（DB パス指定）。環境変数 PAPER_TRADING_SQLITE_PATH も参照。
- research/factor_research.py（ファクター計算基盤）
  - ファクター計算モジュールの骨格を追加（モメンタム・MA200・ATR 等の定義と計算方針を記載）。DuckDB 接続を受けて prices_daily / raw_financials を参照する設計方針を反映。
  - （ファイル途中までの実装：モメンタム計算の準備が含まれる）

### Changed
- ログ出力の標準出力先を stdout に統一
  - logging_setup で StreamHandler を stdout に割り当て、Task Scheduler / cron 等で stdout/stderr リダイレクト時の扱いを配慮。
- .env の自動読み込みをプロジェクトルート判定に基づく方式に変更
  - カレントワーキングディレクトリに依存しないため、パッケージ配布後も安定して動作することを想定。

### Fixed
- 環境変数パースの頑健性向上
  - シングル/ダブルクォート内のバックスラッシュエスケープ対応や、インラインコメントの誤認を低減。
- 起動時の DB 初期化の冪等化
  - init_monitoring_db を実行して監視テーブルの存在を保証（重複実行を許容する設計）。

### Documentation
- 各モジュールに docstring/usage コメントを追加
  - run_monitoring/run_execution/config_setup/validate_config/tools 等に使用方法や挙動説明を明記。

### Internal / Misc
- コード設計方針・TODO コメントを複数箇所に記載
  - 例: position_sizing の将来的な lot_size 銘柄別対応、risk_adjustment の価格フォールバック検討、research モジュールの計算窓サイズ等。

---

今後の予定（想定）
- research/factor_research の完全実装（ファクター算出、正規化、出力フォーマット統一）。
- ExecutionEngine / SystemMonitor の単体テスト追加、CLI パッケージ化（entry_points）の整備。
- config/*.yaml のテンプレート生成スクリプト改善とサンプルの充実。

以上。