# Changelog

すべての変更は Keep a Changelog の形式に準拠しています。  
初版リリース (0.1.0) の内容はコードベースから推測して記載しています。

最新: Unreleased

## [Unreleased]

- （現在の開発中の変更はここに記載してください）

---

## [0.1.0] - 2026-03-18

Added
- 初期リリース: KabuSys 日本株自動売買システムのコアモジュール群を追加。
  - パッケージ初期化情報
    - src/kabusys/__init__.py
      - パッケージ version を "0.1.0" として定義。
      - __all__ に data, strategy, execution, monitoring を設定。
  - 環境・設定管理
    - src/kabusys/config.py
      - .env ファイルおよび環境変数の自動読み込み機能を実装（読み込み順: OS 環境 > .env.local > .env）。
      - プロジェクトルート検出（.git または pyproject.toml を基準）により CWD 非依存で自動ロード。
      - .env パーサ実装（export プレフィックス、クォート、インラインコメント対応）。
      - 自動ロードを無効化する KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
      - 必須環境変数取得ヘルパー _require と Settings クラスを提供。
      - 主要設定:
        - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID を必須として参照。
        - KABUSYS_ENV（development/paper_trading/live）のバリデーション。
        - LOG_LEVEL のバリデーション（DEBUG/INFO/WARNING/ERROR/CRITICAL）。
        - デフォルトの DB パス: DUCKDB_PATH="data/kabusys.duckdb", SQLITE_PATH="data/monitoring.db"。
  - J-Quants クライアント（データ取得・保存）
    - src/kabusys/data/jquants_client.py
      - API レート制限（120 req/min）を守る固定間隔レートリミッタを実装。
      - HTTP リクエスト処理にリトライ（指数バックオフ、最大 3 回）を実装。対象コードに 408/429/5xx を含む。
      - 401 受信時は ID トークンを自動リフレッシュして 1 回だけリトライ（キャッシュ付き）。
      - ページネーション対応の取得関数を実装:
        - fetch_daily_quotes (OHLCV)
        - fetch_financial_statements (四半期財務)
        - fetch_market_calendar (JPX カレンダー)
      - DuckDB へ冪等に保存する save_* 関数を実装（ON CONFLICT DO UPDATE による重複排除）:
        - save_daily_quotes, save_financial_statements, save_market_calendar
      - 取得時刻（fetched_at）を UTC で記録して Look-ahead Bias のトレースを支援。
      - 型変換ユーティリティ (_to_float, _to_int) を実装（不正値を None にする堅牢化）。
  - ニュース収集モジュール
    - src/kabusys/data/news_collector.py
      - RSS フィードからの記事取得と前処理、DuckDB への保存パイプラインを実装。
      - セキュリティ対策:
        - defusedxml を利用して XML Bomb 等に対応。
        - SSRF 対策: リダイレクト時にスキーム検査とプライベートアドレス判定を行うカスタムリダイレクトハンドラを導入。
        - URL スキームは http/https のみ許可。
        - 受信サイズ上限 (MAX_RESPONSE_BYTES = 10MB) を導入しメモリ DoS を防止。gzip 解凍後もサイズ確認。
      - URL 正規化とトラッキングパラメータ除去（_normalize_url）、SHA-256（先頭32文字）で記事 ID を生成（冪等性）。
      - テキスト前処理 (preprocess_text): URL 除去・空白正規化。
      - DuckDB 保存:
        - save_raw_news: チャンク分割 + トランザクション + INSERT ... RETURNING id（ON CONFLICT DO NOTHING）。新規挿入 ID を返却。
        - save_news_symbols/_save_news_symbols_bulk: 記事と銘柄の紐付けを一括挿入（RETURNING で挿入数を正確に取得）。
      - 銘柄コード抽出 util: extract_stock_codes（4桁数字、known_codes に基づくフィルタ、重複除去）。
      - 統合ジョブ run_news_collection を提供。既知銘柄セットが与えられた場合は新規記事の銘柄紐付けまで行う。ソース単位で隔離されたエラーハンドリング。
      - デフォルト RSS ソース: Yahoo Finance のビジネスカテゴリを指定。
  - DuckDB スキーマ管理
    - src/kabusys/data/schema.py
      - Raw / Processed / Feature / Execution 層にまたがるテーブル定義を追加。
      - 主なテーブル（抜粋）:
        - raw_prices, raw_financials, raw_news, raw_executions
        - prices_daily, market_calendar, fundamentals, news_articles, news_symbols
        - features, ai_scores
        - signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
      - 各種制約（PRIMARY KEY, CHECK, FOREIGN KEY）やインデックスを定義。
      - init_schema(db_path) : ディレクトリ自動作成 + 全 DDL 実行（冪等）。
      - get_connection(db_path) : 既存 DB への接続（初期化は行わない）。
  - ETL パイプライン基盤
    - src/kabusys/data/pipeline.py
      - ETLResult dataclass により ETL 実行結果（取得数、保存数、品質問題、エラー）を構造化。
      - DB 存在チェックや最大日付取得のユーティリティ (_table_exists, _get_max_date) を提供。
      - 市場カレンダーの営業日調整ヘルパー (_adjust_to_trading_day) を実装。
      - 差分更新のヘルパー関数:
        - get_last_price_date, get_last_financial_date, get_last_calendar_date
      - run_prices_etl の実装（差分更新、backfill_days デフォルト 3、最小データ日付 2017-01-01）。
      - 設計方針・ドキュメントコメントにより品質チェックモジュール（quality）との連携を想定。
  - パッケージモジュール空ファイルを追加（strategy, execution, data パッケージ初期化）

Security
- ニュース収集周りで複数のセキュリティ対策を導入:
  - defusedxml による XML パースの安全化。
  - SSRF 防止: リダイレクト先のスキーム/ホスト検証、ホストのプライベートアドレス検出。
  - レスポンスサイズ上限および gzip 解凍後のサイズチェック（Gzip Bomb 対策）。
- API クライアントで認証トークンを安全に扱うためのキャッシュと自動リフレッシュを実装。

Notes
- 環境変数の主な必須キー:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
- デフォルトの DuckDB ファイル: data/kabusys.duckdb（必要に応じて DUCKDB_PATH 環境変数で上書き）。
- J-Quants API のレート制限（120 req/min）に合わせた実装のため、大量リクエスト時は待機が発生します。
- save_raw_news / news_symbols は INSERT ... RETURNING を利用するため、DuckDB バージョンや接続方法によっては挙動の差異に注意してください。
- schema.init_schema はファイルシステム上のディレクトリを自動作成します。":memory:" を指定するとインメモリ DB を使用します。

Deprecated
- なし

Removed
- なし

Fixed
- 初期リリースにつき該当なし（ベース機能の実装が中心）

Breaking Changes
- なし（初期リリース）

--- 

注: 本 CHANGELOG は与えられたコードから推測して作成しています。実際のリポジトリのコミット履歴や設計ドキュメントと差異がある可能性があります。必要であれば、各項目をコミット単位で分割した詳細な履歴（機能追加日・コミットID・著者など）に展開します。