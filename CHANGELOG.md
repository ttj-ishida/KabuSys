CHANGELOG
=========

すべての変更は Keep a Changelog の形式に準拠して記載しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

Unreleased
----------
（現状なし）

0.1.0 - 2026-03-17
-----------------

Added
- パッケージの初期リリース。
  - src/kabusys/__init__.py によるパッケージエントリ（__version__ = 0.1.0）。
- 環境設定管理（src/kabusys/config.py）。
  - .env / .env.local を自動読み込み（OS 環境変数を優先）。プロジェクトルートは .git または pyproject.toml を探索して特定。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動読み込みを無効化可能（テスト用）。
  - .env 行パーサ実装（export プレフィックス、クォート、エスケープ、インラインコメント等に対応）。
  - 必須環境変数取得ヘルパ（_require）と Settings クラス（J-Quants / kabu / Slack / DB パス / 環境判定 / ログレベル検証など）。
  - 環境値の妥当性検証（KABUSYS_ENV / LOG_LEVEL の許容値チェック）。
- J-Quants API クライアント（src/kabusys/data/jquants_client.py）。
  - 日足（OHLCV）、財務（四半期 BS/PL）、JPX マーケットカレンダー取得 API ラッパー実装。
  - レート制限制御（120 req/min 固定間隔スロットリング）を内蔵した RateLimiter。
  - リトライロジック（指数バックオフ、最大 3 回、408/429/5xx を対象）。429 の場合は Retry-After を尊重。
  - 401 受信時はトークン自動リフレッシュを行い 1 回リトライ（無限再帰防止のため allow_refresh 制御）。
  - ページネーション対応（pagination_key による走査）。
  - DuckDB へ冪等保存する save_* 関数（ON CONFLICT DO UPDATE）を提供（raw_prices / raw_financials / market_calendar）。
  - データ変換ユーティリティ（_to_float / _to_int）による安全な型変換。
  - モジュールレベルでの id_token キャッシュ（ページネーション間のトークン共有）。
- ニュース収集モジュール（src/kabusys/data/news_collector.py）。
  - RSS フィード取得および前処理パイプラインを実装（URL 正規化、トラッキングパラメータ除去、本文正規化）。
  - defusedxml を用いた XML パース（XML Bomb への対策）。
  - SSRF 対策:
    - URL スキーム検証（http/https のみ許可）。
    - 受信前にホストがプライベートでないか検査（DNS 解決／IP 判定）。
    - リダイレクト時にスキーム・ホスト検証を行うカスタム HTTPRedirectHandler を実装。
  - レスポンスサイズ上限（MAX_RESPONSE_BYTES = 10MB）と gzip 解凍後の再検査によるメモリ DoS 対策。
  - 記事ID を正規化 URL の SHA-256（先頭32文字）で生成して冪等性を保証。
  - DuckDB への保存はトランザクションでまとめ、INSERT ... RETURNING を用いて実際に挿入された件数を取得（save_raw_news / save_news_symbols / _save_news_symbols_bulk）。
  - 銘柄コード抽出ロジック（4桁数字の抽出と known_codes によるフィルタ）。
  - run_news_collection により複数ソースの収集と銘柄紐付けを一括実行（各ソースは独立してエラーハンドリング）。
  - テスト容易性のため、ネットワークオープナ（_urlopen）を差し替え可能に設計。
- スキーマ定義・初期化（src/kabusys/data/schema.py）。
  - DuckDB 用のスキーマを定義（Raw / Processed / Feature / Execution 層）。
  - raw_prices, raw_financials, raw_news, raw_executions などの Raw テーブル、prices_daily, market_calendar, fundamentals, news_articles, news_symbols 等の Processed テーブル、features / ai_scores の Feature テーブル、signals / signal_queue / orders / trades / positions / portfolio_performance 等の Execution テーブルを実装。
  - 適切なチェック制約（CHECK）・主キー・外部キーを付与。
  - 頻出クエリ向けのインデックス作成（複数）。
  - init_schema(db_path) によりディレクトリ作成からテーブル作成までを一括初期化（冪等）。get_connection は既存 DB への接続を返す。
- ETL パイプライン（src/kabusys/data/pipeline.py）。
  - ETLResult（dataclass）による結果集約（取得数、保存数、品質問題、エラー一覧等）。
  - 差分更新ロジック（DB 側の最終取得日を基に date_from を自動算出、backfill_days による差分再取得対応）。
  - 市場カレンダー先読みロジック、営業日補正ヘルパ（_adjust_to_trading_day）。
  - 単体ジョブ run_prices_etl（差分取得→保存→ログ出力）やテーブル存在チェック等の補助関数を提供。
- 運用・開発上の配慮。
  - ロギング（各モジュールで logger を使用、重要事象を info/warning/error で記録）。
  - バルク挿入のチャンク化による SQL 長・パラメータ数の抑制（_INSERT_CHUNK_SIZE）。
  - トランザクション管理による整合性確保（rollback on error）。
  - テスト容易性のためのフック（KABUSYS_DISABLE_AUTO_ENV_LOAD、id_token 注入、_urlopen の差し替え等）。

Security
- RSS パースに defusedxml を使用して XML 関連の脆弱性を軽減。
- SSRF 対策を実装（スキーム検証／プライベートアドレス拒否／リダイレクト検査）。
- .env 読み込み時に OS 環境変数を保護する protected 機構を導入。

Performance
- API 呼び出しに固定間隔スロットリングを導入してレート制限遵守。
- 大量データ挿入時にチャンク化して DB 操作のオーバーヘッドを低減。
- 冪等な INSERT（ON CONFLICT）により重複書込みを抑止。

Known issues
- run_prices_etl の戻り値に関してソース内の最終行が不完全（return 文が不完全な形で終わっている）ため、実行時に期待する (fetched, saved) のタプルが正しく返らない可能性があります。初期実装の不整合として注意してください。

Notes
- 初期リリースのため、将来的にエラーハンドリングの拡充（細かな例外分類・再試行ポリシーの設定化）やメトリクス収集（Prometheus 等）の導入が想定されます。
- DB スキーマや API の挙動は DataPlatform.md / DataSchema.md に準拠している想定です（コード内コメント参照）。

--------------------------------
（以上）