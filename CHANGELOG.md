CHANGELOG
=========

すべての重要な変更はこのファイルに記載します。  
このプロジェクトは Keep a Changelog の方針に準拠しています。  

フォーマット:
- Unreleased: 今後の変更
- 各リリースは日付付きで記載

Unreleased
----------

- 次回リリースに向けた保留中の変更はありません。

[0.1.0] - 2026-03-18
-------------------

初回リリース — 基本的なデータ取得／保存／ETL／ニュース収集および設定周りの基盤実装。

Added
- パッケージ基盤
  - kabusys パッケージ初期化。__version__ を "0.1.0" として公開。
  - パッケージの公開モジュール: data, strategy, execution, monitoring を __all__ に定義。

- 環境設定 (kabusys.config)
  - .env ファイルや環境変数を読み込む Settings クラスを実装。
  - 自動 .env ロード機能:
    - プロジェクトルートを .git または pyproject.toml を起点に探索して検出。
    - 読み込み順序: OS 環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能（テスト用）。
  - .env パーサ: export プレフィックス、シングル／ダブルクォート、エスケープ、インラインコメントの処理に対応。
  - 必須環境変数取得用の _require() と、各種設定プロパティを提供（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID）。
  - DB パスのデフォルト値（DuckDB: data/kabusys.duckdb, SQLite: data/monitoring.db）を設定。
  - KABUSYS_ENV と LOG_LEVEL の値検証ロジックを実装（有効値の検査）。

- J-Quants API クライアント (kabusys.data.jquants_client)
  - 日足株価（fetch_daily_quotes）、財務（fetch_financial_statements）、JPX カレンダー（fetch_market_calendar）の取得を実装（ページネーション対応）。
  - 認証トークン取得（get_id_token）とモジュールレベルでのトークンキャッシュ実装。
  - レート制御: _RateLimiter により 120 req/min（固定間隔スロットリング）を順守。
  - 再試行ロジック:
    - 指数バックオフ、最大 3 回のリトライ（ネットワークエラーや 408/429/5xx を対象）。
    - 401 を受信した場合はトークンを自動リフレッシュして一度だけ再試行。
    - 429 の場合は Retry-After ヘッダ優先。
  - DuckDB への保存関数（冪等実装）:
    - save_daily_quotes: raw_prices に ON CONFLICT DO UPDATE を使って保存。
    - save_financial_statements: raw_financials に ON CONFLICT DO UPDATE を使って保存。
    - save_market_calendar: market_calendar に ON CONFLICT DO UPDATE を使って保存。
  - データの fetched_at を UTC で記録し、いつデータを取得したかをトレース可能にする。
  - 型変換ユーティリティ (_to_float, _to_int) を実装して不正値や小数の切捨てを回避。

- ニュース収集 (kabusys.data.news_collector)
  - RSS フィードから記事を収集して raw_news に保存する機能を実装。
  - セキュリティ対策:
    - defusedxml を使った XML パース（XML Bomb などに対処）。
    - SSRF 防止: URL スキームは http/https のみ許可、リダイレクト先の検査、プライベート IP/ループバック/リンクローカル/マルチキャストへのアクセスを拒否。
    - 受信サイズ上限（MAX_RESPONSE_BYTES = 10MB）を設け、読み込み超過を検出。
    - gzip 圧縮レスポンスの解凍時もサイズ検査を実行（Gzip bomb 対策）。
  - URL 正規化とトラッキングパラメータ除去:
    - _normalize_url により utm_* 等を除去しクエリをソート、フラグメント削除。
    - 記事ID は正規化 URL の SHA-256 ハッシュ（先頭32文字）で生成し冪等性を担保。
  - DB 保存:
    - save_raw_news: INSERT ... ON CONFLICT DO NOTHING RETURNING を用い、実際に挿入された記事IDのリストを返す。チャンク毎に一つのトランザクションで処理。
    - save_news_symbols / _save_news_symbols_bulk: news_symbols テーブルへの銘柄紐付けをチャンク/トランザクションで保存、INSERT ... RETURNING で実際に挿入された件数を返す。
  - テキスト前処理 (preprocess_text): URL 除去、空白正規化。
  - 銘柄コード抽出 (extract_stock_codes): 文章中の4桁数字候補を抽出し known_codes と照合して重複を排除して返す。
  - デフォルト RSS ソースに Yahoo Finance のビジネスカテゴリを追加（DEFAULT_RSS_SOURCES）。

- スキーマ管理 (kabusys.data.schema)
  - DuckDB 用の一貫したスキーマを定義（Raw, Processed, Feature, Execution 層）。
  - テーブル群（raw_prices, raw_financials, raw_news, raw_executions, prices_daily, market_calendar, fundamentals, news_articles, news_symbols, features, ai_scores, signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance）を定義。
  - 各カラムの CHECK 制約、PRIMARY KEY、外部キー制約を設定。
  - 頻出クエリ向けのインデックス群を定義。
  - init_schema(db_path) によりディレクトリ自動作成と全DDL実行（冪等）を提供。get_connection(db_path) で既存 DB に接続可能。

- ETL パイプライン (kabusys.data.pipeline)
  - ETL の設計と基本ヘルパ実装:
    - 差分更新のための最終取得日取得関数（get_last_price_date, get_last_financial_date, get_last_calendar_date）。
    - 営業日調整ヘルパ (_adjust_to_trading_day) を実装（market_calendar に基づき過去方向に調整）。
    - run_prices_etl の骨組みを実装: 差分判定、backfill（デフォルト3日）を考慮して jq.fetch_daily_quotes → jq.save_daily_quotes を実行。取得件数・保存件数を返す設計。
  - ETLResult データクラスを導入し、ETL 実行結果（取得数、保存数、品質問題、エラー等）を構造化して返す仕組みを用意。
  - 品質チェック設計（quality モジュール連携を想定）: 品質問題は致命的でも ETL を継続し呼び出し側で判断する方式。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Security
- news_collector における複数の SSRF／XML 脆弱性緩和策を実装（スキーム検査、プライベートIP検査、defusedxml、サイズ上限など）。
- .env 読み込みは OS 環境変数を保護する仕組み（protected set）を導入し、.env.local は既存のOS環境変数を上書きするが OS変数自体は保護される。

Notes / Known limitations
- run_prices_etl など ETL の一部は基本的なフローを実装済みだが、品質チェック（quality モジュール）や完全なエラー集約・通知フロー、strategy/execution/monitoring の詳細実装は今後の実装対象。
- DuckDB の INSERT 文は文字列連結でプレースホルダを作る実装が含まれるため、将来的に非常に大きなチャンクや特殊文字処理で追加検証が必要になる可能性がある（現在はチャンクサイズ制限を設けている）。
- news_collector の URL 正規化・ハッシュにより URL の微妙な差異は同一記事と見なされる設計。トラッキングパラメータ以外の差異は将来調整の余地あり。

Authors
- 初期実装: 開発チーム（コードベースから推測して記載）

ライセンス
- プロジェクトに付与されるライセンスに従ってください（このコード断片からはライセンス情報は推測できません）。

-- End of changelog --