CHANGELOG
=========

この CHANGELOG は Keep a Changelog の形式に準拠しています。  
以下は与えられたコードベースから推測して作成した変更履歴（日本語）です。

Unreleased
----------

なし

0.1.0 - 2026-04-13
------------------

Added
- 基本パッケージ初期リリース（kabusys 0.1.0）。
- 実行エントリスクリプト
  - run_execution.py: ExecutionEngine を起動する CLI スクリプトを追加。プロセス優先度を開始時に "high" に設定し、BrokerClientFactory による実際の / モックのブローカー選択、OrderRepository / OrderManager / RiskManager / Reconciler を組み立ててセッションを実行する。paper_trading 環境では専用 SQLite（data/paper_trading.db がデフォルト）を使用し、本番 DB と分離。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。起動時にプロセス優先度を "high" に設定する。
- 設定・環境変数管理
  - kabusys.config.Settings を導入。.env 自動ロード（プロジェクトルートを .git / pyproject.toml から探索）機能を追加。読み込み順は OS 環境 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
  - .env パーサーで export KEY=val 形式、シングル/ダブルクォートとバックスラッシュエスケープ、コメントルールなどに対応。
  - 必須キー取得時の _require() と各種プロパティ（DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH, PID_FILE_PATH 等）を提供。
  - PAPER_FILL_MODE, KABUSYS_ENV, LOG_LEVEL 等のバリデーション実装（無効値は ValueError）。
- DB 初期化 / 接続
  - monitoring 用テーブル初期化関数 init_monitoring_db を run 系から呼び出すことで冪等にテーブル存在を保証。
  - DuckDB 接続を各モジュールで利用する設計（research / ai / その他で利用）。
- ポートフォリオ構築（純粋関数群）
  - kabusys.portfolio.portfolio_builder: BUY シグナル選別（select_candidates）、等配分（calc_equal_weights）、スコア加重（calc_score_weights）。
  - kabusys.portfolio.risk_adjustment: セクター集中制限の適用（apply_sector_cap）、市場レジームに応じた乗数（calc_regime_multiplier）。
  - kabusys.portfolio.position_sizing: 発注株数計算（calc_position_sizes）。risk_based / equal / score の配分方式をサポート、lot_size（単元）丸め、aggregate cap によるスケーリング、cost_buffer を考慮した保守的見積り等を実装。
- 研究（research）モジュール
  - kabusys.research.factor_research: Momentum / Volatility / Value ファクター計算関数（calc_momentum, calc_volatility, calc_value）。DuckDB の SQL ウィンドウ関数を活用し、欠損データに対する安全な扱いを実装。
  - kabusys.research.feature_exploration: 将来リターン算出（calc_forward_returns）、IC 計算（calc_ic）、ファクターサマリ（factor_summary）、rank ユーティリティを提供。外部ライブラリに依存せず標準ライブラリのみで実装。
  - 研究モジュールは外部 API に一切アクセスしない設計。
- AI ニュース NLP
  - kabusys.ai.news_nlp: raw_news を OpenAI (gpt-4o-mini) にバッチ送信して銘柄ごとのセンチメントスコアを ai_scores テーブルへ書き込む機能を追加。バッチサイズ、記事/文字数上限、JSON Mode による厳密なレスポンス検証、スコアの ±1.0 クリッピング、429/タイムアウト/5xx に対するエクスポネンシャルバックオフによるリトライを実装。
  - ニュース集計ウィンドウを JST ベースで計算（前日 15:00 JST 〜 当日 08:30 JST）する calc_news_window を提供。
  - API キー未設定時は ValueError を送出。
- ユーティリティ
  - kabusys.utils.process_priority: プラットフォーム差分（Windows / POSIX）を吸収する set_process_priority と set_cpu_affinity を提供。権限不足や未対応 OS の場合は警告を出してスキップする安全策を実装。
- ツール
  - kabusys.tools.paper_verification_report: Paper Trading 検証レポート生成スクリプトを追加。稼働率・注文成功率・送信率・P95 レイテンシ等を算出し、閾値に基づく PASS/FAIL 判定を行う。CLI 引数 --from/--to/--db をサポート。
- パッケージ初期化とバージョン
  - kabusys.__init__.py に __version__ = "0.1.0" を設定。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Deprecated
- なし

Removed
- なし

Security
- OpenAI API キーは明示的に引数または OPENAI_API_KEY 環境変数で解決する仕様。未設定時はエラーで早期検出。

Notes / Design decisions / 既知点
- 監視（run_monitoring.py）は意図的に KABUSYS_ENV に依存せず本番 sqlite_path を使用する設計になっている。監視用 DB として常に本番パスを参照する点に注意。
- run_execution.py は paper_trading 環境時に paper_trading 用 DB を使う（本番 DB と完全分離）。
- .env 自動ロードはプロジェクトルート（.git または pyproject.toml）を基準に探索するため、パッケージ配布後でも CWD に依存せず動作する想定。ただしプロジェクトルートが見つからない場合は自動ロードをスキップする。
- process_priority / cpu_affinity は権限や OS によって失敗する可能性があり、その場合は警告を出して起動を継続するフェイルセーフを採用。
- research モジュールは DuckDB のテーブルスキーマ（prices_daily, raw_financials 等）に依存する。テーブル構造や日付範囲の前提が満たされない場合、一部結果が None になる（設計どおり）。
- ai.news_nlp は OpenAI 呼び出しを行うためレート制限や課金に注意。レスポンスのバリデーションを厳密に行うが、部分的失敗時のデータ保護（既存スコアの保護）を考慮した書き込み手順を採用。
- paper_verification_report は DB が存在しない場合やテーブルがない場合に graceful にメッセージを出力して終了する。

今後の改善候補（参考）
- 銘柄ごとの lot_size を銘柄マスタで管理して position_sizing に注入する（現在は全銘柄共通の lot_size）。
- price 欠損時のフォールバック（前日終値や取得原価）を追加して sector_exposure の過少見積りを改善。
- ai.news_nlp のレスポンスバリデーション時により詳細なログ/メトリクスを追加。
- run_monitoring の DB 選択を設定で制御可能にするオプション追加（現状は意図的な設計）。

----------

（注）上記は提示コードの実装内容から推測してまとめた CHANGELOG です。実際のコミット履歴や変更セットが存在する場合はそちらを優先してください。