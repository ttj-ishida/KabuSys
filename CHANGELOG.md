KEEP A CHANGELOG
すべての変更は https://keepachangelog.com/ja/ のガイドラインに従って記載しています。

全般注意
- 本CHANGELOGはコードベースから推測して作成したもので、実際のコミット履歴ではありません。
- 環境や外部依存（J-Quants API / RSS ソース / DuckDB 等）により挙動が変わる可能性があります。

Unreleased
- なし

[0.1.0] - 2026-03-17
初回公開リリース — 日本株自動売買システムの基礎モジュール群を追加。

Added
- パッケージ初期化
  - kabusys パッケージを導入。バージョン __version__ = "0.1.0"、公開サブパッケージ: data, strategy, execution, monitoring を定義。

- 設定管理 (kabusys.config)
  - .env ファイルおよび環境変数から設定を読み込む自動ローダーを実装。
    - 自動ロードの優先順位: OS環境変数 > .env.local > .env
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 による自動ロード無効化に対応（テスト用途）。
    - プロジェクトルートの検出は __file__ を起点に .git または pyproject.toml を探索。
  - .env パーサーを実装:
    - コメント行・空行スキップ、export KEY=val 形式対応。
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理、インラインコメントの扱い、非クォート時の # コメント処理などに対応。
  - Settings クラスを提供:
    - 必須環境変数チェック（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID）。
    - DBパスの既定値（DUCKDB_PATH="data/kabusys.duckdb", SQLITE_PATH="data/monitoring.db"）と Path 展開。
    - 環境（KABUSYS_ENV）の検証（development/paper_trading/live）とログレベル検証。
    - is_live/is_paper/is_dev のブールプロパティ。

- J-Quants API クライアント (kabusys.data.jquants_client)
  - /token/auth_refresh を使った ID トークン取得機能 (get_id_token) を実装。
  - rate limiter（120 req/min 固定間隔スロットリング）を実装し API 呼び出し間隔を管理。
  - 汎用 HTTP リクエストラッパー (_request) を実装:
    - JSON デコード失敗検知、指数バックオフリトライ（最大3回）、408/429/5xx に対する再試行。
    - 401 受信時はトークンを自動リフレッシュして 1 回リトライ（無限再帰防止フラグあり）。
    - ページネーション対応。ページネーションキーの重複検出でループ終了。
    - モジュールレベルで ID トークンをキャッシュしてページネーション間で使い回し。
  - データ取得関数を実装:
    - fetch_daily_quotes（株価日足: OHLCV）
    - fetch_financial_statements（四半期財務データ）
    - fetch_market_calendar（JPX マーケットカレンダー）
  - DuckDB への保存関数を実装（冪等性を考慮）:
    - save_daily_quotes / save_financial_statements / save_market_calendar
    - INSERT ... ON CONFLICT DO UPDATE を用いて重複を排除・更新。
    - fetched_at を UTC ISO 形式で記録し、いつデータを取得したかを追跡可能に。
  - データ変換ユーティリティ:
    - _to_float / _to_int（安全な型変換、空値や不正値を None にするロジック。float 文字列からの int 変換時は小数部検査を行う）。

- ニュース収集モジュール (kabusys.data.news_collector)
  - RSS フィードから記事を収集して raw_news / news_symbols に格納するワークフローを実装。
  - 安全性・堅牢性設計:
    - defusedxml を用いた XML パース（XML Bomb 等に対策）。
    - SSRF 対策: リダイレクトハンドラでスキーム/ホスト検査、初期ホスト検査、プライベート/ループバック/リンクローカルの検出。
    - URL スキームは http/https のみ許可。非許可スキームは拒否。
    - レスポンス受信サイズ上限を導入（MAX_RESPONSE_BYTES=10MB）し、超過はスキップ（gzip 解凍後もチェック）。
    - User-Agent と Accept-Encoding（gzip）を設定。
  - URL 正規化と記事 ID 生成:
    - トラッキングパラメータ（utm_*, fbclid 等）を除去してクエリをソート、フラグメント削除後に SHA-256 の先頭32文字で id を生成。
  - テキスト前処理（URL 除去、空白正規化）関数を実装。
  - pubDate のパース（RFC2822）を行い UTC で正規化。パース失敗時は警告ログを出し現在時刻で代替。
  - DB 保存:
    - save_raw_news はチャンク分割・トランザクションで INSERT ... ON CONFLICT DO NOTHING RETURNING id を使用し、実際に挿入された記事 ID を返却。
    - save_news_symbols / _save_news_symbols_bulk により記事と銘柄コードの紐付けをチャンク化して一括保存。ON CONFLICT で重複をスキップし、INSERT RETURNING で挿入数を正確に取得。
  - 銘柄コード抽出:
    - 4桁数字パターンを抽出し、known_codes セットでフィルタリングして重複を排除して返す。
  - run_news_collection 関数:
    - 複数ソースを独立して処理し、各ソースの新規挿入数を辞書で返却。既知銘柄コードが与えられた場合は新規記事に対して銘柄紐付けを行う。

- DuckDB スキーマ (kabusys.data.schema)
  - Raw / Processed / Feature / Execution 層のテーブル DDL を定義。
    - raw_prices, raw_financials, raw_news, raw_executions
    - prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - features, ai_scores
    - signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 適切な制約（PRIMARY KEY / CHECK / FOREIGN KEY）と型を設定し、データ整合性を想定。
  - 頻出クエリ向けのインデックスを作成するDDLを定義。
  - init_schema(db_path) により DB ファイルの親ディレクトリ自動作成と DDL 実行でスキーマ初期化（冪等）。
  - get_connection(db_path) により既存 DB への接続を返却（スキーマは初期化しない）。

- ETL パイプライン (kabusys.data.pipeline)
  - ETLResult dataclass により ETL 実行結果と品質・エラー情報を構造化（to_dict メソッド付き）。
  - 差分更新サポート:
    - raw_prices/raw_financials/market_calendar の最終日取得ヘルパー (get_last_price_date / get_last_financial_date / get_last_calendar_date) を実装。
    - 市場カレンダーを用いた営業日調整関数 _adjust_to_trading_day を実装（最大 30 日遡るフォールバック）。
  - run_prices_etl を実装（差分更新ロジック、バックフィル日数設定、J-Quants からの取得 → save までのワークフロー）。
  - 設計上の方針を明記（差分更新、backfill による後出し修正吸収、品質チェックは Fail-Fast しない等）。

Changed
- 初回リリースにつき過去との変更はなし。

Fixed
- 初回リリースにつき修正はなし。

Security
- RSS 処理で defusedxml を採用、SSRF 防止（リダイレクト時の検査、ホストのプライベートIP検査）や受信サイズ上限を設定。
- .env 読み込み時のファイルアクセス失敗は警告により安全に扱う。

Notes / Known limitations
- ETL パイプラインや一部の処理（例: run_prices_etl の戻り値や pipeline の追加ジョブ）は今後の拡張が想定される（現状でも基本的な差分取得/保存は実装済み）。
- news_collector の既定 RSS ソースは Yahoo Finance のビジネスカテゴリのフィードのみを設定（DEFAULT_RSS_SOURCES）。追加のソースは run_news_collection の引数で指定可能。
- J-Quants API 利用時はレート制限とリトライ設定に従うが、実運用ではさらに詳細なスロットリングやモニタリングが必要になる場合がある。
- DuckDB の SQL 実行で使用している生の文字列結合部分（特に大量プレースホルダ生成）は安全性・パフォーマンス観点で注意が必要（現状はパラメータ化を行っているが、チャンクサイズや SQL 長に注意）。

開発者向けヒント
- テスト容易性のため、news_collector._urlopen や jquants_client の id_token 注入ポイントが用意されており、外部依存の差し替え（モック化）が可能。
- 環境変数を自動ロードさせたくないテスト場面では KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。

— End of CHANGELOG —