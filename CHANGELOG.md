# Changelog

すべての重要な変更点を記録します。本ファイルは「Keep a Changelog」仕様に準拠しています。  
フォーマット: バージョン（リリース日） → セクション（Added / Changed / Fixed / Security / Breaking Changes）

## [Unreleased]

## [0.1.0] - 2026-03-17
初回リリース。日本株自動売買プラットフォーム KabuSys のコアモジュールを実装。

### Added
- パッケージ初期化
  - src/kabusys/__init__.py にパッケージ名とバージョン（0.1.0）を追加。公開サブパッケージを __all__ で定義（data, strategy, execution, monitoring）。
- 設定・環境変数管理
  - src/kabusys/config.py:
    - .env ファイルまたは環境変数から設定を読み込む Settings クラスを実装。
    - プロジェクトルート自動検出（.git または pyproject.toml）による自動 .env 読み込みを実装。
    - .env パースロジックを堅牢化（export プレフィックス、シングル/ダブルクォート、インラインコメント、エスケープ処理に対応）。
    - 環境による挙動（development/paper_trading/live）やログレベル検証、各種必須環境変数取得ヘルパーを提供。
    - 自動ロードを無効化する KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート（テスト向け）。
- J-Quants API クライアント
  - src/kabusys/data/jquants_client.py:
    - J-Quants からの日足（OHLCV）、四半期財務データ、マーケットカレンダー取得関数（fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar）を実装（ページネーション対応）。
    - API 呼び出しユーティリティ _request を実装。レート制限（120 req/min）を守る固定間隔レートリミッタを導入。
    - リトライロジック（指数バックオフ、最大 3 回、対象: 408/429/5xx）を実装。429 の Retry-After を優先。
    - 401 受信時は自動でトークンをリフレッシュして 1 回リトライする仕組みを追加。
    - get_id_token による id token 取得（refresh token 経由）を実装。
    - DuckDB への保存関数（save_daily_quotes、save_financial_statements、save_market_calendar）を実装。ON CONFLICT DO UPDATE による冪等保存を保証し、fetched_at（UTC）で取得時刻を記録。
    - 型変換ユーティリティ（_to_float, _to_int）を実装し、不正値や空値を安全に扱う。
- ニュース収集モジュール
  - src/kabusys/data/news_collector.py:
    - RSS フィードからのニュース収集(fetch_rss)・前処理(preprocess_text)・記事ID生成(_make_article_id)を実装。
    - 記事 ID は URL 正規化（トラッキングパラメータ除去）後の SHA-256（先頭32文字）で生成し冪等性を確保。
    - defusedxml を使った XML パース、gzip 対応、最大レスポンスサイズ制限（MAX_RESPONSE_BYTES=10MB）など安全対策を実装。
    - SSRF 対策: URL スキーム検証、ホストのプライベートアドレス検出(_is_private_host)、リダイレクト時の検査ハンドラ(_SSRFBlockRedirectHandler) を導入。
    - raw_news テーブルへのバルク挿入（save_raw_news）をトランザクションで実装し、INSERT ... RETURNING で実際に挿入された記事IDを返す。チャンクサイズ制御あり。
    - news_symbols（記事と銘柄の紐付け）を一括保存する _save_news_symbols_bulk、単一 insert を行う save_news_symbols を実装。
    - テキストから銘柄コード（4桁）を抽出する extract_stock_codes と既知銘柄フィルタリング実装。
    - run_news_collection により複数ソースを扱う統合収集ジョブを提供。個別ソースの失敗は他を止めないフェイルオーバー設計。
- DuckDB スキーマ／初期化
  - src/kabusys/data/schema.py:
    - Raw / Processed / Feature / Execution の多層データモデルを定義する DDL を実装（raw_prices, raw_financials, raw_news, raw_executions, prices_daily, market_calendar, fundamentals, news_articles, news_symbols, features, ai_scores, signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance）。
    - 運用上想定されるインデックスを作成（頻出クエリを想定したインデックス一覧）。
    - init_schema(db_path) でディレクトリ作成～全テーブルの冪等作成を行い DuckDB 接続を返す。get_connection で既存 DB 接続を取得可能。
- ETL パイプライン
  - src/kabusys/data/pipeline.py:
    - 差分更新を行う ETL ジョブ群（get_last_price_date / get_last_financial_date / get_last_calendar_date / run_prices_etl 等）の骨組みを実装。
    - 差分更新ロジック: DB の最終取得日を基に自動で date_from を計算し、backfill_days により数日前から再取得して API の後出し修正を吸収する設計。
    - ETL 実行結果を格納する ETLResult dataclass を実装。品質チェック結果やエラーを集約するプロパティを提供。
    - 市場カレンダーが無い場合のフォールバックや、非営業日調整ヘルパー(_adjust_to_trading_day)を実装。
    - jquants_client の fetch/save を組み合わせ、フェッチ→保存→ログの基本フローを実装（ログ出力により監査可能）。

### Changed
- （初回リリースにつき該当なし）

### Fixed
- （初回リリースにつき該当なし）

### Security
- RSS パーサに defusedxml を採用して XML ベースの脆弱性（XML Bomb 等）に対処。
- HTTP(S) 以外のスキームやプライベート IP 宛先へのアクセスを拒否し、SSRF 対策を実装。
- .env 読み込みは OS 環境変数を保護する仕組み（protected set）を導入。
- 外部API呼び出しはタイムアウト・サイズ制限を設け、DoS やメモリ爆発を低減。

### Performance
- J-Quants API 呼び出しに対して固定間隔レートリミッタを導入（120 req/min を準拠）。
- ニュース保存・銘柄紐付けはチャンクバルク挿入を採用して DB オーバーヘッドを削減。
- ページネーション処理中で ID トークンをモジュールレベルでキャッシュし、無駄な認証リクエストを回避。

### Reliability / Operability
- API 呼び出しに対してリトライ（指数バックオフ）および 401 時の自動トークンリフレッシュを実装。
- DuckDB への書き込みは冪等（ON CONFLICT DO UPDATE / DO NOTHING）により重複を安全に扱う。
- ETL の結果を構造化（ETLResult）し、品質チェックの出力を含めて監査・運用判断を容易にする。
- 設定の自動読み込みはプロジェクトルートから行うため、CWD に依存しない安定した環境設定を実現。
- テスト容易性を考慮して、_urlopen の差し替え（モック）や id_token の注入が可能。

### Deprecated
- （初回リリースにつき該当なし）

### Removed
- （初回リリースにつき該当なし）

### Breaking Changes
- （初回リリースにつき該当なし）

---

補足:
- 本 CHANGELOG はコード内容から実装意図・設計方針を推測して作成しています。実際のリリースノートとして使用する場合は、リリース日・バージョン表記や細部の文言をプロジェクト方針に合わせて調整してください。