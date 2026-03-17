CHANGELOG
=========
All notable changes to this project will be documented in this file.
This project adheres to "Keep a Changelog" and is maintained under
semantic versioning.

[Unreleased]
------------

Added
- ドキュメント化されていない小さな修正や未完成APIの存在を明記（内部テスト用のフラグやモックポイント）。
- テスト容易性のために一部関数（例: news_collector._urlopen）を差し替え可能に実装。

Known issues / TODO
- run_prices_etl の戻り値が (fetched, saved) のタプルを返す想定だが、現状の実装では fetched のみを含む単要素タプルを返している（saved が返されない）。ETL 呼び出し側での扱いに注意が必要。
- strategy/ と execution/ パッケージはプレースホルダ（__init__.py が空）で、戦略・発注ロジックは未実装。
- 単体テスト・統合テストはコード中にテストフックがあるが、実際のテストケースの同梱はまだ。

0.1.0 - 2026-03-17
------------------

Added
- パッケージの初期リリース。
  - パッケージ名: kabusys、__version__ = "0.1.0" を定義。
- 環境設定管理 (kabusys.config)
  - .env ファイルと環境変数から設定値を読み込む自動ロード機能を実装。
  - ルート検出ロジック: .git または pyproject.toml を起点にプロジェクトルートを特定。
  - .env パーサ: export 形式、シングル/ダブルクォート、エスケープ、インラインコメントを考慮してパース。
  - 自動ロードの無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - Settings クラスを公開: J-Quants / kabu API / Slack / DB パス / 環境モード / ログレベル等のプロパティとバリデーションを提供。
- J-Quants クライアント (kabusys.data.jquants_client)
  - API 呼び出しユーティリティ（_request）を実装。JSON デコードエラーの明示的エラー処理を追加。
  - レート制限: 固定間隔スロットリングで 120 req/min を遵守する RateLimiter を導入。
  - 再試行戦略: 指数バックオフ、最大 3 回、HTTP 408/429/5xx を対象にリトライ。
  - 401 レスポンス時にリフレッシュトークンで自動的に ID トークンをリフレッシュして 1 回リトライ。
  - ID トークンのモジュールレベルキャッシュを導入（ページネーション間で共有）。
  - ページネーション対応のデータ取得関数を実装:
    - fetch_daily_quotes（株価日足 / OHLCV）
    - fetch_financial_statements（四半期財務）
    - fetch_market_calendar（JPXカレンダー）
  - DuckDB への冪等保存ロジック（ON CONFLICT DO UPDATE）:
    - save_daily_quotes, save_financial_statements, save_market_calendar を提供。
  - 値変換ユーティリティ: _to_float, _to_int（厳密な変換ルール）。
- ニュース収集モジュール (kabusys.data.news_collector)
  - RSS フィードの取得と raw_news への保存機能を実装。
  - セキュリティ対策:
    - defusedxml を用いた XML パース（XML Bomb 等の防御）。
    - リダイレクト時にスキームとホストを検証するカスタム RedirectHandler（SSRF 対策）。
    - URL スキーム検証（http/https のみ許可）。
    - ホストがプライベート/ループバック/リンクローカル/マルチキャストの場合はアクセス拒否。
    - レスポンスサイズ上限（10 MB）を設け、gzip 解凍後も検査（Gzip bomb 対策）。
  - URL 正規化と記事ID生成:
    - トラッキングパラメータ（utm_*, fbclid 等）を除去して正規化し、SHA-256 の先頭32文字を記事IDに採用（冪等性確保）。
  - テキスト前処理: URL 除去、空白正規化を提供。
  - DB 保存:
    - save_raw_news: INSERT ... RETURNING を使い、実際に挿入された記事IDを返す（チャンク分割、トランザクションまとめ）。
    - save_news_symbols / _save_news_symbols_bulk: 記事と銘柄コードの紐付けを一括挿入（ON CONFLICT DO NOTHING、RETURNINGで挿入数検知）。
  - 銘柄コード抽出ユーティリティ: 4桁数字パターンから既知銘柄セットに基づき抽出（重複排除）。
  - 統合ジョブ: run_news_collection（複数ソースからの収集→保存→銘柄紐付け。ソース単位で独立エラーハンドリング）。
  - デフォルト RSS ソース: Yahoo Finance のビジネスカテゴリを設定。
- DuckDB スキーマ定義 (kabusys.data.schema)
  - Raw / Processed / Feature / Execution の 3 層＋実行層のテーブルを網羅的に定義。
  - 主なテーブル:
    - raw_prices, raw_financials, raw_news, raw_executions
    - prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - features, ai_scores
    - signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 制約（PRIMARY KEY、CHECK）、外部キー、インデックスを定義してクエリ性能とデータ整合性を強化。
  - init_schema(db_path) を提供し、親ディレクトリ自動作成や全テーブル・インデックスの作成を行う。
  - get_connection(db_path) で既存 DB へ接続可能。
- ETLパイプライン (kabusys.data.pipeline)
  - ETLResult dataclass による実行結果表現（取得数、保存数、品質問題、エラー一覧）。
  - 差分更新のためのヘルパー関数:
    - get_last_price_date, get_last_financial_date, get_last_calendar_date
  - 市場カレンダーを参照して指定日を直近の営業日に調整する _adjust_to_trading_day の導入。
  - run_prices_etl の実装（差分算出、backfill の取り扱い、fetch/save の呼び出し）。※（既知の問題: saved の戻り値扱いに注意）
- ロギング:
  - 主要処理（fetch/save/ETL/run_news_collection 等）で info/warning/exception を出力するようログを充実。

Security
- RSS/XML のパースに defusedxml を採用し、XML ベース攻撃を軽減。
- SSRF 対策: リダイレクト先のスキーム/ホスト検査、初期ホスト検証、プライベートIP拒否。
- レスポンスサイズ上限（MAX_RESPONSE_BYTES）と gzip 解凍後検査によるメモリDoS対策。
- .env 読み込み時に OS 環境変数を保護する protected 機構（上書き制御）。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Deprecated / Removed
- （初回リリースのため該当なし）

Notes
- DuckDB を利用した設計で、データの冪等保存・トランザクション管理・INSERT ... RETURNING を活用しているため、データ収集の再実行や並列実行を想定した堅牢性がある。
- 実運用では環境変数（JQUANTS_REFRESH_TOKEN / KABU_API_PASSWORD / SLACK_BOT_TOKEN / SLACK_CHANNEL_ID など）を適切に設定する必要あり（Settings クラスが未設定時は ValueError を出す）。
- pipeline/run_prices_etl の戻り値に関する挙動は注意（上記 Known issues 参照）。この点は次回リリースで修正予定。

----- End of CHANGELOG -----