CHANGELOG
=========

すべての注目すべき変更はここに記録します。  
このファイルは Keep a Changelog の形式に従っています。公表済みの変更はバージョンごとに分けて記載しています。

Unreleased
----------

- （なし）

0.1.0 - 2026-03-17
------------------

Added
- パッケージ初期リリースを追加（kabusys v0.1.0）。
  - src/kabusys/__init__.py にバージョンと公開モジュールを定義。
- 環境変数・設定管理モジュールを追加（src/kabusys/config.py）。
  - .env / .env.local を自動ロードする仕組みを実装（プロジェクトルートは .git または pyproject.toml を基準に検出）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化をサポート。
  - .env のパースは export プレフィックスやクォート、インラインコメント等に対応する細かいロジックを実装。
  - 設定アクセス用 Settings クラスを提供（J-Quants トークン、kabu API 設定、Slack トークン/チャネル、DB パス、KABUSYS_ENV/LOG_LEVEL の検証など）。
  - 環境値の必須チェック（未設定時は ValueError を発生）を実装。
- J-Quants API クライアントを追加（src/kabusys/data/jquants_client.py）。
  - 日足（OHLCV）、財務データ（四半期 BS/PL）、JPX マーケットカレンダーを取得する API 呼び出しを実装。
  - レート制限を厳守する固定間隔スロットリング（_RateLimiter、120 req/min）を実装。
  - リトライロジック（指数バックオフ、最大 3 回、対象ステータス: 408/429/5xx）を実装。429 の場合は Retry-After ヘッダを優先。
  - 401 Unauthorized 受信時はトークンを自動リフレッシュして 1 回だけリトライ（無限再帰防止のため allow_refresh フラグ処理）。
  - レスポンス JSON のデコード失敗時に明示的なエラーを出す実装。
  - ページネーション対応（pagination_key による繰り返し取得）。
  - DuckDB へ保存するための冪等的 save_* 関数を実装（ON CONFLICT DO UPDATE を使用）：save_daily_quotes, save_financial_statements, save_market_calendar。
  - データ保存時に fetched_at を UTC で記録して Look-ahead bias の追跡を可能に。
  - 変換ユーティリティ _to_float/_to_int を実装し堅牢な型変換を行う。
- ニュース収集モジュールを追加（src/kabusys/data/news_collector.py）。
  - RSS フィードからニュース記事を収集し raw_news テーブルへ保存する処理を実装。
  - トラッキングパラメータ除去・URL 正規化（_normalize_url）、記事ID を正規化 URL の SHA-256（先頭32文字）で生成する設計により冪等性を確保。
  - defusedxml を利用して XML Bomb 等の攻撃対策。
  - SSRF 対策: リダイレクト先のスキーム検査、ホストのプライベート/ループバック/リンクローカル判定（_is_private_host）を行い、リダイレクトハンドラ（_SSRFBlockRedirectHandler）を導入。
  - レスポンスサイズ制限（MAX_RESPONSE_BYTES = 10 MB）および gzip 解凍後サイズチェック（Gzip bomb 対策）。
  - URL スキーム検証（http/https のみ許可）、不正な link をスキップ。
  - テキスト前処理（URL 除去、空白正規化）関数 preprocess_text。
  - DuckDB への保存はチャンク化して単一トランザクションで実行し、INSERT ... RETURNING により実際に挿入されたレコードのみを返す（save_raw_news, save_news_symbols, _save_news_symbols_bulk）。
  - 銘柄コード抽出機能 extract_stock_codes（4 桁数字＋ known_codes フィルタ、重複削除）を提供。
  - run_news_collection で複数 RSS ソースからの収集、保存、銘柄紐付けを実行。ソース単位でエラーハンドリングして他ソースに影響を与えない設計。
  - デフォルト RSS ソースとして Yahoo Finance のカテゴリ RSS を定義。
- DuckDB スキーマ定義と初期化を追加（src/kabusys/data/schema.py）。
  - DataSchema.md に基づく 3 層（Raw / Processed / Feature）＋ Execution 層のテーブル定義を実装。
  - raw_prices, raw_financials, raw_news, raw_executions を含む Raw 層。
  - prices_daily, market_calendar, fundamentals, news_articles, news_symbols を含む Processed 層。
  - features, ai_scores を含む Feature 層。
  - signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance を含む Execution 層。
  - 各テーブルの制約（PRIMARY KEY, CHECK, FOREIGN KEY）や型を定義し、冪等な CREATE TABLE IF NOT EXISTS を使用。
  - 検索を高速化する複数のインデックスを定義（例: idx_prices_daily_code_date, idx_signal_queue_status など）。
  - init_schema(db_path) によるディレクトリ自動作成とスキーマ初期化、get_connection(db_path) で接続取得を提供。
- ETL パイプライン基盤を追加（src/kabusys/data/pipeline.py）。
  - 差分更新（最終取得日確認→未取得範囲のみ取得）、backfill_days による再取得（デフォルト 3 日）、品質チェック（quality モジュール連携）を想定した設計。
  - ETLResult データクラスを導入し、取得件数・保存件数・品質問題リスト・エラーリスト等を集約。品質問題は辞書化して to_dict で出力可能。
  - テーブル存在確認、最大日付取得ユーティリティ（_table_exists, _get_max_date）を実装。
  - market_calendar を参照した営業日調整ヘルパー _adjust_to_trading_day を実装。
  - raw_prices / raw_financials / market_calendar の最終取得日取得ヘルパー（get_last_price_date, get_last_financial_date, get_last_calendar_date）を提供。
  - run_prices_etl の骨子を実装（差分算出、fetch_daily_quotes 呼び出し、save_daily_quotes による保存、backfill 処理）。（注: ファイル末尾はスニペットのため続き実装の余地あり）

Security
- ニュース収集におけるセキュリティ対策を多数実装:
  - defusedxml による XML パースの安全化。
  - SSRF 対策（スキーム検査、プライベートアドレス判定、リダイレクト時検査）。
  - レスポンスサイズ制限と Gzip 解凍後のサイズチェックによるメモリ DoS 対策。
  - URL 正規化でトラッキングパラメータ除去。
- J-Quants API 呼び出しでタイムアウト（urllib の timeout）とリトライ方針、429 対応を実装。

Notes / Design Decisions
- API 呼び出しは Look-ahead bias を避けるため fetched_at を UTC で記録する方針。
- DuckDB への保存は可能な限り冪等に（ON CONFLICT DO UPDATE / DO NOTHING）実装しており、再実行に耐える設計。
- 仕様上の重要な定数はソース内に明記（_RATE_LIMIT_PER_MIN, _MAX_RETRIES, MAX_RESPONSE_BYTES 等）。
- 一部モジュール（strategy, execution）の初期パッケージ化は行われているが実装は未追加（空の __init__）。将来の拡張領域として確保。

Fixed
- （該当なし、初回リリース）

Changed
- （該当なし、初回リリース）

Deprecated
- （該当なし）

Removed
- （該当なし）

Security
- 上述の RSS / XML / SSRF / レスポンスサイズ対策を実装。外部に公開する API キー等の扱いは Settings 経由で環境変数から取得する設計。

今後の予定
- pipeline.run_prices_etl の完実装（財務データ・カレンダーの ETL 統合、品質チェック呼び出し結果の ETLResult への反映）。
- strategy / execution モジュールの実装（シグナル生成、注文送信、約定管理）。
- 単体テスト・統合テストの追加（ネットワーク関連はモック可能設計を意識）。
- ドキュメントの充実（DataPlatform.md / DataSchema.md / API 利用手順）。

以上。