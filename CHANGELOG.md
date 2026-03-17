CHANGELOG
=========

すべての変化は Keep a Changelog のフォーマットに準拠して記載しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

Unreleased
----------

- (なし)

[0.1.0] - 2026-03-17
--------------------

Added
- パッケージ基本情報
  - kabusys パッケージの初期公開（src/kabusys/__init__.py）。
  - __version__ = "0.1.0" を設定。data, strategy, execution, monitoring を公開モジュールとしてエクスポート。

- 設定・環境変数管理 (src/kabusys/config.py)
  - .env/.env.local ファイルおよび OS 環境変数からの設定読み込み機能を実装。
  - プロジェクトルート探索ロジック（.git または pyproject.toml を起点）により CWD に依存しない自動ロードを実現。
  - .env ファイルのパース実装（コメント、export プレフィックス、シングル/ダブルクォートおよびエスケープ対応、インラインコメント処理）。
  - 自動ロードの無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD を追加。
  - Settings クラスを提供し、J-Quants, kabuステーション, Slack, DB パス、環境種別（development/paper_trading/live）やログレベルの検証を実装。
  - 必須環境変数取得時に未設定で ValueError を送出する _require 実装。

- J-Quants クライアント (src/kabusys/data/jquants_client.py)
  - J-Quants API からのデータ取得（株価日足、財務データ、JPX カレンダー）を行うクライアント実装。
  - RateLimiter による API レート制御（120 req/min）を実装。
  - 再試行ロジック（指数バックオフ、最大 3 回、408/429/5xx を対象）を実装。
  - 401 レスポンス時にリフレッシュトークンから id_token を自動更新して 1 回リトライする仕組みを実装。
  - ページネーション対応（pagination_key）で全件取得。
  - データの取得時刻（fetched_at）を UTC で記録し、Look-ahead Bias をトレース可能に。
  - DuckDB への保存関数（save_daily_quotes, save_financial_statements, save_market_calendar）を実装。ON CONFLICT DO UPDATE により冪等性を確保。
  - 型変換ユーティリティ _to_float, _to_int を追加し、文字列/空値/不正値対策を実装。

- ニュース収集モジュール (src/kabusys/data/news_collector.py)
  - RSS フィード収集機能を実装。デフォルトで Yahoo Finance のビジネスカテゴリ RSS を参照する設定を含む。
  - defusedxml を利用した安全な XML パース（XML Bomb 等の緩和）。
  - SSRF 対策:
    - URL スキーム検証（http/https のみ許可）。
    - リダイレクト時のスキーム・ホスト検査用カスタム HTTPRedirectHandler を実装。
    - ホストがプライベート/ループバック/リンクローカル/マルチキャストかを判定しブロック。
  - レスポンスサイズ上限（MAX_RESPONSE_BYTES = 10 MB）を導入しメモリ DoS を防止。gzip レスポンスの解凍と追加サイズ検査も実装。
  - URL 正規化（トラッキングパラメータ除去、クエリソート、フラグメント削除）および SHA-256 ベースの記事 ID 生成（先頭32文字）を実装し冪等性を確保。
  - テキスト前処理（URL 除去、空白正規化）を実装。
  - DuckDB への保存: INSERT ... RETURNING を使った新規挿入IDの取得、チャンク分割によるバルク挿入、トランザクション管理を実装（save_raw_news, save_news_symbols, _save_news_symbols_bulk）。
  - 記事内からの銘柄コード抽出ロジック（4桁数字、known_codes フィルタ）を実装。
  - run_news_collection により複数 RSS ソースを順次取得し、個別ソースの失敗を隔離して処理を継続。

- DuckDB スキーマ定義と初期化 (src/kabusys/data/schema.py)
  - DataPlatform.md に基づく多層スキーマを実装（Raw / Processed / Feature / Execution レイヤー）。
  - raw_prices, raw_financials, raw_news, raw_executions 等の Raw テーブルを定義。
  - prices_daily, market_calendar, fundamentals, news_articles, news_symbols 等の Processed テーブルを定義。
  - features, ai_scores 等の Feature テーブルを定義。
  - signals, signal_queue, orders, trades, positions, portfolio_performance 等の Execution テーブルを定義。
  - 頻出クエリ向けのインデックス群を定義。
  - init_schema(db_path) により必要な親ディレクトリを作成し、全テーブル・インデックスを冪等に作成する初期化関数を提供。get_connection() により既存 DB への接続を提供。

- ETL パイプライン (src/kabusys/data/pipeline.py)
  - ETL 実行結果を表す ETLResult dataclass を実装。品質問題やエラーの集約をサポート。
  - 差分更新ヘルパー（テーブル存在チェック、テーブルの最大日付取得）を実装。
  - 市場カレンダーに基づく営業日調整ヘルパー（_adjust_to_trading_day）を実装。
  - raw_prices/raw_financials/market_calendar の最終取得日取得関数を公開。
  - run_prices_etl により差分取得ロジックを実装（最終取得日からの backfill、_MIN_DATA_DATE の取り扱い、jq.fetch_daily_quotes + jq.save_daily_quotes の連携）。品質チェックモジュールとの連携を想定した設計。

Security
- 複数箇所で安全性を考慮:
  - defusedxml を用いた XML パース。
  - RSS フェッチにおける SSRF 対策（スキーム検証、プライベートホスト検査、リダイレクト前検査）。
  - .env 読み込みで OS 環境変数を保護する protected セット機能。
  - HTTP タイムアウトやレスポンスサイズ上限などの過負荷対策。

Known issues / Notes
- run_prices_etl の戻り値について
  - run_prices_etl の実装は差分取得・保存を行う設計になっており、取得件数と保存件数を返すことが想定されています（ETLResult 連携想定）。今後、財務データ/カレンダー/品質チェックとの統合やテストでの整備が必要です。
- テスト・モック
  - ネットワーク部分（_urlopen や HTTP レスポンス）を外部からモックできるように設計されているため、単体テスト追加が容易です。ただし、現状テストケースは含まれていません。
- マイグレーション/互換性
  - DuckDB スキーマは初期版として広範に定義されています。将来的なスキーマ変更はマイグレーション方針を検討してください。

貢献・開発メモ
- 自動環境読み込みはプロジェクトルートを基準に行われるため、パッケージ配布後にテスト等で自動読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- J-Quants 認証は Settings.jquants_refresh_token を利用します。CI/デプロイ環境では機密情報の取り扱いに注意してください。

---
この CHANGELOG はソースコードの内容から推測して作成しています。実際のリリースノートにはテスト結果・マイグレーション手順・既知のバグ修正などの追加情報を含めることを推奨します。