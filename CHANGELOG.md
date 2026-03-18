Keep a Changelog
=================

すべての注目すべき変更を時系列で記載します。  
フォーマットは「Keep a Changelog」に準拠しています。

[Unreleased]
------------

（なし）

[0.1.0] - 2026-03-18
--------------------

初期公開リリース。日本株自動売買システム「KabuSys」のコアライブラリを実装しました。主な追加点・仕様は以下の通りです。

Added
- パッケージ構成
  - kabusys パッケージを追加（バージョン: 0.1.0）。
  - __all__ に data, strategy, execution, monitoring を公開。

- 環境設定管理 (kabusys.config)
  - .env ファイルと環境変数から設定を読み込む自動読み込み機能を実装。
  - 自動ロードの検索はパッケクトルート (.git または pyproject.toml) を基準に行い、CWD に依存しない実装。
  - 読み込み優先順位: OS環境変数 > .env.local > .env。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能（テスト用途）。
  - .env パーサーの強化: export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、行内コメント処理をサポート。
  - Settings オブジェクトを提供。主なプロパティ:
    - jquants_refresh_token, kabu_api_password, kabu_api_base_url
    - slack_bot_token, slack_channel_id
    - duckdb_path（デフォルト data/kabusys.duckdb）, sqlite_path（デフォルト data/monitoring.db）
    - env（development/paper_trading/live の検証）、log_level（DEBUG/INFO/... の検証）
    - is_live / is_paper / is_dev ヘルパー

- J-Quants API クライアント (kabusys.data.jquants_client)
  - API 呼び出しを行うユーティリティを実装（_request, get_id_token）。
  - レート制御: 固定間隔スロットリングで 120 req/min を尊重する RateLimiter を実装。
  - リトライ: 指数バックオフ付きのリトライロジック（最大 3 回）。対象: ネットワーク系エラーと 408/429/5xx。
  - 401 Unauthorized を検出した場合、自動でリフレッシュして 1 回再試行（無限再帰を防止する allow_refresh 制御）。
  - ページネーション対応のデータ取得関数:
    - fetch_daily_quotes（株価日足）
    - fetch_financial_statements（財務データ）
    - fetch_market_calendar（JPX マーケットカレンダー）
  - DuckDB への冪等保存関数（ON CONFLICT DO UPDATE）:
    - save_daily_quotes, save_financial_statements, save_market_calendar
  - データ変換ユーティリティ: _to_float, _to_int（文字列/数値混在を安全に扱う）

- ニュース収集モジュール (kabusys.data.news_collector)
  - RSS フィードからニュース記事を安全に収集する実装。
  - セキュリティ対策:
    - defusedxml を利用して XML Bomb 等を防止
    - URL スキーム検証（http/https のみ許可）
    - リダイレクト先のスキームとホストを事前検証するカスタムリダイレクトハンドラ（SSRF 対策）
    - レスポンス最大サイズ制限（MAX_RESPONSE_BYTES = 10MB）、gzip 解凍後のサイズ検査（Gzip bomb 対策）
    - ホストがプライベート/ループバック/リンクローカルであれば拒否
  - URL 正規化とトラッキングパラメータ削除（utm_* 等を除去）および SHA-256（先頭32文字）から記事ID生成。
  - テキスト前処理（URL 除去、空白正規化）。
  - DB 保存:
    - save_raw_news: チャンク挿入 + トランザクション + INSERT ... ON CONFLICT DO NOTHING RETURNING id（実際に挿入された記事IDを返す）
    - save_news_symbols / _save_news_symbols_bulk: 記事と銘柄コードの紐付けをバルク挿入（ON CONFLICT で重複排除）
  - 銘柄コード抽出: 4桁数字パターンから既知銘柄集合に基づいて抽出する extract_stock_codes。
  - run_news_collection: 複数 RSS ソースを順次処理し、新規保存数を集計。個々のソースは独立してエラーハンドリング（1ソース失敗で他を継続）。

- DuckDB スキーマ定義 (kabusys.data.schema)
  - DataPlatform.md に基づいた 3 層構造+実行レイヤーのテーブル定義を実装。
  - Raw / Processed / Feature / Execution 層の DDL を提供:
    - raw_prices, raw_financials, raw_news, raw_executions
    - prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - features, ai_scores
    - signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 頻出パターン向けのインデックス定義
  - init_schema(db_path) でディレクトリ作成→テーブル/インデックス作成を行い接続を返す（冪等）
  - get_connection(db_path) で既存 DB へ接続（スキーマ初期化は行わない）

- ETL パイプライン（kabusys.data.pipeline）
  - ETLResult データクラスによる処理結果の集約（品質問題とエラー概要を含む）
  - 差分更新用ユーティリティ:
    - get_last_price_date / get_last_financial_date / get_last_calendar_date
    - _adjust_to_trading_day: 非営業日を直近営業日に調整
  - run_prices_etl: 株価差分 ETL（最終取得日からの backfill を考慮して差分取得→保存）。品質チェックモジュール（quality）との統合ポイントあり。
  - 設計上の方針: デフォルト backfill_days=3、calendar は先読み設定あり、品質チェックは Fail-Fast ではなく検出情報を返すスタイル。

Security
- RSS の XML 処理に defusedxml を採用し、XML に起因する脆弱性を緩和。
- SSRF 対策: URL スキーム検証、ホストのプライベートアドレス判定、リダイレクト先検査を実装。
- レスポンスの最大バイト数制限（10MB）と gzip 解凍後の再検査によりメモリ/圧縮爆弾攻撃を緩和。
- J-Quants クライアントは認証トークンの自動リフレッシュ機構を持ち、無限再帰を回避する設計。

Performance / Reliability
- API レート制御（120 req/min）を RateLimiter で実装。
- 冪等性を重視した DuckDB 保存（ON CONFLICT DO UPDATE / DO NOTHING）により再実行可能に。
- ニュース保存はチャンク化（_INSERT_CHUNK_SIZE）して SQL 長やパラメータ数を抑制。
- ネットワーク障害や一時的エラーに対して指数バックオフ付きリトライを実装。

Notes / Usage
- 必須環境変数（例）:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
- DuckDB を使う前に init_schema() でスキーマ初期化することを推奨。
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動 .env 読み込みを無効化可能。
- news_collector.fetch_rss は不正なフィードや大きすぎるレスポンスを検出した場合、空リストを返すことで安全に失敗する。
- pipeline モジュールは quality モジュールに依存しており、品質チェックの実装により ETL の挙動をさらに強化できる設計。

Known limitations / TODO
- strategy, execution, monitoring パッケージの実装は現状ほとんど存在しない（パッケージは公開されているが中身は未実装または空 init）。
- pipeline.run_prices_etl は差分取得ロジックを実装済みだが、プロダクション運用に必要な追加ジョブ（features 生成、AI スコア計算、シグナル生成→発注処理との統合）は今後実装予定。
- quality モジュールは参照されているが、本リリースに含まれる実装は限定的（詳細実装は別途実装予定）。

Breaking Changes
- なし（初期リリース）

Contributors
- 実装コードをもとに CHANGELOG を作成しました。

---  
この CHANGELOG はコードベースの内容から推測して作成しています。実際のリリースノートとして用いる場合は、差分確認や運用上のドキュメント整備を併せてご確認ください。