CHANGELOG
=========

すべての注目すべき変更をこのファイルに記録します。
このファイルは Keep a Changelog の形式に準拠します。

フォーマット:
- Unreleased: 今後の変更（空のままにしておくか、進行中の作業を記載）
- 各リリース: バージョン番号と日付、その下にカテゴリ（Added / Changed / Fixed / Security など）

Unreleased
----------
- （現在未リリースの変更はありません）

0.1.0 - 2026-03-18
------------------
Added
- パッケージ初期リリース: kabusys (バージョン 0.1.0)
  - パッケージ公開情報:
    - src/kabusys/__init__.py: __version__ = "0.1.0"、主要サブパッケージを __all__ に登録 (data, strategy, execution, monitoring)

- 環境変数・設定管理モジュール (src/kabusys/config.py)
  - .env ファイルおよび環境変数から設定を自動読み込みする仕組みを実装
    - プロジェクトルートを .git または pyproject.toml から探索して自動読み込み (.env → .env.local の順で読み込み、.env.local は上書き)
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応（テスト向け）
    - OS 環境変数は protected として上書き保護
  - .env パーサーは以下に対応:
    - export KEY=val 形式
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理
    - インラインコメントの取り扱い（クォート有無で振る舞いを区別）
  - Settings クラスを提供（settings インスタンス経由で利用）
    - J-Quants / kabu / Slack / DB パスなどのプロパティを定義
    - env (development|paper_trading|live) と log_level の値検証
    - duckdb/sqlite のパスを Path として返すユーティリティ
    - is_live / is_paper / is_dev の便宜プロパティ

- J-Quants API クライアント (src/kabusys/data/jquants_client.py)
  - API 呼び出しの共通基盤を実装
    - レート制限（120 req/min）を守る固定間隔スロットリング RateLimiter を実装
    - 冪等性とページネーション対応（pagination_key を用いたループ）
    - リトライロジック（指数バックオフ、最大 3 回。HTTP 408/429 や 5xx、ネットワーク例外を再試行）
    - 401 応答時はリフレッシュトークンから id_token を自動更新して 1 回リトライ
    - id_token キャッシュ（モジュールレベル）を用いてページネーション間で共有
    - JSON デコードエラー時の詳細メッセージ
  - データ取得関数:
    - fetch_daily_quotes: 株価日足（OHLCV）を取得（ページネーション対応）
    - fetch_financial_statements: 財務データ（四半期 BS/PL）を取得（ページネーション対応）
    - fetch_market_calendar: JPX マーケットカレンダーを取得
  - DuckDB への保存関数（冪等）
    - save_daily_quotes / save_financial_statements / save_market_calendar
    - INSERT ... ON CONFLICT DO UPDATE を使用して重複を排除・更新
    - fetched_at を UTC ISO8601 で保存し、取得時点をトレース可能に
  - ユーティリティ:
    - _to_float / _to_int: 安全な型変換（空値や不正文字列を None に変換）

- ニュース収集モジュール (src/kabusys/data/news_collector.py)
  - RSS フィードからニュース取得・前処理・DuckDB への保存を実装
  - セキュリティ・堅牢性対策:
    - defusedxml を使用して XML Bomb 等を防止
    - SSRF 対策: リダイレクト時にスキーム検証・ホストがプライベート/ループバックでないか検査するハンドラを実装
    - URL スキーム制限（http/https のみ）とホストのプライベート判定機能
    - レスポンス受信サイズ上限（MAX_RESPONSE_BYTES = 10 MB）と gzip 解凍後のサイズチェック（Gzip bomb 対策）
    - User-Agent と Accept-Encoding ヘッダの付与
  - データ処理:
    - URL 正規化 (クエリソート、utm_* 等トラッキングパラメータ除去、フラグメント削除)
    - 記事ID は正規化した URL の SHA-256 の先頭32文字を使用して冪等性を担保
    - テキスト前処理（URL 除去・空白正規化）
    - pubDate のパース（RFC2822 → UTC）とフォールバック（失敗時は現在時刻）
  - DB 保存:
    - save_raw_news: INSERT ... ON CONFLICT DO NOTHING + RETURNING id を用い、実際に挿入された記事 ID のリストを返す
    - チャンク単位（_INSERT_CHUNK_SIZE）でのバルク挿入と 1 トランザクションでのコミット／ロールバック
    - save_news_symbols / _save_news_symbols_bulk: 記事と銘柄コードの紐付けを冪等に保存（ON CONFLICT DO NOTHING + RETURNING）
  - 銘柄抽出:
    - extract_stock_codes: 本文から4桁数字（例 "7203"）を抽出し、既知の銘柄セットでフィルタ
  - 統合ジョブ:
    - run_news_collection: 複数 RSS ソースから取得 → raw_news に保存 → 新規記事のみ銘柄紐付け（既知銘柄セットを使用）
    - 各ソースは個別にエラーハンドリング（1 ソース失敗でも他は継続）

- DuckDB スキーマ定義と初期化 (src/kabusys/data/schema.py)
  - DataSchema.md に準拠した 3 層（Raw / Processed / Feature）+ Execution レイヤの DDL を実装
    - Raw 層: raw_prices, raw_financials, raw_news, raw_executions
    - Processed 層: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature 層: features, ai_scores
    - Execution 層: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各テーブルにチェック制約・PRIMARY KEY・外部キーを設定
  - インデックス定義（頻出クエリに対するインデックスを作成）
  - init_schema(db_path): DB ファイルの親ディレクトリを自動作成し、全テーブル・インデックスを冪等に作成して接続を返す
  - get_connection(db_path): 既存 DB への接続を返す（スキーマ初期化は行わない）

- ETL パイプライン基盤 (src/kabusys/data/pipeline.py)
  - ETLResult dataclass を導入し ETL 実行結果（取得件数・保存件数・品質問題・エラー等）を構造化して返却
  - 差分更新・バックフィル方針の実装（デフォルト backfill_days=3）
  - 市場カレンダーの先読み設定（_CALENDAR_LOOKAHEAD_DAYS = 90）
  - ヘルパー実装:
    - _table_exists / _get_max_date: テーブル存在確認と最大日付取得
    - _adjust_to_trading_day: 非営業日の場合に直近の営業日へ調整（カレンダーがない場合はフォールバック）
    - get_last_price_date / get_last_financial_date / get_last_calendar_date
  - 個別 ETL ジョブ:
    - run_prices_etl: 差分ETL の基本ロジック（date_from の自動算出、J-Quants からの取得、保存）を実装
      - 最終取得日から backfill_days 分前を再取得して API の後出し修正を吸収する戦略
      - 取得数・保存数を返す

- パッケージ構成スケルトン
  - src/kabusys/data/__init__.py、src/kabusys/execution/__init__.py、src/kabusys/strategy/__init__.py を配置（strategy/execution は将来的な機能拡張のためのプレースホルダ）

Security
- ニュース収集に関して SSRF / XML 攻撃 / Gzip Bomb / 大容量レスポンスなど複数の攻撃ベクトルへ対策を実装
- .env 読み込みは OS 環境変数を保護する仕組みを導入

Notes / Implementation details
- DuckDB を主要データストアとして採用し、INSERT の冪等性やトランザクション制御を重視している（ON CONFLICT, INSERT ... RETURNING, 明示的トランザクション）
- ロギングを各モジュールで利用しており、処理の可観測性を確保
- 一部モジュール（pipeline の品質チェック等）は quality モジュールなど他コンポーネントに依存する想定で設計されている（実装は別途）
- strategy / execution / monitoring の本格実装は今後のリリースで追加予定

既知の制限 / 今後の予定（推測）
- pipeline の品質チェック部分 (quality モジュール) は別実装が必要
- 実際の発注処理（kabu ステーション連携）や戦略ロジックは未実装（execution/strategy パッケージにて実装予定）
- 単体テスト・統合テスト、CI 設定の追加が未記載（テスト用の環境フラグは config に含む）

お問い合わせ・貢献
- バグ報告・機能要望・プルリクエストはリポジトリに対して行ってください。追って検討し、CHANGELOG に反映します。