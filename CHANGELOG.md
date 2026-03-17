# Changelog

すべての重要な変更点をここに記録します。  
フォーマットは「Keep a Changelog」に準拠します。

現在のバージョンは [0.1.0]（初回リリース）です。

## [Unreleased]

なし。

## [0.1.0] - 2026-03-17

初回リリース。日本株自動売買システムライブラリ「KabuSys」の基本機能を実装しました。主な追加点は以下の通りです。

### Added
- パッケージ基盤
  - src/kabusys/__init__.py: パッケージ初期化、バージョン情報（0.1.0）および公開モジュール定義を追加。

- 設定・環境変数管理
  - src/kabusys/config.py:
    - .env / .env.local ファイルおよび OS 環境変数から設定を読み込む自動ローダ実装（読み込み優先順位: OS 環境変数 > .env.local > .env）。
    - 自動読み込みを無効化する環境変数フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD。
    - .env パーサの実装（export 形式対応、クォート内エスケープ、行内コメントの扱いなど）。
    - OS 環境変数を保護する protected 機能（.env.local の上書き時に既存キーを保護）。
    - Settings クラスを追加し、J-Quants / kabuステーション / Slack / DB パス / システム設定（KABUSYS_ENV, LOG_LEVEL）などをプロパティで取得。値のバリデーション（許容値チェック）を実装。

- J-Quants API クライアント（データ取得・保存）
  - src/kabusys/data/jquants_client.py:
    - API 呼び出しユーティリティ（_request）を実装。JSONデコード、タイムアウト処理、ページネーション対応。
    - レート制御（120 req/min）を守る固定間隔スロットリング実装（_RateLimiter）。
    - 再試行ロジック（指数バックオフ、最大 3 回、408/429/5xx を対象）、429 の場合は Retry-After ヘッダ優先。
    - 401 受信時のトークン自動リフレッシュ（1 回のみ）を実装。トークン取得関数 get_id_token を提供。
    - データ取得関数:
      - fetch_daily_quotes（株価日足、ページネーション対応）
      - fetch_financial_statements（四半期財務、ページネーション対応）
      - fetch_market_calendar（JPX マーケットカレンダー）
    - DuckDB への保存関数（冪等性を確保）:
      - save_daily_quotes, save_financial_statements, save_market_calendar
      - INSERT ... ON CONFLICT DO UPDATE による重複排除・更新、fetched_at を UTC ISO タイムスタンプで記録
    - 型変換ユーティリティ: _to_float, _to_int（安全な数値変換・不正値は None）

- ニュース収集（RSS）モジュール
  - src/kabusys/data/news_collector.py:
    - RSS フィード取得・前処理・DB 保存の一連処理を実装。
    - 設計に基づく安全対策:
      - defusedxml を使用した XML パース（XML Bomb 等に耐性）。
      - SSRF 対策: URL スキーム検証（http/https のみ許可）、ホストがプライベートアドレスかを判定してブロック、リダイレクト時にも検査するカスタムリダイレクトハンドラ（_SSRFBlockRedirectHandler）。
      - レスポンス受信サイズ上限（MAX_RESPONSE_BYTES = 10 MB）を導入し、gzip 解凍後も検査。
      - URL 正規化（トラッキングパラメータ除去、フラグメント削除、クエリソート）、正規化 URL から記事 ID を生成（SHA-256 の先頭32文字）。
      - URL を除去して空白正規化するテキスト前処理。
    - DB 書き込みの効率化・整合性:
      - save_raw_news: チャンク挿入（_INSERT_CHUNK_SIZE）、1 トランザクションで実行、INSERT ... ON CONFLICT DO NOTHING RETURNING id を使用して新規挿入 ID を取得。
      - save_news_symbols / _save_news_symbols_bulk: 記事と銘柄コードの紐付けを一括保存。重複除去・チャンク挿入・トランザクション管理を実装。
    - 銘柄コード抽出:
      - extract_stock_codes: テキスト中の 4 桁数字を候補とし、known_codes（有効コードセット）でフィルタして重複を除去して返す。
    - 高レベルジョブ:
      - fetch_rss（単一フィード取得）および run_news_collection（複数ソースの統合収集、各ソースで独立エラーハンドリング、新規保存件数集計・銘柄紐付け）を実装。
    - デフォルト RSS ソースを定義（DEFAULT_RSS_SOURCES に yahoo_finance を含む）。

- DuckDB スキーマ定義・初期化
  - src/kabusys/data/schema.py:
    - Raw / Processed / Feature / Execution の各レイヤーに対応したテーブル DDL を定義。
    - 制約（PRIMARY KEY / CHECK / FOREIGN KEY 等）を適切に付与。
    - 検索効率化のためのインデックス定義を追加（頻出クエリパターンを考慮）。
    - init_schema(db_path): DB ファイルの親ディレクトリ自動作成、全テーブル・インデックスを冪等的に作成して接続を返す。
    - get_connection(db_path): 既存 DB への接続取得（初期化は行わない）。

- ETL パイプライン基盤
  - src/kabusys/data/pipeline.py:
    - ETLResult dataclass: ETL 実行結果（取得数・保存数・品質問題・エラー等）を集約する構造と to_dict()。
    - 差分更新ユーティリティ:
      - _table_exists, _get_max_date（任意テーブルの最大日付取得）、get_last_price_date, get_last_financial_date, get_last_calendar_date。
      - _adjust_to_trading_day: 非営業日調整（market_calendar の存在を利用）。
    - run_prices_etl: 株価差分 ETL の実装（差分算出、backfill_days による再取得、J-Quants からの取得→保存フロー）。差分更新・バックフィル・品質チェック設計に基づく実装指針を反映。
    - 設計方針として、品質チェックが致命的エラーであっても ETL を継続する（Fail-Fast ではない）点を明示。

### Security
- RSS ニュース収集でのセキュリティ強化:
  - defusedxml を用いた安全な XML パース。
  - SSRF 対策（スキーム検証、プライベート/ループバック/リンクローカルのホスト判定、リダイレクト検査）。
  - レスポンスサイズ制限と gzip 解凍後の再チェック（Gzip Bomb 対策）。
  - 許可されていない URL スキームの除外（mailto:, file:, javascript: 等を排除）。

### Performance / Reliability
- API 呼び出しのレート制御を実装（120 req/min の固定間隔スロットリング）。
- 再試行（指数バックオフ）と 429 の Retry-After 尊重で信頼性を向上。
- DuckDB への挿入処理でチャンク化・トランザクション・ON CONFLICT を活用し冪等性と性能を確保。
- ニュースの大量挿入でチャンク単位に分割して SQL 文長・パラメータ数を抑制。

### Notes
- 環境変数の自動読み込みはデフォルトで有効。テストや CI 等で無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- settings の KABUSYS_ENV・LOG_LEVEL は許容値をチェックし、不正な値は ValueError を送出します。
- jquants_client の save_* 関数は fetched_at を UTC で記録し、Look-ahead Bias のトレースを可能にしています。
- news_collector は記事 ID を正規化 URL の SHA-256 ハッシュ先頭で生成するため、トラッキングパラメータの違いで同一記事が重複登録されるリスクを低減しています。

### Breaking Changes
- 初回リリースのため該当なし。

### Fixed / Changed / Removed
- 初回リリースのため該当なし。

---

貢献・バグ報告・改善提案は Issue / PR を通じてお寄せください。将来的には以下のような拡張を予定しています（例）:
- ETL の品質チェック実装（quality モジュールの統合）。
- strategy / execution / monitoring モジュールの実装強化（現在はパッケージ公開のみ）。
- 単体テスト・統合テストの追加と CI パイプライン整備。