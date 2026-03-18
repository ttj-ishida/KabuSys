Keep a Changelog
=================

すべての重要な変更点をこのファイルに記録します。  
このプロジェクトでは Keep a Changelog の形式に準拠します。

変更履歴
-------

### [0.1.0] - 2026-03-18
初回公開リリース。

主な追加機能・実装内容
- パッケージ基礎
  - パッケージメタ情報を追加（kabusys.__version__ = "0.1.0"）。
  - 公開サブパッケージ: data, strategy, execution, monitoring（__all__ 指定）。

- 設定 / 環境読み込み (kabusys.config)
  - .env ファイルまたは環境変数から設定を自動読み込み（プロジェクトルートは .git / pyproject.toml を探索して特定）。
  - 自動ロードを無効化する環境変数: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - .env 読み込みの優先順位: OS 環境変数 > .env.local > .env（.env.local は上書き）。
  - .env 行パーサを実装（export プレフィックス対応、クォート中のエスケープ、インラインコメント処理など）。
  - 環境変数の保護（既存 OS 環境変数を保護する protected 機構）。
  - Settings クラスを提供し、必須環境変数に対して _require() による明示的エラーを返す:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等を想定。
  - 環境値検証:
    - KABUSYS_ENV は development / paper_trading / live のみ許可。
    - LOG_LEVEL は DEBUG/INFO/WARNING/ERROR/CRITICAL のみ許可。
  - デフォルトファイルパス設定（DuckDB, SQLite 等）を Path 型で提供。

- J-Quants クライアント (kabusys.data.jquants_client)
  - API クライアントを実装。取得対象:
    - 株価日足（OHLCV）、財務データ（四半期 BS/PL）、JPX マーケットカレンダー。
  - レート制御: 固定間隔スロットリングで 120 req/min（_RateLimiter）。
  - リトライ戦略:
    - 最大リトライ 3 回、指数バックオフ（base=2.0）。
    - HTTP 408/429/5xx をリトライ対象に設定。
    - 429 の場合は Retry-After ヘッダを優先して待機。
  - 401 Unauthorized を受けた場合、自動で refresh token から id_token を再取得して 1 回だけリトライ（無限再帰を防止）。
  - ページネーション対応（pagination_key を追跡しループ継続）。
  - 取得時刻（fetched_at）を UTC ISO8601 形式で記録して look-ahead bias を防止。
  - DuckDB への保存関数は冪等性を確保（INSERT ... ON CONFLICT DO UPDATE）:
    - save_daily_quotes -> raw_prices
    - save_financial_statements -> raw_financials
    - save_market_calendar -> market_calendar
  - 型変換ユーティリティ: _to_float, _to_int（安全に None を返す挙動を持つ）。
  - get_id_token()（refresh token から idToken を取得）を実装。

- ニュース収集 (kabusys.data.news_collector)
  - RSS フィード取得と raw_news への保存処理を実装。
  - 設計上の特徴:
    - defusedxml を使用して XML Bomb 等の攻撃対策を実施。
    - SSRF 対策:
      - URL スキーム検証（http/https のみ許可）。
      - リダイレクト時にスキームとホスト/IP を検証する専用ハンドラ（_SSRFBlockRedirectHandler）。
      - ホスト名の DNS 解決後に A/AAAA レコードをチェックし、プライベート/ループバック/リンクローカル/マルチキャストアドレスへのアクセスを拒否。
    - レスポンスサイズ制限（MAX_RESPONSE_BYTES = 10 MB、gzip 解凍後もチェック）でメモリ DoS を防止。
    - トラッキングパラメータ（utm_*, fbclid, gclid, ref_, _ga）を除去して URL を正規化。
    - 正規化 URL の SHA-256 ハッシュ（先頭32文字）を記事IDとして生成し冪等性を担保。
    - テキスト前処理（URL 除去、空白正規化）。
    - DB 保存はトランザクションで一括処理し、INSERT ... RETURNING を利用して実際に挿入された ID/件数を返す。
  - 提供関数:
    - fetch_rss(url, source, timeout): RSS 取得・パース -> NewsArticle リスト返却。
    - save_raw_news(conn, articles): raw_news にチャンク挿入、挿入された記事IDのリストを返す。
    - save_news_symbols(conn, news_id, codes): news_symbols に紐付けを保存（RETURNING で挿入数を返す）。
    - _save_news_symbols_bulk(): 複数記事分の一括保存（重複排除、チャンク挿入）。
    - extract_stock_codes(text, known_codes): 4 桁数字（日本株）を抽出して known_codes に含まれるものだけを返す。
    - run_news_collection(conn, sources=None, known_codes=None, timeout=30): 複数ソースから収集→保存→銘柄紐付けを実行（ソース毎にエラーハンドリングし継続）。

- スキーマ定義 / 初期化 (kabusys.data.schema)
  - DuckDB のスキーマを DataSchema.md に基づき実装（Raw / Processed / Feature / Execution 層）。
  - 主なテーブル（抜粋）:
    - Raw: raw_prices, raw_financials, raw_news, raw_executions
    - Processed: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature: features, ai_scores
    - Execution: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各種制約（PRIMARY KEY, CHECK, FOREIGN KEY）と想定データ品質チェックをDDLレベルで定義。
  - 頻出クエリを考慮したインデックスを作成（例: idx_prices_daily_code_date, idx_signal_queue_status 等）。
  - init_schema(db_path) で DB ファイルの親ディレクトリを自動作成し、全テーブルとインデックスを作成（冪等）。
  - get_connection(db_path) を提供（スキーマ初期化は行わない）。

- ETL パイプライン (kabusys.data.pipeline)
  - ETLResult データクラスを実装し、ETL 実行結果（取得数、保存数、品質問題、エラー等）を記録可能。
  - 差分更新方針:
    - デフォルトで差分更新（最終取得日からの未取得分のみ取得）。
    - backfill_days により最終取得日の数日前から再取得して API の後出し修正を吸収（デフォルト 3 日）。
    - 市場カレンダーの先読み: _CALENDAR_LOOKAHEAD_DAYS = 90。
    - データ最古開始日: _MIN_DATA_DATE = 2017-01-01（初回ロード時に使用）。
  - テーブル存在チェック、最大日付取得ユーティリティを提供（_table_exists, _get_max_date）。
  - trading day 調整ヘルパー（非営業日→直近営業日に調整）。
  - run_prices_etl()（差分 ETL の骨子を実装。fetch -> save の流れを実現）。

改善点 / 実装上の注意
- すべての DB 書き込みは可能な限り冪等に実装（ON CONFLICT DO UPDATE / DO NOTHING）し、複数回実行しても状態が壊れにくい設計。
- ネットワーク/HTTP 周りはタイムアウト・retry・backoff・rate limit を組み合わせて堅牢性を高めている。
- ニュース取得での外部入力は defusedxml / SSRF 検査 / レスポンスサイズ制限により安全性を考慮。
- 設定周りはプロジェクトルート探索によりワークディレクトリに依存せず動作することを意図。

セキュリティ
- XML パースに defusedxml を利用して XML Bomb 等を軽減。
- RSS フェッチで SSRF 対策を実装（スキーム検証、リダイレクト検査、プライベートアドレス拒否）。
- URL 正規化でトラッキングパラメータを除去し ID を決定するため、同一コンテンツの重複挿入を抑制。

既知の未実装/注意事項
- pipeline.run_prices_etl の実装は骨子ができているが（ファイル上の抜粋）、完全な ETL ワークフロー（品質チェックの呼び出し等）や他の ETL ジョブ（財務・カレンダーの完全な差分処理など）は今後の整備対象。
- strategy, execution, monitoring サブパッケージの具体的実装は今回のリリースでは未実装または空の __init__ のみ。

互換性
- 初回リリース（0.1.0）につき後方互換性の概念は現時点で該当なし。今後の変更はこの CHANGELOG に記録予定。

ライセンス・その他
- 各種外部ライブラリ（duckdb, defusedxml 等）を使用。導入時にはそれらのライセンスを確認してください。

問い合わせ・貢献
- バグ報告や改善提案は issue を立ててください。README や DataPlatform.md / DataSchema.md 等の設計文書に従って PR を歓迎します。