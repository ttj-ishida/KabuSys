Keep a Changelog形式で、このコードベースから推測される変更履歴（日本語）を作成しました。バージョンはパッケージ内の __version__（0.1.0）に合わせています。

CHANGELOG.md
=============

すべての注目すべき変更はこのファイルに記載します。  
形式は「Keep a Changelog」に準拠します。

Unreleased
----------

- （現在なし）

[0.1.0] - 2026-03-18
--------------------

Added
- 初期リリース: KabuSys 日本株自動売買システムのコアモジュールを追加。
- パッケージ構成:
  - kabusys (トップレベルパッケージ)
  - サブパッケージ: data, strategy, execution, monitoring（strategy, execution, monitoring は空の __init__ を用意）
- バージョン情報:
  - __version__ = "0.1.0"

- 環境設定管理 (kabusys.config):
  - .env/.env.local の自動読み込み（プロジェクトルート判定：.git または pyproject.toml を探索）
  - .env の高度なパース機能（export 形式、クォート内のバックスラッシュエスケープ、インラインコメント処理）
  - 読み込み優先順位: OS 環境 > .env.local > .env
  - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD
  - 環境変数アクセサ (Settings):
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID などの必須取得 (未設定時は ValueError)
    - KABUSYS_ENV（development/paper_trading/live）と LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL）の検証
    - データベースパス既定値（DUCKDB_PATH, SQLITE_PATH）と Path 型での取得ヘルパ

- J-Quants API クライアント (kabusys.data.jquants_client):
  - API 呼び出しユーティリティ（_request）:
    - レート制限（120 req/min）を固定間隔スロットリングで制御する RateLimiter 実装
    - 冪等な ID トークンキャッシュと自動リフレッシュ（401 で1回のみリフレッシュして再試行）
    - リトライロジック（最大 3 回、指数バックオフ、408/429/5xx を対象、429 の Retry-After 優先）
    - JSON デコードエラーの明示的扱い
  - 認証ユーティリティ:
    - get_id_token(refresh_token=None)（POST /token/auth_refresh）
  - データ取得関数（ページネーション対応）:
    - fetch_daily_quotes（株価日足）
    - fetch_financial_statements（四半期財務）
    - fetch_market_calendar（JPX カレンダー）
    - 各 API 呼び出しは pagination_key を追跡して全件取得
    - fetched_at の概念（Look-ahead bias 防止のため UTC で記録）
  - DuckDB への保存関数（冪等）:
    - save_daily_quotes: raw_prices テーブルへ ON CONFLICT DO UPDATE で保存
    - save_financial_statements: raw_financials テーブルへ ON CONFLICT DO UPDATE で保存
    - save_market_calendar: market_calendar テーブルへ ON CONFLICT DO UPDATE で保存
  - データ変換ユーティリティ:
    - _to_float / _to_int（空値や不正値を安全に扱う）

- ニュース収集モジュール (kabusys.data.news_collector):
  - RSS フィード取得とパース機能:
    - defusedxml を使った XML パース（XML Bomb 等に配慮）
    - gzip 圧縮対応と解凍後サイズチェック（Gzip bomb 対策）
    - Content-Length と読み込み上限（MAX_RESPONSE_BYTES = 10MB）によるメモリDoS対策
    - URL スキーム検証（http/https のみ許可）と SSRF 対策
    - リダイレクト時のスキーム / ホスト検証用ハンドラ (_SSRFBlockRedirectHandler)
    - ホストがプライベート/ループバック/リンクローカル/マルチキャストかを検査する _is_private_host（IP と DNS 解決を組合せ）
    - レスポンスサイズやパースエラーはログに警告を出して安全にスキップ
  - 記事整形・ID生成:
    - URL 正規化（トラッキングパラメータ除去、クエリソート、フラグメント除去）
    - 記事ID は正規化URL の SHA-256 の先頭32文字で生成（冪等性の担保）
    - テキスト前処理（URL 除去、空白正規化）
    - pubDate の堅牢な解析と UTC 変換（失敗時は現在時刻で代替）
  - DB 保存処理（DuckDB）:
    - save_raw_news: INSERT ... ON CONFLICT DO NOTHING + RETURNING id を使い、新規挿入 ID を返却（チャンク挿入、トランザクション）
    - save_news_symbols / _save_news_symbols_bulk: news_symbols への紐付けをチャンク挿入し、RETURNING で実際に挿入された件数を返却
    - 銘柄コード抽出用ユーティリティ extract_stock_codes（4桁数字＋ known_codes でフィルタ、重複除去）
  - 統合収集ジョブ run_news_collection:
    - 複数 RSS ソースを順に処理し、ソース単位でエラーハンドリング（1ソース失敗でも他を継続）
    - known_codes が提供される場合、新規挿入記事に対する銘柄紐付けを一括実行

- DuckDB スキーマ (kabusys.data.schema):
  - DataPlatform に基づく3層＋実行レイヤの DDL を定義（raw / processed / feature / execution）
  - raw_prices, raw_financials, raw_news, raw_executions などの定義
  - prices_daily, market_calendar, fundamentals, news_articles, news_symbols
  - features, ai_scores（特徴量・AI スコア用）
  - signals, signal_queue, orders, trades, positions, portfolio_performance（発注・約定・ポジション管理）
  - インデックス定義（頻出クエリを想定したインデックス群）
  - init_schema(db_path) によりディレクトリ自動作成＋全DDL、インデックスを実行（冪等）
  - get_connection(db_path) で既存DBに接続（初回は init_schema を推奨）

- ETL パイプライン (kabusys.data.pipeline):
  - 差分更新指向の ETL 実装（最終取得日を参照して未取得範囲のみ取得）
  - backfill_days を使った後出し修正吸収（デフォルト 3 日）
  - 市場カレンダーの先読み（_CALENDAR_LOOKAHEAD_DAYS = 90）
  - ETLResult dataclass（取得数、保存数、品質問題リスト、エラーの集約）
  - 品質チェックモジュール（quality）と連携する設計（品質問題は収集を止めず外側で判定）
  - テストしやすい設計（id_token 注入可能など）

Changed
- （初回リリースのため特に過去変更なし）

Fixed
- （初回リリースのため特に修正履歴なし）

Security
- SSRF 対策: RSS の取得時にスキーム検証、リダイレクト先検証、プライベートアドレス除外を実装
- XML パースに defusedxml を使用し、XML 関連攻撃に耐性を向上
- レスポンスサイズ上限と Gzip 解凍後サイズチェックでメモリ DoS を軽減
- .env 読み込みは protected set（既存 OS 環境）を尊重し、上書き制御可能

Notes / Migration / Usage
- データベース:
  - デフォルトの DuckDB パスは data/kabusys.duckdb。init_schema() を最初に呼び出してスキーマを作成すること。
  - get_connection() は既存 DB への接続のみ行う（スキーマは初期化しない）。
- 設定:
  - 必須環境変数（例: JQUANTS_REFRESH_TOKEN, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, KABU_API_PASSWORD）を .env または OS 環境で設定すること。未設定時は ValueError が発生。
  - 自動 .env ロードを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。
- テスト:
  - news_collector._urlopen はモック可能で、外部ネットワークを差し替えてテストできる設計。
  - jquants_client の id_token は外部から注入できるためユニットテストが容易。
- 既知の未実装/プレースホルダ:
  - strategy, execution, monitoring サブパッケージは現時点では未実装（__init__ のみ）。発注実装や戦略ロジックは今後の課題。

開発者向け補足
- ロギング: 各モジュールで logger を使用しており、LOG_LEVEL による制御が可能。
- API レート制御: _MIN_INTERVAL_SEC = 60 / 120 に基づく固定間隔レート制御を実装。必要に応じてこの制約を調整すること。
- DB 操作は多くがトランザクションでまとめて行われ、ON CONFLICT および INSERT ... RETURNING を使うことで実際に挿入された行数が取得できるよう設計されている。

---

（この CHANGELOG はソースコードの構造・コメント・実装から推測して作成しています。実際のリリースノートとして公表する際は、テスト状況・互換性情報・既知の問題などを追記してください。）