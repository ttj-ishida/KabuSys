# CHANGELOG

全ての日付はリポジトリの初期リリース（バージョン 0.1.0）の想定日として 2026-03-18 を使用しています。  
本ファイルは Keep a Changelog の記法に準拠しています。

## [Unreleased]
- 次期リリースで追加予定:
  - strategy / execution モジュールの本実装（現状はパッケージ初期化のみ）
  - ETL パイプラインの品質チェック（quality モジュール連携）の更なる拡充
  - テストカバレッジとモック用フックの追加

## [0.1.0] - 2026-03-18

### Added
- パッケージ初期リリース: kabusys (日本株自動売買システム) の骨組みを追加。
  - src/kabusys/__init__.py にパッケージバージョンと公開モジュール一覧を追加。

- 環境設定管理 (src/kabusys/config.py)
  - .env ファイルと環境変数の自動ロード機能を実装。
    - プロジェクトルート検出は __file__ を起点に .git または pyproject.toml を探索（CWD 非依存）。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - 環境変数自動ロードを無効化するための KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - .env パーサー実装（export 構文、シングル／ダブルクォート、インラインコメント考慮）。
  - Settings クラスを提供し、必須値取得（_require）、各種プロパティ（J-Quants, kabu API, Slack, DB パス, 環境, ログレベル等）を型安全に取得。
  - KABUSYS_ENV と LOG_LEVEL の検証（許容値チェック）を実装。

- J-Quants API クライアント (src/kabusys/data/jquants_client.py)
  - API 呼び出し共通処理を実装（HTTP リクエスト、JSON デコード）。
  - レート制限制御: 固定間隔スロットリング（120 req/min）を実装する _RateLimiter。
  - 再試行ロジック: 指数バックオフ、最大 3 回、408/429/5xx に対するリトライを実装。429 の場合は Retry-After ヘッダを優先。
  - 401 Unauthorized 受信時にリフレッシュトークンで自動再取得して 1 回リトライする処理を実装（無限再帰回避のため allow_refresh フラグあり）。
  - ID トークンのモジュールレベルキャッシュ（ページネーション間でトークン共有）を実装。
  - データ取得 API:
    - fetch_daily_quotes（株価日足、ページネーション対応）
    - fetch_financial_statements（四半期財務、ページネーション対応）
    - fetch_market_calendar（JPX マーケットカレンダー）
  - DuckDB への冪等保存関数:
    - save_daily_quotes: raw_prices テーブルへ INSERT ... ON CONFLICT DO UPDATE
    - save_financial_statements: raw_financials へ同様
    - save_market_calendar: market_calendar へ同様
  - データ整形ユーティリティ (_to_float / _to_int) を提供（空値や不正値に安全）。

- ニュース収集モジュール (src/kabusys/data/news_collector.py)
  - RSS フィード収集と DuckDB への保存処理を実装。
  - セキュリティ対策:
    - defusedxml を使った XML パース（XML Bomb 対策）。
    - SSRF 対策: リダイレクト時および初期 URL 検証でスキーム（http/https のみ）とプライベートアドレスのアクセス禁止。
    - リダイレクト検査用ハンドラ (_SSRFBlockRedirectHandler) 実装。
    - 受信サイズ上限（MAX_RESPONSE_BYTES = 10MB）によるメモリ DoS 対策。gzip 解凍後も検査。
    - URL 正規化とトラッキングパラメータ除去（_normalize_url）。
  - 記事 ID は URL 正規化後の SHA-256 先頭 32 文字を採用して冪等性を保証。
  - fetch_rss: RSS の安全な取得と記事整形（title, content, pubDate のパース）を実装。
  - DB 保存:
    - save_raw_news: INSERT ... ON CONFLICT DO NOTHING + RETURNING を用い、実際に挿入された記事 ID を返す（チャンク化して 1 トランザクションで挿入）。
    - save_news_symbols / _save_news_symbols_bulk: 記事と銘柄の紐付けを INSERT ... ON CONFLICT で実装（RETURNING で挿入数を把握）。
  - 銘柄抽出: 4 桁数字パターンから既知銘柄セットに基づく抽出関数 extract_stock_codes を実装。
  - run_news_collection: 複数 RSS ソースの収集を管理し、各ソースを独立してエラーハンドリング。known_codes による銘柄紐付けに対応。

- DuckDB スキーマ定義 & 初期化 (src/kabusys/data/schema.py)
  - Raw / Processed / Feature / Execution 層それぞれのテーブル DDL を実装。
  - 主なテーブル:
    - raw_prices, raw_financials, raw_news, raw_executions
    - prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - features, ai_scores
    - signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 制約（PRIMARY KEY, CHECK, FOREIGN KEY）を豊富に定義してデータ整合性を担保。
  - インデックス定義（頻出クエリ向け）を追加。
  - init_schema(db_path) により DB ファイルの親ディレクトリを自動作成し、全 DDL とインデックスを作成して接続を返す。
  - get_connection(db_path) による既存 DB への接続を提供。

- ETL パイプライン (src/kabusys/data/pipeline.py)
  - ETLResult データクラスを追加し、ETL 実行結果（取得数、保存数、品質問題、エラー）を一元管理。
  - 差分更新のためのユーティリティ:
    - テーブル存在チェック _table_exists、最大日付取得 _get_max_date
    - market_calendar を用いた営業日調整 _adjust_to_trading_day
    - get_last_price_date / get_last_financial_date / get_last_calendar_date
  - run_prices_etl: 差分ETL（最終取得日から backfill 日数分を遡って再取得するロジック）を実装。J-Quants クライアント経由で取得して保存。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- RSS パーサーで defusedxml を採用し、XML 関連の脆弱性を軽減。
- RSS/HTTP 部分で SSRF 対策（スキーム検証、プライベートアドレス拒否、リダイレクト検査）を実装。
- 大きすぎるレスポンスや gzip ボムを検出して安全にスキップするロジックを追加。

### Notes / Known issues
- strategy および execution パッケージは present だが主要な実装は未実装（将来的な実装予定）。
- ETL の品質チェック周り（quality モジュール依存）はパイプラインから参照されているが、quality モジュールの詳細実装は別途管理される想定。
- 一部 API や関数はユニットテスト用にモック差替え可能な設計（例: news_collector._urlopen）を採用しているが、テスト用ヘルパーは今後整備予定。

---

本 CHANGELOG は、現行コードベースの内容から推測して記載しました。実際のコミット履歴やリリースノートに基づく調整が必要な場合はお知らせください。