# Changelog

すべての重要な変更点を記録します。フォーマットは「Keep a Changelog」に準拠しています。

最新リリース
------------

### [Unreleased]
- 現時点での未リリース変更はありません。

固定リリース
------------

### [0.1.0] - 2026-04-25
初回公開リリース。シンプルな日本株自動売買基盤のコアユーティリティ群、起動スクリプト、設定ツール、ポートフォリオ構築ロジック、および検証ツールを追加しました。

Added
- 起動スクリプト
  - run_execution.py
    - ExecutionEngine の起動スクリプトを追加。起動時にプロセス優先度を "high" に設定。
    - KABUSYS_ENV が `paper_trading` の場合は専用の Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）を使用し、本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler を組み立て、Engine をスレッドで実行。data/stop_requested.flag による停止処理を実装。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数（デフォルト: 60秒）でポーリング間隔を上書き可能。
    - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する設計（監視データは本番 DB に常に書き込む）。
    - 停止フラグ（data/stop_requested.flag）による優雅な終了処理を実装。

- 設定関連
  - config.py
    - .env 自動ロード機能を実装（プロジェクトルートに .git または pyproject.toml がある場合に .env / .env.local を読み込む）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
    - .env のパースは export 形式、クォート／エスケープ、インラインコメントを考慮して実装。
    - Settings クラスを追加し、環境変数から各種設定（DB パス、PID ファイルパス、監視しきい値、環境判定、PAPER_FILL_MODE のバリデーション等）をプロパティで取得できるようにした。
  - config_setup.py
    - 対話式ウィザードで .env を初期作成・更新する CLI を追加。シークレット値はマスク表示、保存前の確認、.env のテンプレート出力を実装。
  - validate_config.py
    - 起動前に .env と config/*.yaml を検証する CLI を追加。必須環境変数の有無チェック、KABUSYS_ENV / LOG_LEVEL の妥当性、DB パスの親ディレクトリ存在チェック、PyYAML がある場合は YAML のパース検査を行う。
    - --strict オプションで警告を失敗扱いにできる。

- ロギング / プロセス制御ユーティリティ
  - utils/logging_setup.py
    - 統一的なログ設定ユーティリティを追加。ルートロガーに stdout への StreamHandler と日次ローテーションする TimedRotatingFileHandler（logs/<app_name>.log、30日分保持）を設定。
    - ログディレクトリ作成に失敗した場合はファイル出力を無効化してコンソール出力のみ続行。
    - LOG_LEVEL / LOG_DIR / 引数による上書きに対応。
  - utils/process_priority.py
    - クロスプラットフォーム（Windows / POSIX）向けにプロセス優先度設定ユーティリティを追加。`set_process_priority("high"|"normal"|"low")` を提供。
    - CPU affinity を固定する `set_cpu_affinity` を追加。
    - 権限不足などで設定に失敗した場合は警告としてスキップする実装。

- ポートフォリオ構築（純関数群）
  - portfolio/portfolio_builder.py
    - シグナル選定（select_candidates）、等重み（calc_equal_weights）、スコア重み（calc_score_weights）を実装。スコア合計が 0 の場合は等重みへフォールバックして警告を出す。
  - portfolio/risk_adjustment.py
    - セクター集中上限を検査して過剰セクターの候補を除外する apply_sector_cap を実装（unknown セクターは制限対象外）。
    - 市場レジームに応じた投下資金乗数 calc_regime_multiplier を実装（bull/neutral/bear のマップ、未知のレジームは 1.0 でフォールバックして警告）。
  - portfolio/position_sizing.py
    - 各銘柄の発注株数を計算する calc_position_sizes を実装。
    - allocation_method="risk_based" / "equal" / "score" をサポート。lot_size（単元株）や cost_buffer（手数料・スリッページ見積り）を考慮。
    - aggregate cap を超えた場合のスケーリングと、小数部分（lot 単位）の再配分ロジックを実装。

- ツール
  - tools/paper_verification_report.py
    - Paper Trading 用 SQLite（PAPER_TRADING_SQLITE_PATH）から検証レポートを生成するスクリプトを追加。
    - システム稼働率、注文成功率、送信率、P95 レイテンシなどを算出し、閾値（稼働率 99%、成功率 90% 等）に基づく PASS/FAIL を表示。
    - DB が存在しない場合やテーブルが足りない場合は安全にハンドリングして N/A を表示。

- リサーチ
  - research/factor_research.py
    - StrategyModel に基づくファクター計算モジュールの骨組みを追加（モメンタム、MA、ATR、流動性などの計算を予定）。DuckDB 接続を受け取り prices_daily / raw_financials に対して処理を行う設計。

Changed
- パッケージ情報
  - src/kabusys/__init__.py にバージョン情報を追加（__version__ = "0.1.0"）し、主要モジュールを __all__ でエクスポート。

Fixed
- 実行時の安全性向上
  - 起動スクリプトでプロセス優先度の設定を起動直後に行うことで、起動中のリソース割当を狙いやすくした。
  - run_execution/run_monitoring ともに、DB 接続（sqlite/duckdb）のクローズを finally で保証。

Notes / Implementation details
- .env の自動読み込みはプロジェクトルートを __file__ を基準に探索して行うため、CWD に依存せずパッケージ配布後も正しく動作します。
- run_monitoring は「監視データは常に本番の monitoring DB に記録する」という設計方針になっています（KABUSYS_ENV に依存しない）。
- run_execution は paper_trading 時に paper 用 DB を使用することで、本番データとの分離を確保します。
- logging_setup は標準エラーではなく標準出力（stdout）にログを出力するようにしてあります。cron 等で stdout/stderr を一本化してリダイレクトする運用を想定しています。
- PAPER_FILL_MODE は "instant" / "partial" / "never" / "reject" のいずれかのみ有効です。無効値は ValueError を発生させます。
- いくつかの箇所（research/factor_research.py の一部など）は引き続き実装・テストが必要です。

Security
- シークレット（トークン・パスワード）は .env に保存する設計ですが、config_setup の出力メッセージで「.env を絶対に Git にコミットしないこと」を明示しています。

Acknowledgements
- 本変更はライブラリの初期設計・骨格構築を目的としたリリースです。今後、ユニットテスト、ドキュメントの拡充、エンドツーエンドテストを順次追加していきます。

（終）