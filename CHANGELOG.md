# CHANGELOG

すべての注目すべき変更をこのファイルに記載します。フォーマットは「Keep a Changelog」に準拠します。

最新: [0.1.0] - 2026-04-23

## [Unreleased]
- （なし）

## [0.1.0] - 2026-04-23
初回リリース。日本株自動売買システム「KabuSys」の基本モジュール群を追加しました。主な追加内容は以下のとおりです。

### Added
- 基本パッケージ
  - パッケージ初期バージョンを追加（__version__ = 0.1.0）。
  - モジュールエクスポートの調整（kabusys パッケージの __all__）。

- 設定・環境変数管理
  - Settings クラス（kabusys.config）を追加。
    - J-Quants / kabuステーション / LINE API / DB パス /監視・システム閾値 など多くの設定プロパティを環境変数経由で提供。
    - KABUSYS_ENV の検証（development, paper_trading, live）。
    - PAPER_FILL_MODE の検証（instant/partial/never/reject）。
    - paper_trading 用 SQLite パスの分離（PAPER_TRADING_SQLITE_PATH）。
  - .env 自動読み込み機能を追加。
    - プロジェクトルート検出（.git または pyproject.toml を基準）により .env / .env.local を自動ロード。
    - OS 環境変数の保護（既存の OS 環境変数を上書きしない動作、.env.local による上書き対応）。
    - 複数の .env 形式・クォート・コメントのパースに対応（export KEY=val, シングル／ダブルクォート、エスケープ、インラインコメント処理等）。

- 設定関連 CLI
  - 環境設定ウィザード（kabusys.config_setup）。
    - 対話式で .env を作成・更新するウィザード。秘密情報はマスク表示。
    - .env の読み書きロジック、デフォルト値と選択肢サポートを実装。
  - 設定検証ツール（kabusys.validate_config）。
    - 必須環境変数のチェック（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD 等）。
    - KABUSYS_ENV / LOG_LEVEL / DB パス / config/*.yaml 存在・パースチェック。
    - PyYAML 未インストール時は YAML パース検証をスキップ（警告）。
    - --strict オプションで警告を失敗扱いにできる。

- 実行スクリプト / サービス
  - 監視プロセス起動スクリプト（kabusys.run_monitoring）。
    - SystemMonitor のポーリングループ起動。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。無効値はデフォルトにフォールバック。
    - 監視は常に本番（settings.sqlite_path）を参照して DB 初期化を行う。
    - stop flag（data/stop_requested.flag）検知で優雅に終了。
    - DuckDB 接続を併用。
  - 実行エンジン起動スクリプト（kabusys.run_execution）。
    - ExecutionEngine をスレッドで起動して監視。
    - KABUSYS_ENV=paper_trading 時は専用（分離された）SQLite（data/paper_trading.db）を使用。MockBrokerClient を利用して本番 DB と隔離。
    - 停止フラグ（data/stop_requested.flag）および PID 管理（data/execution.pid）に対応。
    - 依存コンポーネント（BrokerClientFactory, OrderRepository, OrderManager, RiskManager, Reconciler）を組み立てて実行。

- モニタリング / DB
  - 監視 DB 初期化ユーティリティ（init_monitoring_db）を呼び出すフローを追加（冪等に監視テーブルを保証）。
  - DuckDB を分析用に併用。

- ポートフォリオ構築関連（kabusys.portfolio）
  - portfolio_builder
    - select_candidates: BUY シグナルをスコア降順で選抜（同点は signal_rank でタイブレーク）。
    - calc_equal_weights / calc_score_weights: 等配分・スコア加重（全スコアが 0 の場合は警告を出して等配分にフォールバック）。
  - risk_adjustment
    - apply_sector_cap: セクター集中上限に基づく候補除外ロジック（売却予定銘柄をエクスポージャー計算から除外、"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数。未知レジームは 1.0 にフォールバック。
  - position_sizing
    - calc_position_sizes: リスクベース／等配分／スコア配分に対応した株数決定ロジック。
    - 単元株（lot_size）で丸め、max_position_pct・max_utilization に基づく個別・総合上限、cost_buffer による保守的コスト見積り、スケーリング＆残差処理などを実装。

- リサーチ（研究）モジュール
  - factor_research（部分実装を追加）
    - モメンタム / MA200 / ATR / 出来高等ファクター算出の方針と定数を定義。
    - DuckDB 接続を受け、prices_daily / raw_financials を参照して計算する設計（外部 API 呼び出しなし）。

- ユーティリティ
  - ロギング設定ユーティリティ（kabusys.utils.logging_setup）
    - setup_logging によりルートロガーへ StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション、30日保持）を設定。
    - ログディレクトリ作成失敗時はファイル出力をスキップしてコンソール出力のみで継続。
    - ログレベルとログディレクトリの解決順（引数 / 環境変数 / デフォルト）。
  - プロセス優先度・CPU affinity ユーティリティ（kabusys.utils.process_priority）
    - Windows / POSIX（Linux, macOS 等）差分を吸収してプロセス優先度を設定（psutil を使用）。
    - set_cpu_affinity により最初の N コアへ固定する機能を提供。
    - 権限不足や未対応環境では警告を出して安全にスキップ。

- ツール
  - Paper Trading 検証レポート生成スクリプト（kabusys.tools.paper_verification_report）
    - paper_trading DB（デフォルト data/paper_trading.db）から期間フィルタでデータを集計。
    - システム稼働率、注文成功率、送信率、リスク却下数、API レイテンシ（平均・最大・P95）を算出してレポート出力。
    - 基準値（稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200 ms）を用いて PASS/FAIL 判定を行う。

### Changed
- （初回リリースのため変更履歴なし）

### Fixed
- （初回リリースのため修正履歴なし）

### Deprecated
- （該当なし）

### Removed
- （該当なし）

### Security
- （該当なし）

---

備考:
- 多くのモジュールで「DB が存在しない / テーブルがない」場合に例外をキャッチして安全にフォールバックする設計を採用しています（例: validate_config の YAML パース、paper_verification_report の SQL エラー処理など）。
- 実行・監視スクリプトは停止フラグファイル（data/stop_requested.flag）を利用して外部からの優雅な停止をサポートします。
- Paper Trading（ペーパートレード）は完全に本番 DB と分離された動作を意図して実装されています（専用 SQLite を使用、MockBroker 経由の記録）。