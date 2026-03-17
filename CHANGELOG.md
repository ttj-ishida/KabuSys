CHANGELOG
=========

すべての重要な変更点はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠しています。  

リリースはセマンティックバージョニングに従います。

Unreleased
----------

（今後の変更をここに記載します）

0.1.0 - 2026-03-17
-----------------

Added
- パッケージ初期リリース。パッケージ名: kabusys、バージョン: 0.1.0。
  - src/kabusys/__init__.py にて公開モジュール（data, strategy, execution, monitoring）を定義。

- 環境変数・設定管理（src/kabusys/config.py）
  - プロジェクトルート（.git または pyproject.toml）を基準に .env ファイルを自動検出して読み込みする仕組みを実装。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化対応。
  - .env の行パーサー実装:
    - export KEY=val 形式対応、シングル/ダブルクォート対応、バックスラッシュエスケープ処理、インラインコメント処理等。
    - 読み込みエラー時は警告を出す（warnings.warn）。
  - Settings クラスを提供し、以下の設定プロパティを環境変数から取得:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
    - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）、SQLITE_PATH（デフォルト: data/monitoring.db）
    - KABUSYS_ENV（development/paper_trading/live の検証）および LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL の検証）
    - is_live / is_paper / is_dev のヘルパープロパティ

- J-Quants API クライアント（src/kabusys/data/jquants_client.py）
  - 基本設計: レート制限（120 req/min）を遵守、リトライ（指数バックオフ、最大3回）、401 発生時のトークン自動リフレッシュ、取得時刻（fetched_at）を UTC で記録、DuckDB への冪等保存をサポート。
  - レートリミッタ（固定間隔スロットリング）実装。
  - HTTP リクエストラッパー:
    - JSON デコードエラーハンドリング、リトライ対象ステータス（408, 429, 5xx）、429 の場合は Retry-After ヘッダ優先。
    - 401 は一度だけトークンをリフレッシュして再試行（無限再帰防止のため allow_refresh フラグ）。
  - get_id_token(refresh_token=None) 実装（/token/auth_refresh へ POST）。
  - ページネーション対応の取得関数:
    - fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
  - DuckDB への保存関数（冪等動作）:
    - save_daily_quotes（raw_prices に ON CONFLICT DO UPDATE）
    - save_financial_statements（raw_financials に ON CONFLICT DO UPDATE）
    - save_market_calendar（market_calendar に ON CONFLICT DO UPDATE）
  - 値変換ユーティリティ: _to_float, _to_int（"1.0" などの float 表現を適切に扱い、小数部が非0であれば変換を避ける）

- ニュース収集モジュール（src/kabusys/data/news_collector.py）
  - RSS フィードからの記事収集と DuckDB への保存を実装（設計に基づくセキュリティ対策・性能対策を多数導入）。
  - セキュリティ・堅牢性:
    - defusedxml を利用して XML Bomb 等を防止。
    - SSRF 対策: URL スキーム検証（http/https のみ許可）、プライベート/ループバック/リンクローカル/マルチキャストアドレスの拒否（DNS 解決による A/AAAA 検査）、リダイレクト時にも検証するカスタム RedirectHandler 実装。
    - 受信サイズ上限（MAX_RESPONSE_BYTES = 10MB）と gzip 解凍後のサイズチェック（Gzip bomb 対策）。
  - URL 正規化:
    - トラッキングパラメータ（utm_*, fbclid など）削除、スキーム/ホスト小文字化、クエリソート、フラグメント除去。
    - 正規化後の URL から SHA-256（先頭32文字）で記事 ID を生成して冪等性を確保。
  - RSS パースと前処理:
    - content:encoded 優先、description フォールバック、タイトル/本文の URL 除去・空白正規化（preprocess_text）、pubDate の RFC2822 パース（失敗時は警告して現在時刻を代替）。
  - DB 保存とバルク処理:
    - save_raw_news: INSERT ... ON CONFLICT DO NOTHING RETURNING id を用い、チャンク毎にトランザクションで挿入して実際に挿入された記事IDリストを返す。
    - save_news_symbols / _save_news_symbols_bulk: 記事と銘柄コードの紐付けをバルクで挿入（ON CONFLICT DO NOTHING、INSERT ... RETURNING で挿入数を正確に把握）。
  - 銘柄コード抽出: 4桁数字を正規表現で抽出し、既知コードセットでフィルタ（重複除去）。
  - run_news_collection: 複数 RSS ソースの収集ジョブ。ソース単位で失敗を隔離して他ソースを継続、既知コードがあれば新規記事に対してコード紐付けを一括挿入。

- DuckDB スキーマ定義・初期化（src/kabusys/data/schema.py）
  - Raw / Processed / Feature / Execution の 3 + Execution レイヤーにわたるテーブル定義を実装（raw_prices, raw_financials, raw_news, raw_executions, prices_daily, market_calendar, fundamentals, news_articles, news_symbols, features, ai_scores, signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance）。
  - 各テーブルに NOT NULL/チェック制約/主キー/外部キー を付与。
  - 頻出クエリ用のインデックスを作成（例: idx_prices_daily_code_date, idx_signal_queue_status 等）。
  - init_schema(db_path) によりディレクトリ自動作成・全DDL適用の上で DuckDB 接続を返す。get_connection(db_path) で既存DBへ接続のみ可能。

- ETL パイプライン（src/kabusys/data/pipeline.py）
  - ETL の設計に基づく差分更新パターンを実装。
  - ETLResult データクラスを導入（対象日、取得数/保存数、品質問題リスト、エラーリスト等を保持）。品質問題を辞書化する to_dict を提供。
  - 市場カレンダー補助: _adjust_to_trading_day（非営業日の場合、過去の直近営業日に調整するロジック）を実装。
  - 差分確認ユーティリティ: get_last_price_date, get_last_financial_date, get_last_calendar_date（テーブル存在チェックと MAX 日付取得を行う）。
  - run_prices_etl を実装（差分更新ロジック、backfill_days による再取得、jq.fetch_daily_quotes と jq.save_daily_quotes を利用して取得→保存を実行）。（注意: run_prices_etl の戻り値定義がコード途中までのため、このリリースでは基本的な差分取得/保存フローを提供）

Changed
- 初回リリースのため該当なし。

Fixed
- 初回リリースのため該当なし。

Deprecated
- 初回リリースのため該当なし。

Removed
- 初回リリースのため該当なし。

Security
- RSS パーサーに defusedxml を採用、SSRF 対策（スキーム/ホスト検証、リダイレクト検査、プライベートIP拒否）、レスポンスサイズおよび gzip 解凍後のサイズ検査など、多層の防御を導入しました。
- J-Quants クライアントはトークンの取り扱いで失効検知（401）後に自動的にリフレッシュする実装をしており、無限再帰を防止する制御も組み込まれています。

Notes / Known limitations
- strategy, execution, monitoring パッケージの具体的な実装はこのリリースでは空の __init__ モジュールのみ（骨組みを提供）。戦略ロジックや発注エンジンは今後拡張予定。
- run_prices_etl の戻り値や一部の処理はソースの途中で切れているため、ETL の詳細な品質チェック連携（quality モジュールとの統合など）は追加実装が必要。
- テストコードは含まれていません。ネットワーク、DB操作、外部APIのスタブ/モックを用いた単体テスト追加を推奨します。
- DuckDB の SQL 実行に生SQL文字列を埋め込む箇所があるため（主に動的プレースホルダ生成）、将来的に SQL インジェクション耐性（入力検証）やプリペアドステートメントの更なる強化を検討してください。

作者
- 初期実装: KabuSys チーム（コードベースから推測）

-- end --