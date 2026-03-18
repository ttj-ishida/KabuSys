CHANGELOG
=========

すべての注目すべき変更点を記録します。本ファイルは Keep a Changelog の形式に従います。
リリース日付はパッケージの __version__ とリポジトリの現状から推定して付与しています。

フォーマット:
- Added: 新機能
- Changed: 既存機能の変更
- Fixed: バグ修正
- Security: セキュリティに関する重要事項
- Deprecated / Removed: 廃止・削除事項（該当なしの場合は省略）

Unreleased
----------

- なし

0.1.0 - 2026-03-18
------------------

Added
- パッケージ初回公開 (kabusys 0.1.0)
  - パッケージ概要: 日本株自動売買システムの基盤モジュール群（data, strategy, execution, monitoring）を実装。
  - バージョン定義: src/kabusys/__init__.py にて __version__ = "0.1.0" を設定。

- 環境設定管理 (src/kabusys/config.py)
  - .env ファイルまたは環境変数から設定を読み込む Settings クラスを追加。
  - 自動 .env ロード機能: プロジェクトルート（.git または pyproject.toml）を基に .env / .env.local を自動読み込み。
  - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数により自動ロードを無効化可能（テスト用フック）。
  - .env パースの堅牢化:
    - export KEY=val 形式に対応
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理
    - インラインコメント処理（クォート無し時は '#' の前にスペースがあればコメント扱い）
  - 必須環境変数の明示とバリデーション（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等）。
  - システム設定の検証: KABUSYS_ENV (development|paper_trading|live)、LOG_LEVEL（DEBUG/INFO/...）の値検証および便利プロパティ（is_live, is_paper, is_dev）。
  - データベースパス取得: DUCKDB_PATH / SQLITE_PATH のデフォルトを提供。

- J-Quants API クライアント (src/kabusys/data/jquants_client.py)
  - データ取得機能:
    - 株価日足 (fetch_daily_quotes)
    - 財務データ（四半期 BS/PL、fetch_financial_statements）
    - JPX マーケットカレンダー (fetch_market_calendar)
  - 認証: リフレッシュトークンから ID トークンを取得する get_id_token 実装。トークンキャッシュをモジュールレベルで保持。
  - 安全かつ堅牢な HTTP 処理:
    - 固定間隔のレートリミッタ (_RateLimiter) により 120 req/min を遵守
    - リトライロジック（指数バックオフ、最大 3 回、対象ステータス: 408/429/5xx）
    - 401 受信時はトークンを自動リフレッシュして 1 回だけリトライ
    - JSON デコード失敗時のエラーハンドリング
  - DuckDB への保存関数（冪等設計）:
    - save_daily_quotes, save_financial_statements, save_market_calendar:
      - ON CONFLICT DO UPDATE による上書き（重複回避）
      - PK 欠損行のスキップとログ出力
      - fetched_at を UTC で記録してデータフェッチ時刻をトレース可能
  - 型変換ユーティリティ: _to_float / _to_int（空値や不正値に対して None を返す、安全な変換ロジックを実装）

- ニュース収集モジュール (src/kabusys/data/news_collector.py)
  - RSS フィード取得 (fetch_rss) と記事保存 API (save_raw_news, save_news_symbols, _save_news_symbols_bulk) を実装。
  - 主な設計/機能:
    - デフォルト RSS ソース（Yahoo Finance ビジネスカテゴリ）
    - URL 正規化 (_normalize_url) とトラッキングパラメータ除去（utm_, fbclid 等）
    - 記事 ID は正規化 URL の SHA-256 の先頭32文字で生成（冪等性確保）
    - defusedxml を用いた XML パース（XML Bomb 等の緩和）
    - SSRF 対策:
      - URL スキーム検証（http/https のみ許可）
      - リダイレクト時のスキーム/ホスト検証（_SSRFBlockRedirectHandler）
      - プライベートアドレス判定（_is_private_host）により内部アドレスを拒否
    - レスポンスサイズ制限（MAX_RESPONSE_BYTES=10MB）と gzip 解凍後の追加チェック（Gzip bomb 対策）
    - テキスト前処理（URL除去、空白正規化）
    - DB 保存の最適化:
      - チャンク化してバルク INSERT（_INSERT_CHUNK_SIZE）
      - INSERT ... RETURNING により実際に挿入された ID を返却
      - トランザクションでのコミット/ロールバック
    - 銘柄コード抽出ユーティリティ (extract_stock_codes): 正規表現による 4 桁コード抽出と既知コードセットによるフィルタリング
    - 統合ジョブ run_news_collection により複数ソースの収集・保存・銘柄紐付けを処理

- DuckDB スキーマ定義・初期化 (src/kabusys/data/schema.py)
  - DataPlatform.md に基づく 3 層（Raw / Processed / Feature） + Execution 層のテーブル DDL を実装。
  - 代表的テーブル:
    - Raw: raw_prices, raw_financials, raw_news, raw_executions
    - Processed: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature: features, ai_scores
    - Execution: signals, signal_queue, orders, trades, positions, portfolio_targets, portfolio_performance
  - インデックス群を定義（頻出クエリパターンを想定）。
  - init_schema(db_path) によりディレクトリ自動作成を含めてスキーマ初期化を行い、接続を返す。get_connection() で既存 DB へ接続可能。

- ETL パイプライン基盤 (src/kabusys/data/pipeline.py)
  - 差分更新を意識した ETL 設計:
    - 最終取得日からの差分取得・バックフィル（デフォルト backfill_days=3）
    - 市場カレンダー先読み（_CALENDAR_LOOKAHEAD_DAYS）
    - 最小データ開始日 _MIN_DATA_DATE
  - ETLResult データクラス: ETL 実行結果（取得件数、保存件数、品質問題、エラー）を保持し、辞書化可能（監査ログ用）。
  - テーブル存在チェック、最大日付取得などのヘルパー関数 (_table_exists, _get_max_date, get_last_price_date 等) を提供。
  - run_prices_etl の骨組みを実装（差分計算 → jq.fetch_daily_quotes → jq.save_daily_quotes → 結果ロギング）。（注: ファイル末尾での実装は途中までの表示）

Changed
- なし（初回リリースのため既存変更はなし）

Fixed
- なし（初回リリースのため既存修正はなし）

Security
- RSS パーサに defusedxml を採用し XML 関連攻撃を緩和。
- RSS フェッチで以下の SSRF 対策を実施:
  - URL スキーム検証（http/https のみ）
  - リダイレクト先のスキーム・ホスト検証
  - プライベート/ループバック/リンクローカルアドレスへのアクセス拒否
  - レスポンスサイズ上限と gzip 解凍後サイズチェック（DoS / bomb 緩和）
- J‑Quants API クライアントでトークンの自動リフレッシュ処理を実装（401 発生時に一度のみリフレッシュして再試行）。

Notes / Implementation details
- テスト性:
  - news_collector._urlopen はテストでモック可能（ネットワーク呼び出しの差し替えに対応）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD で自動 .env 読み込みを無効化でき、テスト環境での副作用を抑制可能。
- 数値変換の仕様:
  - _to_int は "1.0" のような文字列を float 経由で整数化する一方、"1.9" のように小数部が残る場合は None を返して意図しない切り捨てを防止する。
- DuckDB の DDL は FOREIGN KEY 制約や CHECK 制約を含むが、実際の運用ではパフォーマンスや互換性に応じた調整が必要となる場合がある。

Deprecated
- なし

Removed
- なし

Acknowledgements / その他
- 本リリースは基盤機能（設定管理、外部データ取得・保存、ETL 基盤、ニュース収集、スキーマ初期化）を中心に実装した初期リリースです。戦略（strategy）、実行（execution）、監視（monitoring）モジュールはパッケージ構成として存在しますが、個別実装は今後拡張される想定です。