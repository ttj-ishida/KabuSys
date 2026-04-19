# Changelog

すべての重要な変更点をこのファイルに記録します。
フォーマットは「Keep a Changelog」に準拠します。

※ 本CHANGELOGはコードベースから推測して作成した要約です。実際のコミット履歴やリリースノートに合わせて適宜修正してください。

## [Unreleased]
- （なし）

## [0.1.0] - 2026-04-19
初回リリース。本バージョンは日本株自動売買システム「KabuSys」の基盤機能群を含みます。

### 追加 (Added)
- 実行/監視の起動スクリプト
  - run_execution: ExecutionEngine を起動する CLI スクリプトを追加。KABUSYS_ENV による paper_trading と live の切り分け、専用の paper_trading DB（data/paper_trading.db）を使用する実装を含む。停止フラグ（data/stop_requested.flag）および PID 管理をサポート。
  - run_monitoring: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は常に本番 sqlite_path を使用する設計。

- 設定管理/補助 CLI
  - config_setup: 対話式ウィザードで .env ファイルを作成・更新するツールを追加。必須/任意項目、シークレット扱いの入力、保存確認などを実装。
  - validate_config: .env および config/*.yaml の起動前チェックツールを追加。必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性、DB パスの親ディレクトリ確認、YAML パース検証（PyYAML が存在する場合）などを実装。--strict オプションで警告も失敗扱いに可能。

- 環境変数読み込み機能
  - 自動 .env ロード機能を実装（プロジェクトルート検出: .git または pyproject.toml を基準）。.env と .env.local の優先順位、OS 環境変数の保護（上書き禁止）に対応。
  - .env パーサは export 形式や引用符付き値、インラインコメントの扱い、エスケープシーケンスに対応。

- ポートフォリオ構築ライブラリ（純粋関数群）
  - portfolio.portfolio_builder: シグナルのソート（スコア降順・タイブレーク）、候補選定 select_candidates、等金額配分 calc_equal_weights、スコア加重 calc_score_weights（スコアが全て 0 の場合は等配分にフォールバック）。
  - portfolio.risk_adjustment: apply_sector_cap（セクター集中制限。既存ポジションのセクター比率が閾値を超える場合、新規候補を除外。'unknown' セクターは除外対象外）、calc_regime_multiplier（市場レジームに応じた資金乗数の決定。未知のレジームはフォールバックで 1.0）。
  - portfolio.position_sizing: calc_position_sizes（risk_based / equal / score の割り当て方式に対応）。損切り率・リスク率に基づく発注株数計算、単元（lot_size）丸め、aggregate cap（利用可能現金を超えた場合のスケールダウンと残差処理）などを実装。

- 実行関連ユーティリティ
  - utils/logging_setup: 統一的なロギング設定ユーティリティを追加。コンソール（stdout）ハンドラと日次ローテーションファイルハンドラ（TimedRotatingFileHandler、30 日分保持）を設定。LOG_DIR 作成失敗時はファイル出力をスキップしてコンソールのみで継続。
  - utils/process_priority: プロセス優先度（high/normal/low）および CPU affinity 設定ユーティリティを追加。Windows と POSIX（Linux/Mac 等）で差分を吸収。権限不足や未対応 OS の場合は警告を出してスキップ。

- Paper Trading 検証ツール
  - tools/paper_verification_report.py: ペーパートレード用 SQLite DB からレポートを生成するスクリプトを追加。システム稼働率、注文成功率・送信率、リスク却下数、API レイテンシ（平均・最大・P95）を集計し PASS/FAIL 判定を行う。閾値（稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200 ms）を定義。

- 研究用ファクター計算モジュール（骨組み）
  - research/factor_research.py: DuckDB 接続を受け取り prices_daily / raw_financials を使って各種ファクター（Momentum、Value、Volatility、Liquidity）を計算する設計。モメンタム計算の定数や API を定義。※ 実装は今後拡張予定（ファイル冒頭に設計方針を記載）。

- パッケージ情報
  - パッケージバージョン __version__ = "0.1.0" を設定。

### 変更 (Changed)
- デフォルト挙動 / 保守的フォールバックを多数採用
  - MONITOR_POLL_INTERVAL に不正な値が設定された場合はログ警告を出してデフォルト（60 秒）にフォールバック。
  - PAPER_FILL_MODE の不正値は ValueError を発生させ、使用者に明示する。
  - 設定ロード時、OS 環境変数を保護する仕組みによって明示的な override 動作を制御。

- ロギング方針
  - StreamHandler を stdout に向ける（stderr ではない）。cron 等からの stdout/stderr の一本化を考慮。

### 修正 (Fixed)
- 起動・終了ハンドリングの堅牢化
  - run_execution と run_monitoring は stop flag（data/stop_requested.flag）を監視して安全に停止できるように設計。KeyboardInterrupt を捕捉してクリーンに終了する。

- DB 初期化の冪等性
  - monitoring 用のテーブル初期化（init_monitoring_db）を起動時に呼び出して、監視テーブルが存在しない場合でも起動できるようにしている（冪等呼び出し）。

### 注意点 / 既知の制約 (Known Issues / Notes)
- apply_sector_cap のエクスポージャー計算は price_map に 0.0 が含まれる場合、過少評価になる可能性があり、将来的に前日終値や取得原価でのフォールバックを検討する旨の TODO コメントあり。
- position_sizing の単元丸めや aggregate cap のスケーリングは lot_size が全銘柄共通という前提。将来的には銘柄別 lot_size を導入する余地あり。
- research/factor_research.py は設計方針と定数を含むが、ファイル末尾に未完の実装（切り出し）あり。今後の実装が必要。
- 一部機能は psutil, duckdb, PyYAML 等外部パッケージに依存。これらが環境にない場合は機能制限（例: YAML 検証スキップ、psutil による優先度設定スキップ）が発生する。

### セキュリティ (Security)
- 環境変数や .env の取り扱いに関する注意喚起をツール内で行っている（.env を絶対に Git にコミットしない等）。secret な設定値は config_setup でマスク表示する。

---
参考: 本CHANGELOGはコード中のドキュメント文字列、コメント、定数、CLI 使用例などから推測して作成しました。実際の機能追加・修正履歴は Git のコミットメッセージ等を参照して正式に更新してください。