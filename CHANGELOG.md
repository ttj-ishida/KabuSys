# Changelog

すべての変更は [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) の形式に従います。

重要: この CHANGELOG はリポジトリ内のソースコードから推測して作成したものであり、実際のコミット履歴や意図とは差異がある可能性があります。

## [Unreleased]

- なし

## [0.1.0] - 2026-04-18

初回公開相当のリリース。日本株自動売買システム「KabuSys」のコアユーティリティ、起動スクリプト、ポートフォリオ構築・リスク調整・ポジションサイジング関数群、および運用支援ツール類を追加。

### Added
- 基本情報
  - パッケージバージョンを `__version__ = "0.1.0"` として定義。

- 起動スクリプト
  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV が `paper_trading` の場合に専用の paper_trading DB（デフォルト `data/paper_trading.db`）を利用し、本番 DB と完全に分離する挙動を実装。
    - BrokerClientFactory を利用してブローカークライアントを生成。
    - ExecutionEngine/OrderManager/OrderRepository/RiskManager/Reconciler の組み立てと実行スレッドによる起動・停止制御を行う。
    - 起動前に停止フラグファイル（data/stop_requested.flag）をチェックして即時終了可能。
    - 高優先度（"high"）でプロセス優先度を設定して起動。

  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL` で上書き可能（デフォルト 60 秒）。
    - Monitoring は実行環境にかかわらず本番 sqlite_path（`Settings.sqlite_path`）を使用する仕様。
    - 停止フラグ（data/stop_requested.flag）を検知してループを終了。

- 設定・環境管理
  - config.py
    - .env の自動ロード機構を実装（プロジェクトルートを `.git` または `pyproject.toml` で検出）。
    - .env/.env.local の読み込みルール（OS 環境変数を保護）を実装。
    - 多数の Settings プロパティを追加（J-Quants トークン、kabu API、DB パス、ログ設定、監視閾値、環境フラグ等）。
    - `paper_fill_mode`（Paper Trading 時のフォールバック挙動）を追加（valid: "instant"|"partial"|"never"|"reject"）。
    - `paper_sqlite_path`（Paper Trading 専用 SQLite パス）を追加。

  - config_setup.py
    - 対話式 .env 作成/更新ウィザードを追加。
    - 各種設定項目（KABUSYS_ENV, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DUCKDB_PATH, SQLITE_PATH, LINE トークン等）を対話的に入力可能。
    - .env の読み込み／既存値の再利用、保存機能を提供。

  - validate_config.py
    - 起動前の設定検証 CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV 値チェック、LOG_LEVEL チェック、DB パスの親ディレクトリチェック、config/*.yaml の存在確認と YAML パース（PyYAML が利用可能な場合）、本番環境向けの追加ガード（LINE 通知や Kill Switch の設定）を実装。
    - `--strict` オプションで警告を失敗扱いにする機能を提供。

- ログ・プロセス管理ユーティリティ
  - utils/logging_setup.py
    - 統一的なログ設定ユーティリティを追加。
    - StreamHandler（stdout）と TimedRotatingFileHandler（日次、30 日保管）をルートロガーに設定。
    - ログディレクトリ作成に失敗した場合はファイル出力をスキップしてコンソールのみで継続するフォールバックを実装。
    - ログレベル・ログディレクトリの解決順を文書化（引数 > 環境変数 > デフォルト）。
  - utils/process_priority.py
    - プロセス優先度設定ユーティリティを追加（Windows / POSIX の差分を吸収）。
    - set_process_priority(level: "high"|"normal"|"low") を提供（psutil ベース）。
    - set_cpu_affinity(cpu_count: int | None) を追加（最初の N コアにピン留め）。許可エラー等は警告で無視する堅牢性。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py
    - select_candidates: Buy シグナルをスコア降順（タイブレークに signal_rank）で選定。
    - calc_equal_weights: 等金額配分。
    - calc_score_weights: スコア加重配分（スコア合計が 0 の場合は等分にフォールバック）。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中制限に基づく候補除外ロジック（売却予定銘柄の除外や "unknown" セクター扱いについての仕様あり）。
    - calc_regime_multiplier: 市場レジーム（"bull"/"neutral"/"bear"）に応じた資金乗数（1.0/0.7/0.3）を実装。未知のレジームは 1.0 にフォールバック。
  - portfolio/position_sizing.py
    - calc_position_sizes: allocation_method（"risk_based" / "equal" / "score"）に対応した株数決定ロジックを実装。
    - 単元（lot_size）丸め、1銘柄上限（max_position_pct）、aggregate cap（available_cash）によるスケールダウン、cost_buffer を考慮した保守的コスト見積もり、残差に基づく追加配分ロジックなどを実装。
    - 不足データ（価格 0 や未取得）の場合はスキップし、ログにデバッグ情報を出力。

- 研究用ファクター計算
  - research/factor_research.py（ファイル追加）
    - DuckDB（prices_daily / raw_financials）を基にモメンタム・Value・Volatility・Liquidity の各種ファクターを計算する設計を追加。モメンタム計算（mom_1m, mom_3m, mom_6m, ma200_dev）等を実装予定の形で用意（コードは途中実装あり）。

- 運用ツール
  - tools/paper_verification_report.py
    - Paper Trading 用検証レポート生成スクリプトを追加。
    - 稼働率（uptime）、注文成功率（fill rate）、送信率（send rate）、P95 レイテンシ等を集計して PASS/FAIL 判定を行う。
    - デフォルト DB パスは環境変数 `PAPER_TRADING_SQLITE_PATH` または `data/paper_trading.db`。
    - P95 算出、各種閾値（稼働率 99%、fill 90%、send 95%、P95 レイテンシ 200ms）を定義。

- 監視テーブル初期化
  - monitoring.monitoring_db の init_monitoring_db を起動スクリプトから呼び出し、監視テーブルが存在することを保証（冪等）。

### Changed
- 起動/監視の運用設計
  - 監視（run_monitoring）では環境にかかわらず本番 sqlite_path を使用する仕様にしており、誤って paper_trading DB を監視しないよう分離が図られている。
  - run_execution は paper_trading 環境の際に paper_trading DB を使うことで発注ログ等を分離。

### Fixed
- 各ユーティリティは外部リソース（ログディレクトリ作成、psutil による優先度設定等）で発生し得る例外をキャッチしてフォールバック動作（警告出力・機能スキップ）を行うようにしており、実運用での堅牢性を向上。

### Notes / Known limitations
- research/factor_research.py はファクター計算機能の実装が途中に見える（ファイル末尾で途中切れ）。完全実装が必要。
- 設定の自動ロードはプロジェクトルート検出に依存（.git / pyproject.toml）。配布後や特殊な配置の場合は自動ロードが無効化される可能性あり。
- position_sizing の lot_size は現状グローバル固定（将来的な銘柄別単位対応は TODO コメントあり）。
- process_priority/set_cpu_affinity は権限不足や未対応 OS での失敗を警告で無視するが、期待通り動作しない環境がある点に注意。

---

（補足）
- ここに記載した内容はソースコードの現状から推測してまとめたものです。実際のリリースノートやバージョン付けはプロジェクトの運用ルールに従って調整してください。