# Changelog

すべての重要な変更は Keep a Changelog の形式に従って記載します。  
このプロジェクトはセマンティックバージョニングに従います: https://semver.org/

## [0.1.0] - 2026-03-17

最初の公開（初期実装）。以下の主要機能と設計方針を実装しています。

### 追加 (Added)
- パッケージ基礎
  - kabusys パッケージの初期実装。バージョンは 0.1.0。
  - public API 想定モジュール: data, strategy, execution, monitoring（__all__ に公開）。

- 環境変数・設定管理 (src/kabusys/config.py)
  - .env ファイルと OS 環境変数から設定を読み込む自動ローダーを実装（プロジェクトルートは .git または pyproject.toml を探索して特定）。
  - .env の行パーサ実装（コメント、export 形式、クォート内のエスケープ、安全なインラインコメント処理等に対応）。
  - .env 読み込みの優先順位: OS 環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化。
  - Settings クラスを公開（J-Quants、kabu API、Slack、DB パス、環境種別、ログレベル等のプロパティを提供）。
  - env / log_level の入力検証（許容値チェック）、is_live / is_paper / is_dev のユーティリティを提供。
  - 必須変数未設定時に ValueError を投げる _require ユーティリティ。

- J-Quants API クライアント (src/kabusys/data/jquants_client.py)
  - 基本的な HTTP リクエスト関数と JSON デコード処理を実装。
  - レート制御: 固定間隔スロットリングで 120 req/min（_RateLimiter）。
  - リトライロジック: 指数バックオフ、最大 3 回、408/429/5xx をリトライ対象。429 時は Retry-After ヘッダを優先。
  - 401 応答時にリフレッシュトークンで自動的に id_token を再取得して 1 回だけ再試行。
  - get_id_token() 実装（refresh token から idToken を取得）。
  - ページネーション対応のデータ取得関数: fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar。
  - DuckDB への冪等保存関数: save_daily_quotes, save_financial_statements, save_market_calendar（ON CONFLICT DO UPDATE を使用）。
  - 値変換ユーティリティ: _to_float, _to_int（空値や不正値を安全に None にするロジック）。

- ニュース収集モジュール (src/kabusys/data/news_collector.py)
  - RSS フィードの取得と記事保存フローを実装（デフォルトソース: Yahoo Finance のビジネス RSS）。
  - セキュリティ対策: defusedxml を使用した XML パース、SSRF 対策（ホストのプライベートアドレス拒否、リダイレクト先検査）、許可スキームは http/https のみ。
  - レスポンスサイズ制限（MAX_RESPONSE_BYTES = 10MB）と gzip 解凍後のサイズチェック（Gzip bomb 対策）。
  - URL 正規化: トラッキングパラメータ（utm_ など）削除、クエリソート、フラグメント除去。
  - 記事 ID は正規化 URL の SHA-256 先頭32文字で生成（冪等性確保）。
  - テキスト前処理（URL除去、空白正規化）。
  - RSS から抽出した記事を DuckDB に一括挿入する save_raw_news（チャンク化、トランザクション、INSERT ... RETURNING を使用して実際に挿入された ID を返す）。
  - 記事と銘柄コードの紐付け機能（extract_stock_codes / save_news_symbols / _save_news_symbols_bulk）。銘柄は 4 桁数字で抽出し、known_codes によるフィルタリングを想定。
  - run_news_collection: 複数ソースを順次処理し、ソース単位でエラーハンドリング（1 ソース失敗しても他を継続）。

- DuckDB スキーマ定義・初期化 (src/kabusys/data/schema.py)
  - DataPlatform に基づく 3 層（Raw / Processed / Feature）と実行層のテーブル定義を実装。
  - raw_prices, raw_financials, raw_news, raw_executions など Raw 層のテーブル。
  - prices_daily, market_calendar, fundamentals, news_articles, news_symbols など Processed 層。
  - features, ai_scores など Feature 層。
  - signals, signal_queue, orders, trades, positions, portfolio_performance など Execution 層。
  - 適切な制約（PRIMARY KEY, CHECK, FOREIGN KEY）とインデックス定義を含む。
  - init_schema(db_path) によるスキーマ作成（親ディレクトリ自動作成、冪等的に CREATE TABLE IF NOT EXISTS を実行）と get_connection() を提供。

- ETL パイプライン (src/kabusys/data/pipeline.py)
  - ETLResult dataclass による ETL 結果表現（品質問題、エラー一覧、各取得/保存件数など）。
  - DB の最終取得日取得ユーティリティ（get_last_price_date, get_last_financial_date, get_last_calendar_date）。
  - 非営業日調整ヘルパー (_adjust_to_trading_day)。
  - 差分更新方針に基づく run_prices_etl の骨組み（差分算出、バックフィル日数の仕様、jquants_client を使った取得と保存）。バックフィル・カレンダー先読み等の設計を反映。

### 改善 (Changed)
- API クライアント・ニュース収集ともに「冪等性」を重視した設計を採用（DB 保存は ON CONFLICT を使って上書きまたはスキップし、二重取得に耐性がある）。
- ネットワーク処理において堅牢なエラーハンドリングとログ出力を強化（リトライ、Retry-After、gzip/Content-Length チェック、XML パース失敗の安全フォールバック）。
- RSS・URL 処理でトラッキングパラメータ除去や URL 正規化を行い、記事重複やトラッキングによる差異を低減。

### セキュリティ (Security)
- RSS パーサに defusedxml を使用して XML インジェクション・XML bomb を緩和。
- SSRF 対策:
  - リダイレクト時にスキームとホストを検査するカスタムハンドラ（_SSRFBlockRedirectHandler）。
  - 初回 URL とリダイレクト後の最終 URL のホストがプライベート IP（ループバック / リンクローカル / マルチキャスト等）でないかチェック。
  - 許可スキームは http/https のみ。
- レスポンスの最大読み取りバイト数を制限してメモリ DoS を防止（MAX_RESPONSE_BYTES）。
- 外部への HTTP 要求で User-Agent を明示。

### 修正 (Fixed)
- （初版リリース）バグ修正履歴はなし（初期実装として機能を追加）。

### 既知の問題 (Known issues)
- run_prices_etl 関数の末尾（pipeline モジュール）が入力サンプルで途中で終端している（return 文が不完全）ように見えるため、実行時に構文エラーまたは期待した戻り値が得られない可能性がある。実際に運用する際はこの関数の完了処理（ETLResult への集約や正しいタプル戻り値）を確認・修正してください。
- strategy/execution/monitoring パッケージは __init__ のみ存在し、実装は未着手または別モジュールでの実装を予定。
- 単体テストや統合テストはこのスナップショット内に含まれていない。ネットワーク依存処理はモック化してテストを実装することを推奨。

---

今後の予定（提案）
- run_prices_etl の完成と完全な ETLResult の返却、品質チェックフロー（quality モジュールとの連携）を実装。
- strategy / execution 層の具体的なアルゴリズムと実取引連携（kabu API 発注実装）の追加。
- CI での自動テスト・静的解析・セキュリティスキャンの整備。
- ドキュメント（DataPlatform.md, API 使用例, .env.example など）の整備とサンプルワークフローの追加。