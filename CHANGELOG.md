# Changelog

すべての重要な変更点をこのファイルに記録します。フォーマットは「Keep a Changelog」に準拠します。  

なお、このチェンジログは提供されたコードベースの内容から推測して作成しています。

## [Unreleased]
- なし

## [0.1.0] - 2026-03-17
初回リリース。日本株自動売買システム KabuSys の基本機能群を実装しました。主な追加点は以下の通りです。

### Added
- パッケージ基盤
  - パッケージメタ情報と公開モジュールを定義（kabusys.__init__: __version__ = 0.1.0、__all__ に data/strategy/execution/monitoring を設定）。

- 環境設定管理（kabusys.config）
  - .env ファイルおよび環境変数から設定を読み込む Settings クラスを実装。
  - 自動ロード: プロジェクトルート（.git または pyproject.toml を根拠）を探索して .env/.env.local を自動読込。OS 環境変数を保護する保護機構を実装。
  - .env パーサ実装: コメント、export 形式、シングル／ダブルクォートとバックスラッシュエスケープ、インラインコメントの扱い等に対応する堅牢な行パーサを実装。
  - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能。
  - 必須環境変数取得ヘルパ（_require）。環境値検証: KABUSYS_ENV（development/paper_trading/live）、LOG_LEVEL の妥当性チェック。
  - 各種設定プロパティを提供（J-Quants トークン、kabu API 設定、Slack トークン／チャンネル、DB パス等）。

- J-Quants API クライアント（kabusys.data.jquants_client）
  - ベース API クライアントを実装。fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar を提供（ページネーション対応）。
  - 認証: リフレッシュトークンから ID トークンを取得する get_id_token を実装。モジュールレベルでトークンをキャッシュ。
  - レート制御: 固定間隔スロットリング方式の RateLimiter を導入し、120 req/min 制限を順守。
  - リトライ戦略: 指数バックオフ（最大 3 回）、408/429/5xx に対する再試行、429 の場合は Retry-After ヘッダを尊重。401 受信時はトークン自動リフレッシュを 1 回行って再試行。
  - DuckDB への保存機能（冪等）を実装: save_daily_quotes, save_financial_statements, save_market_calendar。ON CONFLICT DO UPDATE により重複を排除し更新を行う。
  - データ整形ユーティリティ: _to_float / _to_int（入力の堅牢な数値変換、空値や不正フォーマットに対する安全処理）。
  - ロギングを通じた取得件数／保存件数の記録。

- ニュース収集モジュール（kabusys.data.news_collector）
  - RSS フィードからニュース記事を収集し raw_news テーブルへ保存する機能を実装（fetch_rss / save_raw_news / save_news_symbols 等）。
  - セキュリティ対策:
    - defusedxml を用いた XML パースで XMLBomb 等の攻撃を防御。
    - SSRF 対策: URL スキーム検証（http/https のみ）、ホストがプライベート/ループバック/リンクローカルでないかを検査、リダイレクト時にも検証するカスタム RedirectHandler を導入。
    - 受信最大バイト数制限（MAX_RESPONSE_BYTES = 10 MB）によるメモリ DoS 対策。gzip 圧縮レスポンスの解凍後もサイズ検査。
  - 記事ID設計: URL を正規化（スキームとホスト小文字化、トラッキングパラメータ除去、フラグメント除去、クエリソート）した上で SHA-256 の先頭32文字を用いることで冪等性を保証。
  - トラッキングパラメータ除去: utm_*, fbclid, gclid, ref_, _ga 等の除去に対応。
  - テキスト前処理: URL 除去、空白正規化を行う preprocess_text。
  - DB 保存: INSERT ... RETURNING を使って実際に挿入された記事IDを返却。チャンク化（_INSERT_CHUNK_SIZE）と 1 トランザクションでの処理（conn.begin/commit/rollback）で効率と原子性を確保。
  - 銘柄紐付け: テキストから 4 桁銘柄コードを抽出する extract_stock_codes と一括保存ヘルパ _save_news_symbols_bulk を提供。run_news_collection により複数ソースを順次収集して保存するワークフローを実装。

- DuckDB スキーマ定義（kabusys.data.schema）
  - DataSchema に基づく DB スキーマを実装。Raw / Processed / Feature / Execution の各レイヤのテーブル DDL を含む。
  - 主要テーブル: raw_prices, raw_financials, raw_news, raw_executions, prices_daily, market_calendar, fundamentals, news_articles, news_symbols, features, ai_scores, signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance 等。
  - 制約（PRIMARY KEY / CHECK / FOREIGN KEY）や型を詳細に定義。
  - パフォーマンス考慮でのインデックス定義（銘柄×日付クエリやステータス検索などを想定）。
  - init_schema(db_path) を実装: 親ディレクトリ自動作成、DDL とインデックスを順に実行して DB を初期化して接続を返す。get_connection() で既存 DB に接続可能。

- ETL パイプライン基礎（kabusys.data.pipeline）
  - ETLResult データクラスを導入し、ETL 実行結果（取得数、保存数、品質問題、エラー）を集約可能に。
  - 差分更新ヘルパ: テーブル存在確認、最大日付取得のユーティリティ（_table_exists / _get_max_date / get_last_price_date 等）。
  - 市場カレンダー関連: 非営業日調整ヘルパ _adjust_to_trading_day。
  - run_prices_etl の差分更新ロジック開始: DB 上の最終取得日を基に date_from を自動算出し、backfill_days により後出し修正を吸収する方針を実装（fetch->save の流れを呼び出す設計）。品質チェック（quality モジュール）との連携を想定した構造。

- ユーティリティ・設計
  - 型ヒントとログを多用した読みやすい実装。
  - 冪等性・トランザクション・チャンク処理など、運用性を考えた設計。

### Security
- news_collector にて以下のセキュリティ強化を実施：
  - defusedxml を使用した XML パース（外部実行攻撃対策）。
  - SSRF 対策: 非 http/https スキーム拒否、プライベート IP へのアクセスを DNS レベルで検査してブロック、リダイレクト先検査。
  - レスポンスサイズと gzip 解凍後のサイズ上限チェック（メモリ消費攻撃対策）。
- .env 読み込み時に OS 環境変数の上書きを制御する保護機構を提供。

### Notes / Implementation Decisions
- J-Quants API はレート制限（120 req/min）と 401/429 等の挙動を考慮した堅牢なクライアント実装を行っています。ページネーション間で ID トークンを共有することで効率化しています。
- DuckDB 保存は可能な限り冪等（ON CONFLICT）を重視しており、ETL の再実行や差分更新に耐える設計です。
- ニュース記事の一意性は URL 正規化＋ハッシュにより担保されます。トラッキングパラメータ除去により同一記事の重複登録を低減します。
- ETL パイプラインは差分更新と backfill の考え方を取り入れており、品質チェック（quality モジュール）と組み合わせることでデータ品質を担保する設計を意図しています。

### Fixed
- なし（初回リリース）

### Changed
- なし（初回リリース）