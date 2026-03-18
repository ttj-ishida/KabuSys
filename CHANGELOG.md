CHANGELOG
=========

すべての重要な変更はここに記録します。  
フォーマットは「Keep a Changelog」（https://keepachangelog.com/ja/1.0.0/）に準拠しています。

[Unreleased]
------------

- Known issues / TODO
  - run_prices_etl の戻り値がソースコード断片のため途中で切れており（`return len(records),` のまま）正しいタプル (fetched, saved) を返していない可能性があります。修正が必要です。
  - ETL パイプライン（pipeline モジュール）は全体設計が整っているものの、価格以外の個別ジョブ（財務・カレンダーの差分更新）や品質チェックの統合実装・エラー集約ロジックの最終確認が残っています。
  - 単体テストや統合テスト用のモックインターフェースは一部用意されている（例: news_collector._urlopen がモック可能）が、テストスイートの整備が必要。

[0.1.0] - 2026-03-18
--------------------

Added
- パッケージ初期リリース: kabusys v0.1.0
  - パッケージメタ情報: src/kabusys/__init__.py に __version__ = "0.1.0" を設定し、公開サブパッケージを定義（data, strategy, execution, monitoring）。
- 環境変数・設定管理モジュール（src/kabusys/config.py）
  - .env ファイルおよび環境変数からの設定読み込み機能を実装。
  - プロジェクトルート検出（.git または pyproject.toml を起点）により CWD に依存しない自動 .env ロードを実装。
  - .env 読み込みの優先順位: OS環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能。
  - 複数のユーティリティ（行パーサ、クォート対応、コメント処理）を実装。
  - Settings クラスを導入し、J-Quants トークンやKabu API、Slack、DBパス、環境（development/paper_trading/live）、ログレベル等のプロパティを提供。入力値検証（env/log level）を実装。
- J-Quants クライアント（src/kabusys/data/jquants_client.py）
  - API 呼び出しラッパーを提供（_request）。JSON デコードエラーハンドリング、タイムアウト、ヘッダ設定を実装。
  - レート制限を守る固定間隔スロットリング _RateLimiter を実装（120 req/min、最小インターバル計算）。
  - 冪等性と信頼性: リトライ戦略（指数バックオフ、最大試行回数）、HTTP ステータスに基づく再試行、429 の Retry-After 優先、ネットワークエラー再試行。
  - トークン管理: refresh_token からの id_token 取得、モジュールレベルのトークンキャッシュ、401 受信時の自動リフレッシュ（1 回のみ）を実装。
  - データ取得 API: fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar（ページネーション対応、pagination_key 管理）。
  - DuckDB への保存関数: save_daily_quotes, save_financial_statements, save_market_calendar（ON CONFLICT DO UPDATE による冪等保存、fetched_at を UTC で記録）。
  - 型安全な変換補助関数 _to_float / _to_int を実装（空値・不正値の扱い明示）。
- ニュース収集モジュール（src/kabusys/data/news_collector.py）
  - RSS フィードからの記事取得・前処理・DB 保存ワークフローを実装（fetch_rss、preprocess_text、save_raw_news、save_news_symbols、_save_news_symbols_bulk、run_news_collection）。
  - セキュリティ対策:
    - defusedxml を用いた XML パース（XML Bomb 等の防御）。
    - SSRF 対策: リダイレクト時のスキーム検証／内部アドレス検出（_SSRFBlockRedirectHandler、_is_private_host）、初期 URL の事前検証。
    - URL スキームは http / https のみ許可。その他スキーム（file:, mailto: 等）は拒否。
    - レスポンスサイズ制限（MAX_RESPONSE_BYTES = 10MB）と gzip 解凍後の再チェック（Gzip bomb 対策）。
    - User-Agent、Accept-Encoding ヘッダ設定、タイムアウトパラメータを使用。
  - 記事ID は URL 正規化（utm_* 等のトラッキングパラメータ除去、クエリソート）後の SHA-256 ハッシュ先頭 32 文字で生成し冪等性を確保。
  - DB 保存はチャンク分割とトランザクションで行い、INSERT ... RETURNING を使って実際に挿入された記事／ペア数を正確に取得。
  - 日本株の銘柄コード抽出ロジック（4桁数字）と既知コードセットによるフィルタリングを実装（extract_stock_codes）。
- DuckDB スキーマ定義と初期化（src/kabusys/data/schema.py）
  - Raw / Processed / Feature / Execution の各レイヤーに対応したテーブル DDL を定義。
  - raw_prices, raw_financials, raw_news, raw_executions などの Raw テーブル。
  - prices_daily, market_calendar, fundamentals, news_articles, news_symbols 等の Processed テーブル。
  - features, ai_scores などの Feature テーブル。
  - signals, signal_queue, orders, trades, positions, portfolio_performance などの Execution テーブル。
  - インデックス定義（頻出クエリ向け）と依存順を考慮したテーブル作成順を提供。
  - init_schema(db_path) によりファイル作成（親ディレクトリ自動生成）とテーブル作成を一括で行う API を提供。get_connection() で既存 DB へ接続可能。
- ETL パイプライン基盤（src/kabusys/data/pipeline.py）
  - ETLResult データクラスを導入（ターゲット日、取得件数、保存件数、品質問題、エラーの一覧などを格納）。
  - テーブル存在チェック、最大日付取得ユーティリティ、営業日調整ヘルパー（_adjust_to_trading_day）を実装。
  - 差分更新設計（最終取得日を参照して差分取得、backfill_days による後出し修正吸収の方針）を実装。
  - run_prices_etl の実装骨子（差分算出、fetch_daily_quotes 呼び出し、save_daily_quotes 保存）を追加。
- その他
  - モジュール間の責務分離とテスト容易性のための注入可能な引数（例: id_token, timeout）を多数導入。
  - ロギング（logger）を各モジュールで利用し、操作の可観測性を確保。

Security
- XML パーサに defusedxml を使用して XML 関連の攻撃を軽減。
- RSS フェッチでの SSRF 対策（スキーム検証・プライベートアドレス拒否・リダイレクト検査）。
- ネットワーク呼び出しでタイムアウト・レスポンスサイズ制限・gzip 解凍後のチェックを導入。

Fixed
- （初回リリースのため該当なし）

Changed
- （初回リリースのため該当なし）

Removed
- （初回リリースのため該当なし）

Notes / 実運用上の注意
- DuckDB ファイル（デフォルト data/kabusys.duckdb）や SQLite（data/monitoring.db）はデフォルトパスで作成されるため、運用環境では適切な場所に移すか環境変数で上書きしてください（DUCKDB_PATH / SQLITE_PATH）。
- KABUSYS_ENV、LOG_LEVEL 等に対する値検証があるため、環境変数の設定ミスは早期に検出されます。
- J-Quants や Kabu API、Slack の認証情報は必須（Settings のプロパティが _require を使っています）。開発時は .env.example を参考に .env を作成してください。

開発ロードマップ（今後予定）
- ETL pipeline の完全実装（財務データ・カレンダー差分処理、品質チェックの集約と報告フロー）。
- strategy / execution / monitoring パッケージの具体的実装（戦略生成、発注連携、監視/アラート）。
- 単体テスト・統合テストの整備（HTTP クライアント／DB のモックを含む）。
- run_prices_etl の戻り値バグ修正と追加のエラーハンドリング強化。

----- 

（注）本 CHANGELOG は提供されたソースコードの解析に基づく推測により作成しています。実際のコミット履歴ではなく、コードの実装状況・設計意図を要約したものです。