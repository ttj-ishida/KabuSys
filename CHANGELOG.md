KEEP A CHANGELOG
All notable changes to this project will be documented in this file.

フォーマットは Keep a Changelog に準拠しています。  
次のバージョンに向けた未リリースの変更点は "Unreleased" セクションに記載します。

Unreleased
----------
- なし（初回リリース）

[0.1.0] - 2026-03-17
-------------------
Added
- パッケージ初期実装を追加（kabusys, data, strategy, execution, monitoring を公開）。
- 環境設定管理（kabusys.config）
  - .env / .env.local をプロジェクトルート（.git または pyproject.toml 基準）から自動読み込み（KABUSYS_DISABLE_AUTO_ENV_LOAD により無効化可能）。
  - .env の詳細なパース実装（export プレフィックス、シングル/ダブルクォート、インラインコメント、エスケープ対応）。
  - Settings クラスを提供し、J-Quants / kabu API / Slack / DB パス（DuckDB/SQLite）/実行環境（development/paper_trading/live）/ログレベルの取得とバリデーションを実装。
- J-Quants API クライアント（kabusys.data.jquants_client）
  - 株価日足、財務データ、JPX マーケットカレンダー取得用 API 呼び出しを実装。
  - レート制限対応（固定間隔スロットリングで 120 req/min を保証）。
  - リトライロジック（指数バックオフ、最大 3 回、408/429/5xx のリトライ対応、429 の Retry-After 優先）。
  - 401 の場合はリフレッシュトークンを用いた id_token 自動リフレッシュ（1 回のみ）を実装。
  - ページネーション対応（pagination_key の連続取得）。
  - DuckDB への保存関数（save_daily_quotes, save_financial_statements, save_market_calendar）を実装。ON CONFLICT DO UPDATE による冪等化。
  - データ変換ユーティリティ（_to_float, _to_int）を提供。
- ニュース収集モジュール（kabusys.data.news_collector）
  - RSS フィード取得・解析・前処理・DB保存のワークフローを実装（fetch_rss, save_raw_news, save_news_symbols, run_news_collection）。
  - URL 正規化（トラッキングパラメータ除去、クエリソート、フラグメント除去）と記事 ID の SHA-256（先頭32文字）による冪等化。
  - defusedxml を使った安全な XML パース（XML Bomb 対策）。
  - SSRF 対策: スキーム検証（http/https のみ許可）、ホストがプライベート/ループバック/リンクローカルでないことの検証、リダイレクト時の事前検査（カスタム RedirectHandler）。
  - レスポンスサイズ上限（MAX_RESPONSE_BYTES=10MB）と gzip 解凍後の再チェック（Gzip bomb 対策）。
  - DB 保存はチャンク化とトランザクションで実施し、INSERT ... RETURNING を用いて実際に挿入された件数を正確に返却。
  - 日本株の銘柄コード抽出ユーティリティ（extract_stock_codes）。
- DuckDB スキーマ定義（kabusys.data.schema）
  - Raw / Processed / Feature / Execution 層に対応するテーブル群を定義（raw_prices, raw_financials, raw_news, raw_executions, prices_daily, market_calendar, fundamentals, news_articles, news_symbols, features, ai_scores, signals, signal_queue, orders, trades, positions, portfolio_performance 等）。
  - 適切なチェック制約、主キー・外部キーを定義。
  - 頻出クエリ向けのインデックス定義を追加。
  - init_schema(db_path) によりディレクトリ作成とテーブル/インデックス作成を行う初期化ユーティリティを実装。get_connection() で既存 DB に接続可能。
- ETL パイプライン基盤（kabusys.data.pipeline）
  - ETL 実行結果を表す ETLResult dataclass を実装（品質問題・エラーの集約、辞書化のユーティリティ含む）。
  - DB の最終取得日取得ユーティリティ（get_last_price_date, get_last_financial_date, get_last_calendar_date）を実装。
  - 取引日補正ヘルパー（_adjust_to_trading_day: 非営業日の場合は直近営業日に調整）を実装。
  - run_prices_etl を含む差分更新ロジックを実装（最終取得日からの backfill 処理、_MIN_DATA_DATE, _DEFAULT_BACKFILL_DAYS の概念を導入）。
  - 品質チェックモジュール（quality）との連携を想定した設計（品質チェックで致命的問題が検出されても全件収集を継続する方針）。

Security
- RSS パーサーに defusedxml を採用し XML 脅威を軽減。
- SSRF 対策を多層で実装（スキーム検証・ホストプライベート判定・リダイレクト時検査）。
- HTTP レスポンス長を制限しメモリ DoS / Gzip bomb を防止。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Deprecated
- なし

Removed
- なし

Known issues / Notes
- run_prices_etl の戻り値に関する実装上の問題:
  - 提供されたコードでは run_prices_etl の末尾が "return len(records)," のように途中で切れており、(fetched, saved) の形で保存件数を返すべき箇所が未完であるため、呼び出し側が期待するタプルを返していません。次回リリースで修正が必要です。
- pipeline モジュールは quality モジュールを参照していますが、quality の実装はこの差分では含まれていません。統合テスト時に実装/インターフェイス確認が必要です。
- 初期実装のため、ユニットテスト・エンドツーエンドテストの整備、例外発生時のリトライ/アラートポリシーの調整、監視（monitoring）・実行モジュールの実装が今後の作業項目です。

作者メモ / 次回対応予定
- run_prices_etl の戻り値バグ修正と単体テスト追加。
- pipeline の他 ETL ジョブ（financials, calendar）の完成と品質チェック連携の実装。
- strategy / execution / monitoring パッケージの実装と統合テスト。
- ドキュメント（DataPlatform.md, API 利用手順、運用手順）の整備。

--- End of changelog ---