CHANGELOG
=========

すべての注目すべき変更はこのファイルに記録します。
フォーマットは "Keep a Changelog" に準拠しています。

Unreleased
----------

- （無し）

0.1.0 — 2026-04-24
------------------

Added
- 初期リリース。KabuSys の基本コンポーネントを実装。
- 起動スクリプト
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止はプロジェクト内 data/stop_requested.flag ファイルの存在検出で行う。
    - 監視は KABUSYS_ENV にかかわらず本番用 SQLite パスを使用する実装（monitoring DB 初期化を含む）。
    - 例外発生時はログを出力して次のポーリングへ継続する堅牢化処理を追加。
  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用専用 SQLite（デフォルト data/paper_trading.db）を使用して本番 DB と完全に分離。
    - BrokerClientFactory を用いたブローカークライアント生成（モックの利用を想定）。
    - スレッドで ExecutionEngine を実行し、stop_flag 検出で安全に停止する制御ループを実装。
    - 実行用 PID ファイル管理（data/execution.pid）をサポート。
- 設定関連
  - config.py
    - 環境変数／.env の読み込み機能を実装（プロジェクトルートの検出: .git / pyproject.toml を基準）。
    - .env 自動ロード順序: OS 環境 > .env.local > .env。自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - .env の行パーサは export プレフィックス、クォート（シングル/ダブル）、バックスラッシュエスケープ、インラインコメント等に対応。
    - Settings クラスを提供し、各種設定値（DB パス、API トークン、監視閾値、環境判定等）をプロパティとして取得可能。PAPER_FILL_MODE 等の入力検証を実施。
  - config_setup.py
    - 対話式ウィザードで .env を初期作成／更新できる CLI を追加。シークレット項目はマスク表示。
  - validate_config.py
    - 起動前設定検証 CLI を追加。必須環境変数チェック、KABUSYS_ENV・LOG_LEVEL の妥当性確認、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在確認（PyYAML がある場合はパース検証）を実行。
    - --strict モードで警告を FAIL 扱いにできる。
- ポートフォリオ構築
  - portfolio/portfolio_builder.py
    - 候補選定（スコア降順／signal_rank によるタイブレーク）、等金額配分、スコア加重配分を実装。スコア全体が 0 の場合は等分へフォールバックし警告を出力。
  - portfolio/risk_adjustment.py
    - セクター集中上限適用（既存ポジションのセクター別エクスポージャー計算に基づく候補除外）。
    - 市場レジームに対する投下資金乗数 calc_regime_multiplier を実装（bull/neutral/bear をサポート、未知レジームはフォールバック）。
  - portfolio/position_sizing.py
    - 株数決定ロジックを実装。allocation_method として "risk_based" / "equal" / "score" を想定。
    - 単元株（lot_size）で丸め、1銘柄上限・aggregate 上限を考慮したスケールダウン処理、cost_buffer（手数料・スリッページ見積）対応、残差分の配分ロジックを実装。
- ユーティリティ
  - utils/logging_setup.py
    - ルートロガーの一括設定ユーティリティを追加。StreamHandler（stdout）と TimedRotatingFileHandler（日次・30世代保持）を設定。
    - LOG_LEVEL / LOG_DIR / app_name によるログ解決。ログディレクトリ作成失敗時はファイル出力をスキップして標準出力のみで継続。
  - utils/process_priority.py
    - プロセス優先度（high/normal/low）設定を OS に依存せず統一的に扱うユーティリティを実装。Windows と POSIX (Linux/Mac/FreeBSD) を考慮し、CPU affinity 設定用の set_cpu_affinity 関数も提供。
    - 権限不足や未対応 OS の際は警告を出力してスキップ。
- モニタリング / DB 初期化
  - monitoring.monitoring_db.init_monitoring_db を各起動スクリプトから呼んで監視テーブルが存在することを保証（冪等）。
  - duckdb の利用を想定した接続受け渡しを行う実装（分析用 DB 用途）。
- ツール
  - tools/paper_verification_report.py
    - Paper Trading 用検証レポート生成スクリプトを追加。指定期間の system_status / trade_logs / risk_logs から稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）などを算出し、閾値（稼働率 99% 等）に基づく PASS/FAIL を表示。
    - コマンドライン引数 --from/--to/--db をサポート。DB が存在しない場合はエラーを出力。
- 研究（research）
  - research/factor_research.py（部分実装）
    - DuckDB の prices_daily / raw_financials を参照して Momentum / Value / Volatility / Liquidity 等のファクター計算を行う設計。モメンタム計算のインターフェースを用意（target_date を受け取る）。（ファイル末尾で未完の箇所あり）

Changed
- （初期リリースのため該当なし）

Fixed
- （初期リリースのため該当なし）

Security
- （該当なし）

Notes
- 本 CHANGELOG はリポジトリ内のソースコードから機能・挙動を推測して作成しています。実際のリリースノートやユーザ向けドキュメントを作成する際は、追加の仕様や意図確認を行ってください。