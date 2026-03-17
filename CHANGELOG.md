CHANGELOG
=========

すべての注目すべき変更履歴を記録します。  
このファイルは「Keep a Changelog」準拠の形式で記述しています。

Unreleased
----------

- （なし）

[0.1.0] - 2026-03-17
--------------------

Added
- 初期リリース。Python パッケージ kabusys を追加。
  - パッケージバージョン: 0.1.0（src/kabusys/__init__.py に定義）
  - 公開モジュール: data, strategy, execution, monitoring（__all__）

- 環境設定管理（src/kabusys/config.py）
  - .env ファイルおよび OS 環境変数から設定を読み込む自動ロード機能（プロジェクトルート検出: .git または pyproject.toml を使用）。
  - .env のパース実装（export プレフィックス、クォート・エスケープ、インラインコメント対応）。
  - .env の上書きルール（OS 環境変数を保護する protected set、.env → .env.local の優先度）。
  - 自動ロードを無効化する環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD のサポート。
  - 設定取得用 Settings クラス（必須変数チェック、既定値、バリデーション: 環境種別・ログレベルの許容値）。
  - 利用される主要設定項目のプロパティ（J-Quants トークン、kabu API、Slack、DB パスなど）。

- J-Quants API クライアント（src/kabusys/data/jquants_client.py）
  - API 呼び出しラッパー _request を実装（JSON デコード、例外ハンドリング、最大リトライ、指数バックオフ、429 の Retry-After 考慮）。
  - 固定間隔のレート制限実装（120 req/min を守る _RateLimiter）。
  - id_token のキャッシュと自動リフレッシュ（401 受信時に 1 回のみリフレッシュして再試行）。
  - ページネーション対応のデータ取得関数:
    - fetch_daily_quotes（株価日足）
    - fetch_financial_statements（財務四半期データ）
    - fetch_market_calendar（JPX カレンダー）
  - DuckDB への冪等保存関数（ON CONFLICT DO UPDATE を用いた保存）:
    - save_daily_quotes, save_financial_statements, save_market_calendar
  - 型変換ユーティリティ: _to_float, _to_int（空値・不正値に安全に対応）
  - ロギングによる取得／保存数の記録

- ニュース収集モジュール（src/kabusys/data/news_collector.py）
  - RSS フィードからの記事収集、前処理、DuckDB への冪等保存ワークフローを実装
  - セキュリティ／堅牢性機能:
    - defusedxml を使用した XML パース（XML Bomb 等への対策）
    - SSRF 対策: URL スキーム検証（http/https 限定）、ホスト/IP のプライベート判定（_is_private_host）、リダイレクト時の検証ハンドラ（_SSRFBlockRedirectHandler）
    - レスポンスサイズ上限（MAX_RESPONSE_BYTES）と Gzip 圧縮の検査（Gzip bomb 対策）
    - URL 正規化とトラッキングパラメータ削除（_normalize_url）
    - 記事 ID は正規化 URL の SHA-256（先頭32文字）で生成（冪等性）
  - RSS 取得・パース:
    - fetch_rss（フィード取得、gzip 解凍、XML パース、title/content 前処理、pubDate パース）
    - preprocess_text（URL 削除、空白正規化）
    - _parse_rss_datetime（pubDate を UTC naive datetime に変換、失敗時は代替時刻）
  - DB 保存機能（DuckDB）:
    - save_raw_news（チャンク分割・トランザクション・INSERT ... RETURNING を使用し新規挿入 ID を返却）
    - save_news_symbols / _save_news_symbols_bulk（記事と銘柄コードの紐付けを一括で保存、ON CONFLICT で重複排除）
  - 銘柄コード抽出:
    - extract_stock_codes（本文・タイトルから4桁銘柄コード候補を抽出し known_codes でフィルタ）
  - 統合ジョブ:
    - run_news_collection（複数 RSS ソースを個別に扱い、失敗したソースをスキップしつつ新規保存数を集計）

- DuckDB スキーマ定義（src/kabusys/data/schema.py）
  - Raw / Processed / Feature / Execution 層のテーブル DDL を定義（raw_prices, raw_financials, raw_news, raw_executions, prices_daily, market_calendar, fundamentals, news_articles, news_symbols, features, ai_scores, signals, signal_queue, orders, trades, positions, portfolio_performance など）
  - 制約（PRIMARY KEY、CHECK、FOREIGN KEY）やインデックスを含む設計
  - init_schema(db_path) による初期化（親ディレクトリ自動作成、冪等的テーブル作成）
  - get_connection(db_path) による接続取得（スキーマ初期化は行わない）

- ETL パイプライン（src/kabusys/data/pipeline.py）
  - ETL 設計（差分更新、backfill による後出し修正吸収、品質チェックを考慮した処理方針）
  - ETLResult データクラス（取得数・保存数・品質問題・エラーの集約、辞書化メソッド）
  - テーブル存在チェック、最大日付取得ユーティリティ（_table_exists, _get_max_date）
  - 市場カレンダー補正ヘルパー（_adjust_to_trading_day）
  - 差分更新ヘルパー（get_last_price_date, get_last_financial_date, get_last_calendar_date）
  - 個別 ETL ジョブ（株価差分ETL の run_prices_etl を含む設計・実装。差分計算、jq.fetch_* の呼び出し、jq.save_* による保存、ログ出力）

Security
- RSS パーサに defusedxml を用いるなど、XML/SSRF/Gzip Bomb/巨大レスポンスなどに対する複数の防御を実装
- .env の読み込みは OS 環境変数を保護する仕組みを導入（override/protected）
- J-Quants クライアントは認証トークンの自動リフレッシュとリトライ戦略を備え、失敗時に詳細ログを残す

Changed
- （新規リリースのため該当なし）

Fixed
- （新規リリースのため該当なし）

Removed
- （新規リリースのため該当なし）

Notes / Known limitations
- strategy と execution のパッケージは初期のパッケージ構成として空の __init__ ファイルが追加されており、戦略・発注ロジックは個別実装が必要です。
- ETL パイプラインは差分更新・品質チェックを考慮した設計が含まれますが、運用時の細かなチューニング（backfill 日数、ロギング/メトリクス連携等）は今後の改善候補です。

---