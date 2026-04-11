CHANGELOG
=========

すべての重要な変更をこのファイルに記載します。  
フォーマットは "Keep a Changelog" に準拠しています。

[Unreleased]: https://example.com/kabusys/compare/v0.1.0...HEAD

## [0.1.0] - 2026-04-11

### Added
- 基本版リリースを追加。
- ポートフォリオ構築ロジック（kabusys.portfolio）を実装。
  - select_candidates: BUY シグナルのスコア降順フィルタリング（同点は signal_rank でブレーク）。
  - calc_equal_weights / calc_score_weights: 等金額配分・スコア加重配分を提供。スコア全ゼロ時は等配分へフォールバック。
  - calc_position_sizes: 発注株数計算（allocation_method: "risk_based" / "equal" / "score"）。単元株（lot_size）丸め、per-stock 上限、aggregate cap スケーリング、cost_buffer（手数料・スリッページ見積り）に対応。
  - apply_sector_cap: セクター集中上限チェック（既存保有を考慮、売却予定銘柄は除外可能）。"unknown" セクターは上限適用対象外。
  - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull/neutral/bear）。
- リサーチ機能（kabusys.research）を実装。
  - factor_research: calc_momentum / calc_volatility / calc_value — DuckDB の prices_daily / raw_financials を用いたファクター計算。
  - feature_exploration: calc_forward_returns / calc_ic / factor_summary / rank — 将来リターン、IC（Spearman）、統計サマリー等のユーティリティ。
  - 結果は (date, code) をキーとする dict のリストで返却し、DuckDB クエリにより効率的に計算。
- AI 関連モジュールを追加（kabusys.ai）。
  - news_nlp.score_news: raw_news を集約して OpenAI（gpt-4o-mini）でセンチメントを算出し、ai_scores テーブルへ冪等的に書き込み。バッチ処理、最大記事文字数制限、スコアクリップ（±1.0）、リトライ（429/ネットワーク/5xx）実装。
    - calc_news_window: JST ベースのニュース収集ウィンドウ算出（ルックアヘッド防止のため datetime.today() を直接参照しない設計）。
    - API 呼び出し部は _call_openai_api として切り出し、テスト時に差し替え可能。
    - 応答の厳密なバリデーションを実装（JSON 抽出、results キーと型チェック、未知コード除外）。
  - regime_detector: ETF 1321 の MA200 乖離（70%）とマクロニュース LLM センチメント（30%）を合成して日次の市場レジーム（'bull'/'neutral'/'bear'）を判定し market_regime テーブルへ書き込み。API 失敗時は macro_sentiment=0.0 でフォールバック（フェイルセーフ）。
- 実行用スクリプトを追加。
  - run_execution.py: ExecutionEngine の起動スクリプト。KABUSYS_ENV=paper_trading 時は MockBrokerClient を使用し、paper_trading 用 DB（data/paper_trading.db）へ記録して本番 DB と分離。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプト。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。monitoring は環境にかかわらず本番 sqlite_path を使用。
  - 両スクリプトとも起動直後にプロセス優先度を "high" に設定するユーティリティ呼び出しを行う。
- 設定管理（kabusys.config）を実装。
  - .env 自動読み込み（プロジェクトルート基準で .env → .env.local の順、OS 環境変数は保護）。
  - .env 行パーサは export 形式やクォート、インラインコメントの取り扱いに対応。読み込み失敗時は警告を発行して継続。
  - Settings クラスを提供し、各種環境変数をプロパティで取得。PAPER_FILL_MODE / KABUSYS_ENV / LOG_LEVEL 等の値検証を行い、不正値は ValueError を送出する。
  - paper_trading 用の sqlite パス（PAPER_TRADING_SQLITE_PATH）や pid/kill flag、しきい値設定（CPU/MEMORY/DISK）等をプロパティで管理。
- ユーティリティ（kabusys.utils）を充実。
  - process_priority.set_process_priority: Windows / POSIX (Linux/macOS/FreeBSD) の差分を吸収してプロセス優先度を設定。未対応 OS や権限不足時は警告を出してスキップ。
  - set_cpu_affinity: カレントプロセスの CPU affinity を最初の N コアに固定（引数 None で設定をスキップ）。権限不足や未対応環境でのフォールバックを実装。
- パッケージメタ情報: __version__ = "0.1.0" を設定。

### Changed
- 初期リリースのため変更履歴は割愛（初回公開）。

### Fixed
- 実行・監視ループでの例外処理を強化（check_once の例外をキャッチして次回ポーリングへ継続）。ポーリング間隔の環境変数が不正・0 以下の場合はデフォルトにフォールバックして安全に稼働するよう修正。
- DuckDB への書き込み（ai_scores）で部分失敗時に他銘柄の既存スコアを消さないよう、DELETE → INSERT をコード単位で実行する実装に変更（DuckDB 互換性とフェイルセーフを考慮）。

### Security
- OpenAI API キーの参照は引数優先、未設定時は環境変数 OPENAI_API_KEY を利用。未設定の場合は明示的にエラー（ValueError）を返すことで誤動作を防止。
- .env 自動読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能（テスト環境向けの安全弁）。

### Notes / Migration
- Settings のプロパティは環境変数の値検証を行います。既存の運用で環境変数に誤った値（例: KABUSYS_ENV や PAPER_FILL_MODE、LOG_LEVEL）が設定されている場合は起動時に ValueError が発生します。事前に設定を確認してください。
- run_monitoring は監視のために本番 sqlite_path を参照します。開発・テスト用途で本番 DB を使いたくない場合は注意してください。
- news_nlp・regime_detector の OpenAI 呼び出し部分は外部 API に依存します。API レートやキー管理に注意してください。API 呼び出し関数はテスト時に容易にモック可能です（_call_openai_api を差し替えられます）。
- DuckDB / SQLite のバージョン差異により executemany の空リスト挙動等に注意が必要です（コード側で回避済み）。

---

既知の制限・TODO（抜粋）
- position_sizing の lot_size は現状グローバル固定（将来的に銘柄別 lot_map の導入を検討）。
- price_map に欠損（0.0）がある場合、apply_sector_cap のエクスポージャー計算で過少評価される可能性あり（前日終値や取得原価をフォールバックする拡張を検討）。
- news_nlp の JSON mode でも稀に前後に余計なテキストが混ざることがあるため、最外の {} を抽出して復元するロジックを実装しているが、応答の多様性によっては精度低下の可能性あり。