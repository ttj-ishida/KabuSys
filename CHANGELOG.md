CHANGELOG
=========

すべての注目すべき変更履歴をここに記載します。  
このファイルは「Keep a Changelog」形式に準拠しています。

[Unreleased]
------------

なし。

0.1.0 - 2026-03-18
-----------------

Initial release — 日本株自動売買システムのコア基盤を実装しました。

追加 (Added)
- パッケージ構成
  - kabusys パッケージの初期化（version 0.1.0、公開モジュール指定）。
- 設定管理 (kabusys.config)
  - .env ファイルおよび環境変数を自動読み込みする仕組みを実装（プロジェクトルートの探索は .git / pyproject.toml を基準）。
  - .env の行パース機能を実装（export プレフィックス、クォート、インラインコメント対応）。
  - .env と OS 環境変数の読み込み優先度を実装（OS > .env.local > .env）。自動ロードの無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD を追加。
  - Settings クラスを提供し、必要な設定値をプロパティ経由で取得（必須キーは未設定時に ValueError）。
  - 環境値検証（KABUSYS_ENV, LOG_LEVEL の許容値チェック）と便利プロパティ（is_live / is_paper / is_dev）を追加。
  - デフォルトの DB パス（DUCKDB_PATH / SQLITE_PATH）をサポート。
- J-Quants クライアント (kabusys.data.jquants_client)
  - J-Quants API から日次株価・四半期財務・市場カレンダーを取得するクライアントを実装。
  - レート制限対応（固定間隔スロットリング、120 req/min）。
  - リトライロジック（指数バックオフ、最大 3 回、408/429/5xx の再試行）と 429 の Retry-After への対応。
  - 401 受信時のトークン自動リフレッシュを実装（1 回のみリトライ）。
  - ページネーション対応（pagination_key を用いた完全取得）。
  - 取得タイムスタンプ（fetched_at）を UTC で記録し、Look-ahead Bias のトレースを可能に。
  - DuckDB へ冪等に保存する save_* 関数（ON CONFLICT DO UPDATE）を実装（raw_prices, raw_financials, market_calendar）。
  - 型変換ユーティリティ（_to_float, _to_int）を実装し、入力の頑健性を向上。
- ニュース収集 (kabusys.data.news_collector)
  - RSS フィードから記事を収集して raw_news に保存するパイプラインを実装。
  - URL 正規化とトラッキングパラメータ除去（_normalize_url）を実装。記事IDは正規化 URL の SHA-256 先頭32文字で生成。
  - defusedxml を用いた安全な XML パース（XML Bomb 等対策）。
  - SSRF 対策:
    - URL スキーム検証（http/https のみ許可）。
    - リダイレクト先のスキーム／ホスト検証を行うカスタムリダイレクトハンドラを実装。
    - リダイレクト先がプライベートアドレスの場合は拒否。
    - DNS 解決して A/AAAA レコードを検査し、プライベート/ループバック等を検出。
  - レスポンスサイズ上限 (MAX_RESPONSE_BYTES = 10MB) と gzip 解凍後のサイズ検査を実装（メモリDoS対策）。
  - テキスト前処理（URL 除去、空白正規化）と銘柄コード抽出（4桁数字、known_codes によりフィルタ）を実装。
  - DuckDB へ冪等保存する DB 関連関数を実装:
    - save_raw_news: INSERT ... RETURNING による新規挿入ID取得、チャンク挿入、トランザクション管理。
    - save_news_symbols / _save_news_symbols_bulk: 記事と銘柄コードの紐付けを一括挿入（ON CONFLICT DO NOTHING、RETURNING による正確な挿入数取得）。
  - デフォルト RSS ソースに Yahoo Finance のビジネスカテゴリを設定。
- DuckDB スキーマ定義 (kabusys.data.schema)
  - Raw / Processed / Feature / Execution の多層スキーマを定義する DDL を実装。
  - raw_prices, raw_financials, raw_news, raw_executions を含む Raw 層。
  - prices_daily, market_calendar, fundamentals, news_articles, news_symbols を含む Processed 層。
  - features, ai_scores を含む Feature 層。
  - signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance を含む Execution 層。
  - 適切な CHECK 制約・PRIMARY KEY・FOREIGN KEY を付与し、データ整合性を高めた設計。
  - 頻出クエリのためのインデックスを定義。
  - init_schema(db_path) でディレクトリ作成、全テーブル・インデックス作成を行う初期化関数を実装。get_connection() も提供。
- ETL パイプライン (kabusys.data.pipeline)
  - 差分更新（差分ETL）を実現するユーティリティ群を実装（最終取得日の取得、トレーディングデイ調整）。
  - get_last_* ヘルパー（raw_prices/raw_financials/market_calendar の最終日取得）。
  - run_prices_etl の骨組みを実装（差分計算、backfill_days オプション、取得→保存→ログ出力）。（ETLResult データクラスを定義）
  - ETLResult に品質問題・エラーの収集と to_dict 変換を実装。品質チェックは別モジュール (kabusys.data.quality) と連携する設計。

変更 (Changed)
- なし（初回リリースのため新規実装が中心）。

修正 (Fixed)
- なし（初回リリース）。

削除 (Removed)
- なし。

セキュリティ (Security)
- RSS パーサで defusedxml を使用し XML 関連攻撃を緩和。
- fetch_rss での応答サイズ上限と Gzip 展開後サイズチェックを導入し、メモリ DoS を防止。
- URL のスキーム検証およびリダイレクト先のプライベートアドレスチェックを導入し SSRF を防止。
- .env 読み込みでファイル読み込みエラーを警告し、安全にフォールバック。

互換性に関する注意 (Compatibility / Migration notes)
- 初期リリースのため互換性破壊の履歴はありません。
- 必須環境変数（設定がないと ValueError を送出）:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
- DuckDB 初期化は init_schema() を使用してください。既存 DB がある場合はスキーマ作成はスキップされます（冪等）。
- 自動 .env ロードを無効化する場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

既知の制限・TODO
- pipeline.run_prices_etl の戻り値/処理の一部が継続実装を想定しているため、追加の ETL ジョブ（財務・カレンダー・品質チェック統合）の実装が必要です。
- quality モジュールとの連携、監視／アラート（Slack 等）機能は別モジュールにて実装予定。

作者
- KabuSys 開発チーム

注: この CHANGELOG は現行コードベースから推測して作成しています。実際のリリースノートとして使用する場合は、リリース時の差分やパッケージ配布情報に合わせて調整してください。