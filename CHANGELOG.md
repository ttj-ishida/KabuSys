# CHANGELOG

すべての重要な変更点をこのファイルで管理します。  
フォーマットは「Keep a Changelog」に準拠します。

最新: Unreleased
[Full changelog](./CHANGELOG.md)

## [Unreleased]
- 現時点の開発中の変更点を記載します。

---

## [0.1.0] - 2026-03-29

最初の公開（初期実装）。以下はコードベースから推測してまとめた主要な追加・設計上の決定・修正点です。

### 追加
- パッケージ基盤
  - kabusys パッケージを導入。公開 API として data, research, ai, execution, monitoring 等を __all__ で定義。
  - バージョン番号を `0.1.0` として管理（src/kabusys/__init__.py）。

- 環境設定 (kabusys.config)
  - Settings クラスを実装し、環境変数から設定値を取得するプロパティを提供。
  - 自動 .env ロード機能を追加（プロジェクトルートを .git / pyproject.toml で検出）。.env, .env.local の読み込み順序を実装し、OS 環境変数を保護する仕組みを導入。
  - .env パーサーは export 形式やクォート・エスケープ・インラインコメントに対応。
  - 環境変数の必須チェック(_require) と enum 的な値検証（KABUSYS_ENV, LOG_LEVEL）を実装。
  - Slack / J-Quants / kabu API 等の設定プロパティを提供（例: JQUANTS_REFRESH_TOKEN, SLACK_BOT_TOKEN, KABU_API_PASSWORD 等）。
  - 自動ロード無効化フラグ（KABUSYS_DISABLE_AUTO_ENV_LOAD）に対応。

- AI モジュール (kabusys.ai)
  - ニュース NLP スコアリング（news_nlp.score_news）
    - ニュース集約ウィンドウ計算 (calc_news_window) を実装（JST ベース → UTC naive datetime 変換）。
    - raw_news / news_symbols から銘柄ごとに記事を集約、テキスト長・記事数でトリム。
    - OpenAI（gpt-4o-mini）へのバッチ送信（1 回あたり最大 20 銘柄）と JSON Mode を使用した応答パース。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフのリトライ。
    - レスポンスの厳密なバリデーション（results 配列・code/score 等）とスコアの ±1.0 クリップ。
    - 成功した銘柄のみ ai_scores テーブルへ冪等的に置換（DELETE → INSERT）して部分失敗を保護。
    - Unit test 用に _call_openai_api を差し替え可能に設計。

  - 市場レジーム判定（regime_detector.score_regime）
    - ETF 1321 の 200 日移動平均乖離（比率）とマクロニュースの LLM センチメントを重み合成して日次レジーム（bull/neutral/bear）を算出。
    - マクロキーワードで raw_news をフィルタし、OpenAI を呼んで macro_sentiment を取得（記事なしでは LLM 呼び出しを行わない）。
    - 計算結果を market_regime テーブルへ冪等的に書き込み（BEGIN / DELETE / INSERT / COMMIT）。
    - API キーは引数経由 or 環境変数 OPENAI_API_KEY で注入可能。
    - LLM 呼び出しの失敗時は macro_sentiment=0.0 にフォールバック（フェイルセーフ）。

- Data モジュール
  - カレンダー管理（data.calendar_management）
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day を実装。
    - market_calendar テーブルが無い場合は曜日ベースでフォールバック（週末を非営業日扱い）。
    - DB 登録がある場合は DB 値優先、未登録日は曜日フォールバックで一貫性を担保。
    - next/prev の探索安全策として最大探索日数制限を導入（_MAX_SEARCH_DAYS）。
    - JPX カレンダー夜間更新ジョブ calendar_update_job を実装（J-Quants API 経由・バックフィル・健全性チェックを含む）。
  - ETL / パイプライン（data.pipeline / data.etl）
    - ETLResult データクラスを実装して ETL 実行結果・品質問題・エラーを構造化。
    - 差分取得ロジックを想定したユーティリティ（最大日付取得、テーブル存在チェック等）を実装。
    - jquants_client 経由の保存処理と quality チェック呼び出しを想定（設計ドキュメント準拠）。
    - DuckDB 互換性を考慮した実装（executemany 空リストの扱い等）。

- Research 系（kabusys.research）
  - factor_research: calc_momentum / calc_volatility / calc_value を実装（prices_daily / raw_financials を参照）。
    - Momentum: 1M/3M/6M リターン、200 日 MA 乖離。
    - Volatility: 20 日 ATR, 相対 ATR, 平均売買代金, 出来高比率。
    - Value: PER, ROE（最新の raw_financials を参照）。
  - feature_exploration: calc_forward_returns / calc_ic / factor_summary / rank を実装。
    - 売買リターン・IC（Spearman）・統計サマリーなどの分析ユーティリティを提供。
  - data.stats から zscore_normalize を re-export。

### 変更（設計上の重要な決定）
- ルックアヘッドバイアス対策
  - datetime.today() / date.today() をスコア/ETL 本体のロジックで参照しない方針（target_date を明示的に受け取る設計）。
  - prices_daily クエリは target_date 未満 / 指定範囲のみ参照することで未来データ参照を防止。

- OpenAI 呼び出し
  - JSON Mode を利用し厳格なレスポンス期待（JSON 抽出ロジックは冗長対応も実装している）。
  - 呼び出し関数をモジュール間で共有せず各モジュール独立で _call_openai_api を実装（モジュール結合低減、テスト容易化）。

- データベース操作
  - DB への書き込みは冪等性を重視（DELETE + INSERT, ON CONFLICT 等の想定）。
  - トランザクション内での例外発生時は ROLLBACK を試行し、それ自体の失敗は警告ログで記録して上位に例外を伝播。

- エラー処理方針
  - LLM / 外部 API のエラーはフェイルセーフ（多くのケースでスコアを 0.0 にフォールバック、例外を無闇に投げない）。
  - クリティカルな DB 書き込み失敗等は例外として上位へ伝播させる（呼び出し元での取り扱いを前提）。

### 修正 / 堅牢化
- .env 読込:
  - ファイル読み込み失敗時に警告発行して処理継続（例外で停止しない）。
  - 上書き制御（override/protected）を実装し OS 環境変数を保護。

- OpenAI レスポンス処理:
  - レスポンス JSON のパース失敗時に補正（文字列から最外の { ... } を抽出）してロバストに処理。
  - レスポンス中の score を数値に正規化し、非数値や非有限値は除外。

- リトライ挙動:
  - 429 / ネットワーク / タイムアウト / 5xx に対するエクスポネンシャルバックオフの汎用実装。
  - リトライ上限超過時は警告ログを出力してフェイルセーフの挙動にフォールバック。

- DuckDB 互換性:
  - executemany に空リストを渡せない制約に対応するチェックを追加。
  - DuckDB が返す日付型の安全な date 変換ユーティリティを実装。

### 既知の制約 / 注意点
- OpenAI API キーは外部から注入可能だが、運用上は環境変数 OPENAI_API_KEY を想定。
- gpt-4o-mini / JSON Mode に依存するため、将来の OpenAI SDK/API 変更があればラッパー修正が必要。
- raw_financials の利用により一部指標（EPS/ROE）が未設定・ゼロの場合は None を返す設計。
- カレンダー更新は J-Quants クライアント (jquants_client) に依存。外部 API の可用性により calendar_update_job の結果が変動する。
- DuckDB を用いた SQL 実行で一部の SQL 構文（例: ANY(?) のバインド等）に互換性の差があるため回避実装を行っている。

---

開発・運用に関する注記やバグフィックスは今後の Unreleased に追記します。必要があればこのCHANGELOGをベースにリリースノートをさらに詳細化します。