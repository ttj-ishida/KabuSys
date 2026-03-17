# CHANGELOG

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠しています。

全般: このリポジトリは日本株自動売買基盤（KabuSys）の初期実装を含みます。主要コンポーネントは設定管理、J‑Quants データ取得クライアント、RSS ニュース収集、DuckDB スキーマ定義、ETL パイプラインのユーティリティ群です。

## [Unreleased]

### Added
- プロジェクト初期実装（0.1.0 に相当する機能群）。
  - パッケージエントリポイントを追加（kabusys.__init__）。公開サブパッケージ: data, strategy, execution, monitoring。
- 環境設定管理モジュール（kabusys.config）
  - .env / .env.local をプロジェクトルートから自動読み込みする機能を追加（プロジェクトルート検出は .git または pyproject.toml を基準）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能。
  - .env ローダーは export 構文、クォート／エスケープ、インラインコメント処理に対応。
  - override/protected オプションにより OS 環境変数を保護して .env.local で上書き可能。
  - Settings クラスを提供: J-Quants、kabu ステーション、Slack、DBパス（DuckDB/SQLite）等の設定をプロパティ経由で取得。値の検証（KABUSYS_ENV, LOG_LEVEL）を実装。
- J-Quants API クライアント（kabusys.data.jquants_client）
  - 日足（OHLCV）、財務（四半期 BS/PL）、JPX マーケットカレンダーの取得関数を実装（fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar）。
  - API レート制御: 固定間隔スロットリングで 120 req/min を遵守する RateLimiter 実装。
  - リトライ／バックオフロジック: 指数バックオフ、最大 3 回、408/429/5xx に対するリトライ。429 の場合は Retry-After ヘッダを優先。
  - 401 受信時の自動トークンリフレッシュ処理（1回まで）およびモジュールレベルの ID トークンキャッシュ。
  - ページネーション対応：pagination_key を追跡して全件取得。
  - DuckDB への保存関数（save_daily_quotes, save_financial_statements, save_market_calendar）を実装。冪等性を担保するため ON CONFLICT DO UPDATE を使用し fetched_at（UTC）を記録。
  - 型変換ユーティリティ（_to_float, _to_int）で安全に数値変換。
- ニュース収集モジュール（kabusys.data.news_collector）
  - デフォルト RSS ソース（Yahoo Finance）を定義し、RSS 取得・パース・前処理・DB 保存のワークフローを実装。
  - セキュリティ対策:
    - defusedxml を使用した XML パース（XML Bomb 等の防御）。
    - URL スキーム検証（http/https のみ）とプライベートアドレス検出（SSRF 対策）。リダイレクト時にも検査を行うカスタム RedirectHandler を実装。
    - レスポンスサイズ上限（MAX_RESPONSE_BYTES = 10MB）および gzip 解凍後の再検証（Gzip bomb 対策）。
  - URL 正規化・トラッキングパラメータ除去（utm_* 等）を行い、記事ID を正規化 URL の SHA‑256（先頭32文字）で生成（重複排除に利用）。
  - テキスト前処理（URL除去・空白正規化）実装。
  - DB 保存:
    - save_raw_news: INSERT ... ON CONFLICT DO NOTHING + RETURNING id を利用して新規挿入された記事IDリストを返す。チャンク化と単一トランザクションでの処理を実装。
    - save_news_symbols / _save_news_symbols_bulk: 記事と銘柄コードの紐付けをチャンク化して一括挿入（ON CONFLICT DO NOTHING + RETURNING）し、挿入数を正確に返す。
  - 銘柄コード抽出機能（extract_stock_codes）: 4桁数字パターンを候補とし、known_codes フィルタで有効なコードのみ返す（重複除去）。
  - run_news_collection: 複数ソースを巡回して収集・保存・銘柄紐付けを実行。各ソースごとに独立したエラーハンドリング。
- DuckDB スキーマ定義・初期化（kabusys.data.schema）
  - Raw / Processed / Feature / Execution の多層スキーマを定義し init_schema() で全 DDL とインデックスを冪等的に作成する機能を提供。
  - 主なテーブル: raw_prices, raw_financials, raw_news, market_calendar, prices_daily, fundamentals, news_articles, news_symbols, features, ai_scores, signals, signal_queue, orders, trades, positions, portfolio_performance 等。
  - 各テーブルにチェック制約・主キー・外部キーを定義し、検索を高速化するためのインデックスを用意。
  - get_connection(db_path) を提供。
- ETL パイプラインユーティリティ（kabusys.data.pipeline）
  - ETLResult dataclass を追加（取得数・保存数・品質問題・エラー等を格納。品質問題は簡易シリアライズ可能）。
  - スキーマ・テーブル存在確認や最大日付取得ヘルパー（_table_exists, _get_max_date, get_last_price_date, get_last_financial_date, get_last_calendar_date）を実装。
  - 市場カレンダーに基づく営業日調整ユーティリティ（_adjust_to_trading_day）。
  - run_prices_etl を実装（差分取得ロジック、backfill_days による後出し修正吸収、J-Quants の fetch/save 呼び出し）。その他: 定数（_MIN_DATA_DATE, _CALENDAR_LOOKAHEAD_DAYS, _DEFAULT_BACKFILL_DAYS）と品質チェック連携の設計（quality モジュールを参照）。
  - ETL 設計上、品質チェックは致命的エラーを検出しても ETL を最後まで続行し、呼び出し元で判断できるように設計。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Removed
- （初回リリースのため該当なし）

### Security
- defusedxml の導入、SSRF 対策（スキーム検証・プライベートアドレスチェック・リダイレクト時の検査）、レスポンスサイズ制限、gzip 解凍後サイズチェックなど、外部入力を取り扱う箇所で複数の防御策を実装。

## [0.1.0] - 2026-03-17

初期公開リリース（上記 Unreleased と同じ内容）。主要な機能は以下の通りです。

- 環境設定と Settings
- J-Quants データ取得／保存（rate limit / retry / token リフレッシュ / pagination）
- RSS ニュース収集（安全性・前処理・重複排除・DB 保存）
- DuckDB スキーマと初期化 API
- ETL 補助ユーティリティ（差分算出・バックフィル・ETLResult）
- 各種ユーティリティ（URL 正規化・数値変換等）

## Known issues / Notes（既知の問題・開発者向け注意事項）
- pipeline.run_prices_etl の実装末尾に戻り値に関する明らかな不備（コード末尾で
  `return len(records), `
  のようにカンマで終わっており、期待されるタプル (fetched, saved) を返していない箇所があります。実行時に戻り値エラーが発生する可能性があるため修正が必要です（正しくは `return len(records), saved` のはずです）。
- quality モジュールは参照されていますが、本差分に完全な品質チェック実装が含まれていない可能性があります。ETL の品質判定ロジックを統合する際に追加実装が必要です。
- ニュース収集の既知コードセット（known_codes）は外部から与える設計のため、適切な銘柄一覧の供給が必須です。
- デフォルトで .env/.env.local を自動読み込みしますが、テスト環境や CI で環境変数の衝突が発生する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を利用してください。

## 貢献・開発のヒント
- ユニットテスト: ネットワーク依存箇所（_urlopen, urllib.request.urlopen, jquants API 呼び出し）はモック可能に設計されているため、外部依存をモックして単体テストを作成してください。
- セキュリティ: news_collector の SSRF 判定は DNS 解決失敗時に「安全側（非プライベート）」として通過させます。より厳格なポリシーが必要な場合は挙動を変更してください。
- パフォーマンス: save_raw_news / _save_news_symbols_bulk はチャンク挿入でパフォーマンスを考慮していますが、大規模データ取り込み時はチャンクサイズやトランザクション戦略の調整を検討してください。

---

この CHANGELOG はコードの現状から推測して作成しています。追加の変更点や修正が行われた場合は、該当バージョンのセクションに追記してください。