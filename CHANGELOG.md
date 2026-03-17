Keep a Changelog に準拠した形式でこのコードベースから推測される変更履歴（日本語）を作成しました。初回リリース向けのエントリとしてまとめ、実装上の注意点（既知の問題）も併記しています。

CHANGELOG.md
============

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは Keep a Changelog に準拠しています。  

記録方針:
- バージョンごとに「Added / Changed / Fixed / Security / Deprecated / Removed」などのセクションで要約します。
- 初回リリース（0.1.0）はコードベースから推測できる機能をまとめています。

Unreleased
----------

- 現在未リリースの変更はありません。

[0.1.0] - 2026-03-17
--------------------

Added
- パッケージの初期リリース。
  - パッケージ名: kabusys、バージョン: 0.1.0
- 環境設定管理モジュール（kabusys.config）
  - .env / .env.local 自動読み込み機能（プロジェクトルートを .git または pyproject.toml から探索）。
  - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - .env 読み込み時は OS 環境変数を保護（既存キーは上書きしない）し、.env.local は上書き可能。
  - .env のパースは export キーワード、クォート、エスケープ、インラインコメントなどに対応。
  - Settings クラスを提供（プロパティ経由でアプリ設定にアクセス）。
    - J-Quants / kabu API / Slack / DB パス等のプロパティを用意。
    - KABUSYS_ENV（development/paper_trading/live）や LOG_LEVEL の値検証を実装。
    - duckdb/sqlite のデフォルトパスの提供（expanduser 対応）。
- J-Quants API クライアント（kabusys.data.jquants_client）
  - API ベースURLと認証（リフレッシュトークン → idToken）をサポート。
  - レート制御: 固定間隔スロットリング (_RateLimiter)、デフォルト 120 req/min。
  - リトライ: 指数バックオフ、最大 3 回、408/429/5xx を再試行対象に設定。
  - 401 応答時の自動 id_token リフレッシュ（1 回のみ）を実装。
  - ページネーション対応の取得関数:
    - fetch_daily_quotes（株価日足）
    - fetch_financial_statements（四半期財務）
    - fetch_market_calendar（JPX カレンダー）
  - DuckDB への冪等保存関数:
    - save_daily_quotes（raw_prices、ON CONFLICT DO UPDATE）
    - save_financial_statements（raw_financials、ON CONFLICT DO UPDATE）
    - save_market_calendar（market_calendar、ON CONFLICT DO UPDATE）
  - データ型変換ユーティリティ: _to_float / _to_int（厳密なルール付）
  - 取得時刻（fetched_at）は UTC で記録し、Look-ahead bias 防止を意識。
- ニュース収集モジュール（kabusys.data.news_collector）
  - RSS フィードからの記事取得・整形・DB保存ワークフローを実装。
  - デフォルトRSSソース: Yahoo Finance のビジネスカテゴリを含む DEFAULT_RSS_SOURCES。
  - セキュリティ対策:
    - defusedxml を用いた XML パース（XML Bomb 対策）。
    - SSRF 対策: リダイレクトハンドラでスキーム/ホスト検査、ホストがプライベートIPか確認。
    - 許可スキームを http/https に限定。
    - レスポンスサイズ上限（MAX_RESPONSE_BYTES = 10MB）を設け、超過はスキップ（Gzip を含む）。
    - URL 正規化でトラッキングパラメータ除去（utm_* 等）を実施。
  - 記事ID は正規化 URL の SHA-256 ハッシュ（先頭32文字）で生成し冪等性を担保。
  - fetch_rss：RSS 取得・パース・記事整形（title/content の前処理、pubDate パース）を提供。
  - save_raw_news：DuckDB に対してチャンク INSERT を行い、INSERT ... RETURNING で新規挿入 ID を返す（トランザクションでまとめる）。
  - save_news_symbols / _save_news_symbols_bulk：記事と銘柄コードの紐付けを一括登録（ON CONFLICT DO NOTHING、RETURNING で挿入数を正確に取得）。
  - 銘柄コード抽出機能: 4桁数字パターンを抽出し、known_codes に基づきフィルタ（extract_stock_codes）。
- データベーススキーマ定義（kabusys.data.schema）
  - DuckDB 用のスキーマ（Raw / Processed / Feature / Execution レイヤ）を定義。
  - raw_prices, raw_financials, raw_news, raw_executions など Raw レイヤテーブルを定義。
  - prices_daily, market_calendar, fundamentals, news_articles, news_symbols など Processed レイヤを定義。
  - features, ai_scores など Feature レイヤを定義。
  - signals, signal_queue, orders, trades, positions, portfolio_performance など Execution レイヤを定義。
  - 各種制約（PRIMARY KEY, CHECK 等）やインデックスを定義し、頻出クエリに備える。
  - init_schema(db_path)：親ディレクトリ自動作成、全 DDL/インデックスを実行して DuckDB 接続を返す（冪等）。
  - get_connection(db_path)：既存 DB への接続取得（初期化は行わない）。
- ETL パイプライン（kabusys.data.pipeline）
  - ETLResult データクラス（target_date / fetched/saved カウント / 品質問題 / エラーリスト等）を提供。
  - 差分更新用ユーティリティ:
    - get_last_price_date / get_last_financial_date / get_last_calendar_date。
    - _adjust_to_trading_day（カレンダー情報に基づく営業日調整）。
  - run_prices_etl（株価差分 ETL）の骨組みを実装:
    - 最終取得日を参照して差分（バックフィル）を算出、fetch + save を実行する設計。
    - デフォルト backfill_days = 3、最小データ日付は 2017-01-01。
  - 品質チェックモジュール（quality）へのフック（品質問題は ETLResult に蓄積する設計）。
- パッケージ構成
  - 空の __init__.py が strategy/ execution / data の各サブパッケージに配置され、拡張の土台を用意。

Changed
- N/A（初回リリースのため該当なし）

Fixed
- N/A（初回リリースのため該当なし）

Security
- defusedxml を用いた XML パース、SSRF ガード、レスポンスサイズ制限などを実装。
- .env 読み込みで OS 環境変数保護を実施。

Known issues / Notes
- run_prices_etl の戻り値：
  - ソースコード末尾付近で run_prices_etl が "return len(records)," のように (tuple の片方のみ) を返している箇所が確認されます（saved を返すべき箇所が欠落している）。この点は呼び出し側 API を想定した戻り値 (fetched_count, saved_count) と整合しないため修正が必要です。
- テストと例外シナリオ：
  - ネットワーク/HTTP の一部のエラーでログ出力は行われるが、リトライやフォールバックの調整が運用実績に基づいてチューニングされる可能性があります。
- news_collector の DNS 解決失敗時の取り扱い：
  - DNS 解決が失敗した場合は安全側（非プライベート）として扱う実装になっているため、ネットワーク設定次第で想定外のホストにアクセスする可能性は低いが、運用環境のポリシーに応じた追加制限を検討してください。
- データ型変換:
  - _to_int の仕様は "1.0" のような文字列を許容する一方、"1.9" のような小数表現は None を返す仕様です。データのソースに応じて期待挙動を確認してください。

Authors / Contributors
- コードベースから著者情報は取得できません。内部実装に基づき初回リリースとしてまとめました。

ライセンス
- コード中にライセンス記載がないため、この CHANGELOG でも明記していません。配布時にはライセンス情報を追加してください。

---

必要であれば次の追加作業を提案します：
- run_prices_etl の戻り値修正とそれに伴うユニットテストの追加。
- jquants_client と news_collector のエンドツーエンドテスト（モックによる外部 API / ネットワークリクエストの代替）。
- schema と ETL の互換性テスト（実際の DuckDB を用いた統合テスト）。
- ドキュメント（README / DataPlatform.md / DataSchema.md 参照文書）の整備。