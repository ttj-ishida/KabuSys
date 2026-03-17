# Changelog

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。  

全般:
- バージョン番号はパッケージ内 src/kabusys/__init__.py の __version__ に従います。

## [Unreleased]

（今後の変更や未リリースの修正をここに記載します）

---

## [0.1.0] - 2026-03-17
初回リリース。日本株自動売買基盤のコア機能を実装・公開。

### Added
- パッケージ基盤
  - pakage メタ情報と公開 API: src/kabusys/__init__.py にて __version__ を設定、モジュール公開（data, strategy, execution, monitoring）。
  - strategy/execution パッケージ骨組みを追加（将来的な戦略・発注実装場所）。

- 設定管理（src/kabusys/config.py）
  - .env ファイルおよび環境変数から設定を自動読み込みする仕組みを実装。
    - プロジェクトルートを .git または pyproject.toml を基準に自動検出（CWD に依存しない）。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能（テスト向け）。
  - .env ファイルの柔軟なパース機能を実装（export プレフィックス対応、クォート内エスケープ、コメント処理）。
  - Settings クラスを提供し、J-Quants / kabu / Slack / DB パスなどの設定取得を整理。
    - 必須設定は _require() による明示的エラー（ValueError）。
    - KABUSYS_ENV と LOG_LEVEL の検証ロジックを追加（許容値チェック）。
    - パス系は pathlib.Path で返却（expanduser 対応）。
    - ヘルパープロパティ: is_live, is_paper, is_dev。

- J-Quants API クライアント（src/kabusys/data/jquants_client.py）
  - 基本機能:
    - 株価日足（OHLCV）、財務（四半期 BS/PL）、JPX マーケットカレンダーを取得する fetch_* 関数群を実装（ページネーション対応）。
    - get_id_token によるリフレッシュトークン → idToken の取得（POST）。
  - 信頼性 / レート制御:
    - 固定間隔スロットリングによるレート制限（120 req/min）を実装（_RateLimiter）。
    - リトライロジック（指数バックオフ、最大 3 回）。再試行対象: ネットワークエラー、HTTP 408/429/5xx。
    - 401 受信時はトークンを自動リフレッシュして1回のみリトライ（無限再帰防止）。
    - id_token のモジュールレベルキャッシュを導入（ページネーション間で共有）。
  - DuckDB 保存ユーティリティ:
    - save_daily_quotes / save_financial_statements / save_market_calendar を実装。いずれも冪等（INSERT ... ON CONFLICT DO UPDATE）で保存。
    - 型変換ユーティリティ (_to_float, _to_int) にて不正値や空値を安全に扱う。
    - fetched_at（UTC ISO8601）を記録して Look-ahead bias を防止。

- ニュース収集（src/kabusys/data/news_collector.py）
  - RSS フィードからのニュース取得と DuckDB への格納ワークフローを実装。
    - fetch_rss: RSS 取得 → XML パース → 記事リスト（NewsArticle 型）を返却。
    - save_raw_news: raw_news テーブルへチャンク INSERT（ON CONFLICT DO NOTHING）し、実際に挿入された記事IDリストを RETURNING で取得。
    - save_news_symbols / _save_news_symbols_bulk: 記事と銘柄コードの紐付け（news_symbols）を一括保存（ON CONFLICT DO NOTHING、トランザクション対応）。
    - run_news_collection: 複数フィードを処理して総括的に保存件数を返す。各ソースは独立してエラーハンドリング（1ソース失敗しても継続）。
  - セキュリティ・堅牢性対策:
    - defusedxml を用いて XML Bomb 等の攻撃を緩和。
    - SSRF 対策: URL スキーム検証（http/https のみ許可）、ホストがプライベート/ループバック/リンクローカルでないことを検査、リダイレクト時の検証を実装（カスタム RedirectHandler）。
    - レスポンスサイズ上限（MAX_RESPONSE_BYTES = 10MB）でメモリ DoS を防止。gzip 解凍後も検査。
    - User-Agent と Accept-Encoding ヘッダ制御。
  - データ整形:
    - URL 正規化（_normalize_url）でトラッキングパラメータ（utm_ など）を除去。
    - 記事IDは正規化 URL の SHA-256 先頭32文字を採用して冪等性を担保。
    - テキスト前処理（URL 除去・空白正規化）。
    - RFC2822 pubDate パース（タイムゾーンを UTC に正規化）。パース失敗時は現在時刻で代替。
  - 銘柄抽出:
    - テキスト中の 4 桁数字を候補とし、known_codes（有効銘柄コードセット）と照合して抽出（重複除去）。

- DuckDB スキーマ管理（src/kabusys/data/schema.py）
  - Raw / Processed / Feature / Execution 層に対応したテーブル DDL を定義。
    - raw_prices, raw_financials, raw_news, raw_executions など Raw Layer。
    - prices_daily, market_calendar, fundamentals, news_articles, news_symbols など Processed Layer。
    - features, ai_scores など Feature Layer。
    - signals, signal_queue, orders, trades, positions, portfolio_performance など Execution Layer。
  - 制約（PRIMARY KEY, CHECK, FOREIGN KEY）を丁寧に付与（データ整合性重視）。
  - 頻出クエリ用のインデックスを定義。
  - init_schema(db_path) によりファイル作成・テーブル作成を一括で行う初期化関数を提供（冪等）。
  - get_connection(db_path) で既存 DB へ接続（スキーマ初期化は行わない旨を明示）。

- ETL パイプライン（src/kabusys/data/pipeline.py）
  - 差分更新とバックフィルを扱う ETL の基礎を実装。
    - 最終取得日の自動検出（get_last_price_date / get_last_financial_date / get_last_calendar_date）。
    - run_prices_etl: 差分取得ロジック（date_from 自動算出、backfill_days による再取得）と保存処理の呼び出し（fetch -> save）。
    - ETLResult dataclass を導入し、取得件数・保存件数・品質チェック結果・エラー情報を集約。品質チェック結果は to_dict() でシリアライズ可能。
  - 設計指針:
    - デフォルトのバックフィルは 3 日。calendar は将来分を先読み（90 日）する想定。
    - 品質チェックは全件収集し、呼び出し元でのアクション判断を想定（Fail-Fast ではない）。

### Security
- ニュース収集における SSRF 対策（スキーム検証・プライベート IP 検査・リダイレクト時検査）。
- defusedxml を利用した安全な XML パース。
- .env 読み込みで OS 環境変数を保護する機能（protected set を使って上書き防止）。
- HTTP クライアント処理でタイムアウト / サイズチェック / gzip 検査を実装。

### Performance / Reliability
- J-Quants クライアント側でレートリミッティング（120 req/min）を実装し API 制限を遵守。
- 再試行（リトライ）と指数バックオフにより一時的な失敗に対処。
- DB への書き込みはチャンク化・トランザクション化してオーバーヘッドと部分失敗を制御。
- INSERT ... RETURNING を用い、実際に挿入された件数を正確に取得。

### Documentation / API
- 公開関数の主要な API:
  - config.settings（Settings オブジェクト）
  - jquants_client: get_id_token, fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar, save_daily_quotes, save_financial_statements, save_market_calendar
  - news_collector: fetch_rss, save_raw_news, save_news_symbols, run_news_collection
  - schema: init_schema, get_connection
  - data.pipeline: run_prices_etl, get_last_price_date, get_last_financial_date, get_last_calendar_date, ETLResult

### Known issues / Notes
- strategy と execution パッケージは現在モジュール骨組みのみで具体的な戦略ロジック・発注エンジンは未実装。
- pipeline.run_prices_etl の末尾付近に未完の戻り値処理がある（コードの断片によりこのリリースでは一部関数が未完の可能性あり）。テスト時は挙動確認が必要。
- 一部型ヒントや変換ロジックは現実の外部データの多様性に対して追加の例外処理が必要になる可能性がある（特に財務データのフォーマット差異など）。

---

セマンティックバージョニングの方針:
- この 0.1.0 は初回公開（初期実装）です。後続の機能追加は minor、破壊的変更は major の増分とします。

（以降のリリースでは本ファイルを更新してください）