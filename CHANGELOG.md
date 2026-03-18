# Changelog

すべての変更は Keep a Changelog の形式に従います。  
このプロジェクトではセマンティックバージョニングを使用します。

## [0.1.0] - 2026-03-18

### 追加
- 初回リリースを追加。パッケージ名: kabusys、バージョン 0.1.0。
- パッケージ公開インターフェースを定義（src/kabusys/__init__.py）。
  - __version__ = "0.1.0"
  - __all__ = ["data", "strategy", "execution", "monitoring"]

- 環境設定管理モジュールを追加（src/kabusys/config.py）。
  - .env ファイルおよび環境変数から設定を読み込む自動ロード機能（プロジェクトルート検出: .git または pyproject.toml）。
  - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - .env パーサーは export KEY=val 形式、シングル/ダブルクォート、インラインコメントの扱いをサポート。
  - 設定アクセス用 Settings クラスを提供（必須変数取得の _require）。
  - 主な設定プロパティ:
    - JQUANTS_REFRESH_TOKEN（必須）
    - KABU_API_PASSWORD（必須）
    - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
    - SLACK_BOT_TOKEN（必須）
    - SLACK_CHANNEL_ID（必須）
    - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
    - SQLITE_PATH（デフォルト: data/monitoring.db）
    - KABUSYS_ENV（development/paper_trading/live の検証）
    - LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL の検証）

- J-Quants API クライアントを追加（src/kabusys/data/jquants_client.py）。
  - 株価日足（OHLCV）、財務データ（四半期 BS/PL）、JPX マーケットカレンダーを取得する fetch_* 関数を実装。
  - レート制限: 固定間隔スロットリングで 120 req/min を遵守する RateLimiter 実装。
  - リトライロジック: 指数バックオフ（最大 3 回）、HTTP 408/429/5xx に対する再試行。
  - 401 Unauthorized を受けた場合は自動でトークンをリフレッシュして 1 回リトライ（再帰防止の allow_refresh フラグ）。
  - ページネーション対応（pagination_key の取り扱い）。
  - DuckDB への保存関数 save_daily_quotes / save_financial_statements / save_market_calendar を実装（冪等性: ON CONFLICT DO UPDATE）。
  - データ取得時の fetched_at は UTC ISO8601（Z 表記）で記録。
  - ユーティリティ関数: 型変換のための _to_float / _to_int（安全な変換と不正値の扱い）。

- ニュース収集モジュールを追加（src/kabusys/data/news_collector.py）。
  - RSS フィードから記事を収集し raw_news に保存するフローを実装。
  - セキュリティ対策:
    - defusedxml による XML パース（XML Bomb 等への防御）。
    - SSRF 対策: URL スキーム検証（http/https のみ）、ホストがプライベート/ループバック/リンクローカルかを判定し拒否、リダイレクト時にも検証。
    - 受信サイズ制限（MAX_RESPONSE_BYTES = 10 MB）および gzip 解凍後の再チェック（Gzip bomb 対策）。
    - 最終 URL の再検証。
  - 記事 ID は URL 正規化（トラッキングパラメータ除去・クエリソート等）後の SHA-256 ハッシュ先頭 32 文字で生成し冪等性を保証。
  - テキスト前処理（URL 除去、空白正規化）。
  - DB 保存:
    - save_raw_news: INSERT ... ON CONFLICT DO NOTHING をチャンク単位（デフォルト 1000）で行い、INSERT RETURNING により実際に挿入された記事 ID のリストを返す。トランザクション管理とロールバック処理あり。
    - save_news_symbols / _save_news_symbols_bulk: 記事と銘柄コードの紐付けを一括保存（ON CONFLICT DO NOTHING、INSERT RETURNING で挿入数を正確に取得）。重複除去とチャンク処理。
  - 銘柄抽出ロジック: 4桁数字パターンから known_codes に含まれるもののみを抽出する extract_stock_codes。
  - フェッチ用のカスタムオープナー関数 _urlopen を作成しテスト時にモック可能にしてある。

- DuckDB スキーマ定義・初期化モジュールを追加（src/kabusys/data/schema.py）。
  - Raw / Processed / Feature / Execution 層のテーブル DDL を定義。
  - 主要テーブル: raw_prices, raw_financials, raw_news, raw_executions, prices_daily, market_calendar, fundamentals, news_articles, news_symbols, features, ai_scores, signals, signal_queue, orders, trades, positions, portfolio_performance など。
  - インデックス定義（頻出クエリ向け）。
  - init_schema(db_path) でディレクトリ作成（必要時）→ テーブルとインデックスを作成して DuckDB 接続を返す（冪等）。
  - get_connection(db_path) による既存 DB への接続（初期化は行わない）。

- ETL パイプラインモジュールを追加（src/kabusys/data/pipeline.py）。
  - 差分更新ロジック（最終取得日からの差分算出、デフォルトバックフィル日数=3 日）。
  - 市場カレンダーの先読み（デフォルト lookahead 90 日）や初期ロード時の最小日付を定義。
  - ETLResult データクラスを実装し、品質問題（quality モジュールで検出される想定）の収集、エラー一覧保持、has_errors / has_quality_errors 等のプロパティを提供。
  - DB テーブル存在チェック・最大日付取得ユーティリティを実装。
  - run_prices_etl の骨組みを実装（差分判定、fetch→save の流れ）。（注: サンプルコード末尾で戻り値タプルの記述が途中で終わっている点は後述参照）

### 変更
- なし（初回リリース）。

### 修正
- なし（初回リリース）。

### セキュリティ
- RSS パーサーに defusedxml を使用して XML による攻撃を軽減。
- ニュース取得での SSRF 対策（スキーム検証、プライベート IP 検査、リダイレクト検査）。
- .env 読み込み時に OS 環境変数を保護する protected 機能を実装（.env.local の上書き制御等）。

### 注意事項 / 既知の問題
- settings.jquants_refresh_token / slack 等の必須環境変数が未設定の場合は ValueError を送出します。初回利用前に .env を作成するか環境変数を設定してください。
- jquants_client の _request は最大 3 回のリトライを行い、それでも失敗した場合は RuntimeError を投げます。
- news_collector.fetch_rss はネットワーク例外（urllib.error.URLError）を投げる可能性があります。run_news_collection では各ソースで例外を捕捉して処理を継続します。
- news_collector._urlopen はテスト時にモック可能にしてあります。外部への実接続を抑制したい場合は差し替えてください。
- pipeline.run_prices_etl のサンプルコード末尾で return タプルが途中で切れているように見える箇所があります（提供されたコードの抜粋のための可能性あり）。実運用前に最終戻り値の整合性を確認してください。

### マイグレーション / 初期設定ガイド
- DuckDB スキーマを初期化する:
  - from kabusys.data.schema import init_schema
  - conn = init_schema(settings.duckdb_path)  # settings は kabusys.config.settings
- 環境変数（例）:
  - JQUANTS_REFRESH_TOKEN（必須）
  - KABU_API_PASSWORD（必須）
  - SLACK_BOT_TOKEN（必須）
  - SLACK_CHANNEL_ID（必須）
  - KABUSYS_ENV（development/paper_trading/live）
  - LOG_LEVEL（DEBUG/INFO/…）
  - DUCKDB_PATH / SQLITE_PATH（任意、デフォルトを使用可）
- 自動 .env ロードを無効化する場合:
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト用途）。

---

今後のリリースでは次のような改善を予定しています（例）:
- pipeline の完全な ETL ジョブ（品質チェック quality モジュールとの統合、ログ・メトリクス出力）の完成。
- execution 層（kabu ステーションとの発注処理）の実装。
- strategy 層のサンプル戦略とモニタリング（Slack 通知等）の追加。
- 単体テストと CI 設定の整備。

もし CHANGELOG に追記して欲しい点（重要な設計決定や追加で強調したいセキュリティ事項等）があれば教えてください。