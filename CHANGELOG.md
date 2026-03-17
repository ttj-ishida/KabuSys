CHANGELOG
=========
すべての注目すべき変更はこのファイルに記録します。
このプロジェクトは Keep a Changelog の形式に従います。
配布済みの変更のみをこのファイルに記載します。

フォーマット: https://keepachangelog.com/ja/1.0.0/

Unreleased
----------
（なし）

[0.1.0] - 2026-03-17
--------------------
初回リリース。日本株自動売買システム "KabuSys" の基本機能を提供します。

Added
- パッケージのエントリポイントを追加
  - src/kabusys/__init__.py に __version__ = "0.1.0" と __all__ を定義。
- 環境・設定管理モジュールを追加（kabusys.config）
  - .env / .env.local の自動読み込み機能（プロジェクトルート検出: .git または pyproject.toml）。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。
  - 自動ロードの無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - .env パース機能（export プレフィックス、クォート、コメント処理をサポート）。
  - 必須設定取得ヘルパー (_require) と Settings クラスを公開。
  - 必須環境変数（例）: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID。
  - デフォルト値: KABU_API_BASE_URL, DUCKDB_PATH, SQLITE_PATH。環境（KABUSYS_ENV）とログレベル検証。

- J-Quants API クライアントを追加（kabusys.data.jquants_client）
  - 株価日足（OHLCV）、四半期財務データ、JPX マーケットカレンダー取得 API を実装。
  - 設計上の特徴:
    - API レート制限遵守のための固定間隔スロットリング（RateLimiter、120 req/min）。
    - リトライロジック（指数バックオフ、最大 3 回。対象: 408/429/5xx。429 に対して Retry-After を優先）。
    - 401 受信時にリフレッシュトークンで自動的に id_token を更新して 1 回だけ再試行。
    - トークンのモジュールレベルキャッシュ（ページネーション処理で共有）。
    - ページネーション対応（pagination_key によるループ取得）。
    - 取得時刻（fetched_at）を UTC で記録し、look-ahead bias のトレースを可能に。
  - DuckDB への冪等保存関数を実装（ON CONFLICT DO UPDATE）:
    - save_daily_quotes, save_financial_statements, save_market_calendar。
  - 型変換ユーティリティ: _to_float, _to_int（安全な変換・不正値は None）。

- ニュース収集モジュールを追加（kabusys.data.news_collector）
  - RSS フィードから記事を取得し raw_news テーブルへ保存するフローを実装。
  - 設計上の特徴（セキュリティ・堅牢性重視）:
    - URL 正規化とトラッキングパラメータ削除（utm_* 等）。
    - 記事 ID を正規化 URL の SHA-256（先頭32文字）で生成し冪等性を保証。
    - defusedxml を用いた XML パース（XML Bomb 等対策）。
    - SSRF 対策:
      - URL スキーム検証（http/https のみ許可）。
      - ホストがプライベート/ループバック/リンクローカル/マルチキャストであれば拒否（DNS 解決して A/AAAA をチェック）。
      - リダイレクト時にもスキームとホスト検証を実施するカスタムハンドラ（_SSRFBlockRedirectHandler）。
    - レスポンスサイズ制限（MAX_RESPONSE_BYTES = 10 MiB）と gzip 解凍後の再チェック（Gzip bomb 対策）。
    - RSS の pubDate を安全にパースして UTC に正規化（_parse_rss_datetime）。
    - テキスト前処理（URL 除去、空白正規化）。
    - DB へのバルク保存はトランザクションとチャンク挿入（INSERT ... RETURNING）で実装：
      - save_raw_news: 新規挿入された記事 ID のリストを返す。
      - save_news_symbols / _save_news_symbols_bulk: 記事と銘柄コードの紐付けを冪等に保存。
    - 銘柄コード抽出ユーティリティ extract_stock_codes（4桁数字、known_codes によるフィルタリング）。

- DuckDB スキーマ定義と初期化を追加（kabusys.data.schema）
  - DataSchema.md に基づく 3 層構造（Raw / Processed / Feature）と Execution 層のテーブル DDL を実装。
  - raw_prices, raw_financials, raw_news, raw_executions 等の Raw 層。
  - prices_daily, market_calendar, fundamentals, news_articles, news_symbols 等の Processed 層。
  - features, ai_scores 等の Feature 層。
  - signals, signal_queue, orders, trades, positions, portfolio_performance 等の Execution 層。
  - 代表的な制約（PRIMARY KEY, CHECK, FOREIGN KEY）やインデックス (idx_* ) を定義。
  - init_schema(db_path) によりディレクトリ自動作成・テーブル作成を行い、接続を返す。
  - get_connection(db_path) で既存 DB に接続。

- ETL パイプラインの基礎を追加（kabusys.data.pipeline）
  - 差分更新・バックフィルの方針を含む ETL の設計。
  - ETLResult データクラス（品質問題・エラーの集約、to_dict サポート）。
  - DB の最終取得日取得ヘルパー（get_last_price_date, get_last_financial_date, get_last_calendar_date）。
  - 市場カレンダーに基づく営業日調整ヘルパー (_adjust_to_trading_day)。
  - run_prices_etl の差分ロジック（date_from 自動算出、backfill_days の扱い）を実装（J-Quants から取得して保存までの流れ）。
  - 品質チェック（quality モジュール）連携のための準備が含まれる。

Changed
- （初版のため該当なし）

Fixed
- （初版のため該当なし）

Security
- RSS/XML 処理に defusedxml を採用して XML 攻撃対策を実施。
- ニュース収集での SSRF 対策（スキーム検証、プライベートホスト拒否、リダイレクト検査）。
- HTTP レスポンスサイズ制限と gzip 解凍後の検査によりメモリ DoS / 圧縮爆弾に対処。
- DB 操作はトランザクションで保護し、失敗時にロールバック。

Notes / Migration
- 初回リリース。既存データベースがない場合は init_schema() を呼び出してから ETL を実行してください。
- 環境変数が多数必須です。開発前に .env を準備することを推奨します（.env.example を参照）。
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定するとテスト等で自動 .env ロードを抑制できます。

Acknowledgements / Known limitations
- quality モジュールの具体的な品質チェック実装（欠損・スパイク検出など）は外部モジュールとして想定されており、pipeline は検出結果を集約するインターフェースを提供します。
- run_prices_etl 実装は差分の算出・取得・保存を行いますが、（このリリース時点で）完全なジョブスケジューリング・監視機能は別モジュール（monitoring / execution 等）に依存します。
- news_collector の URL 正規化・コード抽出は既知のトラッキングパラメータや 4 桁銘柄コードに依存しており、将来的な拡張（追加ソース・自然言語処理によるタグ付け等）を想定。

今後の予定
- execution（発注ロジック）、monitoring（ジョブ監視・Slack 通知）モジュールの実装拡張。
- quality モジュールの詳細実装および ETL の自動スケジューリング機能。
- テストカバレッジ拡充（ネットワーク周りの模擬、DuckDB の統合テストなど）。

--- End of CHANGELOG ---