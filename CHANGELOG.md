CHANGELOG
=========

すべての重要な変更点を一元管理します。  
フォーマットは "Keep a Changelog" に準拠しています。  

[Unreleased]
-------------

- （なし）

[0.1.0] - 2026-03-17
--------------------

初回リリース。日本株自動売買システム「KabuSys」の基盤機能を一通り実装しました。主な追加内容は以下の通りです。

Added
- パッケージメタ情報
  - パッケージバージョンを src/kabusys/__init__.py にて __version__ = "0.1.0" として追加。
  - エクスポート対象モジュールを __all__ で定義。

- 環境設定管理 (src/kabusys/config.py)
  - .env / .env.local または環境変数から設定を読み込む自動ロード機能を実装。
    - プロジェクトルートは .git または pyproject.toml を基準に __file__ から探索するため、CWD に依存しない。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能（テスト用フック）。
    - .env.local は .env より優先して上書き（ただし OS 環境変数は保護）。
  - .env のパースは export 形式、クォート、インラインコメント、エスケープシーケンスに対応する堅牢な実装。
  - 必須の環境変数取得ヘルパー _require と Settings クラスを提供。
    - JQUANTS_REFRESH_TOKEN / KABU_API_PASSWORD / SLACK_BOT_TOKEN / SLACK_CHANNEL_ID 等をプロパティで取得可能。
    - KABUSYS_ENV（development/paper_trading/live）・LOG_LEVEL の検証を実装。
    - 各種パス（DuckDB/SQLite）はデフォルト値と expanduser 対応。

- J-Quants API クライアント (src/kabusys/data/jquants_client.py)
  - 日足（OHLCV）、財務指標（四半期 BS/PL）、JPX マーケットカレンダーの取得機能を実装。
  - レート制御: 固定間隔スロットリングによる 120 req/min 制限（_RateLimiter）。
  - リトライ機能: 指数バックオフ（最大 3 回）、対象ステータス（408/429/>=500）でリトライ。
    - 429 の場合は Retry-After ヘッダを考慮。
  - 認証トークン管理:
    - get_id_token(): リフレッシュトークンから id_token を取得（POST）。
    - モジュールレベルの id_token キャッシュを持ち、401 受信時に一度だけ自動リフレッシュして再試行する仕組み。
  - ページネーション対応 fetch_* 関数（fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar）。
  - DuckDB への冪等保存関数（save_daily_quotes / save_financial_statements / save_market_calendar）を実装。
    - INSERT ... ON CONFLICT DO UPDATE による重複排除。
    - fetched_at を UTC タイムスタンプで記録して look-ahead bias を防止。
    - 型変換ユーティリティ (_to_float / _to_int) を提供（不正値は None）。

- ニュース収集 (src/kabusys/data/news_collector.py)
  - RSS フィードからニュース記事を収集し raw_news / news_symbols へ保存するモジュールを実装。
  - セキュリティ対策:
    - defusedxml を使用した安全な XML パース（XML Bomb 等への対策）。
    - SSRF 対策: fetch 前にホストのプライベート判定、リダイレクト先の検査（_SSRFBlockRedirectHandler）、許容スキームは http/https のみ。
    - レスポンスサイズ上限（MAX_RESPONSE_BYTES=10MB）を設け、GZIP 解凍後も検査（gzip bomb 対策）。
    - URL 正規化によりトラッキングパラメータ (utm_*, fbclid, gclid, ref_, _ga など) を削除。
  - 記事ID設計: 正規化 URL の SHA-256 の先頭32文字を ID として冪等性を保証。
  - テキスト前処理: URL 除去、空白正規化（preprocess_text）。
  - 銘柄コード抽出: 正規表現ベースで 4 桁銘柄コードを抽出し、known_codes によるフィルタリング（extract_stock_codes）。
  - DB 保存:
    - save_raw_news(): INSERT ... ON CONFLICT DO NOTHING RETURNING id を用い、実際に挿入された ID を返す。チャンク単位＆トランザクションで実行。
    - save_news_symbols(), _save_news_symbols_bulk(): 銘柄紐付けをチャンクで一括保存。RETURNING を使って挿入数を正確に返す。
  - テスト用フック: _urlopen をモック可能に設計。

- DuckDB スキーマ定義・初期化 (src/kabusys/data/schema.py)
  - DataSchema.md に基づく3層（Raw / Processed / Feature / Execution）テーブル群を定義。
    - raw_prices, raw_financials, raw_news, raw_executions
    - prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - features, ai_scores
    - signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各カラムに CHECK 制約や PRIMARY KEY / FOREIGN KEY を設定してデータ整合性を担保。
  - 頻出クエリ向けの INDEX を定義（例: idx_prices_daily_code_date, idx_signal_queue_status 等）。
  - init_schema(db_path) で初期化と DDL 実行、get_connection(db_path) で接続取得。

- ETL パイプライン基盤 (src/kabusys/data/pipeline.py)
  - ETL 実行結果を表すデータクラス ETLResult（品質問題リスト・エラーリスト、シリアライズ用 to_dict() を含む）を実装。
  - 差分更新ヘルパー:
    - get_last_price_date / get_last_financial_date / get_last_calendar_date により DB の最終取得日を返す。
    - _adjust_to_trading_day() で非営業日を直近営業日に補正するロジックを実装（market_calendar を参照）。
  - run_prices_etl(): 株価差分 ETL の実装（差分算出、backfill_days による再取得を考慮、jquants_client 呼び出し）。
  - ETL 設計方針: 差分更新デフォルトは営業日単位、backfill（デフォルト 3 日）で後出し修正を吸収、品質チェックは fail-fast しない性質。

Changed
- （初回リリースのため変更履歴はなし）

Fixed
- （初回リリースのため修正履歴はなし）

Security
- RSS 取得と XML パースにおいて SSRF/XXE/ZIP-Bomb 相当の対策を取り入れています（defusedxml、ホスト判定、リダイレクト検査、レスポンスサイズ制限、gzip 解凍後検査など）。

Notes / Usage
- 主要な公開 API（例）
  - 設定: from kabusys.config import settings
  - J-Quants: from kabusys.data.jquants_client import fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar, get_id_token, save_* 関数
  - ニュース: from kabusys.data.news_collector import run_news_collection, fetch_rss, save_raw_news
  - DB スキーマ: from kabusys.data.schema import init_schema, get_connection
  - ETL: from kabusys.data.pipeline import run_prices_etl, ETLResult など
- デフォルトではプロジェクトルートの .env / .env.local を自動読み込みします。CI/テスト等で自動ロードを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- テスト容易性のため、news_collector._urlopen や config の自動読み込みの無効化など、差し替え可能なフックを用意しています。

Breaking Changes
- なし（初回リリース）

Acknowledgements / Design
- 各モジュールの docstring に設計方針や目的を明記しています（例: Look-ahead bias を避けるための fetched_at、API レート制限、冪等性設計など）。

今後予定（参考）
- 品質チェックモジュール (quality) の実装と ETL 統合（pipeline 内での呼び出しを想定）
- execution / strategy / monitoring の具象実装（現状はパッケージ階層を用意）
- テストカバレッジの充実、CI 設定、パッケージ配布（wheel, PyPI）

-- END --