# Changelog

すべての重要な変更点をこのファイルに記録します。フォーマットは「Keep a Changelog」に準拠します。

次の規約に従っています：
- すべての公開リリースはバージョン名と日付を持ちます
- 主要な変更はカテゴリ別（Added, Changed, Fixed, Security など）に分けて記載します

## [Unreleased]

> （現時点ではリリース済みバージョン 0.1.0 のみを含みます。今後の変更はここに記載してください）

---

## [0.1.0] - 2026-03-17

初回公開リリース。日本株自動売買プラットフォームの基礎機能を実装しました。以下はコードベースから推測される主な追加点・設計上の特徴です。

### Added
- パッケージ基盤
  - kabusys パッケージを追加。バージョンは 0.1.0。
  - __all__ に data, strategy, execution, monitoring を公開。

- 設定/環境変数管理（kabusys.config）
  - .env / .env.local からの自動読み込み（プロジェクトルートは .git または pyproject.toml を探索して決定）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化オプション。
  - .env パーサ実装（export KEY=val 形式、クォート/エスケープ、インラインコメント対応）。
  - 環境設定ラッパ Settings を提供。J-Quants / kabuステーション / Slack / DB パス等のプロパティを定義。
  - env / log_level の値検証（開発・ペーパー・ライブ環境の列挙、ログレベルの許容値チェック）。
  - デフォルト値（KABUSYS_API_BASE_URL、DUCKDB_PATH など）を設定。

- J-Quants API クライアント（kabusys.data.jquants_client）
  - データ取得 API 実装: 日次株価（fetch_daily_quotes）、財務（fetch_financial_statements）、マーケットカレンダー（fetch_market_calendar）。
  - 認証ヘルパ get_id_token とモジュールレベルのトークンキャッシュ／自動リフレッシュを実装。
  - API レート制御: 固定間隔スロットリングで 120 req/min を順守する RateLimiter。
  - 再試行ロジック: 指数バックオフ（base=2.0）、最大 3 回、408/429/5xx に対するリトライ、429 の Retry-After を尊重。
  - HTTP 401 を検出した場合はトークンを1回リフレッシュしてリトライする仕組み。
  - DuckDB への保存関数（save_daily_quotes, save_financial_statements, save_market_calendar）を実装。ON CONFLICT を用いた冪等保存（INSERT ... ON CONFLICT DO UPDATE）。
  - 取得時刻(fetched_at) を UTC ISO 形式で記録し、Look-ahead Bias のトレースを可能にする。
  - 値変換ユーティリティ (_to_float, _to_int) を実装し、型安全な変換を保証。

- ニュース収集（kabusys.data.news_collector）
  - RSS フィード収集機能（fetch_rss）と統合ジョブ（run_news_collection）を実装。デフォルトで Yahoo Finance のビジネス RSS を使用。
  - セキュリティ対策:
    - defusedxml を使用して XML Bomb 等に対処。
    - SSRF 対策: URL スキーム検証（http/https のみ）、ホストがプライベート/ループバック/リンクローカルでないことをチェック、リダイレクト時にも検証するカスタムリダイレクトハンドラを導入。
    - レスポンスサイズ上限（MAX_RESPONSE_BYTES = 10MB）と gzip 解凍後サイズ検査により DoS を軽減。
  - 記事ID生成: URL 正規化（トラッキングパラメータ除去・クエリソート等）後に SHA-256 を取り、先頭32文字を採用（冪等性保証）。
  - テキスト前処理: URL 削除、空白正規化等（preprocess_text）。
  - DB 保存:
    - raw_news のバルク INSERT（チャンク）、INSERT ... RETURNING を使って実際に挿入された新規記事IDを返却。
    - news_symbols（記事と銘柄の紐付け）を一括 INSERT して RETURNING で挿入数を取得。
    - トランザクションまとめてのコミット／ロールバック処理。
  - 銘柄抽出: 正規表現による 4 桁数値の抽出（日本株の銘柄コード想定）と既知銘柄セットによるフィルタ処理（extract_stock_codes）。

- DuckDB スキーマ定義（kabusys.data.schema）
  - Raw / Processed / Feature / Execution の各レイヤーに対応したテーブル定義を実装（raw_prices, raw_financials, raw_news, prices_daily, market_calendar, fundamentals, features, ai_scores, signals, signal_queue, orders, trades, positions, portfolio_performance 等）。
  - 制約（PRIMARY KEY / CHECK / FOREIGN KEY）と推奨インデックスを定義。
  - init_schema(db_path) でディレクトリ自動作成と全テーブル＋インデックス作成（冪等）。:memory: をサポート。
  - get_connection(db_path) で既存DBへの接続を提供。

- ETL パイプライン（kabusys.data.pipeline）
  - ETLResult dataclass により ETL 実行結果・品質問題・エラーを構造化。
  - 差分更新ヘルパ: DB 上の最終取得日を取得するユーティリティ（get_last_price_date, get_last_financial_date, get_last_calendar_date）。
  - 営業日調整ヘルパ (_adjust_to_trading_day) を提供し、非営業日は直近の営業日に調整。
  - run_prices_etl の実装（差分取得ロジック、バックフィル日数指定、取得→保存の流れ）。品質チェックモジュール (quality) との連携を想定。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- RSS 周りで defusedxml を使用し XML インジェクション/爆弾対策を実施。
- 外部 URL に対しスキーム・ホスト検証を厳格化（http/https のみ許可、プライベートIP/ループバックの排除、リダイレクト時の再検査）。
- レスポンスサイズ制限と Gzip 解凍後のサイズチェックによりメモリ DoS を軽減。
- .env 読み込み時の warn 出力でファイル読み込み失敗を明示。

### Performance / Reliability
- J-Quants API のレートリミッタとリトライ（指数バックオフ）により API 呼び出しの安定性を向上。
- DuckDB への保存はバルク/チャンク単位で行い、トランザクションをまとめることでオーバーヘッドを低減。
- save_* 系関数は ON CONFLICT を使った冪等実装のため、再実行耐性がある。

### Notes / Implementation details
- 環境変数の必須キーは Settings._require により未設定時に ValueError を送出するため、実稼働前に .env を適切に用意する必要があります。
- J-Quants トークンの自動リフレッシュは 401 応答時に1回のみ実行されるよう設計されているため、無限再帰を防止します。
- news_collector は既知銘柄セット（known_codes）を与えることで銘柄抽出→news_symbols への紐付けを行います。既知銘柄が未指定の場合は紐付けはスキップされます。
- DuckDB スキーマは外部キー依存を考慮した順序で作成されます。

---

今後のリリースでの望ましい改善点（例）
- strategy / execution / monitoring モジュールの具体実装（現状はパッケージエントリのみ）。
- quality モジュールの実装と ETL 結果に応じた運用自動化（アラート/ロールバック）。
- テストカバレッジの拡充（ネットワーク・DB のモックを含む）。
- NewsCollector のソース登録インターフェースやフェッチスケジュール化の追加。

（この CHANGELOG はソースコードの内容から推測して作成しています。開発履歴・コミットメッセージ等と合わせて運用することを推奨します。）