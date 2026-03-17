CHANGELOG
=========

すべての注目すべき変更はここに記録します。本ファイルは「Keep a Changelog」準拠の形式で記載しています。

フォーマットの慣例:
- 重大な追加は「Added」
- バグ修正は「Fixed」
- 互換性のない変更は「Removed / Breaking Changes」
- セキュリティ関連は「Security」

注: この CHANGELOG は提供されたコードベースの内容から推測して作成しています（実際のコミットログではありません）。

Unreleased
----------

（現時点の開発中の変更をここに記載します）

0.1.0 - 2026-03-17
------------------

### Added
- パッケージ初版を追加。
  - パッケージ名: kabusys、バージョン: 0.1.0（src/kabusys/__init__.py）。
- 環境変数・設定管理モジュールを追加（src/kabusys/config.py）。
  - .env / .env.local の自動ロード（プロジェクトルート検出: .git または pyproject.toml）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化オプション。
  - .env 行パーサの実装（export プレフィックス、シングル/ダブルクォート、インラインコメント取り扱いなどに対応）。
  - 環境変数の必須チェック関数 (_require) と Settings クラス（J-Quants, kabu API, Slack, DB パス, 環境/ログレベル検証等）。
  - KABUSYS_ENV と LOG_LEVEL の検証（許容値の制約）。

- J-Quants API クライアントを追加（src/kabusys/data/jquants_client.py）。
  - API 呼び出し共通処理: 固定間隔のレートリミッタ（120 req/min）を実装。
  - リトライロジック（指数バックオフ、最大 3 回）、408/429/5xx のリトライ対応、429 の Retry-After 優先。
  - 401 受信時の自動トークンリフレッシュ（1 回）とトークンのモジュールレベルキャッシュ。
  - JSON パースエラーやタイムアウト処理、ページネーション対応（pagination_key を使用）。
  - データ取得関数: fetch_daily_quotes（株価日足）、fetch_financial_statements（財務データ）、fetch_market_calendar（JPX カレンダー）。
  - DuckDB への保存（冪等）関数: save_daily_quotes, save_financial_statements, save_market_calendar。ON CONFLICT DO UPDATE により重複を排除し上書き。

- ニュース収集モジュールを追加（src/kabusys/data/news_collector.py）。
  - RSS フィード取得（DEFAULT_RSS_SOURCES を含む）と記事抽出の実装。
  - セキュリティ対策: defusedxml による XML パース、SSRF 対策（リダイレクト時のスキーム検証・プライベートIPチェック）、許可されたスキームは http/https のみ。
  - レスポンスサイズ制限（MAX_RESPONSE_BYTES、デフォルト 10MB）と gzip 解凍後のサイズ検査（Gzip bomb 対策）。
  - URL 正規化とトラッキングパラメータ除去（utm_ など）、記事 ID は正規化 URL の SHA-256（先頭 32 文字）で生成し冪等性を確保。
  - テキスト前処理（URL 除去・空白正規化）と RSS pubDate の堅牢なパース（タイムゾーン処理）。
  - DuckDB への保存: save_raw_news（チャンク挿入、INSERT ... RETURNING で実際に挿入された記事 ID を返す）、save_news_symbols、内部バルク挿入関数 _save_news_symbols_bulk。
  - 銘柄コード抽出機能（4桁数字パターンと known_codes によるフィルタリング）。
  - 全体ジョブ run_news_collection: 各ソースを独立に扱い、一部ソース失敗でも継続。

- DuckDB スキーマ定義と初期化モジュールを追加（src/kabusys/data/schema.py）。
  - Raw / Processed / Feature / Execution の多層スキーマを定義（raw_prices, raw_financials, raw_news, market_calendar, prices_daily, fundamentals, features, ai_scores, signals, signal_queue, orders, trades, positions, portfolio_performance 等）。
  - 制約（PRIMARY KEY / CHECK / FOREIGN KEY）やインデックスを定義。
  - init_schema(db_path) でディレクトリ作成と DDL 実行を行い接続を返す（冪等）。
  - get_connection() を提供（初回は init_schema を推奨）。

- ETL パイプラインモジュールを追加（src/kabusys/data/pipeline.py）。
  - 差分更新設計: DB の最終取得日を参照し、バックフィル（デフォルト backfill_days=3）により後出し修正を吸収。
  - 市場カレンダーの先読みポリシー変数（_CALENDAR_LOOKAHEAD_DAYS）。
  - ETLResult dataclass（target_date, fetched/saved カウント, quality_issues, errors を保持）と補助プロパティ（has_errors, has_quality_errors）。
  - テーブル存在確認・最大日付取得ユーティリティ（_table_exists, _get_max_date）。
  - 市場日調整ヘルパー (_adjust_to_trading_day)。
  - 個別 ETL ジョブの雛形（run_prices_etl など、差分取得→保存のフロー、jquants_client を利用）。テスト容易性のため id_token 注入可能。

### Security
- ニュース収集での SSRF 対策を実装。
  - リダイレクト先のスキーム検証とプライベートアドレス拒否（_SSRFBlockRedirectHandler, _is_private_host）。
  - defusedxml を利用し XML インジェクション攻撃を軽減。
  - HTTP レスポンスのサイズ上限および gzip 解凍後の検査によりメモリ DoS を防止。
- 環境ファイル読み込み時に OS 環境変数を保護するため protected キーセットを導入（既存環境変数への上書きを制御）。

### Internal / Quality of Life
- テストしやすい設計:
  - jquants_client の id_token を外部注入可能にし、get_id_token の再帰を防ぐ allow_refresh フラグを導入。
  - news_collector の _urlopen をモック可能な形で分離。
- ロギングを適切に配置（情報・警告・例外ログ）し、障害時のトレースを容易に。
- 各種ユーティリティ関数（_to_float, _to_int, preprocess_text, _normalize_url, extract_stock_codes など）を実装。

### Known limitations / Notes
- 実行には duckdb と defusedxml 等の依存が必要（requirements に明示する想定）。
- ETL の品質チェックモジュール（quality）は参照されているがこのスニペットでは定義が省略されている（別ファイルで提供される想定）。
- run_prices_etl の戻り値箇所に不完全なタプルリターンのように見える行（ファイル末尾）があります。実運用前に完全な戻り値の確認を推奨。

Acknowledgements
----------------
この CHANGELOG は提供されたコードを元に推測して作成しました。実際のリリースノートはコミット履歴・差分に基づいて作成してください。必要であれば、各関数やファイルごとの詳細な変更点（行単位での説明）も作成できます。