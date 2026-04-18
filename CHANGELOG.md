# Changelog

すべての notable な変更はここに記録します。  
フォーマットは "Keep a Changelog" に準拠します。

現在バージョン: 0.1.0  
リリース日: 2026-04-18

## [0.1.0] - 2026-04-18

### Added
- 基本アプリケーションパッケージを追加（kabusys v0.1.0）。
  - パッケージメタデータ: src/kabusys/__init__.py に __version__ = "0.1.0"。
- 環境設定 / ロード機能
  - Settings クラス（src/kabusys/config.py）を追加。
    - .env/.env.local の自動読み込み（プロジェクトルートを .git または pyproject.toml から探索）。
    - 環境変数取得ユーティリティ（必須チェック _require、各種デフォルト値）。
    - 許容値検証（KABUSYS_ENV、LOG_LEVEL、PAPER_FILL_MODE など）。
    - SQLite/DuckDB パス、PID/Kill フラグ、監視閾値などの設定プロパティを提供。
  - .env パース機能の強化（引用符、エスケープ、インラインコメント対応）。
  - 自動ロード抑止用フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD。
- 環境セットアップウィザード CLI（src/kabusys/config_setup.py）
  - 対話式ウィザードで .env の初期作成・更新が可能。
  - 各設定項目に対して説明、デフォルト、選択肢、シークレット入力をサポート。
  - .env の読み書き（書式と注意書きコメントを含むテンプレート出力）。
- 設定検証 CLI（src/kabusys/validate_config.py）
  - .env と config/*.yaml の基本的な整合性チェックを行う。
  - 必須環境変数の未設定検出、KABUSYS_ENV の妥当性検証、ログレベル確認、DB パス親ディレクトリ確認、YAML パース（PyYAML が存在する場合）等。
  - `--strict` オプションで警告をエラー扱いにできる。
  - 本番（live）向けの追加ガード（LINE 通知の未設定や Kill Switch の設定確認）。
- 起動スクリプト
  - SystemMonitor 用起動スクリプト（src/kabusys/run_monitoring.py）
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番 sqlite_path を使用して監視テーブルを初期化。
    - 停止フラグ（data/stop_requested.flag）検出でループ終了。
    - 予期せぬ例外はキャッチしてログ出力後、次ポーリングまで待機。
  - ExecutionEngine 用起動スクリプト（src/kabusys/run_execution.py）
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用専用 SQLite（デフォルト data/paper_trading.db）を使用して本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository/OrderManager/RiskManager/Reconciler の組み立て、および ExecutionEngine の起動処理を実装。
    - 起動時に停止フラグを検出した場合は起動を中止。起動中は停止フラグで安全に停止を試みる。
    - PID ファイル管理（data/execution.pid など）。
- ロギングユーティリティ（src/kabusys/utils/logging_setup.py）
  - setup_logging 関数を提供。
    - ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション、既定 30 日保持）を設定。
    - LOG_LEVEL / LOG_DIR / 引数で動作を柔軟に制御。
    - ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
- プロセス優先度・CPU 固定ユーティリティ（src/kabusys/utils/process_priority.py）
  - set_process_priority(level) により Windows / POSIX の差分を吸収してプロセス優先度を設定。
  - set_cpu_affinity(cpu_count) でプロセスを最初の N コアに固定可能（利用不可や権限不足時は警告）。
- Portfolio 構築ライブラリ（src/kabusys/portfolio/*）
  - 候補選定: select_candidates（スコア降順、signal_rank によるタイブレーク）。
  - 重み付け: calc_equal_weights, calc_score_weights（スコアが全て 0 の場合は等配分にフォールバック）。
  - セクター集中制限: apply_sector_cap（既存保有と価格マップに基づき特定セクターを除外、"unknown" は除外対象外）。
  - レジーム乗数: calc_regime_multiplier（bull/neutral/bear に対応、未知レジームは 1.0 でフォールバック）。
  - 株数決定: calc_position_sizes
    - allocation_method に "risk_based", "equal", "score" をサポート。
    - 単元株（lot_size）丸め、1 銘柄上限（max_position_pct）、総投下上限（max_utilization）、手数料やスリッページ見積り cost_buffer を考慮したスケーリング機能を実装。
    - aggregate cap 超過時のスケールダウンと端数処理（残余キャッシュで fractional 残差の大きい順に lot 単位で追加配分）。
- Paper Trading 検証ツール（src/kabusys/tools/paper_verification_report.py）
  - ペーパートレード SQLite（PAPER_TRADING_SQLITE_PATH）から集計して検証レポートを生成する CLI を提供。
  - 指標:
    - システム稼働率（system_status）: 稼働率閾値 THRESHOLD_UPTIME_PCT (=99.0%)。
    - 注文成功率（trade_logs）: fill_rate, send_rate（閾値 90% / 95%）。
    - API レイテンシ: 平均・最大・P95（P95 閾値 200 ms）。
    - risk_logs からリスク却下数を集計。
  - 日付フィルタ（--from/--to）と DB path（--db / 環境変数）をサポート。
  - P95 の計算ユーティリティと欠損データ扱い（データなし→N/A）を実装。
- Research モジュール（src/kabusys/research/factor_research.py）
  - ファクター計算の設計とモメンタム計算基準値・定数を追加（DuckDB 経由で prices_daily / raw_financials を参照）。
  - モメンタム計算 calc_momentum の雛形（1M/3M/6M リターン、MA200 乖離率等）を含む（実装継続前提）。

### Changed
- （初期リリースのため該当なし）

### Fixed
- （初期リリースのため該当なし）

### Security
- シークレット値は config_setup の表示でマスクし、.env 生成時は注意を明記（.env を Git にコミットしない旨の注記を記載）。

### Notes / 動作上の重要な挙動
- 環境変数の自動ロードはプロジェクトルートが見つかった場合のみ行う（.git または pyproject.toml が基準）。
- 自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。
- PAPER_FILL_MODE の有効値は "instant" | "partial" | "never" | "reject"。無効値は ValueError を発生させる。
- run_monitoring は監視用 DB として Settings.sqlite_path を常に使用する（環境に依らず本番 DB 想定）。
- run_execution は paper_trading モード時に paper_sqlite_path を使用して本番 DB と分離する。
- ログは標準出力（stdout）へ出力されるため、cron 等で stdout/stderr を一本化してリダイレクトするとログ管理が容易。
- process_priority / set_cpu_affinity は権限不足や未対応プラットフォームでは警告ログを出力して安全にスキップする。
- position sizing の計算は価格データの欠損時（price が None または <= 0）にその銘柄をスキップする旨の挙動がある（将来的にフォールバック価格を検討するコメントあり）。
- paper_verification_report の閾値は現在ソース内の定数で定義されている（要調整可能）。

---

将来的には次の改良を検討しています（例）:
- factor_research の完全実装（DuckDB SQL と Python の組み合わせによるファクター生成）。
- ポートフォリオ構築で銘柄ごとの lot_size を考慮するためのマスタ拡張。
- run_monitoring / run_execution のユニットテストおよび統合テストの整備。
- モニタリング DB のスキーマ拡張・詳細アラートルールの追加。

（以上）