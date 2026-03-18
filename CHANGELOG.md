CHANGELOG
=========

すべての変更は Keep a Changelog の形式に準拠して記載しています。  
このファイルは日本語での説明を目的としています。

フォーマット:
- Added: 新機能
- Changed: 変更点（後方互換性が維持される変更）
- Fixed: バグ修正
- Removed: 削除
- Security: セキュリティ関連の注意

[Unreleased]
-------------

（現時点のリリース履歴は下記参照）

[0.1.0] - 2026-03-18
-------------------

Added
- パッケージ初期リリース (kabusys v0.1.0)
  - パッケージメタデータ:
    - src/kabusys/__init__.py にて __version__="0.1.0" を設定。
  - 環境・設定管理:
    - src/kabusys/config.py
      - .env/.env.local をプロジェクトルート（.git または pyproject.toml を基準）から自動読み込みする仕組みを追加（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
      - .env 行解析の詳細処理を実装（export 形式対応、クォートやインラインコメントの扱い、エスケープ処理など）。
      - 環境変数取得のヘルパー _require() と Settings クラスを導入。J-Quants / kabu API / Slack / DB パス 等の設定プロパティを提供。
      - KABUSYS_ENV（development/paper_trading/live）と LOG_LEVEL（DEBUG/INFO/...）の検証を追加。
      - デフォルト DB パス: DUCKDB_PATH=data/kabusys.duckdb、SQLITE_PATH=data/monitoring.db。
  - J-Quants API クライアント:
    - src/kabusys/data/jquants_client.py
      - API 呼び出しの共通処理を実装（_request）。
      - レート制御（120 req/min 固定間隔スロットリング）を実装する RateLimiter を導入。
      - 再試行（最大3回、指数バックオフ）と HTTP ステータスごとのハンドリング（408/429/5xx のリトライ、429 の Retry-After 利用）を実装。
      - 401 受信時にリフレッシュトークンから id_token を自動更新して 1 回だけリトライするロジックを導入（無限再帰防止）。
      - ページネーション対応のデータ取得関数を追加: fetch_daily_quotes、fetch_financial_statements、fetch_market_calendar。
      - DuckDB への冪等保存関数を追加: save_daily_quotes、save_financial_statements、save_market_calendar（ON CONFLICT DO UPDATE を使用）。
      - 取得時刻（fetched_at）を UTC ISO フォーマットで記録して Look-ahead Bias のトレース性を確保。
      - 値変換ユーティリティ _to_float / _to_int を提供（安全な型変換と不正値の扱い）。
  - ニュース収集モジュール:
    - src/kabusys/data/news_collector.py
      - RSS フィード取得と前処理の実装（fetch_rss）。
      - セキュリティ対策: defusedxml による XML パース、防御的リダイレクトハンドラ（SSRF 対策）、ホストがプライベート/ループバックでないことの検査、HTTP スキーム検証（http/https のみ）。
      - レスポンスサイズ制限（MAX_RESPONSE_BYTES = 10MB）と gzip 解凍後サイズ検査（Gzip bomb 対策）。
      - URL 正規化（トラッキングパラメータ除去、クエリソート、フラグメント除去）と記事ID生成（正規化 URL の SHA-256 の先頭32文字）を実装し、冪等性を確保。
      - テキスト前処理（URL除去・空白正規化）と記事構造化（NewsArticle 型）を実装。
      - DuckDB への保存: save_raw_news（チャンク挿入、トランザクション管理、INSERT ... RETURNING による実際に挿入された ID の取得）、save_news_symbols、内部バルク保存 _save_news_symbols_bulk を実装。
      - 銘柄コード抽出関数 extract_stock_codes（4桁数字パターンと known_codes フィルタ）を提供。
      - run_news_collection による統合収集ジョブを実装（ソース単位でのエラーハンドリング、銘柄紐付けの一括登録）。
      - デフォルト RSS ソースとして Yahoo Finance のカテゴリフィードを指定。
  - DuckDB スキーマ定義:
    - src/kabusys/data/schema.py
      - Raw / Processed / Feature / Execution の多層スキーマを定義する DDL を追加。
      - raw_prices, raw_financials, raw_news, raw_executions, prices_daily, market_calendar, fundamentals, news_articles, news_symbols, features, ai_scores, signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance などを定義。
      - 制約（PRIMARY KEY、CHECK 等）や頻出クエリに対するインデックスを設定。
      - init_schema(db_path) による初期化関数と get_connection を公開。親ディレクトリ自動作成、:memory: 対応。
  - ETL パイプライン:
    - src/kabusys/data/pipeline.py
      - ETLResult dataclass による実行結果表現（品質チェック結果・エラー収集）。
      - 差分更新ロジック（DB の最終取得日から backfill_days を考慮して再取得）を実装。
      - 市場カレンダー先読み、最小データ日付の扱いなどの定数を導入。
      - テーブル存在確認・最大日付取得ユーティリティ、非営業日の調整ロジックを実装。
      - run_prices_etl（株価 ETL の差分実行）を実装（fetch と save の呼び出し、保存件数の返却）。
  - パッケージ構成:
    - src/kabusys/data, src/kabusys/strategy, src/kabusys/execution, src/kabusys/monitoring 等のモジュール用のパッケージ化（__init__.py）を追加（空ファイル/プレースホルダを含む）。

Changed
- （初回リリースにつき該当なし）

Fixed
- （初回リリースにつき該当なし）

Removed
- （初回リリースにつき該当なし）

Security
- ニュース収集での複数のセキュリティ対策を導入:
  - defusedxml を用いて XML 関連攻撃を防止。
  - リダイレクト時にスキームとホストの検査を行うハンドラを実装し SSRF を軽減。
  - ホストの DNS 解決結果や直接 IP を検査してプライベート/ループバック/リンクローカル/マルチキャストを拒否。
  - URL スキーム検証により file:, javascript:, mailto: 等を排除。
  - レスポンス長の上限（10MB）と gzip 解凍後のサイズチェック（Gzip bomb 対策）を実装。
- API クライアントでの認証トークン自動リフレッシュは allow_refresh フラグで制御し、無限再帰を防止。

Notes / Usage highlights
- 環境変数の必須キー:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID は Settings のプロパティ経由で必須チェックされる。
- デフォルト設定:
  - KABUSYS_ENV のデフォルトは "development"。有効値は {"development","paper_trading","live"}。
  - LOG_LEVEL のデフォルトは "INFO"。
  - J-Quants API レート制限は 120 req/min（最小間隔 0.5 秒）。
  - J-Quants リトライは最大 3 回、バックオフ係数は 2.0（指数バックオフ）。
  - RSS 最大受信サイズ 10MB、デフォルトソースは Yahoo Finance。
- DuckDB スキーマは冪等（IF NOT EXISTS）なので何度でも init_schema を呼べます。初回は init_schema()、以降は get_connection() を使用してください。

今後の予定（例）
- strategy / execution / monitoring の具体実装（現在はパッケージプレースホルダ）。
- 品質チェックモジュール (quality) の詳細チェックと pipeline との統合の強化。
- 単体テスト・統合テスト補完、CI ワークフロー追加。

---