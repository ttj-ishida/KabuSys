# Changelog

すべての変更は Keep a Changelog の形式に従い、セマンティックバージョニングを採用しています。  
このファイルには主にコードベースから推測できる機能追加・設計方針・重要実装点をまとめています。

## [Unreleased]

## [0.1.0] - 2026-03-17

初期リリース — KabuSys: 日本株自動売買システムの基礎実装を追加。

### Added
- パッケージ基盤
  - パッケージメタ情報（kabusys.__version__ = 0.1.0）と公開モジュール一覧を追加。
- 設定管理（kabusys.config）
  - .env ファイルおよび環境変数の自動読み込み機能を実装（プロジェクトルートを .git または pyproject.toml から検出）。
  - .env/.env.local の読み込み順序（OS環境変数 > .env.local > .env）、および自動ロード無効化フラグ（KABUSYS_DISABLE_AUTO_ENV_LOAD）をサポート。
  - .env パーサ（export対応、クォート／エスケープ、インラインコメント処理）を実装。
  - Settings クラスを追加し、J-Quants / kabuステーション / Slack / DB パス 等の環境変数をプロパティで取得。値検証（KABUSYS_ENV, LOG_LEVEL）を実施。
- J-Quants API クライアント（kabusys.data.jquants_client）
  - ベース機能: ID トークン取得（リフレッシュトークン経由）、ページネーション対応のデータ取得関数を実装。
  - 取得対象: 株価日足（OHLCV）、財務データ（四半期 BS/PL）、JPX マーケットカレンダー。
  - レート制御: 固定間隔スロットリングで 120 req/min を遵守する RateLimiter を実装。
  - 再試行 (retry) ロジック: 指数バックオフ、最大 3 回、408/429/5xx に対するリトライ、およびネットワークエラー再試行。
  - 401 受信時の自動トークンリフレッシュ（1回のみ）とキャッシュ機構（モジュールレベル）を追加。
  - DuckDB への保存関数（save_daily_quotes, save_financial_statements, save_market_calendar）を実装。ON CONFLICT DO UPDATE による冪等保存を保証。
  - データ正規化ユーティリティ（_to_float, _to_int）を追加（不正値や小数切捨てを考慮）。
- ニュース収集モジュール（kabusys.data.news_collector）
  - RSS フィード収集器を実装（デフォルトで Yahoo Finance のビジネスRSSを登録）。
  - セキュリティ/堅牢性設計:
    - defusedxml を用いた XML パース、XML Bomb 等への対策。
    - SSRF 対策: URL スキーム検証（http/https のみ）、リダイレクト検査用ハンドラ(_SSRFBlockRedirectHandler)、プライベートアドレス判定（DNS 解決と直接IP判定）。
    - レスポンスサイズ上限（MAX_RESPONSE_BYTES = 10 MB）と gzip の解凍後チェック（Gzip bomb 対策）。
    - 許可しないスキームや大きなコンテンツはログとともにスキップ。
  - URL 正規化（トラッキングパラメータ除去、クエリソート、フラグメント除去）、ID 生成（正規化 URL の SHA-256 の先頭32文字）を実装して冪等性を確保。
  - テキスト前処理（URL除去・空白正規化）と記事構造の整形。
  - DuckDB への保存:
    - save_raw_news: INSERT ... ON CONFLICT DO NOTHING + RETURNING id を用い、実際に挿入された記事IDを返す。チャンク処理とトランザクションで安全に挿入。
    - save_news_symbols / _save_news_symbols_bulk: 記事と銘柄コードの紐付けを一括挿入（ON CONFLICT で重複を除外）し、挿入件数を正確に返す。
  - 銘柄コード抽出関数（extract_stock_codes）を実装（4桁数字パターン + known_codes フィルタ）。
  - run_news_collection: 複数RSSソースを巡回し、個別にエラーハンドリングして収集・保存・銘柄紐付けを行う。
- データベーススキーマ（kabusys.data.schema）
  - DuckDB 用のスキーマ定義を追加（Raw / Processed / Feature / Execution の4層構造）。
  - 主要テーブル群を定義（raw_prices, raw_financials, raw_news, raw_executions, prices_daily, market_calendar, fundamentals, news_articles, news_symbols, features, ai_scores, signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance 等）。
  - 各テーブルに適切な制約（PRIMARY KEY, CHECK, FOREIGN KEY）を付与。
  - パフォーマンスを考慮したインデックス群を定義（例: idx_prices_daily_code_date, idx_signal_queue_status 等）。
  - init_schema(db_path) を提供し、必要に応じて親ディレクトリを作成して全DDL/インデックスを冪等実行。get_connection で既存DBへの接続を取得。
- ETL パイプライン基盤（kabusys.data.pipeline）
  - ETLResult データクラスを実装して ETL 実行結果／品質問題／エラー一覧を構造化。
  - 差分取得のためのユーティリティ（テーブル存在チェック、テーブルの最終日取得、営業日調整）を実装。
  - run_prices_etl（株価差分ETL）の実装（差分ロジック、バックフィル設定、fetch→save の流れ）。
  - 設計における方針をコードコメントで明確化（差分更新、backfill、品質チェックの扱い、テスト容易性のための id_token 注入等）。
- その他
  - 型注釈・ログ出力・詳細なdocstringを多用し可読性と運用時のトレース性を向上。

### Changed
- （初期リリースのため該当なし。将来のリリースで API の安定化や名前変更が発生する可能性あり）

### Fixed
- （初期リリースのため該当なし）

### Security
- ニュース収集周りでSSRF・XML攻撃・DoS対策を実装:
  - defusedxml を使用（XML攻撃防止）。
  - リダイレクト先のスキーム・ホスト検証、プライベートIP拒否。
  - レスポンスサイズと gzip 解凍後サイズの上限チェック。
- .env 読み込みで OS 環境変数を保護する protected 機構を導入（.env.local での上書きを制御可能）。

### Notes / Limitations
- ETL パイプラインは基礎的な差分取得・保存ロジックを提供しますが、品質チェックモジュール（kabusys.data.quality）は外部モジュールとして参照される設計です。実際の品質ルールの実装・設定は別途必要です。
- 実装では urllib.request を用いた同期HTTPを行っており、高並列での取得が必要な場合は将来の拡張（非同期化、コネクションプール等）を検討してください。
- 現在の J-Quants クライアントは最大再試行回数やレート制限の定数がハードコードされているため、運用状況に応じた調整や設定化が今後の改善点です。
- run_prices_etl 等の関数は引数で id_token を注入できるためテストはしやすい設計ですが、実運用時のスケジューリングや監視（監査ログ、Slack 通知など）は別途導入が必要です。

---

（注）この CHANGELOG は提供されたソースコード内容から推測して作成したものであり、実際のリリースノートと差異がある場合があります。必要に応じて補足情報（マイグレーション手順、互換性ポリシー、既知の不具合など）を追記してください。