# CHANGELOG

すべての重要な変更点を記録します。  
このファイルは「Keep a Changelog」形式に準拠しています。

## [Unreleased]
- （なし）

## [0.1.0] - 2026-03-17
初回リリース

### 追加 (Added)
- パッケージ基盤
  - パッケージエントリポイントを追加（kabusys.__init__、バージョン 0.1.0）。
  - モジュール構成: data, strategy, execution, monitoring（strategy と execution は初期プレースホルダ）。

- 設定 / 環境変数管理
  - 環境変数・設定モジュールを追加（kabusys.config）。
  - .env / .env.local の自動読み込み機能を実装（プロジェクトルート検出: .git または pyproject.toml を基準）。
  - 読み込み順序: OS 環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応。
  - .env パーサ（export キー、クォート文字列、インラインコメントの取り扱い）を実装。
  - Settings クラスで各種必須設定をプロパティで提供（J-Quants, kabu API, Slack, DB パスなど）。
  - KABUSYS_ENV / LOG_LEVEL 値の検証ロジックを追加（許可値チェック）。
  - デフォルトの DB パス（duckdb/sqlite）を設定。

- J-Quants API クライアント
  - jquants_client モジュールを追加。
  - レート制御 (120 req/min) を守る固定間隔スロットリング実装（_RateLimiter）。
  - リトライロジック（指数バックオフ、最大 3 回、408/429/5xx のリトライ）を実装。
  - 401 レスポンス受信時にリフレッシュトークンで自動的にトークンを更新して1回再試行。
  - ページネーション対応で株価日足・財務データを取得する fetch_* 関数を実装（fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar）。
  - DuckDB に対する冪等保存関数を実装（save_daily_quotes / save_financial_statements / save_market_calendar）。ON CONFLICT DO UPDATE による重複排除。
  - 型安全な変換ユーティリティ（_to_float, _to_int）を提供。
  - ロギングによる取得件数・保存件数の通知。

- ニュース収集モジュール
  - news_collector モジュールを追加（RSS フィード収集→raw_news 保存→銘柄紐付け）。
  - RSS 取得処理（fetch_rss）を実装:
    - defusedxml を使った安全な XML パース（XML Bomb 等の対策）。
    - リダイレクト時の事前検証と SSRF ブロック（_SSRFBlockRedirectHandler, _is_private_host）。
    - スキーム検証（http/https のみ許可）、Content-Length と実際の読み込みサイズで最大受信バイト数を制限（MAX_RESPONSE_BYTES = 10MB）。
    - gzip 圧縮レスポンスの解凍とサイズ検査（Gzip bomb 対策）。
    - URL 正規化とトラッキングパラメータ削除（_normalize_url）。
    - 記事IDは正規化 URL の SHA-256 の先頭 32 文字で生成（_make_article_id）。
    - テキスト前処理（URL 除去、空白正規化）。
  - DB 保存機能:
    - raw_news のチャンク挿入 + トランザクション + INSERT ... RETURNING により実際に挿入された記事IDを返却（save_raw_news）。
    - news_symbols の一括保存（_save_news_symbols_bulk）と個別保存（save_news_symbols）、ON CONFLICT による重複スキップ。
    - 銘柄コード抽出（4桁数字）関数 extract_stock_codes を実装。
  - デフォルト RSS ソース（例: Yahoo Finance）を設定。

- スキーマ定義 / DB 初期化
  - DuckDB 用スキーマ定義（raw / processed / feature / execution 各レイヤ）を追加（kabusys.data.schema）。
  - 各種テーブル DDL、制約、インデックスを用意。
  - init_schema(db_path) で DB ファイル親ディレクトリ自動作成→テーブル作成（冪等）・接続を返却。
  - get_connection(db_path) を提供。

- ETL パイプライン
  - data.pipeline モジュールを追加。
  - ETLResult dataclass による結果集約と品質問題・エラーメッセージの収集（to_dict を含む）。
  - 差分取得ヘルパー（テーブル存在確認、最大日付取得、営業日調整）を実装。
  - run_prices_etl を実装（差分取得・バックフィル・fetch/save の統合、デフォルト backfill_days=3、_MIN_DATA_DATE の適用）。

### セキュリティ (Security)
- RSS 処理時の SSRF 対策を実装（スキーム/ホストの検証、リダイレクト先検査、プライベートアドレス拒否）。
- XML パースに defusedxml を採用し安全性を強化。
- レスポンスの読み込み上限を設け、メモリ DoS / Gzip bomb を軽減。
- .env パーサはクォート・エスケープを正しく扱い、予期せぬ環境変数注入を防止。

### パフォーマンス (Performance)
- API 呼び出しのレート制限を守るスロットリング、トークンキャッシュ、指数バックオフで安定稼働を意図。
- DB 保存はチャンク分割・トランザクション・INSERT ... RETURNING を利用してオーバーヘッドを抑制。
- news_symbols の重複除去（順序保持）とバルク保存で挿入効率を改善。

### 既知の制限 / 注意点 (Known issues / Notes)
- strategy, execution パッケージはプレースホルダ（追加実装が想定される）。
- ETL の品質チェック（quality モジュール参照）は pipeline に統合される設計だが、実運用でのさらなる検証が必要。
- 単体テスト・統合テストはこの差分からは同梱されていないため、挙動確認のためのテストケース追加を推奨。

---

フィードバックや追加実装（例: 実行層の発注処理、戦略モジュールの実装、監視・アラート統合、CI テストの追加）は歓迎します。