CHANGELOG
=========

すべての変更は「Keep a Changelog」規約に従って記載しています。  
このファイルは、コードベースの現状から推測して作成した初期の変更履歴です（自動生成された .env/設定ファイル等の動作や振る舞いはコード記載に基づく推測です）。

Unreleased
----------

- （現時点なし）

0.1.0 - 2026-04-18
------------------

Added
- 初期リリース（0.1.0）。
- 実行・監視の起動スクリプトを追加。
  - run_execution.py
    - ExecutionEngine 起動用スクリプトを提供。スレッド実行でエンジンを起動・監視し、停止フラグにより安全に停止可能。
    - KABUSYS_ENV=paper_trading 時は paper_trading 用の専用 SQLite DB を使用し、本番 DB から完全に分離する挙動を実装（PAPER_TRADING_SQLITE_PATH で上書き可能）。
    - 起動時にプロセス優先度を "high" に設定。
    - 起動前に監視テーブルの存在を保証する init_monitoring_db 呼び出しを行う（冪等）。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを提供。MONITOR_POLL_INTERVAL 環境変数で間隔を上書き可能（デフォルト 60 秒）。
    - 監視は実行環境にかかわらず本番の sqlite_path を使用する挙動を明示。
    - 停止フラグ（data/stop_requested.flag）検知でループを終了。
- 設定管理・ヘルパー類を追加。
  - config.py
    - .env の自動読み込み機能（プロジェクトルート検出: .git または pyproject.toml を基準）。
    - .env のパース処理は export プレフィックス、シングル/ダブルクォート、エスケープ、インラインコメント（条件付き）等に対応。
    - Settings クラスにより各種設定（パス、閾値、API トークン、実行環境判定など）をプロパティとして提供。バリデーションも含む（環境名やログレベル等の検証）。
  - config_setup.py
    - 対話式ウィザードで .env を初期作成・更新する CLI を実装。秘密項目はマスク表示、確認プロンプト付きで .env を安全に生成。
  - validate_config.py
    - 起動前に .env と config/*.yaml（存在チェック・パース）を検証する CLI を実装。--strict モードにより警告を失敗扱いにできる。
    - PyYAML が未インストールの場合は YAML 検証をスキップして警告を出す。
- ロギング・プロセス管理ユーティリティを追加。
  - utils/logging_setup.py
    - StreamHandler（stdout）と TimedRotatingFileHandler（日次・30日保持）をルートロガーに一元設定するユーティリティを実装。
    - ログディレクトリ作成に失敗した場合はファイル出力をスキップしてコンソール出力のみ継続する耐障害設計。
  - utils/process_priority.py
    - Windows と POSIX 系（Linux/Mac/FreeBSD）を吸収するプロセス優先度設定ユーティリティを実装。
    - CPU affinity 設定ユーティリティ（最初の N コアに固定）も提供。アクセス権限や環境により失敗しても警告を出してスキップ。
- ポートフォリオ構築・リスク調整・単元丸めの純関数群を実装（DB 非依存、メモリ内計算）。
  - portfolio/portfolio_builder.py
    - BUY シグナルの候補選定（スコア降順、同点は signal_rank でタイブレーク）、等重み・スコア重みの計算を提供。スコアが全て 0 の場合は等重みへフォールバックして警告を出す。
  - portfolio/risk_adjustment.py
    - セクター集中制限（apply_sector_cap）と市場レジームに応じた乗数（calc_regime_multiplier）を実装。unknown セクターはセクター上限の対象外とする挙動。
    - 未知レジームでは 1.0 でフォールバックし警告を出す。
  - portfolio/position_sizing.py
    - allocation_method に応じた株数計算（risk_based / equal / score）を実装。
    - 単元（lot_size）丸め、1 銘柄上限、aggregate cap（利用可能現金でスケーリング）、cost_buffer（手数料・スリッページ見積り）を考慮したスケーリングと残差処理（端数処理）を実装。
- research/factor_research.py（ファクター計算基盤）を追加。
  - DuckDB 接続を受け取り prices_daily / raw_financials を参照して各種ファクター（モメンタム、Value、Volatility、Liquidity 等）を計算する設計を開始（関数・定数の骨格を実装）。
- ツール: Paper Trading 検証レポート生成スクリプトを追加。
  - tools/paper_verification_report.py
    - ペーパートレード用 SQLite（デフォルト data/paper_trading.db）からシステム稼働性、注文成功率、送信率、リスク却下数、API レイテンシ等の指標を集計してレポート出力。
    - P95 計算、日付フィルタ、閾値による PASS/FAIL 判定を実装（閾値はレポート冒頭で定義）。
- パッケージ定義・バージョンを追加。
  - __init__.py に __version__ = "0.1.0" を設定。

Fixed
- monitor 起動時の MONITOR_POLL_INTERVAL の不正値に対してデフォルトへフォールバックするロジックを追加（0 以下や非数値の指定で ValueError を避ける）。
- run_execution が停止フラグ検知時に不用意にエンジンを起動しないようガードを追加（起動前に停止フラグが立っている場合は起動せず終了）。
- init_monitoring_db を起動スクリプト側で呼び出し、監視テーブルが存在することを保証（冪等化）。

Changed
- （初期リリースのため該当なし）

Security
- 実行に必須の機密情報（J-Quants トークン、kabu API パスワード等）は Settings 経由で取得し、config_setup ウィザードではシークレット扱いでマスク表示するなど、誤コミットを避ける注意喚起を導入。

Notes / Operational considerations
- .env の自動ロードはデフォルトで有効。自動ロードを無効化する場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- run_monitoring は監視 DB として設定された sqlite_path（Settings.sqlite_path）を常に使用します。Monitoring を別 DB に切り離したい場合はコード側の調整が必要です。
- ロギングのファイル出力は指定されたログディレクトリの作成に依存します。権限等で作成に失敗した場合はコンソール出力のみで継続します。
- process_priority / cpu_affinity の設定は実行権限やプラットフォームに依存します。失敗時は警告を出して処理を継続します。
- research/factor_research.py はファクター計算ロジックの骨格を含みますが、データスキャンの実装や詳細な SQL 実装が未完の可能性があるため、使用前にテスト・レビューを推奨します。

Acknowledgments
- 本 CHANGELOG は提供されたソースコードの内容から機能・振る舞いを推測して作成しています。ドキュメント化やリリースノート向けに追加の詳細（修正履歴の正確な日付、コミット情報、既知の不具合など）があれば反映します。