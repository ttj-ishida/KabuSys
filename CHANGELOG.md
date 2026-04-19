# CHANGELOG

すべての変更点は Keep a Changelog の形式に準拠して記載しています。

注意: この CHANGELOG は提供されたコードベースの内容から推測して作成しています。実際のコミット履歴ではなく、ソースコードに明示されている機能追加・設計方針・重要な動作を要約したものです。

## [Unreleased]
- 特になし。

## [0.1.0] - 2026-04-19

### Added
- 基本的な自動売買フレームワークを実装（パッケージ名: kabusys）。
  - パッケージバージョンを 0.1.0 として定義（src/kabusys/__init__.py）。
- 実行用スクリプトを追加:
  - run_execution: ExecutionEngine を起動するエントリポイント。プロセス優先度を上げる処理とスレッドでの実行管理、停止フラグ検知に対応（src/kabusys/run_execution.py）。
    - KABUSYS_ENV=paper_trading の場合、専用のペーパートレード用 SQLite (PAPER_TRADING_SQLITE_PATH / data/paper_trading.db) を使用し、本番 DB と分離する挙動を実装。
    - BrokerClientFactory を用いたブローカークライアント生成、OrderRepository、OrderManager、RiskManager、Reconciler、ExecutionEngine の組み立て処理を組み込み。
    - Engine の PID ファイル管理、停止フラグ（data/stop_requested.flag）を検知して安全に停止する機構を実装。
  - run_monitoring: SystemMonitor のポーリングループ起動スクリプト（src/kabusys/run_monitoring.py）。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値は警告を出してデフォルトにフォールバック。
    - Monitoring は KABUSYS_ENV にかかわらず本番用 sqlite_path を使用する設計（監視データを一元化する意図）。
    - 停止フラグファイルでループ中断、KeyboardInterrupt による正常終了処理、内部例外発生時のログ出力とループ継続を行う。
- 設定管理:
  - Settings クラスを追加し、環境変数から各種設定を取得（src/kabusys/config.py）。
    - DuckDB/SQLite パス、PID/kill flag パス、閾値、ログレベル、実行環境判定プロパティ（is_live / is_paper / is_dev）などを提供。
    - PAPER_FILL_MODE の検証、有効値チェックを実装。
  - .env 自動ロード機能を実装:
    - プロジェクトルートを .git または pyproject.toml から検出して .env/.env.local をロード（自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
    - .env パーサは export プレフィックス対応、クォート／エスケープ、インラインコメント処理など堅牢なパースを実施。
- 設定関連の CLI を追加:
  - config_setup: 対話式ウィザードで .env の初期作成・更新を支援（src/kabusys/config_setup.py）。
    - シークレット項目はマスク表示、既存 .env の読み込みと Enter での再利用、保存前の確認を実装。
  - validate_config: .env と config/*.yaml の基本検証 CLI（src/kabusys/validate_config.py）。
    - 必須環境変数チェック（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD）、KABUSYS_ENV / LOG_LEVEL の妥当性、DB パスの親ディレクトリ存在チェック、YAML ファイルの存在とパースチェック（PyYAML が利用可能な場合）。
    - --strict オプションで警告も FAIL 扱いにする機能を実装。
- ログ設定ユーティリティを追加:
  - setup_logging: ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（日次、30日保持）を設定する共通ユーティリティ（src/kabusys/utils/logging_setup.py）。
    - ログレベル/ログディレクトリの解決順を定義し、ファイル出力の作成に失敗した場合はコンソール出力のみで継続するフォールバックを実装。
    - StreamHandler は stdout を用いる（cron 等で stdout/stderr を一本化する運用を考慮）。
- プロセス優先度・CPU affinity ユーティリティを追加:
  - set_process_priority: Windows と POSIX の差分を吸収して「high/normal/low」を設定。アクセス拒否等は警告でフォールバック（src/kabusys/utils/process_priority.py）。
  - set_cpu_affinity: 指定コア数にプロセスをピン留めする機能を提供（存在しない環境では警告でスキップ）。
- ポートフォリオ構築モジュール（純粋関数群）を追加（src/kabusys/portfolio/*）:
  - portfolio_builder:
    - select_candidates: スコア降順で上位 N を選択（タイブレークに signal_rank を使用）。
    - calc_equal_weights / calc_score_weights: 等金額配分・スコア加重配分。スコア合計が 0 の場合は等配分にフォールバック（警告）。
  - risk_adjustment:
    - apply_sector_cap: セクター別上限（max_sector_pct）を超過する場合、新規候補から除外するロジック（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じて投下資金乗数を返す。未知レジームは 1.0 にフォールバック（警告）。
  - position_sizing:
    - calc_position_sizes: allocation_method（risk_based/equal/score）に応じた株数計算を提供。
      - 単元 lot_size（デフォルト 100）で丸め、max_position_pct / max_utilization / cost_buffer を考慮した aggregate cap スケールダウン、残差配分ロジックを実装。
      - risk_based モードでは risk_pct, stop_loss_pct を用いたポジションサイズ計算。価格欠損時のスキップやログ出力あり。
- DuckDB 統合:
  - DuckDB 接続を受け取って分析・リサーチ処理を行う基盤（部分的に実装された research/factor_research.py）。prices_daily / raw_financials を参照して各種ファクターを計算する設計。
- Paper Trading 検証ツールを追加:
  - tools/paper_verification_report.py: ペーパートレード SQLite を読み取り検証レポートを生成する CLI。
    - システム稼働率、注文成功率（fill_rate）、送信率、リスク却下数、レイテンシ（avg/max/P95）を集計。
    - P95 計算、日付フィルタ、閾値（稼働率 99%, fill_rate 90%, send_rate 95%, P95 <= 200ms）に基づく PASS/FAIL 判定。
    - --from/--to/--db オプションに対応。

### Changed
- ログ出力方針:
  - コンソール出力は stderr ではなく stdout を使用するよう統一（setup_logging）。cron 等からの運用を想定。
- DB 初期化:
  - monitoring 用テーブルの初期化関数 init_monitoring_db を起動時に呼び出して冪等にテーブル存在を保証（run_monitoring/run_execution）。

### Fixed
- 環境変数パースの堅牢化:
  - .env パーサで export プレフィックス、クォート内のエスケープ、インラインコメント処理、無効行の無視を扱うように修正（src/kabusys/config.py / config_setup.py）。

### Security
- .env の取り扱いに関する注意を明示:
  - config_setup にて .env を生成する際、ファイルを絶対に Git にコミットしない旨をヘッダに記載（src/kabusys/config_setup.py）。

### Documentation / Misc
- 各モジュールに docstring と使用例を充実させ、設計方針や運用上の注意（例: レジーム乗数の意味、price 欠損時の TODO）を明記。
- validate_config と config_setup による起動前チェック / 設定ウィザードの追加により初期設定フローを改善。

---

今後の改善候補（ソース内コメントに基づく）
- price 欠損時のフォールバックロジック（前日終値や取得原価の利用）を実装してエクスポージャー算出精度を向上する。
- 銘柄ごとの lot_size をサポートする（stocks マスタに lot_size を持たせる等）。
- research/factor_research の実装完了および単体テスト追加。
- より詳細な監視アラート（LINE 通知等）や本番環境用のガードを強化する（validate_config の warn で指摘している項目など）。

もし特定の変更点やリリースノートの粒度（例: もっと詳細／簡潔）を調整したい場合は指示してください。