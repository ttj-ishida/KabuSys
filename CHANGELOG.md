CHANGELOG
=========

すべての変更は Keep a Changelog のガイドラインに準拠して記載しています。

Unreleased
----------

- （なし）

0.1.0 - 2026-03-18
------------------

Added
- パッケージ初版リリース (kabusys v0.1.0)
  - パッケージのトップメタ情報を追加（src/kabusys/__init__.py: __version__ = "0.1.0"）。
- 環境設定管理モジュールを追加（src/kabusys/config.py）
  - .env / .env.local の自動読み込み機能を実装（プロジェクトルートを .git または pyproject.toml で検出）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化をサポート（テスト用）。
  - .env の行パーサ実装（export プレフィックス、クォート処理、インラインコメント処理に対応）。
  - .env.local は既存の OS 環境変数を保護しつつ上書き（override=True, protected keys）。
  - 必須環境変数取得ヘルパ _require を提供。
  - アプリケーション設定クラス Settings を提供し、以下のプロパティを公開：
    - jquants_refresh_token（JQUANTS_REFRESH_TOKEN）
    - kabu_api_password（KABU_API_PASSWORD）
    - kabu_api_base_url（デフォルト: http://localhost:18080/kabusapi）
    - slack_bot_token / slack_channel_id（Slack 関連の必須設定）
    - duckdb_path / sqlite_path（デフォルトパスを提供）
    - env（KABUSYS_ENV: development/paper_trading/live のバリデーション）
    - log_level（LOG_LEVEL のバリデーション）
    - is_live / is_paper / is_dev の簡易判定プロパティ
- J-Quants API クライアントを追加（src/kabusys/data/jquants_client.py）
  - 日足（OHLCV）、財務諸表、マーケットカレンダーを取得する fetch_* API を実装（ページネーション対応）。
  - レート制限（120 req/min）に従う固定間隔スロットリング RateLimiter を実装。
  - リトライロジック（指数バックオフ、最大3回、408/429/5xx を対象）を実装。
  - 401 受信時のトークン自動リフレッシュを実装（リフレッシュは1回のみ試行、無限再帰防止）。
  - ページネーション間での ID トークン共有用モジュールレベルキャッシュを実装。
  - DuckDB へ冪等に保存する save_* 関数を実装（ON CONFLICT DO UPDATE を使用し重複更新を防止）。
  - 取得時刻を UTC で記録する fetched_at を付与し Look-ahead Bias のトレースを可能に。
  - 数値変換ユーティリティ _to_float / _to_int を提供（空文字列や不正値の扱いを定義）。
- ニュース収集モジュールを追加（src/kabusys/data/news_collector.py）
  - RSS フィード取得と raw_news への保存を実装（デフォルトソースに Yahoo Finance を登録）。
  - URL 正規化（トラッキングパラメータ削除、クエリソート、フラグメント除去）と記事ID生成（正規化後の SHA-256 の先頭32文字）で冪等性を確保。
  - defusedxml を用いた安全な XML パース（XML Bomb 等の防御）。
  - SSRF 対策:
    - _SSRFBlockRedirectHandler によるリダイレクト先のスキーム/ホスト検査。
    - _is_private_host による直接 IP と DNS 解決した A/AAAA レコードのプライベートアドレス判定。
    - HTTP/HTTPS 以外のスキームを拒否。
  - レスポンス読み取りの上限（MAX_RESPONSE_BYTES = 10MB）設定、gzip 解凍後のサイズ検査、Content-Length の事前チェックを実装（DoS 防御）。
  - テキスト前処理（URL 除去、空白正規化）と pubDate パース（RFC2822 -> UTC naive）を実装。
  - DB 保存はチャンク＆トランザクションで行い、INSERT ... RETURNING で実際に挿入された ID / 件数を返す（save_raw_news / save_news_symbols / _save_news_symbols_bulk）。
  - 銘柄コード抽出ロジック（4桁数値を候補に既知コードセットでフィルタ）を提供。
  - run_news_collection により複数ソースの収集 / 保存 / 銘柄紐付けの統合ジョブを提供（ソース単位での堅牢なエラーハンドリング）。
- DuckDB スキーマ定義・初期化モジュールを追加（src/kabusys/data/schema.py）
  - Raw / Processed / Feature / Execution の各レイヤーに対応するテーブル DDL を実装。
    - 例: raw_prices, raw_financials, raw_news, market_calendar, prices_daily, features, ai_scores, signal_queue, orders, trades, positions, portfolio_performance など多数。
  - 各種制約（PRIMARY KEY, CHECK, FOREIGN KEY）を付与。
  - 頻出クエリ用のインデックス定義を追加（code×date、status 検索等）。
  - init_schema(db_path) によりディレクトリ自動作成を行いスキーマを初期化する API を提供。
  - get_connection(db_path) で既存 DB への接続を提供（スキーマ初期化は行わない）。
- ETL パイプラインの基本モジュールを追加（src/kabusys/data/pipeline.py）
  - ETLResult データクラスで ETL 実行結果 / 品質問題 / エラー列を集約。
  - 差分更新（最終取得日を確認して未取得範囲のみ取得）と backfill の概念を導入（デフォルト backfill_days = 3）。
  - 市場カレンダー先読み（lookahead）や最小データ開始日を定義（_MIN_DATA_DATE = 2017-01-01）。
  - DB テーブル存在・最大日付取得ユーティリティ（_table_exists / _get_max_date）を提供。
  - 非営業日調整ヘルパ（_adjust_to_trading_day）実装。
  - get_last_price_date / get_last_financial_date / get_last_calendar_date を提供。
  - run_prices_etl を実装（差分計算、jq.fetch_daily_quotes 呼び出し、save 呼び出し、backfill 処理を含む）。

Changed
- （初版のため変更履歴はなし）

Fixed
- （初版のため修正履歴はなし）

Security
- RSS 取得処理で以下のセキュリティ対策を実施
  - defusedxml を用いた XML パース（外部攻撃耐性向上）。
  - SSRF 防止（スキーム検証、プライベートアドレス拒否、リダイレクト先検査）。
  - レスポンスサイズ上限（10MB）設定と gzip 解凍後サイズ検査（メモリ DoS 対策）。
- .env 読み込み時に OS 環境変数を保護する protected キーセットを導入（.env.local から OS 変数を誤って上書きしない）。

Deprecated
- （初版のためなし）

Removed
- （初版のためなし）

Notes / Migration
- 初期化:
  - DuckDB スキーマは init_schema(db_path) を呼び出して作成してください。既存のテーブルがある場合はスキップされます。
- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID が必須です（Settings._require により未設定時に ValueError を送出）。
- .env の仕様:
  - export プレフィックス、シングル/ダブルクォート、インラインコメント（クォート無しで # の直前が空白/タブの場合）に対応します。
  - .env.local は .env の上位互換として OS 環境変数を保護しつつ上書き可能です。
- テスト用フック:
  - news_collector._urlopen をモックして外部接続を置き換え可能です。

Known issues / TODO
- run_prices_etl の戻り値実装が不完全（ソースコード末尾が "return len(records), " のまま途切れているように見えます）。本来 (fetched_count, saved_count) を返す想定です。リリース時点ではこの点に注意してください（あとで修正予定）。
- jquants_client._request のエラーメッセージや例外ラッピングは実運用での詳細ログを調整する可能性があります。
- news_collector の DNS 解決失敗時は「安全側」として通過させていますが、運用環境によっては挙動調整が必要です（厳格に拒否するポリシーなど）。

参考実装ファイル
- src/kabusys/config.py
- src/kabusys/data/jquants_client.py
- src/kabusys/data/news_collector.py
- src/kabusys/data/schema.py
- src/kabusys/data/pipeline.py

貢献・バグ報告
- バグ報告や改善提案は issue を作成してください。重大なセキュリティ問題は秘匿チャネルでご連絡ください。