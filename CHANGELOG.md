CHANGELOG
=========

すべての変更は Keep a Changelog の形式に従って記載します。  
このファイルはコードベースから推測して作成した初期リリースの変更履歴です。

[Unreleased]
------------

- なし

[0.1.0] - 2026-03-17
-------------------

Added
- パッケージ初期リリース: kabusys 0.1.0
  - パッケージ初期化: src/kabusys/__init__.py に __version__ = "0.1.0" と公開モジュール一覧を追加。
- 環境設定管理 (src/kabusys/config.py)
  - .env ファイルまたは既存 OS 環境変数から設定を自動読み込みする機能を実装（プロジェクトルートは .git または pyproject.toml を探索）。
  - .env のパース機能を実装（export プレフィックス、クォート内のエスケープ、行内コメント処理などに対応）。
  - 自動ロードの無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD に対応。
  - Settings クラスを提供し、J-Quants / kabuステーション / Slack / DB パス 等の設定プロパティを提供。必須キー未設定時は ValueError を送出。
  - KABUSYS_ENV と LOG_LEVEL の妥当性検証を実装（allowed set チェック）。
- J-Quants API クライアント (src/kabusys/data/jquants_client.py)
  - 日足（OHLCV）、財務データ（四半期 BS/PL）、マーケットカレンダーを取得する fetch_* 関数を実装（ページネーション対応）。
  - レートリミッタ実装（120 req/min 固定間隔スロットリング）。
  - リトライロジック（指数バックオフ、最大 3 回、408/429/5xx をリトライ）と 401 受信時のトークン自動リフレッシュ（1回のみ）を実装。
  - トークンキャッシュをモジュールレベルで保持し、ページネーション間で共有。
  - DuckDB への保存関数 save_daily_quotes / save_financial_statements / save_market_calendar を実装。ON CONFLICT DO UPDATE により冪等性を保証。
  - fetched_at を UTC タイムスタンプで記録し、取得時点のトレースを可能にする（Look-ahead bias 対策）。
  - データ型変換ユーティリティ（_to_float, _to_int）を実装（安全な数値変換と不正値処理）。
- ニュース収集モジュール (src/kabusys/data/news_collector.py)
  - RSS フィード収集と前処理、raw_news への保存、銘柄紐付けまでを行う一連の機能を実装。
  - URL 正規化（トラッキングパラメータ除去、クエリソート、フラグメント除去）と記事ID生成（正規化後の URL を SHA-256 ハッシュ化して先頭32文字を使用）を実装し、冪等性を確保。
  - defusedxml による XML パースで XML Bomb 等を防御。
  - SSRF 対策: URL スキーム検証（http/https のみ許可）、ホストがプライベート/ループバック/リンクローカルでは拒否、リダイレクト先の事前検査を行うカスタム RedirectHandler を実装。
  - レスポンスサイズ上限（MAX_RESPONSE_BYTES=10MB）チェックおよび gzip 解凍時の上限検査（Gzip bomb 対策）を実装。
  - Content-Length の事前チェック、受信バイト数超過時のスキップなどを実装。
  - テキスト前処理（URL 除去、空白正規化）を実装。
  - DB 保存はチャンク & トランザクションでまとめて実行し、INSERT ... RETURNING を使って実際に挿入された行を返す（save_raw_news, save_news_symbols, _save_news_symbols_bulk）。チャンクサイズ制御で SQL/パラメータ数の上限を抑制。
  - 銘柄コード抽出（4桁日本株コード候補）と既知銘柄セットとの照合ロジックを実装（extract_stock_codes）。
  - run_news_collection: 複数 RSS ソースを個別に収集し、失敗したソースはスキップしつつ残りは継続する堅牢な統合ジョブを提供。
  - デフォルト RSS ソースとして Yahoo Finance ビジネスカテゴリを設定。
- DuckDB スキーマ定義・初期化 (src/kabusys/data/schema.py)
  - Raw / Processed / Feature / Execution の3層（+Raw Execution）に対応したテーブル定義を実装（raw_prices, raw_financials, raw_news, raw_executions, prices_daily, market_calendar, fundamentals, news_articles, news_symbols, features, ai_scores, signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance 等）。
  - テーブル制約（PRIMARY KEY, CHECK, FOREIGN KEY）とよく使うクエリ向けのインデックスを定義。
  - スキーマ初期化関数 init_schema(db_path) を実装。db_path の親ディレクトリが存在しない場合は自動作成し、全DDLを冪等的に実行。
  - 既存 DB への接続取得用 get_connection を提供（初期化は行わない旨を明記）。
- ETL パイプライン基礎 (src/kabusys/data/pipeline.py)
  - ETL の設計方針に基づくユーティリティを実装（差分更新・バックフィル・品質チェック連携のための関数群の骨格）。
  - ETLResult dataclass を追加し、ETL 実行結果（取得数・保存数・品質問題・エラー）を構造化して返せるようにした。品質問題は JSON 化可能。
  - テーブル存在チェック、最大日付取得ヘルパー（_table_exists, _get_max_date）を提供。
  - market_calendar を基に非営業日調整を行う _adjust_to_trading_day を追加。
  - 差分更新ヘルパー: get_last_price_date / get_last_financial_date / get_last_calendar_date を提供。
  - run_prices_etl を実装（差分取得ロジック、backfill_days 処理、J-Quants クライアント呼び出しと保存）。デフォルトのバックフィル日数は 3 日。
- パッケージ構成
  - 空のパッケージモジュールプレースホルダ: execution, strategy, data パッケージ初期化ファイルを追加（将来的な拡張を見越した構成）。

Changed
- 新規リリースのため該当なし。

Fixed
- 新規リリースのため該当なし。

Security
- RSS パーサーで defusedxml を採用し XML 攻撃を緩和。
- RSS フェッチ時に SSRF 対策を実装（スキーム検証、プライベートホスト拒否、リダイレクト先検査）。
- レスポンス・圧縮解凍サイズ上限を設け、メモリ DoS / Gzip bomb を緩和。
- .env 読み込み時のファイル読み取り失敗に対して警告を出すなど安全性を考慮。

Notes / Implementation details
- J-Quants クライアントはページネーション対応。pagination_key を用いて全件を取得する。
- トークンはモジュールレベルでキャッシュされ、get_id_token(refresh_token=None) は Settings からリフレッシュトークンを取得する。
- DB 保存は基本的に冪等（ON CONFLICT DO UPDATE / DO NOTHING）を前提としているため、再実行が安全。
- news_collector の記事IDは正規化後 URL の SHA-256 ハッシュ先頭32文字を使用しトラッキングパラメータを取り除くことで同一記事の重複挿入を抑える。
- ETL の差分取得では既存最大日時を基に date_from を自動算出し、backfill_days により後出し修正を吸収する戦略を採用。
- DuckDB の init_schema は ":memory:" を受け付ける。ファイル DB の親ディレクトリは自動作成される。

Credits
- 初期実装はコードベース（src/kabusys 以下）から推測して作成しました。

ライセンスや既知の制約、互換性の注意事項などはソースリポジトリの README やドキュメントを参照してください。