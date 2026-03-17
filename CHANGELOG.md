# Changelog

すべての注目すべき変更点を記録します。  
このファイルは Keep a Changelog の形式に準拠しています。

全般:
- ルール: https://keepachangelog.com/ja/1.0.0/ に準拠
- バージョン番号はパッケージの __version__ (src/kabusys/__init__.py) に合わせています。

## [0.1.0] - 2026-03-17

### Added
- 基本パッケージ構成を追加
  - モジュール: kabusys (パッケージルート)、subpackages: data, strategy, execution, monitoring（各サブモジュールは初期実装またはプレースホルダ）。
  - バージョン情報: __version__ = "0.1.0"

- 環境設定管理 (kabusys.config)
  - .env/.env.local の自動読み込み（プロジェクトルートを .git または pyproject.toml から検出）。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロード無効化可能（テスト向け）。
  - .env パース機能:
    - export KEY=val 形式対応、クォートのエスケープ対応、インラインコメント処理。
    - 保護された OS 環境変数を上書きから保護する仕組み（override/protected）。
  - Settings クラスによる環境変数アクセス（必須キーは _require による検査）
    - J-Quants、kabuステーション、Slack、DBパス等のアクセサを提供。
    - KABUSYS_ENV / LOG_LEVEL の値検証（有効値チェック）。
    - Path 型でのデフォルト DB パス取得 (duckdb/sqlite)。

- J-Quants API クライアント (kabusys.data.jquants_client)
  - API 呼び出しユーティリティ _request を実装。
    - レート制限: 固定間隔スロットリングで 120 req/min を遵守（_RateLimiter）。
    - リトライ: 指数バックオフ（最大 3 回）、対象ステータス (408, 429, 5xx)。
    - 401 受信時は自動でリフレッシュして 1 回再試行（無限再帰防止フラグあり）。
    - JSON デコードエラーハンドリング。
    - ページネーション対応（pagination_key の検出・追跡）。
  - get_id_token(): リフレッシュトークンから id_token を取得（POST）。
  - データ取得関数:
    - fetch_daily_quotes: 株価日足（OHLCV）のページネーション取得。
    - fetch_financial_statements: 財務データ（四半期 BS/PL）のページネーション取得。
    - fetch_market_calendar: JPX マーケットカレンダー取得。
    - 取得ログ（件数）を出力し、取得日時のトレースを想定。
  - DuckDB への保存関数（冪等）
    - save_daily_quotes, save_financial_statements, save_market_calendar:
      - fetched_at を UTC で記録（ISO8601 Z 形式）。
      - ON CONFLICT ... DO UPDATE により冪等性を確保。
      - PK 欠損レコードのスキップと警告ログ。
  - 型変換ユーティリティ _to_float / _to_int（安全な変換、空値は None）。

- ニュース収集モジュール (kabusys.data.news_collector)
  - RSS フィードからの記事収集・整形・DB保存を実装。
  - 安全設計:
    - defusedxml を利用した XML パース（XML Bomb を含む攻撃緩和）。
    - SSRF 対策: 
      - リダイレクト時にスキームとホストを検証する _SSRFBlockRedirectHandler。
      - 初回 URL および最終 URL に対するプライベートアドレス検査（_is_private_host）。
      - スキームは http/https のみ許可。
    - レスポンスサイズ制限（MAX_RESPONSE_BYTES = 10MB）と Gzip 解凍後のサイズ検証（Gzip bomb 対策）。
    - 許可されない URL スキームや大きすぎるレスポンスはログ出力のうえスキップ。
  - 正規化・ID 生成:
    - _normalize_url: トラッキングパラメータ（utm_* 等）除去、クエリキーソート、フラグメント削除。
    - _make_article_id: 正規化 URL の SHA-256 先頭32文字を記事IDに採用（冪等性）。
  - テキスト前処理: URL 除去、空白正規化（preprocess_text）。
  - RSS パース: content:encoded 優先、pubDate を UTC naive datetime に正規化。
  - DB 保存:
    - save_raw_news: チャンク分割の INSERT ... ON CONFLICT DO NOTHING RETURNING id を使用し、実際に挿入された記事IDを返す。トランザクションでまとめる。
    - save_news_symbols / _save_news_symbols_bulk: news_symbols に対する一括保存（重複削除、チャンク、RETURNING で正確な挿入数を取得）。
  - 銘柄抽出:
    - extract_stock_codes: 正規表現で 4 桁数字を抽出し、known_codes に基づきフィルタ。重複除去。

- DuckDB スキーマ定義・初期化 (kabusys.data.schema)
  - Raw / Processed / Feature / Execution の各レイヤーのテーブル定義を追加。
    - 例: raw_prices, raw_financials, raw_news, market_calendar, prices_daily, features, ai_scores, signal_queue, orders, trades, positions 等。
  - 制約: PRIMARY KEY, CHECK 制約（値範囲/型チェック）を多用。
  - インデックス定義（頻出クエリに最適化）。
  - init_schema(db_path) によりディレクトリ作成、全DDL実行、インデックス作成を行い接続を返す（冪等）。
  - get_connection(db_path) を提供（スキーマ初期化は行わない）。

- ETL パイプライン (kabusys.data.pipeline)
  - 差分更新・バックフィルの考慮をした ETL 用ユーティリティを追加。
    - 最終取得日の取得: get_last_price_date, get_last_financial_date, get_last_calendar_date。
    - 市場カレンダーへの調整: _adjust_to_trading_day（非営業日の補正）。
    - run_prices_etl の骨組み（差分算出・J-Quants からの取得・保存・ログ記録）。
  - ETL 実行結果を表す ETLResult dataclass（品質問題、エラー一覧、各取得/保存数を保持）。
  - テスト容易化のため、id_token 注入や内部挙動の分離を考慮。

### Security
- 外部データ取得に対する複数の防御策を実装
  - defusedxml による XML パース
  - SSRF 防止（スキーム検査、プライベートアドレス検査、リダイレクト検査）
  - レスポンスサイズ上限、Gzip 解凍後の上限チェック
  - .env の保護された読み込み（OS 環境変数の誤上書きを防止）

### Performance / Reliability
- API レート制御（固定スロットリング）と指数バックオフ付きリトライにより外部 API 呼び出しの安定化を図る。
- DuckDB 側はチャンク INSERT とトランザクションを利用してオーバーヘッドを削減。
- ページネーション対応で大量データの取得に対応。

### Changed
- 初期リリースのため該当なし（新規実装中心）。

### Fixed
- 初期リリースのため該当なし。

### Notes / Requirements
- 必須環境変数（settings で _require しているもの）:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
  - テストやローカル実行では KABUSYS_DISABLE_AUTO_ENV_LOAD を利用可能
- 依存ライブラリ: duckdb, defusedxml（その他標準ライブラリを利用）

### Known issues / TODO
- run_prices_etl の最終行が不完全（return 文が途中で終わっているように見える）ため、実行時に例外や不正な戻り値になる可能性があります。実運用前に return の整合性を確認してください。
- strategy / execution / monitoring サブパッケージは初期プレースホルダまたは未実装の部分があるため、発注ロジックやモニタリング周りの実装は今後追加が必要です。
- schema による FOREIGN KEY 制約は定義されているが、運用時の参照整合性チェックとマイグレーション戦略（スキーマ変更手順）は今後の整備が必要です。

---

（注）本 CHANGELOG は提示されたソースコードからの推測に基づくまとめです。実際のリポジトリ履歴やコミットメッセージが存在する場合はそれらに合わせて更新してください。