# CHANGELOG

すべての変更は Keep a Changelog の形式に従っています。  
このプロジェクトの初版リリースを記録しています。

## [0.1.0] - 2026-03-17

### Added
- パッケージ初期リリース "KabuSys" を追加。
  - パッケージメタ情報: src/kabusys/__init__.py に __version__ = "0.1.0"、公開サブパッケージを __all__ に定義（data, strategy, execution, monitoring）。

- 環境設定管理モジュール（src/kabusys/config.py）
  - .env ファイルまたは環境変数から設定を読み込む自動ローダーを実装。
    - 読み込み優先順位: OS環境変数 > .env.local > .env。
    - プロジェクトルート検出は .git または pyproject.toml を基準に行い、CWD に依存しない方式を採用。
    - 自動ロードを無効化するための環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - .env パーサの強化:
    - export KEY=val 形式に対応。
    - シングル/ダブルクォート内のバックスラッシュエスケープを考慮した解析。
    - コメント取り扱い（クォート外の # の扱い等）の取り扱いを実装。
  - 環境変数取得ヘルパー _require と型安全な Settings クラスを提供。
    - J-Quants / kabuステーション / Slack / DB パス 等のプロパティを定義。
    - KABUSYS_ENV（development/paper_trading/live）および LOG_LEVEL の検証ロジックを追加。

- J-Quants API クライアント（src/kabusys/data/jquants_client.py）
  - データ取得機能:
    - 株価日足（fetch_daily_quotes）、財務データ（fetch_financial_statements）、JPX マーケットカレンダー（fetch_market_calendar）の取得をページネーション対応で実装。
  - リクエスト基盤:
    - 固定間隔スロットリングによるレート制限（120 req/min）を _RateLimiter で実装。
    - 再試行（指数バックオフ、最大 3 回）を実装。対象ステータス（408、429、5xx）でリトライ。
    - 401 受信時は ID トークンを自動リフレッシュして 1 回だけ再試行する仕組みを実装（無限再帰回避）。
    - get_id_token によるリフレッシュトークン→IDトークン取得を実装。
    - モジュールレベルの ID トークンキャッシュを導入（ページネーション間で共有）。
  - DuckDB への保存:
    - save_daily_quotes / save_financial_statements / save_market_calendar を実装。
    - 冪等性を担保するため INSERT ... ON CONFLICT DO UPDATE を使用し、重複を排除して更新する実装。
  - ユーティリティ関数:
    - _to_float / _to_int（厳密な変換ルールを実装。例: "1.0" を int 化するが小数部が非ゼロの float 文字列は None を返す）やログ出力を備える。
  - ロギング: 取得件数・保存件数等の情報をログ出力。

- ニュース収集モジュール（src/kabusys/data/news_collector.py）
  - RSS フィードからのニュース収集と DuckDB への保存処理を実装。
    - デフォルト RSS ソース（Yahoo Finance）を定義。
    - fetch_rss: URL 正規化、コンテンツの前処理（URL 除去、空白正規化）、gzip 解凍対応、Content-Length と受信サイズ上限チェック（10MB）、XML パース（defusedxml を使用）など堅牢な取得処理を実装。
    - セキュリティ対策: SSRF 転送防止のためリダイレクト先のスキーム・ホストを検査する _SSRFBlockRedirectHandler と事前検証ロジックを導入。http/https 以外のスキームを拒否。
    - URL 正規化と記事 ID 生成: トラッキングパラメータ（utm_ 等）を除去してソートしたクエリで正規化し、SHA-256 の先頭 32 文字を記事 ID として生成（冪等性確保）。
    - save_raw_news: チャンク（デフォルト 1000）でトランザクション単位に INSERT ... ON CONFLICT DO NOTHING RETURNING id を使用し、実際に挿入された記事 ID のリストを返す実装。トランザクション失敗時はロールバック。
    - save_news_symbols / _save_news_symbols_bulk: 記事と銘柄コードの紐付けを一括で保存（ON CONFLICT DO NOTHING RETURNING を利用）する処理を実装。
    - extract_stock_codes: 正規表現ベースで 4 桁銘柄コード候補を抽出し、与えられた known_codes セットと照合して一意なコードを返す。
    - run_news_collection: 全ソースに対する統合収集ジョブを実装。各ソースの失敗は他ソースに影響を与えないよう個別にエラーハンドリング。既知銘柄が与えられた場合は新規挿入記事に対して銘柄紐付けを一括保存。

- DuckDB スキーマ定義と初期化（src/kabusys/data/schema.py）
  - DataSchema.md に基づき、Raw / Processed / Feature / Execution 層のテーブル DDL を網羅的に定義。
    - raw_prices, raw_financials, raw_news, raw_executions
    - prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - features, ai_scores
    - signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各テーブルに適切な制約（PRIMARY KEY, CHECK, FOREIGN KEY）を付与。
  - 頻出クエリに備えたインデックス群を定義。
  - init_schema(db_path) で親ディレクトリの自動作成、全DDLおよびインデックスを実行して初期化済み DuckDB 接続を返す機能を提供。get_connection は既存DBへ接続するユーティリティ。

- ETL パイプライン基盤（src/kabusys/data/pipeline.py）
  - ETLResult データクラスを導入して ETL 実行結果（取得件数、保存件数、品質問題、エラー等）を構造化して返却可能に。
  - 差分更新ヘルパー: _table_exists, _get_max_date, get_last_price_date, get_last_financial_date, get_last_calendar_date を実装。
  - 市場カレンダー補助: _adjust_to_trading_day（非営業日の調整ロジック）を実装。
  - run_prices_etl を実装（差分更新ロジック、バックフィル日数、_MIN_DATA_DATE を使用）。J-Quants から差分取得して保存する流れを実装（fetch -> save）。ログ出力あり。
  - 設計指針: 差分更新、backfill_days による後出し修正吸収、品質チェックモジュールとの分離（quality モジュール呼び出しは想定）などを採用。

- テスト容易性・運用性のための考慮
  - ニュース収集の _urlopen を差し替え可能にしてユニットテストでのモックを容易に。
  - ロギングを各所に追加して監査・デバッグを容易に。

### Security
- XML を defusedxml でパースして XML Bomb 等の脆弱性を軽減。
- RSS フィード取得時に SSRF 対策を実装:
  - HTTP リダイレクト先のスキーム検査と内部アドレス（プライベート/ループバック/リンクローカル/マルチキャスト）へのアクセス拒否。
  - fetch_rss の事前ホストチェックと最終 URL の二重検証。
- ネットワーク系の入力（URL）のスキーム検証を強化（http/https のみ許可）。

### Performance
- J-Quants API 呼び出しに対して固定間隔スロットリング（120 req/min）を導入し、API レート制限を厳守する設計。
- 大量の DB INSERT をチャンク化してトランザクションをまとめ、オーバーヘッドを削減。
- DuckDB 側での ON CONFLICT による冪等保存を用いて再実行コストを低減。

### Notes / Implementation details
- API 再試行ロジック:
  - 408/429/5xx 系を対象に最大 3 回の指数バックオフリトライを実行。429 の場合は Retry-After ヘッダを尊重。
  - 401 は ID トークン刷新を 1 回だけ行い再試行する。
- .env パーサは複雑な引用符/エスケープ/コメントのケースに堅牢に対応。
- DuckDB の日時・日付カラム取り扱いで変換を行っており、保存時には取得時刻（fetched_at）を UTC ISO 8601 形式で記録。

### Breaking Changes
- 初期リリースのため該当なし。

### Deprecated
- なし

### Removed
- なし

---

もしリリース日やバージョニングの取り扱いを別途指定したい場合や、CHANGELOG に追記してほしい具体的な変更点（例えば追加の ETL ジョブや strategy/execution/monitoring の実装予定など）があれば教えてください。