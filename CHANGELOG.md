Keep a Changelog 形式に準拠した CHANGELOG.md（日本語）を作成しました。パッケージのバージョンは src/kabusys/__init__.py の __version__ = "0.1.0" に合わせ、初回リリースとして記載しています。以下をそのまま CHANGELOG.md としてお使いください。

---
All notable changes to this project will be documented in this file.

The format is based on "Keep a Changelog" and this project adheres to Semantic Versioning.

Unreleased
----------
(現在なし)

0.1.0 - 2026-03-17
------------------
Added
- 基本パッケージ構成を追加
  - パッケージエントリ: kabusys (src/kabusys/__init__.py) を導入。__version__ = 0.1.0。公開モジュールは data, strategy, execution, monitoring を想定。

- 環境設定 / 設定読み込み機能（kabusys.config）
  - .env と .env.local をプロジェクトルート（.git または pyproject.toml を基準）から自動読み込みする仕組みを追加（自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
  - .env パーサは export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントの取り扱いに対応。
  - OS 環境変数を保護する protected 機能と override フラグを実装。
  - Settings クラスを提供し、J-Quants / kabu API / Slack / DB パス / 環境（development/paper_trading/live）/ログレベル等の設定をプロパティとして取得可能。値検証（有効な env 値、ログレベル）を実装。

- J-Quants API クライアント（kabusys.data.jquants_client）
  - 日足（OHLCV）、財務データ（四半期 BS/PL）、JPX マーケットカレンダーを取得する fetch_* 関数を実装（ページネーション対応）。
  - HTTP リクエスト共通処理で以下をサポート：
    - API レート制御（120 req/min）を固定間隔スロットリングで実装（_RateLimiter）。
    - リトライロジック（指数バックオフ、最大 3 回、408/429/>=500 を対象）。429 の場合は Retry-After ヘッダを優先。
    - 401 受信時は ID トークン自動リフレッシュを 1 回行って再試行する仕組み（無限再帰対策の allow_refresh 制御あり）。
    - JSON デコード失敗時の明示的エラー。
  - DuckDB への保存関数 save_daily_quotes / save_financial_statements / save_market_calendar を実装。ON CONFLICT DO UPDATE による冪等性を保証し、PK 欠損行のスキップ・ログ出力あり。
  - 型変換ユーティリティ（_to_float/_to_int）を追加。float 文字列の厳密な int 変換ルールを実装。

- ニュース収集モジュール（kabusys.data.news_collector）
  - RSS フィードからのニュース収集フローを実装（fetch_rss, save_raw_news, save_news_symbols, run_news_collection）。
  - セキュリティ対策:
    - defusedxml を利用して XML Bomb 等に対策。
    - SSRF 対策: リダイレクト時にスキーム/ホストの事前検証を行う独自ハンドラ（_SSRFBlockRedirectHandler）を導入。ホストがプライベート/ループバック/リンクローカル等の場合はアクセスを拒否。
    - URL スキームは http/https のみ許可。
    - レスポンス受信サイズ上限（MAX_RESPONSE_BYTES = 10 MB）を導入しメモリ DoS を防止。gzip 解凍後のサイズチェックも実施。
  - コンテンツ前処理:
    - URL 除去、空白正規化を行う preprocess_text。
    - URL 正規化（トラッキングパラメータ除去、スキーム/ホスト小文字化、フラグメント除去、クエリソート）と、それに基づく SHA-256（先頭32文字）での記事ID生成（_make_article_id）による冪等性を保証。
  - DB 保存:
    - raw_news への一括挿入はチャンク分割とトランザクションで処理。INSERT ... ON CONFLICT DO NOTHING RETURNING を使い、実際に挿入された記事IDのみを返す。
    - news_symbols（記事⇔銘柄紐付け）を一括挿入する内部関数を実装し、INSERT ... RETURNING で正確な挿入数を返す。
  - 銘柄抽出:
    - テキスト中の4桁数字パターンから既知銘柄セットに基づいて銘柄コードを抽出する extract_stock_codes を実装。

- DuckDB スキーマ定義 / 初期化（kabusys.data.schema）
  - Raw / Processed / Feature / Execution を想定したテーブル群の DDL を実装（raw_prices, raw_financials, raw_news, raw_executions, prices_daily, market_calendar, fundamentals, news_articles, news_symbols, features, ai_scores, signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance）。
  - テーブル作成順序は外部キー依存を考慮。インデックス定義も含む。
  - init_schema(db_path) でディレクトリ作成を行い、全DDLとインデックスを実行して接続を返す。get_connection() も提供（スキーマ初期化は行わない）。

- ETL パイプライン（kabusys.data.pipeline）
  - 差分更新を行う ETL 設計（差分取得、backfill_days による後出し修正吸収、品証チェックフック想定）。
  - ETLResult データクラスを提供し、実行結果・品質問題・エラー要約を格納・辞書化可能。
  - market_calendar の有無や非営業日に対する調整ヘルパー（_adjust_to_trading_day）を実装。
  - DB の最終取得日を返すユーティリティ（get_last_price_date, get_last_financial_date, get_last_calendar_date）。
  - run_prices_etl の差分ロジック・fetch/save 呼び出しを実装（date_from 自動算出、_MIN_DATA_DATE での初回ロード制御、バックフィル日数のデフォルトは 3 日、ログ出力）。

Security
- RSS パーシングに defusedxml を使用して XML 攻撃を防止。
- ニュース取得で SSRF 対策を導入（リダイレクト時のスキーム/ホスト検査・事前ホスト検査）。
- .env 自動読み込みでは OS 環境変数の上書きを保護する仕組みを提供。

Performance / robustness
- J-Quants API クライアントにレートリミッタ、再試行（指数バックオフ）、429での Retry-After 優先処理を実装。
- bulk insert のチャンク処理、トランザクションまとめにより DB 書き込みオーバーヘッドを低減。
- news_collector のレスポンスサイズ制限・gzip サイズチェックでリソース保護。

Fixed
- 初回リリースのため該当なし。

Known issues / Notes
- run_prices_etl の戻り値の実装に注意:
  - run_prices_etl の最後の return が "return len(records)," のように単一要素のタプルとなっており、関数注釈で期待される (int, int) を返していないように見えます（保存件数 saved を返す実装が抜けている可能性があります）。運用前に戻り値の整合性（取得数と保存数を両方返す）を確認してください。
- そのほか、初期実装のため細かい例外処理やエッジケース（外部APIの仕様変更、DuckDB のバージョン差異など）については運用中に追加改修が必要になる可能性があります。

Migration notes
- 初回リリースのため、マイグレーションは不要。
- 既存のデータベースがある場合は init_schema の実行で既存テーブルはスキップされる（冪等）。

API 使い方（主な公開関数）
- 設定:
  - from kabusys.config import settings
- DB 初期化:
  - from kabusys.data.schema import init_schema, get_connection
  - conn = init_schema("data/kabusys.duckdb")
- J-Quants:
  - from kabusys.data import jquants_client as jq
  - token = jq.get_id_token()
  - records = jq.fetch_daily_quotes(id_token=token, date_from=..., date_to=...)
  - saved = jq.save_daily_quotes(conn, records)
- ニュース収集:
  - from kabusys.data import news_collector as nc
  - articles = nc.fetch_rss(url, source)
  - new_ids = nc.save_raw_news(conn, articles)
  - nc.save_news_symbols(conn, news_id, codes)
  - 全収集ジョブ: nc.run_news_collection(conn, sources, known_codes)

---

上記はコード内容から推測して作成した CHANGELOG です。必要であれば以下を追加できます:
- リリースノートの英語版
- 各機能ごとの利用例（スニペット）
- 既知のバグに対する PR / 修正案の候補

どの追加情報が必要か教えてください。