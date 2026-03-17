CHANGELOG
=========

すべての変更は Keep a Changelog の形式に従って記載しています。  
バージョン番号はパッケージ内部の __version__（src/kabusys/__init__.py）に合わせています。

[Unreleased]
-------------

（なし）

[0.1.0] - 2026-03-17
-------------------

Added
- 基本パッケージ骨格を追加（kabusys パッケージ、__all__ に data/strategy/execution/monitoring を公開）。
  - ファイル: src/kabusys/__init__.py

- 環境設定管理機能を追加（Settings クラス）。
  - .env ファイルと OS 環境変数の自動読み込み機能を実装（プロジェクトルート検出: .git または pyproject.toml を基準）。
  - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - 認証トークン（JQUANTS_REFRESH_TOKEN）、kabu ステーション（KABU_API_PASSWORD, KABU_API_BASE_URL）、Slack（SLACK_BOT_TOKEN, SLACK_CHANNEL_ID）、データベースパス（DUCKDB_PATH, SQLITE_PATH）など主要設定をプロパティとして提供。
  - KABUSYS_ENV（development/paper_trading/live）・LOG_LEVEL のバリデーションを実装。
  - ファイル: src/kabusys/config.py

- J-Quants API クライアントを実装（データ取得 + DuckDB 保存ユーティリティ）。
  - レート制限ガード（固定間隔スロットリング、デフォルト 120 req/min）。
  - リトライ（指数バックオフ、最大 3 回）、HTTP 408/429/5xx にリトライ。429 の場合は Retry-After を尊重。
  - 401 を受けた場合はリフレッシュトークンから id_token を自動更新して 1 回のみリトライ。
  - 取得関数: fetch_daily_quotes（株価日足、ページネーション対応）、fetch_financial_statements（四半期財務）、fetch_market_calendar（JPX カレンダー）。
  - DuckDB 保存関数: save_daily_quotes, save_financial_statements, save_market_calendar（いずれも冪等: ON CONFLICT DO UPDATE）。
  - 取得時刻を UTC の fetched_at に記録して Look‑ahead Bias を防止。
  - 型変換ユーティリティ (_to_float, _to_int) を実装（安全な変換ポリシー）。
  - ファイル: src/kabusys/data/jquants_client.py

- ニュース収集モジュールを追加（RSS ベース）。
  - RSS フィード取得（gzip 対応）、XML パーサは defusedxml を利用して XML 攻撃を防御。
  - SSRF 対策:
    - URL スキーム検証（http/https のみ許可）。
    - リダイレクト時にスキームおよびホストのプレ検証を行うカスタムリダイレクトハンドラ。
    - ホストがプライベート/ループバック/リンクローカル/マルチキャストであれば拒否。
  - レスポンスサイズ上限の導入（MAX_RESPONSE_BYTES = 10MB）と Gzip 展開後の再検査（Gzip Bomb 対策）。
  - URL 正規化とトラッキングパラメータ除去（utm_* 等）、記事ID は正規化 URL の SHA-256 先頭 32 文字で生成し冪等性を保証。
  - テキスト前処理（URL 除去、空白正規化）。
  - DuckDB への保存:
    - save_raw_news: チャンク化して一括 INSERT、トランザクションでまとめる、INSERT ... RETURNING を使い新規挿入IDを返す（ON CONFLICT DO NOTHING）。
    - save_news_symbols / _save_news_symbols_bulk: 記事と銘柄コードの紐付けを冪等に保存（チャンク化、RETURNING により挿入数を正確に計測）。
  - 銘柄抽出機能（4桁コード、known_codes によるフィルタ、重複除去）。
  - 統合ジョブ run_news_collection を提供（各ソース独立にエラーハンドリングし継続）。
  - 既定の RSS ソースに Yahoo Finance が登録。
  - ファイル: src/kabusys/data/news_collector.py

- DuckDB スキーマ定義と初期化モジュールを追加。
  - Raw / Processed / Feature / Execution 層のテーブルを定義（raw_prices, raw_financials, raw_news, raw_executions, prices_daily, market_calendar, fundamentals, news_articles, news_symbols, features, ai_scores, signals, signal_queue, orders, trades, positions, portfolio_performance 等）。
  - 適切な型、制約（チェック制約・主キー・外部キー）を設計。
  - 頻出クエリのためのインデックス定義を含む。
  - init_schema(db_path) でディレクトリ自動作成 → テーブル／インデックス作成（冪等）を行い接続を返す。get_connection を提供。
  - ファイル: src/kabusys/data/schema.py

- ETL パイプラインのベースを追加。
  - ETLResult データクラス（結果集計、品質問題リスト、エラー一覧、JSON 変換ヘルパ）。
  - 差分更新のためのヘルパ関数（テーブル存在チェック、最終日取得 get_last_price_date / get_last_financial_date / get_last_calendar_date、営業日調整 _adjust_to_trading_day）。
  - run_prices_etl: 差分取得ロジック（最終取得日 から backfill_days を差し戻し再取得）、jquants_client を使った fetch と save を呼び出す仕組み（デフォルト backfill_days = 3、最小取得日 _MIN_DATA_DATE = 2017-01-01）。
  - ファイル: src/kabusys/data/pipeline.py

Security
- 環境変数ロード時に OS 環境変数を保護する protected セットを導入し、.env による既存値上書きを制御。
  - ファイル: src/kabusys/config.py
- ニュース収集で defusedxml を使用、SSRF/プライベートネットワークアクセスを防ぐための検査、レスポンスサイズ制限を実装。
  - ファイル: src/kabusys/data/news_collector.py

Design / Implementation notes
- J-Quants クライアントは 120 req/min のレートリミットと最大リトライ 3 回の設計を採用。Token キャッシュをモジュールレベルで保持し、ページネーション間で再利用。
  - ファイル: src/kabusys/data/jquants_client.py
- DuckDB への保存は可能な限り冪等（ON CONFLICT DO UPDATE / DO NOTHING）にして、再実行可能な ETL を目指す。
- NewsCollector の記事 ID は URL 正規化後のハッシュで生成し、トラッキングパラメータ除去による重複排除を行う。

Fixed
- （初回リリースのため該当なし）

Changed
- （初回リリースのため該当なし）

Deprecated
- （初回リリースのため該当なし）

Removed
- （初回リリースのため該当なし）

Notes / Known issues
- run_prices_etl の戻り値や ETL の細部は pipeline モジュールで継続的に拡張される想定です。実運用前に総合的なテスト（API 呼び出し、DuckDB 保存、品質チェックルーチンの統合）を推奨します。
- news_collector の既定 RSS ソースは最小構成（Yahoo Finance）。多様なソース追加や既存ソースのモニタリング・チューニングは随時必要です。
- 本リリースはデータ収集・保存・基盤スキーマ・ETL の基盤を提供する初期バージョンです。戦略実装（strategy）、発注実行（execution）、監視（monitoring）モジュールは別途実装・統合予定です。

参考ファイル一覧
- src/kabusys/__init__.py
- src/kabusys/config.py
- src/kabusys/data/jquants_client.py
- src/kabusys/data/news_collector.py
- src/kabusys/data/schema.py
- src/kabusys/data/pipeline.py
- src/kabusys/data/__init__.py
- src/kabusys/execution/__init__.py
- src/kabusys/strategy/__init__.py

（記載内容は提供されたコードベースから推測してまとめた概要です。実際のリリースノート作成時はコミットログ・Issue 等を参照のうえ調整してください。）