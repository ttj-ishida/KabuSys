# CHANGELOG

すべての変更は Keep a Changelog の形式に準拠して記載しています。  
初回リリース (0.1.0) における実装内容を、コードベースから推測してまとめています。

## [0.1.0] - 2026-03-17

### Added
- パッケージ基盤
  - kabusys パッケージを追加。サブパッケージとして data, strategy, execution, monitoring を公開。
  - バージョン: 0.1.0 (src/kabusys/__init__.py)

- 設定 / 環境変数管理 (src/kabusys/config.py)
  - .env ファイルおよび環境変数から設定を自動読み込みする仕組みを実装。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能（テスト向け）。
    - プロジェクトルート検出は __file__ から親ディレクトリを探索して .git または pyproject.toml を探す実装（配布後の実行でも動作）。
  - .env 解析の強化:
    - `export KEY=val` 形式対応、クォート文字列のバックスラッシュエスケープ処理、コメント処理の細かなルールを実装。
  - Settings クラスを提供し、主要な環境変数へのアクセサを実装:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL (デフォルト http://localhost:18080/kabusapi)
    - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DUCKDB_PATH (デフォルト data/kabusys.duckdb), SQLITE_PATH (デフォルト data/monitoring.db)
    - KABUSYS_ENV (development / paper_trading / live)、LOG_LEVEL（DEBUG/INFO/...）の検証ロジック
    - is_live/is_paper/is_dev 等のユーティリティプロパティ

- J-Quants API クライアント (src/kabusys/data/jquants_client.py)
  - API 呼び出しの共通基盤を実装:
    - レート制限: 固定間隔スロットリングで 120 req/min を保証（_RateLimiter）
    - 再試行ロジック: 指数バックオフ、最大 3 回、対象ステータスに基づくリトライ（408/429/5xx 等）
    - 401 受信時はリフレッシュトークンから id_token を自動更新して 1 回リトライ（無限再帰防止の allow_refresh フラグ）
    - id_token のモジュールレベルキャッシュを共有（ページネーション時のトークン共有）
  - データ取得関数を実装（ページネーション対応）
    - fetch_daily_quotes (日足 OHLCV)
    - fetch_financial_statements (四半期 BS/PL)
    - fetch_market_calendar (JPX カレンダー)
  - DuckDB への保存関数（冪等）
    - save_daily_quotes: raw_prices テーブルへ ON CONFLICT DO UPDATE
    - save_financial_statements: raw_financials テーブルへ ON CONFLICT DO UPDATE
    - save_market_calendar: market_calendar テーブルへ ON CONFLICT DO UPDATE
  - 型変換ユーティリティ: _to_float, _to_int（安全な変換ロジック、空値/不正値は None）

- ニュース収集モジュール (src/kabusys/data/news_collector.py)
  - RSS フィードから記事を取得・前処理・DuckDB へ保存する一連処理を実装。
  - 設計上の主な特徴:
    - トラッキングパラメータ (utm_*, fbclid, gclid, ref_, _ga など) の除去、URL 正規化
    - 記事 ID は正規化 URL の SHA-256 の先頭32文字で生成し冪等性を担保
    - defusedxml による XML パース（XML Bomb 等の対策）
    - SSRF 対策:
      - URL スキームは http/https のみ許可
      - ホストがプライベート/ループバック/リンクローカル/マルチキャストであれば拒否
      - リダイレクト時に検証するカスタム HTTPRedirectHandler を実装
    - 受信サイズの上限 MAX_RESPONSE_BYTES = 10MB（gzip 展開後も検証）
    - gzip 対応、Content-Length による事前チェック
    - テキスト前処理: URL 削除・空白正規化
    - DB 保存はチャンク化してトランザクション内で実行、INSERT ... RETURNING を利用して実際に挿入された件数を返す
  - 公開関数:
    - fetch_rss(url, source, timeout) -> list[NewsArticle]
    - save_raw_news(conn, articles) -> list[str]（新規挿入された article.id のリスト）
    - save_news_symbols(conn, news_id, codes) -> int
    - run_news_collection(conn, sources=None, known_codes=None, timeout=30) -> dict[source_name, 新規件数]

- スキーマ定義 / DB 初期化 (src/kabusys/data/schema.py)
  - DuckDB 用スキーマを定義（Raw / Processed / Feature / Execution の層を想定）
  - 主なテーブル定義（制約付き）:
    - Raw: raw_prices, raw_financials, raw_news, raw_executions
    - Processed: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature: features, ai_scores
    - Execution: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - インデックス定義を提供（頻出クエリ向け）
  - init_schema(db_path) により DB ファイルの親ディレクトリ作成・テーブル作成を行い DuckDB 接続を返却
  - get_connection(db_path) で既存 DB への接続を取得（スキーマ初期化は行わない）

- ETL パイプライン基盤 (src/kabusys/data/pipeline.py)
  - ETLResult dataclass を追加（ETL 実行結果の集約、品質問題・エラーの保持、辞書変換）
  - 差分更新ヘルパー:
    - get_last_price_date, get_last_financial_date, get_last_calendar_date
    - _table_exists, _get_max_date (汎用)
  - 市場カレンダー補正: _adjust_to_trading_day（非営業日の調整）
  - run_prices_etl 実装（差分取得・バックフィル対応）
    - デフォルト最小データ開始日: 2017-01-01
    - デフォルトバックフィル: 3 日（最終取得日の数日前から再取得）
    - 市場カレンダーの先読み設定等を想定（定数あり）

### Security
- RSS/XML 関連:
  - defusedxml を使用して XML パースを安全化。
  - SSRF 対策: URL スキーム検証、ホスト(IP) のプライベート判定、リダイレクト時の事前検証を実装。
  - レスポンスサイズ検査および gzip 展開後のサイズ検査を行い、リソース消費攻撃に対処。

- API クライアント:
  - タイムアウト設定、再試行・バックオフ、401 自動リフレッシュを備え、堅牢性を確保。

### Notes / Defaults
- 環境変数の必須チェックは Settings のプロパティで行われ、未設定の場合は ValueError を送出する（例: JQUANTS_REFRESH_TOKEN, SLACK_BOT_TOKEN など）。
- DuckDB のデフォルトパスは data/kabusys.duckdb。init_schema は親ディレクトリを自動作成する。
- ニュース収集のデフォルト RSS ソースは Yahoo Finance のビジネスカテゴリ（DEFAULT_RSS_SOURCES）。
- jquants_client は 120 req/min を想定した固定間隔レートリミッタを使用しているため、外部で追加のスロットリングを行う必要は基本的にない。

### Known limitations / TODO（コードから推測）
- pipeline.run_prices_etl は差分ETLの主要ロジックを含むが、品質チェック (quality モジュール) や calendar の自動先読み、financials の ETL、統合 ETL ワークフローの完成など、さらに実装が想定される箇所がある（quality モジュールへの参照あり）。
- strategy / execution / monitoring サブパッケージは __init__.py のみ存在し、実装は今後拡張予定。
- エラーハンドリングは主要な箇所で実装されているが、運用監視（Slack 通知や自動再試行ポリシー等）は外部コンポーネントでの実装を想定。

---

以上がコードベースから推測して作成した初回リリース（0.1.0）の変更点一覧です。追加で、リリースノートの粒度（より詳細な関数単位の変更ログやコミット単位の履歴）を希望される場合は、その旨をお知らせください。