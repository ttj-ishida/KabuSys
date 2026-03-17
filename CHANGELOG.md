# Changelog

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。

## [Unreleased]

## [0.1.0] - 2026-03-17
初回リリース。日本株自動売買プラットフォームのコアライブラリを追加。

### Added
- パッケージ基盤
  - パッケージ識別子とバージョンを追加（kabusys.__version__ = "0.1.0"）。
  - パッケージの公開モジュールを __all__ に定義（data, strategy, execution, monitoring）。

- 設定管理（kabusys.config）
  - .env ファイルおよび環境変数から設定を自動ロードする仕組みを実装。
    - プロジェクトルートは __file__ を起点に .git または pyproject.toml を探索して特定（CWDに依存しない）。
    - 読み込み優先順位: OS環境変数 > .env.local > .env。
    - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - .env のパース機能を実装（export プレフィックス、クォート値、インラインコメント、バックスラッシュエスケープへ対応）。
  - Settings クラスを提供し、必要な設定項目をプロパティで露出（J-Quants トークン、kabu API パスワード、Slack トークン/チャンネル、DBパスなど）。
  - KABUSYS_ENV と LOG_LEVEL の検証ロジックを追加（許容値チェック）。
  - Path 型でのデフォルトデータベースパス取り扱い（expanduser 対応）。

- データ取得クライアント（kabusys.data.jquants_client）
  - J-Quants API クライアントを実装。
    - レート制限（120 req/min）を守る固定間隔スロットリング（_RateLimiter）。
    - 再試行ロジック（指数バックオフ、最大3回）。HTTP 408/429/5xx はリトライ対象。
    - 401 を受信した場合の自動トークンリフレッシュを1回まで行い再試行。
    - ページネーション対応（pagination_key を利用して全ページ取得）。
    - 取得時刻（fetched_at）を UTC ISO 形式で記録し、Look-ahead Bias を抑制。
  - データ保存関数（DuckDB 用）
    - save_daily_quotes, save_financial_statements, save_market_calendar を実装。ON CONFLICT DO UPDATE により冪等保存。
    - 型変換ユーティリティ _to_float/_to_int を提供（不正値・空値は None に変換）。

- ニュース収集（kabusys.data.news_collector）
  - RSS フィードから記事を収集し raw_news テーブルへ保存する機能を実装。
    - デフォルトソース（例: Yahoo Finance のビジネスRSS）を定義。
    - XML パースに defusedxml を使用して XML Attack を軽減。
    - SSRF 対策: URL スキーム検証、ホストがプライベートアドレスかのチェック、リダイレクト時の検査（独自の HTTPRedirectHandler）を実装。
    - レスポンスサイズ上限（MAX_RESPONSE_BYTES = 10MB）を導入し、gzip 解凍後もサイズ検査を実施（Gzip bomb 対策）。
    - URL 正規化: トラッキングパラメータ（utm_* など）を削除し、クエリをソートしてハッシュ化。記事IDは正規化URLのSHA-256（先頭32文字）で生成して冪等性を担保。
    - テキスト前処理（URL除去、空白正規化）。
    - DuckDB への保存はトランザクションでチャンクごとに行い、INSERT ... RETURNING を利用して実際に挿入された記事IDを返す。
    - 銘柄コード抽出（4桁数字パターン）と news_symbols への一括保存機能を提供。
    - run_news_collection により複数ソースを順次処理し、ソース単位でエラーハンドリングを行う。

- スキーマ管理（kabusys.data.schema）
  - DuckDB のスキーマを定義（Raw/Processed/Feature/Execution 層）。
    - raw_prices, raw_financials, raw_news, raw_executions などの Raw 層。
    - prices_daily, market_calendar, fundamentals, news_articles, news_symbols などの Processed 層。
    - features, ai_scores などの Feature 層。
    - signals, signal_queue, orders, trades, positions, portfolio_performance などの Execution 層。
  - 適切な CHECK 制約・PRIMARY KEY・FOREIGN KEY を付与し、データ整合性を確保。
  - よく使うクエリ向けのインデックスを定義。
  - init_schema(db_path) によりディレクトリ作成・DDL 実行・インデックス作成を行う（冪等）。
  - get_connection(db_path) を提供（スキーマ初期化は行わない）。

- ETL パイプライン（kabusys.data.pipeline）
  - ETL の設計枠組みと一部実装を追加。
    - ETLResult dataclass により処理結果・品質問題・エラーを集約。
    - 差分更新のヘルパー（テーブル最終日取得、営業日調整）を実装。
    - run_prices_etl を実装（差分算出・backfill 機能・J-Quants からの取得と保存の呼び出し）。取得開始日は最終取得日から backfill_days を引いた日付がデフォルト。
    - get_last_price_date / get_last_financial_date / get_last_calendar_date を実装。
    - 市場カレンダーの先読みパラメータやバックフィル日数の定数化。

### Security
- ニュース収集で以下のセキュリティ対策を導入:
  - defusedxml を採用して XML 関連の脆弱性を緩和。
  - SSRF 対策（スキーム検証、プライベートIP検査、リダイレクト検査）。
  - レスポンスサイズ制限と Gzip 解凍後のサイズチェック（DoS／Zip bomb 対策）。
  - URL 正規化によりトラッキングパラメータを除去。

### Changed
- （初版のため該当なし）

### Fixed
- （初版のため該当なし）

### Deprecated
- （初版のため該当なし）

### Removed
- （初版のため該当なし）

### Breaking Changes
- （初版のため該当なし）

---

Notes / 今後の留意点（コードからの推測）
- strategy/ と execution/ の __init__ モジュールはプレースホルダであり、実際の戦略ロジック・発注ロジックは未実装。拡張予定。
- pipeline.run_prices_etl の末尾が未完のように見える箇所があるため（戻り値の整形や他の ETL ジョブとの統合）、実運用前に追加実装・レビューが必要。
- quality チェックモジュール（kabusys.data.quality）は参照されているが今回のコードスニペットには実装が含まれていない。品質判定ロジックの実装・設定が必要。
- テスト用フック（news_collector._urlopen のモックなど）が組み込まれているため、ユニットテストの作成が容易。

この CHANGELOG はソースコードの内容から推測して作成しています。実際のリリースノート作成時は実際の変更差分・コミットログに基づく追記・修正を行ってください。