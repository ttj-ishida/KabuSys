# CHANGELOG

全ての重要な変更点を記録します。  
このファイルは Keep a Changelog の形式に準拠しています。  

※リリース日付はコードベースから推測して記載しています。

## [Unreleased]
- 次期リリースに向けた未確定の変更点を記載します。

---

## [0.1.0] - 2026-03-17
初回公開リリース。以下の主要機能・設計を実装しています。

### Added
- パッケージ基盤
  - パッケージエントリポイントを定義（kabusys.__init__）。
  - モジュール分割: data, strategy, execution, monitoring のパッケージ構成を用意（将来の拡張用の空 __init__ を含む）。

- 設定管理（kabusys.config）
  - .env ファイルと環境変数から設定を読み込む自動ローダを実装。
  - プロジェクトルート検出ロジック（.git / pyproject.toml を基準）により CWD に依存しない自動読み込み。
  - .env/.env.local の優先度処理（OS 環境変数保護、override 制御）。
  - .env 行パーサー（export プレフィックス、クォート・エスケープ、行内コメント処理に対応）。
  - Settings クラスを公開し、J-Quants トークン、kabu API パスワード、Slack 設定、DBパス等をプロパティ経由で取得可能。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化をサポート。
  - KABUSYS_ENV / LOG_LEVEL の値検証（許容値チェック）。

- J-Quants クライアント（kabusys.data.jquants_client）
  - API クライアントを実装（株価日足、財務データ、マーケットカレンダーの取得に対応）。
  - レート制御（120 req/min）を固定間隔スロットリングで実装（内部 RateLimiter）。
  - 再試行ロジック（指数バックオフ、最大 3 回）と 408/429/5xx への対応。
  - 401 発生時の自動トークンリフレッシュ（1 回のみリトライ）を実装。モジュールレベルで ID トークンをキャッシュしてページネーション間で共有。
  - ページネーション対応（pagination_key を用いた取得の継続）。
  - DuckDB への冪等保存関数（save_daily_quotes / save_financial_statements / save_market_calendar）を実装。ON CONFLICT DO UPDATE による上書き。
  - レスポンス JSON デコードエラーや HTTP エラーの詳細ハンドリングを実装。
  - 値変換ユーティリティ（_to_float / _to_int）で不正値を安全に None に変換。

- ニュース収集（kabusys.data.news_collector）
  - RSS フィード取得と raw_news テーブルへの保存を実装。
  - 記事IDは正規化した URL の SHA-256 ハッシュ先頭32文字で生成し冪等性を担保。
  - URL 正規化: スキーム/ホスト小文字化、トラッキングパラメータ除去（utm_* 等）、フラグメント除去、クエリソート。
  - セキュリティ対策:
    - defusedxml による XML パース（XML Bomb 等対策）。
    - SSRF 対策: リダイレクト時のスキーム検証、プライベート IP/ホストの検出と拒否、最終 URL 再検証。
    - 受信サイズ上限（MAX_RESPONSE_BYTES = 10MB）および gzip 解凍後のサイズチェック（Gzip bomb 対策）。
    - HTTP スキームの検証（http/https のみ受け入れ）。
  - 内容前処理（URL 除去、空白正規化）と pubDate のパース（RFC 2822 対応、失敗時は現在時刻で代替）。
  - DuckDB へチャンク化して一括 INSERT（INSERT ... RETURNING を活用）し、挿入された ID を返す save_raw_news を実装。
  - 記事と銘柄の紐付け機能（extract_stock_codes / save_news_symbols / _save_news_symbols_bulk）。既知の4桁銘柄コード抽出と一括保存に対応。
  - デフォルト RSS ソースとして Yahoo Finance を用意（設定可能）。

- DuckDB スキーマ（kabusys.data.schema）
  - Raw / Processed / Feature / Execution の 3 層（＋Execution）に基づくテーブル定義を実装。
  - raw_prices, raw_financials, raw_news, raw_executions を含む Raw レイヤ。
  - prices_daily, market_calendar, fundamentals, news_articles, news_symbols を含む Processed レイヤ。
  - features, ai_scores を含む Feature レイヤ。
  - signals, signal_queue, orders, trades, positions, portfolio_performance 等の Execution レイヤ。
  - インデックス定義とテーブル作成順序の管理。
  - init_schema(db_path) によりディレクトリ自動作成・テーブル作成を実行、get_connection() を提供。

- ETL パイプライン（kabusys.data.pipeline）
  - 差分更新方式の ETL 設計・ヘルパーを実装（最終取得日の検出・バックフィル考慮）。
  - run_prices_etl をはじめとした差分取得ロジック（date_from 自動算出、backfill_days による後出し修正吸収）。
  - ETLResult dataclass により実行結果/品質問題/エラーを集約して返却可能。
  - 市場カレンダー先読み（_CALENDAR_LOOKAHEAD_DAYS）や最小データ開始日（_MIN_DATA_DATE）などの定数定義。
  - DB 存在チェック・最大日付取得ユーティリティを提供。

- パフォーマンス・運用配慮
  - NewsCollector のバルク挿入チャンクサイズ（_INSERT_CHUNK_SIZE）で SQL 長やパラメータ数を制御。
  - save_raw_news / _save_news_symbols_bulk は1トランザクションで複数チャンクをコミットしてオーバーヘッドを削減。
  - jquants_client のレートリミッタと retry/backoff により API レート制限・過負荷回避を実装。

### Changed
- 初回リリースにつき該当なし。

### Fixed
- 初回リリースにつき該当なし。

### Security
- ニュース収集で以下の対策を実施:
  - defusedxml を利用した安全な XML パース。
  - リダイレクト検査とプライベートアドレス判定で SSRF を防止。
  - レスポンスサイズ制限（読み込み上限・解凍後上限）でメモリ DoS/Gzip bomb を防止。
  - URL スキーマ検証（http/https のみ）で file:, data:, javascript: 等を拒否。
- .env 自動読み込み時に OS 環境変数を protected として上書きを防止するロジックを実装。

### Known issues / Notes
- quality モジュールは pipeline で参照している（品質チェック用の型や定数を使用）が、本リリースのコードベースに quality の全文は含まれていない場合は別モジュールとして提供される想定です。実行環境では quality 実装の有無に注意してください。
- strategy / execution / monitoring パッケージは最小の初期構成（将来の実装領域）としてディレクトリを準備しています。
- Python バージョン: 型ヒント（| を使ったユニオン等）から Python 3.10+ を想定しています。
- デフォルトの DB パスは data/kabusys.duckdb（DuckDB）および data/monitoring.db（sqlite）となっています。運用時は環境変数で上書きしてください。
- jquants_client の BASE URL は https://api.jquants.com/v1 を使用。テスト環境向けに settings 経由でカスタマイズ可能（KABU_API_BASE_URL 等）。
- run_prices_etl の実装はファイル末尾で途中になっている可能性がある（切り出し範囲による）。必要に応じて呼び出しロジックの完成を確認してください。

---

（今後のリリース案）
- strategy と execution の実装（シグナル生成、注文管理、kabu API 連携）
- 品質チェック（quality モジュール）の完全実装と ETL への統合強化
- 監視・通知（Slack 統合）の実装（settings に Slack 設定あり）

---