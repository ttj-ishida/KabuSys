# Changelog

すべての重要な変更履歴を記録します。本ファイルは Keep a Changelog の形式に準拠します。

## [Unreleased]
（なし）

## [0.1.0] - 2026-04-19

### Added
- 基本アプリケーション構成を実装
  - パッケージバージョン: `kabusys.__version__ = "0.1.0"` を導入。
- 起動 / 実行用スクリプト
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV による paper_trading モードに対応。paper_trading 時は MockBrokerClient を使用し、data/paper_trading.db を専用 DB として利用して本番 DB と分離。
    - エンジン起動前に停止フラグ（data/stop_requested.flag）をチェックし、既に立っている場合は起動をスキップ。
    - 実行中は別スレッドで engine.run_session を実行し、停止フラグ検知で安全に停止する仕組みを実装。
    - 起動時に PID ファイルを書き出すための pid_file パスをサポート。
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。不正な値はデフォルトにフォールバックして警告を出力。
    - 監視処理は環境に関係なく本番用 sqlite_path を使用する設計（監視データは一元管理）。
    - 停止フラグ検知でループを終了、KeyboardInterrupt に対しても安全に終了して DB 接続をクローズ。
- 設定管理
  - config.py: 環境変数/.env 読み込みと Settings クラスを実装。
    - プロジェクトルートの自動検出（.git または pyproject.toml を基準）。ルートが見つからない場合は自動ロードをスキップ。
    - .env および .env.local の読み込み順序を実装（OS 環境変数を保護する仕組み）。
    - 複雑な .env 行のパースに対応（export プレフィックス、クォート文字・バックスラッシュエスケープ、行末コメント処理等）。
    - 必須環境変数取得ヘルパー `_require` と各種プロパティ（DB パス、API トークン、各種閾値、環境判定など）を提供。
    - PAPER_FILL_MODE の妥当性チェックや KABUSYS_ENV / LOG_LEVEL のバリデーションを実装。
- 設定作成/検証 CLI
  - config_setup.py: 対話式ウィザードで .env を初期作成 / 更新する CLI を追加。
    - シークレット項目はマスク表示、既存 .env を読み込んで Enter で再利用可能。
    - ファイル書き出しテンプレートと確認プロンプトを実装。
  - validate_config.py: 起動前に .env と config/*.yaml を検証する CLI を追加。
    - 必須環境変数の存在チェック、KABUSYS_ENV / LOG_LEVEL の検証、DB パスの親ディレクトリ確認、config/*.yaml の存在・パース検証（PyYAML がない場合は警告）など。
    - --strict オプションで警告を FAIL 扱いにできる。
- ロギング / プロセスユーティリティ
  - utils/logging_setup.py: 統一ロギング設定ユーティリティを追加。
    - stdout への StreamHandler と日次ローテーション（TimedRotatingFileHandler）で logs/<app_name>.log に出力（30日保持）。
    - LOG_DIR 作成に失敗した場合はファイル出力をスキップしてコンソールのみで継続。
    - 既存ハンドラをクリアして二重設定を防止。
  - utils/process_priority.py: プロセス優先度および CPU affinity 設定ユーティリティを追加。
    - Windows/Linux/Mac（POSIX）の差分を吸収して set_process_priority(level) を提供（"high"/"normal"/"low"）。
    - set_cpu_affinity(cpu_count) でプロセスを先頭 N コアに固定する機能を提供。
    - アクセス権限や未対応 OS の場合は警告を出して安全にスキップ。
- ポートフォリオ構築関連（純粋関数群）
  - portfolio/portfolio_builder.py
    - select_candidates: BUY シグナルをスコア降順で選定（タイブレーク: signal_rank）。
    - calc_equal_weights: 等金額配分の重み計算。
    - calc_score_weights: スコア比率で重み算出。全てのスコアが 0 の場合は等配分にフォールバックして警告。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中上限チェック。既存ポジションを考慮して新規候補を除外。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数を返す（未知レジームは 1.0 でフォールバックし警告）。
  - portfolio/position_sizing.py
    - calc_position_sizes: allocation_method（"risk_based" / "equal" / "score"）に応じた発注株数計算を実装。
    - 単元株（lot_size）丸め、1銘柄上限・aggregate cap のスケールダウン、cost_buffer（手数料/スリッページ見積）を考慮した安全な配分ロジックを実装。
- Paper Trading 検証ツール
  - tools/paper_verification_report.py: Paper Trading 用検証レポート生成ツールを追加。
    - DB（PAPER_TRADING_SQLITE_PATH / --db）から system_status / trade_logs / risk_logs を集計して稼働率・注文成功率・送信率・レイテンシ（平均/最大/P95）等を出力。
    - レポートは閾値（稼働率 >= 99%、注文成功率 >= 90%、送信率 >= 95%、P95 <= 200 ms）に基づく PASS/FAIL 判定を表示。
    - 日付フィルタ（--from / --to）に対応。P95 の計算は簡易実装（サンプル数が小さい場合も対応）。
- research/factor_research.py （ファクター計算基盤）
  - DuckDB 接続を受け取り prices_daily / raw_financials を用いたモメンタム等のファクター計算設計を開始（モジュールの冒頭実装を含む）。関数は SQL + Python での計算を想定。

### Changed
- なし（初期リリース）

### Fixed
- .env 読み込みの堅牢化
  - export プレフィックスやクォート内のバックスラッシュエスケープ、行末コメント処理などに対応し、一般的な .env フォーマットのバリエーションを正しく処理するように改善。
- ログディレクトリ作成失敗時のフォールバック
  - logging_setup: ログディレクトリ作成に失敗した場合でもコンソールログのみで処理を続行するようにし、例外で起動が止まらないように改善。
- プロセス優先度設定の安全化
  - process_priority: 権限不足や未実装 API に対して警告を出してスキップするハンドリングを追加。

### Notes
- 初期実装のため、以下は今後の改善候補です：
  - position_sizing の price フォールバック（価格が欠損した場合の適切な扱い）。
  - portfolio の lot_size を銘柄毎に持たせる拡張（現状は全銘柄共通）。
  - research モジュールの完全実装とテストケース追加。
  - 各コンポーネントのユニットテストおよび統合テストの充実。

---

この CHANGELOG はソースコードから推測して作成しています。実際の開発履歴やコミットログと差異がある場合があります。必要であれば特定の変更点をコミット単位で洗い出してさらに詳細な履歴に更新できます。