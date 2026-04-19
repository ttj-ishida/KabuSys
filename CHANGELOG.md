# CHANGELOG

すべての変更は Keep a Changelog のフォーマットに準拠して記載しています。  
セマンティックバージョニングを採用しています。  

なお本 CHANGELOG はリポジトリ内のコードから推測して作成したもので、実際の履歴と差異がある場合があります。

## [Unreleased]

（現時点で未リリースの変更はありません）

---

## [0.1.0] - 2026-04-19

初回公開リリース。

### Added
- 基本アプリケーション構成を実装
  - パッケージ: kabusys
  - バージョン: __version__ = "0.1.0"

- 実行・運用用スクリプト
  - run_execution.py
    - ExecutionEngine の起動スクリプトを提供。
    - プロセス優先度を設定（high）。
    - 環境に応じて本番/ペーパートレード用の SQLite を切り替え（KABUSYS_ENV=paper_trading 時は専用 DB を使用）。
    - BrokerClientFactory によるブローカークライアント生成。
    - OrderRepository、OrderManager、RiskManager、Reconciler、ExecutionEngine の組み立て。
    - スレッドで engine.run_session を実行し、停止フラグファイル（data/stop_requested.flag）で安全に停止可能。
    - PID ファイルを書き込む仕組みをサポート。

  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを提供。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は常に本番用 sqlite_path を使用して監視データを保存。
    - 停止フラグ検知による安全終了をサポート。

- 環境設定関連 CLI
  - config_setup.py
    - 対話式ウィザードで .env を初期作成／更新できる。
    - 複数の設定項目（KABUSYS_ENV、JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、DUCKDB_PATH、SQLITE_PATH、LINE 関連、LOG_LEVEL、KILL_FLAG_CLEAR_ON_START 等）をサポート。
    - .env 書き込みテンプレートと注意書きを出力（.env を Git にコミットしない旨）。

  - validate_config.py
    - .env と config/*.yaml の設定検証 CLI。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の値チェック、DB パスの親ディレクトリ存在チェック、YAML ファイルの存在・パース検査、live 環境へのガード（LINE 設定や KILL_FLAG_CLEAR_ON_START の確認）を実行。
    - --strict オプションで警告も失敗扱いにできる。

- 設定管理ユーティリティ
  - config.py
    - .env ファイルの自動ロード（プロジェクトルート検出:.git または pyproject.toml を基準）。
    - .env 読み込みの際の堅牢なパーサ実装（クォート、エスケープ、インラインコメント対応）。
    - 環境変数の保護（OS 環境変数の上書きを防ぐ protected 機能）。
    - Settings クラスを提供し、各種設定値へプロパティ経由でアクセス可能（DB パス、paper_trading 用パス、しきい値、PID/kill flag パス、env/log_level 判定等）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化に対応。

- ポートフォリオ構築ライブラリ（純粋関数群）
  - portfolio/portfolio_builder.py
    - 候補選定(select_candidates)、等金額配分(calc_equal_weights)、スコア加重配分(calc_score_weights) を実装。
    - スコア全てが 0 の場合に等金額配分へフォールバックし WARNING を出力。

  - portfolio/risk_adjustment.py
    - セクター集中制限の適用 (apply_sector_cap)。
    - 市場レジームに応じた資金乗数 calc_regime_multiplier を実装（bull/neutral/bear）。
    - 未知レジームは警告を出して 1.0 でフォールバック。

  - portfolio/position_sizing.py
    - ポジションサイズ計算 calc_position_sizes を実装。
    - allocation_method: "risk_based" / "equal" / "score" をサポート。
    - 単元(lot_size)丸め、per-position および aggregate cap、コストバッファ（手数料・スリッページ見積）に対応。
    - スケーリングと残差処理により利用可能現金を超過しない調整を実装。

- モニタリング / DB 初期化
  - monitoring/monitoring_db.init_monitoring_db を利用して監視テーブルの存在を保証（冪等に初期化）。

- ログ・プロセス管理ユーティリティ
  - utils/logging_setup.py
    - StreamHandler（stdout）と TimedRotatingFileHandler（日次, 30 日保持）をルートロガーに設定するユーティリティを提供。
    - LOG_LEVEL / LOG_DIR の解決順をサポート。ログディレクトリ作成失敗時はファイル出力をスキップして stdout のみで継続。

  - utils/process_priority.py
    - Windows/Linux/macOS の差分を吸収したプロセス優先度設定(set_process_priority)。
    - CPU affinity 設定(set_cpu_affinity) を実装。
    - 権限不足や未対応 OS の場合には安全に警告を出してスキップ。

- ツール
  - tools/paper_verification_report.py
    - Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）から検証レポートを生成するスクリプト。
    - 指標: 稼働率(uptime_pct)、注文成功率(fill_rate)、送信率(send_rate)、P95 レイテンシ、リスク却下数等を算出。
    - 合格基準（デフォルト閾値）を定義（例: 稼働率 >= 99%、P95 <= 200 ms 等）し PASS/FAIL で判定。
    - 日付範囲フィルタ(--from/--to) と DB パスオーバーライド(--db) に対応。

- リサーチ / ファクター計算（骨格）
  - research/factor_research.py
    - モメンタム等のファクター計算を行う設計と定数を定義（momentum periods, ATR, volume）。
    - DuckDB を用いた prices_daily / raw_financials 参照を前提とした設計。
    - （注）calc_momentum の実装は途中で切れているように見え、今後の実装継続が必要。

- パッケージ初期化 / エクスポート
  - kabusys/__init__.py と各 subpackage の __all__ を整備し、主要関数をエクスポート。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Known issues / Notes
- research/factor_research.calc_momentum はファイル中で未完に見える（実装途中）。ファクター計算を完全に機能させるには続きを実装する必要あり。
- position_sizing.calc_position_sizes の価格欠損時の扱いに TODO コメントあり（価格が欠損するとエクスポージャーが過少見積りされる可能性）。
- logging_setup はログディレクトリ作成に失敗した場合、ファイル出力をスキップして stdout のみで継続する設計。運用時はログディレクトリの権限確認を推奨。
- process_priority の設定は権限不足や未対応 OS で失敗する可能性があり、その場合は警告を出してスキップする。
- .env の自動ロードはプロジェクトルート探索に依存する（.git または pyproject.toml）。ルートが特定できない場合は自動ロードをスキップする。自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD を設定する。

### Security
- 環境変数 .env 内の機密情報（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD）は .env に保存される設計のため、.env をリポジトリにコミットしない旨を README と .env 生成テンプレートで注意喚起。

---

（以上）