# CHANGELOG

すべての変更は Keep a Changelog の原則に従って記載しています。互換性のある後方互換性や重要な設計決定を明確にするため、リリースごとの追加・変更・セキュリティ対応などを分類しています。

## [0.1.0] - 2026-03-17

初回公開リリース。日本株自動売買プラットフォームの基盤機能を実装しました。主にデータ取得・保存、環境設定、ニュース収集、DuckDB スキーマ定義、ETL パイプラインの基礎実装が含まれます。

### Added
- パッケージ初期化
  - パッケージメタ情報を追加（kabusys.__version__ = "0.1.0"）。パッケージの公開エントリを定義（data, strategy, execution, monitoring を __all__ に含む）。

- 環境設定モジュール（kabusys.config）
  - .env ファイルおよび環境変数から設定を自動読み込みする仕組みを実装（プロジェクトルートの検出は .git または pyproject.toml を基準に行う）。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。自動ロードを無効化するためのフラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - .env パーサの実装: コメント、export プレフィックス、クォート文字列のエスケープ、インラインコメントの扱い等に対応。
  - Settings クラスを提供し、J-Quants / kabu ステーション / Slack / DB パス等の設定をプロパティとして取得可能（必須設定未指定時は ValueError を送出）。
  - 環境値のバリデーション（KABUSYS_ENV, LOG_LEVEL の許容値チェック）と is_live/is_paper/is_dev のユーティリティを追加。

- J-Quants API クライアント（kabusys.data.jquants_client）
  - API ベース機能を実装：
    - 固定間隔スロットリングによるレート制御（120 req/min を遵守する RateLimiter）。
    - リトライロジック（指数バックオフ、最大3回、ネットワーク系・429/408/5xx に対応）。
    - 401 の際のトークン自動リフレッシュ（1 回のみ）とモジュールレベルのトークンキャッシュ。
    - JSON パースエラー時の明示的なエラー報告。
  - 認証関数 get_id_token を実装（リフレッシュトークンから ID トークン取得、Settings からのトークン読み込みをサポート）。
  - API からのデータ取得関数を実装（ページネーション対応）：
    - fetch_daily_quotes（株価日足 OHLCV）
    - fetch_financial_statements（四半期 BS/PL）
    - fetch_market_calendar（JPX マーケットカレンダー）
  - DuckDB への冪等保存関数を実装：
    - save_daily_quotes, save_financial_statements, save_market_calendar（いずれも ON CONFLICT を用いた更新で重複排除）。
  - 入出力変換ユーティリティ（_to_float, _to_int）を追加し、文字列データの安全な数値変換をサポート。
  - Look-ahead bias 対策：データ取得時刻（fetched_at）を UTC タイムスタンプとして保存する方針を採用。

- ニュース収集モジュール（kabusys.data.news_collector）
  - RSS フィードからの収集処理を実装（既定ソースに Yahoo Finance のビジネスカテゴリ RSS）。
  - セキュリティ対策を多数実装：
    - defusedxml を用いた XML パース（XML Bomb 等の防御）。
    - SSRF 対策：URL スキーム検証、リダイレクト先の事前検査（プライベート/ループバック/リンクローカルの拒否）、ホストの IP 解決チェック、リダイレクトハンドラの導入。
    - レスポンスサイズ上限（MAX_RESPONSE_BYTES = 10MB）と gzip 解凍後のサイズチェック（Gzip bomb 対策）。
    - 許可スキームは http/https のみ。
  - 記事の前処理と一意ID生成：
    - URL 正規化（トラッキングパラメータ除去、フラグメント削除、パラメータソート）および SHA-256（先頭32文字）による記事ID生成で冪等性を担保。
    - テキスト前処理（URL 除去、空白正規化）。
    - pubDate のパース（RFC 2822→UTC naive datetime、失敗時は警告出力して現在時刻で代替）。
  - DuckDB 保存ロジック：
    - save_raw_news: チャンク（デフォルト1000件）毎に INSERT ... ON CONFLICT DO NOTHING RETURNING id を実行し、新規挿入IDリストを返す。1 トランザクションでバルク挿入・コミット／ロールバックを実施。
    - save_news_symbols / _save_news_symbols_bulk: 記事と銘柄の紐付けを一括保存（ON CONFLICT で重複をスキップし、実際に挿入された件数を返す）。トランザクション管理あり。
  - 銘柄コード抽出ユーティリティ（4桁数字の抽出、known_codes フィルタ）を実装。
  - 統合収集ジョブ run_news_collection を実装（各ソース独立でエラーハンドリングし、既知銘柄との紐付けを行う）。

- スキーマ定義と初期化（kabusys.data.schema）
  - DuckDB 用の完全なスキーマを実装（Raw / Processed / Feature / Execution レイヤー）。
  - raw_prices, raw_financials, raw_news, raw_executions 等の Raw レイヤーテーブルを定義。
  - prices_daily, market_calendar, fundamentals, news_articles, news_symbols 等の Processed レイヤーテーブルを定義。
  - features, ai_scores 等の Feature レイヤーテーブルを定義。
  - signal_queue, orders, trades, positions, portfolio_performance 等の Execution レイヤーテーブルを定義。
  - 頻出クエリ向けのインデックスを複数定義。
  - init_schema(db_path) により DB ファイルの親ディレクトリ自動作成とテーブル作成（冪等）を行う。:memory: のサポートあり。
  - get_connection(db_path) を提供（スキーマ初期化は行わない）。

- ETL パイプライン基盤（kabusys.data.pipeline）
  - ETLResult データクラスを実装（ETL 実行結果、品質問題リスト、エラー等を保持）。
  - テーブル存在チェック、最大日付取得ユーティリティを実装。
  - 市場カレンダーに基づく営業日調整ユーティリティ（_adjust_to_trading_day）を実装。
  - 差分更新のためのヘルパー関数（get_last_price_date / get_last_financial_date / get_last_calendar_date）を追加。
  - run_prices_etl を実装（差分算出、backfill デフォルト 3 日、API 取得→保存の流れ）。（注: ETL 全体のフローは段階的に実装予定）

### Security
- セキュリティ関連の改善点を初期実装として含む：
  - ニュース収集時の SSRF 対策（スキーム検査、プライベートアドレス拒否、リダイレクト時の検査）。
  - XML パースに defusedxml を使用して XML 攻撃を緩和。
  - HTTP レスポンスのサイズ制限によるメモリ DoS / Gzip bomb 対策。
  - .env ローダーは OS 環境変数を保護するため protected セットを使用。

### Notes / Required environment variables
- 本システムを実行するには少なくとも以下の環境変数（または .env）を設定してください:
  - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
  - KABU_API_PASSWORD: kabu ステーション API のパスワード
  - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID: Slack 通知用
  - DUCKDB_PATH / SQLITE_PATH: データベース保存先（デフォルト値あり）
- 自動 .env ロードを無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト等で利用）。

### Known limitations / TODO
- strategy, execution, monitoring パッケージの実装は現状ファイル構造のみ（初期のエクスポート宣言あり）があり、実際の戦略・発注ロジックはこれから実装予定です。
- ETL パイプライン（pipeline モジュール）は prices の差分 ETL を実装中であり、品質チェック（quality モジュール）との統合や他リソース（財務データ、カレンダー）のフルワークフローは今後拡張予定です。
- テスト用のモックポイント（例: news_collector._urlopen や pipeline の id_token 注入）は設けられているが、テストスイートの実装は別途必要です。

---

今後のリリースでは、ETL の完全な自動化、戦略実装、注文実行モジュール、監視/アラート機能、より詳細な品質チェックとドキュメント整備を予定しています。