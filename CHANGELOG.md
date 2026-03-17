CHANGELOG
=========

すべての重要な変更はこのファイルに記録します。本ファイルは "Keep a Changelog" の形式に準拠しています。

Unreleased
----------

- なし

0.1.0 - 2026-03-17
------------------

Added
- パッケージ初版を追加（kabusys v0.1.0）。
  - パッケージ公開用の __version__ および __all__ を定義。
- 環境設定 (kabusys.config)
  - .env / .env.local ファイルおよび環境変数から設定を自動読み込みする仕組みを実装。
  - プロジェクトルートの探索は __file__ を起点に .git または pyproject.toml を探索することで CWD に依存しない実装を採用。
  - .env パース実装:
    - 空行・コメント行の無視、export プレフィックスのサポート。
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理と対応する閉じクォート探索。
    - クォートなしの値では inline コメント (#) をスペース/タブで判定して除去。
  - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - Settings クラスを導入し、J-Quants / kabu / Slack / DB パス / システム環境 (env, log_level) のプロパティを提供。
    - env, log_level に対するバリデーション（許容値チェック）を実装。
    - is_live / is_paper / is_dev のヘルパを提供。
- J-Quants クライアント (kabusys.data.jquants_client)
  - API 呼び出しに対する共通ユーティリティを実装:
    - 固定間隔スロットリングによるレート制限制御（120 req/min）。
    - 冪等的なページネーション取得（pagination_key を追跡してループ）。
    - リトライロジック（最大 3 回、指数バックオフ）を実装。対象ステータスは 408 / 429 / 5xx。
    - 401 受信時はリフレッシュトークンで id_token を自動リフレッシュして 1 回だけリトライ。
    - JSON デコード失敗時のエラー報告。
    - fetched_at を UTC タイムゾーンで記録して Look-ahead Bias を軽減。
  - 認証ヘルパ get_id_token を実装（refreshtoken → idToken）。
  - データ取得 API を実装:
    - fetch_daily_quotes（株価日足、ページネーション対応）
    - fetch_financial_statements（四半期財務、ページネーション対応）
    - fetch_market_calendar（JPX マーケットカレンダー）
  - DuckDB への保存関数（冪等）を実装:
    - save_daily_quotes（raw_prices テーブルへ INSERT ... ON CONFLICT DO UPDATE）
    - save_financial_statements（raw_financials）
    - save_market_calendar（market_calendar）
  - 値変換ユーティリティ _to_float / _to_int を追加（空値・不正値に対する安全な変換、_to_int は "1.0" のような文字列を float 経由で変換し、小数部が0以外なら None を返すことで意図しない切り捨てを防止）。
- ニュース収集モジュール (kabusys.data.news_collector)
  - RSS フィードからのニュース収集と DuckDB 保存を実装（DataPlatform.md に準拠）。
  - セキュリティ対策:
    - defusedxml を用いた XML パース（XML Bomb 等への対策）。
    - URL スキーム検証（http/https のみ許可）と SSRF 対策（リダイレクト先のスキーム・ホスト検証）。
    - ホストがプライベート / ループバック / リンクローカル / マルチキャストかを判定し内部アドレスへのアクセスをブロック。
    - レスポンス受信サイズ上限（MAX_RESPONSE_BYTES = 10MB）を導入しメモリ DoS を抑止。gzip 解凍後もサイズチェックを実行。
  - URL 正規化とトラッキングパラメータ除去:
    - _normalize_url によりスキーム・ホストの小文字化、utm_* 等の traking パラメータ除去、フラグメント削除、クエリのキー順ソートを実施。
    - 記事ID は正規化 URL の SHA-256 ハッシュ先頭 32 文字で生成（冪等性確保）。
  - RSS パース／前処理:
    - fetch_rss: channel/item の探索、title/content の前処理（URL 除去・空白正規化）、pubDate のパース（UTC に正規化）。
  - DB 保存:
    - save_raw_news: INSERT ... ON CONFLICT DO NOTHING RETURNING id を利用し、実際に挿入された記事 ID のリストを返す。チャンク分割と単一トランザクションでの保存。
    - save_news_symbols / _save_news_symbols_bulk: news_symbols テーブルへの記事⇆銘柄紐付けを一括保存（ON CONFLICT DO NOTHING RETURNING で正確な挿入数を返す）。
  - 銘柄コード抽出:
    - extract_stock_codes によりテキスト中の 4 桁数字候補を検出し、known_codes に基づいてフィルタ（重複除去）。
  - run_news_collection: RSS ソースごとに独立して取得・保存し、既知銘柄が与えられれば新規挿入記事に対して一括で銘柄紐付けを実行（ソース単位で例外処理）。
- スキーマ定義 (kabusys.data.schema)
  - DuckDB のスキーマを定義（Raw / Processed / Feature / Execution の 3 層/4 層構造に準拠）。
  - 主なテーブル:
    - raw_prices, raw_financials, raw_news, raw_executions
    - prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - features, ai_scores
    - signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各テーブルに PRIMARY KEY / CHECK / FOREIGN KEY 制約を付与しデータ整合性を担保。
  - 頻出クエリ向けに多数の INDEX を作成（例: idx_prices_daily_code_date, idx_signal_queue_status など）。
  - init_schema(db_path) によりディレクトリ作成 → 全DDL・インデックスの適用を行い DuckDB 接続を返す。get_connection は既存 DB への接続を返す（初期化は行わない）。
- ETL パイプライン (kabusys.data.pipeline)
  - ETLResult データクラスを導入（ETL の対象日、取得/保存件数、品質チェック結果、エラー一覧などを格納）。
  - 品質チェックの重大度を扱うプロパティ（has_quality_errors 等）。
  - DB の最終取得日取得ユーティリティ _get_max_date, get_last_price_date, get_last_financial_date, get_last_calendar_date を実装。
  - 市場カレンダーを利用した営業日調整ヘルパ _adjust_to_trading_day を実装（最長 30 日遡る検索）。
  - run_prices_etl を実装（差分更新・backfill_days による後出し修正吸収の方針、jq.fetch_daily_quotes + jq.save_daily_quotes を利用）。

Security
- RSS/HTTP 周りで複数の堅牢化を実装（defusedxml, SSRF 軽減, レスポンスサイズ制限、gzip 解凍時のサイズ検査）。
- 環境変数の自動読み込みは保護された OS 環境変数を上書きしない実装（override/protected の扱い）。

Internal / other
- ログ出力ポイントを多く設け、処理状況や警告（サイズ超過・XML パース失敗・PK 欠損スキップ等）を記録。
- モジュールレベルでの id_token キャッシュを導入し、ページネーション間でのトークン再利用を最適化。
- 一部パッケージ（kabusys.execution, kabusys.strategy, kabusys.data）に __init__ プレースホルダを用意。

Known issues / Notes
- run_prices_etl の戻り値が不完全:
  - 現在の run_prices_etl の末尾は "return len(records)," のようにタプルの 2 要素目が欠けており、意図した (fetched, saved) の戻り値を返していません。修正が必要です（第二要素は jq.save_daily_quotes の戻り値 saved を返す想定）。
- execution/strategy パッケージの __init__ は空であり、発注ロジックや戦略本体は未実装／未公開。
- 一部のエラーケースで明示的な型やメッセージの整備が今後望まれる（例: HTTP エラー時の例外ラッピングや詳細ログの拡充）。
- news_collector のホスト名解決失敗時は安全側（非プライベート）として扱う設計だが、運用上のポリシーに応じて変更を検討可能。

References / Implementation notes
- API レート制限: 120 req/min（_MIN_INTERVAL_SEC = 60 / 120）。
- ニュース受信上限: 10 MB（MAX_RESPONSE_BYTES）。
- 記事ID: 正規化 URL の SHA-256 ハッシュ先頭 32 文字。
- DuckDB の冪等保存: INSERT ... ON CONFLICT DO UPDATE / DO NOTHING を多用。

--- 

今後のリリース予定（例）
- run_prices_etl の戻り値修正と ETLResult を用いた監査ログ出力の統合。
- execution（発注）モジュールの実装、kabu API 統合テスト。
- 品質チェックモジュール (kabusys.data.quality) の実装と ETL パイプラインへの組み込み。