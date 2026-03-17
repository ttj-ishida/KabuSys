# Changelog

すべての注目すべき変更をこのファイルに記録します。  
このプロジェクトは Keep a Changelog の慣習に従います。  

※日付はリリース日を表します。

## [0.1.0] - 2026-03-17

初回リリース — 日本株自動売買基盤のコア機能を実装。

### 追加 (Added)
- パッケージ基盤
  - kabusys パッケージの初期公開（バージョン 0.1.0）。
  - サブパッケージプレースホルダ: data, strategy, execution, monitoring。

- 設定・環境読み込み（kabusys.config）
  - .env ファイルまたは環境変数から設定を自動読み込みする仕組みを実装。
    - 読み込み優先順位: OS環境変数 > .env.local > .env。
    - プロジェクトルートは __file__ を基準に .git または pyproject.toml から探索。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
    - OS環境変数を保護するために上書き禁止キーセット（protected）をサポート。
  - .env のパーサ実装:
    - export プレフィックス、クォート付き値のエスケープ処理、行内コメント処理などを考慮。
  - Settings クラスでアプリ設定をプロパティとして公開:
    - J-Quants / kabuAPI / Slack / DB パス（DuckDB/SQLite）などの設定を取得。
    - KABUSYS_ENV（development/paper_trading/live）や LOG_LEVEL のバリデーション。
    - is_live / is_paper / is_dev のヘルパー。

- J-Quants クライアント（kabusys.data.jquants_client）
  - J-Quants API から株価日足・四半期財務・マーケットカレンダーを取得する API クライアントを実装。
  - レート制限 (120 req/min) を守る固定間隔スロットリング (RateLimiter) を実装。
  - 再試行ロジック（最大 3 回、指数バックオフ、対象ステータス: 408/429/5xx）。
  - 401 受信時は自動でリフレッシュトークンを使って id_token を更新して1回リトライ。
  - ページネーション対応の fetch_* 関数（fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar）。
  - DuckDB への冪等保存関数（save_daily_quotes, save_financial_statements, save_market_calendar）を実装。
    - INSERT ... ON CONFLICT DO UPDATE を使って重複を排除／更新。
    - fetched_at を UTC タイムスタンプで記録し、取得時刻をトレース可能に。
  - HTTP レスポンスの JSON デコードエラーハンドリングや詳細ログ出力。
  - 値変換ユーティリティ (_to_float, _to_int) を実装（安全な数値変換ロジック）。

- ニュース収集（kabusys.data.news_collector）
  - RSS フィードからニュース記事を収集し raw_news / news_symbols に保存する機能を実装。
  - 設計上の特徴:
    - 記事ID は正規化された URL の SHA-256（先頭32文字）で生成して冪等性を担保。
    - URL 正規化でトラッキングパラメータ（utm_* 等）を除去、クエリソート、フラグメント除去。
    - defusedxml を使った安全な XML パース（XML Bomb 等への対策）。
    - SSRF 対策:
      - URL スキーム検証（http/https のみ許可）。
      - リダイレクト時のスキーム・ホスト検証（_SSRFBlockRedirectHandler）。
      - ホストがプライベート/ループバック/リンクローカル/マルチキャストであれば拒否。
    - レスポンスサイズ制限（MAX_RESPONSE_BYTES = 10 MB）と gzip 解凍後のサイズチェック（Gzip bomb 対策）。
    - 不正なレスポンスやパース失敗はログ出力して安全にスキップ。
  - DB 保存:
    - save_raw_news はチャンク (最大 _INSERT_CHUNK_SIZE) ごとに INSERT ... ON CONFLICT DO NOTHING RETURNING id を実行し、実際に挿入された ID を返す。
    - save_news_symbols / _save_news_symbols_bulk: 記事と銘柄コードの紐付けをトランザクションで一括保存（ON CONFLICT で重複除去）し、実際に挿入された件数を返す。
  - テキスト前処理（URL 除去・空白正規化）と RSS pubDate の安全なパース（_parse_rss_datetime）。
  - 銘柄コード抽出: テキストから 4 桁の候補を抽出し、known_codes に含まれるもののみ返す extract_stock_codes。
  - run_news_collection: 複数フィードの収集を統合し、個別ソースは独立してエラー処理（1 ソース失敗で他に影響しない）。

- DuckDB スキーマ管理（kabusys.data.schema）
  - DataSchema.md に基づいた多層データモデルを実装。
    - Raw / Processed / Feature / Execution レイヤー向けのテーブル定義を提供。
    - 主要テーブル: raw_prices, raw_financials, raw_news, raw_executions, prices_daily, market_calendar, fundamentals, news_articles, news_symbols, features, ai_scores, signals, signal_queue, orders, trades, positions, portfolio_performance, 等。
  - チェック制約や主キー・外部キーを定義してデータ整合性を強化。
  - 頻出クエリ向けインデックスを作成（例: idx_prices_daily_code_date 等）。
  - init_schema(db_path) で DB ファイルの親ディレクトリ自動作成 → 全テーブル・インデックスを作成（冪等）。
  - get_connection(db_path) で既存 DB への接続を返す（初回は init_schema を推奨）。

- ETL パイプライン（kabusys.data.pipeline）
  - ETL の基本的な流れを実装:
    - 差分更新のための最終取得日取得ヘルパ（get_last_price_date, get_last_financial_date, get_last_calendar_date）。
    - 非営業日調整ヘルパ（_adjust_to_trading_day）。
    - ETLResult dataclass を提供して ETL の実行結果、品質問題、エラーを集約。
    - run_prices_etl 実装（差分取得ロジック、backfill_days による再取得、fetch + save の呼び出し）。
  - データ品質チェックを行う品質モジュール（quality）との連携設計（重大度管理など）。

### セキュリティ (Security)
- ニュース収集での安全対策:
  - defusedxml による XML パースで XML 攻撃を軽減。
  - SSRF 対策: スキーム検証、リダイレクト先検査、プライベートIPチェック。
  - レスポンスサイズ制限と gzip 解凍後のサイズチェックにより DoS/Gzip-bomb を軽減。
  - URL のトラッキングパラメータ除去により同一記事の重複挿入を抑制。
- 環境変数読み込み:
  - OS 環境変数を保護するために .env 上書きを制御する protected セットを採用。

### 依存関係（注意）
- 実行には少なくとも以下のライブラリが必要:
  - duckdb
  - defusedxml
  - 標準ライブラリの urllib, json, datetime 等

### 既知の制限 / 今後の改善候補
- pipeline.run_prices_etl の外側ジョブ（スケジューリング・監視・Slack 通知等）は未実装（Settings に Slack 設定はあるが通知機能の実装は今後）。
- strategy / execution / monitoring の具象実装はまだなく、インターフェースやワークフロー統合は今後の実装予定。
- 単体テストや統合テスト用のモック/テストヘルパは一部で設計に配慮（例: _urlopen の差し替え可能性）しているが、テストスイートは追加予定。

### 破壊的変更 (Breaking Changes)
- 初回リリースのため無し。

---

参考: パッケージバージョンは src/kabusys/__init__.py の __version__ = "0.1.0" に合わせています。