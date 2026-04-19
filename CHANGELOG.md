# CHANGELOG

すべての変更は Keep a Changelog の形式に従って記載しています。  
新しいバージョンについてはセマンティックバージョニングを想定しています。

注: 以下の変更点はコードベースの内容から推測してまとめたもので、実際のコミット履歴に基づくものではありません。

## [Unreleased]
- なし

## [0.1.0] - 2026-04-19
初回リリース。日本株自動売買システム「KabuSys」のコアユーティリティ、実行/監視スクリプト、設定管理、ポートフォリオ構築ロジック、検証ツールなどを追加。

### Added
- 実行・監視スクリプト
  - run_execution.py
    - ExecutionEngine を起動する CLI スクリプトを追加。
    - KABUSYS_ENV による paper_trading モード対応（paper_trading 時は MockBrokerClient を使用し data/paper_trading.db に記録）。
    - プロセス優先度を起動時に "high" に設定。
    - 停止フラグ（data/stop_requested.flag）検出により安全に停止。
    - 実行 PID ファイル管理（data/execution.pid）。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で上書き可能（デフォルト: 60秒）。不正値は警告を出してデフォルトにフォールバック。
    - 監視データベースは環境に依らず本番 sqlite_path を使用。
    - 停止フラグ（data/stop_requested.flag）でループを終了。

- 設定・検証・ウィザード
  - config.py
    - Settings クラスを導入し、環境変数から各種設定を取得する API を提供。
    - .env 自動ロード機能（プロジェクトルート検出: .git または pyproject.toml 基準）。自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能。
    - 各種プロパティ: J-Quants / kabu API / DB パス（duckdb/sqlite） / PAPER_FILL_MODE（入力検証） / PID/KILL フラグパス / リソース閾値 / 環境判定（is_live/is_paper/is_dev）等。
  - validate_config.py
    - .env と config/*.yaml の起動前検証 CLI を追加。必須環境変数チェック、KABUSYS_ENV・LOG_LEVEL 検証、DB パス/ディレクトリ存在チェック、YAML のパース検証（PyYAML があれば実行）。
    - --strict オプションで警告を失敗扱いにできる。
  - config_setup.py
    - 対話式ウィザードで .env を作成／更新するツールを追加。
    - 入力のマスク（シークレット）、選択肢、デフォルト、確認表示、保存機能を備える。

- ロギング / プロセス制御ユーティリティ
  - utils/logging_setup.py
    - 統一的なログ設定関数 setup_logging() を実装。
    - StreamHandler（stdout）＋ TimedRotatingFileHandler（日次、30日保持）をルートロガーに設定。
    - LOG_LEVEL / LOG_DIR / 引数での上書きに対応。既存ハンドラの二重登録を防止するため再設定時にハンドラをクリア。
    - ログディレクトリ作成に失敗した場合はファイル出力をスキップして警告を表示。
  - utils/process_priority.py
    - プラットフォーム差（Windows/Linux/macOS）を吸収してプロセス優先度を設定する set_process_priority(level) を実装（"high"/"normal"/"low"）。
    - CPU affinity を設定する set_cpu_affinity(cpu_count) を実装（利用できない場合は警告を出してスキップ）。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py
    - シグナルの候補選定 (select_candidates)、等分配 (calc_equal_weights)、スコア加重配分 (calc_score_weights) を追加。
    - スコア全体が 0 の場合は等分配にフォールバックして警告出力。
  - portfolio/risk_adjustment.py
    - セクター集中制限を適用する apply_sector_cap を追加（売却予定銘柄を除外して既存保有のセクター別エクスポージャを計算）。
    - market レジームに応じた投下資金乗数 calc_regime_multiplier を追加（"bull"=1.0、"neutral"=0.7、"bear"=0.3。未知は 1.0 へフォールバックして警告）。
  - portfolio/position_sizing.py
    - position sizing ロジック calc_position_sizes を実装。allocation_method ("risk_based"/"equal"/"score") に対応。
    - 単元株（lot_size）丸め、1銘柄上限・総投下上限・コストバッファ考慮、資金超過時のスケーリング＋端数配分ロジックを備える。

- 監視・モニタリング関連
  - monitoring の初期化呼び出し（init_monitoring_db）を run_execution/run_monitoring から呼ぶことで監視テーブルの存在を保証（冪等）。
  - stop/kill フラグや PID ファイル経由で外部からの制御を行える設計。

- ツール
  - tools/paper_verification_report.py
    - Paper Trading 用の検証レポート生成ツールを追加。
    - 指標: 稼働率（uptime）、注文成功率（fill rate）、送信率（send rate）、レイテンシ（平均/最大/P95）、リスク却下数。
    - デフォルトの合格基準（しきい値）を定義: 稼働率 >= 99%、fill >= 90%、send >= 95%、P95 レイテンシ <= 200ms。
    - CLI 引数 --from/--to/--db に対応。データ不足やテーブル未存在時に Graceful に N/A 表示。

- 研究モジュール（部分実装）
  - research/factor_research.py
    - Momentum / Value / Volatility / Liquidity 等のファクター計算方針と一部定数を追加。
    - DuckDB を用いた prices_daily / raw_financials を前提とした計算設計。calc_momentum の実装が途中（ファイル末尾で切れている）。

- パッケージ初期化
  - kabusys/__init__.py に初期バージョン __version__ = "0.1.0" を追加。

### Changed
- なし（初回リリースのため新規追加が中心）

### Fixed
- なし

### Deprecated
- なし

### Removed
- なし

### Security
- なし

(以上)