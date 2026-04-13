Keep a Changelog 準拠の形式で、提供されたコードベースから推測した変更履歴を日本語で作成しました。初回リリース相当の内容としてまとめています。必要なら過去リリースや細かいチケット参照を追加できます。

CHANGELOG.md
============

すべての重要な変更はこのファイルに記載します。  
フォーマットは "Keep a Changelog" に準拠しています。  

[Unreleased]
-------------

（未リリースの変更はここに記載）

[0.1.0] - 2026-04-13
--------------------

Added
- 初回リリース: KabuSys パッケージを追加。バージョンは __version__ = "0.1.0"。
- 実行エントリ
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔をオーバーライド可能（デフォルト 60 秒）。監視は環境設定にかかわらず本番 sqlite_path を使用して DB を初期化。
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。KABUSYS_ENV=paper_trading の場合は paper_trading 用の専用 SQLite DB を使用して MockBrokerClient（Factory 経由）で分離された動作を行う。プロセス優先度を高に設定して ExecutionEngine.run_session() を実行。
- 設定管理
  - config.py: 自動 .env 読み込み（プロジェクトルートの検出 .git / pyproject.toml 基準）、.env と .env.local の優先度処理、OS 環境変数保護（上書き禁止）。高度な .env パーサを実装（export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、コメント処理）。KABUSYS_DISABLE_AUTO_ENV_LOAD で自動ロードを無効化可能。
  - Settings クラス: 各種環境変数をプロパティとして提供（DB パス、PID/kill フラグパス、各種閾値、PAPER_FILL_MODE、env/log_level 検証など）。
- モジュール化したコンポーネント
  - execution/*: BrokerClientFactory、ExecutionEngine、OrderManager、OrderRepository、Reconciler、RiskManager（RiskConfig）等の組み立てロジックを追加。RiskConfig のデフォルト値（max_position_pct、max_utilization、rate_limit_per_sec、circuit_breaker_errors/window、max_drawdown など）を設定。initial_portfolio_value を broker.get_available_cash() から初期化。
  - monitoring/*: 監視 DB 初期化ユーティリティ（init_monitoring_db）や SystemMonitor を使用する仕組みを追加。
- ポートフォリオ構築
  - portfolio/portfolio_builder.py: 候補選定 select_candidates（スコア降順、同点は signal_rank 昇順タイブレーク）、等金額/スコア加重の重み計算（calc_equal_weights, calc_score_weights）。スコア合計が 0 の場合は等金額にフォールバック。
  - portfolio/risk_adjustment.py: apply_sector_cap（セクター上限チェック、売却予定銘柄を除外可能）、calc_regime_multiplier（bull/neutral/bear マッピング、未知レジームはフォールバック）を実装。
  - portfolio/position_sizing.py: calc_position_sizes を実装。risk_based / equal / score の割当方式、損切り・リスク率に基づく算出、単元株（lot_size）丸め、per-stock と aggregate の上限チェック、cost_buffer を考慮した保守的見積りとスケーリング、端数処理で残余キャッシュを再配分するアルゴリズムを導入。
- リサーチ機能（DuckDB ベース）
  - research/factor_research.py: calc_momentum, calc_volatility, calc_value を実装。prices_daily / raw_financials を参照してモメンタム・ボラティリティ・バリュー系ファクターを算出（MA200、ATR20、平均売買代金等）。窓サイズ・バッファは定数化。
  - research/feature_exploration.py: 将来リターン計算（calc_forward_returns）、IC（calc_ic：Spearman）や rank/ factor_summary（count/mean/std/min/max/median）を実装。外部ライブラリに依存せず純 Python + DuckDB で実装。
  - research/__init__.py: 主なユーティリティを公開（zscore_normalize を data.stats から再エクスポート）。
- ツール
  - tools/paper_verification_report.py: Paper Trading の検証レポート生成 CLI を追加。指定期間（--from / --to）またはデフォルト全期間の稼働率、注文成功率（fill_rate）, 送信率（send_rate）, p95 レイテンシ等を算出して PASS/FAIL を出力。閾値はソース内で定義（稼働率 99%、fill 90%、send 95%、P95 200ms）。DB が存在しない場合やテーブルが無ければ N/A を扱うフェイルセーフ。
- AI ニューススコアリング
  - ai/news_nlp.py: raw_news テーブルを集約し OpenAI API（gpt-4o-mini）へバッチ送信して銘柄ごとの sentiment score（-1.0〜1.0）を ai_scores テーブルへ書き込む機能を追加。バッチサイズ、記事数/文字数上限、リトライ＆指数バックオフ、レスポンスバリデーション、スコアクリッピング、部分成功時の DB 操作による既存スコア保護等の設計。calc_news_window によりニュース集計窓を JST ベースで算出（UTC に変換して DB 検索）。
- ユーティリティ
  - utils/process_priority.py: set_process_priority（Windows / POSIX を吸収して nice または Windows 優先度を設定）、set_cpu_affinity（指定コア数への固定）を実装。権限不足時は警告を出してスキップする安全処理を搭載。

Changed / Improved
- .env 読み込みの堅牢化: export プレフィックス、クォート内のバックスラッシュエスケープ、インラインコメント処理をサポート。プロジェクトルート自動検出により CWD に依存しない挙動。
- 設定値バリデーションを強化:
  - PAPER_FILL_MODE の許容値チェック（instant/partial/never/reject）。
  - KABUSYS_ENV と LOG_LEVEL の検証を追加。
  - MONITOR_POLL_INTERVAL の不正値に対するフォールバックと警告出力。
- エラー耐性の向上:
  - モニタリングループ内での check_once() の例外をログに残して次のポーリングへ継続。
  - DuckDB / SQLite のクエリ失敗（OperationalError）を考慮してレポート生成時に N/A を返す保護。
  - OpenAI API 呼び出しでの 429/タイムアウト/5xx に対するリトライ設計（指数バックオフ）。
- ロギング・診断情報: 多くのモジュールでデバッグ/情報ログを追加して挙動が追跡しやすくなった。

Fixed
- calc_score_weights: 全銘柄のスコア合計が 0 の場合にゼロ除算を回避して等金額配分へフォールバック（warning を出力）。
- calc_momentum/calc_volatility 等: ウィンドウ内のデータ不足時に None を返す一貫した仕様により、 downstream での未定義値処理を容易に。

Security
- .env 自動上書き時に OS 環境変数を protected として扱い、上書きを抑止する仕組みを導入（_load_env_file の protected 引数）。

Documentation / Notes
- 多数のモジュールに設計方針や注記（PortfolioConstruction.md / StrategyModel.md 参照）を docstring に記載。
- tools/paper_verification_report の CLI 使用例と環境変数の説明を追加。

Known limitations / Todo
- position_sizing の price フォールバック: price が欠損（0.0）の場合にエクスポージャーが過少見積りされる旨の TODO コメントあり。前日終値や取得原価などをフォールバックする拡張が検討対象。
- ai/news_nlp.py の書き込みロジックは部分失敗耐性を持つが、さらに堅牢なトランザクション処理（部分コミット回避やロールバック）を検討可能。
- 単元株（lot_size）は現状グローバル固定（デフォルト 100）。将来的に銘柄別 lot_map を導入予定。

参考（環境変数）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒）
- KABUSYS_ENV: development | paper_trading | live
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite DB パス（デフォルト data/paper_trading.db）
- DUCKDB_PATH / SQLITE_PATH / PID_FILE_PATH / KILL_FLAG_PATH / OPENAI_API_KEY / PAPER_FILL_MODE 等（詳細は config.Settings のプロパティ参照）
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により .env の自動読み込みを無効化可能

---

必要であれば各機能ごとにより細かいリリースノート（例: 主要関数の入力/出力仕様、期待される DB スキーマ、CLI の出力サンプル）を追記できます。