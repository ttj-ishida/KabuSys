# CHANGELOG

すべての変更は Keep a Changelog の形式に従って記載しています。  
以下の変更履歴は、提供いただいたコードベースの内容から推測して作成した初期リリースの要約です（コメント・実装内容に基づく推測を含みます）。

全般
- 初版リリース: 0.1.0（2026-03-28）
- パッケージ名: kabusys
- 内部的に DuckDB をデータプラットフォームのストレージとして想定
- 設計方針として「ルックアヘッドバイアス回避（datetime.today()/date.today() を直接参照しない）」「DB 書き込みは冪等性を意識」「外部 API 呼び出しはフェイルセーフ」が徹底されている

## [0.1.0] - 2026-03-28

### 追加 (Added)
- パッケージ基礎
  - kabusys パッケージ初期化（__version__ = 0.1.0）。公開モジュール: data, strategy, execution, monitoring。
- 環境設定管理 (kabusys.config)
  - .env 自動読み込み機能を実装（プロジェクトルートは .git または pyproject.toml を探索して判定）。
  - .env/.env.local の読み込み順序を実装（OS 環境変数を保護しつつ .env.local が上書き可能）。
  - .env ファイルパーサ実装：export KEY=val 形式、シングル/ダブルクォート対応、バックスラッシュエスケープ、インラインコメント処理等に対応。
  - 環境変数アクセスのための Settings クラスを公開（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, DUCKDB_PATH, SQLITE_PATH, KABUSYS_ENV, LOG_LEVEL など）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化フラグ実装。
  - KABUSYS_ENV と LOG_LEVEL の値検証を実装（許可値セットを定義）。
- ニュース NLP（kabusys.ai.news_nlp）
  - score_news(conn, target_date, api_key=None) を実装。raw_news、news_symbols から記事を集約して OpenAI（gpt-4o-mini）で銘柄別センチメントを算出し ai_scores テーブルへ保存する。
  - ニュース集計ウィンドウ calc_news_window(target_date) 実装（JST 基準で前日 15:00 ～ 当日 08:30 を UTC に変換）。
  - バッチ処理実装: 1 API コール最大 20 銘柄（_BATCH_SIZE=20）、1銘柄あたり最大記事数 10、最大文字数 3000 でトリム。
  - API 呼び出しは JSON Mode（response_format）で実施。レスポンスを厳密にバリデーションして有効スコアのみ登録。
  - 再試行・指数バックオフ: RateLimitError, APIConnectionError, APITimeoutError, 5xx 系 APIError に対してリトライを実装（最大リトライ回数・待機秒数の定義あり）。
  - エラー耐性: API／パース失敗時は個別チャンクや銘柄をスキップして処理を継続（フェイルセーフ）。部分成功時は既存スコアを保護するため対象コードのみ DELETE → INSERT。
  - テスト容易性のため _call_openai_api を内部関数として定義しパッチ可能にしている。
- レジーム検知（kabusys.ai.regime_detector）
  - score_regime(conn, target_date, api_key=None) を実装。ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して市場レジーム（bull/neutral/bear）を判定・保存する。
  - ma200_ratio 計算（_calc_ma200_ratio）: target_date 未満のデータのみ使用してルックアヘッドを防止。データ不足時は中立（1.0）を返すフォールバック。
  - マクロニュース取得（_fetch_macro_news）: タイトルにマクロキーワードでフィルタ（キーワードリストを内包）。
  - LLM 呼び出し（_score_macro）: gpt-4o-mini を使用、JSON レスポンスをパース、失敗時は macro_sentiment = 0.0 にフォールバック。リトライ処理・5xx 判定ロジックあり。
  - レジームスコア合成ロジック: clip(0.7*(ma200_ratio-1)*10 + 0.3*macro_sentiment, -1, 1)、閾値により bull / bear / neutral を判定。
  - market_regime テーブルへの冪等書き込み（BEGIN / DELETE WHERE date = ? / INSERT / COMMIT）、失敗時は ROLLBACK を試行して例外を再送出。
- 研究用ファクター（kabusys.research）
  - factor_research モジュールを実装:
    - calc_momentum(conn, target_date): mom_1m, mom_3m, mom_6m, ma200_dev を計算。データ不足時は None を返す。
    - calc_volatility(conn, target_date): 20 日 ATR（atr_20）、atr_pct、avg_turnover、volume_ratio を計算。
    - calc_value(conn, target_date): raw_financials から最新財務を取得して PER, ROE を計算（EPS が 0/欠損のときは None）。
  - feature_exploration モジュールを実装:
    - calc_forward_returns(conn, target_date, horizons=None): 翌日/翌週/翌月などの将来リターンを一括取得するクエリを実装（ホライズンは整数かつ <= 252 制約を検査）。
    - calc_ic(factor_records, forward_records, factor_col, return_col): スピアマンのランク相関（IC）を計算（有効レコード 3 未満なら None）。
    - rank(values): 同順位は平均ランクにするランク関数を実装（丸めで ties を安定化）。
    - factor_summary(records, columns): count/mean/std/min/max/median を計算する統計サマリー機能を実装（None を除外）。
  - 研究モジュールは外部 API に依存せず、DuckDB の prices_daily / raw_financials を用いる設計。
- データ管理（kabusys.data）
  - calendar_management モジュール:
    - JPX カレンダー管理: market_calendar テーブルを使った営業日判定 is_trading_day, is_sq_day、翌営業日/前営業日取得 next_trading_day / prev_trading_day、期間内営業日取得 get_trading_days を提供。
    - DB にカレンダーデータがない/一部しかない場合は曜日（平日）ベースのフォールバックを採用。
    - 夜間バッチ calendar_update_job(conn, lookahead_days=90) を実装（J-Quants クライアントを通じて差分取得→保存、バックフィル・健全性チェックあり）。
  - pipeline / ETL:
    - ETLResult データクラスを公開（target_date、取得・保存件数、quality_issues、errors 等）。
    - _get_max_date、_table_exists などのユーティリティを実装。
    - ETL の設計方針（差分更新、バックフィル、品質チェックの継続処理、id_token 注入可能など）が設計ドキュメントに従って実装されていることを反映。

### 変更 (Changed)
- （初版のため変更履歴なし）

### 修正 (Fixed)
- （初版のため修正履歴なし）

### 削除 (Removed)
- （初版のため削除履歴なし）

### 非推奨 (Deprecated)
- （初版のためなし）

### セキュリティ (Security)
- OpenAI API キーの取り扱い: api_key 引数または環境変数 OPENAI_API_KEY を利用。未設定時は ValueError を送出して明示的に失敗させる実装（誤操作による API 呼び出しを防止）。
- .env 読み込み時に OS 環境変数は保護対象（protected set）として扱い、意図しない上書きを防止。

---

注意事項（実装に基づく挙動の補足）
- 多くの処理で「ルックアヘッドバイアス防止」と明言しており、target_date 未満／以前のデータのみを参照するように実装されている点に留意してください。
- AI 周り（news_nlp / regime_detector）の外部 API 呼び出しはリトライやパース失敗時のフォールバック（0.0 やスキップ）を設けており、運用時の堅牢化が図られています。
- データベース書き込みは基本的にトランザクションで囲み冪等性を保つ実装（DELETE → INSERT パターン）になっています。部分失敗時に既存データを誤って消さない配慮が見られます。
- logger による詳細ログ出力が多く、運用時のトラブルシュートを意識した実装です。

（必要であれば、各関数・モジュールごとのより詳細な変更点や使い方ドキュメント、または将来のリリースノート草案を作成します。）