CHANGELOG
=========
すべての notable な変更は Keep a Changelog の形式に従って記載しています。
慣例:
  - 変更はカテゴリ別（Added, Changed, Fixed, ...）に整理
  - 日付は本ファイル作成日（2026-04-17）

[Unreleased]
-------------

[0.1.0] - 2026-04-17
-------------------

Added
- 基本アプリケーション骨格を実装（初期リリース）。
  - パッケージ情報: kabusys.__version = "0.1.0"。
- 実行用スクリプトを追加。
  - run_execution.py:
    - ExecutionEngine を起動するエントリポイント。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用の専用 SQLite DB（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）を使用し、本番 DB と完全分離する挙動を実装。
    - BrokerClientFactory を用いたブローカークライアント生成。
    - OrderRepository, OrderManager, RiskManager, Reconciler を組み合わせて ExecutionEngine を構築・起動。デーモンスレッドで実行し、stop flag により安全に停止可能。
    - プロセス PID 管理（data/execution.pid）、停止フラグ（data/stop_requested.flag）に対応。
    - デフォルトの RiskManager 設定（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker など）を採用。
  - run_monitoring.py:
    - SystemMonitor のポーリングループ起動スクリプト。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値入力時のフォールバック処理あり。
    - 監視は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する仕様（監視データは本番 DB を参照/保存）。
    - stop flag による安全終了、KeyboardInterrupt 対応あり。
- 環境設定・検証系 CLI を実装。
  - config_setup.py:
    - インタラクティブな .env 作成・更新ウィザード。
    - デフォルト値・選択肢・シークレット入力（マスク表示）に対応し、最終確認の後に .env を生成/上書き。
    - .env に関する注意（Git へコミットしない等）を明記して出力。
  - validate_config.py:
    - .env と config/*.yaml の事前検証ツール。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の検証、DB パス親ディレクトリ確認、YAML パースチェック（PyYAML があれば実行）などを実装。
    - --strict オプションで警告を FAIL 扱いにできる。
- 環境変数ロード機構を実装・強化（config.py）。
  - プロジェクトルート自動検出（.git または pyproject.toml を基準）により .env/.env.local の自動読み込みを行う（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
  - .env パーサの強化:
    - export プレフィックス対応、クォート（シングル/ダブル）内のバックスラッシュエスケープ対応、インラインコメントの取り扱い、無効行のスキップなど。
  - Settings クラスに各種設定プロパティを提供（J-Quants/Kabu API, DuckDB/SQLite パス, PID/kill flag パス, 監視しきい値, PAPER_FILL_MODE の検証等）。
  - PAPER_FILL_MODE に対する入力検証（instant/partial/never/reject）。
- ポートフォリオ構築関連（純粋関数モジュール）。
  - portfolio/portfolio_builder.py:
    - 候補選定（select_candidates）、等重・スコア加重（calc_equal_weights, calc_score_weights）。
    - スコア合計が 0 の場合のフォールバック警告（等金額配分）。
  - portfolio/risk_adjustment.py:
    - セクター集中制限の適用（apply_sector_cap）。
    - 市場レジームに応じた投下資金乗数（calc_regime_multiplier）。既知レジーム（bull/neutral/bear）に対応、未知レジームはフォールバックして 1.0 を返す。
    - apply_sector_cap は "unknown" セクターを除外しないなどの仕様を採用。
  - portfolio/position_sizing.py:
    - position size 計算（risk_based / equal / score）。
    - lot_size（単元株）での丸め、portfolio レベル・position レベルの上限検査、aggregate cap（利用可能現金に応じたスケーリング）を実装。
    - cost_buffer による手数料・スリッページ考慮、残余キャッシュを使った端数配分ロジックを実装。
    - 不足価格等のケースはログ出力してスキップ。
- 監視・運用支援ツールを追加。
  - tools/paper_verification_report.py:
    - Paper Trading 用 SQLite DB から稼働率、注文成功率、送信率、レイテンシ（avg/max/P95）などを集計し、PASS/FAIL 判定付きで標準出力レポートを生成。
    - デフォルト閾値（稼働率 99%、成立率 90%、送信率 95%、P95 200 ms）を採用。P95 計算や期間フィルタの実装あり。
- 研究用ファクター計算モジュール（research/factor_research.py）。
  - DuckDB を使って prices_daily / raw_financials を参照し、Momentum / Volatility / Liquidity / Value 等のファクター計算関数を実装（calc_momentum, calc_volatility 等）。
  - スキャン幅・ウィンドウ長等の定数を管理し、データ不足時の None 返却を行う設計。
- ユーティリティ。
  - utils/process_priority.py:
    - psutil を用いたクロスプラットフォームなプロセス優先度設定（set_process_priority）と CPU affinity 設定（set_cpu_affinity）。
    - Windows と POSIX（Linux/Mac/FreeBSD）向けの実装差分吸収、パーミッション不足時の警告ログ。
  - 各モジュールの __all__ エクスポート整理（portfolio/__init__.py 等）。

Changed
- （設計面）監視プロセスが常に本番向け sqlite_path を使う仕様を採用。これにより監視データは環境に依存せず一元化される。
- .env 読み込み順序: OS 環境変数 > .env.local > .env（.env.local は上書き許可）。
- config_setup で生成する .env のテンプレートに注意書き（.env を Git に含めない等）を追加。

Fixed
- MONITOR_POLL_INTERVAL に 0 以下や不正な文字列が設定された場合の例外発生を回避（フォールバック&警告）。

Security
- .env ファイルに関する注意喚起を追加（生成された .env を絶対に Git にコミットしないこと）。config_setup の出力にも注意書きを含める。

Notes / Known limitations / TODO
- portfolio/risk_adjustment.apply_sector_cap:
  - price_map に価格が欠損（0.0）の場合にエクスポージャーが過少見積りされる可能性あり。将来的には前日終値や取得原価でのフォールバックを検討する旨を TODO コメントで記載。
- position_sizing:
  - 銘柄ごとの単元（lot_size）を将来的に銘柄マスタから取得する拡張を想定（現在は共通 lot_size パラメータ）。
- process_priority/set_cpu_affinity:
  - 一部 OS では未対応または権限不足で失敗するケースがあるため、例外時は警告ログを出してスキップする設計。
- research/factor_research は DuckDB と prices_daily/raw_financials に依存。実行時にデータが不足すると None を返却する箇所がある。

Upgrade notes
- 本リリースは初期公開版です。導入時は以下を確認してください。
  - .env（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD 等の必須項目）を正しく設定すること。
  - 本番運用時は KABUSYS_ENV=live の際の LINE 通知設定（LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID）と KILL_FLAG_CLEAR_ON_START の設定に注意すること。
  - Paper Trading を使う場合は PAPER_TRADING_SQLITE_PATH を適切に設定して本番 DB と分離すること。

参考: 主要な環境変数
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV (development / paper_trading / live)
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (デフォルト: data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH (デフォルト: data/paper_trading.db)
- PAPER_FILL_MODE (instant / partial / never / reject)
- MONITOR_POLL_INTERVAL (監視ポーリング間隔、秒。デフォルト 60)
- KABUSYS_DISABLE_AUTO_ENV_LOAD (1 にすると .env の自動ロードを無効化)

もし特定の変更点（例: 個別ファイルの差分やコミット履歴に基づいた詳しい履歴）が必要であれば、対象のファイル/機能を指定してください。