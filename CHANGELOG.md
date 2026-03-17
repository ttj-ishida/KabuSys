# Changelog

すべての重要な変更は本ファイルに記録します。
このファイルは Keep a Changelog の慣習に準拠しています。  
日付はリリース日です。

## [Unreleased]


## [0.1.0] - 2026-03-17

初期リリース。日本株自動売買システム「KabuSys」のコア基盤を実装しました。
主にデータ取得/保存・ETL・設定管理・RSSニュース収集・DBスキーマ定義を含みます。

### Added
- パッケージ基礎
  - パッケージ名 kabusys を追加。バージョンは 0.1.0。
  - __all__ に data, strategy, execution, monitoring を公開（strategy と execution は初期プレースホルダ）。

- 環境変数 / 設定管理（kabusys.config）
  - .env ファイルまたは環境変数から設定を読み込む Settings クラスを実装。
  - プロジェクトルート自動検出（.git または pyproject.toml）に基づく .env 自動ロード機能。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。
  - 自動読み込みを無効化する KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート（テスト用）。
  - .env パーサを実装（export プレフィックス、シングル/ダブルクォート、インラインコメント、エスケープを考慮）。
  - 必須設定取得用の _require()、env/log_level のバリデーション、フラグ系ユーティリティ（is_live 等）。
  - デフォルトの DB パス設定（DUCKDB_PATH, SQLITE_PATH）を提供。

- J-Quants API クライアント（kabusys.data.jquants_client）
  - J-Quants のエンドポイント（株価日足、財務データ、マーケットカレンダー）を取得する fetch_* 関数を実装。
  - レート制限（120 req/min）を守る固定間隔スロットリング RateLimiter を実装。
  - 冪等性を考慮した DuckDB 保存ヘルパ（save_daily_quotes, save_financial_statements, save_market_calendar）を実装。INSERT ... ON CONFLICT DO UPDATE を利用。
  - HTTP リクエストに対するリトライロジック（指数バックオフ、最大3回、408/429/5xx をリトライ対象）。
  - 401 受信時はリフレッシュトークンから id_token を自動更新して1回だけ再試行する仕組みを実装。
  - ページネーション対応（pagination_key を用いたループ取得）。
  - データ取得時に fetched_at を UTC で記録し、Look-ahead バイアスの追跡を可能に。
  - 型変換ユーティリティ（_to_float, _to_int）を実装し不正値を安全に処理。

- RSS ニュース収集（kabusys.data.news_collector）
  - RSS フィード取得・前処理・DB 保存のワークフローを実装（fetch_rss, save_raw_news, save_news_symbols, run_news_collection）。
  - defusedxml を利用した XML パースで XML-Bomb 等を軽減。
  - SSRF 対策:
    - リダイレクト時にスキーム／ホスト検証を行うカスタムリダイレクトハンドラを実装。
    - ホストのプライベート/ループバック/リンクローカル判定を行い内部アドレスへのアクセスを拒否。
    - URL スキーム検証（http/https のみ許可）。
  - レスポンスサイズ上限（MAX_RESPONSE_BYTES = 10MB）を設け、Content-Length の事前チェックと読み込み上限でメモリ DoS を抑制。
  - gzip 圧縮レスポンスの解凍と解凍後サイズチェック（Gzip-bomb 対策）。
  - 記事IDは URL 正規化（トラッキングパラメータ削除、ソート、フラグメント除去）後の SHA-256 の先頭32文字で生成し冪等性を確保。
  - トラッキングパラメータ削除（utm_*, fbclid, gclid 等）と URL 正規化処理。
  - raw_news への挿入はチャンク分割と INSERT ... ON CONFLICT DO NOTHING RETURNING で新規挿入IDを正確に取得し、1トランザクションで実行。
  - 銘柄抽出（extract_stock_codes）を実装し、既知の銘柄コードセットとのマッチングで news_symbols テーブルへ紐付け。

- DuckDB スキーマ定義・初期化（kabusys.data.schema）
  - Raw / Processed / Feature / Execution 層を想定したテーブル群を定義（raw_prices, raw_financials, raw_news, raw_executions, prices_daily, market_calendar, fundamentals, news_articles, news_symbols, features, ai_scores, signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance）。
  - 適切な型・チェック制約・主キー・外部キーを設定。
  - 頻出クエリに備えた複数のインデックス定義を追加。
  - init_schema(db_path) でディレクトリ作成・DDL 実行・インデックス作成を行う初期化関数を提供。get_connection() で既存 DB へ接続。

- ETL パイプライン（kabusys.data.pipeline）
  - 差分更新（差分取得・バックフィル）を念頭に置いた ETL パイプライン基盤を実装。
  - ETLResult dataclass を定義し、取得数/保存数/品質チェック結果/エラーを集約。
  - 市場カレンダーの先読みや backfill_days による再取得ロジック、品質チェックのためのフック（quality モジュールとの連携を想定）。
  - raw_prices/raw_financials/market_calendar の最終取得日取得関数（get_last_price_date 等）を実装。
  - run_prices_etl を実装（差分計算→fetch_daily_quotes→save_daily_quotes の流れ、バックフィル対応）。

### Security
- 外部入力（RSS/XML/HTTP）に対して複数の防御策を実装:
  - defusedxml による XML パース。
  - SSRF 防止（スキーム検査、プライベートアドレス判定、リダイレクト検査）。
  - レスポンスサイズチェック・gzip 解凍後のサイズ検証でメモリ攻撃を軽減。
  - .env ファイル読み込みで OS 環境変数の保護（protected set）を導入。

### Performance / Reliability
- API クライアントで固定間隔のレート制限実装によりレート超過を予防。
- リトライ（指数バックオフ）と 429 の Retry-After ヘッダ尊重で堅牢性を向上。
- DuckDB へのバルク挿入をチャンク化しトランザクションでまとめて処理、INSERT RETURNING により正確な新規件数を取得。

### Internal / Developer Experience
- テスト容易性を考慮し、id_token の注入や _urlopen の差し替え（モック可能）を設計。
- .env 自動ロードは環境変数で無効化可能（KABUSYS_DISABLE_AUTO_ENV_LOAD）。
- 明確なログ出力（logger を多用）で運用時のトラブルシュートを支援。

### Known issues / Notes
- strategy および execution パッケージは初期プレースホルダとして存在するが具体的な戦略ロジック・発注実装は未実装（今後の開発対象）。
- monitoring は __all__ に含まれるが、このリリースのコードベースにはモジュール実装が見当たらない（将来追加予定）。
- ETL パイプラインや quality モジュールの連携は設計済みだが、品質チェックの具体的なルール実装は別途実装が必要。

---

参考: ソースコードに記載された設計方針・コメントを基に要約しています。今後のリリースでは strategy 実装、execution（kabuAPI 連携）、監視/アラート機能、品質チェックルールの充実化を予定しています。