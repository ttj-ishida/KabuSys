# Changelog

すべての注目すべき変更を記録します。フォーマットは Keep a Changelog に準拠します。

## [0.1.0] - 2026-04-16

### Added
- 基本サービス起動スクリプトを追加
  - run_execution.py: ExecutionEngine を起動するエントリポイントを追加。KABUSYS_ENV=paper_trading の場合は専用の Paper Trading SQLite DB（data/paper_trading.db 既定）と MockBrokerClient を使用する。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（既定 60 秒）。停止フラグファイル（data/stop_requested.flag）で安全に停止。
- 設定管理モジュール（kabusys.config）を追加
  - .env/.env.local 自動読み込み（プロジェクトルート検出: .git または pyproject.toml 基準）。環境変数優先で読み込み挙動を制御可能（KABUSYS_DISABLE_AUTO_ENV_LOAD により無効化）。
  - 各種プロパティ（DB パス、API トークン、監視閾値、環境名等）の取得と妥当性検証を提供。
- ポートフォリオ構築ライブラリを追加（kabusys.portfolio）
  - portfolio_builder: 候補選定（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）。
  - position_sizing: 株数決定ロジック（calc_position_sizes）。risk_based / equal / score の配分方式に対応。単元株丸め、aggregate cap によるスケールダウン、cost_buffer（手数料・スリッページ見積り）を考慮。
  - risk_adjustment: セクター集中制限（apply_sector_cap）、市場レジームに応じた投下資金乗数（calc_regime_multiplier）。
- 研究・リサーチ機能を追加（kabusys.research）
  - factor_research: モメンタム・ボラティリティ・バリュー系ファクターを DuckDB 上で計算するユーティリティ（calc_momentum, calc_volatility, calc_value）。
  - feature_exploration: 将来リターン計算（calc_forward_returns）、IC（calc_ic）、ファクター統計サマリ（factor_summary）、ランク関数（rank）。
  - DuckDB 接続を受け取り prices_daily / raw_financials を参照して純粋関数として実行可能。
- ニュース NLP スコアリング（kabusys.ai.news_nlp）
  - raw_news を集約して OpenAI（gpt-4o-mini）で銘柄ごとにセンチメント（-1.0〜1.0）を算出し、ai_scores テーブルへ書き込む処理を追加。バッチング、文字数制限、API リトライ（指数バックオフ）、レスポンス検証、スコアクリップを実装。
  - ニュース収集ウィンドウ計算ユーティリティ（calc_news_window）を提供。
- ユーティリティを追加
  - process_priority: クロスプラットフォームでプロセス優先度設定と CPU affinity を行うユーティリティ（set_process_priority, set_cpu_affinity）。権限不足等の例外は警告でスキップ。
- 運用ツールを追加
  - tools/paper_verification_report.py: Paper Trading 用の検証レポート生成スクリプトを追加。稼働率、注文成功率、送信率、レイテンシ（P95）などを算出して PASS/FAIL 判定を行う。閾値はファイル内定義（稼働率 99% など）。--from / --to / --db CLI をサポート。
- パッケージメタ情報
  - __version__="0.1.0" を設定。

### Changed
- DB 設定の分離
  - run_execution は paper_trading 環境時に専用の PAPER_TRADING_SQLITE_PATH（既定 data/paper_trading.db）を使用するように明確化。Monitoring は環境にかかわらず本番 sqlite_path を使用する仕様を明記。
- 環境変数パースの堅牢化
  - .env ファイル読み込みで export 形式・クォート・エスケープ・行内コメントを適切に処理するよう改善。既存 OS 環境変数を保護するため protected オプションを導入。
- ポートフォリオロジックの挙動調整
  - calc_score_weights が全銘柄のスコア合計が 0 の場合に等金額配分へフォールバックするよう変更（警告ログ出力）。
  - calc_position_sizes にて lot_size 単位での切り捨て・残余キャッシュへの再配分ロジックを導入し、aggregate cap 超過時のスケーリングを実装。
- ファクター／リサーチ SQL のパフォーマンス配慮
  - スキャン範囲をホライズンに応じたバッファ（日数×2）で限定することで DuckDB クエリの無駄な IO を削減。
- ニュース NLP のフェイルセーフ設計
  - API 失敗時は部分失敗を許容し、可能なデータを保持する方針。書き込みは対象コードのみ置換することで他コードの既存データを保護。

### Fixed
- run_execution/run_monitoring の安定起動・停止の扱いを明確化
  - 起動時に停止フラグが既に立っている場合は起動せず終了する仕組みを追加（run_execution）。
  - run_monitoring のポーリングループで check_once() の例外をキャッチして次ループへ継続するようにして、監視プロセスの永久停止を防止。
- .env 読み込み時のファイルアクセスエラーを警告に変換し、致命的エラーにならないよう改善。
- DuckDB executemany 前のパラメータ空チェックに関する注意喚起（ai モジュール設計注記）。

### Security
- OpenAI API 利用
  - news_nlp.score_news は OpenAI API キー（api_key 引数または OPENAI_API_KEY 環境変数）を必要とする。未設定時は ValueError を送出するため、運用時は安全にキー管理を行ってください。

### Notes / Migration
- .env の自動読み込みはデフォルトで有効（プロジェクトルートが見つからない場合や KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により無効化可能）。既存運用で環境変数の扱いが異なる場合は注意してください。
- Paper Trading 利用時は PAPER_TRADING_SQLITE_PATH を明示または環境変数で設定してください（デフォルト: data/paper_trading.db）。
- MONITOR_POLL_INTERVAL は整数（秒）を期待します。不正な値や 0 以下は警告のうえ既定値（60 秒）へフォールバックします。

---

このリリースは初期機能群の追加と運用・研究・ポートフォリオ構築の基盤を提供します。運用上の注意点や既知制限は今後のリリースで改善していきます。