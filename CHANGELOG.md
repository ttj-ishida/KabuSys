# Changelog

すべての注目すべき変更を記録します。本ファイルは Keep a Changelog の形式に準拠しています。

次のポリシーに従います:
- 互換性のある API に対する後方互換性のある変更は "Changed"、
- 新機能は "Added"、
- バグ修正は "Fixed"、
- セキュリティ関連の強化は "Security" セクションに記載します。

未リリースの変更は "Unreleased" に記載します。

## [Unreleased]

- なし

## [0.1.0] - 2026-03-17

### Added
- パッケージ初期リリース: KabuSys - 日本株自動売買システムの基礎実装を追加。
  - src/kabusys/__init__.py にてバージョンと公開モジュールを定義 (バージョン: 0.1.0)。
- 環境設定管理モジュールを追加 (src/kabusys/config.py)。
  - .env / .env.local の自動読み込み機能（プロジェクトルート検出: .git または pyproject.toml ベース）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化。
  - export KEY=val 形式やクォート・インラインコメント等に対応した .env 行パーサを実装。
  - 必須環境変数取得のヘルパ（_require）と Settings クラスを提供（J-Quants / kabu / Slack / DB パス / 環境/ログレベル等のプロパティ）。
  - KABUSYS_ENV と LOG_LEVEL の入力検証（許容値チェック）。
- J-Quants API クライアントを追加 (src/kabusys/data/jquants_client.py)。
  - 日次株価 (OHLCV)、財務諸表（四半期 BS/PL）、JPX 市場カレンダーの取得関数を実装（fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar）。
  - レート制限（120 req/min）を守る固定間隔スロットリング実装（_RateLimiter）。
  - 冪等保存用の DuckDB への保存関数を実装（save_daily_quotes, save_financial_statements, save_market_calendar） — ON CONFLICT による上書き処理を実装。
  - リトライロジック（指数バックオフ、最大試行回数、特定ステータスでの再試行）と 401 受信時のトークン自動リフレッシュを実装。
  - レスポンスの JSON デコードや数値変換ユーティリティ（_to_float, _to_int）を実装。
- ニュース収集モジュールを追加 (src/kabusys/data/news_collector.py)。
  - RSS フィード取得、XML パース、記事前処理、DuckDB への冪等保存フローを実装（fetch_rss, save_raw_news, save_news_symbols, run_news_collection）。
  - URL 正規化とトラッキングパラメータ除去（_normalize_url, _make_article_id）、記事 ID は正規化 URL の SHA-256 の先頭 32 文字を採用。
  - コンテンツの前処理（URL 除去、空白正規化）と pubDate の安全なパースを実装。
  - bulk チャンク挿入（INSERT ... RETURNING）とトランザクション単位での安全な保存（ロールバック機構）を実装。
  - 銘柄コード抽出ユーティリティ（4桁数字パターン）と既知銘柄セットによるフィルタリング（extract_stock_codes）。
- DuckDB スキーマ定義・初期化モジュールを追加 (src/kabusys/data/schema.py)。
  - Raw / Processed / Feature / Execution の多層スキーマを定義（raw_prices, raw_financials, raw_news, market_calendar, prices_daily, features, ai_scores, signal_queue, orders, trades, positions, portfolio_performance 等）。
  - 各テーブルの制約（PRIMARY KEY、CHECK、外部キー）と頻出クエリを想定したインデックスを定義。
  - init_schema(db_path) によりディレクトリ作成 → テーブル/インデックス作成を行う初期化 API を提供。get_connection() も提供。
- ETL パイプラインモジュールを追加（部分実装） (src/kabusys/data/pipeline.py)。
  - 差分取得（最終取得日から backfill を考慮）・保存（jquants_client の save_* を利用）・品質チェック呼び出しの骨子を実装。
  - ETL 実行結果を表す ETLResult データクラスを導入（品質問題とエラーの集約、辞書化ユーティリティ）。
  - 市場カレンダーを考慮した営業日調整、テーブル存在確認、最終日取得ユーティリティ（get_last_price_date 等）を実装。
  - run_prices_etl の差分ロジック（一部）を実装（date_from の自動算出・backfill の考慮、fetch→save の流れ）。
- テスト容易性・運用面の配慮:
  - モジュールレベルの ID トークンキャッシュと、テストで置き換え可能な _urlopen フック（news_collector）を用意。
  - RSS 取得時の受信バイト上限（10MB）・gzip 解凍後のサイズチェックを実装してメモリ DoS を軽減。
  - リダイレクト時にスキームとホストを事前検証するハンドラを導入し、SSRF リスクを低減。

### Changed
- 初回リリースのため該当なし。

### Fixed
- 初回リリースのため該当なし。

### Security
- ニュース収集時のセキュリティ対策を実装:
  - defusedxml を用いた XML パースで XML Bomb 等から保護。
  - RSS リダイレクト検査・スキーム検証・プライベートアドレス検査（_is_private_host）により SSRF を抑止。
  - レスポンスサイズ上限と gzip 解凍後のサイズ検査によるメモリ消費制限。
- J-Quants API 呼び出し時に認証トークン自動リフレッシュを実装し、不正な 401 状態からの安全な回復を行う。ただしトークン更新処理中の無限再帰を防ぐ設計になっている。

### Notes / Migration
- データベースを使用する前に必ず init_schema() を呼んで DuckDB スキーマを初期化してください。
  - 例: from kabusys.data.schema import init_schema; conn = init_schema(settings.duckdb_path)
- .env 自動ロードはデフォルトで有効です。CI/テスト等で自動ロードを抑止する場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- pipeline/quality モジュールは参照されているが品質チェックの実装は別途（あるいは未実装の可能性あり）。品質チェックのルールや QualityIssue 型は pipeline 側で定義されています。

### Known limitations
- ETL パイプラインは骨子が実装されていますが、すべてのジョブ（例: 財務・カレンダーのフル差分処理や品質チェックの詳細）は今後の実装/拡張を想定しています。
- 一部の外部モジュール（quality 等）の実体はこの差分からは確認できません。これらは別モジュールとして提供される前提です。

---

Copyright © プロジェクト KabuSys

(注: 上記の変更履歴は提供されたコードベースから推測して作成しています。実際の履歴・日付やリリース方針に合わせて適宜修正してください。)