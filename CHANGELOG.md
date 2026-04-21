# Changelog

すべての重要な変更をここに記録します。本ファイルは「Keep a Changelog」形式に準拠しています。日付はコミット内容から推測して記載しています。

## [Unreleased]

（現在未リリースの変更はありません）

## [0.1.0] - 2026-04-21

初回リリース。主要な機能・ユーティリティ・CLI を含む日本株自動売買システムの骨子を実装しました。

### Added
- 基本パッケージ情報
  - パッケージバージョンを `__version__ = "0.1.0"` として定義。

- 実行スクリプト
  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV が `paper_trading` の場合は Paper Trading 専用 SQLite（`data/paper_trading.db`、環境変数で上書き可）を使用し、本番 DB と分離して動作。
    - BrokerClientFactory を通じたブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立てを行い、ExecutionEngine を別スレッドで実行。data/stop_requested.flag と execution.pid による停止・PID管理をサポート。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL` で上書き可能（デフォルト 60 秒）。監視用 DB は環境にかかわらず本番用 sqlite_path を使用する挙動を明示。

- 設定周り
  - config.py
    - Settings クラスを実装し、環境変数経由で各種設定を取得（J-Quants, kabuAPI, LINE, DB パス, 監視閾値など）。
    - プロジェクトルート自動検出（.git または pyproject.toml）に基づく .env 自動読み込み機能を実装（`.env` → `.env.local` の優先順）。OS 環境変数を保護する仕組みあり。自動ロードは `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
    - `paper_fill_mode`（Paper Trading の模擬約定モード）や `paper_sqlite_path` 等のプロパティを提供。環境値検証（有効値チェック）や便利な bool プロパティ（is_live / is_paper / is_dev）を追加。

  - config_setup.py
    - 対話式ウィザードで `.env` を生成・更新する CLI を追加。
    - シークレット入力、選択肢、デフォルト値対応。既存 .env の読み込み・Enter で既存値継承、保存確認をサポート。

  - validate_config.py
    - 起動前に設定不備を検出する検証 CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性チェック、DB パス親ディレクトリ存在確認、config/*.yaml の存在および（PyYAML があれば）パース検証、KABUSYS_ENV=live 時の追加ガード（LINE 通知設定や Kill Switch の危険設定検知）を実装。
    - `--strict` オプションで警告も失敗扱いにするモードをサポート。

- ロギング・プロセス管理ユーティリティ
  - utils/logging_setup.py
    - ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（ファイル、日次ローテーション、30日保持）を設定する共通ユーティリティを追加。
    - ログディレクトリ自動作成、環境変数 / 引数によるログレベル・ログディレクトリ解決、既存ハンドラの上書き防止処理を実装。ファイル作成失敗時はコンソールのみで継続。
  - utils/process_priority.py
    - Windows / POSIX を吸収するプロセス優先度設定を実装（`set_process_priority("high"|"normal"|"low")`）。
    - CPU affinity を設定する `set_cpu_affinity` を追加（N コアに固定）。
    - psutil による実装で、権限不足や未対応環境では警告を出してスキップ。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py
    - 候補抽出（select_candidates）、等配分（calc_equal_weights）、スコア加重配分（calc_score_weights）を実装。スコアが全て 0 の場合は警告を出して等配分にフォールバック。
  - portfolio/risk_adjustment.py
    - セクター集中制限（apply_sector_cap）を実装。既存保有のセクター別時価から上限を超えるセクターの新規候補を除外する。unknown セクターは上限を適用しない。
    - 市場レジームに応じた投下資金乗数（calc_regime_multiplier）を実装（bull/neutral/bear をサポート、未知レジームはフォールバック）。
  - portfolio/position_sizing.py
    - position sizing を実装（allocation_method: "risk_based" / "equal" / "score"）。
    - 単元（lot_size）丸め、銘柄毎上限（max_position_pct）、aggregate cap（available_cash）を考慮したスケーリング、cost_buffer（手数料・スリッページ見積り）を用いた保守的見積り、残差を基にした lot 単位での追加配分ロジックを実装。

- Execution / Risk 設定
  - run_execution にて RiskManager の設定（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker_errors/window 等）を初期化。初期ポートフォリオ値は broker.get_available_cash() から取得。

- 監視・モニタリング
  - run_monitoring は SystemMonitor を初期化してポーリングループを実行（例外時のログ、停止フラグ検知による終了処理を実装）。監視 DB の初期化（init_monitoring_db）を呼び出す。

- Paper Trading 検証ツール
  - tools/paper_verification_report.py
    - Paper Trading 用 SQLite を解析し、システム稼働率（uptime）、注文成功率（fill rate）、送信率（send rate）、API レイテンシ（avg/max/P95）などのレポートを生成する CLI を追加。
    - P95 計算、日付フィルタ（--from / --to）、閾値による PASS/FAIL 判定（稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200 ms）を実装。
    - DB が存在しない場合のエラーメッセージ、欠損テーブルへの耐性（OperationalError を捕捉して N/A 扱い）を実装。

- データ分析 / リサーチ（途中実装）
  - research/factor_research.py（ファクター計算モジュール骨子）
    - Momentum / Value / Volatility / Liquidity の計算方針を定義。DuckDB 接続を受け取り prices_daily / raw_financials を参照して計算する設計（関数スケルトンと定数定義あり）。

### Changed
- N/A（初回リリースのため既知の変更履歴はありません）

### Fixed
- N/A（初回リリース）

### Security
- 環境変数の取扱いに注意喚起（config_setup に .env を絶対に Git にコミットしない旨のコメントを追加）。

### Notes / Implementation details（重要な挙動）
- .env 自動読み込みはプロジェクトルートが検出できない場合はスキップされます。
- .env パーサは export 形式、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントの基本的な処理に対応しています。
- run_monitoring は監視 DB に本番 sqlite_path を常に使用する設計（KABUSYS_ENV に無関係に本番監視 DB を参照）。
- run_execution は paper_trading モード時に DB を完全分離することで、本番 DB への誤操作リスクを低減します。
- ログは stdout（StreamHandler）へ出力し、ファイル出力が可能なら logs/<app_name>.log に日次ローテーションで保存されます。ログディレクトリ作成に失敗した場合はファイル出力をスキップして stdout のみで継続します。
- プロセス優先度・CPU affinity の設定は権限や OS に依存し、失敗した場合は警告を出して処理を続行します。

---

今後の改善候補（未実装・TODO）
- portfolio.position_sizing: 銘柄ごとの lot_size を stocks マスタから取得する拡張。
- price 欠損時のフォールバック（前日終値や取得原価など）を用いたエクスポージャー推定（risk_adjustment の TODO）。
- research/factor_research: 各ファクター計算の完全実装とユニットテスト・パフォーマンス最適化。
- validate_config: config/*.yaml のより詳細なスキーマ検証（JSON Schema 等）の導入検討。

（以上）