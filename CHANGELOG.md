# Changelog

すべての注目すべき変更点を記録します。フォーマットは「Keep a Changelog」に準拠しています。

## [0.1.0] - 2026-03-18
初回リリース

### Added
- パッケージ基盤
  - kabusys パッケージを追加。公開モジュール: data, strategy, execution, monitoring（src/kabusys/__init__.py）。
  - バージョン情報を __version__ = "0.1.0" に設定。

- 環境変数 / 設定管理（src/kabusys/config.py）
  - .env ファイルまたは環境変数から設定を自動読み込みする仕組みを実装（プロジェクトルートを .git / pyproject.toml から検出）。
  - 読み込み順序: OS 環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応。
  - .env パーサは export 形式、クォート、インラインコメント等に堅牢に対応。
  - Settings クラスを提供し、J-Quants トークン、kabu API パスワード、Slack トークン/チャンネル、DB パス、環境（development/paper_trading/live）やログレベル検証などのプロパティを追加。
  - 必須環境変数未設定時は _require() が ValueError を送出。

- J-Quants クライアント（src/kabusys/data/jquants_client.py）
  - J-Quants API 用クライアントを実装。
  - 機能:
    - 株価日足（fetch_daily_quotes）
    - 財務データ（fetch_financial_statements）
    - マーケットカレンダー（fetch_market_calendar）
    - リフレッシュトークンからの id_token 取得（get_id_token）
  - 設計上の特徴:
    - 固定間隔のレートリミッタ（120 req/min）を実装。
    - 再試行ロジック（指数バックオフ、最大 3 回、408/429/5xx を対象）。
    - 401 受信時は自動で id_token をリフレッシュして 1 回リトライ（無限再帰を防止）。
    - ページネーション対応（pagination_key）とモジュールレベルの id_token キャッシュ。
    - DuckDB への保存関数（save_daily_quotes / save_financial_statements / save_market_calendar）は冪等性を保つ（ON CONFLICT DO UPDATE）。
    - fetched_at を UTC で記録し、取得時刻をトレース可能に。

- ニュース収集モジュール（src/kabusys/data/news_collector.py）
  - RSS フィードから記事を収集して raw_news に保存する機能を実装。
  - 機能:
    - RSS 取得（fetch_rss）、テキスト前処理（preprocess_text）
    - URL 正規化（_normalize_url）とトラッキングパラメータ除去（utm_* 等）
    - 記事ID を正規化 URL の SHA-256（先頭32文字）で生成（_make_article_id）して冪等性を保証
    - XML 解析は defusedxml を利用（XML Bomb 等の防御）
    - レスポンスサイズ上限（MAX_RESPONSE_BYTES = 10MB）でメモリDoSを防止
    - SSRF 対策: スキーム検証、プライベートアドレス判定、リダイレクト検査（_SSRFBlockRedirectHandler / _is_private_host）
    - gzip 解凍対応と解凍後サイズチェック
    - DB 保存: save_raw_news はチャンク化（_INSERT_CHUNK_SIZE）し、INSERT ... RETURNING で実際に挿入された ID を返す。トランザクションで安全に実行。
    - 銘柄紐付け: extract_stock_codes で本文から 4 桁銘柄コード抽出、有効コードのみ紐付け、_save_news_symbols_bulk で一括挿入。

- DuckDB スキーマ定義と初期化（src/kabusys/data/schema.py）
  - DataSchema.md に基づくテーブル群を定義（Raw / Processed / Feature / Execution 層）。
  - 主要テーブル（例: raw_prices, raw_financials, raw_news, market_calendar, prices_daily, features, ai_scores, signals, signal_queue, orders, trades, positions, portfolio_performance 等）を作成する DDL を実装。
  - インデックス定義（頻出クエリ向け）を追加。
  - init_schema(db_path) でディレクトリ自動作成後に全テーブル・インデックスを作成（冪等）。get_connection は既存 DB への接続を返す。

- ETL パイプライン（src/kabusys/data/pipeline.py）
  - 差分更新ベースの ETL ロジックを実装。
  - 機能・設計:
    - 最終取得日を元に差分（date_from）を自動算出。デフォルトのバックフィル日数は 3 日（backfill_days）。
    - 市場カレンダーの先読み（デフォルトで将来 90 日までを取得する設計パラメータあり）。
    - 品質チェック（quality モジュール）と連携するためのインターフェース（ETLResult に品質問題を格納）。
    - ETLResult データクラスを導入し、実行結果・品質問題・エラーを集約。to_dict による辞書化対応。
    - run_prices_etl（差分取得→保存）の雛形を実装（fetch + save の呼び出し、ログ出力、日付調整ヘルパー等）。

### Security
- RSS ニュース収集におけるセキュリティ対策を実装
  - defusedxml を使用した XML パースにより XML ベース攻撃（例: XML Bomb）を緩和。
  - URL スキーム検証（http/https のみ許可）とリダイレクト先のスキーム検証により SSRF を低減。
  - ホスト名／IP のプライベートアドレス判定（_is_private_host）で内部アドレスへのアクセスを拒否。
  - レスポンスの最大読み取りバイト数を設定（10 MB）してメモリ DoS を防止。
  - URL 正規化でトラッキングパラメータを削除し、記事 ID の一貫性とプライバシー配慮を強化。

### Internal / Quality of life
- 各所でログ出力を充実（info/warning/exception）し、運用時のトラブルシュートを補助。
- 各種ユーティリティ関数（_to_float / _to_int / preprocess_text / _parse_rss_datetime / _normalize_url / extract_stock_codes など）を整備。
- DB 操作はトランザクションでラップ（begin/commit/rollback）し、安全に例外処理。

### Fixed
- （初回リリースのため該当なし）

### Changed
- （初回リリースのため該当なし）

### Removed
- （初回リリースのため該当なし）

### Notes / Migration
- 初期リリース。今後のリリースで API の追加・仕様変更、品質チェックモジュール（quality）や execution/strategy/monitoring 実装の拡充が予定されています。
- DuckDB スキーマは init_schema() 実行により作成されます。既存データとの互換性を保つため、スキーマ変更時はマイグレーションを検討してください。

(この CHANGELOG はコード内容から推測して作成しています。実際の変更履歴やリリース日などはプロジェクトの運用に合わせて調整してください。)