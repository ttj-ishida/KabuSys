# CHANGELOG

すべての重大な変更はこのファイルに記録します。  
フォーマットは "Keep a Changelog" に準拠します。

## [0.1.0] - 2026-04-17

### Added
- 初版リリース: KabuSys 自動売買システムのコア機能を追加。
- 実行用スクリプト
  - run_execution.py: ExecutionEngine の起動スクリプトを追加。Environment に応じて paper_trading 用 DB を分離して使用（KABUSYS_ENV=paper_trading 時は paper_trading.db を使用）。エンジンは別スレッドで実行され、データディレクトリの stop_requested.flag により外部から安全に停止可能。
- 監視用スクリプト
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は環境に関わらず本番の sqlite_path を使用する仕様。
- 設定管理
  - config.Settings: .env 自動読み込み機能（プロジェクトルート検出）、.env / .env.local の取り扱い（OS 環境変数優先）、多くの設定プロパティを提供（DB パス、PID ファイル、監視閾値、paper_trading 関連設定等）。
  - .env パースはエクスポート構文、クォート、エスケープ、インラインコメントなどに対応する堅牢な実装を追加。
- ポートフォリオ構築
  - portfolio/portfolio_builder.py: 候補選定（スコア降順、タイブレークロジック）・等金額／スコア加重配分を実装。
  - portfolio/position_sizing.py: 株数決定ロジック（risk_based / equal / score）、単元株丸め、aggregate cap によるスケールダウン、cost_buffer を考慮した保守的見積りを実装。
  - portfolio/risk_adjustment.py: セクター集中制限（apply_sector_cap）および市場レジームに応じた投下資金乗数（calc_regime_multiplier）を実装。
- リサーチ機能（DuckDB ベース）
  - research/factor_research.py: Momentum / Volatility / Value ファクター計算。prices_daily / raw_financials テーブルを参照して純粋関数的に結果を返却。
  - research/feature_exploration.py: 将来リターン計算（複数ホライズン対応）、IC（Spearman）計算、ファクター統計サマリ、ランク関数を実装。外部依存を避けた純粋 Python 実装。
  - research パッケージで zscore_normalize（data.stats）をエクスポート。
- AI ニューススコアリング
  - ai/news_nlp.py: raw_news から銘柄ごとに記事を集約し OpenAI（gpt-4o-mini）でセンチメント評価を行う機能を追加。バッチ送信、リトライ（指数バックオフ）、レスポンス検証、スコアクリッピング（±1.0）、ai_scores テーブルへの置換書き込みの設計を実装。
  - ニュース収集ウィンドウ計算（JST→UTC の変換）を提供（calc_news_window）。
- ツール
  - tools/paper_verification_report.py: Paper Trading の検証レポート生成スクリプトを追加。稼働率、注文成功率、送信率、レイテンシ（平均・最大・P95）などを集計し PASS/FAIL を判定する閾値を定義。
- ユーティリティ
  - utils/process_priority.py: Windows / POSIX の差分を吸収するプロセス優先度設定ユーティリティ（set_process_priority）と CPU affinity 設定（set_cpu_affinity）を追加。権限不足や未対応プラットフォーム時に安全にフォールバック。
- DB 初期化
  - monitoring.monitoring_db.init_monitoring_db への呼び出し（監視テーブルの存在保証）を run_monitoring/run_execution の起動処理で実行。
- パッケージ情報
  - __init__.py にてパッケージバージョンを 0.1.0 として設定。

### Changed
- 設定読み込み順序を明確化: OS 環境変数 > .env.local > .env（.env.local は上書き許可）。OS 環境変数は保護され上書きされない。
- Paper trading の DB を本番と完全分離する仕様を採用（Settings.paper_sqlite_path, run_execution の分岐）。
- run_monitoring では監視用 DB に常に settings.sqlite_path（本番）を使用する仕様を明確化（監視は常に本番 DB を参照する）。
- position_sizing: allocation ロジックと aggregate cap の扱いを明確化。lot_size（単元）考慮と残差処理の実装を追加。
- factor / volatility / forward returns の SQL は DuckDB を前提に最適化されたクエリへ修正。
- feature_exploration.calc_forward_returns: horizons のバリデーション（1〜252）を追加して誤った入力を防止。

### Fixed
- .env パーサーの堅牢化:
  - export プレフィックス対応、シングル/ダブルクォート内のバックスラッシュエスケープ処理、インラインコメント取り扱いの改善。
  - 無効行やキーのない行をスキップすることで誤読を防止。
- run_monitoring/_get_poll_interval: MONITOR_POLL_INTERVAL が不正（0 以下や非数）の場合にデフォルトへフォールバックしログ出力するよう改善（time.sleep に渡す値の検証）。
- process_priority: 未対応 OS や権限不足時に適切に警告を出して処理を継続するよう改善。
- paper_verification_report: P95（パーセンタイル）計算の安定化、NULL/データ欠損時の N/A 表示や OperationalError を捕捉してレポート生成を継続する処理を追加。

### Security
- ai/news_nlp.score_news: OpenAI API キーが未設定の場合に明示的に ValueError を送出することで誤実行を防止。
- 設定モジュールで必須環境変数（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD）を _require() で検証し、未設定時に起動時に明示的なエラーを発生させる設計。

### Known issues / Notes
- ai/news_nlp.py の記事取得周り（_fetch_articles 等）の実装が途中で切れている箇所が見られます（ファイル末尾が不完全）。このためニューススコアリングのフルパス実行には追加の実装が必要です。
- 一部 TODO コメントあり（例: position_sizing の銘柄別 lot_size 拡張や price 欠損時のフォールバック価格）。将来的に拡張予定。
- 一部の SQL は DuckDB 固有のウィンドウ関数や ROWS 範囲を利用しており、他の SQL エンジンでの互換性は保証されません。
- 実行時のプロセス優先度設定や CPU affinity は実行環境の権限に依存するため、権限不足による警告が発生する可能性があります。

---

（注）この CHANGELOG は現行コードベースの内容から推測して作成しています。実際のコミット履歴・設計ドキュメントに基づく正式な変更履歴は別途作成してください。