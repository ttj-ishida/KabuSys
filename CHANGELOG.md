# Changelog

すべての重要な変更をこのファイルに記録します。フォーマットは「Keep a Changelog」に準拠し、セマンティックバージョニングを採用します。

## [Unreleased]

## [0.1.0] - 2026-03-17
初回リリース。日本株自動売買システム「KabuSys」の基盤機能を実装しました。主に以下のモジュール・機能を導入しています。

### Added
- パッケージ基本情報
  - パッケージ名とバージョンを定義（kabusys.__version__ = "0.1.0"）。
  - パッケージのエクスポート対象を __all__ で定義（data, strategy, execution, monitoring）。

- 環境設定管理（kabusys.config）
  - .env/.env.local ファイルと OS 環境変数を統合して読み込む自動ローディング機能。
  - プロジェクトルート検出ロジック（.git または pyproject.toml を起点に探索）。
  - .env 行パーサ（export 形式、クォート内エスケープ、インラインコメント対応等）。
  - 自動ロードの無効化フラグ（KABUSYS_DISABLE_AUTO_ENV_LOAD）。
  - 必須環境変数取得ヘルパーと Settings クラス（J-Quants / kabuステーション / Slack / DB パス / 環境・ログレベル検証プロパティ）。
  - 環境名・ログレベルのバリデーション（許可値チェック）および is_live / is_paper / is_dev 判定ヘルパー。

- J-Quants API クライアント（kabusys.data.jquants_client）
  - 基本 API 呼び出しラッパー（_request）を実装：JSON デコード、タイムアウト、クエリパラメータ、POST ボディ対応。
  - レートリミッタ（_RateLimiter）を実装し、API レート制限（120 req/min）を固定間隔スロットリングで順守。
  - 再試行（リトライ）ロジック：指数バックオフ、最大 3 回、408/429/5xx を対象。429 の場合は Retry-After を尊重。
  - 401 Unauthorized の自動トークンリフレッシュを 1 回試行（キャッシュ付きの ID トークン管理）。
  - ページネーション対応のデータ取得関数：
    - fetch_daily_quotes（株価日足）
    - fetch_financial_statements（財務四半期データ）
    - fetch_market_calendar（JPX マーケットカレンダー）
  - DuckDB への冪等保存関数（ON CONFLICT DO UPDATE）：
    - save_daily_quotes, save_financial_statements, save_market_calendar
  - 型変換ユーティリティ（_to_float, _to_int）で不正値や空値を安全に扱う。

- ニュース収集（kabusys.data.news_collector）
  - RSS フィードからのニュース収集ロジック（fetch_rss）と記事整形ユーティリティ群。
  - セキュリティ対策：
    - defusedxml による安全な XML パース（XML Bomb 等対策）。
    - HTTP/HTTPS スキームのみ許可。その他スキーム（file:, mailto: 等）を拒否。
    - SSRF 防止：ホストがプライベート／ループバック／リンクローカルかを判定し拒否。リダイレクト時にも検査するカスタムハンドラを導入。
    - レスポンスサイズ上限（MAX_RESPONSE_BYTES = 10MB）によるメモリ DoS 対策。gzip 解凍後の再チェック含む。
  - URL 正規化とトラッキングパラメータ除去（_normalize_url、_make_article_id により SHA-256 ハッシュの短縮IDを生成）。
  - テキスト前処理（URL 除去、空白正規化）。
  - DB 保存ロジック（DuckDB）：
    - save_raw_news: チャンク分割・トランザクション・INSERT ... RETURNING を用いた冪等保存。
    - save_news_symbols / _save_news_symbols_bulk: ニュースと銘柄の紐付けを一括挿入（重複排除、トランザクション、RETURNING 集計）。
  - 銘柄コード抽出ユーティリティ（4桁コード抽出、known_codes フィルタ）。
  - デフォルト RSS ソースの定義（Yahoo Finance のカテゴリRSS を含む）。

- DuckDB スキーマ管理（kabusys.data.schema）
  - Raw / Processed / Feature / Execution といったレイヤーに沿ったテーブル定義を実装（raw_prices, raw_financials, raw_news, raw_executions, prices_daily, market_calendar, fundamentals, news_articles, news_symbols, features, ai_scores, signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance 等）。
  - 各種制約・データ型（CHECK, PRIMARY KEY, FOREIGN KEY）を明示。
  - 頻出クエリに対するインデックス定義を追加。
  - init_schema(db_path) により DB ファイル親ディレクトリを自動作成して全テーブル・インデックスを冪等に作成。
  - get_connection(db_path) による既存 DB への接続ユーティリティ。

- ETL パイプライン（kabusys.data.pipeline）
  - ETL 結果を表す ETLResult データクラス（品質検査結果・エラー一覧を含む）。
  - DB テーブル存在チェック、最大日付取得ユーティリティ（_table_exists, _get_max_date）。
  - 市場カレンダー非営業日調整ヘルパー（_adjust_to_trading_day）。
  - 差分更新用ユーティリティ（get_last_price_date, get_last_financial_date, get_last_calendar_date）。
  - run_prices_etl の初期実装（差分算出、backfill_days による再取得、J-Quants からの取得と保存の呼び出し）。設計上の方針（差分更新・バックフィル・品質チェックの継続動作）を実装。

- テスト支援 / 拡張性
  - RSS のネットワーク呼び出しを差し替え可能（_urlopen をモック可能）など、テストしやすい設計を採用。
  - 型アノテーション・詳細なドキュメント文字列を多用し可読性を確保。

### Security
- news_collector および fetch_rss 周辺で複数の安全対策を導入（defusedxml、SSRF/プライベートネットワーク検出、サイズ上限、スキーム検証）。
- J-Quants クライアントでの認証トークン自動リフレッシュとリトライ戦略により認証エラーや一時的な障害に耐性を持たせる。

### Performance
- API レート制御（固定間隔）によりレート違反を回避。
- DuckDB へのバルク挿入・チャンク処理および INSERT ... RETURNING による効率的な DB 操作。
- news_collector のチャンクサイズ制御で SQL 長やパラメータ数の上限を抑制。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Deprecated
- （初回リリースのため該当なし）

### Removed
- （初回リリースのため該当なし）

### Internal
- モジュール間でのトークンキャッシュやヘルパー関数を整備し、ページネーションや複数関数間の共通処理を安全に再利用可能に実装。
- strategy/execution/monitoring パッケージはエントリポイント（__init__）のみ整備済みで、今後戦略・発注・監視ロジックを追加予定。

---

注: 本 CHANGELOG は提供されたソースコードから機能・設計方針を推測して作成しています。実際のリリースノートや変更履歴はリポジトリのコミット履歴やリリース時の決定に基づいて調整してください。