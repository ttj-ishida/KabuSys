# Changelog

すべての注目すべき変更をここに記録します。  
フォーマットは「Keep a Changelog」に準拠します。

※本ファイルの内容は与えられたソースコードから推測して記載しています。

## [Unreleased]

### 修正予定 / 要対応
- run_prices_etl の戻り値が不完全（実装途中に見える）。現状は `return len(records),` で終わっており、本来返すべき `(fetched_count, saved_count)` の形式になっていない。リリース前に修正が必要。

---

## [0.1.0] - 2026-03-18

初期リリース（ソースコードから推測した主要機能・設計方針のまとめ）

### 追加 (Added)
- パッケージ基盤
  - kabusys パッケージ初期化（__version__ = 0.1.0, __all__ の定義）。

- 環境設定管理 (src/kabusys/config.py)
  - .env ファイルおよび環境変数から設定を自動読み込み（プロジェクトルートを .git / pyproject.toml で探索）。
  - 自動ロードの無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - .env ファイルの export KEY=val 形式やクォートあり/なし行のパースに対応する独自パーサを実装。
  - 読み込み順序: OS環境変数 > .env.local > .env、.env.local は上書きモードで読み込む。
  - Settings クラスを提供（J-Quants トークン、kabu API パスワード、Slack トークン/チャネル、DBパス等）。
  - KABUSYS_ENV の許容値チェック（development, paper_trading, live）。
  - LOG_LEVEL の許容値チェック（DEBUG, INFO, WARNING, ERROR, CRITICAL）。

- J‑Quants データクライアント (src/kabusys/data/jquants_client.py)
  - API ベース実装（_BASE_URL）。
  - レート制限（120 req/min）を守る固定間隔スロットリング _RateLimiter 実装。
  - 再試行ロジック（指数バックオフ、最大 3 回、対象ステータス: 408 / 429 / 5xx）。
  - 401 (Unauthorized) 受信時のトークン自動リフレッシュ（1 回のみ）とトークンキャッシュ共有。
  - ページネーション対応の取得関数:
    - fetch_daily_quotes (株価日足)
    - fetch_financial_statements (財務データ)
    - fetch_market_calendar (JPX マーケットカレンダー)
  - DuckDB へ冪等に保存する save_* 関数:
    - save_daily_quotes (raw_prices, ON CONFLICT DO UPDATE)
    - save_financial_statements (raw_financials, ON CONFLICT DO UPDATE)
    - save_market_calendar (market_calendar, ON CONFLICT DO UPDATE)
  - 型変換ユーティリティ _to_float / _to_int（空値と不正値を扱うロジック、"1.0" → int 変換の扱いなど）。
  - Look-ahead バイアス対策として fetched_at を UTC で記録。

- ニュース収集 (src/kabusys/data/news_collector.py)
  - RSS フィードから記事を収集し raw_news に保存する機能。
  - セキュリティ対策:
    - defusedxml を用いた XML パースで XML Bomb 等への対策。
    - SSRF 対応: URL スキーム検証（http/https 限定）、ホストがプライベート/ループバック/リンクローカルの場合は拒否（DNS 解決で A/AAAA を検査）。
    - リダイレクト時にスキームとホストを検証するカスタム RedirectHandler を実装。
    - 受信サイズ上限 MAX_RESPONSE_BYTES（10 MB）を導入、gzip 解凍後も検査（Gzip bomb 対策）。
  - URL 正規化:
    - トラッキングパラメータ（utm_*, fbclid 等）の除去、クエリソート、フラグメント除去。
    - 記事ID は正規化 URL の SHA-256 の先頭32文字で生成（冪等性）。
  - テキスト前処理関数 preprocess_text（URL除去、空白正規化）。
  - RSS 取得関数 fetch_rss（XML パースエラーは警告して空リスト返却、ネットワーク例外は伝播）。
  - DB 保存:
    - save_raw_news: INSERT ... RETURNING id を使い、実際に挿入された記事IDを返す。チャンク処理・1トランザクションで実行。
    - save_news_symbols / _save_news_symbols_bulk: 記事と銘柄コードの紐付けを一括保存（ON CONFLICT DO NOTHING、INSERT RETURNING を利用）。
  - 銘柄コード抽出アルゴリズム extract_stock_codes（4桁数字パターン + known_codes フィルタ、重複除去）。
  - 集約ジョブ run_news_collection: 複数ソース処理、ソース単位でエラーハンドリング、既知銘柄の紐付けを一括保存。

- DuckDB スキーマ管理 (src/kabusys/data/schema.py)
  - Raw / Processed / Feature / Execution 層のテーブル定義を網羅した DDL を提供。
  - 主要テーブル:
    - raw_prices, raw_financials, raw_news, raw_executions
    - prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - features, ai_scores
    - signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 索引（頻出クエリ向け）を複数定義。
  - init_schema(db_path) でディレクトリ自動作成後に全DDL/インデックスを実行して初期化（:memory: 対応）。
  - get_connection() を用意（スキーマ初期化は行わない）。

- ETL パイプライン (src/kabusys/data/pipeline.py)
  - ETLResult dataclass による処理結果表現（品質問題・エラーリストを含む）。
  - 差分更新のためのユーティリティ:
    - _table_exists, _get_max_date
    - get_last_price_date, get_last_financial_date, get_last_calendar_date
    - _adjust_to_trading_day（非営業日調整、market_calendar に基づく）
  - run_prices_etl の設計（差分取得、backfill_days による再取得、jq.fetch / jq.save 呼び出し、ログ出力）
  - デフォルトのバックフィル日数、カレンダー先読み等の定数を定義（_DEFAULT_BACKFILL_DAYS 等）。
  - 品質チェックモジュール（quality）との設計連携（品質問題を収集して返す方針）。

### 変更 (Changed)
- （初回リリースのため該当なし、設計方針として冪等性・リトライ・セキュリティ重視が反映されている点を記載）

### 修正 (Fixed)
- （初回リリースのため該当なし）

### セキュリティ (Security)
- news_collector:
  - defusedxml による XML パース、安全なリダイレクト検査、プライベートIP/ループバック拒否、受信サイズ制限、許可スキーム制御など複数の SSRF/DoS 対策を実装。
- jquants_client:
  - API トークンの自動リフレッシュは allow_refresh フラグで制御し、無限再帰を防止。
  - レート制限に従うことで API 制限関連の問題を回避。

### 既知の問題 / 注意点 (Known issues / Notes)
- run_prices_etl の戻り値が途中で切れている（実装ミスの可能性）。期待される戻り値は (取得レコード数, 保存レコード数) であるが、現状は保存数を返していないように見える。デプロイ前に修正・テストが必要。
- 一部関数やモジュールは外部ドキュメント（DataPlatform.md, DataSchema.md 等）に依存する設計方針を参照しているが、該当ドキュメントはソースに含まれていないため、運用時は別途ドキュメント整備が必要。
- schema の外部キー制約などは DuckDB の挙動に依存するため、移行・バージョン差分に注意。

---

作成者注: 上記は提供いただいたコードから推測してまとめた CHANGELOG です。リリースに際しては実際のコミット履歴・チケットや追加のテスト結果に基づいて項目を精査・追記してください。