# Changelog

すべての注目すべき変更をここに記録します。フォーマットは「Keep a Changelog」に準拠します。

※ リリース内容はソースコードから推測して作成しています。

## [Unreleased]

（なし）

## [0.1.0] - 2026-04-17

### Added
- パッケージ初期リリース "KabuSys" を追加。
  - パッケージバージョン: 0.1.0（src/kabusys/__init__.py）
- 実行系スクリプトを追加
  - run_execution.py
    - ExecutionEngine 起動スクリプト。プロセス優先度を起動時に "high" に設定。
    - KABUSYS_ENV が `paper_trading` の場合、paper_trading 用の専用 SQLite DB（デフォルト: data/paper_trading.db）を使用して本番 DB と分離。
    - BrokerClientFactory を介して本番/モックブローカーを切り替え可能（paper_trading 時は MockBrokerClient を利用する想定）。
    - 実行中の停止フラグ (data/stop_requested.flag) と PID 管理 (data/execution.pid) に対応。
- 監視系スクリプトを追加
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はデフォルトにフォールバックして警告を出力。
    - 監視は環境設定に関わらず本番 sqlite_path を使用して監視テーブルを操作。
    - 停止フラグ (data/stop_requested.flag) による安全停止をサポート。
- 設定/環境変数管理モジュールを追加
  - src/kabusys/config.py
    - .env 自動ロード機能（プロジェクトルートの検出: .git または pyproject.toml を基準）。
    - .env / .env.local の読み込み順序・上書きルール（OS 環境変数保護）。
    - 複雑な .env 行のパース対応（export プレフィックス、クォート・エスケープ、インラインコメントの取り扱い）。
    - 自動ロードを無効化する `KABUSYS_DISABLE_AUTO_ENV_LOAD` をサポート。
    - Settings クラスで主要な設定値をプロパティで提供（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、DUCKDB_PATH、SQLITE_PATH、PAPER_FILL_MODE 等）。
    - `PAPER_FILL_MODE` の値検証（有効値: instant|partial|never|reject）。
    - `KABUSYS_ENV` の値検証（development, paper_trading, live）。
- ポートフォリオ構築ライブラリ（純粋関数群）を追加
  - portfolio.portfolio_builder
    - select_candidates: スコア降順＋タイブレークで候補選定。
    - calc_equal_weights / calc_score_weights: 等配分およびスコア加重（全スコアが 0 の場合に等配分へフォールバック）。
  - portfolio.risk_adjustment
    - apply_sector_cap: セクター集中制限（既存保有を考慮、unknown セクターは制限免除）。
    - calc_regime_multiplier: 市場レジームに基づく投下資金乗数（bull/neutral/bear をマッピング、未知値はフォールバック警告）。
  - portfolio.position_sizing
    - calc_position_sizes: 複数の allocation_method（risk_based / equal / score）に対応。
    - 単元株（lot_size）丸め、最大ポジション比率・利用率・コストバッファを考慮した集約キャップ処理、スケーリングと端数分配ロジックを実装。
- 研究（Research）モジュールを追加
  - research.factor_research
    - calc_momentum, calc_volatility, calc_value: DuckDB の prices_daily/raw_financials を用いたファクター計算。
  - research.feature_exploration
    - calc_forward_returns: 将来リターン計算（任意ホライズン、入力検証あり）。
    - calc_ic: スピアマンランク相関（IC）計算、最小有効サンプルチェック。
    - factor_summary, rank: 基本統計量とランク化ユーティリティ（外部ライブラリ不使用で実装）。
  - research パッケージは zscore_normalize を data.stats から再輸出。
- AI ニュース NLP モジュールを追加（OpenAI を利用するニュースセンチメント処理）
  - ai.news_nlp
    - raw_news を集約して OpenAI（モデル: gpt-4o-mini）へバッチ送信し、銘柄ごとの ai_score を ai_scores テーブルへ書き込むフローを実装。
    - バッチサイズ、1銘柄あたり記事数・文字数の上限、JSON Mode 期待フォーマットの厳密検証、スコアクリップ（±1.0）、リトライ（429/5xx/接続エラーに指数バックオフでリトライ）等をサポート。
    - calc_news_window(target_date) でニュース収集ウィンドウ（JST → UTC 変換）を提供。
    - score_news は API キー解決（引数または環境変数 OPENAI_API_KEY）と書き込みカウントを返す。API キー未設定時は ValueError を送出。
- ツール: Paper Trading 検証レポート
  - tools/paper_verification_report.py
    - コマンドラインで paper_trading の SQLite データから検証レポートを生成（期間指定オプション --from / --to、--db で DB パス指定可）。
    - 稼働率、注文成功率、送信率、P95 レイテンシなどの指標取得と Pass/Fail 判定の出力。基準値はソース内で定義（稼働率 99% など）。
- DB / データ接続関連
  - duckdb を利用する分析用接続を提供（Settings.duckdb_path）。
  - 監視用テーブル初期化ユーティリティ init_monitoring_db を run_* スクリプトで呼び出し、監視テーブルの存在を保証。
- ユーティリティ
  - utils.process_priority
    - set_process_priority(level) で Windows / POSIX の差分を吸収してプロセス優先度を設定（失敗時はワーニングでスキップ）。
    - set_cpu_affinity(cpu_count) でプロセスを最初の N コアに固定（アクセス権限不足時はワーニングでスキップ）。

### Changed
- 初回リリースのため特段の変更履歴はなし（初版）。

### Fixed
- .env パーサの改善により以下をサポート／修正
  - export プレフィックス、クォート付き値（バックスラッシュエスケープ対応）、およびインラインコメントの扱いを明確化。
  - .env.local による上書きロジック（OS 環境変数は保護）を導入。
- MONITOR_POLL_INTERVAL の不正値ハンドリングを導入（0 以下や非整数時にデフォルトへフォールバックしワーニング出力）。

### Security
- 環境変数による機密情報管理を前提。OpenAI API キー・外部 API トークン等は環境変数で提供する設計のため、運用時は OS レベルの安全な管理を推奨。

### Notes / Known issues（コードから推測）
- ai/news_nlp.py の score_news 実装は堅牢な設計（バッチ・リトライ・レスポンス検証）を反映していますが、提供されたソースの最後の部分が途中で切れており、記事集約用関数（内部参照の _fetch_articles 等）や最終的な DB 書き込みロジックの完全実装が不足している箇所が確認されます。実運用前に以下を確認してください:
  - 記事取得／集約関数（_fetch_articles の実装）および AI レスポンスのパースと DB 書換ロジックが存在すること。
  - OpenAI レスポンスのバリデーションと部分失敗時のロールバック／保護（設計コメントにある挙動）を正しく実装済みであること。
- position_sizing の price 欠損時のフォールバックについては TODO コメントあり。前日終値や取得原価などのフォールバック価格ロジックが未実装のため、価格欠損データがあると投資量が過小見積になる可能性があります。

---

作成した CHANGELOG はソースコードの現状からの推測に基づきます。実際の変更履歴やリリースノート作成時には、コミットログ・PR記録・リリース方針に基づく追加の注記（互換性に関する注意、マイグレーション手順、運用上の注意点など）を追記してください。