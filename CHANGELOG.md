# Changelog

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠し、セマンティックバージョニングを使用します。

全般的な注意:
- デフォルトや振る舞いはコード内のドキュメント文字列・コメントや Settings クラスの実装から推測して記載しています。
- 自動ロードされる環境変数やファイルパスの既定値はソース上の値を使用しています。

## [Unreleased]

（現在未リリースの変更はありません）

## [0.1.0] - 2026-04-22

Added
- 基本機能の初期実装を追加。
  - 自動売買システム「KabuSys」のコアモジュール群を追加。
- 実行・監視用エントリスクリプトを追加。
  - run_execution.py
    - ExecutionEngine を起動するランチャー。
    - KABUSYS_ENV が `paper_trading` の場合は paper_trading 専用 SQLite（デフォルト: data/paper_trading.db）を使用して本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント生成。
    - Engine をデーモンスレッドで実行し、 data/stop_requested.flag による停止検知を実装。
    - 実行中の PID を data/execution.pid に保持（pid_file のパスは設定から取得）。
  - run_monitoring.py
    - SystemMonitor のポーリングループを実行するランチャー。
    - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で上書き可（デフォルト: 60 秒）。不正値はデフォルトにフォールバックし警告を出力。
    - 監視は KABUSYS_ENV に関係なく production 用 sqlite_path を使用する仕様。
    - data/stop_requested.flag による停止検知を実装。
- 設定管理とウィザードを追加。
  - config.py
    - Settings クラスで環境変数から各種設定値を取得する API を提供（J-Quants / kabu API / DB パス / 監視閾値 など）。
    - .env 自動読み込み機能: プロジェクトルート（.git または pyproject.toml）を検出して .env/.env.local を順に読み込み。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。既存 OS 環境変数は保護して上書きしない。
    - env 値の検証（KABUSYS_ENV の許容値、LOG_LEVEL の許容値、PAPER_FILL_MODE の列挙チェックなど）。
  - config_setup.py
    - 対話式ウィザードによる .env の初期作成/更新を実装。デフォルト提示、シークレットマスク、選択肢バリデーション、保存確認など。
- 設定検証 CLI を追加。
  - validate_config.py
    - .env および config/*.yaml（存在チェック・YAML パース）等の事前チェックを実装。
    - 必須環境変数チェック、KABUSYS_ENV の追加ガード（live の場合の注意喚起）、ファイルパス親ディレクトリ存在チェックなど。
    - --strict オプションで警告をエラー扱いにできる。
- ロギング・プロセス運用ユーティリティを追加。
  - utils/logging_setup.py
    - ルートロガーに StreamHandler (stdout) と TimedRotatingFileHandler（日次ローテーション・30日保持）を設定するユーティリティ。
    - ログディレクトリ作成に失敗した場合はファイル出力を無効化してコンソール出力のみで継続。
    - ログレベル解決順: 引数 > 環境変数 LOG_LEVEL > デフォルト "INFO"。
  - utils/process_priority.py
    - クロスプラットフォームでのプロセス優先度設定（Windows の優先度クラス / POSIX の nice 値）と CPU affinity 設定関数を提供。
    - 権限不足や未対応プラットフォームでは警告を出して安全にスキップする実装。
- ポートフォリオ構築関連の純粋関数群を追加（DB非依存、メモリ内計算）。
  - portfolio/portfolio_builder.py
    - signal のソート（スコア降順、タイブレークは signal_rank）と候補選択関数 select_candidates。
    - 等金額配分 calc_equal_weights、スコア加重配分 calc_score_weights（全スコアが0 の場合は等配分にフォールバック）。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中上限チェックと候補除外ロジック（"unknown" セクターは上限対象外）。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull/neutral/bear をマップ、未知のレジームは警告して 1.0 にフォールバック）。
  - portfolio/position_sizing.py
    - calc_position_sizes: risk_based / equal / score の配分方式をサポート。単元株（lot_size）丸め、per-position 上限、aggregate cap（利用可能現金を超える場合のスケーリングと端数配分）を実装。コストバッファ対応。
- Paper Trading 向け解析ツールを追加。
  - tools/paper_verification_report.py
    - ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）から統計を集計し、稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）などの指標を出力。
    - 閾値に基づく PASS/FAIL 判定（稼働率 99% など）を実装。
    - 日付フィルタ (--from / --to)、--db オプションをサポート。
- リサーチ用ファクター計算モジュール（骨格）を追加。
  - research/factor_research.py
    - Momentum / Value / Volatility / Liquidity の計算設計を実装。DuckDB 接続を受け取り prices_daily / raw_financials テーブルを利用する方針。モメンタム計算関数群の実装を開始（ファイル末尾で実装途中の可能性あり）。

Changed
- パッケージ初期バージョンを 0.1.0 として公開（src/kabusys/__init__.py の __version__ を設定）。

Fixed
- （初期リリースにつき既知の小バグ修正履歴はなし。ただし一部実装に TODO コメントを残し将来的な改善を明記。）

Notes / Behavior / Defaults
- 環境変数自動読み込み:
  - プロジェクトルートが見つかる場合、.env を未定義のキーのみで読み込み、.env.local を既存キーを上書きして読み込み。OS 環境変数は保護され上書きされない。
- データベース:
  - DuckDB のパス: 環境変数 DUCKDB_PATH（デフォルト data/kabusys.duckdb）。
  - SQLite（監視）: SQLITE_PATH（デフォルト data/monitoring.db）。monitoring 系は環境にかかわらず本番 sqlite_path を参照。
  - Paper Trading 用 SQLite: PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）。paper_trading 環境は本番 DB と完全に分離。
- ログ:
  - デフォルトログディレクトリ: logs/。日次ローテーションで 30 日分保持。
  - コンソール出力は stdout を使用（stderr ではない）。
- プロセス運用:
  - 起動時に set_process_priority("high") を呼び出して優先度を上げようとする（権限不足時は警告を出して続行）。
  - CPU 固定（affinity）関数も提供しているが、run スクリプトからは明示呼び出しされていない（必要な場合に利用可能）。
- セキュリティ:
  - .env の取り扱いに関する注意が config_setup.py に明記（.env を Git にコミットしないこと）。
- 既知の注記:
  - position_sizing.calc_position_sizes 内で price が欠損（0.0）の場合に保守的にスキップする実装があり、将来的には前日終値等でのフォールバックを検討する旨の TODO コメントあり。
  - risk_adjustment.apply_sector_cap は "unknown" セクターをセクター上限適用外にしており、マスタにセクター情報が無い銘柄は除外されない点に注意。

Breaking Changes
- 初回リリースのため過去互換性の考慮は該当なし。

Security
- 機密値（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, LINE チャンネルトークン等）は .env に保存する設計。config_setup にも「.env を絶対に Git にコミットしないこと」が明記されています。

開発者向け補足
- 設定検証ツール (python -m kabusys.validate_config) と設定ウィザード (python -m kabusys.config_setup) を併用することで、起動前に環境やファイルの不備を検出できる設計になっています。
- run_execution / run_monitoring はそれぞれ daemon 向けに設計されており、外部のプロセスマネージャ (systemd / supervisor / docker など) から監視・起動する想定です。

----- 

（この CHANGELOG はソースコードのコメント・実装から推測して作成しています。実際のリリースノート作成時はコミット履歴や CHANGELOG のポリシーに合わせて必要に応じて修正してください。）