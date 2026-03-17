# CHANGELOG

すべての重要な変更はこのファイルに記載します。  
このプロジェクトは Keep a Changelog の慣例に従います。  

## [Unreleased]
(なし)

## [0.1.0] - 2026-03-17
初回リリース。日本株自動売買プラットフォームの基盤となるモジュール群を追加しました。主な機能は以下のとおりです。

### Added
- パッケージ基盤
  - kabusys パッケージを追加。公開APIとして data, strategy, execution, monitoring をエクスポート。
  - バージョン情報: `__version__ = "0.1.0"` を設定。

- 環境設定 / 設定管理（kabusys.config）
  - .env ファイルおよび環境変数から設定を自動読み込みする仕組みを実装。
  - プロジェクトルート探索は `__file__` を起点に `.git` または `pyproject.toml` を探すため、CWD に依存しない動作。
  - `.env` のパース機能を実装（コメント・export プレフィックス・クォート/エスケープ対応）。
  - 自動ロードは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能（テスト用途）。
  - `Settings` クラスを提供：
    - J-Quants / kabuステーション / Slack / DB パス等の必須/任意設定プロパティを提供（必須未設定時は ValueError を送出）。
    - `KABUSYS_ENV` の値検証（development/paper_trading/live）。
    - `LOG_LEVEL` の値検証。
    - `is_live` / `is_paper` / `is_dev` 等のユーティリティプロパティ。

- J-Quants API クライアント（kabusys.data.jquants_client）
  - J-Quants API から株価日足・財務データ・マーケットカレンダーを取得する関数を実装：
    - fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar（ページネーション対応）。
  - 認証トークン取得：get_id_token（リフレッシュトークンから ID トークンを取得）。
  - HTTP レイヤにおける堅牢性：
    - API レート制限（120 req/min）を守る固定間隔スロットリング（_RateLimiter）。
    - リトライ戦略（指数バックオフ、最大 3 回）。対象ステータスや Retry-After ヘッダへの配慮。
    - 401 受信時はトークンを自動リフレッシュして1回リトライ（無限再帰対策あり）。
  - DuckDB への保存関数（冪等）を提供：
    - save_daily_quotes, save_financial_statements, save_market_calendar：ON CONFLICT DO UPDATE により重複を排除して更新。
    - データ型変換ユーティリティ `_to_float` / `_to_int` を実装。
  - 取得時刻（fetched_at）を UTC で記録し、Look-ahead Bias を抑止。

- ニュース収集モジュール（kabusys.data.news_collector）
  - RSS フィードから記事を収集し raw_news / news_symbols へ格納する機能を実装。
  - セキュリティ・堅牢性対策：
    - defusedxml を利用した安全な XML パース（XML bomb 対策）。
    - SSRF 対策：URL スキーム検証（http/https のみ許可）、プライベートIP/ループバック/リンクローカル検出、リダイレクト時も検査する専用ハンドラ `_SSRFBlockRedirectHandler`。
    - レスポンスサイズ上限（MAX_RESPONSE_BYTES = 10MB）を厳格にチェック（Content-Length と実際の読み込み両方を検査）。gzip 解凍後のサイズ検査も実装。
  - URL 正規化（トラッキングパラメータ削除、クエリソート、フラグメント削除）と記事ID生成（正規化 URL の SHA-256 の先頭32文字）により冪等性を確保。
  - テキスト前処理（URL 除去、空白正規化）。
  - DB への保存はトランザクションでまとめて実行し、INSERT ... RETURNING を使って実際に新規挿入された件数/IDを正確に取得：
    - save_raw_news（チャンク挿入、ON CONFLICT DO NOTHING、挿入IDリストを返す）
    - save_news_symbols / _save_news_symbols_bulk（銘柄紐付けの一括保存）
  - 銘柄コード抽出ユーティリティ extract_stock_codes（4桁数字、known_codes フィルタ、重複除去）。
  - 全体ジョブ run_news_collection を提供（各ソース独立でエラーハンドリング、known_codes による銘柄紐付け）。

- DuckDB スキーマ定義 / 初期化（kabusys.data.schema）
  - DataSchema.md に基づく多層スキーマ（Raw / Processed / Feature / Execution）を定義。
  - raw_prices, raw_financials, raw_news, raw_executions を含む Raw 層。
  - prices_daily, market_calendar, fundamentals, news_articles, news_symbols などの Processed 層。
  - features, ai_scores の Feature 層。
  - signals, signal_queue, orders, trades, positions, portfolio_performance 等の Execution 層。
  - 頻出クエリ向けのインデックス定義を追加。
  - init_schema(db_path) でディレクトリ作成→テーブル/インデックス作成（冪等）、get_connection() を提供。

- ETL パイプライン（kabusys.data.pipeline）
  - 差分更新を行う ETL パイプラインの基盤を実装：
    - ETLResult dataclass（実行結果・品質問題・エラーの集約）。
    - テーブル最終取得日取得ユーティリティ（get_last_price_date, get_last_financial_date, get_last_calendar_date）。
    - 市場カレンダーの営業日調整ヘルパー（_adjust_to_trading_day）。
    - run_prices_etl の骨組み（差分取得、backfill の考慮、fetch -> save の流れ）を実装（差分ロジック、最小データ日付の扱い）。
  - 設計方針として「差分更新」「backfill による後出し修正吸収」「品質チェックは収集を続行して呼び出し元で対処」等を反映。

### Security
- RSS 取得周りでの SSRF 防止施策を導入（スキーム検証、プライベートアドレス判定、リダイレクト検査）。
- XML パースに defusedxml を利用し、XML Bomb 等の攻撃に対処。
- HTTP レスポンスの最大受信サイズ制限を導入し、メモリ DoS を軽減。

### Other
- ロギングを各主要処理に追加（情報・警告・例外出力を適切に出力）。
- テストしやすさを考慮し、ネットワーク呼び出し（_urlopen 等）やトークンの注入ポイントを設けている。

---

既知の不完全点・注意事項
- pipeline.run_prices_etl 等、ETLパイプラインの一部は骨組みが中心で、上流の品質チェックモジュール（kabusys.data.quality）など外部モジュールとの結合が前提です。実運用前に品質チェックやスケジュール実行ロジックの統合が必要です。
- 0.1.0 は初期機能セットです。運用で得られたフィードバックに基づきエラーハンドリングや性能改善、追加機能（戦略モジュール、実取引連携等）を計画しています。

---
記載方針: リリースには各コミットの詳細ログを添付することを推奨します。