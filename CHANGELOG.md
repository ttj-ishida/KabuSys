# CHANGELOG

すべての重要な変更を記録します。本ファイルは Keep a Changelog の形式に準拠しています。

例: バージョン番号／日付はソースコードから推測した初期リリース日を使用しています。

## [Unreleased]
- 現在未リリースの変更点はありません。

## [0.1.0] - 2026-04-19
初期リリース。日本株自動売買システム「KabuSys」のコア CLI / ライブラリ群を導入します。

### Added
- 基本情報
  - パッケージバージョンを __version__ = "0.1.0" として追加。
  - パッケージ公開用に主要サブパッケージを __all__ に列挙 (data, strategy, execution, monitoring)。

- 実行スクリプト / デーモン
  - run_execution: ExecutionEngine 起動スクリプトを追加。
    - プロセス優先度を設定して起動。
    - KABUSYS_ENV に応じて paper_trading モードの DB 分離（data/paper_trading.db）を採用。
    - BrokerClientFactory によるブローカークライアントの抽象化を導入。
    - OrderRepository、OrderManager、RiskManager（RiskConfig）、Reconciler、ExecutionEngine の組み立てと実行。
    - 停止フラグ（data/stop_requested.flag）と PID ファイル（data/execution.pid）による制御。
    - スレッドでエンジンを実行し、停止フラグ検知で安全に停止するロジック。

  - run_monitoring: SystemMonitor ポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - Monitoring は環境にかかわらず本番 sqlite_path を使用する設計。
    - 停止フラグ検知でループを終了、例外時はログに詳細を出力して次回ポーリングまで待機。
    - duckdb と sqlite の両方に接続して監視 DB 初期化（init_monitoring_db）を行う。

- 設定管理・検証ツール
  - config.py: 環境変数 / .env ロードと Settings クラスを追加。
    - プロジェクトルート探索 (.git / pyproject.toml) に基づく .env 自動読み込み（.env と .env.local の重ね合わせ）。
    - LOAD を無効化する環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
    - .env パースの詳細実装（export ワード、クォート文字、エスケープ、インラインコメントの扱い）。
    - 必須環境変数取得ヘルパー _require と各種設定プロパティ（DB パス、PAPER_FILL_MODE、閾値、env/log level 判定等）。
    - Settings インスタンス（settings）をエクスポート。

  - config_setup.py: .env の対話式ウィザードを追加。
    - J-Quants、kabu API、DB パス、LINE 通知設定、ログレベル、Kill Switch 設定などを対話的に作成・更新。
    - 既存 .env の読み込み・マスク表示・確認プロンプト・保存機能を提供。
    - .env のテンプレート書き込みロジックを含む。

  - validate_config.py: 起動前設定検証 CLI を追加。
    - 必須環境変数の存在チェック、KABUSYS_ENV / LOG_LEVEL の妥当性、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在と PyYAML によるパース検証（PyYAML 未インストール時は警告）。
    - KABUSYS_ENV=live 時の追加ガード（LINE 通知設定、KILL_FLAG_CLEAR_ON_START の警告）。
    - --strict オプションで警告を失敗扱いにして exit(1)。

- ロギング・プロセス制御ユーティリティ
  - utils/logging_setup.py:
    - 統一的なログ設定関数 setup_logging を追加。
    - stdout への StreamHandler と日次ローテーション（TimedRotatingFileHandler）によるファイル出力を組み合わせる。
    - LOG_DIR / LOG_LEVEL の環境変数参照、既存ハンドラのクリア、ログディレクトリ作成失敗時のフォールバックを実装。
    - 30 日分のログ保持設定を既定として採用。

  - utils/process_priority.py:
    - プラットフォーム抽象化した set_process_priority を追加（Windows の priority class / POSIX の nice 値対応）。
    - set_cpu_affinity による CPU ピンニング機能を追加（アクセス権限や未対応 OS の場合は警告）。
    - 失敗時は警告ログを出してスキップする堅牢性設計。

- ポートフォリオ構築ライブラリ（純粋関数群）
  - portfolio/portfolio_builder.py:
    - select_candidates: スコア降順の候補選定（タイブレークに signal_rank）。
    - calc_equal_weights: 等金額配分。
    - calc_score_weights: スコア加重配分（全スコア 0 の場合は等配分にフォールバック）。

  - portfolio/risk_adjustment.py:
    - apply_sector_cap: セクター集中上限チェック（sell_codes を除外、unknown セクターは無視）。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull/neutral/bear、未知レジームは 1.0 にフォールバック）。

  - portfolio/position_sizing.py:
    - calc_position_sizes: 各銘柄の発注株数計算を実装。
      - allocation_method: "risk_based" / "equal" / "score" をサポート。
      - lot_size（単元）、max_position_pct、max_utilization、cost_buffer 等のパラメータを考慮。
      - aggregate cap（総投下額が available_cash を超える場合のスケーリング）と lot_size単位での端数処理（残差に基づく追加配分）を実装。
      - 価格欠損時のスキップやログ出力を考慮。

  - portfolio/__init__.py で上記関数をエクスポート。

- 監視・検証ツール
  - monitoring.monitoring_db の初期化呼び出し（init_monitoring_db）を run スクリプトで保証（冪等）。
  - tools/paper_verification_report.py:
    - ペーパートレード用の検証レポート生成 CLI を追加（DB パスオーバーライド可能）。
    - システム稼働率、注文成功率、送信率、P95 レイテンシ等を集計し、閾値に基づいて PASS / FAIL を判定。
    - p95 計算、日付フィルタ、SQL クエリの堅牢な扱い（テーブル不存在時の例外耐性）を実装。

- 研究モジュール（計算コアの下地）
  - research/factor_research.py を追加（ファクター計算の骨格）。
    - モメンタム・ボラティリティ等の仕様・定義、DuckDB を用いた計算方針を文書化。
    - calc_momentum の実装開始（ファイル末尾で未完の記述あり：さらなる実装が必要）。

### Changed
- 初期リリースのため該当項目なし。

### Fixed
- 初期リリースのため該当項目なし。
- ただし各所で不正な環境変数やファイルシステム操作に対するフォールバック・警告処理を多数実装しており、運用時の堅牢性を高めている（例: MONITOR_POLL_INTERVAL の不正値時のデフォルトフォールバック、ログディレクトリ作成失敗時のファイルハンドラ無効化など）。

### Security
- .env ファイルに関する注意を config_setup.py のヘッダに明記（.env を絶対に Git にコミットしない旨）。
- config.py にて OS 環境変数を保護するため .env 読み込み時に既存 OS 環境変数を上書きしないデフォルト動作を採用。必要に応じ .env.local による上書きを許容。

### Known issues / TODO
- research/factor_research.calc_momentum が未完（ファイル末尾で途中）。ファクター計算の追加実装が必要。
- position_sizing の price 欠損時の扱いに TODO コメントあり（前日終値等のフォールバック価格の導入検討）。
- 将来的には銘柄ごとの lot_size をサポートする設計（stock マスタに lot_size を持たせる等）を想定。
- 一部機能は外部依存（psutil, PyYAML, duckdb）により、未インストール時は機能制限または警告になる。

---

以上。追加の要望（例えば日付の調整、より詳細な変更理由の追記、各ファイル別の差分記述など）があれば指示してください。