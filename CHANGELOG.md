CHANGELOG
=========

すべての重要な変更を日付順に記録します。本ファイルは「Keep a Changelog」形式に準拠しています。

フォーマット:
- 変更はカテゴリ別（Added / Changed / Fixed / Deprecated / Removed / Security）に分類しています。
- 日付はリリース日を示します。
- 記載内容はソースコードから推測して作成した要約です。

Unreleased
----------

- （現在なし）

0.1.0 - 2026-04-13
-----------------

Added
- 初回公開: KabuSys 自動売買フレームワークのコアコンポーネントを追加。
  - portfolio: 銘柄選定・配分・ポジションサイズ計算・リスク調整の純粋関数群を追加。
    - portfolio_builder.select_candidates: スコア降順で候補抽出（signal_rank によるタイブレーク）。
    - portfolio_builder.calc_equal_weights / calc_score_weights: 等金額・スコア加重の重み計算。全銘柄スコアが 0 の場合は等分配にフォールバック。
    - risk_adjustment.apply_sector_cap: セクター集中の上限チェック（既存保有の時価ベースで判定、sell_codes を考慮）。
    - risk_adjustment.calc_regime_multiplier: 市場レジームに応じた乗数（bull/neutral/bear をサポート、未知値はフォールバック）。
    - position_sizing.calc_position_sizes: リスクベース / 等配分 / スコア配分に基づく発注株数決定、単元（lot）丸め、aggregate cap によるスケーリング。
  - research: ファクター計算・特徴量分析モジュールを追加。
    - research.factor_research: Momentum / Volatility / Value ファクター計算（DuckDB を用いた SQL ベースの実装）。
    - research.feature_exploration: 将来リターン計算、IC（Spearman ρ）計算、ファクター統計サマリ、ランキングユーティリティ。
    - research パッケージは zscore_normalize（data.stats 経由）をエクスポート。
  - ai.news_nlp: ニュースを OpenAI（gpt-4o-mini）でセンチメントスコア化し ai_scores テーブルに書き込む処理を追加。
    - ニュース集約ウィンドウの算出、記事トリミング、バッチ送信、リトライ（指数バックオフ）、レスポンス検証、スコアクリップなど機能を搭載。
  - monitoring / execution ランナー:
    - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプト。MONITOR_POLL_INTERVAL 環境変数で間隔上書き可。常に本番 sqlite_path を使用して監視データを記録。
    - run_execution.py: ExecutionEngine 起動スクリプト。KABUSYS_ENV=paper_trading 時は paper_trading 用 DB と MockBroker を使用して本番 DB と完全分離。
  - tools.paper_verification_report: Paper Trading 用の検証レポート生成スクリプトを追加。稼働率、注文成功率、送信率、レイテンシ（P95 等）などを集計して判定を出力。
  - config: 環境変数の自動ロードと管理を行う Settings クラスを追加。
    - .env / .env.local の自動読み込み（プロジェクトルート検出：.git または pyproject.toml）。
    - 環境変数必須チェック (_require)、各種デフォルトパス（DUCKDB_PATH, SQLITE_PATH 等）、paper_trading 用設定、監視閾値等を定義。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化。
  - utils.process_priority: クロスプラットフォームでのプロセス優先度設定ユーティリティを追加（Windows / POSIX 対応）。CPU affinity 設定関数も含む。
  - パッケージ初期化: kabusys.__init__ にバージョン情報（0.1.0）と主要サブパッケージの __all__ を追加。

Changed
- （初回リリースのため該当なし）

Fixed
- モジュール実装時に考慮された堅牢性向上点（実装上の注意・フォールバックを導入）。
  - config._parse_env_line: quotes やエスケープ、インラインコメントの扱いを丁寧に実装して .env の柔軟性を確保。
  - portfolio.position_sizing / risk_adjustment: 価格が欠損（<=0）時はスキップするようにして不正な計算を防止。
  - process_priority.set_process_priority / set_cpu_affinity: アクセス権限や未対応プラットフォームで例外を拾いログでスキップする安全策を追加。
  - monitoring / execution スクリプト: DB テーブル初期化（init_monitoring_db）を起動時に呼ぶことで冪等的に監視テーブルの存在を保証。
  - ai.news_nlp: API キー未設定時に ValueError を投げる明示的挙動、スコアの ±1.0 クリップ、チャンク処理のログ出力と部分失敗時の保護策（書き込み前にコード絞り込み）を実装。

Deprecated
- （初回リリースのため該当なし）

Removed
- （初回リリースのため該当なし）

Security
- OpenAI API キーや機密情報は環境変数経由での取り扱いを前提。自動 .env ロードは OS 環境変数を保護する設計（.env.local の上書き可。ただし OS 環境変数は保護）になっている点を明記。

Notes / Known limitations
- ai.news_nlp は OpenAI API を利用するため、ネットワーク障害や API 料金に注意。429 / 5xx / タイムアウトはリトライするが回復不能なケースはスキップされる。
- DuckDB を利用する research/ai モジュールは prices_daily / raw_financials / raw_news 等のテーブル構造に依存する。DB スキーマが存在しない環境では該当機能は実行できない（tools の各クエリは sqlite/duckdb の OperationalError を捕捉して N/A とする設計）。
- position_sizing の単元株（lot_size）は現状グローバル固定（デフォルト 100）。将来的に銘柄別の lot_map へ拡張することを想定するコメントあり。
- apply_sector_cap のエクスポージャー計算は price_map の欠損を 0 と扱うため、過小見積りとなり得る点が TODO コメントで明示されている。

開発者向けメモ
- 自動環境ロードはプロジェクトルートの検出に依存するため、パッケージ配布後の環境や CI では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を使って明示的に制御することを推奨。
- ロガーレベルの制御は Settings.log_level で行えるが、起動スクリプトでは基本的に logging.basicConfig(level=logging.INFO) を使用している。

以上

（この CHANGELOG は提示されたソースコードの実装・コメントから推測して作成しています。実際のリリースノートとして使用する際は必要に応じて調整してください。）