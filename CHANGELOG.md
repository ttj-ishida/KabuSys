# Changelog

すべての変更は Keep a Changelog の仕様に準拠して記述しています。  
安定リリースと互換性のためにセマンティックバージョニングを採用しています。

なお本ログは提供されたソースコードから推測して作成した初期リリース記録です。

## [Unreleased]
- 次回リリースに向けた未確定の変更はここに記載します。

## [0.1.0] - 2026-03-17
初回公開リリース。日本株自動売買システム「KabuSys」のコア機能群を実装。

### Added
- パッケージ基礎
  - パッケージ初期化（kabusys.__init__）とバージョン定義を追加（0.1.0）。
  - 空のサブパッケージプレースホルダを追加（kabusys.execution, kabusys.strategy, kabusys.data）。

- 設定・環境変数管理（kabusys.config）
  - .env ファイルおよび環境変数から設定を読み込む Settings クラスを実装。
  - 自動 .env ロード機構（プロジェクトルートを .git / pyproject.toml で検出）。
  - 読み込み順序: OS 環境変数 > .env.local > .env（.env.local は上書き許可）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動読み込みを無効化可能（テスト向け）。
  - .env パースの堅牢化（export プレフィックス、クォート内のエスケープ、インラインコメント処理など）。
  - 必須環境変数チェック（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID）。
  - 管理用設定メソッド: duckdb/sqlite のデフォルトパス、KABUSYS_ENV のバリデーション（development/paper_trading/live）、LOG_LEVEL の検証。

- J-Quants API クライアント（kabusys.data.jquants_client）
  - 日足（OHLCV）、四半期財務データ、JPXマーケットカレンダーを取得する fetch_* 関数を実装（ページネーション対応）。
  - HTTP レート制限対応（固定スロットリング、120 req/min、_RateLimiter）。
  - リトライロジック（指数バックオフ、最大 3 回、408/429/5xx をリトライ対象）。
  - 401 応答時にリフレッシュトークンから自動で id_token を再取得して 1 回リトライ。
  - id_token のモジュールレベルキャッシュ（ページネーション間で共有）。
  - DuckDB への保存関数（save_daily_quotes, save_financial_statements, save_market_calendar）を実装。ON CONFLICT DO UPDATE により冪等性を確保。
  - データ型変換ユーティリティ（_to_float, _to_int）を実装し、空文字列や不正値を安全に扱う。
  - 取得時刻（fetched_at）を UTC ISO8601 で記録し、Look-ahead Bias 回避のため「いつデータを取得したか」をトレース可能に。

- ニュース収集モジュール（kabusys.data.news_collector）
  - RSS フィードからニュース記事を取得・正規化して DuckDB に保存する一連処理を実装。
  - デフォルト RSS ソースに Yahoo Finance のビジネスカテゴリを設定。
  - セキュリティ対策:
    - defusedxml を用いた XML パースで XML Bomb 等を防止。
    - SSRF 対策: リダイレクト時や最終 URL のスキーム検証、ホストがプライベートアドレスかどうかのチェック（IP/DNS 解決を含む）。
    - 許可スキームは http/https のみ。
    - レスポンス受信上限（MAX_RESPONSE_BYTES = 10MB）を実装しメモリ DoS を軽減。gzip 圧縮にも対応し、解凍後サイズチェックを実施。
  - URL 正規化処理（トラッキングパラメータ除去・クエリソート・フラグメント削除）とそれに基づく記事ID生成（SHA-256 の先頭32文字）で冪等性を確保。
  - テキスト前処理（URL除去、空白正規化）。
  - extract_stock_codes による本文/タイトルからの銘柄コード抽出（4桁数字、known_codes によるフィルタ）。
  - DB 保存:
    - raw_news テーブルへのチャンク化された INSERT ... ON CONFLICT DO NOTHING RETURNING id を使用し、実際に挿入された ID の一覧を返す。
    - news_symbols（記事と銘柄の紐付け）を一括保存する内部ユーティリティ（重複を除去してチャンクINSERT、RETURNING で正確な挿入数を取得）。
    - すべてのDB保存はトランザクションで実行し、失敗時はロールバック。

- スキーマ管理（kabusys.data.schema）
  - DuckDB 用スキーマを定義（Raw / Processed / Feature / Execution の層）。
  - テーブル定義: raw_prices, raw_financials, raw_news, raw_executions, prices_daily, market_calendar, fundamentals, news_articles, news_symbols, features, ai_scores, signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance など。
  - 適用可能な整合性制約（PRIMARY KEY, FOREIGN KEY, CHECK）を明記。
  - よく使うクエリパターン向けのインデックスを作成（code/date や status 等）。
  - init_schema(db_path) 実装: 必要に応じて親ディレクトリ作成 → 全 DDL とインデックスを実行して接続を返す（冪等）。
  - get_connection(db_path): 既存 DB への接続を返す（初期化は行わない）。

- ETL パイプライン（kabusys.data.pipeline）
  - 差分更新/差分取得に基づく ETL フローを実装する基礎（差分取得の自動算出、backfill_days による後出し修正吸収、品質チェックとの連携ポイント）。
  - ETLResult データクラス: 実行結果、検出した品質問題、エラー一覧を集約。品質問題はチェック名・重大度・メッセージへ変換可能。
  - 市場カレンダーの「営業日補正」ヘルパーを実装（非営業日なら直近営業日に調整）。
  - テーブル存在確認や最終日取得ユーティリティ（get_last_price_date 等）を実装。
  - run_prices_etl: 差分に基づく日足取得と保存の処理を実装（デフォルト backfill_days=3、最小取得開始日 _MIN_DATA_DATE = 2017-01-01、取得範囲チェック等）。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- news_collector において SSRF 対策、defusedxml 導入、受信サイズ制限、gzip 解凍後のサイズチェックを実装。
- .env パースや自動読み込みロジックにおいて OS 環境変数を保護するための protected セットを導入（.env.local による上書きでも OS 環境変数は保持）。

### Notes / Requirements
- 必要パッケージ（例）:
  - duckdb
  - defusedxml
- Python の型表記（X | Y / typing）を使用しているため Python 3.10 以上を想定。

### Known issues / TODO
- run_prices_etl の戻り値に関する潜在的なバグ:
  - ソースコード末尾で return 文が `return len(records),` のように末尾の saved 値を返していない（片方のみのタプルになっている、あるいはコピーミスの可能性）。期待される戻り値は (fetched_count, saved_count) のはずです。次回リリースで修正予定。
- 一部モジュール（kabusys.execution, kabusys.strategy）の実装はプレースホルダであり、注文発行ロジックや戦略の実装はまだ行われていません。
- デフォルト RSS ソースは1つのみ（yahoo_finance）。ソース管理や追加は設定で行う想定。

### Migration / Upgrade notes
- 既存のプロジェクトに導入する場合は次の環境変数が必須:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
- DuckDB の初期化には init_schema() を用いてスキーマを作成してください。既存 DB を使う場合は get_connection() を利用してスキーマ初期化を行わないようにできます。
- 自動 .env ロードが不要なテスト環境等では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

フルな変更履歴や追加の修正・機能要望があれば、該当する差分や目的を教えてください。CHANGELOG の追加・修正を作成します。