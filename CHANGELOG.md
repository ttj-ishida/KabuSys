# Changelog

すべての重要な変更をこのファイルに記録します。  
このプロジェクトは Keep a Changelog の慣習に従います。

## [Unreleased]
（なし）

## [0.1.0] - 2026-03-28
初回リリース

### Added
- パッケージ基盤
  - パッケージメタ情報を追加（kabusys.__version__ = "0.1.0"）。パッケージの公開エントリとして data/strategy/execution/monitoring を公開。
- 環境設定
  - 環境変数／.env 管理モジュールを追加（kabusys.config）。
    - .env / .env.local の自動読み込み（プロジェクトルートは .git または pyproject.toml を基準に検出）。
    - export 付き行、クォート付き値、インラインコメントなどを考慮したパーサ実装。
    - 自動ロード無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
    - 必須変数取得用の _require と Settings クラスを提供（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID など）。
    - 一部設定にはバリデーション（KABUSYS_ENV, LOG_LEVEL）を実装。
- データ基盤（DuckDB を想定）
  - ETL パイプライン結果型 ETLResult を公開（kabusys.data.pipeline, kabusys.data.etl）。
    - ETL の実行概要（取得数・保存数・品質問題・エラー等）を表現する dataclass を実装。
  - マーケットカレンダー管理モジュールを追加（kabusys.data.calendar_management）。
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day 等の営業日判定ユーティリティを提供。
    - calendar_update_job により J-Quants API から差分取得して market_calendar テーブルへ冪等的に保存する処理を実装。
    - DB にデータがない場合は曜日ベースのフォールバック（平日を営業日）を採用。
    - 最大探索日数やバックフィル日数など安全対策を実装。
  - ETL / pipeline 周りのユーティリティ（テーブル存在チェック、最大日付取得等）を追加。
- AI（LLM）関連
  - ニュース NLP スコアリング（kabusys.ai.news_nlp）
    - raw_news と news_symbols を集約して銘柄ごとのニュースを作成し、OpenAI（gpt-4o-mini、JSON mode）で銘柄ごとのセンチメントを取得して ai_scores テーブルへ書き込む。
    - バッチ処理（最大 20 銘柄）、1 銘柄あたりの最大記事数・文字数トリム、レスポンスバリデーション、スコアのクリップ（±1.0）、エクスポネンシャルバックオフによるリトライ等を実装。
    - API キー注入（引数または環境変数 OPENAI_API_KEY）。未設定時は ValueError を送出。
    - テスト容易性のため _call_openai_api を patch で差し替えられる設計。
  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）とニュースの LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定、market_regime テーブルへ冪等書き込み。
    - マクロニュース抽出、OpenAI 呼び出し（gpt-4o-mini、JSON mode）、リトライ・エラーフォールバック（API 失敗時は macro_sentiment=0.0）等を実装。
    - ルックアヘッドバイアス対策（内部で datetime.today()/date.today() を参照しない、DB クエリは target_date 未満を参照）。
- リサーチ（研究）モジュール
  - ファクター計算（kabusys.research.factor_research）
    - Momentum（1M/3M/6M リターン、200 日 MA 乖離）、Value（PER/ROE）、Volatility（20 日 ATR）等を DuckDB 上で計算する関数を実装。
    - prices_daily / raw_financials のみを参照し、本番注文 API にアクセスしない設計。
  - 特徴量探索（kabusys.research.feature_exploration）
    - 将来リターン calc_forward_returns、IC（Information Coefficient）計算 calc_ic、rank、統計サマリー factor_summary 等を提供。
    - 外部ライブラリに依存せず標準ライブラリのみで実装。
  - 研究ユーティリティの再エクスポート（kabusys.research.__init__）。
- その他設計上の注意点（挙動）
  - データベース書き込みは冪等性を意識（DELETE→INSERT、BEGIN/COMMIT/ROLLBACK の利用）。
  - DuckDB の executemany に関する互換性考慮（空リストの扱いに注意）。
  - LLM レスポンスの頑健なパース（JSON だけでなく前後ノイズからの復元）とバリデーションを実装。
  - API 失敗時のフェイルセーフ動作（例：LLM 失敗時はスコアを 0.0 で継続、処理全体を止めない）。

### Changed
- （初回リリースにつき該当なし）

### Fixed
- （初回リリースにつき該当なし）

### Security
- 外部 API キー（OpenAI 等）を必須にする設計。鍵は環境変数で注入し、.env 読み込みによりローカルでの管理が可能。
- 自動 .env 読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD により無効化可能（テストや CI 用）。

### Notes / Migration
- 必要な環境変数
  - OPENAI_API_KEY（LLM 呼び出し、news_nlp / regime_detector / その他で使用）
  - JQUANTS_REFRESH_TOKEN（J-Quants API 用）
  - KABU_API_PASSWORD / KABU_API_BASE_URL（kabuステーション API）
  - SLACK_BOT_TOKEN / SLACK_CHANNEL_ID（モニタリング通知用）
  - DUCKDB_PATH / SQLITE_PATH（デフォルトは data/ 以下）
- DB スキーマ（期待されるテーブル）
  - prices_daily, raw_news, news_symbols, ai_scores, market_regime, market_calendar, raw_financials など。各モジュールはこれらのテーブル構造を前提に動作。
- ルックアヘッドバイアス対策により、日付処理はすべて明示的な target_date を受け取る形。自動で「今日」を参照する関数はないため、外部ジョブから target_date を指定して利用してください。
- テストしやすい設計
  - LLM 呼び出し箇所は内部関数を patch してモックできるよう設計されています（例: kabusys.ai.news_nlp._call_openai_api の差し替え）。

---

（初回リリースのため Breaking Changes や Deprecated はありません）