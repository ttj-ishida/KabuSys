# Changelog

すべての重要な変更は "Keep a Changelog" の慣例に従って記載しています。  
このファイルは主にコードベースの初期リリース（0.1.0）で追加された機能群・公開 API・設計上の注意点をまとめたものです。記載内容はソースコードから推測して作成しています。

全般
- DuckDB を主要な分析データストアとして利用する設計になっています（多くの関数は DuckDB の接続オブジェクトを引数に取ります）。
- OpenAI（gpt-4o-mini）を使用したニュース NLP / マクロセンチメント判定機能を含みます（JSON Mode を利用）。
- ルックアヘッドバイアス防止のため、内部処理は datetime.today() / date.today() を直接参照しない方針で実装されています（target_date を明示的に渡して処理）。
- 自動環境変数読み込み機能を提供（.env / .env.local）。ただし自動読み込みは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。

Unreleased
- (なし)

0.1.0 - 2026-03-31
------------------

Added
- パッケージ初期公開
  - パッケージ名: kabusys
  - バージョン: 0.1.0
  - __all__ に ["data", "strategy", "execution", "monitoring"] を定義（公開構成の雛形）。

- 環境設定管理 (kabusys.config)
  - .env/.env.local をプロジェクトルート（.git または pyproject.toml を基準）から自動読み込みするユーティリティを実装。
  - .env パーサ実装（コメント、export の扱い、シングル/ダブルクォート内のバックスラッシュエスケープ等に対応）。
  - 自動読み込みの挙動:
    - 優先順位: OS 環境変数 > .env.local > .env
    - .env.local は override=True（ただし既存の OS 環境変数は保護）
    - 自動ロード無効化: KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  - Settings クラスを実装し、アプリケーション設定値をプロパティ経由で取得可能:
    - 必須: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - 任意/デフォルトあり: KABU_API_BASE_URL（デフォ: http://localhost:18080/kabusapi）、DUCKDB_PATH（デフォ: data/kabusys.duckdb）、SQLITE_PATH（デフォ: data/monitoring.db）
    - 環境: KABUSYS_ENV（development / paper_trading / live のいずれか）検証
    - LOG_LEVEL の検証（DEBUG/INFO/WARNING/ERROR/CRITICAL）
    - is_live / is_paper / is_dev ヘルパー

- AI 関連 (kabusys.ai)
  - ニュース NLP（kabusys.ai.news_nlp）
    - 関数: score_news(conn, target_date, api_key=None)
      - raw_news と news_symbols から前日 15:00 JST ～ 当日 08:30 JST の記事を集約して銘柄ごとのセンチメントスコアを生成。
      - OpenAI をバッチ呼び出し（最大 _BATCH_SIZE=20 銘柄/リクエスト）。
      - 1銘柄あたりの最大記事数や文字数制限（_MAX_ARTICLES_PER_STOCK=10, _MAX_CHARS_PER_STOCK=3000）。
      - レスポンスバリデーション（JSON 抽出・results 構造・コード照合・数値チェック）。
      - スコアは ±1.0 にクリップして ai_scores テーブルへ置換(DELETE→INSERT)。
      - 失敗時は影響を最小化するフェイルセーフ実装（API失敗時は当該チャンクをスキップし、処理継続）。
      - タイムウィンドウ計算関数: calc_news_window(target_date) を公開。
      - リトライ / バックオフ戦略（429・ネットワーク断・タイムアウト・5xx をリトライ対象）を実装。
  - レジーム判定（kabusys.ai.regime_detector）
    - 関数: score_regime(conn, target_date, api_key=None)
      - ETF 1321（=日経225連動型）の 200 日移動平均乖離（重み70%）と、マクロニュースの LLM センチメント（重み30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定し market_regime テーブルへ冪等書き込み。
      - ma200 比率計算: _calc_ma200_ratio（データ不足時は中立(1.0)として扱い WARNING ログ）。
      - マクロニュース抽出: raw_news からマクロキーワードでフィルタ（最大 _MAX_MACRO_ARTICLES=20）。
      - LLM 呼び出しは独立実装（news_nlp とは別の内部 _call_openai_api を使用）。
      - API 失敗やパース失敗時は macro_sentiment=0.0 としてフォールバック（例外を投げない）。
      - リトライ / バックオフ戦略を実装。

- Research（定量解析） (kabusys.research)
  - factor_research モジュール
    - calc_momentum(conn, target_date): 1M/3M/6M リターン、200日MA乖離(ma200_dev) を計算。
    - calc_volatility(conn, target_date): 20日 ATR、相対 ATR、20日平均売買代金、出来高比率等を計算。
    - calc_value(conn, target_date): raw_financials から最新財務情報を取得して PER / ROE を計算（EPS が 0/欠損のときは None）。
    - 設計上、prices_daily / raw_financials テーブルのみ参照し、本番発注API等へはアクセスしない。
  - feature_exploration モジュール
    - calc_forward_returns(conn, target_date, horizons=None): 指定ホライズンの将来リターンを計算（デフォルト horizons=[1,5,21]）。
    - calc_ic(factor_records, forward_records, factor_col, return_col): Spearman のランク相関による IC 計算（有効レコード < 3 の場合は None）。
    - rank(values): 同順位は平均ランクで扱うランク化ユーティリティ。
    - factor_summary(records, columns): count/mean/std/min/max/median を計算する統計要約。

- Data / ETL / カレンダー (kabusys.data)
  - calendar_management
    - is_trading_day(conn, d), is_sq_day(conn, d), next_trading_day(conn, d), prev_trading_day(conn, d), get_trading_days(conn, start, end) を実装。
    - market_calendar が存在しない場合は曜日ベースでフォールバック（土日は非営業日扱い）。
    - calendar_update_job(conn, lookahead_days=90): J-Quants から差分取得して market_calendar を更新（バックフィルや健全性チェックあり）。
  - pipeline / ETL
    - ETLResult データクラスを実装（kabusys.data.pipeline.ETLResult）。data.etl で再エクスポート。
    - 差分更新・backfill の方針、品質チェック（quality モジュール参照）の結果を ETLResult で集約する設計。
    - 内部ユーティリティ: テーブル存在確認や最大日付取得等を実装。

- 例外処理とロギング
  - 多くの処理で失敗時に例外を上位に伝播させる前に適切なロールバックやログ出力が行われる（DB トランザクションの BEGIN/DELETE/INSERT/COMMIT / ROLLBACK を明示）。
  - OpenAI 呼び出し周りで発生しうる各種例外（RateLimitError, APIConnectionError, APITimeoutError, APIError 等）を分類してリトライ制御を行う。

Changed
- (初回リリースのため該当なし)

Deprecated
- (該当なし)

Removed
- (該当なし)

Fixed
- (初回リリースのため該当なし)

Security
- OpenAI API キーは引数で注入可能（api_key）か環境変数 OPENAI_API_KEY を利用する仕様。未設定時は ValueError を送出して利用者に明示。

Notes / 使用上の注意（コードから推測）
- すべての公開関数は DuckDB の接続オブジェクトを引数に取る設計です。呼び出し側は適切にテーブル（prices_daily, raw_news, news_symbols, ai_scores, market_regime, raw_financials, market_calendar など）を用意する必要があります。
- AI モジュールは外部 API に依存するため、API キーの管理・レート制限に注意してください。モジュールは失敗時にフェイルセーフで継続するよう設計されていますが、部分的なスキップが発生します。
- calc_news_window / score_news / score_regime 等はルックアヘッドバイアスを避けるため target_date を明示して呼び出す必要があります（内部で現在時刻参照を行わない）。
- .env パーサは複雑なケース（クォート内のエスケープ、inline コメントの扱い等）に対応していますが、特殊なフォーマットの .env を利用する場合は挙動確認を推奨します。
- Settings はいくつかの環境変数値を検証します（KABUSYS_ENV, LOG_LEVEL）。無効な値は ValueError を引き起こします。

今後の想定（ドキュメント的補足）
- strategy / execution / monitoring などのモジュール群は __all__ に列挙されていますが、今回提供されたコードでは一部名前空間の雛形が示されているに留まる可能性があります。実運用に向けては実際の発注ロジックや監視処理の実装が必要です。

---

もし CHANGELOG を別の粒度（モジュール別、コミット別）や英語版が必要であればお知らせください。