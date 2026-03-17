Keep a Changelog に準拠した形式で、このコードベースの初回リリース向け CHANGELOG.md を作成しました。リリース日には現在の日付（2026-03-17）を使用しています。必要に応じて日付や記載内容を調整してください。

KEEP A CHANGELOG
All notable changes to this project will be documented in this file.

[0.1.0] - 2026-03-17
====================

Added
-----
- パッケージ基盤
  - kabusys パッケージ初期化（__version__ = 0.1.0）。モジュール構成: data, strategy, execution, monitoring をエクスポート。

- 環境設定（kabusys.config）
  - .env ファイルまたは環境変数から設定を自動読み込みする仕組みを実装。
    - プロジェクトルートは .git または pyproject.toml を基準に探索（CWD に依存しない）。
    - 読み込み順序: OS 環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
  - .env 行パーサを実装（export プレフィックス、クォート内のエスケープ、インラインコメント処理に対応）。
  - Settings クラスを実装し、J-Quants / kabu API / Slack / DB パス / 環境種別 / ログレベルなどのプロパティを提供。必須環境変数未設定時は ValueError を送出。
  - 有効な環境種別（development, paper_trading, live）とログレベル検証を実装。

- J-Quants クライアント（kabusys.data.jquants_client）
  - API 通信基盤を実装（エンドポイント: https://api.jquants.com/v1）。
  - レート制御（固定間隔スロットリング）で 120 req/min を遵守する RateLimiter を導入。
  - リトライロジックを実装（指数バックオフ、最大 3 回。対象: 408/429/5xx、429 は Retry-After を考慮）。
  - 401 受信時にリフレッシュトークンから自動で id_token を更新して 1 回だけ再試行するロジックを実装（無限再帰防止）。
  - ページネーション対応の取得関数:
    - fetch_daily_quotes（株価日足）
    - fetch_financial_statements（四半期財務）
    - fetch_market_calendar（JPX カレンダー）
  - DuckDB への保存関数（冪等性を考慮した INSERT ... ON CONFLICT DO UPDATE）:
    - save_daily_quotes（raw_prices）
    - save_financial_statements（raw_financials）
    - save_market_calendar（market_calendar）
  - データ変換ユーティリティ (_to_float, _to_int) を実装（安全な変換・空値処理・小数切捨て防止の取り扱い）。

- ニュース収集（kabusys.data.news_collector）
  - RSS フィードからニュース記事を取得して raw_news に保存する機能を実装。
  - セキュリティ対策:
    - defusedxml を利用した XML パース（XML Bomb 等への対策）。
    - SSRF 対策: URL スキーム検証（http/https のみ）、ホスト/IP のプライベート判定（DNS 解決して A/AAAA を検査）、リダイレクト先検査（カスタム RedirectHandler）。
    - レスポンスサイズ上限（MAX_RESPONSE_BYTES = 10 MB）と gzip 解凍後のサイズチェック（Gzip bomb 対策）。
  - URL 正規化（トラッキングパラメータ除去、フラグメント削除、キーソート）と記事ID生成（正規化 URL の SHA-256 先頭32文字）を導入し、冪等性を確保。
  - テキスト前処理（URL 削除、空白正規化）。
  - DB 保存:
    - save_raw_news: INSERT ... RETURNING id を用い、挿入された記事IDのみを返す。チャンク分割と1トランザクションでのコミットを実装。
    - save_news_symbols / _save_news_symbols_bulk: 記事と銘柄コードの紐付けを一括保存（ON CONFLICT DO NOTHING、RETURNING による実挿入数取得）。
  - 銘柄コード抽出ロジック（4桁数字パターンを抽出し、既知コードセットと照合して重複除去して返す）。
  - デフォルト RSS ソース（例: Yahoo Finance カテゴリの RSS）を設定。

- DuckDB スキーマ（kabusys.data.schema）
  - DataPlatform 設計に基づく 3 層（Raw / Processed / Feature）＋Execution 層のスキーマ DDL を実装。
  - 主なテーブル:
    - Raw: raw_prices, raw_financials, raw_news, raw_executions
    - Processed: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature: features, ai_scores
    - Execution: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 制約（PRIMARY KEY, CHECK, FOREIGN KEY）とインデックス（頻出クエリ向け）を定義。
  - init_schema(db_path) によりディレクトリ作成→テーブル作成→インデックス適用まで自動初期化する API を提供。get_connection() で既存 DB へ接続可能。

- ETL パイプライン（kabusys.data.pipeline）
  - ETL の設計に基づく差分更新パイプラインの下地を実装。
  - ETLResult データクラスを導入し、取得数・保存数・品質問題・エラーを集約して返却可能に。
  - 差分検出ユーティリティ:
    - get_last_price_date / get_last_financial_date / get_last_calendar_date
  - 市場カレンダーに基づく営業日補正関数 (_adjust_to_trading_day) を実装。
  - run_prices_etl: 日足差分 ETL の基本実装（最終取得日から backfill_days 前を date_from とするロジック、J-Quants からの取得→保存まで）。

Changed
-------
- 初回リリースのため変更履歴はなし。

Fixed
-----
- 初回リリースのため修正履歴はなし。

Security
--------
- news_collector にて複数の SSRF / XML / DoS 緩和策を実施:
  - defusedxml の利用、レスポンスサイズ制限、gzip 解凍後のサイズ検査、スキーム制限、プライベートアドレス検査、リダイレクト前の検査。
- 環境変数自動読み込みは明示フラグで無効化可能（テスト時などの安全策）。

Notes / Known limitations
-------------------------
- 現時点は初期実装であり、以下は今後の改善候補:
  - ETL 全体の統合ジョブ（run_financials_etl, run_calendar_etl 等）の完成度向上と品質チェックモジュール（kabusys.data.quality）との連携拡充。
  - unit テスト・統合テストの追加（外部 API やネットワーク依存部のモック化）。
  - jquants_client のレートリミッティングはプロセス内の単純スロットリング実装のため、分散実行時の共有制御が必要なら外部レートリミッタ導入を検討。
  - NewsCollector の既知銘柄リスト (known_codes) の取得・更新手法（別途シンクロナイズ処理が必要）。

署名
----
- initial implementation — kabusys 0.1.0

（補足）必要であれば英語版や更に細かいモジュール単位の変更履歴、リリースノート向けの短いハイライト文言なども作成できます。