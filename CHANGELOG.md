# CHANGELOG

すべての注目すべき変更は Keep a Changelog の形式に従って記載しています。  
このファイルは、プロジェクトのリリース履歴と主要な変更点のサマリを提供します。

フォーマット: https://keepachangelog.com/ja/1.0.0/

## [Unreleased]


## [0.1.0] - 2026-03-18
初回リリース。ローカル開発／データ収集／ETL 基盤のコア機能を実装。

### Added
- パッケージ全体
  - pakcage 名称/メタ情報を導入（kabusys.__init__ に __version__ = "0.1.0"、主要サブパッケージを __all__ に定義）。
  - モジュール構成: data, strategy, execution, monitoring（空の __init__ を含むディレクトリ構造の導入）。

- 設定管理 (kabusys.config)
  - .env ファイルまたは環境変数から構成を読み込む自動ローダーを実装。
    - プロジェクトルート検出: カレントディレクトリに依存せず、__file__ を基点に .git または pyproject.toml を探索してプロジェクトルートを特定。
    - 読み込み順序: OS 環境変数 > .env.local > .env。
    - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能（テスト向け）。
  - .env パーサ: export キーワード対応、クォート内のエスケープ処理、インラインコメントの扱い、無効行スキップなどをサポート。
  - .env ロード時の上書き制御: override と protected（OS 環境変数保護）を実装。
  - Settings クラスを提供し、アプリケーションで使う主要な設定をプロパティ経由で取得可能に:
    - J-Quants / kabuステーション / Slack / DB パス（DuckDB / SQLite）/ 環境（development/paper_trading/live）/ログレベル等。
    - env と log_level の値検証ロジック（許容値以外は ValueError）。

- J-Quants クライアント (kabusys.data.jquants_client)
  - J-Quants API クライアントを実装:
    - 株価日足（OHLCV）、財務データ（四半期 BS/PL）、JPX マーケットカレンダーの取得関数を実装（ページネーション対応）。
    - HTTP レスポンスの JSON デコード検査。
  - レート制御:
    - 固定間隔スロットリングで API レート制限（デフォルト 120 req/min）を厳守する RateLimiter を実装。
  - 再試行（Retry）ロジック:
    - 指数バックオフ（最大 3 回）、対象ステータスコード（408, 429 および 5xx）へのリトライ処理。
    - 429 の場合は Retry-After ヘッダを優先して待機時間を決定。
  - 認証トークン管理:
    - refresh_token から id_token を取得する get_id_token。
    - モジュールレベルの id_token キャッシュを共有し、401 受信時は自動でトークンをリフレッシュして 1 回リトライ。
  - DuckDB への保存関数（冪等）:
    - save_daily_quotes / save_financial_statements / save_market_calendar：ON CONFLICT DO UPDATE による上書きで冪等性を保証。
    - 保存時に fetched_at を UTC ISO タイムスタンプで記録（Look-ahead bias 抑止）。
  - データ変換ユーティリティ:
    - _to_float / _to_int：安全な型変換（空値・不正値は None、"1.0" のような浮動小数文字列の整数変換の扱い等）。

- ニュース収集モジュール (kabusys.data.news_collector)
  - RSS フィードから記事を収集して DuckDB に保存する機能を実装。
    - デフォルト RSS ソース (例: Yahoo Finance) を提供。
    - fetch_rss: RSS の取得・XML 解析（defusedxml を使用）・記事整形・記事リスト生成。
    - 前処理: URL 除去・空白正規化。
    - URL 正規化: スキーム/ホスト小文字化、utm_* 等のトラッキングパラメータ削除、フラグメント除去、クエリ整列。
    - 記事ID: 正規化 URL の SHA-256（先頭32文字）による deterministic ID 生成で冪等性を確保。
    - セキュリティ対策:
      - defusedxml による XML Bomb 等の緩和。
      - SSRF 対策: fetch 前とリダイレクト先のホストをチェックしてプライベートアドレスを拒否。
      - 許容スキームは http/https のみ。
      - レスポンス長の上限（MAX_RESPONSE_BYTES = 10 MB）を設け、gzip 圧縮の解凍後もチェック。
    - DB 保存:
      - save_raw_news: INSERT ... ON CONFLICT DO NOTHING RETURNING id を用い、新規挿入された記事IDのみを返す（チャンク毎に一括挿入し1トランザクションで処理）。
      - save_news_symbols / _save_news_symbols_bulk: 記事と銘柄コードの紐付けを一括保存。ON CONFLICT DO NOTHING と RETURNING を使用して実際に挿入された数を正確に返す。
      - バルク挿入時にチャンク処理を行い SQL 長やパラメータ数を抑制。
    - 銘柄コード抽出:
      - 正規表現により 4 桁数値を候補として抽出し、known_codes に含まれるコードのみ返す（重複除去）。

- スキーマ管理 (kabusys.data.schema)
  - DuckDB 用のスキーマ (Raw / Processed / Feature / Execution 層) を定義する DDL を実装。
    - Raw 層: raw_prices, raw_financials, raw_news, raw_executions
    - Processed 層: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature 層: features, ai_scores
    - Execution 層: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各テーブルに制約・チェック制約を付与（NOT NULL, PRIMARY KEY, CHECK 等）。
  - 頻出クエリに備えたインデックス定義を追加。
  - init_schema(db_path) により DB ファイルの親ディレクトリ作成、全テーブルとインデックスを冪等的に作成して DuckDB 接続を返す。
  - get_connection(db_path) を提供（スキーマ初期化は行わない）。

- ETL パイプライン (kabusys.data.pipeline)
  - ETLResult dataclass を導入し、ETL 実行結果（取得数・保存数・品質問題・エラー等）を構造化。
  - 差分更新ロジックのためのユーティリティ:
    - _table_exists / _get_max_date を実装し、raw テーブルの最終取得日を取得する関数を提供。
    - get_last_price_date / get_last_financial_date / get_last_calendar_date を実装。
  - 市場カレンダー考慮のヘルパー: _adjust_to_trading_day（非営業日の補正処理）。
  - run_prices_etl を実装（差分取得・バックフィル日数の扱い・J-Quants からの取得と保存を統合）。
    - デフォルトバックフィル: 3 日。初回ロード時は最小データ開始日（2017-01-01）を使用。
    - ETL は取得 → 保存の流れを実施し、ログ出力と取得/保存件数を返す。
  - 品質チェック（quality モジュール）を呼び出すためのフックを想定（quality は別モジュールとして用意される想定）。

### Security
- 外部データ取得に対する複数のセキュリティ対策を導入:
  - RSS XML 解析に defusedxml を使用して XML-based 攻撃を緩和。
  - SSRF 対策: フェッチ元 URL とリダイレクト先のスキーム検証、ホストのプライベート/ループバック/リンクローカル判定で内部ネットワークアクセスを拒否。
  - レスポンスサイズの上限と gzip 解凍後のサイズ検査でメモリ DoS を軽減。
  - HTTP リクエストに対するタイムアウトと最大受信バイト数を設定。

### Reliability / Resilience
- API 呼び出しに対してレートリミッティング、リトライ（指数バックオフ）、およびトークン自動リフレッシュを実装。
- DuckDB への保存は冪等性を意識（ON CONFLICT DO UPDATE / DO NOTHING）しており、重複挿入や再実行に耐性あり。
- トランザクション周りは明示的に begin/commit/rollback を行い、失敗時はロールバックして例外を再送出。

### Performance
- RSS/ニュースの一括保存においてチャンクサイズを導入し、一度に大量のパラメータを投げない工夫を実装。
- RateLimiter により API 呼び出し間隔を制御してサーバ側レート制限違反の発生を抑制。

### Testing / Developer Experience
- 自動 .env ロードを無効化する KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数を提供し、テスト時に環境を制御しやすくした。
- news_collector._urlopen はテスト用にモック差し替え可能なラッパー関数になっている（外部通信を置き換え可能）。

### Notes
- run_prices_etl などの ETL 関数は差分更新とバックフィルの考慮を行う設計。品質チェック（quality モジュール）との統合は想定されているが、quality 側の実装は別途。
- 一部の関数は将来の拡張（例: strategy / execution / monitoring の具象実装）を想定したインタフェースになっている。

---

今後の予定（例）
- strategy / execution モジュールの具体実装（シグナル生成 → 発注連携）。
- quality モジュール（データ品質チェック）の実装と ETL パイプラインへの統合。
- モニタリング・アラート（Slack 連携）の実装。