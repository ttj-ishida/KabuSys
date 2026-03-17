CHANGELOG
=========

すべての重要な変更は Keep a Changelog の形式に従って記載しています。  
このファイルでは、リリースごとの追加・変更・修正点を日本語でまとめています。

フォーマット:
- Added: 新機能
- Changed: 既存機能の変更
- Fixed: バグ修正
- Security: セキュリティ関連の改善（該当時のみ）

[0.1.0] - 2026-03-17
-------------------

Added
- 基本パッケージの初期実装を追加（kabusys v0.1.0）
  - パッケージトップ: src/kabusys/__init__.py にてバージョンと主要モジュールを公開。

- 環境設定管理モジュールを追加（src/kabusys/config.py）
  - .env ファイルおよび環境変数から設定を自動ロードする機能を実装。
  - 自動ロードの優先順位: OS環境変数 > .env.local > .env。
  - 開発時・テスト時の無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD=1。
  - プロジェクトルート検出ロジック: .git または pyproject.toml を基準（__file__ 基点の親探索で CWD 非依存）。
  - .env パーサ実装:
    - export KEY=val 形式対応
    - シングル/ダブルクォート対応（バックスラッシュエスケープをサポート）
    - インラインコメントの取り扱い（クォートあり/なしの違いを考慮）
  - 環境値のバリデーション/必須チェックを提供する Settings クラス:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID など必須項目をプロパティで取得（未設定時は ValueError）。
    - KABU_API_BASE_URL, DUCKDB_PATH, SQLITE_PATH 等のデフォルト値を定義。
    - KABUSYS_ENV（development, paper_trading, live）と LOG_LEVEL の検証ロジック。
    - is_live / is_paper / is_dev のヘルパープロパティ。

- J-Quants API クライアントを実装（src/kabusys/data/jquants_client.py）
  - API からのデータ取得:
    - 株価日足（fetch_daily_quotes）
    - 財務データ（fetch_financial_statements）
    - JPX マーケットカレンダー（fetch_market_calendar）
  - 設計上の特徴:
    - レート制限（120 req/min）を守る固定間隔スロットリング実装（_RateLimiter）。
    - リトライロジック（指数バックオフ、最大 3 回）。HTTP 408/429 と 5xx に対する再試行。
    - 401 応答時は自動でリフレッシュトークンから id_token を取得して 1 回だけ再試行。
    - モジュールレベルで ID トークンキャッシュを保持し、ページネーション間で共有。
    - レスポンスを JSON としてパースし、デコード失敗時に明確な例外を投げる。
  - DuckDB への冪等保存関数を提供:
    - save_daily_quotes: raw_prices に ON CONFLICT DO UPDATE で保存（PK: date, code）。PK 欠損行はスキップしてログ出力。
    - save_financial_statements: raw_financials に保存（ON CONFLICT DO UPDATE、PK: code, report_date, period_type）。
    - save_market_calendar: market_calendar に保存（ON CONFLICT DO UPDATE）。
    - 保存時に fetched_at を UTC ISO8601（Z）形式で記録。
  - 数値変換ユーティリティ:
    - _to_float / _to_int（空値・不正値を None に変換。float 文字列を int に変換する際の安全チェック等）。

- ニュース収集モジュールを追加（src/kabusys/data/news_collector.py）
  - RSS フィードからの記事収集と DuckDB への保存ワークフローを実装。
  - 主な機能:
    - fetch_rss: RSS フィードの取得、XML パース、記事抽出（title, description/content:encoded, link/guid, pubDate）。
    - preprocess_text: URL 除去と空白正規化。
    - URL 正規化と記事 ID 生成: _normalize_url と _make_article_id（トラッキングパラメータ除去、SHA-256 の先頭32文字を ID に使用）で冪等性を確保。
    - 保護対策: defusedxml を使用した XML パース、SSRF 防止（スキーム検証・ホストがプライベートアドレスかの判定・リダイレクト時検査）、レスポンスサイズ制限（MAX_RESPONSE_BYTES、10MB）、gzip 解凍後のサイズ再検査。
    - DB 保存:
      - save_raw_news: INSERT ... ON CONFLICT DO NOTHING RETURNING id を用いて新規挿入 ID を返す（チャンク分割、トランザクションまとめ）。
      - save_news_symbols / _save_news_symbols_bulk: 記事と銘柄コードの紐付けを保存（ON CONFLICT DO NOTHING RETURNING 1、チャンク・トランザクション処理）。
    - 銘柄抽出: extract_stock_codes（本文から 4 桁数字を抽出し、与えられた known_codes セットに基づきフィルタ）。
    - run_news_collection: 複数 RSS ソースを巡回して記事取得→保存→銘柄紐付けを実行。ソース単位で堅牢にエラーハンドリング（1ソース失敗でも他を継続）。
    - デフォルト RSS ソースに Yahoo Finance のカテゴリフィードを設定。

- DuckDB スキーマ定義・初期化モジュールを追加（src/kabusys/data/schema.py）
  - Raw / Processed / Feature / Execution の 3 層＋実行層に対応するテーブル群を定義。
  - 主なテーブル:
    - raw_prices, raw_financials, raw_news, raw_executions
    - prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - features, ai_scores
    - signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 制約・チェック付きカラム（NULL/NOT NULL、CHECK、PRIMARY/FOREIGN KEY）を定義。
  - インデックスを頻出クエリパターンに合わせて作成。
  - init_schema(db_path) によりフォルダ作成→DuckDB接続→テーブル/インデックス作成（冪等）。
  - get_connection(db_path) にて既存 DB への接続を提供（スキーマ初期化は行わない）。

- ETL パイプラインの基礎を追加（src/kabusys/data/pipeline.py）
  - ETLResult データクラス: ETL 実行結果（取得数、保存数、品質問題、エラー等）を集約して返す。
  - 差分更新ユーティリティ:
    - _table_exists, _get_max_date により既存最終日を取得。
    - get_last_price_date, get_last_financial_date, get_last_calendar_date ヘルパー実装。
    - _adjust_to_trading_day: 非営業日を直近営業日に調整（market_calendar を利用）。
  - run_prices_etl の基礎実装:
    - 差分計算（最終取得日から backfill_days を考慮）に基づいて fetch/save を実行する設計。
    - 初回ロードは最小日付（2017-01-01）から取得する仕様。
    - 取得したレコード数と保存数をログ出力して返却する想定（実装の一部が続く設計）。

Changed
- （初期リリースのため該当なし）

Fixed
- （初期リリースのため該当なし）

Security
- ニュース収集・RSS ハンドリングにおける多数のセキュリティ対策を導入:
  - defusedxml を用いた XML パースで XML BOM 攻撃等を回避。
  - SSRF 対策:
    - URL スキーム検証（http/https のみ許可）。
    - ホストがプライベート/ループバック/リンクローカル/マルチキャストでないことを検査（直接 IP または DNS 解決で判定）。
    - リダイレクト発生時にもスキーム・ホスト検証を行うカスタムリダイレクトハンドラを導入。
  - レスポンス最大サイズ制限（10MB）および gzip 解凍後のサイズ再チェックでメモリ DoS を軽減。

Notes / Migration
- DuckDB スキーマは init_schema() で作成されるため、既存 DB がない状態で init_schema を呼び出してください。既存テーブルがある場合は冪等でスキップされます。
- 環境変数は Settings を通じて参照することを推奨します。必須設定が未定義だと ValueError が発生します。
- J-Quants API の認証にはリフレッシュトークンが必要です（環境変数 JQUANTS_REFRESH_TOKEN を設定）。

今後の予定（未実装/検討中）
- ETL pipeline の品質チェックモジュール（quality）の詳細実装。
- run_prices_etl の残りロジック（戻り値の整備など）とその他 ETL ジョブの完成（財務データ・カレンダー等の差分 ETL）。
- execution / strategy / monitoring パッケージ内の各実装（現在はパッケージ空ファイルを配置）。
- テストカバレッジの追加（特にネットワーク周り・SSRF 対策・.env パーサ）。

以上。