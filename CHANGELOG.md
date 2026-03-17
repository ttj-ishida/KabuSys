Changelog
=========

すべての注目すべき変更はここに記録します。  
フォーマットは「Keep a Changelog」に準拠します。

[Unreleased]
------------

（なし）

[0.1.0] - 2026-03-17
-------------------

初回リリース。

Added
- パッケージの基本構成
  - pakage: kabusys（src/kabusys）
  - バージョン定義: __version__ = "0.1.0"
  - __all__ エクスポート: ["data", "strategy", "execution", "monitoring"]

- 設定 / 環境変数管理（src/kabusys/config.py）
  - .env / .env.local ファイルと OS 環境変数から設定を自動読み込みする仕組みを実装。
  - プロジェクトルート探索は __file__ を起点に .git または pyproject.toml を探索（CWDに依存しない実装）。
  - .env のパース機能: export プレフィックス、シングル/ダブルクォート、エスケープ、インラインコメント処理に対応。
  - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能（テスト向け）。
  - Settings クラスを公開（settings）。以下のプロパティを提供:
    - JQUANTS_REFRESH_TOKEN（必須）
    - KABU_API_PASSWORD
    - KABU_API_BASE_URL（デフォルト http://localhost:18080/kabusapi）
    - SLACK_BOT_TOKEN / SLACK_CHANNEL_ID（必須）
    - DUCKDB_PATH / SQLITE_PATH（デフォルト値あり）
    - KABUSYS_ENV の検証（development / paper_trading / live）
    - LOG_LEVEL の検証（DEBUG/INFO/WARNING/ERROR/CRITICAL）
    - is_live/is_paper/is_dev（環境判定ユーティリティ）

- J-Quants API クライアント（src/kabusys/data/jquants_client.py）
  - 基本機能:
    - 株価日足（OHLCV）取得: fetch_daily_quotes
    - 財務データ取得（四半期 BS/PL）: fetch_financial_statements
    - JPX マーケットカレンダー取得: fetch_market_calendar
    - リクエストの共通処理: _request、get_id_token（リフレッシュ用）
  - 設計・実装上の特徴:
    - レート制御: 固定間隔スロットリングで 120 req/min を遵守（_RateLimiter）。
    - リトライロジック: 指数バックオフ、最大 3 回、408/429/5xx を対象。429 の場合は Retry-After を優先。
    - 401 発生時の自動トークンリフレッシュ（1 回のみ）と、ページネーション間で使えるモジュールレベルの ID トークンキャッシュ。
    - ページネーション処理をサポート（pagination_key の扱い）。
    - DuckDB への保存関数: save_daily_quotes / save_financial_statements / save_market_calendar（いずれも冪等性を考慮した ON CONFLICT DO UPDATE を使用）。
    - 取得タイミングを記録する fetched_at（UTC ISO8601、Z表記）。
    - 型変換ユーティリティ: _to_float / _to_int（空値・不正値への安全な対応）。
    - ログ出力による操作状況のトレース。

- ニュース収集モジュール（src/kabusys/data/news_collector.py）
  - RSS フィードからのニュース収集・前処理・DB保存を実装:
    - fetch_rss: RSS 取得 → XML パース → 記事リスト生成
    - save_raw_news: raw_news テーブルへチャンク単位で INSERT ... RETURNING を使って保存（トランザクション・チャンク挿入）
    - save_news_symbols / _save_news_symbols_bulk: 記事と銘柄コードの紐付け（news_symbols テーブル）
    - extract_stock_codes: 本文から 4 桁銘柄コード（正規表現 \b(\d{4})\b）を抽出（known_codes によるフィルタ、重複除去）
  - セキュリティ・堅牢性対策:
    - defusedxml を利用して XML Bomb 等を防御。
    - SSRF 対策:
      - URL スキーム検証（http/https のみ許可）。
      - リダイレクト時にスキームとホスト/IP を検査する HTTPRedirectHandler（_SSRFBlockRedirectHandler）。
      - _is_private_host によりホスト/IP がプライベート/ループバック/リンクローカル/マルチキャストでないことを確認。
    - レスポンスサイズ制限: MAX_RESPONSE_BYTES = 10MB、超過時はスキップ（読み込み上限チェック・gzip 解凍後も検証）。
    - URL 正規化: _normalize_url（トラッキングパラメータ除去、フラグメント除去、クエリソート）。
    - 記事ID は正規化 URL の SHA-256（先頭 32 文字）で生成し冪等性を担保。
  - 実装上のパフォーマンス配慮:
    - バルク INSERT のチャンク化（_INSERT_CHUNK_SIZE）。
    - 一連の挿入を 1 トランザクションにまとめることでオーバーヘッド削減。
    - INSERT ... RETURNING を利用して実際に挿入された件数/ID を正確に取得。
  - デフォルト RSS ソースを定義（DEFAULT_RSS_SOURCES に yahoo_finance を含む）。

- データベーススキーマ & 初期化（src/kabusys/data/schema.py）
  - DuckDB 用スキーマ定義（Raw / Processed / Feature / Execution 層）を実装:
    - raw_prices, raw_financials, raw_news, raw_executions
    - prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - features, ai_scores
    - signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 制約・チェック条件（NOT NULL, PRIMARY KEY, CHECK 等）を保有。
  - 推奨インデックスを定義（よく使うクエリパターンを想定した索引群）。
  - 公開 API:
    - init_schema(db_path): DB ファイル親ディレクトリの自動作成、DDL/INDEX の冪等実行、DuckDB 接続を返す。
    - get_connection(db_path): 既存 DB への接続（スキーマ初期化は行わない）。

- ETL パイプライン（src/kabusys/data/pipeline.py）
  - ETL の設計と実装支援:
    - ETLResult dataclass: 実行結果、取得/保存件数、品質チェック結果、エラー一覧等を保持。to_dict によりシリアライズ可能。
    - 差分更新ユーティリティ:
      - _table_exists / _get_max_date（テーブル存在確認・最大日付取得）
      - get_last_price_date / get_last_financial_date / get_last_calendar_date
      - _adjust_to_trading_day: 非営業日の調整（market_calendar に基づく）
    - run_prices_etl:
      - 差分更新ロジック（DB の最終取得日から backfill_days を考慮して取得レンジを決定、初回は _MIN_DATA_DATE を使用）
      - jq.fetch_daily_quotes → jq.save_daily_quotes を使って取得・保存
  - 設計方針:
    - デフォルト差分単位は営業日1日分、backfill_days による後出し修正吸収。
    - 品質チェックは fail-fast しない（問題が見つかっても可能な限り収集を継続し、呼び出し元が判断する）。

Security
- XML パーサに defusedxml を使用して XML 関連の攻撃を緩和。
- RSS フェッチでの SSRF 対策（URL スキーム検証、リダイレクト先の検査、プライベートアドレス拒否）。
- .env ロード時、OS 環境変数を保護する protected セットを導入（.env.local の override を制御）。

Performance
- J-Quants API へのアクセスは 120 req/min のレート制御（固定スロットリング）。
- トークン再取得はキャッシュを使い、ページネーション間で共有して API 呼び出しを効率化。
- DB への書き込みはバルク挿入 / チャンク化 / トランザクションでオーバーヘッドを低減。
- 冪等性を確保するため INSERT ... ON CONFLICT を積極的に採用。

Notes / Migration
- 初期リリースのため互換性破壊の履歴はありません。
- DuckDB を運用する際は init_schema() を一度実行してスキーマを作成してください。既存スキーマがある場合は冪等的にスキップされます。
- 自動 .env ロードを無効にしたい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。

Contact / Contributing
- バグ報告や改善提案はリポジトリの ISSUE へお願いします。
- テストや CI に関連するフラグ（例: KABUSYS_DISABLE_AUTO_ENV_LOAD）を用意しており、テスト容易性を考慮した設計になっています。

----- 

（補足）この CHANGELOG は提供されたコードベースから推測して作成しています。実際のリリースノートを作成する際は、追加の変更点やリリース手順・既知の制限事項を追記してください。