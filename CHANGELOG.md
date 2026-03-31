# Changelog

すべての注目すべき変更はここに記録します。  
フォーマットは Keep a Changelog に準拠します。  

なお、本リポジトリは初期リリース（0.1.0）としてコードベースを提供しています。

## [Unreleased]
（なし）

## [0.1.0] - 2026-03-31
Initial release

### Added
- パッケージ基盤
  - pakage 初期化: kabusys パッケージのエントリポイントを追加（バージョン: 0.1.0）。
  - __all__ に main サブパッケージ（data, strategy, execution, monitoring）を公開。

- 環境設定 / 設定管理 (kabusys.config)
  - .env / .env.local 自動ロード機能を実装
    - プロジェクトルート検出は .git または pyproject.toml を起点に行うため CWD に依存しない。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
    - .env パースは export プレフィックス対応、引用符中のエスケープ、インラインコメント処理等に対応。
    - override/protected 機構により OS 環境変数の意図しない上書きを防止。
  - Settings クラスを提供（settings インスタンス経由でアクセス）
    - 必須環境変数検証: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID。
    - デフォルト値付き設定: KABU_API_BASE_URL, DUCKDB_PATH, SQLITE_PATH, PID_FILE_PATH。
    - 監視閾値: CPU/MEM/DISK の閾値を環境変数で設定可能（デフォルト値を提供）。
    - 環境・ログレベルの検証（KABUSYS_ENV, LOG_LEVEL の許容値チェック）。
    - ヘルパー bool プロパティ: is_live/is_paper/is_dev。

- AI（自然言語処理）機能 (kabusys.ai)
  - ニュースセンチメント（銘柄単位）: score_news
    - raw_news / news_symbols を集約して銘柄ごとのニュースを OpenAI（gpt-4o-mini）へ送信し、銘柄ごとの ai_score を ai_scores テーブルへ書き込む。
    - タイムウィンドウ定義（前日 15:00 JST ～ 当日 08:30 JST）を calc_news_window で提供（UTC に変換して DB と比較）。
    - 1銘柄あたりの上限: 記事数と文字数でトリム（_MAX_ARTICLES_PER_STOCK, _MAX_CHARS_PER_STOCK）。
    - バッチ送信（最大 _BATCH_SIZE=20 銘柄）・JSON Mode を用いた厳密なレスポンスバリデーション。
    - リトライ/バックオフ戦略：429, ネットワーク断, タイムアウト, 5xx を対象に指数バックオフ。その他エラーはスキップして継続（フェイルセーフ）。
    - レスポンス検証に失敗した銘柄は無視し、取得済み銘柄のみを DELETE → INSERT で置換することで部分失敗時の既存データ保護を実現。
    - テスト容易性のため _call_openai_api をモック差し替えできる設計。
  - 市場レジーム判定: score_regime (regime_detector)
    - ETF 1321（日経225 連動ETF）の 200 日移動平均乖離（重み 70%）とマクロニュース由来の LLM センチメント（重み 30%）を合成して market_regime テーブルへ冪等的に書き込み。
    - マクロニュースは raw_news からマクロキーワードで抽出（上限 _MAX_MACRO_ARTICLES）。
    - LLM 呼び出しは gpt-4o-mini、JSON レスポンスをパースして macro_sentiment を取得。API 失敗時は macro_sentiment=0.0 でフォールバック。
    - 設計方針としてルックアヘッドバイアス回避（datetime.today()/date.today() を直接参照せず、target_date を明示的に受け取る）を徹底。
    - 書き込みは BEGIN/DELETE/INSERT/COMMIT の形で冪等性を確保。失敗時は ROLLBACK を試行。

- Research（ファクター計算・特徴量解析） (kabusys.research)
  - ファクター計算モジュール（factor_research）
    - calc_momentum: mom_1m / mom_3m / mom_6m / ma200_dev を prices_daily から計算。データ不足時は None を返す。
    - calc_volatility: ATR(20), atr_pct, avg_turnover, volume_ratio を計算（data windowing と NULL 安全な true_range 処理）。
    - calc_value: raw_financials と prices_daily を組み合わせて PER / ROE を算出。report_date <= target_date の最新財務レコードを使用。
    - すべて DuckDB に対する SQL を主体とする実装で外部 API への依存なし。
  - 特徴量探索モジュール（feature_exploration）
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）で将来リターンを計算。horizons のバリデーション付き。
    - calc_ic: ファクター値と将来リターンの Spearman ランク相関（IC）を計算。データ不足時は None を返す。
    - rank: 同順位は平均ランクで扱うランク化ユーティリティ（丸めを導入して ties の検出安定化）。
    - factor_summary: count/mean/std/min/max/median を算出する統計サマリー。
    - パッケージ初期化で公開: calc_momentum, calc_value, calc_volatility, zscore_normalize（kabusys.data.stats から）, calc_forward_returns, calc_ic, factor_summary, rank。

- Data（ETL / カレンダー管理） (kabusys.data)
  - calendar_management
    - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days を提供。
    - market_calendar テーブルが存在する場合は DB 値を優先、未登録日は曜日（平日）ベースでフォールバックする一貫性のあるロジック。
    - next/prev_trading_day は最大探索日数制限（_MAX_SEARCH_DAYS）を設けて無限ループ防止。
    - calendar_update_job: J-Quants クライアント経由で JPX カレンダーを差分取得し market_calendar を冪等に更新。バックフィルと健全性チェック（将来日付の異常検出）を実装。
  - ETL / pipeline
    - ETLResult dataclass を定義（対象日・取得件数・保存件数・品質問題・エラー列挙など）。
    - ETLResult に has_errors / has_quality_errors / to_dict を提供（品質問題は辞書化してログ等に使える）。
    - pipeline モジュールは差分取得、jquants_client を使った冪等保存、品質チェックを統合する設計（quality モジュールとの連携）。
    - etl モジュールは ETLResult を再エクスポートして外部から利用しやすくしている。
  - jquants_client / quality との明示的な結合点を確保（外部 API 呼び出しは抽象化）。

### Design / Reliability / Testing notes
- ルックアヘッドバイアス回避
  - AI モジュール、研究モジュールともに内部で datetime.today()/date.today() を直接参照せず、必ず target_date を引数として受け取る設計。
- フェイルセーフ挙動
  - OpenAI API 失敗時やデータ不足時は例外で全体を止めない（デフォルト値やスキップで継続）。
  - DB 書き込みは可能な限り冪等性を保つ（DELETE→INSERT 等）。
- テスト容易性
  - AI API 呼び出し箇所で _call_openai_api をモック可能にしてユニットテストを容易化。
- DuckDB の互換性配慮
  - executemany に空リストを渡さない等、DuckDB のバージョン依存性に配慮した実装。

### Removed
- （なし）

### Fixed
- （なし）

---

備考:
- 本 CHANGELOG はコードベースから推測して記載しています。実際の意図やドキュメントの正確な文章については、実装者による確認・補足を推奨します。