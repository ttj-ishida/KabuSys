# Changelog

すべての変更は Keep a Changelog の形式に準拠しています。  
日付はリリース日を示します。

## [0.1.0] - 2026-04-12

### Added
- 基本パッケージ構成を追加（kabusys 0.1.0）。
  - __version__ を "0.1.0" に設定。
- 実行系・監視ランナー
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV が `paper_trading` の場合は MockBrokerClient を使用し、paper_trading 用の専用 SQLite DB（デフォルト: data/paper_trading.db）へ記録する（本番 DB と分離）。
    - 起動時にプロセス優先度を設定（utils.process_priority.set_process_priority）。
    - duckdb 接続を受け取り、ExecutionEngine を構成して run_session を実行。
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可（デフォルト 60 秒）。
    - 監視は環境に関係なく本番 sqlite_path を使用する実装。
    - エラーハンドリングと KeyboardInterrupt での正しい終了処理を実装。
- 設定管理
  - config.Settings を追加。環境変数と .env ファイルの管理を統一。
    - .env 自動ロード機構を実装（プロジェクトルートの .git または pyproject.toml を基準に探索）。
    - 読み込み順序: OS 環境 > .env.local > .env。OS 環境を上書きしない保護機構を備える。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 による自動ロード無効化をサポート（テスト用）。
    - 複数の設定項目をプロパティで提供（例: PAPER_FILL_MODE、PAPER_TRADING_SQLITE_PATH、PID_FILE_PATH、閾値設定、LOG_LEVEL、KABUSYS_ENV 判定ユーティリティ等）。
    - 環境変数値のバリデーション（有効値チェック、未設定時の明示的エラー等）。
- ユーティリティ
  - utils.process_priority:
    - set_process_priority(level) を実装。Windows / POSIX の差分を吸収してプロセス優先度を設定。
    - set_cpu_affinity(cpu_count) を追加。プロセスを最初の N コアに固定する機能（None の場合は変更しない）。
    - 権限不足・未対応 OS では警告を出して安全にスキップする。
- ポートフォリオ構築（純粋関数群）
  - portfolio.portfolio_builder:
    - select_candidates: スコア降順で候補抽出（同点は signal_rank でタイブレーク）。
    - calc_equal_weights / calc_score_weights: 等金額・スコア加重配分。全スコアが 0 の場合は等配分にフォールバック。
  - portfolio.risk_adjustment:
    - apply_sector_cap: セクター集中を防止するフィルタリング（売却予定銘柄除外や "unknown" セクター扱いの説明を含む）。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull/neutral/bear をサポート、未知のレジームは 1.0 でフォールバック）。
  - portfolio.position_sizing:
    - calc_position_sizes: 株数算出ロジックを実装（risk_based / equal / score の各方式、lot_size 単位で丸め、aggregate cap によるスケールダウン、コストバッファ対応）。
- リサーチ / ファクター計算
  - research.factor_research:
    - calc_momentum, calc_volatility, calc_value を実装。DuckDB の prices_daily / raw_financials を使用して各種ファクターを計算（MA200、ATR20、リターン等）。
  - research.feature_exploration:
    - calc_forward_returns: 将来リターンを一括取得するクエリ。
    - calc_ic: スピアマンランク相関（Information Coefficient）を実装（ties の平均ランク処理含む）。
    - factor_summary / rank: 基本統計量・ランク計算ユーティリティを追加。
  - research パッケージの公開 API を __init__ に整備。
- AI / ニュース NLP
  - ai.news_nlp:
    - raw_news と news_symbols を集約して OpenAI（gpt-4o-mini）を用いた銘柄ごとのセンチメントスコアリングを実装。
    - タイムウィンドウ計算（JST ベース → UTC 変換）、バッチ（最大 20 銘柄）処理、トークン肥大化対策（記事数・文字数の上限）、エクスポネンシャルバックオフによるリトライ、レスポンスバリデーション、スコアクリップ、部分成功時の安全な DB 更新戦略（DELETE/INSERT の絞り込み）を含む。
    - OPENAI_API_KEY 未設定時の ValueError を実装。
- ツール
  - tools.paper_verification_report:
    - Paper Trading 検証レポート生成ツールを追加（コマンドライン実行可能: python -m kabusys.tools.paper_verification_report）。
    - レポート出力（稼働率・注文成功率・送信率・P95 レイテンシ等）と PASS/FAIL 判定基準を実装。デフォルト DB は data/paper_trading.db。--from/--to/--db オプションをサポート。
    - 複数の SQL クエリで存在しないテーブルを想定した堅牢な例外処理を実装（OperationalError をキャッチしてデフォルト値にフォールバック）。

### Changed
- .env 読み込みの柔軟化
  - _parse_env_line: export 句、クォート文字列のバックスラッシュエスケープ、インラインコメントの扱いなどを考慮したパーサを実装。
  - _load_env_file: ファイルが読めない場合に warnings.warn を出すようにして安全性を強化。
- DB 初期化
  - run_execution/run_monitoring で init_monitoring_db を呼び出し、監視テーブルが存在することを冪等に保証するように変更。
- ロギング・エラーメッセージの改善（各モジュールで info/debug/warning を適切に追加）。

### Fixed
- 設定バリデーション
  - PAPER_FILL_MODE の不正値検出と明確なエラーメッセージを追加。
  - KABUSYS_ENV / LOG_LEVEL の有効値チェックを追加。
- ポーリング間隔の堅牢化
  - _get_poll_interval() において、0 または負の値や非整数の環境変数が設定された場合にデフォルト値へフォールバックするように修正（time.sleep への不適切な値渡しを防止）。
- calc_score_weights: 全銘柄のスコアが 0.0 の場合に警告を出して等金額配分へフォールバック。
- position_sizing のスケールダウン処理で残余キャッシュを有効活用するロジックを追加（lot 単位での再配分）。
- process_priority の権限不足や未対応 OS での例外をログ警告に置き換え、プロセスを続行できるように改修。
- research.feature_exploration.calc_forward_returns: horizons の検証を追加（正の整数かつ <= 252）。

### Deprecated
- なし

### Removed
- なし

### Security
- OpenAI API キーは引数または環境変数 OPENAI_API_KEY から読み取る仕様。未設定時は明示的な例外を発生させることで誤操作を抑止。

---

## マイグレーション / 運用上の注意
- 監視 (run_monitoring) は「環境にかかわらず本番 sqlite_path を使用する」よう実装されています。開発環境で別 DB を期待している場合は注意してください。
- 実行 (run_execution) は KABUSYS_ENV=paper_trading のときに paper_trading 用 DB（PAPER_TRADING_SQLITE_PATH）を使用します。本番 DB を上書きしないため安全にペーパートレードできます。
- 自動で .env を読み込む動作は既定で有効です。CI/テスト等で自動ロードを抑止したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- MONITOR_POLL_INTERVAL の指定には正の整数を使ってください。無効な値は 60 秒にフォールバックします。
- PAPER_FILL_MODE の有効値は "instant" / "partial" / "never" / "reject" のいずれかです。不正値は ValueError を投げます。
- OpenAI によるニューススコアリングを利用する場合、OPENAI_API_KEY を設定してください（もしくは score_news に api_key を渡す）。

もし特定ファイルの変更内容をより詳細に記載したい場合は、そのファイル名を指定してください。追加のリリースノート（例: 例外ケースや性能に関するベンチ結果）も必要であれば生成します。