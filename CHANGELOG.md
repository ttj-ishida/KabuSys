CHANGELOG
=========

すべての注目に値する変更はこのファイルに記録します。  
フォーマットは Keep a Changelog に準拠します。

Unreleased
----------

- （なし）

0.1.0 - 2026-04-18
------------------

Added
- 初回リリース: KabuSys 自動売買フレームワークの基本コンポーネントを追加。
  - パッケージ初期化とバージョン情報 (src/kabusys/__init__.py).
- 実行系・監視の起動スクリプトを追加。
  - ExecutionEngine 起動スクリプト (src/kabusys/run_execution.py):
    - 環境に応じて paper_trading 用 DB と MockBrokerClient を分離して使用。
    - スレッドで ExecutionEngine を起動し、data/stop_requested.flag による外部停止に対応。
    - PID ファイル管理 (data/execution.pid)。
  - SystemMonitor ポーリングループ起動スクリプト (src/kabusys/run_monitoring.py):
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番用 sqlite_path を使用して監視テーブルを初期化。
    - 停止フラグ検出・KeyboardInterrupt ハンドリング・接続クローズ保証。
- 設定・環境変数管理を実装。
  - Settings クラスによる集中管理 (src/kabusys/config.py):
    - 自動 .env ロード (.env, .env.local) をプロジェクトルート (.git または pyproject.toml 基準) から行う（無効化可）。
    - .env のパースは export 形式、引用符、エスケープ、インラインコメント等に対応。
    - 各種環境変数のデフォルト、検証（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE など）を提供。
    - paper_trading 用 DB パスと各種しきい値等のプロパティを提供。
  - 環境設定ウィザード CLI (src/kabusys/config_setup.py):
    - 対話式で .env を作成・更新するウィザード。シークレット値のマスク表示、既存値の再利用、保存確認機能を持つ。
  - 設定検証 CLI (src/kabusys/validate_config.py):
    - 必須環境変数、KABUSYS_ENV、LOG_LEVEL、DB パスの親ディレクトリ、config/*.yaml の存在とパース（PyYAML 利用可）等をチェック。
    - --strict オプションで警告を失敗扱いにできる。
- ポートフォリオ構築ロジック（純粋関数群）を追加（DB 参照なし）。
  - 候補選定・重み計算 (src/kabusys/portfolio/portfolio_builder.py):
    - select_candidates, calc_equal_weights, calc_score_weights（スコア合計が 0 の場合は等分配へフォールバック）。
  - セクター集中度制御・レジーム乗数 (src/kabusys/portfolio/risk_adjustment.py):
    - apply_sector_cap（既存ポジションを考慮したセクター上限除外）、calc_regime_multiplier（bull/neutral/bear のマッピング）。
  - 株数決定・投下資金スケーリング (src/kabusys/portfolio/position_sizing.py):
    - risk_based / equal / score の配分方式に対応。
    - lot_size 単位丸め、個別上限・aggregate cap のスケーリング、cost_buffer による保守的見積り。
    - スケールダウン時に残差を考慮して lot 単位で再配分するロジックを備える。
  - portfolio パッケージのエクスポートを整備 (src/kabusys/portfolio/__init__.py).
- ユーティリティ群を追加。
  - ロギング設定ユーティリティ (src/kabusys/utils/logging_setup.py):
    - stdout StreamHandler と 日次ローテーションの TimedRotatingFileHandler（30日保持）をルートロガーに設定。
    - ログディレクトリ作成失敗時はファイル出力をスキップしてコンソール出力のみで継続。
    - LOG_LEVEL / LOG_DIR の解決順を実装。
  - プロセス優先度 / CPU affinity 設定ユーティリティ (src/kabusys/utils/process_priority.py):
    - Windows / POSIX を吸収して nice値や Windows priority を設定。失敗時は警告を出してスキップ。
    - set_cpu_affinity による指定コアへのピン留め機能。
- Execution 系の補助コンポーネントを組み立てるためのコード追加（参照のみ、実体は別ファイルで実装される想定）。
  - BrokerClientFactory, ExecutionEngine, OrderManager, OrderRepository, Reconciler, RiskManager 等への呼び出し（src/kabusys/run_execution.py）。
  - RiskManager のデフォルト設定値（max_position_pct, max_utilization, rate_limit_per_sec など）を用意。
- 監視（monitoring）DB 初期化呼び出しを提供（init_monitoring_db を各起動スクリプトで呼ぶ）。
- 分析／研究用モジュール（部分実装）。
  - ファクター計算モジュール (src/kabusys/research/factor_research.py):
    - Momentum、MA200乖離、ATR、出来高等の計算方針と定数を定義。DuckDB 接続を受け SQL/Python で計算する設計。
    - 実装は途中（ファイル末尾で未完: 一部コード切れ）。
- ペーパートレード検証ツールを追加。
  - Paper Trading 検証レポート生成スクリプト (src/kabusys/tools/paper_verification_report.py):
    - 指標: 稼働率、注文成功率（Filled/Created）、送信率（Sent/Created）、リスク却下数、レイテンシ（avg/max/P95）。
    - デフォルト閾値（稼働率 99%、注文成功率 90%、送信率 95%、P95 レイテンシ 200ms）に基づく PASS/FAIL 判定。
    - DB path は引数 --db / 環境変数 PAPER_TRADING_SQLITE_PATH / デフォルトで解決。
    - latency の P95 は単純パーセンタイル計算を使用。
- その他ドキュメント・設計メモ（コード内コメント）:
  - PortfolioConstruction.md, StrategyModel.md 等の参照を明示した設計方針。
  - TODO / 注意点の注釈（例: price 欠損時のフォールバック、将来的な lot_size 拡張など）。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Known issues / Limitations
- research/factor_research.py は途中までしか実装されておらず、完全なファクター出力が未完成（ファイル末尾で切れている）。
- position_sizing の price フォールバックが未実装（コード内に TODO コメントあり）。価格欠損時に保守的な挙動となる可能性。
- 単元株数 lot_size は現状グローバル固定（将来的に銘柄別対応が想定されている）。
- ログディレクトリの作成やプロセス優先度の変更は権限に依存し、失敗時は警告でスキップされる（設計上意図的）。
- config/*.yaml の厳密なスキーマ検証機能は現状未実装（PyYAML によるパース確認のみ）。

Notes
- .env の自動読込はプロジェクトルートが特定できない場合はスキップされる。自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定する。
- MONITOR_POLL_INTERVAL や PAPER_FILL_MODE など、いくつかの挙動は環境変数で調整可能。無効な値はログ警告でデフォルトにフォールバックする設計。
- paper_trading を明示すると SQLite DB を data/paper_trading.db に分離して使用し、本番データと完全に分離することを意図している。

Security
- 機密情報（トークン・パスワード）は .env に保存する設計だが、.env を Git に含めない旨を README コメントで注意している (.env は絶対にコミットしない)。

-----

上記はソースコードとコメントから推測して作成した変更履歴です。追加でリリースノートの形式合わせ（Unreleased の追記、コミット単位の詳細化、影響範囲の明記など）や、ファイル一覧に基づく個別の変更箇所追跡が必要であればお知らせください。