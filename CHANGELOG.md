CHANGELOG
=========

すべての注目すべき変更をここに記録します。  
このファイルは Keep a Changelog の慣習に従います。  

注意:
- このCHANGELOGは提示されたコードベースからの推測に基づいて作成しています。
- リリース日やバージョン番号はソース中の __version__（0.1.0）および現在日付を参考にしています。

Unreleased
----------

- （なし）

[0.1.0] - 2026-03-18
--------------------

Initial release — KabuSys の最初の実装を追加しました。日本株の自動売買プラットフォームの基盤機能を中心に実装されています。

Added
- パッケージ初期化
  - src/kabusys/__init__.py: パッケージ名、__version__ = "0.1.0" と公開サブパッケージの __all__ を定義。

- 環境設定管理
  - src/kabusys/config.py:
    - .env ファイルおよび環境変数から設定を読み込む Settings クラスを実装。
    - .env 自動読み込み（プロジェクトルート判定: .git または pyproject.toml を探索）。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 による自動ロード無効化をサポート（テスト用）。
    - .env のパース機能（コメント、export プレフィックス、クォートとエスケープの扱い）を実装。
    - 必須環境変数取得用の _require メソッドと各種プロパティ（J-Quants トークン、kabu API、Slack、DBパス、環境区分、ログレベル判定など）。
    - 環境値検証（KABUSYS_ENV や LOG_LEVEL の許容値チェック）。

- J-Quants API クライアント
  - src/kabusys/data/jquants_client.py:
    - 日足（OHLCV）・財務データ・市場カレンダー取得関数を実装（fetch_daily_quotes、fetch_financial_statements、fetch_market_calendar）。
    - get_id_token によるリフレッシュトークン→IDトークン取得（POST）。
    - HTTP リクエスト共通処理 _request:
      - 固定間隔スロットリングによるレート制限遵守（120 req/min）。
      - 指数バックオフでのリトライ実装（最大3回、408/429/5xx 等を対象）。
      - 401 受信時は自動で ID トークンをリフレッシュして 1 回だけ再試行（再帰ループ防止の仕組みあり）。
      - JSON デコードエラー等のハンドリング。
    - DuckDB への冪等保存関数（ON CONFLICT DO UPDATE）:
      - save_daily_quotes, save_financial_statements, save_market_calendar
    - 取得時刻を UTC の fetched_at として記録し、Look-ahead バイアス対策を考慮。
    - 型変換ユーティリティ _to_float/_to_int（堅牢な変換ロジック）。

- ニュース収集モジュール
  - src/kabusys/data/news_collector.py:
    - RSS フィードから記事を収集し raw_news に保存する機能を実装（fetch_rss、save_raw_news 等）。
    - セキュリティ対策:
      - defusedxml を用いた XML パース（XML Bomb 等の防止）。
      - SSRF 対策: リダイレクト時の検査を行うハンドラ（_SSRFBlockRedirectHandler）、事前のホストプライベート判定（_is_private_host）。
      - URL スキーム検証（http/https のみ許可）。
      - レスポンスサイズ上限（MAX_RESPONSE_BYTES = 10MB）と gzip 解凍後サイズ検証（Gzip bomb 対策）。
    - URL 正規化とトラッキングパラメータ削除（_normalize_url）および正規化 URL の SHA-256 先頭 32 文字を用いた記事ID生成（_make_article_id）。これにより冪等性を確保。
    - テキスト前処理（URL 除去、空白正規化）。
    - DB 保存:
      - save_raw_news: INSERT ... RETURNING id を使い、実際に挿入された記事IDを返却。チャンク挿入・トランザクション制御あり。
      - save_news_symbols / _save_news_symbols_bulk: 記事と銘柄コードの紐付けをバルク挿入、ON CONFLICT で重複を無視。
    - 銘柄コード抽出ロジック（4桁数字の検出と既知コードセットによるフィルタ: extract_stock_codes）。
    - 統合収集ジョブ run_news_collection: 複数ソースを順に処理し、個別ソースでの失敗を他ソースに影響させない実装。

- DuckDB スキーマと初期化
  - src/kabusys/data/schema.py:
    - DataSchema.md に基づく3層（Raw / Processed / Feature / Execution）スキーマを定義。
    - raw_prices, raw_financials, raw_news, raw_executions など Raw レイヤー、
      prices_daily, market_calendar, fundamentals, news_articles, news_symbols など Processed レイヤー、
      features, ai_scores など Feature レイヤー、
      signals, signal_queue, orders, trades, positions, portfolio_performance など Execution レイヤーを作成。
    - 各テーブルに適切な制約（PK、CHECK、FK）を設定。
    - よく使われるクエリ向けのインデックスを定義。
    - init_schema(db_path) でデータベースファイルの親ディレクトリ自動作成、全DDLとインデックスの適用を行う（冪等）。
    - get_connection(db_path) で既存DBへの接続を返す（初期化は行わない）。

- ETL パイプライン（骨格）
  - src/kabusys/data/pipeline.py:
    - ETL の設計方針・差分更新ロジックを実装。
    - ETLResult データクラス（品質チェック結果・エラー集約を含む）を追加。
    - 差分判定ユーティリティ（_table_exists, _get_max_date, get_last_price_date, get_last_financial_date, get_last_calendar_date）。
    - 市場カレンダーを用いた営業日調整ヘルパー _adjust_to_trading_day。
    - run_prices_etl: 日足データ差分ETLを実行（backfill_days による再取得、jq.fetch_daily_quotes と jq.save_daily_quotes を呼び出し）。※（下記の Known issues を参照）

- ドキュメント / 設計メモ（コード中の docstring とコメント）
  - 各モジュールに設計方針、セキュリティ考慮、API制限対応、冪等性、品質チェック方針などを詳細に記述。

Security
- RSS/HTTP 周りおよび XML 処理に対して複数の保護策を導入（defusedxml、SSRF ブロック、プライベートIP検査、レスポンスサイズ制限、gzip 解凍後サイズ検査）。
- 環境変数読み込み時に OS 環境変数を保護するための protected キーセットを導入し、.env.local による上書きを制御。

Fixed
- （初回リリースのため該当なし）

Changed
- （初回リリースのため該当なし）

Removed
- （初回リリースのため該当なし）

Known issues / Notes / Migration
- run_prices_etl の戻り値
  - 現状ファイル末尾の run_prices_etl の return が不完全（len(records), のように見え、saved を返していない可能性がある）。ETL の呼び出し側で期待するタプル (fetched, saved) を確実に受け取れるよう修正が必要です（要確認・修正）。
- strategy/execution パッケージ
  - src/kabusys/strategy/__init__.py と src/kabusys/execution/__init__.py は空ファイル（将来的な戦略・発注ロジックの拡張ポイント）。
- 初回導入時の手順
  - DuckDB スキーマを利用するには init_schema(db_path) を呼び出してテーブル作成を行ってください。
  - 環境変数（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID など）を設定する必要があります。config.Settings の _require により未設定時は ValueError が送出されます。
- テストのためのフック
  - KABUSYS_DISABLE_AUTO_ENV_LOAD で自動 .env 読み込みを無効化できます。
  - news_collector の _urlopen はテストでモック可能。

開発者向けメモ
- J-Quants API のレート制限と 401 リフレッシュのロジックは jquants_client._request に実装されています。ページネーション間で利用するトークンはモジュールキャッシュ（_ID_TOKEN_CACHE）で共有されます。
- DuckDB の INSERT ... RETURNING を多用して「実際に挿入された件数」を正確に取得する方針です。
- news_collector では記事IDを URL 正規化→SHA-256 で生成し先頭32文字を利用しているため、同一記事の冪等性が確保されます。

Contributors
- 初期実装（推測に基づく作成のため、具体的なコントリビュータ情報はソースに記載がありません）。

--- 

今後のリリースでは下記を検討すると良いでしょう:
- pipeline モジュールの各 ETL ジョブの単体テストとエンドツーエンドテストの追加。
- run_prices_etl の戻り値バグ修正と他 ETL 関数（financials, calendar）の実装・統合。
- strategy・execution 層の初期実装（シグナル生成、注文送信、約定処理、ポジション管理）。
- モニタリング用モジュール（Slack 通知など）の実装・統合テスト。