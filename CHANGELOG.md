# Changelog

すべての変更は「Keep a Changelog」の形式に従い、重要な変更点をバージョンごとに日本語で記載しています。

<!--
参考:
- https://keepachangelog.com/ja/1.0.0/
-->

## [0.1.0] - 2026-03-29

初回リリース。日本株自動売買プラットフォームのコアライブラリを追加しました。主な追加点は以下の通りです。

### 追加 (Added)
- パッケージ初期化
  - pakage メタ情報: kabusys.__version__ = "0.1.0"
  - パッケージ外部公開モジュール一覧: __all__ = ["data", "strategy", "execution", "monitoring"]

- 環境設定・ロード機能 (`kabusys.config`)
  - Settings クラスを追加し、環境変数からアプリケーション設定を取得するプロパティを提供。
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等の必須チェック。
    - KABUSYS_ENV（development / paper_trading / live）の検証と is_live / is_paper / is_dev ヘルパー。
    - LOG_LEVEL の検証（DEBUG/INFO/WARNING/ERROR/CRITICAL）。
    - データベースパス設定: DUCKDB_PATH, SQLITE_PATH（Path オブジェクトで取得）。
  - .env 自動読み込み機能を実装（プロジェクトルート判定: .git または pyproject.toml を基準）。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
    - .env パーサ実装: export 形式、クォート内のエスケープ、インラインコメントの取り扱い等に対応。
    - 読み込み時の上書き制御（override）と OS 環境変数保護のサポート。

- ニュース NLP（センチメント） (`kabusys.ai.news_nlp`)
  - score_news(conn, target_date, api_key=None)
    - raw_news / news_symbols を集約して銘柄ごとにマージしたテキストを OpenAI（gpt-4o-mini）に送信してセンチメントを算出。
    - バッチ処理（_BATCH_SIZE=20）とチャンク単位での API 呼び出し。
    - トークン肥大化対策: 1銘柄あたりの記事数・文字数上限（_MAX_ARTICLES_PER_STOCK / _MAX_CHARS_PER_STOCK）。
    - レスポンスの厳格バリデーション（JSON 抽出、"results" 構造、コードの正規化、スコアの数値検証）。
    - スコアは ±1.0 にクリップし、ai_scores テーブルへ冪等的に（DELETE → INSERT）書き込み。
    - API の 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフリトライ実装（_MAX_RETRIES）。
    - API 呼び出し箇所はテストで差し替え可能（_call_openai_api を patch してモック可能）。
    - ルックアヘッドバイアスを避けるため datetime.today() を参照しない設計。対象ウィンドウ計算関数 calc_news_window を提供。

- 市場レジーム判定 (`kabusys.ai.regime_detector`)
  - score_regime(conn, target_date, api_key=None)
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して market_regime テーブルへ書き込み。
    - ma200_ratio 計算（対象日は排他 date < target_date、データ不足時は中立値 1.0 を使用）。
    - マクロキーワードで raw_news タイトルを抽出し、OpenAI（gpt-4o-mini）へ送信して macro_sentiment を取得（記事が無ければ LLM 呼び出しなしで 0.0）。
    - レジームスコアを clip(-1,1) で正規化し、閾値により "bull"/"neutral"/"bear" を判定。
    - DB 書き込みは BEGIN / DELETE / INSERT / COMMIT の冪等処理。失敗時は ROLLBACK を試行して例外を上位へ伝播。
    - API 呼び出し失敗時のフォールバックやリトライの実装、テスト容易性のための差し替えポイントあり。
    - OpenAI の API 呼び出しに関するエラー種別（RateLimitError, APIConnectionError, APITimeoutError, APIError）に応じた扱いを実装。

- 研究・ファクター計算 (`kabusys.research`)
  - ファクター計算モジュール
    - calc_momentum(conn, target_date): mom_1m / mom_3m / mom_6m / ma200_dev（200日移動平均乖離）を計算。
    - calc_volatility(conn, target_date): 20日 ATR / 相対 ATR / 20日平均売買代金 / 出来高比率を計算。
    - calc_value(conn, target_date): raw_financials から EPS/ROE を取得し PER / ROE を計算。
    - 設計は DuckDB の SQL と Python を組み合わせ、prices_daily / raw_financials のみ参照。実行は本番発注系に影響を与えない。
  - 特徴量探索モジュール
    - calc_forward_returns(conn, target_date, horizons=None): 複数ホライズンの将来リターンを取得（LEAD を利用した単一クエリ）。
    - calc_ic(factor_records, forward_records, factor_col, return_col): スピアマンのランク相関（IC）を計算。
    - rank(values): 平均ランクでの同順位処理（丸めで ties 検出の安定化）。
    - factor_summary(records, columns): count/mean/std/min/max/median を計算する統計サマリー。
  - 研究 API は pandas 等に依存せず、標準ライブラリ＋DuckDB で実装。

- データプラットフォーム（Data） (`kabusys.data`)
  - calendar_management
    - JPX カレンダー管理機能（market_calendar テーブル操作）を提供。
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day 等の営業日判定ヘルパーを実装。
    - カレンダー未取得時は曜日ベース（土日除外）でフォールバックする一貫した挙動。
    - calendar_update_job(conn, lookahead_days=_CALENDAR_LOOKAHEAD_DAYS): J-Quants API から差分取得 → market_calendar へ冪等保存（fetch / save は jquants_client を使用）。
    - バックフィル、健全性チェック、最大探索日数制限などの安全策を実装。
  - ETL / パイプライン
    - pipeline.ETLResult データクラスを公開（kabusys.data.etl で再エクスポート）。
    - ETLResult は取得件数・保存件数・品質問題（quality.QualityIssue）・エラー一覧を保持、has_errors/has_quality_errors/to_dict を提供。
    - pipeline モジュールは差分更新ロジック、バックフィル、品質チェック（quality モジュール）との連携を想定した設計。

- テストしやすさ / フェイルセーフ設計
  - OpenAI 呼び出し箇所に差し替えポイント（_call_openai_api）を残し unittest.mock.patch により簡単にモック可能。
  - LLM の失敗は例外でバーストさせずフォールバック値（macro_sentiment=0.0、スコア未取得はスキップ）で継続する方針を採用。
  - DB 書き込みは可能な限り部分失敗で既存データを消さない設計（ai_scores の個別 DELETE → INSERT、market_regime の日付単位置換）。

### 変更 (Changed)
- 初版につき変更履歴なし。

### 修正 (Fixed)
- 初版につき修正履歴なし。

### 非推奨 (Deprecated)
- 初版につき非推奨項目なし。

### 削除 (Removed)
- 初版につき削除履歴なし。

### セキュリティ (Security)
- 現時点で既知のセキュリティ修正はありません。
- 環境変数に API キー等を期待するため、運用上は .env の権限管理やシークレット管理の利用を推奨します。

---

補足:
- 多くのモジュールは DuckDB 接続（duckdb.DuckDBPyConnection）を受け取り SQL と組み合わせて動作する設計です。実行環境側で DuckDB ファイルパスや接続を用意して利用してください。
- OpenAI クライアントを利用する機能は api_key 引数を受け取り、テスト時に明示的に注入できるようになっています。環境変数 OPENAI_API_KEY もサポートしますが、未設定時は ValueError を送出します。